// TASK-289 — Day 를 열고 영상이 스스로 재생되지 않는지, ▶ 을 누르면 그 위치부터 재생되는지 본다.
// 사용: node video.mjs <day> <label> [noplay]   판정은 iframe 안 <video> 의 currentTime·paused 와 플레이어 상태값.
import { open, APP, api, saver, sleep, PORT } from "./lib.mjs";
import { connect } from "./cdp.mjs";
const [DAY, LABEL, NOPLAY] = [process.argv[2], process.argv[3], process.argv[4] === "noplay"];
const { note, save } = saver(`VIDEO-${LABEL}`);
const p = await open();
async function vstate() {
  for (let k = 0; k < 3; k++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const f = list.filter((t) => t.type === "iframe" && t.url.includes("youtube.com/embed")).at(-1);
      if (!f) { await sleep(500); continue; }
      const fc = await connect(f.webSocketDebuggerUrl);
      const r = await Promise.race([fc.send("Runtime.evaluate", { returnByValue: true, expression: `(() => { const v = document.querySelector('video'); const mp = document.querySelector('#movie_player');
        return { t: v ? Math.round(v.currentTime * 100) / 100 : null, paused: v?.paused ?? null, state: mp?.getPlayerState?.() ?? null, ad: mp ? mp.classList.contains('ad-showing') : null }; })()` }), sleep(3000).then(() => null)]);
      fc.close();
      if (r) return r.result.value;
    } catch {}
    await sleep(300);
  }
  return null;
}
async function clickPlayer() {
  const b = await p.ev(`(() => { const r = document.querySelector('[data-testid=course-player] iframe').getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
  for (const type of ["mousePressed", "mouseReleased"]) await p.c.send("Input.dispatchMouseEvent", { type, x: b.x, y: b.y, button: "left", clickCount: 1 });
}
try {
  const prog = (await api(`/api/course/days/${DAY}`)).progress;
  note("savedBeforeOpen", prog);
  // 학습자 경로: 목록에서 Day 를 누른다(SPA 이동)
  await p.nav(`${APP}/course`, `(() => { const a = document.querySelector('[data-testid=course-day-${DAY}] a'); return !!a && Object.keys(a).some(k => k.startsWith('__reactProps')); })()`);
  await p.ev(`document.querySelector('[data-testid=course-day-${DAY}] a').click()`);
  await p.waitFor(`location.pathname === '/course/${DAY}' && !!document.querySelector('[data-testid=course-player] iframe')`);
  const t0 = Date.now(); const samples = [];
  for (const at of [2000, 4000, 7000, 11000, 15000]) { await sleep(Math.max(0, at - (Date.now() - t0))); samples.push({ atMs: Date.now() - t0, ...(await vstate()) }); }
  note("samplesAfterOpen", samples);
  note("pageAfterOpen", await p.state());
  await p.shot(`VIDEO-${LABEL}-open`);
  if (!NOPLAY) {
    await clickPlayer();
    const s2 = [];
    for (const at of [1500, 4000, 7000]) { const st = Date.now(); await sleep(at - (s2.at(-1)?.rel ?? 0)); s2.push({ rel: at, ...(await vstate()) }); }
    note("samplesAfterPlayClick", s2);
    await p.shot(`VIDEO-${LABEL}-played`);
    await clickPlayer(); // 다시 눌러 멈춤
    await sleep(800);
    note("afterPauseClick", await vstate());
  }
  await sleep(5500);
  note("savedAfter", (await api(`/api/course/days/${DAY}`)).progress);
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { save(); p.c.close(); }
