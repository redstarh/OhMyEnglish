// 회차 b5 — D3: 목록에서 저장 위치가 있는 Day 를 열어(SPA) 더 재생하고 떠난다. 사용: node video3.mjs <day> <link|back> [playSec]
// 판정: 떠난 뒤 저장값이 0 이 아니고, 연 위치 S 보다 크고, 떠나기 직전 영상 시각 - 5.5초 이상인가.
import { writeFileSync } from "node:fs";
import { connect, pageTarget, sleep, EV, PORT } from "./cdp.mjs";
const APP = "http://localhost:3000", API = "http://localhost:8002";
const DAY = process.argv[2] ?? "3", HOW = process.argv[3] ?? "link", PLAY = Number(process.argv[4] ?? "12");
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
await c.send("Page.enable"); await c.send("Runtime.enable");
const out = { day: DAY, how: HOW }; const note = (k, v) => { out[k] = v; console.log(k, JSON.stringify(v)); };
const ev = async (expression) => { const r = await c.send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text); return r.result.value; };
const waitFor = async (e, t = 15000, s = 50) => { const st = Date.now(); while (Date.now() - st < t) { try { if (await ev(e)) return Date.now() - st; } catch {} await sleep(s); } throw new Error("timeout " + e); };
const prog = async () => (await (await fetch(`${API}/api/course/days/${DAY}`)).json()).progress;
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

const linkReady = (sel) => `(() => { const a = ${sel}; return !!a && Object.keys(a).some(k => k.startsWith('__reactProps')); })()`;
try {
  await c.send("Page.navigate", { url: `${APP}/course` });
  await waitFor(linkReady(`document.querySelector('[data-testid=course-day-${DAY}] a')`));
  const S = (await prog())?.position_sec ?? 0;
  note("S_savedBeforeOpen", S);
  await ev(`document.querySelector('[data-testid=course-day-${DAY}] a').click()`);
  await waitFor(`location.pathname === '/course/${DAY}' && !!document.querySelector('[data-testid=course-player] iframe')`);
  await sleep(3500);
  const v0 = await vstate();
  note("v_afterOpen", v0);
  if (!v0 || v0.paused) await clickPlayer();
  await sleep(1500);
  note("v_playing", await vstate());
  await sleep(PLAY * 1000);
  const before = await vstate();
  const savedBefore = (await prog())?.position_sec;
  const leaveWall = new Date().toISOString();
  note("beforeLeave", { v: before, savedBefore, wall: leaveWall });
  if (HOW === "back") {
    await ev("history.back()");
  } else {
    await waitFor(linkReady(`[...document.querySelectorAll('a')].find(a => a.textContent.trim() === '← 학습 목록')`));
    await ev(`[...document.querySelectorAll('a')].find(a => a.textContent.trim() === '← 학습 목록').click()`);
  }
  await waitFor(`location.pathname === '/course' && !!document.querySelector('[data-testid=course-day-1]')`);
  await sleep(1500);
  const after = await prog();
  note("savedAfterLeave", after);
  const t = before?.t ?? null;
  note("judge", { S, tBeforeLeave: t, saved: after?.position_sec, lagSec: t == null ? null : Math.round((t - after.position_sec) * 100) / 100,
    notZero: after?.position_sec > 0, beyondOpen: after?.position_sec > S, within55: t != null && after.position_sec >= t - 5.5 && after.position_sec <= t + 0.5 });
  note("listRow", await ev(`(() => { const d = document.querySelector('[data-testid=course-day-${DAY}]'); return { status: d.querySelectorAll('span')[1].textContent, link: d.querySelector('a').textContent }; })()`));
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { writeFileSync(`${EV}/VIDEO3-day${DAY}-${HOW}${process.env.TAG ? "-" + process.env.TAG : ""}.json`, JSON.stringify(out, null, 1)); c.close(); }
