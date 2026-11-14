// 2단계 — 세션 실패 화면(마이크 거부 · 소켓 없음)과 실제 코치 세션 1개(Free talk)의 잠금 · End lesson.
// 사용: node session.mjs <폭>. 390 이면 아래쪽 입구의 카드 스크롤(TASK-308)도 봄.
// ⛔ 실제 Nova 세션은 이 스크립트 1회당 1개. 가짜 마이크 소리는 말이 아니므로 대화 내용은 판정하지 않음.
// ⚠️ End lesson 에는 testid 가 없어 문구(「End lesson」)로 고름.
import { APP, connect, newPage, verdicts, waitUrl, shot, save } from "./lib.mjs";

const W = Number(process.argv[2] ?? 1400);
const V = verdicts(`session-${W}.json`);
const { ctx } = await connect();
const HERO = '[data-testid="home-hero"]';

async function home(page) {
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector(`${HERO}[data-state="ready"]`, { timeout: 15000 });
  await page.waitForTimeout(800);
}
/** 잠김 상태 모음 — 링크는 aria-disabled, 버튼은 disabled. */
async function lockState(page) {
  return page.evaluate(() => {
    const q = (s) => document.querySelector(s);
    const all = (s) => [...document.querySelectorAll(s)];
    return {
      navLocked: q('nav[aria-label="Main"]')?.getAttribute("data-locked") ?? null,
      navHome: q('[data-testid="nav-home"]')?.getAttribute("aria-disabled") ?? null,
      logo: all('a[href="/"]').filter((a) => a.offsetParent && a.textContent.includes("OhMyEnglish")).map((a) => a.getAttribute("aria-disabled")),
      links: ["home-history", "home-weekly", "quick-videos", "practice-videos"].map((t) => [t, q(`[data-testid="${t}"]`)?.getAttribute("aria-disabled") ?? null]),
      buttons: all('[data-testid^="path-day-"], [data-testid="home-path-all"], [data-testid="focus-practice"], button[data-testid^="quick-"], button[data-testid^="practice-"]').map((b) => [b.dataset.testid, b.disabled]),
    };
  });
}
const lockedAll = (s) => s.links.every(([, v]) => v === "true") && s.buttons.filter(([t]) => t !== "home-path-all").every(([, d]) => d) && (s.navHome === null || s.navHome === "true");
const freeAll = (s) => s.links.every(([, v]) => v === null) && s.buttons.filter(([t]) => t !== "practice-roleplay").every(([, d]) => !d);

// ── 실패 화면 ──
const fp = await newPage(ctx, W);
try {
  await fp.addInitScript(() => {
    window.__gum = 0;
    navigator.mediaDevices.getUserMedia = () => {
      window.__gum += 1;
      return Promise.reject(new DOMException("denied", "NotAllowedError"));
    };
  });
  await home(fp);
  const before = await lockState(fp);
  await fp.locator('[data-testid="practice-free_talk"]').click();
  await fp.waitForSelector('[data-testid="session-failed"]', { timeout: 10000 });
  const reason = await fp.locator('[data-testid="session-failed"]').getAttribute("data-reason");
  const mode = await fp.locator(HERO).getAttribute("data-mode");
  V.add({ id: "F1", screen: "session-failed", action: "Free talk(마이크 거부)", expect: "카드 안 session-failed · data-reason=microphone_permission_denied", actual: `mode=${mode} reason=${reason}`, verdict: mode === "session" && reason === "microphone_permission_denied" ? "통과" : "실패" });
  const locked = await lockState(fp);
  V.add({ id: "F2", screen: "session-failed", action: "실패 화면 동안 잠금", expect: "링크 aria-disabled · 세션 여는 버튼·Day 줄 disabled (대조: 열기 전엔 모두 풀림)", actual: `before free=${freeAll(before)} · now ${JSON.stringify(locked)}`, verdict: freeAll(before) && lockedAll(locked) ? "통과" : "실패" });
  await fp.evaluate(() => document.querySelector('[data-testid="home-history"]').click());
  await fp.waitForTimeout(1200);
  V.add({ id: "F3", screen: "session-failed", action: "잠긴 History → 를 DOM 클릭", expect: "주소 / 그대로", actual: `url=${new URL(fp.url()).pathname}`, verdict: new URL(fp.url()).pathname === "/" ? "통과" : "실패" });
  const g0 = await fp.evaluate(() => window.__gum);
  await fp.locator('[data-testid="session-failed"]').getByRole("button", { name: "Try again" }).click();
  await fp.waitForTimeout(1200);
  const g1 = await fp.evaluate(() => window.__gum);
  const still = await fp.locator('[data-testid="session-failed"]').count();
  V.add({ id: "F4", screen: "session-failed", action: "Try again", expect: "세션을 다시 시도(getUserMedia 호출 +1) · 거부가 그대로라 다시 실패 화면", actual: `getUserMedia ${g0}→${g1} failed=${still}`, verdict: g1 === g0 + 1 && still === 1 ? "통과" : "실패" });
  await fp.locator('[data-testid="session-failed-home"]').click();
  await fp.waitForTimeout(800);
  const m5 = await fp.locator(HERO).getAttribute("data-mode");
  const free = await lockState(fp);
  V.add({ id: "F5", screen: "session-failed", action: "← Home(session-failed-home)", expect: "data-mode=idle · 잠금 모두 풀림", actual: `mode=${m5} free=${freeAll(free)}`, verdict: m5 === "idle" && freeAll(free) ? "통과" : "실패" });
} catch (e) {
  V.add({ id: "FX", screen: "session-failed", action: "드라이버 예외", expect: "-", actual: e.message.split("\n")[0], verdict: "불확실" });
} finally {
  await fp.close();
}

