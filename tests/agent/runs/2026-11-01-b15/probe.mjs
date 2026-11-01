// 회차 b15 — 문장 칸 안쪽 너비와 번호 줄 넘침(codex 리뷰 ①②). 사용: node probe.mjs <폭> <포트>
import { open, APP, VIS, sleep } from "./lib.mjs";
const width = Number(process.argv[2]), port = Number(process.argv[3] ?? 9365);
const p = await open({ port, width, height: 1000 });
await p.nav(`${APP}/`, `!!(${VIS("start-session")})`); await sleep(800);
await p.click("start-session"); await p.waitFor(`!!(${VIS("course-card")})`); await sleep(800);
console.log(width, JSON.stringify(await p.ev(`(() => { const c = ${VIS("course-card")}; const s = getComputedStyle(c); const inner = c.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
  const num = ${VIS("course-sentence-number")}; const row = num.parentElement.parentElement; const sp = document.createElement('span'); sp.textContent = ' · ② Say it · 10.0s'; num.after(sp);
  const tr = ${VIS("course-attempts")}; const o = tr.textContent; tr.textContent = 'Try 10';
  const r = { inner: Math.round(inner), rowScroll: row.scrollWidth, rowClient: row.clientWidth, rowH: row.getBoundingClientRect().height, sentenceFont: getComputedStyle(${VIS("course-sentence")}).fontSize };
  sp.remove(); tr.textContent = o; return r; })()`)));
p.c.close();
