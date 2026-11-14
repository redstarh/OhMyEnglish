// 홈 Your progress 의 주간 문구와 그 순간의 /api/weekly-report 응답을 같이 받음 · 주간 화면도 같은 방식
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
const OUT = join(dirname(fileURLToPath(import.meta.url)), "evidence", "probe-weekly.json");
const browser = await chromium.connectOverCDP("http://127.0.0.1:9401");
const page = await browser.contexts()[0].newPage();
await page.setViewportSize({ width: 1400, height: 1000 });
const bodies = [];
page.on("response", async (r) => {
  if (r.url().includes("/api/weekly-report")) bodies.push({ at: new Date().toISOString(), url: r.url(), status: r.status(), body: await r.text().catch(() => null) });
});
const out = { tz: await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone).catch(() => null) };
await page.goto("http://localhost:3000/", { waitUntil: "domcontentloaded" });
await page.waitForSelector('[data-testid="home-weekly-stats"][data-state="ready"]', { timeout: 20000 });
await new Promise((r) => setTimeout(r, 1000));
out.homeText = await page.locator('[data-testid="home-weekly-stats"]').innerText();
out.homeResponses = bodies.splice(0);
await page.goto("http://localhost:3000/history/weekly", { waitUntil: "domcontentloaded" });
await new Promise((r) => setTimeout(r, 3000));
out.weeklyHead = (await page.locator("main").first().innerText().catch(() => page.locator("body").innerText())).slice(0, 200);
out.weeklyResponses = bodies.splice(0);
out.tz = await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone);
writeFileSync(OUT, JSON.stringify(out, null, 1));
console.log(JSON.stringify(out).slice(0, 1500));
await page.close();
process.exit(0);
