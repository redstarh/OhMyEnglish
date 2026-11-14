// 회차 b18 화면 탭 — 장면별 단계 스크린샷 + 배치 측정. 단일 명령: node runs/2026-11-14-b18/screens/shoot.mjs [장면…]
// ⛔ 브라우저는 띄우지 않고 호출자의 헤드리스 Chrome(:9461)에 붙음. 페이지만 열고 닫음.
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
const CDP = "http://127.0.0.1:9461";
const WIDTHS = [
  { w: 1400, h: 1000 },
  { w: 390, h: 844 },
];
const DONE_SESSION = "/results/7a18a111-2a62-4697-9ad8-a4b668fc0807"; // 격리 DB · 11-01 · 발화 있음(b16 과 같음)
const SILENT_SESSION = "/results/13869294-9b06-4c75-a56c-6529dcfa7971"; // 격리 DB · 11-14 · 발화 0건(db.py 조회)
const ONLY = process.argv.slice(2);
const LOG = join(EVID, "run.log");
const log = (m) => {
  const line = `${new Date().toISOString()} ${m}\n`;
  process.stdout.write(line);
  writeFileSync(LOG, line, { flag: "a" });
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// 가짜 인식기 — b17 live.mjs 의 installFakes 와 같음(각본 window.__srScript 대로 결과를 냄).
function installFakes() {
  const state = { calls: [], instances: 0, timers: [] };
  window.__sr = state;
  window.__srScript = [];
  class FakeRecognition {
    constructor() {
      state.instances += 1;
      this.segments = [];
      this.onresult = this.onerror = this.onend = this.onaudiostart = null;
      this.ended = false;
    }
    emit(text, isFinal) {
      this.segments = [...this.segments.filter((s) => s.isFinal), { text, isFinal }];
      const results = this.segments.map((s) => Object.assign([{ transcript: s.text }], { isFinal: s.isFinal }));
      this.onresult?.({ results, resultIndex: 0 });
    }
    end() {
      if (this.ended) return;
      this.ended = true;
      this.onend?.();
    }
    clear() {
      state.timers.forEach(clearTimeout);
      state.timers = [];
    }
    start() {
      state.calls.push(["start", Math.round(performance.now())]);
      state.timers.push(setTimeout(() => this.onaudiostart?.(), 100));
      for (const step of window.__srScript) {
        state.timers.push(
          setTimeout(() => {
            state.calls.push([step.type, Math.round(performance.now()), step.text ?? ""]);
            if (step.type === "interim") this.emit(step.text, false);
            else if (step.type === "final") this.emit(step.text, true);
            else if (step.type === "end") this.end();
          }, 100 + step.at),
        );
      }
    }
    stop() {
      state.calls.push(["stop", Math.round(performance.now())]);
      this.clear();
      const pending = this.segments.find((s) => !s.isFinal);
      setTimeout(() => {
        if (pending) this.emit(pending.text, true);
        this.end();
      }, 50);
    }
    abort() {
      state.calls.push(["abort", Math.round(performance.now())]);
      this.clear();
      setTimeout(() => {
        this.onerror?.({ error: "aborted" });
        this.end();
      }, 10);
    }
  }
  window.SpeechRecognition = FakeRecognition;
  window.webkitSpeechRecognition = FakeRecognition;
  if (window.speechSynthesis) {
    window.speechSynthesis.speak = (u) => {
      setTimeout(() => u.onstart?.(), 10);
      setTimeout(() => u.onend?.(), 300);
    };
    window.speechSynthesis.cancel = () => {};
  }
}

// 페이지 안에서 도는 측정 — 넘침 · 잘린 글자 · 카드 높이 · 대문자 라벨 · 한국어 · 주요 문구
function measureInPage() {
  const de = document.documentElement;
  const vis = (el) => {
    const s = getComputedStyle(el);
    if (s.display === "none" || s.visibility === "hidden" || Number(s.opacity) === 0) return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const tids = (el) => {
    const out = [];
    for (let e = el; e; e = e.parentElement) {
      const t = e.getAttribute && e.getAttribute("data-testid");
      if (t) out.push(t);
    }
    return out.slice(0, 4).join("<");
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
        clipped.push({ tid: tids(el), tag: el.tagName, text: txt.slice(0, 60), sw: el.scrollWidth, cw: el.clientWidth, sh: el.scrollHeight, ch: el.clientHeight });
      }
      if (r.right > window.innerWidth + 1 || r.left < -1) {
        offRight.push({ tid: tids(el), tag: el.tagName, text: txt.slice(0, 60), left: Math.round(r.left), right: Math.round(r.right) });
      }
      if (s.textTransform === "uppercase") {
        labels.push({ tid: tids(el), text: txt.slice(0, 40), fontSize: s.fontSize, fontWeight: s.fontWeight, letterSpacing: s.letterSpacing, color: s.color });
      }
      if (HANGUL.test(txt)) korean.push({ tid: tids(el), tag: el.tagName, text: txt.slice(0, 80) });
    }
    for (const a of ["aria-label", "placeholder", "title", "alt"]) {
      const v = el.getAttribute(a);
      if (v && HANGUL.test(v)) korean.push({ tid: tids(el), tag: el.tagName, attr: a, text: v.slice(0, 80) });
    }
  }
  // 넘침 상자 — iframe·img·video 처럼 글자 없는 큰 요소도 봄
  const wideMedia = [...document.querySelectorAll("iframe,img,video,canvas")]
    .filter(vis)
    .map((e) => ({ tag: e.tagName, right: Math.round(e.getBoundingClientRect().right) }))
    .filter((x) => x.right > window.innerWidth + 1);
  const box = (id) => {
    const el = document.querySelector(`[data-testid="${id}"]`);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { top: Math.round(r.top + window.scrollY), h: Math.round(r.height * 10) / 10, w: Math.round(r.width) };
  };
  const txt = (id) => {
    const el = document.querySelector(`[data-testid="${id}"]`);
    return el ? el.innerText.trim().replace(/\s+/g, " ").slice(0, 200) : null;
  };
  const font = (id) => {
    const el = document.querySelector(`[data-testid="${id}"]`);
    if (!el) return null;
    const s = getComputedStyle(el);
    return `${s.fontSize}/${s.fontWeight}/${s.fontFamily.split(",")[0]}`;
  };
  const TEXT_IDS = [
    "home-hero-title", "home-hero-day", "home-weekly-period", "home-course-progress", "home-week-days", "practice-day",
    "course-sentence-number", "course-sentence", "course-translation-text", "course-transcript", "course-live", "course-notice",
    "course-prev", "course-next", "practice-close", "results-status", "weekly-heading", "weekly-period", "history-not-analyzed-hint",
    "session-end",
  ];
  const texts = {};
  for (const id of TEXT_IDS) {
    const v = txt(id);
    if (v !== null) texts[id] = v;
  }
  const hero = document.querySelector('[data-testid="home-hero"]');
  return {
    url: location.pathname + location.search,
    innerWidth: window.innerWidth,
    scrollWidth: de.scrollWidth,
    clientWidth: de.clientWidth,
    bodyScrollWidth: document.body.scrollWidth,
    hOverflow: document.body.scrollWidth > window.innerWidth || offRight.length > 0 || wideMedia.length > 0,
    scrollY: Math.round(window.scrollY),
    docHeight: de.scrollHeight,
    hero: box("home-hero"),
    heroMode: hero?.getAttribute("data-mode") ?? null,
    progress: box("home-progress"),
    courseCard: box("course-card"),
    sessionPanel: box("session-panel"),
    fonts: { sentence: font("course-sentence"), transcript: font("course-transcript"), live: font("course-live"), translation: font("course-translation-text") },
    koPressed: document.querySelector('[data-testid="course-translation"]')?.getAttribute("aria-pressed") ?? null,
    texts,
    clipped,
    offRight: offRight.slice(0, 20),
    wideMedia,
    labels,
    korean: korean.slice(0, 60),
    buttons: [...document.querySelectorAll("a.omy-button,button.omy-button")].filter(vis).map((b) => b.innerText.trim().slice(0, 30)),
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
  results[scene][w].push({ n, desc, file, at: new Date().toISOString(), ...extra, m });
  results[scene][w].sort((a, b) => a.n - b.n);
  save();
  log(`${scene} ${w} #${n} ${desc} over=${m.hOverflow}(${m.bodyScrollWidth}) hero=${m.hero?.h ?? "-"}(${m.heroMode}) card=${m.courseCard?.h ?? "-"} clip=${m.clipped.length} ko=${m.korean.length}`);
  return m;
}

const T = (id) => `[data-testid="${id}"]`;
const path = (page) => new URL(page.url()).pathname;
// 홈을 열고 KO·모드 저장값을 처음 값으로 돌림(앞 장면의 토글이 남지 않게).
async function home(page, { ko = false } = {}) {
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.evaluate((on) => {
    localStorage.removeItem("omy.course.mode");
    localStorage.setItem("omy.course.translation", on ? "on" : "off");
  }, ko);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.waitForSelector(T("home-hero"), { timeout: 20000 });
  await page.waitForSelector(T("start-session"), { timeout: 20000 });
  await sleep(1500);
}
async function click(page, sel) {
  const loc = page.locator(sel).first();
  await loc.waitFor({ state: "visible", timeout: 15000 });
  await loc.click();
}
const phase = (page) => page.evaluate(() => document.querySelector('[data-testid="course-phase"]')?.dataset.phase ?? "idle");

const SCENES = {
  // 1. 홈 대기 — KO 끔과 KO 켬(대기 카드 높이도 KO 를 따라야 함)
  async home_idle(page, w) {
    await home(page);
    await shot(page, "home_idle", w, 1, "홈 대기 — 첫 화면(KO 끔)");
    await home(page, { ko: true });
    await shot(page, "home_idle", w, 2, "홈 대기 — KO 켬으로 저장된 상태");
  },
  // 2. 홈 문장 연습 — KO 끔 → KO 켬 → 실시간 표시 → 결과 → Next → ← Previous → ← Close
  async home_practice(page, w) {
    await page.addInitScript(installFakes);
    await home(page);
    const y0 = await page.evaluate(() => Math.round(window.scrollY));
    await click(page, T("start-session"));
    await page.waitForSelector(T("practice-close"), { timeout: 20000 });
    await page.waitForSelector(`${T("course-start")}, ${T("course-retry")}`, { timeout: 20000 });
    await click(page, T("course-mode-manual"));
    await sleep(1200);
    await shot(page, "home_practice", w, 1, "Start speaking — 카드 안 문장 연습(KO 끔 · Manual)", { scrollYBefore: y0 });
    await click(page, T("course-translation"));
    await sleep(800);
    await shot(page, "home_practice", w, 2, "KO 켬 — 문장 아래 한국어 번역");
    const sentence = (await page.locator(T("course-sentence")).first().innerText()).trim();
    const words = sentence.split(/\s+/);
    const plain = sentence.replace(/[.,!?]/g, "");
    await page.evaluate(
      (s) => (window.__srScript = s),
      [
        { at: 300, type: "interim", text: words.slice(0, 2).join(" ") },
        { at: 1500, type: "interim", text: words.slice(0, Math.max(3, Math.ceil(words.length / 2))).join(" ") },
        { at: 4500, type: "final", text: plain },
      ],
    );
    await click(page, T("course-start"));
    await page.waitForSelector(T("course-live-interim"), { timeout: 10000 });
    await sleep(1600);
    await shot(page, "home_practice", w, 3, "Start — 말하는 동안 실시간 표시(가짜 인식기)", { sentence });
    await page.waitForFunction(() => document.querySelector('[data-testid="course-phase"]')?.dataset.phase === "done", null, { timeout: 30000 });
    await sleep(600);
    await shot(page, "home_practice", w, 4, "판정 결과 — 말한 내용(문장과 같은 글자)", { phase: await phase(page) });
    await click(page, T("course-next"));
    await sleep(1000);
    await shot(page, "home_practice", w, 5, "Next → — 다음 문장");
    await click(page, T("course-prev"));
    await sleep(1000);
    await shot(page, "home_practice", w, 6, "← Previous — 앞 문장으로 돌아옴");
    await click(page, T("practice-close"));
    await page.waitForSelector(T("start-session"), { timeout: 15000 });
    await sleep(800);
    await shot(page, "home_practice", w, 7, "← Close — 대기로 돌아옴(KO 켬 유지)");
  },
  // 3. Day 2 를 고른 연습
  async path_day2(page, w) {
    await home(page);
    const row = page.locator(T("path-day-2")).first();
    await row.scrollIntoViewIfNeeded();
    await sleep(500);
    const y1 = await page.evaluate(() => Math.round(window.scrollY));
    await shot(page, "path_day2", w, 1, "Continue your path — Day 줄 목록");
    await row.click();
    await page.waitForSelector(T("practice-day"), { timeout: 20000 });
    await sleep(1500);
    const dayText = (await page.locator(T("practice-day")).first().textContent())?.trim();
    await shot(page, "path_day2", w, 2, "Day 2 고름 — 카드에서 연습이 열림", { dayText, url: path(page), scrollYBefore: y1 });
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
    const statuses = await page.locator('[data-testid^="path-day-"]').evaluateAll((els) => els.map((e) => e.innerText.replace(/\s+/g, " ").trim().slice(0, 80)));
    await shot(page, "view_all", w, 2, "View all — 모든 Day 로 펼침", { rows: after, label: (await btn.textContent())?.trim(), url: path(page), statuses });
    await btn.scrollIntoViewIfNeeded();
    await btn.click();
    await sleep(800);
    const back = await page.locator('[data-testid^="path-day-"]').count();
    await shot(page, "view_all", w, 3, "Show less — 다시 접음", { rows: back, label: (await btn.textContent())?.trim() });
  },
  // 5. 코치 세션 (Free talk 1개) → End → 결과(발화 없는 세션) → Start again
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
    await sleep(10000);
    await shot(page, "coach", w, 3, "약 12초 뒤");
    await click(page, T("session-end"));
    await page.waitForURL(/\/results\//, { timeout: 30000 }).catch(() => {});
    await sleep(6000);
    const sessionUrl = path(page);
    await shot(page, "coach", w, 4, "End lesson — 결과 화면", { sessionUrl });
    const again = page.locator(T("results-start-again"));
    if (await again.count()) {
      await again.first().click();
      await page.waitForURL((u) => u.pathname === "/", { timeout: 15000 }).catch(() => {});
      await sleep(1500);
      await shot(page, "coach", w, 5, "Start again → — 홈으로", { url: path(page) });
    }
  },
  // 6. 기록 — 날짜 줄(세션 하나 → 결과 · 여럿 → 펼쳐 고름)
  async history(page, w) {
    await home(page);
    await click(page, T("home-history"));
    await page.waitForURL(/\/history$/, { timeout: 15000 });
    await sleep(2500);
    const links = await page.locator(T("history-day-link")).count();
    const groups = await page.locator(T("history-day-group")).count();
    await shot(page, "history", w, 1, "Your progress → History — /history", { links, groups });
    if (links) {
      const l = page.locator(T("history-day-link")).first();
      const label = (await l.innerText()).replace(/\s+/g, " ").trim();
      await l.scrollIntoViewIfNeeded();
      await l.click();
      await page.waitForURL(/\/results\//, { timeout: 15000 }).catch(() => {});
      await sleep(4000);
      await shot(page, "history", w, 2, "세션 하나인 날짜 줄 → 그 결과", { label, url: path(page) });
      await page.goBack({ waitUntil: "domcontentloaded" });
      await sleep(2500);
    }
    if (groups) {
      const g = page.locator(T("history-day-group")).first();
      await g.scrollIntoViewIfNeeded();
      const label = (await g.locator("summary").first().innerText()).replace(/\s+/g, " ").trim();
      await g.locator("summary").first().click();
      await sleep(800);
      const inner = await g.locator(T("history-session-link")).count();
      await shot(page, "history", w, 3, "세션 여럿인 날짜 줄 → 펼쳐 세션 목록", { label, sessionLinks: inner });
      if (inner) {
        await g.locator(T("history-session-link")).first().click();
        await page.waitForURL(/\/results\//, { timeout: 15000 }).catch(() => {});
        await sleep(4000);
        await shot(page, "history", w, 4, "펼친 목록의 세션 → 그 결과", { url: path(page) });
      }
    }
  },
  // 7. 주간
  async weekly(page, w) {
    await home(page);
    await click(page, T("home-weekly"));
    await page.waitForURL(/\/history\/weekly/, { timeout: 15000 });
    await sleep(2500);
    await shot(page, "weekly", w, 1, "Your progress → Weekly report — /history/weekly");
    await click(page, T("weekly-home"));
    await page.waitForURL((u) => u.pathname === "/", { timeout: 15000 }).catch(() => {});
    await sleep(1500);
    await shot(page, "weekly", w, 2, "← Home — 홈으로", { url: path(page) });
  },
  // 8. 결과 — 지난 완료 세션 · 발화 없는 세션
  async results(page, w) {
    await page.goto(APP + DONE_SESSION, { waitUntil: "domcontentloaded" });
    await sleep(5000);
    await shot(page, "results", w, 1, "지난 완료 세션(11-01 · 발화 있음)", { href: DONE_SESSION });
    await page.goto(APP + SILENT_SESSION, { waitUntil: "domcontentloaded" });
    await sleep(5000);
    await shot(page, "results", w, 2, "발화 없는 세션(11-14 · 발화 0건)", { href: SILENT_SESSION });
  },
  // 9. /course · /course/1 리다이렉트
  async course(page, w) {
    await page.goto(APP + "/course", { waitUntil: "domcontentloaded" });
    await page.waitForURL((u) => u.pathname === "/", { timeout: 15000 }).catch(() => {});
    await sleep(2500);
    await shot(page, "course", w, 1, "/course 를 주소로 엶 → 홈", { from: "/course", url: path(page) });
    await page.goto(APP + "/course/1", { waitUntil: "domcontentloaded" });
    await page.waitForURL((u) => u.pathname === "/", { timeout: 15000 }).catch(() => {});
    await sleep(2500);
    await shot(page, "course", w, 2, "/course/1 을 주소로 엶 → 홈", { from: "/course/1", url: path(page) });
  },
  // 10. 영상 목록 · 영상 화면
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
    await shot(page, "videos", w, 1, "Learn with videos → 영상 목록 /videos", { viaHome: viaHome > 0 });
    const v = await page.locator('a[href^="/videos/"]').first().getAttribute("href", { timeout: 5000 }).catch(() => null);
    if (!v) return;
    await page.goto(APP + v, { waitUntil: "domcontentloaded" });
    await sleep(5000);
    await shot(page, "videos", w, 2, `영상 화면 ${v}`, { href: v });
  },
};

const browser = await chromium.connectOverCDP(CDP);
const context = browser.contexts()[0];
await context.grantPermissions(["microphone"], { origin: APP });
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
      await SCENES[name](page, w);
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
