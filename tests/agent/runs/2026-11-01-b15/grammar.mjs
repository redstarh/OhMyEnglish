// 회차 b15 — TASK-314 More practice 「Grammar course」 → 오늘의 연습 카드(현재 Day). 사용: node grammar.mjs <폭> <포트>
// ⛔ dev DB — 현재 Day 를 열기만 함(같은 위치를 다시 저장). Start 는 누르지 않음.
import { open, APP, VIS, saver, sleep } from "./lib.mjs";
const width = Number(process.argv[2] ?? 1400), port = Number(process.argv[3] ?? 9365);
const { note, save } = saver(`grammar-${width}`);
const p = await open({ port, width, height: 1000 });
await p.nav(`${APP}/`, `!!(${VIS("practice-course")})`); await sleep(1000);
note("element", await p.ev(`(() => { const e = ${VIS("practice-course")}; return e.tagName + ' href=' + e.getAttribute('href'); })()`));
await p.ev(`window.scrollTo(0, document.documentElement.scrollHeight)`); await sleep(300);
const before = await p.ev(`Math.round(scrollY)`);
await p.click("practice-course");
await p.waitFor(`(${VIS("practice-day")})?.dataset.state === 'ready'`); await sleep(800);
note("opened", await p.ev(`({ path: location.pathname, practiceDay: ${VIS("practice-day")}.innerText, heroTop: Math.round(${VIS("home-hero")}.getBoundingClientRect().top), scrollBefore: ${before}, scrollAfter: Math.round(scrollY), selected: [...document.querySelectorAll('[data-selected="true"]')].map(e => e.dataset.testid) })`));
await p.shot(`grammar-${width}`);
await p.click("practice-close"); await sleep(1000);
save(); p.c.close();
