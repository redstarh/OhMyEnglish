// TASK-332 · TASK-333 화면 확인 — 1400 · 390. 실행: node check333.mjs (Chrome 이 CDP :9470 에 떠 있어야 함)
// ⛔ 쓰기 요청(POST·PUT·PATCH·DELETE)은 모두 page.route 로 막고 가짜로 답함 — dev DB 에 쓰지 않음.
// ⛔ 코치 세션 소켓(/ws/session)은 routeWebSocket 으로 가짜로 받음 — 실제 Nova 세션을 열지 않음.
// ⚠️ 살아 있는 백엔드는 --reload 가 없어 새 필드(history.days[].spoken · results.entry)를 아직 싣지 않음 →
//    그 두 갈래는 page.route 로 가짜 응답을 줌(그 사실을 결과에 적음).
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const EVIDENCE = join(HERE, "evidence");
mkdirSync(EVIDENCE, { recursive: true });
const APP = "http://localhost:3000";
const API = "http://localhost:8002";
const T = (id) => `[data-testid="${id}"]`;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const results = [];
const blocked = [];
const sockets = [];
function verdict(item, width, ok, detail) {
  results.push({ item, width, ok, detail });
  console.log(`${ok ? "PASS" : ok === null ? "SKIP" : "FAIL"} ${item} @${width} ${JSON.stringify(detail)}`);
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
  // ⛔ 모든 쓰기를 막음. 판정 요청만 가짜 판정으로, 나머지는 빈 성공으로 답함.
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
    // 서버에 잇지 않음 — 세션 시작 사건만 보냄.
    ws.onMessage(() => {});
    setTimeout(() => ws.send(JSON.stringify({ type: "session_started", session_id: "fake-333" })), 200);
  });
  await context.route("https://www.youtube.com/oembed**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ title: "Fake preview", author_name: "Fake channel" }) }),
  );
}

async function shot(page, name, el) {
  const path = join(EVIDENCE, `${name}.png`);
  if (el) await page.locator(el).first().screenshot({ path });
  else await page.screenshot({ path, fullPage: true });
  return `evidence/${name}.png`;
}

const json = (route, body) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });

async function checkHome(page, w) {
  await page.goto(`${APP}/`, { waitUntil: "networkidle" });
  await page.waitForSelector(T("stat-best-streak"), { timeout: 20000 });
  await sleep(600);
  const n1 = await page.evaluate(() => {
    const q = (s) => document.querySelector(`[data-testid="${s}"]`);
    const best = q("stat-best-streak");
    const stats = q("home-weekly-stats");
    const period = q("home-weekly-period");
    const br = best.getBoundingClientRect();
    const pr = period?.getBoundingClientRect();
    return {
      best: best.textContent,
      insideWeeklyStats: stats.contains(best),
      underCaption: stats.querySelectorAll('[data-testid^="stat-"]').length,
      caption: period?.textContent ?? null,
      bestAboveCaption: pr ? br.bottom <= pr.top : null,
      bestRow: [...best.parentElement.children].map((e) => e.textContent),
    };
  });
  const s1 = await shot(page, `N1-progress-${w}`, T("home-progress"));
  verdict("N1", w, !n1.insideWeeklyStats && n1.underCaption === 2 && n1.bestAboveCaption === true, { ...n1, shot: s1 });
  await shot(page, `home-${w}`);
}

