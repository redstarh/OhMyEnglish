// 회차 b16 화면 탭 — 장면별 단계 스크린샷 + 배치 측정. 단일 명령: node runs/2026-11-14-b16/screens/shoot.mjs [장면…]
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SHOTS = join(HERE, "storyboard", "shots");
const EVID = join(HERE, "evidence");
mkdirSync(SHOTS, { recursive: true });
mkdirSync(EVID, { recursive: true });
const APP = "http://localhost:3000";
const CDP = "http://127.0.0.1:9401";
const WIDTHS = [
  { w: 1400, h: 1000 },
  { w: 390, h: 844 },
];
const ONLY = process.argv.slice(2);
const LOG = join(EVID, "run.log");
const log = (m) => {
  const line = `${new Date().toISOString()} ${m}\n`;
  process.stdout.write(line);
  writeFileSync(LOG, line, { flag: "a" });
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 페이지 안에서 도는 측정 — 넘침 · 잘린 글자 · 카드 높이 · 대문자 라벨 · 한국어
function measureInPage() {
  const de = document.documentElement;
  const vis = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden" || Number(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const tid = (el) => {
    const t = el.closest("[data-testid]");
    return t ? t.getAttribute("data-testid") : null;
  };
  const ownText = (el) =>
    [...el.childNodes]
      .filter((n) => n.nodeType === 3)
      .map((n) => n.textContent)
      .join("")
      .trim();
  const clipped = [];
  const offRight = [];
  const labels = [];
  const korean = [];
  const HANGUL = /[ㄱ-ㆎ가-힣]/;
  for (const el of document.body.querySelectorAll("*")) {
    if (!vis(el)) continue;
    const s = getComputedStyle(el);
    const txt = ownText(el);
    const r = el.getBoundingClientRect();
    if (txt) {
      const hidesX = ["hidden", "clip"].includes(s.overflowX) || s.textOverflow === "ellipsis";
      const hidesY = ["hidden", "clip"].includes(s.overflowY);
      if ((hidesX && el.scrollWidth > el.clientWidth + 1) || (hidesY && el.scrollHeight > el.clientHeight + 1)) {
        clipped.push({ tid: tid(el), tag: el.tagName, text: txt.slice(0, 60), sw: el.scrollWidth, cw: el.clientWidth, sh: el.scrollHeight, ch: el.clientHeight });
      }
      if (r.right > window.innerWidth + 1 || r.left < -1) {
        offRight.push({ tid: tid(el), tag: el.tagName, text: txt.slice(0, 60), left: Math.round(r.left), right: Math.round(r.right) });
      }
      if (s.textTransform === "uppercase") {
        labels.push({ tid: tid(el), text: txt.slice(0, 40), fontSize: s.fontSize, fontWeight: s.fontWeight, letterSpacing: s.letterSpacing, color: s.color });
      }
      if (HANGUL.test(txt)) korean.push({ tid: tid(el), tag: el.tagName, text: txt.slice(0, 80) });
    }
    for (const a of ["aria-label", "placeholder", "title", "alt"]) {
      const v = el.getAttribute(a);
      if (v && HANGUL.test(v)) korean.push({ tid: tid(el), tag: el.tagName, attr: a, text: v.slice(0, 80) });
    }
  }
  const box = (id) => {
    const el = document.querySelector(`[data-testid="${id}"]`);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { top: Math.round(r.top + window.scrollY), h: Math.round(r.height * 10) / 10, w: Math.round(r.width) };
  };
  return {
    url: location.pathname + location.search,
    innerWidth: window.innerWidth,
    scrollWidth: de.scrollWidth,
    clientWidth: de.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
    hOverflow: de.scrollWidth > de.clientWidth || document.body.scrollWidth > de.clientWidth,
    scrollY: Math.round(window.scrollY),
    docHeight: de.scrollHeight,
    hero: box("home-hero"),
    heroMode: document.querySelector('[data-testid="home-hero"]')?.getAttribute("data-mode") ?? null,
    progress: box("home-progress"),
    sessionPanel: box("session-panel"),
    clipped,
    offRight: offRight.slice(0, 20),
    labels,
    korean: korean.slice(0, 40),
    title: document.title,
  };
}

