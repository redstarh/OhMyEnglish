// 회차 b22 화면 확인 — TASK-335(This week 기준) · TASK-337(320 폭 결과 자리). 실행: node check.mjs [label]
// ⛔ 쓰기 요청(POST·PUT·PATCH·DELETE)은 모두 context.route 로 막고 가짜로 답함 — dev DB 에 쓰지 않음.
// ⛔ 코치 세션 소켓(/ws/session)은 routeWebSocket 으로 받아 서버에 잇지 않고 바로 닫음 — Nova 세션을 열지 않음.
// 가짜 인식기 · 판정은 b21 check333-longest.mjs 에서 옮겨 옴.
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const EVIDENCE = join(HERE, "evidence");
mkdirSync(EVIDENCE, { recursive: true });
const LABEL = process.argv[2] ?? "after";
const APP = "http://localhost:3000";
const API = "http://localhost:8002";
const T = (id) => `[data-testid="${id}"]`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const results = [];
const blocked = [];
const sockets = [];
function verdict(item, width, ok, detail) {
  results.push({ item, width, ok, detail });
  console.log(`${ok ? "PASS" : ok === null ? "INFO" : "FAIL"} ${item} @${width} ${JSON.stringify(detail)}`);
}

// 가짜 인식기 — b18 shoot.mjs 의 installFakes 를 줄인 것(각본 window.__srScript 대로 결과를 냄).
function installFakes() {
  const state = { timers: [] };
  window.__srScript = [];
  class FakeRecognition {
    constructor() {
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
    start() {
      state.timers.push(setTimeout(() => this.onaudiostart?.(), 100));
      for (const step of window.__srScript) {
        state.timers.push(
          setTimeout(() => {
            if (step.type === "final") this.emit(step.text, true);
            else if (step.type === "end") this.end();
          }, 100 + step.at),
        );
      }
    }
    stop() {
      state.timers.forEach(clearTimeout);
      setTimeout(() => this.end(), 50);
    }
    abort() {
      state.timers.forEach(clearTimeout);
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

// 문장 연습 판정의 가짜 답 — 모드는 차례마다 바꿈(all · some).
let attemptMode = "all";
let currentSentence = "";
function fakeAttempt(sentence) {
  const words = sentence.replace(/[.,!?]/g, "").split(/\s+/).filter(Boolean);
  if (attemptMode === "all") {
    return { transcript: sentence, words: words.map((word) => ({ word, verdict: "match" })), attempts: 1 };
  }
  return {
    transcript: words.slice(0, -1).join(" ").replace(words[1], "big"),
    words: words.map((word, i) => ({ word, verdict: i === 1 ? "different" : i === words.length - 1 ? "missing" : "match" })),
    attempts: 1,
  };
}

async function guard(context) {
  await context.route("**/*", async (route) => {
    const req = route.request();
    const method = req.method();
    if (["GET", "HEAD", "OPTIONS"].includes(method)) return route.fallback();
    blocked.push(`${method} ${req.url()}`);
    if (/\/api\/course\/sentences\/[^/]+\/attempts/.test(req.url())) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(fakeAttempt(currentSentence)) });
    }
    return route.fulfill({ status: 204, body: "" });
  });
  await context.routeWebSocket(/\/ws\/session/, (ws) => {
    sockets.push(ws.url());
    ws.close();
  });
}

async function shot(page, name, el) {
  const path = join(EVIDENCE, `${name}.png`);
  if (el) await page.locator(el).first().screenshot({ path });
  else await page.screenshot({ path, fullPage: true });
  return `evidence/${name}.png`;
}
const json = (route, body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
const heroHeight = (page) => page.locator(T("home-hero")).evaluate((e) => e.getBoundingClientRect().height);

// ── TASK-335 ──
const hDay = (day, learned, spoken) => ({
  day, learned, completed_scenarios: learned ? 1 : 0, analyzed: false, occurrence_count: 0, pattern_count: 0, sessions: [],
  ...(spoken === undefined ? {} : { spoken }),
});
async function weekText(page) {
  await page.goto(`${APP}/`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelector('[data-testid="home-week-days"]')?.dataset.state === "ready", null, { timeout: 20000 });
  return (await page.locator(T("home-week-days")).innerText()).trim();
}
async function check335(page, w) {
  const real = await (await fetch(`${API}/api/history`)).json();
  const recent = [...real.days].sort((a, b) => (a.day < b.day ? 1 : -1)).slice(0, 7);
  const want = recent.filter((d) => d.learned && d.spoken !== false).length;
  const realText = await weekText(page);
  verdict("335-real", w, realText === `This week: ${want} / ${recent.length} days`, {
    text: realText, want, recent: recent.map((d) => [d.day, d.learned, d.spoken]), shot: await shot(page, `335-real-${LABEL}-${w}`, T("home-progress")),
  });
  // 가짜 — 마쳤지만 말하지 않은 날 2 · 말한 날 1 · 안 한 날 4.
  const days = [hDay("2026-11-15", true, false), hDay("2026-11-14", true, true), hDay("2026-11-13", true, false)];
  for (let d = 12; d >= 9; d -= 1) days.push(hDay(`2026-11-${d}`, false, false));
  await page.route(`${API}/api/history`, (route) => json(route, { streak: { current: 1, longest: 1, today_done: false }, days }));
  const fakeText = await weekText(page);
  verdict("335-fake", w, fakeText === "This week: 1 / 7 days", { text: fakeText, shot: await shot(page, `335-fake-${LABEL}-${w}`, T("home-progress")) });
  await page.unroute(`${API}/api/history`);
}

// ── TASK-337 ──
const LONGEST = "We deploy on Fridays. This week we are deploying on Thursday.";
async function slotFacts(page) {
  return page.evaluate(() => {
    const q = (s) => document.querySelector(`[data-testid="${s}"]`);
    const slot = q("course-result-slot");
    const card = q("course-card");
    const cs = getComputedStyle(card);
    return {
      slotClient: slot.clientHeight,
      slotScroll: slot.scrollHeight,
      fits: slot.scrollHeight <= slot.clientHeight + 1,
      slotFont: getComputedStyle(slot).fontSize,
      cardContentWidth: card.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight),
      cardHeight: card.getBoundingClientRect().height,
    };
  });
}
async function check337(page, w) {
  await page.goto(`${APP}/`, { waitUntil: "networkidle" });
  await page.waitForSelector(T("home-hero"), { timeout: 20000 });
  await sleep(500);
  const waiting = await heroHeight(page);
  await page.locator(T("start-session")).click();
  await page.waitForSelector(`${T("course-start")}, ${T("course-retry")}`, { timeout: 20000 });
  await page.locator(T("course-mode-manual")).click().catch(() => {});
  await sleep(800);
  const states = { waiting, idle: await heroHeight(page) };
  const idleFacts = await slotFacts(page);
  const facts = { idle: idleFacts };
  for (const mode of ["all", "some"]) {
    attemptMode = mode;
    currentSentence = (await page.locator(T("course-sentence")).innerText()).trim();
    const plain = currentSentence.replace(/[.,!?]/g, "");
    await page.evaluate((s) => (window.__srScript = s), [{ at: 600, type: "final", text: plain }]);
    await page.locator(`${T("course-start")}, ${T("course-retry")}`).first().click();
    await sleep(300);
    states[`${mode}-listening`] = await heroHeight(page);
    await page.waitForFunction(() => document.querySelector('[data-testid="course-phase"]')?.dataset.phase === "done", null, { timeout: 30000 });
    await sleep(500);
    states[`${mode}-done`] = await heroHeight(page);
    facts[mode] = await slotFacts(page);
    await shot(page, `337-${mode}-${LABEL}-${w}`, T("home-hero"));
    if (mode === "all") {
      await page.locator(T("course-next")).click();
      await sleep(800);
      states.next = await heroHeight(page);
    }
  }
  const heights = Object.values(states).slice(1);
  const fixed = heights.every((h) => Math.abs(h - heights[0]) < 0.5);
  verdict("337-slot-fits", w, facts.some.fits && facts.all.fits, { some: facts.some, all: facts.all });
  verdict("337-card-fixed", w, fixed, { states });
  await page.locator(T("practice-close")).click();
  await sleep(500);
}

const browser = await chromium.connectOverCDP("http://127.0.0.1:9480");
for (const [w, h] of [[1400, 1000], [390, 844], [320, 700]]) {
  const context = await browser.newContext({ viewport: { width: w, height: h }, permissions: ["microphone"] });
  await guard(context);
  await context.addInitScript(installFakes);
  await context.route(/localhost:8002\/api\/course\/days\/\d+$/, async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    for (const unit of body.units) for (const item of unit.sentences) item.text = LONGEST;
    return route.fulfill({ response, json: body });
  });
  const page = await context.newPage();
  for (const [name, fn] of [["335", check335], ["337", check337]]) {
    try {
      await fn(page, w);
    } catch (err) {
      verdict(`${name}-error`, w, false, { error: String(err).slice(0, 400) });
    }
  }
  await shot(page, `home-${LABEL}-${w}`);
  await context.close();
}
await browser.close().catch(() => {});
writeFileSync(join(EVIDENCE, `results-${LABEL}.json`), JSON.stringify({ results, blocked, sockets }, null, 2));
console.log(`blocked writes: ${blocked.length} · sockets: ${sockets.length}`);
console.log(`pass ${results.filter((r) => r.ok === true).length} · fail ${results.filter((r) => r.ok === false).length}`);
