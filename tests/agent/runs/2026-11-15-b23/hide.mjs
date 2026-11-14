// TASK-338 확인 — 홈에 More practice · Practice a pattern 이 없고 카드 높이가 그대로인가. 사용: node hide.mjs <포트>
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const b = await chromium.connectOverCDP(`http://127.0.0.1:${process.argv[2] ?? 9490}`);
const p = await b.contexts()[0].newPage();
for (const [w, h] of [[1400, 1000], [390, 844]]) {
  await p.setViewportSize({ width: w, height: h });
  await p.goto("http://localhost:3000/"); await p.waitForSelector('[data-testid="home-hero"]'); await p.waitForTimeout(1200);
  const r = await p.evaluate(() => ({
    morePractice: document.querySelectorAll('[data-testid="home-more-practice"], [data-testid^="practice-"]').length,
    focusPractice: document.querySelectorAll('[data-testid="focus-practice"]').length,
    focusList: !!document.querySelector('[data-testid="home-focus"], section h2'),
    sections: [...document.querySelectorAll("h2")].map((e) => e.innerText.trim()),
    hero: Math.round(document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().height * 10) / 10,
    bodySW: document.body.scrollWidth,
  }));
  console.log(w, JSON.stringify(r));
  await p.screenshot({ path: new URL(`evidence/home-${w}.png`, import.meta.url).pathname, fullPage: true });
}
await p.close(); process.exit(0);