const results = existsSync(join(EVID, "measures.json")) ? JSON.parse(readFileSync(join(EVID, "measures.json"), "utf8")) : {};
const save = () => writeFileSync(join(EVID, "measures.json"), JSON.stringify(results, null, 1));

async function shot(page, scene, w, n, desc, extra = {}) {
  const file = `${scene}-${w}-${String(n).padStart(2, "0")}.jpg`;
  await page.screenshot({ path: join(SHOTS, file), type: "jpeg", quality: 70, fullPage: true });
  const m = await page.evaluate(measureInPage);
  results[scene] ??= {};
  results[scene][w] ??= [];
  results[scene][w] = results[scene][w].filter((s) => s.n !== n);
  results[scene][w].push({ n, desc, file, ...extra, m });
  results[scene][w].sort((a, b) => a.n - b.n);
  save();
  log(`${scene} ${w} #${n} ${desc} hOverflow=${m.hOverflow} hero=${m.hero?.h ?? "-"} prog=${m.progress?.h ?? "-"} clipped=${m.clipped.length} ko=${m.korean.length}`);
  return m;
}

const T = (id) => `[data-testid="${id}"]`;
async function home(page) {
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector(T("home-hero"), { timeout: 20000 });
  await page.waitForSelector(T("start-session"), { timeout: 20000 });
  await sleep(1500);
}
async function click(page, sel) {
  const loc = page.locator(sel).first();
  await loc.waitFor({ state: "visible", timeout: 15000 });
  await loc.click();
}