async function checkPractice(page, w) {
  await page.goto(`${APP}/`, { waitUntil: "networkidle" });
  await page.locator(T("start-session")).click();
  await page.waitForSelector(`${T("course-start")}, ${T("course-retry")}`, { timeout: 20000 });
  await page.locator(T("course-mode-manual")).click().catch(() => {});
  await sleep(800);
  const ko = await page.locator(T("course-translation")).getAttribute("title");
  verdict("X3", w, ko === "Show Korean translation", { title: ko, shot: await shot(page, `X3-ko-${w}`, T("home-hero")) });
  const heightBefore = await page.locator(T("home-hero")).evaluate((e) => e.getBoundingClientRect().height);
  for (const mode of ["all", "some"]) {
    attemptMode = mode;
    currentSentence = (await page.locator(T("course-sentence")).innerText()).trim();
    const plain = currentSentence.replace(/[.,!?]/g, "");
    await page.evaluate((s) => (window.__srScript = s), [{ at: 600, type: "final", text: plain }]);
    await page.locator(`${T("course-start")}, ${T("course-retry")}`).first().click();
    await page.waitForFunction(() => document.querySelector('[data-testid="course-phase"]')?.dataset.phase === "done", null, { timeout: 30000 });
    await sleep(500);
    const m = await page.evaluate(() => {
      const q = (s) => document.querySelector(`[data-testid="${s}"]`);
      const slot = q("course-result-slot");
      const spoken = q("course-spoken");
      const verdictLine = spoken?.querySelector("[data-verdict]")?.parentElement;
      return {
        allMatchedAttr: spoken?.dataset.allMatched,
        allMatchedText: q("course-all-matched")?.textContent ?? null,
        verdictLineHidden: verdictLine ? verdictLine.hidden : null,
        verdictLineText: verdictLine && !verdictLine.hidden ? verdictLine.innerText.split("\n")[0] : null,
        verdictSpans: spoken ? spoken.querySelectorAll("[data-verdict]").length : 0,
        slotFits: slot.scrollHeight <= slot.clientHeight + 1,
        slotScroll: slot.scrollHeight,
        slotClient: slot.clientHeight,
      };
    });
    const heightAfter = await page.locator(T("home-hero")).evaluate((e) => e.getBoundingClientRect().height);
    const sameHeight = Math.abs(heightAfter - heightBefore) < 0.5;
    const ok =
      mode === "all"
        ? m.allMatchedText === "All words matched" && m.verdictLineHidden === true && m.verdictSpans > 0
        : m.allMatchedText === null && m.verdictLineHidden === false && (m.verdictLineText ?? "").startsWith("Sentence:");
    verdict(`N2-${mode}`, w, ok && m.slotFits && sameHeight, {
      ...m,
      sentence: currentSentence,
      heightBefore,
      heightAfter,
      shot: await shot(page, `N2-${mode}-${w}`, T("home-hero")),
    });
    await page.locator(T("course-next")).click();
    await sleep(800);
  }
  await page.locator(T("practice-close")).click();
  await sleep(800);
}

async function checkCoach(page, w) {
  for (const [key, label] of [
    ["practice-free_talk", "Free talk"],
    ["practice-weak_patterns", "Weak spots"],
    ["focus-practice", "Practice a pattern"],
  ]) {
    await page.goto(`${APP}/`, { waitUntil: "networkidle" });
    const btn = page.locator(T(key)).first();
    if (await btn.isDisabled()) {
      verdict(`N3-${label}`, w, null, { note: "버튼이 꺼져 있음(데이터 없음)" });
      continue;
    }
    await btn.click();
    await page.waitForSelector(T("session-title"), { timeout: 20000 });
    const title = (await page.locator(T("session-title")).innerText()).trim();
    const shotPath = await shot(page, `N3-${key}-${w}`, T("home-hero"));
    verdict(`N3-${label}`, w, title === label, { title, socket: sockets.at(-1), shot: shotPath });
  }
}

const noSpeech = (entry) => ({
  status: "no_utterances",
  partial_failure: false,
  pronunciation: [],
  awaiting_analysis: false,
  summary: { went_well: [], weak_points: [] },
  session_date: "2026-11-14",
  finished: true,
  ...(entry ? { entry } : {}),
});

