// TASK-324 — 단원 이름이 길 때 Auto/Manual 전환이 잘리는가. 사용: node toggle.mjs <포트>
// ⛔ dev DB — 연습을 열기만 함(같은 위치를 다시 씀). 진도 저장 요청은 막음.
import { readFileSync } from "node:fs";
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const content = JSON.parse(readFileSync("/Users/redstar/MyProject/OhMyEnglish/app/backend/app/content/grammar_basic.json", "utf8"));
const topics = content.days.flatMap((d) => d.units.map((u) => `Unit ${u.unit} · ${u.topic}`));
const b = await chromium.connectOverCDP(`http://127.0.0.1:${process.argv[2] ?? 9430}`);
const p = await b.contexts()[0].newPage();
await p.route("**/api/course/days/*/progress", (r) => r.fulfill({ status: 204, body: "" }));
for (const [w, h] of [[320, 800], [390, 844], [1400, 1000]]) {
  await p.setViewportSize({ width: w, height: h });
  await p.goto("http://localhost:3000/"); await p.waitForSelector('[data-testid="start-session"]'); await p.waitForTimeout(600);
  await p.click('[data-testid="start-session"]'); await p.waitForSelector('[data-testid="course-mode-auto"]'); await p.waitForTimeout(600);
  const r = await p.evaluate((topics) => {
    const unit = document.querySelector('[data-testid="course-unit"]'); const auto = document.querySelector('[data-testid="course-mode-auto"]');
    const group = auto.parentElement; const orig = unit.textContent; let worst = null;
    for (const t of topics) { unit.textContent = t; const g = group.getBoundingClientRect(); const clipped = group.scrollWidth - group.clientWidth; const autoW = Math.round(auto.getBoundingClientRect().width);
      if (!worst || clipped > worst.clipped || autoW < worst.autoW) worst = { t, clipped, autoW, groupW: Math.round(g.width) }; }
    unit.textContent = orig; return worst; }, topics);
  console.log(w, JSON.stringify(r));
  await p.click('[data-testid="practice-close"]'); await p.waitForTimeout(400);
}
await p.close(); process.exit(0);
