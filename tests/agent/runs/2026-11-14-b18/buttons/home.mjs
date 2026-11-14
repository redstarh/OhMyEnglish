// 2단계 — 홈 버튼 동작. 사용: node home.mjs <폭> [높이]. 코치 세션은 열지 않음(session.mjs · entries.mjs 가 맡음).
// 진도 저장은 routeCourse 로 받아 DB 에 쓰지 않음.
import { APP, connect, newPage, verdicts, shot, waitUrl, home, routeCourse, save } from "./lib.mjs";

const W = Number(process.argv[2] ?? 1400);
const H = Number(process.argv[3] ?? (W < 600 ? 844 : 900));
const V = verdicts(`home-${W}x${H}.json`);
const { ctx } = await connect();
const HERO = '[data-testid="home-hero"]';
const attr = (page, sel, name) => page.locator(sel).first().getAttribute(name);
const text = async (page, sel) => (await page.locator(sel).first().innerText()).trim();
const selected = (page) => page.locator('[data-testid^="path-day-"][data-selected="true"]').evaluateAll((els) => els.map((e) => e.dataset.testid));

const page = await newPage(ctx, W, H);
const reqs = await routeCourse(page);
try {
  await home(page);

  // H1 Start speaking — 창 스크롤 그대로. 클릭 뒤 1.2초 동안 매 프레임 scrollY · 카드 높이 · 문서 높이를 기록함.
  const want = H < 800 ? 200 : 40;
  await page.evaluate((y) => window.scrollTo(0, y), want);
  await page.waitForTimeout(300);
  const pre = await page.evaluate(() => ({
    y: window.scrollY,
    doc: document.documentElement.scrollHeight,
    hero: Math.round(document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().height * 10) / 10,
  }));
  await page.evaluate(() => {
    window.__frames = [];
    const t0 = performance.now();
    const tick = () => {
      const hero = document.querySelector('[data-testid="home-hero"]');
      window.__frames.push([Math.round(performance.now() - t0), window.scrollY, Math.round(hero.getBoundingClientRect().height * 10) / 10, document.documentElement.scrollHeight]);
      if (performance.now() - t0 < 1500) requestAnimationFrame(tick);
    };
    document.querySelector('[data-testid="start-session"]').addEventListener("click", () => requestAnimationFrame(tick), { once: true, capture: true });
  });
  await page.locator('[data-testid="start-session"]').click();
  await page.waitForSelector('[data-testid="course-start"], [data-testid="course-retry"]', { timeout: 15000 });
  await page.waitForTimeout(1600);
  const frames = await page.evaluate(() => window.__frames);
  const y1 = await page.evaluate(() => window.scrollY);
  const minHero = Math.min(...frames.map((f) => f[2]));
  const ys = [...new Set(frames.map((f) => f[1]))];
  const mode = await attr(page, HERO, "data-mode");
  save(`home-${W}x${H}-frames.json`, { pre, frames });
  V.add({
    id: "H1", screen: `home@${W}x${H}`, action: `Start speaking(scrollY ${want} 에서)`,
    expect: "data-mode=practice · 주소 / · 매 프레임 scrollY 가 시작값 그대로 · 카드 높이가 대기 높이 아래로 내려가지 않음",
    actual: `pre=${JSON.stringify(pre)} frames=${frames.length} scrollY 값=${JSON.stringify(ys)} 끝 ${y1} · 최소 카드 높이 ${minHero} · mode=${mode}`,
    verdict: pre.y > 0 && mode === "practice" && y1 === pre.y && ys.length === 1 && minHero >= pre.hero - 1 && new URL(page.url()).pathname === "/" ? "통과" : pre.y === 0 ? "불확실" : "실패",
  });
  const sel1 = await selected(page);
  V.add({ id: "H2", screen: "home-practice", action: "Start speaking 뒤 현재 Day 줄 강조", expect: "현재 Day 줄 하나만 data-selected=true", actual: JSON.stringify(sel1), verdict: sel1.length === 1 ? "통과" : "실패" });
  await shot(page, `home-${W}x${H}-practice.png`);

  // H3 ← Close
  await page.locator('[data-testid="practice-close"]').click();
  await page.waitForTimeout(600);
  const modeC = await attr(page, HERO, "data-mode");
  const selC = await selected(page);
  V.add({ id: "H3", screen: "home-practice", action: "← Close", expect: "data-mode=idle · 강조 줄 0개", actual: `mode=${modeC} selected=${JSON.stringify(selC)}`, verdict: modeC === "idle" && selC.length === 0 ? "통과" : "실패" });

  // H4 View all ↔ Show less
  const all = '[data-testid="home-path-all"]';
  const n0 = await page.locator('[data-testid^="path-day-"]').count();
  const t0 = await text(page, all);
  await page.click(all);
  await page.waitForTimeout(300);
  const n1 = await page.locator('[data-testid^="path-day-"]').count();
  const t1 = await text(page, all);
  const e1 = await attr(page, all, "aria-expanded");
  await page.click(all);
  await page.waitForTimeout(300);
  const n2 = await page.locator('[data-testid^="path-day-"]').count();
  const t2 = await text(page, all);
  V.add({ id: "H4", screen: "home", action: "View all ↔ Show less", expect: "n줄 View all → 더 많은 줄 Show less(aria-expanded=true) → n줄 View all", actual: `${n0} "${t0}" → ${n1} "${t1}" exp=${e1} → ${n2} "${t2}"`, verdict: n1 > n0 && n2 === n0 && t0 === "View all" && t1 === "Show less" && e1 === "true" && t2 === "View all" ? "통과" : "실패" });

  // H5 Day 4 줄 → 주소 / · Day 4 연습 · 그 줄만 강조
  await page.click(all);
  await page.waitForTimeout(300);
  await page.click('[data-testid="path-day-4"]');
  await page.waitForSelector('[data-testid="course-start"], [data-testid="course-retry"]', { timeout: 15000 });
  await page.waitForTimeout(800);
  const d4 = await text(page, '[data-testid="practice-day"]');
  const s4 = await selected(page);
  const b4 = await page.locator('[data-testid="path-day-4"]').evaluate((e) => getComputedStyle(e).borderColor);
  const b5 = await page.locator('[data-testid="path-day-5"]').evaluate((e) => getComputedStyle(e).borderColor);
  V.add({ id: "H5", screen: "home", action: "Day 4 줄", expect: "주소 / · practice-day 가 Day 4 · 강조 path-day-4 만 · 테두리 색이 다른 줄과 다름", actual: `url=${new URL(page.url()).pathname} day="${d4}" selected=${JSON.stringify(s4)} border4=${b4} border5=${b5}`, verdict: new URL(page.url()).pathname === "/" && /Day 4\b/.test(d4) && s4.length === 1 && s4[0] === "path-day-4" && b4 !== b5 ? "통과" : "실패" });

  // H6 연습 중 Day 2 줄 → 카드가 Day 2
  await page.click('[data-testid="path-day-2"]');
  await page.waitForTimeout(1500);
  const d2 = await text(page, '[data-testid="practice-day"]');
  const s2 = await selected(page);
  V.add({ id: "H6", screen: "home-practice", action: "연습 중 Day 2 줄", expect: "practice-day 가 Day 2 · 강조 path-day-2 만", actual: `day="${d2}" selected=${JSON.stringify(s2)}`, verdict: /Day 2\b/.test(d2) && s2.length === 1 && s2[0] === "path-day-2" ? "통과" : "실패" });
  await page.locator('[data-testid="practice-close"]').click();
  await page.waitForTimeout(600);
  await page.click(all); // 접음
  await page.waitForTimeout(300);

  // H7 More practice 에 Grammar course 없음 · 빠른 카드 없음
  const more = await page.locator('[data-testid="home-more-practice"]').innerText();
  const gc = await page.locator('[data-testid="practice-course"]').count();
  const quick = await page.locator('[data-testid^="quick-"]').count();
  V.add({ id: "H7", screen: "home", action: "More practice 구성", expect: "practice-course 0 · 문구 Grammar course 0 · quick-* 0(TASK-323)", actual: `practice-course=${gc} grammarText=${/Grammar course/i.test(more)} quick=${quick} 문구="${more.replace(/\s+/g, " ").slice(0, 160)}"`, verdict: gc === 0 && !/Grammar course/i.test(more) && quick === 0 ? "통과" : "실패" });

  // H8 Work role-play 비활성
  const rp = await page.locator('[data-testid="practice-roleplay"]').isDisabled();
  V.add({ id: "H8", screen: "home", action: "Work role-play", expect: "disabled", actual: `disabled=${rp}`, verdict: rp ? "통과" : "실패" });

  // H9 390 — 아래쪽 입구(Day 2 줄)로 열면 카드로 스크롤(TASK-308 · TASK-314)
  if (W < 600) {
    await page.locator('[data-testid="path-day-2"]').evaluate((e) => e.scrollIntoView({ block: "center" }));
    await page.waitForTimeout(400);
    const box = () => page.evaluate(() => {
      const r = document.querySelector('[data-testid="home-hero"]').getBoundingClientRect();
      return { y: window.scrollY, top: Math.round(r.top), bottom: Math.round(r.bottom), mode: document.querySelector('[data-testid="home-hero"]').dataset.mode };
    });
    const preM = await box();
    await page.locator('[data-testid="path-day-2"]').click();
    await page.waitForTimeout(1500);
    const postM = await box();
    V.add({ id: "H9", screen: "home@390", action: "path-day-2(아래에서)", expect: "누르기 전 카드가 화면 밖 → 누른 뒤 카드 위가 화면 안 · 연습 열림", actual: `pre=${JSON.stringify(preM)} post=${JSON.stringify(postM)}`, verdict: preM.bottom < 0 && postM.top >= 0 && postM.top < H && postM.mode === "practice" ? "통과" : "실패" });
    await page.locator('[data-testid="practice-close"]').click();
    await page.waitForTimeout(600);
  }

  // H10 · H11 History → · Weekly report → — 파란 바탕 · 이동
  for (const [id, tid, path] of [["H10", "home-history", "/history"], ["H11", "home-weekly", "/history/weekly"]]) {
    await home(page);
    const look = await page.locator(`[data-testid="${tid}"]`).evaluate((e) => ({ primary: e.classList.contains("omy-button-primary"), bg: getComputedStyle(e).backgroundColor }));
    await page.click(`[data-testid="${tid}"]`);
    const ok = await waitUrl(page, (u) => u.pathname === path);
    V.add({ id, screen: "home", action: tid, expect: `omy-button-primary(파란 바탕) · 주소 ${path}`, actual: `${JSON.stringify(look)} url=${new URL(page.url()).pathname}`, verdict: ok && look.primary && look.bg === "rgb(50, 99, 220)" ? "통과" : "실패" });
  }
  // H12 Learn with videos
  await home(page);
  await page.click('[data-testid="practice-videos"]');
  const okV = await waitUrl(page, (u) => u.pathname === "/videos");
  V.add({ id: "H12", screen: "home", action: "practice-videos", expect: "주소 /videos", actual: `url=${new URL(page.url()).pathname}`, verdict: okV ? "통과" : "실패" });

  // H13 사이드바 Home(1400) · H14 로고 → /
  await page.goto(APP + "/history", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(800);
  if (W >= 1024) {
    await page.click('[data-testid="nav-home"]');
    const ok = await waitUrl(page, (u) => u.pathname === "/");
    V.add({ id: "H13", screen: "shell", action: "nav-home(/history 에서)", expect: "주소 /", actual: `url=${new URL(page.url()).pathname}`, verdict: ok ? "통과" : "실패" });
    await page.goto(APP + "/history", { waitUntil: "domcontentloaded" });
    await page.waitForTimeout(800);
  }
  await page.locator('a[href="/"]').filter({ hasText: "OhMyEnglish" }).filter({ visible: true }).first().click();
  const okLogo = await waitUrl(page, (u) => u.pathname === "/");
  V.add({ id: "H14", screen: "shell", action: "로고(/history 에서)", expect: "주소 /", actual: `url=${new URL(page.url()).pathname}`, verdict: okLogo ? "통과" : "실패" });
} catch (e) {
  V.add({ id: "HX", screen: "home", action: "드라이버 예외", expect: "-", actual: e.message.split("\n")[0], verdict: "불확실" });
  await shot(page, `home-${W}x${H}-error.png`);
} finally {
  save(`home-${W}x${H}-requests.json`, reqs);
  V.flush();
  await page.close();
  process.exit(0);
}