const SCENES = {
  // 1. 홈 대기
  async home_idle(page, w) {
    await home(page);
    await shot(page, "home_idle", w, 1, "홈 대기 — 첫 화면");
  },
  // 2. 홈 문장 연습
  async home_practice(page, w) {
    await home(page);
    await shot(page, "home_practice", w, 1, "Start speaking 누르기 전");
    await click(page, T("start-session"));
    await page.waitForSelector(T("practice-close"), { timeout: 20000 });
    await sleep(1500);
    await shot(page, "home_practice", w, 2, "Start speaking — 카드 안 문장 연습");
    const start = page.locator(T("course-start")).first();
    if (await start.isVisible().catch(() => false)) {
      await start.click();
      await sleep(2500);
      await shot(page, "home_practice", w, 3, "Start 누름 — 듣는 중");
      await sleep(6000);
      await shot(page, "home_practice", w, 4, "말한 뒤 결과 자리(가짜 마이크)");
    }
    const next = page.locator(T("course-next")).first();
    if (await next.isEnabled().catch(() => false)) {
      await next.click();
      await sleep(1200);
      await shot(page, "home_practice", w, 5, "Next — 다음 문장");
    }
    await click(page, T("practice-close"));
    await page.waitForSelector(T("start-session"), { timeout: 15000 });
    await sleep(800);
    await shot(page, "home_practice", w, 6, "← Close — 대기로 돌아옴");
  },
  // 3. Day 2 를 고른 연습
  async path_day2(page, w) {
    await home(page);
    const row = page.locator(T("path-day-2")).first();
    await row.scrollIntoViewIfNeeded();
    await sleep(500);
    await shot(page, "path_day2", w, 1, "Continue your path — Day 줄 목록");
    await row.click();
    await page.waitForSelector(T("practice-day"), { timeout: 20000 });
    await sleep(1500);
    const dayText = (await page.locator(T("practice-day")).first().textContent())?.trim();
    await shot(page, "path_day2", w, 2, "Day 2 고름 — 카드에서 연습이 열림", { dayText, url: new URL(page.url()).pathname });
    await click(page, T("practice-close"));
    await sleep(800);
  },
  // 4. View all 펼침
  async view_all(page, w) {
    await home(page);
    const before = await page.locator('[data-testid^="path-day-"]').count();
    const btn = page.locator(T("home-path-all")).first();
    await btn.scrollIntoViewIfNeeded();
    await sleep(400);
    await shot(page, "view_all", w, 1, "View all 누르기 전", { rows: before, label: (await btn.textContent())?.trim() });
    await btn.click();
    await sleep(1000);
    const after = await page.locator('[data-testid^="path-day-"]').count();
    await shot(page, "view_all", w, 2, "View all — 모든 Day 로 펼침", { rows: after, label: (await btn.textContent())?.trim(), url: new URL(page.url()).pathname });
    await btn.scrollIntoViewIfNeeded();
    await btn.click();
    await sleep(800);
    const back = await page.locator('[data-testid^="path-day-"]').count();
    await shot(page, "view_all", w, 3, "Show less — 다시 접음", { rows: back, label: (await btn.textContent())?.trim() });
  },
  // 5. 코치 세션 (Free talk 1개)
  async coach(page, w) {
    await home(page);
    const btn = page.locator(T("practice-free_talk")).first();
    await btn.scrollIntoViewIfNeeded();
    await sleep(400);
    await shot(page, "coach", w, 1, "More practice — Free talk 버튼");
    await btn.click();
    await page.waitForSelector(T("session-panel"), { timeout: 30000 });
    await sleep(2500);
    const lock = await page.evaluate(() => [...document.querySelectorAll('[data-locked="true"]')].length);
    await shot(page, "coach", w, 2, "세션 시작 — 카드 안 대화 화면", { lockedLinks: lock });
    await sleep(12000);
    await shot(page, "coach", w, 3, "코치 첫 발화 뒤(약 15초)");
    const end = page.locator(`${T("session-panel")} button`, { hasText: /end/i }).first();
    const endText = (await end.textContent().catch(() => null))?.trim();
    await end.click();
    await sleep(8000);
    await shot(page, "coach", w, 4, "End — 종료 뒤 화면", { endText });
    await sleep(15000);
    const idle = await page.locator(T("start-session")).count();
    await shot(page, "coach", w, 5, "종료 후 약 23초", { idleBack: idle > 0 });
  },
  // 6. 세션 실패(마이크 거부)
  async mic_denied(page, w, ctx) {
    const cdp = await ctx.browser.newBrowserCDPSession();
    const origin = APP;
    await cdp.send("Browser.setPermission", { permission: { name: "microphone" }, setting: "denied", origin });
    try {
      await home(page);
      const btn = page.locator(T("practice-free_talk")).first();
      await btn.scrollIntoViewIfNeeded();
      await btn.click();
      const failed = await page.waitForSelector(T("session-failed"), { timeout: 30000 }).then(() => true).catch(() => false);
      await sleep(1000);
      const failText = failed ? (await page.locator(T("session-failed")).first().innerText()).slice(0, 300) : null;
      await shot(page, "mic_denied", w, 1, "마이크 거부 — 실패 화면", { failed, failText });
      if (failed) {
        await click(page, T("session-failed-home"));
        await sleep(1200);
        await shot(page, "mic_denied", w, 2, "← Home — 대기로 돌아옴", { idleBack: (await page.locator(T("start-session")).count()) > 0 });
      }
    } finally {
      await cdp.send("Browser.setPermission", { permission: { name: "microphone" }, setting: "granted", origin });
      await cdp.detach();
    }
  },
  // 7. 기록
  async history(page, w) {
    await home(page);
    await click(page, T("home-history"));
    await page.waitForURL(/\/history$/, { timeout: 15000 });
    await sleep(2500);
    await shot(page, "history", w, 1, "Your progress → History — /history");
    const row = page.getByText("2026-11-01", { exact: false }).first();
    const before = page.url();
    await row.click().catch(() => {});
    await sleep(2000);
    await shot(page, "history", w, 2, "공부한 날(2026-11-01) 줄을 누름", { moved: page.url() !== before, url: new URL(page.url()).pathname, rowTag: await row.evaluate((e) => e.tagName + (e.closest("a,button") ? "/clickable" : "/plain")).catch(() => null) });
  },
  // 8. 주간
  async weekly(page, w) {
    await home(page);
    await click(page, T("home-weekly"));
    await page.waitForURL(/\/history\/weekly/, { timeout: 15000 });
    await sleep(2500);
    await shot(page, "weekly", w, 1, "Your progress → Weekly report — /history/weekly");
  },
  // 9. 결과
  async results(page, w) {
    const FIXED = "/results/7a18a111-2a62-4697-9ad8-a4b668fc0807";
    await page.goto(APP + FIXED, { waitUntil: "domcontentloaded" });
    await sleep(5000);
    await shot(page, "results", w, 2, "격리 DB 완료 세션(발화 26건) 결과 화면", { href: FIXED });
    await page.goto(APP + "/history", { waitUntil: "domcontentloaded" });
    await sleep(3000);
    let href = await page.locator('a[href^="/results/"]').first().getAttribute("href").catch(() => null);
    if (!href) {
      const days = page.locator('button, [role="button"], summary');
      log(`results: /history 에 결과 링크 없음 — 펼칠 거리 ${await days.count()}개`);
    }
    if (!href) {
      await shot(page, "results", w, 1, "/history — 결과 링크를 찾지 못함", { href: null });
      return;
    }
    await page.goto(APP + href, { waitUntil: "domcontentloaded" });
    await sleep(3500);
    await shot(page, "results", w, 1, `결과 화면 ${href}`, { href });
  },
  // 10. 코스 목록
  async course(page, w) {
    await page.goto(APP + "/course", { waitUntil: "domcontentloaded" });
    await sleep(3000);
    await shot(page, "course", w, 1, "코스 목록 /course(주소로만 닿음)");
  },
  // 11. Day 화면
  async course_day(page, w) {
    await page.goto(APP + "/course/1", { waitUntil: "domcontentloaded" });
    await sleep(4000);
    await shot(page, "course_day", w, 1, "Day 화면 /course/1 — 열기만 해도 진도 저장");
  },
  // 12. 영상 목록 · 13. 영상 화면
  async videos(page, w) {
    await home(page);
    const link = page.locator('a[href="/videos"]').first();
    const viaHome = await link.count();
    if (viaHome) {
      await link.scrollIntoViewIfNeeded();
      await link.click();
      await page.waitForURL(/\/videos$/, { timeout: 15000 });
    } else {
      await page.goto(APP + "/videos", { waitUntil: "domcontentloaded" });
    }
    await sleep(3000);
    await shot(page, "videos", w, 1, "영상 목록 /videos", { viaHome: viaHome > 0 });
    const v = await page.locator('a[href^="/videos/"]').first().getAttribute("href").catch(() => null);
    if (!v) return;
    await page.goto(APP + v, { waitUntil: "domcontentloaded" });
    await sleep(5000);
    await shot(page, "videos", w, 2, `영상 화면 ${v}`, { href: v });
  },
};

const browser = await chromium.connectOverCDP(CDP);
const ctx = { browser };
const context = browser.contexts()[0];
const names = ONLY.length ? ONLY : Object.keys(SCENES);
for (const name of names) {
  for (const { w, h } of WIDTHS) {
    const page = await context.newPage();
    await page.setViewportSize({ width: w, height: h });
    const errs = [];
    page.on("pageerror", (e) => errs.push(String(e).slice(0, 200)));
    page.on("console", (m) => {
      if (m.type() === "error") errs.push(m.text().slice(0, 200));
    });
    try {
      await SCENES[name](page, w, ctx);
    } catch (e) {
      log(`ERROR ${name} ${w}: ${String(e).split("\n")[0]}`);
      results[name] ??= {};
      results[name][`err-${w}`] = String(e).slice(0, 400);
      try {
        await page.screenshot({ path: join(SHOTS, `${name}-${w}-ERR.jpg`), type: "jpeg", quality: 60, fullPage: true });
      } catch {}
    }
    results[name] ??= {};
    results[name][`console-${w}`] = errs.slice(0, 10);
    save();
    await page.close();
  }
}
log("DONE");
process.exit(0);
