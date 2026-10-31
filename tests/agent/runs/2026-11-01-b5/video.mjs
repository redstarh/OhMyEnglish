// 회차 b3 — 영상: 재생 → 5초 저장 → 목록으로 떠남 → 다시 열기 → 그 위치부터인지. 연습 시작 시 영상 멈춤 · 영상 재생 시 연습 멈춤.
import { writeFileSync } from "node:fs";
import { connect, pageTarget, sleep, EV, PORT } from "./cdp.mjs";
const APP = "http://localhost:3000", API = "http://localhost:8002";
const DAY = process.argv[2] ?? "3";
const page = await pageTarget();
const c = await connect(page.webSocketDebuggerUrl);
await c.send("Page.enable"); await c.send("Runtime.enable");
const out = {}; const note = (k, v) => { out[k] = v; console.log(k, JSON.stringify(v)); };
const ev = async (expression) => { const r = await c.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text); return r.result.value; };
const waitFor = async (e, t = 15000, s = 50) => { const st = Date.now(); while (Date.now() - st < t) { try { if (await ev(e)) return Date.now() - st; } catch {} await sleep(s); } throw new Error("timeout " + e); };
const api = async (p) => (await fetch(API + p)).json();
const prog = async () => (await api(`/api/course/days/${DAY}`)).progress;
// b5: iframe 대상이 교체되면 옛 연결이 응답하지 않는다(1차 실측) — 매 읽기마다 지금의 iframe 에 새로 붙고 3초 제한을 둔다.
async function frame() { return { close() {} }; }
async function vstate() {
  for (let k = 0; k < 3; k++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const f = list.filter((t) => t.type === "iframe" && t.url.includes("youtube.com/embed")).at(-1);
      if (!f) { await sleep(500); continue; }
      const fc = await connect(f.webSocketDebuggerUrl);
      const r = await Promise.race([fc.send("Runtime.evaluate", { returnByValue: true, expression: `(() => { const v = document.querySelector('video'); const mp = document.querySelector('#movie_player');
        return { t: v ? Math.round(v.currentTime * 100) / 100 : null, paused: v?.paused, ad: mp ? mp.classList.contains('ad-showing') : null, state: mp?.getPlayerState?.() }; })()` }), sleep(3000).then(() => null)]);
      fc.close();
      if (r) return { frame: f.id.slice(0, 8), ...r.result.value };
    } catch {}
    await sleep(300);
  }
  return null;
}
async function clickPlayer() {
  const b = await ev(`(() => { const r = document.querySelector('[data-testid=course-player] iframe').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  for (const type of ["mousePressed", "mouseReleased"]) await c.send("Input.dispatchMouseEvent", { type, x: b.x, y: b.y, button: "left", clickCount: 1 });
}
const phase = () => ev(`document.querySelector('[data-testid=course-phase]')?.dataset.phase ?? 'idle'`);
const btnReady = (t) => `(() => { const b = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === ${JSON.stringify(t)}); return !!b && Object.keys(b).some(k => k.startsWith('__reactProps')); })()`;
try {
  await c.send("Page.navigate", { url: `${APP}/course/${DAY}` });
  await waitFor(`location.pathname === '/course/${DAY}' && ${btnReady("시작")}`);
  await waitFor(`!!document.querySelector('[data-testid=course-player] iframe')`);
  await sleep(2500);
  note("progressAtOpen", await prog());
  let fc = await frame();
  note("frameFound", !!fc);
  note("v0", await vstate(fc));
  await clickPlayer();
  const samples = [];
  for (let i = 0; i < 12; i++) { await sleep(2000); samples.push({ wall: new Date().toISOString(), v: await vstate(fc), saved: (await prog())?.position_sec ?? null, phase: await phase() }); }
  note("playSamples", samples);
  // 연습 시작 → 영상이 멈추는가
  await ev(`[...document.querySelectorAll('button')].find(b => b.textContent.trim() === '시작').click()`);
  await sleep(1500);
  note("afterPracticeStart", { v: await vstate(fc), phase: await phase() });
  // 연습 중 영상 재생 → 연습이 멈추는가
  await clickPlayer();
  await sleep(2500);
  note("afterVideoReplay", { v: await vstate(fc), phase: await phase() });
  await sleep(4000);
  const before = await vstate(fc);
  note("beforeLeave", { v: before, saved: (await prog())?.position_sec, wall: new Date().toISOString() });
  await waitFor(`(() => { const a = [...document.querySelectorAll('a')].find(a => a.textContent.trim() === '← 학습 목록'); return !!a && Object.keys(a).some(k => k.startsWith('__reactProps')); })()`);
  await ev(`[...document.querySelectorAll('a')].find(a => a.textContent.trim() === '← 학습 목록').click()`);
  await waitFor(`location.pathname === '/course' && !!document.querySelector('[data-testid=course-day-1]')`);
  await sleep(1500);
  note("savedAfterLeave", await prog());
  note("listRow", await ev(`(() => { const d = document.querySelector('[data-testid=course-day-${DAY}]'); return { status: d.querySelectorAll('span')[1].textContent, bar: [...d.querySelectorAll('div')].map(x => x.style.width).filter(Boolean), link: d.querySelector('a').textContent }; })()`));
  fc.close();
  // 다시 열기
  await ev(`document.querySelector('[data-testid=course-day-${DAY}] a').click()`);
  await waitFor(`location.pathname === '/course/${DAY}' && ${btnReady("시작")}`);
  await sleep(4000);
  fc = await frame();
  const re = [];
  for (let i = 0; i < 3; i++) { re.push({ wall: new Date().toISOString(), v: await vstate(fc) }); await sleep(1500); }
  note("reopen", re);
  // 다시 연 뒤 재생하면 저장 위치부터인가
  await clickPlayer();
  await sleep(3000);
  note("reopenAfterPlay", await vstate(fc));
  // 멈춰 두기
  await clickPlayer();
  await sleep(1500);
  note("paused", await vstate(fc));
  fc.close();
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { writeFileSync(`${EV}/VIDEO-day${DAY}${process.env.TAG ? "-" + process.env.TAG : ""}.json`, JSON.stringify(out, null, 1)); c.close(); }
