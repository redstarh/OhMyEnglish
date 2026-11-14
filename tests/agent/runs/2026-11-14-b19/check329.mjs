// TASK-329 확인 — 보고서 보완안 9건을 1400·390 실제 화면으로 봄.
// 실행: node check329.mjs (CDP 9440 의 헤드리스 Chrome · :3000 next dev · :8002 백엔드)
// ⛔ 쓰기 요청(POST/PUT/PATCH/DELETE)은 모두 막음 — 개발 DB `ohmyenglish` 를 바꾸지 않음.
// ⚠️ 개발 DB 에 없는 상태(빈 세션 · 지난 세션 · 새 응답 키)는 page.route 로 가짜 응답을 줌.
//    지금 떠 있는 백엔드는 --reload 없이 떠 있어 TASK-329 의 새 키를 아직 주지 않음.
import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const EVIDENCE = join(HERE, "evidence");
const APP = "http://localhost:3000";
const TODAY = "2026-11-14";
const THIS_MONDAY = "2026-11-09";
const VIDEO = "e5463a72-bc9d-488e-8357-f4dc13ddfa54";
const SESS = {
  today: "1d8ac161-f683-4f37-b082-7fc8fd6b01c3",
  today2: "cff880f9-322e-4015-90ff-96c95ed5c714",
  today3: "2a9cbf0f-5920-4c2a-8594-654a4504563e",
  past: "760b639f-7fd2-4f02-939c-d5b52df2b42d",
  empty: "00000000-0000-4000-8000-000000000329",
};

