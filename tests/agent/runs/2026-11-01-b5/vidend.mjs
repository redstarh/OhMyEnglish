// 회차 b5 — 영상 끝 경로: 저장 위치를 영상 끝 몇 초 앞에 두고 목록에서 열어 끝까지 재생 → 완료 뒤 12초 관측 → 떠남.
// 판정: 완료 횟수 +1 · 영상이 다시 재생되지 않음 · 진도 0초·첫 단원·첫 문장 유지 · 진행 중 Day 로 뽑히지 않음.
import { writeFileSync } from "node:fs";
import { connect, pageTarget, sleep, EV, PORT } from "./cdp.mjs";
const DAY = process.argv[2] ?? "6", LEAD = Number(process.argv[3] ?? "8");
const API = "http://localhost:8002";
const c = await connect((await pageTarget()).webSocketDebuggerUrl);
await c.send("Page.enable"); await c.send("Runtime.enable");
const out = {}; const note = (k, v) => { out[k] = v; console.log(k, JSON.stringify(v)); };
const ev = async (e) => { const r = await c.send("Runtime.evaluate", { expression: e, returnByValue: true, awaitPromise: true, userGesture: true }); if (r.exceptionDetails) throw new Error(r.exceptionDetails.text); return r.result.value; };
const waitFor = async (e, t = 15000) => { const s = Date.now(); while (Date.now() - s < t) { try { if (await ev(e)) return; } catch {} await sleep(30); } throw new Error("timeout " + e); };
const prog = async () => (await (await fetch(`${API}/api/course/days/${DAY}`)).json()).progress;
const ov = async () => { const j = await (await fetch(`${API}/api/course`)).json(); return { cycle: j.cycle, current_day: j.current_day }; };
async function vs() { for (let k = 0; k < 3; k++) { try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json(); const f = l.filter((t) => t.type === "iframe" && t.url.includes("youtube.com/embed")).at(-1); if (!f) { await sleep(300); continue; }
  const fc = await connect(f.webSocketDebuggerUrl); const r = await Promise.race([fc.send("Runtime.evaluate", { returnByValue: true, expression: `(() => { const v = document.querySelector('video'); const mp = document.querySelector('#movie_player'); return { t: v ? Math.round(v.currentTime*100)/100 : null, paused: v?.paused, ended: v?.ended, state: mp?.getPlayerState?.(), dur: mp?.getDuration?.() }; })()` }), sleep(3000).then(() => null)]); fc.close(); if (r) return r.result.value; } catch {} await sleep(300); } return null; }
const ready = (sel) => `(() => { const a = ${sel}; return !!a && Object.keys(a).some(k => k.startsWith('__reactProps')); })()`;
const back = `[...document.querySelectorAll('a')].find(a => a.textContent.trim() === '← 학습 목록')`;
try {
  if (process.argv[4]) {
    const S = Number(process.argv[4]);
    const r = await fetch(`${API}/api/course/days/${DAY}/progress`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ position_sec: S, unit: Number(process.argv[5]), sentence_index: 0, completed: false, completed_count: Number(process.argv[6] ?? "0") }) });
    note("setup", { S, status: r.status });
  }
  note("progressBefore", await prog()); note("overviewBefore", await ov());
  await c.send("Page.navigate", { url: "http://localhost:3000/course" });
  await waitFor(ready(`document.querySelector('[data-testid=course-day-${DAY}] a')`));
  await ev(`document.querySelector('[data-testid=course-day-${DAY}] a').click()`);
  await waitFor(`location.pathname === '/course/${DAY}' && !!document.querySelector('[data-testid=course-player] iframe')`);
  await sleep(3000);
  let v = await vs(); note("vOpen", v);
  if (process.argv[2] && !process.argv[4]) { note("durationOnly", v?.dur); }
  else {
    if (v && v.paused && !v.ended) { const b = await ev(`(() => { const r = document.querySelector('[data-testid=course-player] iframe').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`); for (const type of ["mousePressed", "mouseReleased"]) await c.send("Input.dispatchMouseEvent", { type, x: b.x, y: b.y, button: "left", clickCount: 1 }); }
    const samples = [];
    for (let i = 0; i < 16; i++) { await sleep(2000); samples.push({ wall: new Date().toISOString(), v: await vs(), p: await prog(), notice: await ev(`document.querySelector('[data-testid=course-notice]')?.textContent ?? null`), num: await ev(`document.querySelector('[data-testid=course-sentence-number]')?.textContent + ' ' + document.querySelector('[data-testid=course-unit]')?.textContent.slice(0,9)`) }); }
    note("samples", samples.map((s) => ({ wall: s.wall.slice(11, 19), t: s.v?.t, paused: s.v?.paused, ended: s.v?.ended, st: s.v?.state, pos: s.p?.position_sec, unit: s.p?.unit, cc: s.p?.completed_count, upd: s.p?.updated_at?.slice(11, 19), notice: s.notice, at: s.num })));
    await ev(`${back}.click()`); await waitFor(`location.pathname === '/course'`); await sleep(1500);
    note("progressAfterLeave", await prog()); note("overviewAfterLeave", await ov());
    note("row", await ev(`(() => { const d = document.querySelector('[data-testid=course-day-${DAY}]'); return { status: d.querySelectorAll('span')[1].textContent, link: d.querySelector('a').textContent }; })()`));
  }
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { writeFileSync(`${EV}/VIDEND-day${DAY}${process.env.TAG ? "-" + process.env.TAG : ""}.json`, JSON.stringify(out, null, 1)); c.close(); }