async function checkResults(page, w) {
  // 실제 서버(옛 판 · entry 없음) — 홈으로 가야 함.
  const real = "2a9cbf0f-5920-4c2a-8594-654a4504563e";
  await page.goto(`${APP}/results/${real}`, { waitUntil: "networkidle" });
  await page.waitForSelector(T("results-start-again"), { timeout: 20000 });
  const realHref = await page.locator(T("results-start-again")).getAttribute("href");
  verdict("N4-old-server", w, realHref === "/", { href: realHref, shot: await shot(page, `N4-old-${w}`) });

  // 가짜 entry — Free talk · 쉐도잉.
  const cases = [
    ["speaking", { mode: "speaking", source: "additional", item: null, pattern: null }, "/?mode=speaking&source=additional"],
    [
      "shadowing",
      { mode: "shadowing", source: "additional", item: "c0ffee00-0000-0000-0000-000000000333", pattern: null },
      "/?mode=shadowing&source=additional&item=c0ffee00-0000-0000-0000-000000000333",
    ],
  ];
  for (const [name, entry, want] of cases) {
    const id = `00000000-0000-0000-0000-00000000033${name === "speaking" ? 1 : 2}`;
    await page.route(`${API}/api/sessions/${id}/results`, (route) => json(route, noSpeech(entry)));
    await page.goto(`${APP}/results/${id}`, { waitUntil: "networkidle" });
    await page.waitForSelector(T("results-start-again"), { timeout: 20000 });
    const href = await page.locator(T("results-start-again")).getAttribute("href");
    const text = await page.locator("main").innerText();
    const homeLinks = await page.locator(T("results-home")).count();
    const shotPath = await shot(page, `N4-${name}-${w}`);
    verdict(`N4-href-${name}`, w, href === want && text.includes("Check your microphone, then start again."), { href, homeLinks, shot: shotPath });
    if (name === "speaking") {
      const before = sockets.length;
      await page.locator(T("results-start-again")).click();
      await page.waitForSelector(T("session-title"), { timeout: 20000 });
      const title = (await page.locator(T("session-title")).innerText()).trim();
      const socket = sockets.slice(before).at(-1) ?? null;
      verdict("N4-reopens", w, title === "Free talk" && /mode=speaking/.test(socket ?? "") && /source=additional/.test(socket ?? ""), {
        title,
        socket,
        url: page.url(),
        shot: await shot(page, `N4-reopened-${w}`, T("home-hero")),
      });
    }
  }

  // N7 — 지난 세션 · 드릴 미달.
  const n7 = "00000000-0000-0000-0000-000000000337";
  await page.route(`${API}/api/sessions/${n7}/results`, (route) =>
    json(route, {
      status: "final",
      partial_failure: false,
      pronunciation: [],
      awaiting_analysis: false,
      corrections: [],
      drill: { exchanges_observed: 3, exchanges_expected: 6 },
      summary: { went_well: [], weak_points: [] },
      session_date: "2026-11-01",
      finished: true,
    }),
  );
  await page.goto(`${APP}/results/${n7}`, { waitUntil: "networkidle" });
  await page.waitForSelector(T("results-status"), { timeout: 20000 });
  const t7 = await page.locator("main").innerText();
  verdict("N7", w, t7.includes("This drill was shorter than planned.") && !t7.includes("Today's drill"), { shot: await shot(page, `N7-${w}`) });
}

const hDay = (day, learned, extra = {}) => ({
  day,
  learned,
  completed_scenarios: learned ? 1 : 0,
  analyzed: false,
  occurrence_count: 0,
  pattern_count: 0,
  sessions: [],
  ...extra,
});

async function checkHistory(page, w) {
  // 실제 서버 — N8 접힘(spoken 키 없음 → 옛 문구).
  await page.goto(`${APP}/history`, { waitUntil: "networkidle" });
  await page.waitForSelector(T("history-weekly"), { timeout: 20000 });
  await sleep(400);
  const real = await page.evaluate(() => ({
    gaps: [...document.querySelectorAll('[data-testid="history-gap"]')].map((e) => e.textContent),
  }));
  verdict("N8-real", w, real.gaps.length >= 1 && real.gaps.every((g) => g.startsWith("No study · ")), { ...real, shot: await shot(page, `N8-real-${w}`) });

  // 가짜 history — spoken 거짓인 날 · 참인 날 · 빈 날 구간.
  const days = [hDay("2026-11-14", true, { spoken: false, sessions: [{ session_id: "a", title: "Free talk A" }, { session_id: "b", title: "Free talk B" }] })];
  for (let d = 13; d >= 2; d -= 1) days.push(hDay(`2026-11-${String(d).padStart(2, "0")}`, false, { spoken: false }));
  days.push(hDay("2026-11-01", true, { spoken: true, sessions: [{ session_id: "c", title: "Weekend plans" }] }));
  days.push(hDay("2026-10-31", false, { spoken: false }));
  await page.route(`${API}/api/history`, (route) => json(route, { streak: { current: 0, longest: 1, today_done: false }, days }));
  await page.goto(`${APP}/history`, { waitUntil: "networkidle" });
  await page.waitForSelector(T("history-gap"), { timeout: 20000 });
  const fake = await page.evaluate(() => {
    const groups = [...document.querySelectorAll('[data-testid="history-day-group"] summary, [data-testid="history-day-link"]')];
    return {
      rowFacts: groups.map((e) => (e.closest("div, details")?.innerText ?? e.innerText).replace(/\s+/g, " ").trim()),
      gaps: [...document.querySelectorAll('[data-testid="history-gap"]')].map((e) => e.textContent),
      hint: !!document.querySelector('[data-testid="history-not-analyzed-hint"]'),
    };
  });
  const said = fake.rowFacts.find((t) => t.startsWith("2026-11-14")) ?? "";
  const other = fake.rowFacts.find((t) => t.startsWith("2026-11-01")) ?? "";
  verdict("N5-nothing-said", w, said.includes("Nothing said") && other.includes("Not analyzed yet") && fake.hint, {
    said,
    other,
    hint: fake.hint,
    shot: await shot(page, `N5-N8-fake-${w}`),
  });
  verdict("N8-fake", w, JSON.stringify(fake.gaps) === JSON.stringify(["No study · Nov 2 – Nov 13", "No study · Oct 31"]), { gaps: fake.gaps });
  await page.unroute(`${API}/api/history`);
}