const results = [];
const blocked = [];
const check = (item, width, name, ok, detail) => {
  results.push({ item, width, name, ok: Boolean(ok), detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${item} @${width} ${name}${detail ? ` — ${detail}` : ""}`);
};

const json = (route, body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

function resultPayload(sessionDate, extra = {}) {
  return {
    status: "final", partial_failure: false, corrections: [], pronunciation: [], awaiting_analysis: false,
    summary: { went_well: ["You kept talking."], weak_points: [] },
    session_date: sessionDate, finished: true, ...extra,
  };
}

async function setup(page, { weekStart = "2026-11-02" } = {}) {
  await page.route("**/*", async (route) => {
    const req = route.request();
    const url = new URL(req.url());
    if (req.method() !== "GET" && req.method() !== "HEAD" && req.method() !== "OPTIONS" && url.port !== "3000") {
      blocked.push(`${req.method()} ${url.pathname}`);
      return route.abort();
    }
    if (url.port === "8002") {
      const path = url.pathname;
      if (path === "/api/weekly-report") {
        const real = await (await route.fetch()).json();
        return json(route, { ...real, week_start: weekStart, this_week_start: THIS_MONDAY,
          metrics: { ...real.metrics, session_count: 4, pattern_count: 2, top_patterns: [] } });
      }
      if (path === "/api/history") {
        const real = await (await route.fetch()).json();
        const days = real.days.map((d) => ({ ...d, sessions: [] }));
        const at = (day) => days.find((d) => d.day === day);
        if (at(TODAY)) Object.assign(at(TODAY), { learned: true, analyzed: false, sessions: [
          { session_id: SESS.today3, title: "Meeting someone for the first time" },
          { session_id: SESS.today2, title: "After work with a colleague" },
          { session_id: SESS.today, title: "Weekend plans with a friend" }] });
        if (at("2026-11-01")) Object.assign(at("2026-11-01"), { learned: true, sessions: [
          { session_id: SESS.past, title: "Weekend plans with a friend" }] });
        return json(route, { ...real, days });
      }
      if (path === "/api/daily-summary") {
        const real = await (await route.fetch()).json();
        return json(route, { ...real, summary_date: TODAY, completed_today: true, completed_scenarios: 3 });
      }
      const m = path.match(/^\/api\/sessions\/([^/]+)\/results$/);
      if (m) {
        if (m[1] === SESS.past) return json(route, resultPayload("2026-11-01"));
        if (m[1] === SESS.today) return json(route, resultPayload(TODAY));
        if (m[1] === SESS.empty) return json(route, {
          status: "no_utterances", partial_failure: false, pronunciation: [], awaiting_analysis: false,
          summary: { went_well: [], weak_points: [] }, session_date: TODAY, finished: true });
      }
    }
    return route.continue();
  });
}

const text = (page, sel) => page.locator(sel).first().innerText().catch(() => null);
const shot = (page, name, width) => page.screenshot({ path: join(EVIDENCE, `${name}-${width}.png`), fullPage: true });

async function run(context, width) {
  // ① 홈 Your progress
  let page = await context.newPage();
  await setup(page);
  await page.goto(`${APP}/`, { waitUntil: "networkidle" });
  await page.getByTestId("home-weekly-period").waitFor({ timeout: 15000 });
  check(1, width, "기간 줄", (await text(page, '[data-testid="home-weekly-period"]')) === "Last week · Nov 2 – Nov 8",
    await text(page, '[data-testid="home-weekly-period"]'));
  check(1, width, "옛 아래 줄 없음", !(await page.locator("text=Weekly report · week of").count()));
  await page.getByTestId("home-progress").screenshot({ path: join(EVIDENCE, `1-home-progress-${width}.png`) });
  // ④ 문장 연습 ← Previous
  await page.getByRole("button", { name: /Start speaking/ }).first().click();
  await page.getByTestId("course-prev").waitFor({ timeout: 15000 });
  const prev = await text(page, '[data-testid="course-prev"]');
  check(4, width, "← Previous", prev === "← Previous", prev);
  await shot(page, "4-practice", width);
  await page.close();

  // ① 이번 주 리포트면 This week
  page = await context.newPage();
  await setup(page, { weekStart: THIS_MONDAY });
  await page.goto(`${APP}/`, { waitUntil: "networkidle" });
  await page.getByTestId("home-weekly-period").waitFor({ timeout: 15000 });
  check(1, width, "이번 주는 This week", (await text(page, '[data-testid="home-weekly-period"]')) === "This week · Nov 9 – Nov 15");
  // ② 같은 상태의 주간 리포트
  await page.goto(`${APP}/history/weekly`, { waitUntil: "networkidle" });
  await page.getByTestId("weekly-period").waitFor({ timeout: 15000 });
  check(2, width, "이번 주 본문", (await page.locator("main").innerText()).includes("Try next week"));
  await shot(page, "2-weekly-this", width);
  await page.close();

  // ② ⑧ 지난주 리포트
  page = await context.newPage();
  await setup(page);
  await page.goto(`${APP}/history/weekly`, { waitUntil: "networkidle" });
  await page.getByTestId("weekly-period").waitFor({ timeout: 15000 });
  const heading = await text(page, '[data-testid="weekly-heading"]');
  check(2, width, "제목에 기간", heading === "Weekly report · Nov 2 – Nov 8", heading);
  const body = await page.locator("main").innerText();
  check(2, width, "본문에 this week 없음", !/this week/i.test(body.replace("Try this week", "")), "Try this week 만 허용");
  check(2, width, "Common mistakes last week", body.includes("Common mistakes last week"));
  check(8, width, "← Home 버튼", (await text(page, '[data-testid="weekly-home"]')) === "← Home"
    && (await page.getByTestId("weekly-home").getAttribute("class"))?.includes("omy-button"));
  await shot(page, "2-8-weekly-last", width);
  await page.getByTestId("weekly-home").click();
  await page.waitForURL(`${APP}/`, { timeout: 10000 });
  check(8, width, "← Home 이 홈으로 감", new URL(page.url()).pathname === "/");
  await page.close();

  // ③ 결과 — 지난 세션 · 오늘 세션
  page = await context.newPage();
  await setup(page);
  await page.goto(`${APP}/results/${SESS.past}`, { waitUntil: "networkidle" });
  await page.getByTestId("results-done").waitFor({ timeout: 15000 });
  check(3, width, "지난 세션", (await text(page, '[data-testid="results-done"]')) === "You finished on Nov 1",
    await text(page, '[data-testid="results-done"]'));
  check(3, width, "총평 제목", (await page.locator("main").innerText()).includes("Lesson on Nov 1"));
  await shot(page, "3-results-past", width);
  await page.goto(`${APP}/results/${SESS.today}`, { waitUntil: "networkidle" });
  await page.getByTestId("results-done").waitFor({ timeout: 15000 });
  check(3, width, "오늘 세션", (await text(page, '[data-testid="results-done"]')) === "You finished today — 3 scenes");
  await shot(page, "3-results-today", width);
  // ⑨ 발화 0건
  await page.goto(`${APP}/results/${SESS.empty}`, { waitUntil: "networkidle" });
  await page.getByTestId("results-start-again").waitFor({ timeout: 15000 });
  check(9, width, "사실 문구", (await text(page, '[data-testid="results-status"]')) === "We didn't hear you this time.");
  check(9, width, "칭찬 없음", (await page.getByTestId("results-done").count()) === 0
    && !(await page.locator("main").innerText()).includes("You finished"));
  check(9, width, "Start again → 은 primary", (await page.getByTestId("results-start-again").getAttribute("class"))?.includes("omy-button-primary"));
  await shot(page, "9-results-empty", width);
  await page.close();

  // ⑤ ⑦ 기록
  page = await context.newPage();
  await setup(page);
  await page.goto(`${APP}/history`, { waitUntil: "networkidle" });
  await page.getByTestId("history-day-group").waitFor({ timeout: 15000 });
  const hbody = await page.locator("main").innerText();
  check(5, width, "Not analyzed yet", hbody.includes("Not analyzed yet") && !hbody.includes("Not checked"));
  check(5, width, "설명 한 줄", (await page.getByTestId("history-not-analyzed-hint").count()) === 1);
  await page.getByTestId("history-day-group").locator("summary").click();
  check(7, width, "여러 세션은 목록", (await page.getByTestId("history-session-link").count()) === 3);
  await shot(page, "5-7-history", width);
  const single = page.getByTestId("history-day-link").first();
  check(7, width, "한 세션은 바로 링크", (await single.getAttribute("href")) === `/results/${SESS.past}`);
  await single.click();
  await page.waitForURL(`**/results/${SESS.past}`, { timeout: 10000 });
  check(7, width, "결과로 이동", page.url().endsWith(`/results/${SESS.past}`));
  await page.close();

  // ⑥ 영상
  page = await context.newPage();
  await setup(page);
  await page.goto(`${APP}/videos/${VIDEO}`, { waitUntil: "domcontentloaded" });
  const mark = page.getByRole("button", { name: "Mark a hard part" });
  await mark.waitFor({ timeout: 15000 });
  check(6, width, "Mark a hard part", (await mark.count()) === 1 && (await page.getByText("Mark start").count()) === 0);
  await shot(page, "6-video-idle", width);
  await mark.click();
  check(6, width, "이어지는 버튼", (await page.getByRole("button", { name: "End the hard part here" }).count()) === 1
    && (await page.getByRole("button", { name: "Cancel" }).count()) === 1);
  await shot(page, "6-video-marking", width);
  await page.close();
}

const browser = await chromium.connectOverCDP("http://127.0.0.1:9440");
for (const [width, height] of [[1400, 900], [390, 844]]) {
  const context = await browser.newContext({ viewport: { width, height } });
  try {
    await run(context, width);
  } catch (error) {
    check("run", width, "예외", false, String(error).slice(0, 300));
  }
  await context.close();
}
await browser.close();
writeFileSync(join(EVIDENCE, "check329.json"), JSON.stringify({ results, blocked }, null, 2));
const fails = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - fails}/${results.length} PASS · blocked writes: ${blocked.length}`, blocked);
process.exit(fails ? 1 : 0);
