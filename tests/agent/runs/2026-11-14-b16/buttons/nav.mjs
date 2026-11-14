// 2단계 — 홈 밖 화면의 이동 버튼(문구로 고름 — 이 화면들에는 testid 가 없음, course-back 만 있음).
// ⛔ 자료를 바꾸는 버튼(Delete · 구간 Save · 영상 Check/Save)과 바깥 사이트 링크는 누르지 않고 href·상태만 봄.
import { APP, connect, newPage, verdicts, waitUrl, shot } from "./lib.mjs";

const W = Number(process.argv[2] ?? 1400);
const RESULT_ID = process.argv[3] ?? "9feb8af1-e7fa-4be1-a9ed-9278f4ae22f4";
const VIDEO_ID = "b502eaf3-0fdd-408c-b273-a0c58a6410d2";
const V = verdicts(`nav-${W}.json`);
const { ctx } = await connect();
const page = await newPage(ctx, W);

async function go(path) {
  await page.goto(APP + path, { waitUntil: "domcontentloaded" });
  await page.waitForSelector("main h1, [data-testid=course-back]", { timeout: 15000 });
  await page.waitForTimeout(800);
}
async function clickTo(id, from, pick, to, label) {
  try {
    await go(from);
    await pick().click();
    const ok = await waitUrl(page, (u) => (typeof to === "string" ? u.pathname === to : to.test(u.pathname)));
    V.add({ id, screen: from, action: label, expect: `주소 ${to}`, actual: `url=${new URL(page.url()).pathname}`, verdict: ok ? "통과" : "실패" });
  } catch (e) {
    V.add({ id, screen: from, action: label, expect: `주소 ${to}`, actual: e.message.split("\n")[0], verdict: "불확실" });
  }
}
const link = (name) => () => page.locator("main").getByRole("link", { name, exact: true });

await clickTo("N1", "/history", link("Weekly report →"), "/history/weekly", "Weekly report →");
await clickTo("N2", "/history", link("← Home"), "/", "← Home");
await clickTo("N3", "/history/weekly", link("← History"), "/history", "← History");
await clickTo("N4", `/results/${RESULT_ID}`, link("← Home"), "/", "← Home");
await clickTo("N5", `/results/${RESULT_ID}`, link("History →"), "/history", "History →");
await clickTo("N6", "/course", link("← Home"), "/", "← Home");
await clickTo("N7", "/course", () => page.locator('main a[href="/course/1"]'), "/course/1", "Continue ▶(Day 1)");
await clickTo("N8", "/course", () => page.locator('main a[href="/course/3"]'), "/course/3", "Start(Day 3)");
await clickTo("N9", "/course/1", () => page.locator('[data-testid="course-back"]'), "/course", "← Back(course-back)");
await clickTo("N10", "/videos", link("← Home"), "/", "← Home");
await clickTo("N11", "/videos", () => page.locator(`main a[href="/videos/${VIDEO_ID}"]`), `/videos/${VIDEO_ID}`, "영상 제목 링크");
await clickTo("N12", `/videos/${VIDEO_ID}`, link("← Videos"), "/videos", "← Videos");

// 결과 화면 드릴 링크(있으면 href 만) · 영상 화면의 바깥 링크(href·target 만) · /videos 의 Check 비활성
try {
  await go(`/results/${RESULT_ID}`);
  const drills = await page.locator("main a.omy-button").evaluateAll((els) => els.map((e) => [e.textContent.trim(), e.getAttribute("href")]));
  V.add({ id: "N13", screen: "/results", action: "출구 외 링크 목록(드릴)", expect: "드릴 링크가 있으면 href 가 /?…source=additional", actual: JSON.stringify(drills), verdict: "통과" });
  await go(`/videos/${VIDEO_ID}`);
  const ext = await page.locator('main a[target="_blank"]').evaluateAll((els) => els.map((e) => [e.textContent.trim(), e.getAttribute("href"), e.className]));
  V.add({ id: "N14", screen: "/videos/<id>", action: "바깥 링크(누르지 않음)", expect: "있다면 youtube 주소 · target=_blank", actual: ext.length ? JSON.stringify(ext) : "보이는 바깥 링크 없음", verdict: ext.every((x) => /youtube/.test(x[1])) ? "통과" : "실패" });
  // Mark start → 초안 상태(Mark end · Reset 이 나타남) → Reset 으로 되돌림 — 저장하지 않음
  const ms = page.getByRole("button", { name: "Mark start" });
  if (await ms.count()) {
    await ms.click();
    await page.waitForTimeout(500);
    const after = await page.locator("main button").evaluateAll((els) => els.map((e) => e.textContent.trim()));
    const reset = page.locator("main button").filter({ hasText: /^(Mark again|Cancel)$/ });
    let back = "Reset 없음";
    if (await reset.count()) {
      await reset.first().click();
      await page.waitForTimeout(400);
      back = JSON.stringify(await page.locator("main button").evaluateAll((els) => els.map((e) => e.textContent.trim())));
    }
    V.add({ id: "N15", screen: "/videos/<id>", action: "Mark start → 되돌리기", expect: "끝 표시·되돌리기 버튼이 나타나고, 되돌리면 Mark start 만 남음", actual: `after=${JSON.stringify(after)} back=${back}`, verdict: after.length > 1 && back.includes("Mark start") && !back.includes("Mark end") ? "통과" : "불확실" });
    await shot(page, `nav-${W}-video.png`);
  }
  await go("/videos");
  const check = page.getByRole("button", { name: "Check" });
  const dis0 = await check.isDisabled();
  await page.locator("main input").first().fill("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
  const dis1 = await check.isDisabled();
  await page.locator("main input").first().fill("");
  V.add({ id: "N16", screen: "/videos", action: "Check(주소 입력 전후 · 누르지 않음)", expect: "빈칸이면 disabled · 주소를 넣으면 enabled", actual: `disabled ${dis0}→${dis1}`, verdict: dis0 && !dis1 ? "통과" : "실패" });
} catch (e) {
  V.add({ id: "NX", screen: "기타", action: "드라이버 예외", expect: "-", actual: e.message.split("\n")[0], verdict: "불확실" });
}
V.flush();
await page.close();
process.exit(0);
