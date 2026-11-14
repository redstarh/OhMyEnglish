// storyboard/index.html 을 file:// 로 열어 이미지 로드 성공·실패 수와 첫 화면을 남김
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
const HERE = dirname(fileURLToPath(import.meta.url));
const browser = await chromium.connectOverCDP("http://127.0.0.1:9401");
const page = await browser.contexts()[0].newPage();
await page.setViewportSize({ width: 1400, height: 1000 });
await page.goto(pathToFileURL(join(HERE, "storyboard", "index.html")).href, { waitUntil: "load" });
await page.evaluate(async () => {
  for (const img of document.images) img.loading = "eager";
  await Promise.all([...document.images].map((i) => (i.complete ? null : new Promise((r) => { i.onload = i.onerror = r; }))));
});
const r = await page.evaluate(() => {
  const imgs = [...document.images];
  return { total: imgs.length, ok: imgs.filter((i) => i.naturalWidth > 0).length, broken: imgs.filter((i) => !i.naturalWidth).map((i) => i.getAttribute("src")).slice(0, 10), sections: document.querySelectorAll("section").length, steps: document.querySelectorAll(".step").length, external: [...document.querySelectorAll("link[href],script[src]")].length };
});
await page.screenshot({ path: join(HERE, "evidence", "board-check.jpg"), type: "jpeg", quality: 60 });
console.log(JSON.stringify(r));
await page.close();
process.exit(0);