async function checkWeekly(page, w) {
  await page.goto(`${APP}/history/weekly`, { waitUntil: "networkidle" });
  await page.waitForSelector(T("weekly-home"), { timeout: 20000 });
  await sleep(400);
  const m = await page.evaluate(() => {
    const out = {};
    for (const h of document.querySelectorAll("main h2")) out[h.textContent] = h.nextElementSibling?.textContent ?? null;
    return out;
  });
  const next = Object.entries(m).find(([h]) => h.startsWith("Try"));
  verdict("N6", w, next?.[1] === "No suggestions yet.", { sections: m, shot: await shot(page, `N6-${w}`) });
}

async function checkVideos(page, w) {
  await page.goto(`${APP}/videos`, { waitUntil: "networkidle" });
  await page.waitForSelector(T("videos-check"), { timeout: 20000 });
  const label = (await page.locator(T("videos-check")).innerText()).trim();
  verdict("N9", w, label === "Preview video", { label });
  await page.locator(T("videos-url")).fill("https://www.youtube.com/watch?v=jNQXAC9IVRw");
  await page.locator(T("videos-check")).click();
  await page.waitForSelector(T("videos-save"), { timeout: 10000 });
  const listIds = await page.evaluate(() => [...new Set([...document.querySelectorAll("main [data-testid]")].map((e) => e.dataset.testid))]);
  const listUntagged = await page.evaluate(() =>
    [...document.querySelectorAll("main button, main a")].filter((e) => !e.dataset.testid).map((e) => e.textContent),
  );
  const shotList = await shot(page, `TASK332-videos-${w}`);
  await page.locator(T("videos-cancel")).click();
  const want = ["videos-home", "videos-url", "videos-check", "videos-save", "videos-cancel", "videos-title", "videos-delete"];
  verdict("TASK-332-list", w, want.every((id) => listIds.includes(id)) && listUntagged.length === 0, { listIds, untagged: listUntagged, shot: shotList });

  await page.locator(T("videos-title")).first().click();
  await page.waitForSelector(T("video-mark-start"), { timeout: 20000 });
  await sleep(2500);
  await page.locator(T("video-mark-start")).click();
  await sleep(500);
  const detailIds = await page.evaluate(() => [...new Set([...document.querySelectorAll("main [data-testid]")].map((e) => e.dataset.testid))]);
  const untagged = await page.evaluate(() =>
    [...document.querySelectorAll("main button, main a")].filter((e) => !e.dataset.testid).map((e) => e.textContent),
  );
  const wantD = ["video-back", "video-mark-end", "video-mark-cancel", "video-listen", "video-practise", "video-delete", "video-word"];
  verdict("TASK-332-detail", w, wantD.every((id) => detailIds.includes(id)) && untagged.length === 0, {
    detailIds,
    untagged,
    shot: await shot(page, `TASK332-video-${w}`),
  });
  await page.locator(T("video-mark-cancel")).click();
  await sleep(300);
  const backToStart = await page.locator(T("video-mark-start")).count();
  verdict("TASK-332-cancel", w, backToStart === 1, { markStartAfterCancel: backToStart });
}

const browser = await chromium.connectOverCDP("http://127.0.0.1:9470");
for (const [w, h] of [
  [1400, 1000],
  [390, 844],
]) {
  const context = await browser.newContext({ viewport: { width: w, height: h }, permissions: ["microphone"] });
  await guard(context);
  await context.addInitScript(installFakes);
  const page = await context.newPage();
  const consoleErrors = [];
  page.on("console", (msg) => msg.type() === "error" && consoleErrors.push(msg.text().slice(0, 200)));
  for (const fn of [checkHome, checkPractice, checkCoach, checkResults, checkHistory, checkWeekly, checkVideos]) {
    try {
      await fn(page, w);
    } catch (err) {
      verdict(fn.name, w, false, { error: String(err).slice(0, 400) });
    }
  }
  results.push({ item: "console-errors", width: w, ok: null, detail: consoleErrors });
  await context.close();
}
await browser.close().catch(() => {});
writeFileSync(join(EVIDENCE, "results.json"), JSON.stringify({ results, blocked, sockets }, null, 2));
console.log(`blocked writes: ${blocked.length} · fake sockets: ${sockets.length}`);
console.log(`pass ${results.filter((r) => r.ok === true).length} · fail ${results.filter((r) => r.ok === false).length}`);
