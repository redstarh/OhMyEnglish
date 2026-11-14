// TASK-340 · TASK-341 확인 — 문장 연습 아래 버튼 셋이 칸 안에 드는가 · ?extras=1 스위치. 사용: node nav.mjs <포트> <라벨>
// ⛔ dev DB — 진도 저장 요청은 막음. Start 는 누르지 않음(Try again 상태는 글자만 바꿔 잼).
import { writeFileSync } from "node:fs";
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const label = process.argv[3] ?? "run";
const b = await chromium.connectOverCDP(`http://127.0.0.1:${process.argv[2] ?? 9495}`);
const p = await b.contexts()[0].newPage();
await p.route("**/api/course/days/*/progress", (r) => r.fulfill({ status: 204, body: "" }));
const out = {};
for (const [w, h] of [[320, 800], [390, 844], [1400, 1000]]) {
  await p.setViewportSize({ width: w, height: h });
  await p.goto("http://localhost:3000/"); await p.waitForSelector('[data-testid="start-session"]'); await p.waitForTimeout(700);
  await p.click('[data-testid="start-session"]'); await p.waitForSelector('[data-testid="course-next"], [data-testid="course-finish"]'); await p.waitForTimeout(600);
  out[w] = await p.evaluate(() => {
    const card = document.querySelector('[data-testid="course-card"]'); const cs = getComputedStyle(card);
    const innerRight = card.getBoundingClientRect().right - parseFloat(cs.paddingRight) - parseFloat(cs.borderRightWidth);
    const measure = () => ["course-prev", "course-start", "course-retry", "course-next", "course-finish"].map((t) => document.querySelector(`[data-testid="${t}"]`)).filter(Boolean).map((e) => ({ t: e.dataset.testid, right: Math.round(e.getBoundingClientRect().right), w: Math.round(e.getBoundingClientRect().width), h: Math.round(e.getBoundingClientRect().height) }));
    const cardH = () => Math.round(card.getBoundingClientRect().height * 10) / 10;
    const start = measure(); const startH = cardH();
    const mid = document.querySelector('[data-testid="course-start"]'); const orig = mid.textContent; mid.textContent = "Try again";
    const retry = measure(); const retryH = cardH(); mid.textContent = orig;
    return { innerRight: Math.round(innerRight), start, retry, startH, retryH, clipped: [...start, ...retry].some((x) => x.right > innerRight + 0.5) };
  });
  console.log(w, JSON.stringify(out[w]));
  await p.screenshot({ path: new URL(`evidence/${label}-practice-${w}.png`, import.meta.url).pathname });
}
for (const q of ["", "?extras=1"]) {
  await p.setViewportSize({ width: 1400, height: 1000 });
  await p.goto(`http://localhost:3000/${q}`); await p.waitForSelector('[data-testid="home-hero"]'); await p.waitForTimeout(1200);
  out[`extras${q}`] = await p.evaluate(() => ({ more: document.querySelectorAll('[data-testid^="practice-"]').length, focus: document.querySelectorAll('[data-testid="focus-practice"]').length }));
  console.log("home" + (q || " (no query)"), JSON.stringify(out[`extras${q}`]));
}
writeFileSync(new URL(`evidence/${label}.json`, import.meta.url), JSON.stringify(out, null, 1));
await p.close(); process.exit(0);
