// 회차 b15 — TASK-315 「Start speaking」으로 연 현재 Day 와 강조 줄이 같은가. 사용: node start.mjs <폭> <포트>
import { open, APP, VIS, saver, sleep } from "./lib.mjs";
const width = Number(process.argv[2] ?? 1400), port = Number(process.argv[3] ?? 9365);
const { note, save } = saver(`start-${width}`);
const p = await open({ port, width, height: 1000 });
await p.nav(`${APP}/`, `!!(${VIS("start-session")})`); await sleep(1000);
await p.click("start-session");
await p.waitFor(`(${VIS("practice-day")})?.dataset.state === 'ready'`); await sleep(600);
note("opened", await p.ev(`({ practiceDay: ${VIS("practice-day")}.innerText, selected: [...document.querySelectorAll('[data-selected="true"]')].map(e => e.dataset.testid) })`));
await p.click("practice-close"); await sleep(800);
note("closed", await p.ev(`[...document.querySelectorAll('[data-selected="true"]')].map(e => e.dataset.testid)`));
save(); p.c.close();
