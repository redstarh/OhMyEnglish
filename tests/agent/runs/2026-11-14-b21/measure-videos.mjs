import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
const browser = await chromium.connectOverCDP("http://127.0.0.1:9470");
const out = [];
for (const w of [390, 320]) {
  const ctx = await browser.newContext({ viewport: { width: w, height: 844 } });
  await ctx.route("**/*", (r) => (["GET", "HEAD", "OPTIONS"].includes(r.request().method()) ? r.fallback() : r.fulfill({ status: 204, body: "" })));
  const page = await ctx.newPage();
  await page.goto("http://localhost:3000/videos", { waitUntil: "networkidle" });
  await page.waitForSelector('[data-testid="videos-check"]');
  out.push(await page.evaluate((w) => {
    const b = document.querySelector('[data-testid="videos-check"]').getBoundingClientRect();
    const main = document.querySelector("main").getBoundingClientRect();
    return { w, bodyScroll: document.body.scrollWidth, buttonRight: Math.round(b.right), mainRight: Math.round(main.right) };
  }, w));
  await ctx.close();
}
console.log(JSON.stringify(out));
await browser.close().catch(() => {});