// ── 실제 코치 세션 1개 ──
const page = await newPage(ctx, W);
const ws = [];
page.on("websocket", (s) => {
  ws.push({ url: s.url(), at: Date.now() });
  s.on("framereceived", (f) => {
    const p = typeof f.payload === "string" ? f.payload : "";
    const m = p.match(/"type"\s*:\s*"([a-z_]+)"/);
    if (m && !["agent_audio", "audio"].includes(m[1])) ws.push({ in: m[1], sid: (p.match(/"session_id"\s*:\s*"([0-9a-f-]+)"/) ?? [])[1], at: Date.now() });
  });
});
try {
  await home(page);
  if (W < 600) {
    // 390 — 아래쪽 입구: Day 줄 · Grammar course 로 열 때 카드로 스크롤(TASK-308)
    for (const [id, tid] of [["M1", "path-day-2"], ["M2", "practice-course"]]) {
      await page.locator(`[data-testid="${tid}"]`).evaluate((e) => e.scrollIntoView({ block: "center" }));
      await page.waitForTimeout(400);
      const pre = await page.evaluate(() => {
        const r = document.querySelector('[data-testid="home-hero"]').getBoundingClientRect();
        return { y: window.scrollY, top: Math.round(r.top), bottom: Math.round(r.bottom) };
      });
      await page.locator(`[data-testid="${tid}"]`).click();
      await page.waitForTimeout(1500);
      const post = await page.evaluate(() => {
        const r = document.querySelector('[data-testid="home-hero"]').getBoundingClientRect();
        return { y: window.scrollY, top: Math.round(r.top), bottom: Math.round(r.bottom), mode: document.querySelector('[data-testid="home-hero"]').dataset.mode };
      });
      V.add({ id, screen: "home@390", action: `${tid}(아래에서)`, expect: "누르기 전 카드가 화면 밖 → 누른 뒤 카드 위가 화면 안(0 ≤ top < 화면 높이) · 연습 열림", actual: `pre=${JSON.stringify(pre)} post=${JSON.stringify(post)}`, verdict: pre.bottom < 0 && post.top >= 0 && post.top < 844 && post.mode === "practice" ? "통과" : "실패" });
      await page.locator('[data-testid="practice-close"]').click();
      await page.waitForTimeout(800);
    }
  } else {
    // 1400 — 문장 연습을 연 채로 Free talk → 연습이 먼저 닫히고 세션이 열림
    await page.locator('[data-testid="start-session"]').click();
    await page.waitForSelector('[data-testid="course-start"]', { timeout: 10000 });
  }

  const target = page.locator('[data-testid="practice-free_talk"]');
  if (W < 600) {
    await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await page.waitForTimeout(500);
  }
  const preS = await page.evaluate(() => ({ y: window.scrollY, top: Math.round(document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().top) }));
  await target.click();
  await page.waitForSelector('[data-testid="session-panel"]', { timeout: 10000 });
  const endBtn = page.locator('[data-testid="session-panel"]').getByRole("button", { name: "End lesson" });
  await endBtn.waitFor({ timeout: 30000 });
  const tActive = Date.now();
  await page.waitForTimeout(1500);
  const postS = await page.evaluate(() => ({ y: window.scrollY, top: Math.round(document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().top) }));
  const practiceGone = await page.locator('[data-testid="sentence-practice"]').count();
  const mode = await page.locator(HERO).getAttribute("data-mode");
  V.add({
    id: "S1", screen: `home@${W}`, action: W < 600 ? "Free talk(맨 아래에서)" : "Free talk(문장 연습을 연 채)",
    expect: W < 600 ? "카드로 스크롤(top 이 화면 안) · 카드 안 세션 · End lesson 보임" : "문장 연습 닫힘 · 카드 안 세션 · End lesson 보임",
    actual: `mode=${mode} practice=${practiceGone} pre=${JSON.stringify(preS)} post=${JSON.stringify(postS)}`,
    verdict: mode === "session" && practiceGone === 0 && (W >= 600 || (preS.top < 0 && postS.top >= 0 && postS.top < 844)) ? "통과" : "실패",
  });
  // 세션 시작 이벤트까지 기다림(세션 ID 없이 끝내면 결과 화면이 없음)
  const tS = Date.now();
  while (!ws.some((x) => x.in === "session_started") && Date.now() - tS < 20000) await page.waitForTimeout(200);
  const started = ws.find((x) => x.in === "session_started");
  const locked = await lockState(page);
  V.add({ id: "S2", screen: `home@${W}`, action: "세션 중 잠금", expect: "링크 aria-disabled · 세션 버튼·Day 줄 disabled · nav data-locked(1400)", actual: JSON.stringify(locked), verdict: lockedAll(locked) && (W < 600 || locked.navLocked === "true") ? "통과" : "실패" });
  await page.evaluate(() => document.querySelector('[data-testid="home-weekly"]').click());
  await page.waitForTimeout(1000);
  const stay = new URL(page.url()).pathname;
  const stillEnd = await endBtn.count();
  V.add({ id: "S3", screen: `home@${W}`, action: "잠긴 Weekly report → DOM 클릭", expect: "주소 / 그대로 · 세션 유지", actual: `url=${stay} endBtn=${stillEnd}`, verdict: stay === "/" && stillEnd === 1 ? "통과" : "실패" });
  await shot(page, `session-${W}-active.png`);
  const endStyle = await endBtn.evaluate((e) => {
    const r = e.getBoundingClientRect();
    const cs = getComputedStyle(e);
    return { h: Math.round(r.height * 10) / 10, fs: cs.fontSize, bg: cs.backgroundColor, radius: cs.borderRadius, omy: e.classList.contains("omy-button") };
  });
  await page.waitForTimeout(Math.max(0, 6000 - (Date.now() - tActive)));
  await endBtn.click();
  await page.waitForTimeout(200);
  const endingText = await page.locator('[data-testid="session-panel"] header button').innerText().catch(() => "?");
  const toResults = await waitUrl(page, (u) => u.pathname.startsWith("/results/"), 90000);
  const rid = new URL(page.url()).pathname.split("/")[2] ?? null;
  V.add({
    id: "S4", screen: `home@${W}`, action: "End lesson",
    expect: "누른 직후 Ending... · 결과 화면 /results/<session_started 의 ID>",
    actual: `ending="${endingText}" url=${new URL(page.url()).pathname} started=${started?.sid ?? "관측 못함"}`,
    verdict: toResults && endingText.startsWith("Ending") && (!started?.sid || started.sid === rid) ? "통과" : "실패",
  });
  if (toResults) {
    await page.waitForSelector("main h1", { timeout: 20000 });
    await page.waitForTimeout(1500);
    await shot(page, `session-${W}-results.png`);
  }
  save(`session-${W}-meta.json`, { rid, started, endStyle, ws: ws.slice(0, 40) });
} catch (e) {
  V.add({ id: "SX", screen: `home@${W}`, action: "드라이버 예외", expect: "-", actual: e.message.split("\n")[0], verdict: "불확실" });
  await shot(page, `session-${W}-error.png`);
} finally {
  V.flush();
  await page.close();
  process.exit(0);
}
