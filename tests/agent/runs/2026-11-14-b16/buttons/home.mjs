// 2단계 — 홈 버튼 동작(1400). 코치 세션은 열지 않음(session.mjs 가 맡음).
import { APP, connect, newPage, verdicts, shot, waitUrl } from "./lib.mjs";

const W = Number(process.argv[2] ?? 1400);
const V = verdicts(`home-${W}.json`);
const { ctx } = await connect();
const HERO = '[data-testid="home-hero"]';

async function home(page) {
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector(`${HERO}[data-state="ready"]`, { timeout: 15000 });
  await page.waitForTimeout(800);
}
const attr = (page, sel, name) => page.locator(sel).first().getAttribute(name);
const text = (page, sel) => page.locator(sel).first().innerText();
const scrollY = (page) => page.evaluate(() => window.scrollY);

const page = await newPage(ctx, W);
try {
  await home(page);

  // H1 Start speaking → 카드 안 문장 연습 · 창 스크롤 그대로 · Listen/Slow 없음
  await page.evaluate(() => window.scrollTo(0, 40));
  await page.waitForTimeout(200);
  const y0 = await scrollY(page);
  await page.click('[data-testid="start-session"]');
  await page.waitForSelector('[data-testid="course-start"]', { timeout: 10000 });
  await page.waitForTimeout(800);
  const y1 = await scrollY(page);
  const mode = await attr(page, HERO, "data-mode");
  const inHero = await page.locator(`${HERO} [data-testid="sentence-practice"]`).count();
  const day = await text(page, '[data-testid="practice-day"]');
  const listenSlow = await page.locator('[data-testid="course-listen"], [data-testid="course-slow"]').count();
  const listenText = await page.getByRole("button", { name: /^(Listen|Slow)$/ }).count();
  V.add({
    id: "H1", screen: "home", action: "Start speaking",
    expect: "data-mode=practice · 카드 안 sentence-practice · scrollY 불변",
    actual: `mode=${mode} inHero=${inHero} day="${day}" scrollY ${y0}→${y1} url=${new URL(page.url()).pathname}`,
    verdict: mode === "practice" && inHero === 1 && y0 === y1 && new URL(page.url()).pathname === "/" ? "통과" : "실패",
  });
  V.add({
    id: "H2", screen: "home-practice", action: "Listen/Slow 부재",
    expect: "course-listen · course-slow · 문구 Listen/Slow 버튼 0개",
    actual: `testid ${listenSlow} · 문구 ${listenText}`,
    verdict: listenSlow === 0 && listenText === 0 ? "통과" : "실패",
  });
  const sel1 = await attr(page, '[data-testid="path-day-1"]', "data-selected");
  V.add({
    id: "H3", screen: "home-practice", action: "Start speaking 뒤 현재 Day 줄 강조",
    expect: "path-day-<current> data-selected=true",
    actual: `path-day-1 data-selected=${sel1}`,
    verdict: sel1 === "true" ? "통과" : "실패",
  });
  await shot(page, `home-${W}-practice.png`);

  // H4 Close → 대기
  await page.click('[data-testid="practice-close"]');
  await page.waitForTimeout(600);
  const modeC = await attr(page, HERO, "data-mode");
  const selC = await page.locator('[data-testid^="path-day-"][data-selected="true"]').count();
  V.add({
    id: "H4", screen: "home-practice", action: "← Close",
    expect: "data-mode=idle · 강조 줄 0개",
    actual: `mode=${modeC} selected=${selC}`,
    verdict: modeC === "idle" && selC === 0 ? "통과" : "실패",
  });

  // H5 View all ↔ Show less
  const n0 = await page.locator('[data-testid^="path-day-"]').count();
  const all = '[data-testid="home-path-all"]';
  const t0 = (await text(page, all)).trim();
  await page.click(all);
  await page.waitForTimeout(300);
  const n1 = await page.locator('[data-testid^="path-day-"]').count();
  const t1 = (await text(page, all)).trim();
  const e1 = await attr(page, all, "aria-expanded");
  await page.click(all);
  await page.waitForTimeout(300);
  const n2 = await page.locator('[data-testid^="path-day-"]').count();
  const t2 = (await text(page, all)).trim();
  V.add({
    id: "H5", screen: "home", action: "View all ↔ Show less",
    expect: "2줄 View all → 6줄 Show less(aria-expanded=true) → 2줄 View all",
    actual: `${n0} "${t0}" → ${n1} "${t1}" exp=${e1} → ${n2} "${t2}"`,
    verdict: n0 === 2 && n1 === 6 && n2 === 2 && t0 === "View all" && t1 === "Show less" && e1 === "true" ? "통과" : "실패",
  });

  // H6 Day 줄(펼친 뒤 Day 4) → 주소 / · 그 Day 연습 · 그 줄만 강조
  await page.click(all);
  await page.waitForTimeout(300);
  await page.click('[data-testid="path-day-4"]');
  await page.waitForSelector('[data-testid="course-start"]', { timeout: 10000 });
  await page.waitForTimeout(800);
  const d4 = await text(page, '[data-testid="practice-day"]');
  const s4 = await page.locator('[data-testid^="path-day-"][data-selected="true"]').evaluateAll((els) => els.map((e) => e.dataset.testid));
  const b4 = await page.locator('[data-testid="path-day-4"]').evaluate((e) => getComputedStyle(e).borderColor);
  const b5 = await page.locator('[data-testid="path-day-5"]').evaluate((e) => getComputedStyle(e).borderColor);
  const unit4 = await text(page, '[data-testid="course-unit"]');
  V.add({
    id: "H6", screen: "home", action: "Day 4 줄",
    expect: "주소 / · practice-day 가 Day 4 · 강조 path-day-4 만 · 테두리 색이 다른 줄과 다름",
    actual: `url=${new URL(page.url()).pathname} day="${d4}" unit="${unit4}" selected=${JSON.stringify(s4)} border4=${b4} border5=${b5}`,
    verdict: new URL(page.url()).pathname === "/" && /Day 4\b/.test(d4) && s4.length === 1 && s4[0] === "path-day-4" && b4 !== b5 ? "통과" : "실패",
  });

  // H7 연습 중 다른 Day(2) 고르기 → 카드가 Day 2 로 바뀜
  await page.click('[data-testid="path-day-2"]');
  await page.waitForTimeout(1500);
  const d2 = await text(page, '[data-testid="practice-day"]');
  const s2 = await page.locator('[data-testid^="path-day-"][data-selected="true"]').evaluateAll((els) => els.map((e) => e.dataset.testid));
  V.add({
    id: "H7", screen: "home-practice", action: "연습 중 Day 2 줄",
    expect: "practice-day 가 Day 2 · 강조 path-day-2 만",
    actual: `day="${d2}" selected=${JSON.stringify(s2)}`,
    verdict: /Day 2\b/.test(d2) && s2.length === 1 && s2[0] === "path-day-2" ? "통과" : "실패",
  });

  // H8 Grammar course → 현재 Day(1) 연습
  await page.click('[data-testid="practice-course"]');
  await page.waitForTimeout(1500);
  const dg = await text(page, '[data-testid="practice-day"]');
  const sg = await page.locator('[data-testid^="path-day-"][data-selected="true"]').evaluateAll((els) => els.map((e) => e.dataset.testid));
  V.add({
    id: "H8", screen: "home", action: "More practice · Grammar course",
    expect: "주소 / · practice-day 가 현재 Day(1) · 강조 path-day-1",
    actual: `url=${new URL(page.url()).pathname} day="${dg}" selected=${JSON.stringify(sg)}`,
    verdict: new URL(page.url()).pathname === "/" && /Day 1\b/.test(dg) && sg[0] === "path-day-1" ? "통과" : "실패",
  });
  await page.click('[data-testid="practice-close"]');
  await page.waitForTimeout(600);

  // H9 Work role-play 비활성
  const rp = await page.locator('[data-testid="practice-roleplay"]').isDisabled();
  V.add({ id: "H9", screen: "home", action: "Work role-play", expect: "disabled", actual: `disabled=${rp}`, verdict: rp ? "통과" : "실패" });

  // H10~ 링크 이동
  for (const [id, tid, path] of [
    ["H10", "home-history", "/history"],
    ["H11", "home-weekly", "/history/weekly"],
    ["H12", "quick-videos", "/videos"],
    ["H13", "practice-videos", "/videos"],
  ]) {
    await home(page);
    await page.click(`[data-testid="${tid}"]`);
    const ok = await waitUrl(page, (u) => u.pathname === path);
    V.add({ id, screen: "home", action: tid, expect: `주소 ${path}`, actual: `url=${new URL(page.url()).pathname}`, verdict: ok ? "통과" : "실패" });
  }

  // H14 사이드바 Home · 로고 → / (1400 만 사이드바가 있음)
  await page.goto(APP + "/history", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(800);
  if (W >= 1024) {
    await page.click('[data-testid="nav-home"]');
    const ok = await waitUrl(page, (u) => u.pathname === "/");
    V.add({ id: "H14", screen: "shell", action: "nav-home(/history 에서)", expect: "주소 /", actual: `url=${new URL(page.url()).pathname}`, verdict: ok ? "통과" : "실패" });
    await page.goto(APP + "/history", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(800);
  }
  await page.locator('aside a[href="/"], header a[href="/"]').filter({ hasText: "OhMyEnglish" }).filter({ visible: true }).first().click();
  const okLogo = await waitUrl(page, (u) => u.pathname === "/");
  V.add({ id: "H15", screen: "shell", action: "로고(/history 에서)", expect: "주소 /", actual: `url=${new URL(page.url()).pathname}`, verdict: okLogo ? "통과" : "실패" });
} catch (e) {
  V.add({ id: "HX", screen: "home", action: "드라이버 예외", expect: "-", actual: e.message.split("\n")[0], verdict: "불확실" });
  await shot(page, `home-${W}-error.png`);
} finally {
  V.flush();
  await page.close();
  process.exit(0);
}
