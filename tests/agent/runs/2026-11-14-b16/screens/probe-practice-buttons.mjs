// 홈 문장 연습의 버튼 목록 — Listen/Slow(course-listen · course-slow) 가 없는지 개수로 잼. 양성 대조로 course-next 를 같이 셈
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "evidence", "probe-practice-buttons.json");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9401");
const out = {};
for (const w of [1400, 390]) {
  const page = await browser.contexts()[0].newPage();
  await page.setViewportSize({ width: w, height: w === 390 ? 844 : 1000 });
  await page.goto("http://localhost:3000/", { waitUntil: "domcontentloaded" });
  await page.locator('[data-testid="start-session"]').click();
  await page.waitForSelector('[data-testid="practice-close"]', { timeout: 20000 });
  await new Promise((r) => setTimeout(r, 1500));
  out[w] = await page.evaluate(() => {
    const c = (id) => document.querySelectorAll(`[data-testid="${id}"]`).length;
    const panel = document.querySelector('[data-testid="home-hero"]');
    return {
      listen: c("course-listen"),
      slow: c("course-slow"),
      next: c("course-next"),
      prev: c("course-prev"),
      buttons: [...panel.querySelectorAll("button")].map((b) => b.textContent.trim()),
    };
  });
  await page.locator('[data-testid="practice-close"]').click();
  await page.close();
}
writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log(JSON.stringify(out));
process.exit(0);
