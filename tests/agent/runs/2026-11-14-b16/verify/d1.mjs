// 회차 b16 호출자 대조 — 버튼 탭 D1(1400×900 Start speaking 이 scrollY 를 0 으로 옮김) 재현. 사용: node verify/d1.mjs <포트>
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const b = await chromium.connectOverCDP(`http://127.0.0.1:${process.argv[2] ?? 9402}`);
const p = await b.contexts()[0].newPage();
for (const [w, h, y] of [[1400, 900, 40], [1400, 700, 200], [390, 844, 120]]) {
  await p.setViewportSize({ width: w, height: h });
  await p.goto("http://localhost:3000/"); await p.waitForSelector('[data-testid="start-session"]'); await p.waitForTimeout(800);
  await p.evaluate((y) => window.scrollTo(0, y), y); await p.waitForTimeout(300);
  const before = await p.evaluate(() => Math.round(scrollY));
  const docH = await p.evaluate(() => document.documentElement.scrollHeight);
  await p.click('[data-testid="start-session"]');
  const heights = await p.evaluate(() => new Promise((res) => { const out = []; let n = 0; const tick = () => { out.push(Math.round(document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().height)); if (++n < 30) requestAnimationFrame(tick); else res(out); }; tick(); }));
  await p.waitForTimeout(800);
  const after = await p.evaluate(() => Math.round(scrollY));
  console.log(`${w}x${h} docH=${docH} scrollY ${before}→${after} heroMin=${Math.min(...heights)} heroMax=${Math.max(...heights)}`);
  await p.click('[data-testid="practice-close"]'); await p.waitForTimeout(600);
}
await p.close(); process.exit(0);
