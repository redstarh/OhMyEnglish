// 회차 b3 — 영상 위치 저장의 경계 가르기. 1) 재생 13초 → 새로 고침(pagehide) → 저장값·다시 연 위치
// 2) 저장 위치 S>0 에서 열어 재생 12초 더 → SPA 이동(← 학습 목록) → 저장값이 S 로 되돌아가는가
import { writeFileSync } from "node:fs";
import { connect, pageTarget, sleep, EV, PORT } from "./cdp.mjs";
const APP = "http://localhost:3000", API = "http://localhost:8002";
const DAY = process.argv[2] ?? "4";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
await c.send("Page.enable"); await c.send("Runtime.enable");
const out = {}; const note = (k, v) => { out[k] = v; console.log(k, JSON.stringify(v)); };
const ev = async (expression) => { const r = await c.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text); return r.result.value; };
const waitFor = async (e, t = 15000, s = 50) => { const st = Date.now(); while (Date.now() - st < t) { try { if (await ev(e)) return; } catch {} await sleep(s); } throw new Error("timeout " + e); };
const prog = async () => (await (await fetch(`${API}/api/course/days/${DAY}`)).json()).progress;
const btnReady = `(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === '시작'); return !!b && Object.keys(b).some(k => k.startsWith('__reactProps')); })()`;
async function frame() { for (let i = 0; i < 40; i++) { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); const f = l.find((t) => t.type === "iframe" && t.url.includes("youtube.com/embed")); if (f) { const fc = await connect(f.webSocketDebuggerUrl); await fc.send("Runtime.enable"); return fc; } await sleep(250); } return null; }
const vs = async (fc) => (await fc.send("Runtime.evaluate", { returnByValue: true, expression: `(() => { const v = document.querySelector('video'); const mp = document.querySelector('#movie_player'); return { t: v ? Math.round(v.currentTime*10)/10 : null, paused: v?.paused, state: mp?.getPlayerState?.() }; })()` })).result.value;
async function clickPlayer() { const b = await ev(`(() => { const r = document.querySelector('[data-testid=course-player] iframe').getBoundingClientRect(); return { x: r.left + r.width/2, y: r.top + r.height/2 }; })()`); for (const type of ["mousePressed", "mouseReleased"]) await c.send("Input.dispatchMouseEvent", { type, x: b.x, y: b.y, button: "left", clickCount: 1 }); }
async function open() { await c.send("Page.navigate", { url: `${APP}/course/${DAY}` }); await waitFor(`location.pathname === '/course/${DAY}' && ${btnReady}`); await waitFor(`!!document.querySelector('[data-testid=course-player] iframe')`); await sleep(3000); return frame(); }
try {
  let fc = await open();
  note("A_open", { v: await vs(fc), saved: await prog() });
  await clickPlayer(); await sleep(13000);
  note("A_beforeReload", { v: await vs(fc), saved: (await prog())?.position_sec });
  fc.close();
  await ev("window.__m = 1"); await c.send("Page.reload", {}); await waitFor(`!window.__m && ${btnReady}`);
  await sleep(1000);
  note("A_savedAfterReload", (await prog())?.position_sec);
  await sleep(3000); fc = await frame();
  note("A_reopenV", await vs(fc));
  // B: 지금 저장 위치 S 에서 열린 상태 — 재생 12초 더 → SPA 이동
  const S = (await prog())?.position_sec;
  note("B_S", S);
  await clickPlayer(); await sleep(12000);
  note("B_beforeLeave", { v: await vs(fc), saved: (await prog())?.position_sec });
  fc.close();
  await waitFor(`(() => { const a = [...document.querySelectorAll('a')].find(a => a.textContent.trim() === '← 학습 목록'); return !!a && Object.keys(a).some(k => k.startsWith('__reactProps')); })()`);
  await ev(`[...document.querySelectorAll('a')].find(a => a.textContent.trim() === '← 학습 목록').click()`);
  await waitFor(`location.pathname === '/course'`); await sleep(1500);
  note("B_savedAfterLeave", await prog());
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { writeFileSync(`${EV}/VIDEO2-day${DAY}.json`, JSON.stringify(out, null, 1)); c.close(); }
