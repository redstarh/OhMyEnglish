// 양성 대조 — home.mjs H1 의 프레임 기록기가 scrollY 변화를 잡는지 봄. 390 에서 아래쪽 Day 2 줄을 누르면
// 카드로 스크롤하므로(TASK-308) 같은 기록기에 scrollY 값이 여럿 찍혀야 함.
import { connect, newPage, home, routeCourse, save } from "./lib.mjs";

const { ctx } = await connect();
const page = await newPage(ctx, 390);
await routeCourse(page);
try {
  await home(page);
  await page.locator('[data-testid="path-day-2"]').evaluate((e) => e.scrollIntoView({ block: "center" }));
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    window.__frames = [];
    const t0 = performance.now();
    const tick = () => {
      const hero = document.querySelector('[data-testid="home-hero"]');
      window.__frames.push([Math.round(performance.now() - t0), window.scrollY, Math.round(hero.getBoundingClientRect().height * 10) / 10]);
      if (performance.now() - t0 < 1500) requestAnimationFrame(tick);
    };
    document.querySelector('[data-testid="path-day-2"]').addEventListener("click", () => requestAnimationFrame(tick), { once: true, capture: true });
  });
  await page.locator('[data-testid="path-day-2"]').click();
  await page.waitForTimeout(1800);
  const frames = await page.evaluate(() => window.__frames);
  const ys = [...new Set(frames.map((f) => f[1]))];
  save("probe-frames.json", { frames });
  console.log(`frames=${frames.length} 서로 다른 scrollY 값 ${ys.length}개 · 처음 ${ys[0]} · 끝 ${ys[ys.length - 1]} → ${ys.length > 1 ? "기록기가 변화를 잡음" : "기록기가 변화를 못 잡음"}`);
} finally {
  await page.close();
  process.exit(0);
}
