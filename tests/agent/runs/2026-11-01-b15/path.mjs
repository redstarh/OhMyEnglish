// 회차 b15 — TASK-314 Continue your path → 오늘의 연습 카드. 사용: node path.mjs <폭> <포트>
// ⛔ dev DB — 이미 진도 행이 있는 Day 1·2 만 엶(열면 같은 위치를 다시 저장함). Start 는 누르지 않음.
import { open, APP, VIS, saver, sleep } from "./lib.mjs";
const width = Number(process.argv[2] ?? 1400), port = Number(process.argv[3] ?? 9365);
const { note, save } = saver(`path-${width}`);
const p = await open({ port, width, height: 1000 });
await p.nav(`${APP}/`, `!!(${VIS("path-day-1")})`); await sleep(1000);
note("nav", await p.ev(`[...document.querySelectorAll('[data-testid^="nav-"]')].filter(e => e.getClientRects().length).map(e => e.dataset.testid)`));
note("rows", await p.ev(`[...document.querySelectorAll('[data-testid^="path-day-"]')].map(e => e.tagName + ':' + e.dataset.testid)`));
await p.click("home-path-all"); await sleep(400);
note("expanded", await p.ev(`({ label: ${VIS("home-path-all")}.innerText.trim(), rows: document.querySelectorAll('[data-testid^="path-day-"]').length })`));
await p.shot(`path-expanded-${width}`);
await p.click("home-path-all"); await sleep(400);
note("collapsed", await p.ev(`document.querySelectorAll('[data-testid^="path-day-"]').length`));
note("progressLinks", await p.ev(`['home-history','home-weekly'].map(t => { const e = [...document.querySelectorAll('[data-testid="' + t + '"]')].find(x => x.getClientRects().length); return t + ' ' + e?.getAttribute('href') + ' ' + Math.round(e?.getBoundingClientRect().height ?? 0); })`));
for (const d of [2, 1]) {
  await p.ev(`window.scrollTo(0, ${VIS(`path-day-${d}`)}.getBoundingClientRect().top + scrollY - 200)`); await sleep(300);
  const before = await p.ev(`Math.round(scrollY)`);
  await p.click(`path-day-${d}`);
  await p.waitFor(`(${VIS("practice-day")})?.dataset.state === 'ready' && (${VIS("practice-day")}).innerText.startsWith('Day ${d} ')`);
  await sleep(800);
  note(`day${d}`, await p.ev(`(() => { const h = ${VIS("home-hero")}.getBoundingClientRect(); return { path: location.pathname, practiceDay: ${VIS("practice-day")}.innerText, unit: ${VIS("course-unit")}.innerText, heroTop: Math.round(h.top), scrollBefore: ${before}, scrollAfter: Math.round(scrollY), selected: [...document.querySelectorAll('[data-selected="true"]')].map(e => e.dataset.testid) }; })()`));
  await p.shot(`path-day${d}-${width}`);
}
await p.click("practice-close"); await sleep(1000);
save(); p.c.close();
