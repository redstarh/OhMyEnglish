// 1단계 — 화면마다 보이는 버튼·링크 목록(1400 · 390). 세션 화면 목록은 session.mjs 가 남김.
// 홈 문장 연습은 진도 저장을 routeCourse 로 받아 DB 에 쓰지 않음.
import { APP, connect, newPage, inventory, save, home, routeCourse } from "./lib.mjs";

const ZERO = "13869294-9b06-4c75-a56c-6529dcfa7971"; // 발화 0건 세션(db.py 조회)
const SPOKEN = "9feb8af1-e7fa-4be1-a9ed-9278f4ae22f4"; // 발화 8건 세션
const { ctx } = await connect();
const out = {};

for (const W of [1400, 390]) {
  const page = await newPage(ctx, W);
  await routeCourse(page);
  const rec = (out[W] = {});
  const grab = async (name, extra = {}) => {
    rec[name] = { url: new URL(page.url()).pathname, ...extra, items: await inventory(page) };
    console.log(W, name, rec[name].url, rec[name].items.length);
  };
  try {
    await home(page);
    await grab("home");
    await page.locator('[data-testid="start-session"]').click();
    await page.waitForSelector('[data-testid="course-start"], [data-testid="course-retry"]', { timeout: 15000 });
    await page.waitForTimeout(500);
    await grab("home-practice");

    for (const [name, path, wait] of [
      ["history", "/history", "main h1"],
      ["weekly", "/history/weekly", '[data-testid="weekly-heading"]'],
      ["results-zero", `/results/${ZERO}`, '[data-testid="results-status"]'],
      ["results-spoken", `/results/${SPOKEN}`, '[data-testid="results-status"]'],
      ["videos", "/videos", '[data-testid="videos-home"]'],
    ]) {
      await page.goto(APP + path, { waitUntil: "domcontentloaded" });
      await page.waitForSelector(wait, { timeout: 20000 }).catch(() => {});
      await page.waitForTimeout(1500);
      await grab(name);
    }
    // 첫 영상 화면
    const videoHref = await page.locator('main a[href^="/videos/"]').first().getAttribute("href").catch(() => null);
    if (videoHref) {
      await page.goto(APP + videoHref, { waitUntil: "domcontentloaded" });
      await page.waitForSelector('[data-testid="video-back"]', { timeout: 20000 }).catch(() => {});
      await page.waitForTimeout(2500);
      await grab("video", { videoHref });
    } else rec.video = { missing: true };

    for (const [name, path] of [["course", "/course"], ["course-1", "/course/1"]]) {
      await page.goto(APP + path, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(2500);
      await grab(name, { requested: path });
    }
  } catch (e) {
    rec.error = e.message.split("\n")[0];
    console.log("오류", W, rec.error);
  } finally {
    await page.close();
  }
}
save("inventory.json", out);
process.exit(0);
