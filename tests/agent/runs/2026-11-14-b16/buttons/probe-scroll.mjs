// H1 반증 — Start speaking 뒤 scrollY 가 0 이 된 것이 앱의 스크롤인가, 드라이버의 클릭 전 스크롤인가,
// 문서 높이가 줄어 생긴 클램프인가. 폭별로 DOM 직접 클릭(el.click())과 Playwright 클릭을 대조함.
import { APP, connect, newPage, save } from "./lib.mjs";

const { ctx } = await connect();
const out = [];
for (const W of [1400, 390]) {
  for (const how of ["dom", "playwright"]) {
    for (const y of [40, 150]) {
      const page = await newPage(ctx, W);
      try {
        await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
        await page.waitForSelector('[data-testid="home-hero"][data-state="ready"]', { timeout: 15000 });
        await page.waitForTimeout(800);
        await page.evaluate((yy) => {
          window.scrollTo(0, yy);
          window.__scrolls = [];
          window.addEventListener("scroll", () => window.__scrolls.push([Math.round(performance.now()), window.scrollY]));
        }, y);
        await page.waitForTimeout(300);
        const before = await page.evaluate(() => ({
          y: window.scrollY,
          docH: document.documentElement.scrollHeight,
          vh: window.innerHeight,
          btnTop: Math.round(document.querySelector('[data-testid="start-session"]').getBoundingClientRect().top),
        }));
        if (how === "dom") await page.evaluate(() => document.querySelector('[data-testid="start-session"]').click());
        else await page.click('[data-testid="start-session"]');
        await page.waitForSelector('[data-testid="course-start"]', { timeout: 10000 });
        await page.waitForTimeout(1200);
        const after = await page.evaluate(() => ({
          y: window.scrollY,
          docH: document.documentElement.scrollHeight,
          heroTop: Math.round(document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().top),
          scrolls: window.__scrolls.slice(0, 10),
          maxY: document.documentElement.scrollHeight - window.innerHeight,
        }));
        out.push({ W, how, y, before, after });
        console.log(W, how, y, JSON.stringify(before), JSON.stringify(after));
      } catch (e) {
        out.push({ W, how, y, error: e.message.split("\n")[0] });
      } finally {
        await page.close();
      }
    }
  }
}
save("probe-scroll.json", out);
process.exit(0);
