// 목록 /course 의 히트맵·이력 표를 DOM 에서 읽고 API 와 함께 남긴다. 사용: node overview.mjs <label>
import { open, APP, api, saver } from "./lib.mjs";
const { note, save } = saver(`OVERVIEW-${process.argv[2]}`);
const p = await open();
try {
  await p.nav(`${APP}/course`, `!!document.querySelector('[data-testid=course-day-6]') && !!document.querySelector('[data-testid=course-heatmap]')`);
  note("kstToday", await p.ev(`new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Seoul' }).format(new Date())`));
  note("heatNonZero", await p.ev(`[...document.querySelectorAll('[data-testid=course-heatmap] [data-attempts]')].filter(i => i.dataset.attempts !== '0').map(i => ({ title: i.title, attempts: i.dataset.attempts, bg: i.style.background }))`));
  note("heatLast", await p.ev(`[...document.querySelectorAll('[data-testid=course-heatmap] [data-attempts]')].slice(-2).map(i => i.title)`));
  note("heatCount", await p.ev(`document.querySelectorAll('[data-testid=course-heatmap] [data-attempts]').length`));
  note("recentRows", await p.ev(`[...document.querySelectorAll('[data-testid=course-recent] tbody tr')].map(tr => [...tr.cells].map(td => td.textContent))`));
  note("day1Row", await p.ev(`document.querySelector('[data-testid=course-day-1]')?.textContent`));
  const o = await api("/api/course");
  note("apiRecent", o.recent);
  note("apiHeatNonZero", o.heatmap.filter((h) => h.attempts > 0));
  note("apiHeatLast", o.heatmap.slice(-1));
  await p.shot(`OVERVIEW-${process.argv[2]}`);
} catch (e) { note("ERROR", String(e?.stack ?? e)); }
finally { save(); p.c.close(); }
