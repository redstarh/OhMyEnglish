// TASK-323 확인 — 빠른 카드·Grammar course 제거 · /course 리다이렉트 · 버튼 모양. 사용: node verify/t323.mjs <포트>
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const b = await chromium.connectOverCDP(`http://127.0.0.1:${process.argv[2] ?? 9420}`);
const p = await b.contexts()[0].newPage();
const look = (sel) => p.evaluate((sel) => [...document.querySelectorAll(sel)].filter((e) => e.getClientRects().length).map((e) => { const s = getComputedStyle(e); return `${(e.dataset.testid || e.innerText.trim()).slice(0, 22)}:${Math.round(e.getBoundingClientRect().height)}/${s.fontSize}`; }), sel);
for (const [w, h] of [[1400, 1000], [390, 844]]) {
  await p.setViewportSize({ width: w, height: h });
  await p.goto("http://localhost:3000/"); await p.waitForSelector('[data-testid="home-path-all"]'); await p.waitForTimeout(800);
  console.log(w, "quick", await p.locator('[data-testid^="quick-"]').count(), "grammar", await p.locator('[data-testid="practice-course"]').count());
  console.log(w, "buttons", (await look('[data-testid^="practice-"], [data-testid="home-path-all"], [data-testid="focus-practice"]')).join(" "));
  await p.screenshot({ path: new URL(`t323-home-${w}.png`, import.meta.url).pathname, fullPage: true });
}
for (const path of ["/course", "/course/1"]) { await p.goto(`http://localhost:3000${path}`); await p.waitForTimeout(1500); console.log(path, "→", new URL(p.url()).pathname); }
const vids = await (await fetch("http://localhost:8002/api/videos")).json();
await p.setViewportSize({ width: 1400, height: 1000 });
for (const path of ["/videos", `/videos/${vids.videos[0].id}`]) { await p.goto(`http://localhost:3000${path}`); await p.waitForTimeout(2500); console.log(path, (await look("main button, main a.omy-button")).join(" ")); }
await p.close(); process.exit(0);
