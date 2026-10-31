// 회차 b7 — 재생 전에 머문 뒤 앱 안 링크로 떠날 때 저장 위치가 바뀌지 않는지 본다. 사용: node stay.mjs <day> <label> [stayMs]
import { open, APP, api, saver, sleep } from "./lib.mjs";
const [DAY, LABEL] = [process.argv[2], process.argv[3]]; const STAY = Number(process.argv[4] ?? 12000);
const { note, save } = saver(`STAY-${LABEL}`);
const p = await open();
try {
  note("savedBeforeOpen", (await api(`/api/course/days/${DAY}`)).progress);
  await p.nav(`${APP}/course`, `(() => { const a = document.querySelector('[data-testid=course-day-${DAY}] a'); return !!a && Object.keys(a).some(k => k.startsWith('__reactProps')); })()`);
  await p.ev(`document.querySelector('[data-testid=course-day-${DAY}] a').click()`);
  await p.waitFor(`location.pathname === '/course/${DAY}' && !!document.querySelector('[data-testid=course-player] iframe')`);
  if (process.argv[5] === "play") {
    await sleep(3000);
    const b = await p.ev(`(() => { const r = document.querySelector('[data-testid=course-player] iframe').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
    for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: b.x, y: b.y, button: "left", clickCount: 1 });
    note("playClickedAt", new Date().toISOString());
  }
  const t0 = Date.now(); const mid = [];
  for (const at of [6000, STAY]) { await sleep(Math.max(0, at - (Date.now() - t0))); mid.push({ atMs: Date.now() - t0, saved: (await api(`/api/course/days/${DAY}`)).progress?.position_sec }); }
  note("savedDuringStay", mid);
  const links = await p.ev(`[...document.querySelectorAll('a')].map(a => [a.textContent.trim(), a.getAttribute('href')])`);
  note("links", links);
  note("playerTimeBeforeLeave", await p.ev(`(() => { try { const f = document.querySelector('[data-testid=course-player] iframe'); return YT.get(f.id).getCurrentTime(); } catch (e) { return String(e); } })()`));
  await p.ev(`[...document.querySelectorAll('a')].find(a => a.getAttribute('href') === '/course').click()`);
  await p.waitFor(`location.pathname === '/course'`);
  await sleep(1500);
  note("savedAfterLeave", (await api(`/api/course/days/${DAY}`)).progress);
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { save(); p.c.close(); }
