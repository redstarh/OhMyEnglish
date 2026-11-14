// 1단계 — 화면마다 보이는 버튼·링크 목록(testid · 문구 · 태그 · href · 모양)을 1400 · 390 에서 모음.
// ⚠️ /course/1 과 홈 문장 연습은 열기만 해도 진도를 저장함(격리 DB).
import { APP, connect, newPage, inventory, save, shot, logger } from "./lib.mjs";

const RESULT_ID = "9feb8af1-e7fa-4be1-a9ed-9278f4ae22f4";
const VIDEO_ID = "b502eaf3-0fdd-408c-b273-a0c58a6410d2";
const log = logger("inventory.log");

const SCREENS = [
  { key: "home", path: "/", ready: '[data-testid="home-hero"][data-state="ready"]' },
  {
    key: "home-practice",
    path: "/",
    ready: '[data-testid="home-hero"][data-state="ready"]',
    then: async (p) => {
      await p.click('[data-testid="start-session"]');
      await p.waitForSelector('[data-testid="course-start"]', { timeout: 10000 });
    },
  },
  {
    key: "session-failed",
    path: "/",
    ready: '[data-testid="home-hero"][data-state="ready"]',
    deny: true,
    then: async (p) => {
      await p.locator('[data-testid="practice-free_talk"]').click();
      await p.waitForSelector('[data-testid="session-failed"]', { timeout: 10000 });
    },
  },
  { key: "history", path: "/history", ready: "main h1" },
  { key: "weekly", path: "/history/weekly", ready: "main h1" },
  { key: "results", path: `/results/${RESULT_ID}`, ready: "main h1" },
  { key: "course", path: "/course", ready: '[data-testid^="course-day-"]' },
  { key: "course-1", path: "/course/1", ready: '[data-testid="course-back"]' },
  { key: "videos", path: "/videos", ready: "main h1" },
  { key: "video", path: `/videos/${VIDEO_ID}`, ready: "main h1" },
];

const { ctx } = await connect();
const all = {};
for (const width of [1400, 390]) {
  for (const s of SCREENS) {
    const page = await newPage(ctx, width);
    try {
      if (s.deny) {
        await page.addInitScript(() => {
          navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException("denied", "NotAllowedError"));
        });
      }
      await page.goto(APP + s.path, { waitUntil: "domcontentloaded" });
      await page.waitForSelector(s.ready, { timeout: 15000 });
      await page.waitForTimeout(1200);
      if (s.then) await s.then(page);
      await page.waitForTimeout(400);
      const items = await inventory(page);
      all[`${s.key}@${width}`] = { url: page.url(), items };
      await shot(page, `inv-${s.key}-${width}.png`);
      log(s.key, width, "items", items.length);
    } catch (e) {
      all[`${s.key}@${width}`] = { error: e.message.split("\n")[0] };
      log(s.key, width, "ERR", e.message.split("\n")[0]);
    } finally {
      await page.close();
    }
  }
}
save("inventory.json", all);
log("done");
