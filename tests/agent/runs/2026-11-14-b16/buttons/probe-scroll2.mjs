// H1 가설 확인 — Start speaking 뒤 프레임마다 문서 높이 · 카드 높이 · scrollY 를 표본함.
// 창 높이 900(문서 여유 51px)과 700(여유 큼)에서 같은 절차를 돌려, 움직임이 클램프인지 앱의 스크롤인지 가름.
import { APP, connect, save } from "./lib.mjs";

const { ctx } = await connect();
const out = [];
for (const [W, H, y] of [[1400, 900, 40], [1400, 700, 200]]) {
  const page = await ctx.newPage();
  await page.setViewportSize({ width: W, height: H });
  try {
    await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="home-hero"][data-state="ready"]', { timeout: 15000 });
    await page.waitForTimeout(800);
    await page.evaluate((yy) => window.scrollTo(0, yy), y);
    await page.waitForTimeout(300);
    const samples = await page.evaluate(
      () =>
        new Promise((resolve) => {
          const s = [];
          const t0 = performance.now();
          const tick = () => {
            const hero = document.querySelector('[data-testid="home-hero"]');
            s.push({
              t: Math.round(performance.now() - t0),
              y: window.scrollY,
              docH: document.documentElement.scrollHeight,
              heroH: Math.round(hero.getBoundingClientRect().height),
              mode: hero.dataset.mode,
              loading: !document.querySelector('[data-testid="course-start"]'),
            });
            if (performance.now() - t0 < 1500) requestAnimationFrame(tick);
            else resolve(s);
          };
          document.querySelector('[data-testid="start-session"]').click();
          requestAnimationFrame(tick);
        }),
    );
    // 바뀐 지점만 남김
    const changes = samples.filter((x, i) => i === 0 || JSON.stringify({ ...x, t: 0 }) !== JSON.stringify({ ...samples[i - 1], t: 0 }));
    out.push({ W, H, y, changes });
    console.log(W, H, y, JSON.stringify(changes));
  } catch (e) {
    out.push({ W, H, y, error: e.message.split("\n")[0] });
  } finally {
    await page.close();
  }
}
save("probe-scroll2.json", out);
process.exit(0);
