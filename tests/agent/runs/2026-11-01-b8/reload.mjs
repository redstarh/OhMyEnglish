import { open, APP, saver, sleep } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/runs/2026-11-01-b8/lib.mjs";
const { note, save } = saver("AUTO-r1-reload");
const p = await open();
try {
  await p.ev("localStorage.setItem('omy.course.mode','manual')");
  await p.nav(`${APP}/course/1`, p.READY);
  await sleep(500);
  note("day1Api", await (await fetch("http://localhost:8002/api/course/days/1")).json().then(d => ({ progress: d.progress, s: d.units[0].sentences.map(x => [x.key, x.attempts]) })));
  note("landed", await p.state());
  const shown = {};
  for (let g = 0; g < 6; g++) { const s = await p.state(); shown[s.num] = s.attempts; if (s.num === "문장 1 / 5") break; await p.click("← 이전"); await sleep(300); }
  note("shownAfterReload", shown);
  note("phaseAfter", (await p.state()).phase);
} catch (e) { note("ERROR", String(e)); } finally { save(); p.c.close(); }
