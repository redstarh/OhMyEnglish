// TASK-317 실시간 따라 말하기 시나리오 — 가짜 SpeechRecognition 으로 화면 논리를 잼(설계서 §8 ①~⑧).
// 사용: node live.mjs <CDP 포트(기본 9430)>
// ⚠️ 시험 Chrome 에서는 실물 인식기가 가짜 오디오를 전사하지 않음(설계서 §2-2) — 그래서 인식기를 가짜로 심음.
// ⛔ 사용자 스택(:3000 · :8002 · dev DB)에 쓰지 않음 — 텍스트 시도와 진도 저장은 page.route 로 가로채
//    가짜 응답을 주고, 요청 본문만 단정함. 읽기(GET)만 실제 백엔드에 닿음.
import { mkdirSync, writeFileSync } from "node:fs";
import { chromium } from "/Users/redstar/MyProject/OhMyEnglish/tests/agent/tools/node_modules/playwright/index.mjs";

const PORT = process.argv[2] ?? "9430";
const APP = "http://localhost:3000";
const OUT = new URL("./evidence/", import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });

// 페이지에 심는 가짜 인식기 — 각본(window.__srScript)대로 결과·오류를 내고 호출을 기록함.
// 결과 목록은 실물처럼 쌓임: 미확정은 앞의 미확정을 갈아 끼우고, 확정은 그 자리를 굳힘.
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
      state.calls.push(["start", Math.round(performance.now()), { lang: this.lang, continuous: this.continuous, interim: this.interimResults }]);
      state.timers.push(setTimeout(() => this.onaudiostart?.(), 100));
      for (const step of window.__srScript) {
        state.timers.push(
          setTimeout(() => {
            state.calls.push([step.type, Math.round(performance.now()), step.text ?? step.error ?? ""]);
            if (step.type === "interim") this.emit(step.text, false);
            else if (step.type === "final") this.emit(step.text, true);
            else if (step.type === "error") this.onerror?.({ error: step.error });
            else if (step.type === "end") this.end();
          }, 100 + step.at),
        );
      }
    }
    stop() {
      state.calls.push(["stop", Math.round(performance.now())]);
      this.clear();
      // 실물처럼 남은 미확정을 확정으로 굳힌 뒤 끝냄.
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
  // 헤드리스의 음성 합성은 끝 신호가 오지 않아 어림값의 3배를 기다림 — 시나리오 시간을 줄이려고 0.3초로 끝냄.
  if (window.speechSynthesis) {
    window.speechSynthesis.speak = (utterance) => {
      setTimeout(() => utterance.onstart?.(), 10);
      setTimeout(() => utterance.onend?.(), 300);
    };
    window.speechSynthesis.cancel = () => {};
  }
}

const rows = [];
function verdict(id, width, expect, actual, pass) {
  rows.push({ id, width, expect, actual, verdict: pass ? "통과" : "실패" });
  console.log(`[${pass ? "통과" : "실패"}] ${id} @${width} — ${actual}`);
}

const browser = await chromium.connectOverCDP(`http://127.0.0.1:${PORT}`);
const ctx = browser.contexts()[0];
await ctx.grantPermissions(["microphone"], { origin: APP });

async function openPractice(width) {
  const page = await ctx.newPage();
  await page.setViewportSize({ width, height: width < 600 ? 844 : 900 });
  await page.addInitScript(installFakes);
  const posts = [];
  const progress = [];
  const counts = {};
  // `queue` 는 요청마다 앞에서 하나씩 꺼내 쓰는 지연(ms) · `invalid` 면 200 에 JSON 이 아닌 몸통을 줌.
  const delay = { ms: 0, queue: [], invalid: false };
  await page.route("**/api/course/sentences/*/attempts/text", async (route) => {
    const request = route.request();
    const key = request.url().split("/sentences/")[1].split("/")[0];
    const body = request.postDataJSON();
    posts.push({ key, body, at: Date.now() });
    // 서버처럼 도착 순서로 횟수를 매김 — 늦게 돌려줘도 먼저 온 요청이 작은 횟수임.
    counts[key] = (counts[key] ?? 0) + 1;
    const attempts = 100 + counts[key];
    const wait = delay.queue.length ? delay.queue.shift() : delay.ms;
    if (wait) await new Promise((resolve) => setTimeout(resolve, wait));
    if (delay.invalid) {
      await route.fulfill({ status: 200, contentType: "application/json", body: "not json{" });
      return;
    }
    const words = String(body.transcript).split(/\s+/).map((word) => ({ word, verdict: "match" }));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ transcript: body.transcript, words, attempts }) });
  });
  await page.route("**/api/course/days/*/progress", async (route) => {
    progress.push(route.request().postDataJSON());
    await route.fulfill({ status: 204, body: "" });
  });
  // PCM 경로가 불리면 실패로 잡음 — 인식기가 있으면 쓰지 않아야 함.
  const pcmPosts = [];
  await page.route("**/api/course/sentences/*/attempts", async (route) => {
    pcmPosts.push(route.request().url());
    await route.fulfill({ status: 500, body: "" });
  });
  await page.goto(APP + "/", { waitUntil: "domcontentloaded" });
  await page.waitForSelector('[data-testid="home-hero"]', { timeout: 20000 });
  await page.waitForTimeout(800);
  await page.locator('[data-testid="start-session"]').click();
  await page.waitForSelector('[data-testid="course-start"], [data-testid="course-retry"]', { timeout: 15000 });
  await page.locator('[data-testid="course-mode-manual"]').click();
  return { page, posts, progress, pcmPosts, delay };
}

const $ = (page, tid) => page.locator(`[data-testid="${tid}"]`);
const text = async (page, tid) => ((await $(page, tid).count()) ? (await $(page, tid).first().innerText()).trim() : null);
const box = async (page) => {
  const b = await $(page, "course-card").boundingBox();
  return b ? { w: Math.round(b.width * 10) / 10, h: Math.round(b.height * 10) / 10 } : null;
};
const calls = (page) => page.evaluate(() => window.__sr.calls.map((c) => c[0]));
const phase = (page) => page.evaluate(() => document.querySelector('[data-testid="course-phase"]')?.dataset.phase ?? "idle");
const setScript = (page, script) => page.evaluate((s) => (window.__srScript = s), script);
const sentenceText = (page) => text(page, "course-sentence");
const tryCount = async (page) => Number((await text(page, "course-attempts")).replace(/\D/g, ""));
async function start(page) {
  const retry = await $(page, "course-retry").count();
  await $(page, retry ? "course-retry" : "course-start").click();
}
async function waitPhase(page, value, timeout = 15000) {
  await page.waitForFunction((v) => (document.querySelector('[data-testid="course-phase"]')?.dataset.phase ?? "idle") === v, value, { timeout });
}

async function runWidth(width) {
  const { page, posts, progress, pcmPosts, delay } = await openPractice(width);
  const sentence = await sentenceText(page);
  const words = sentence.split(/\s+/);
  const plain = sentence.replace(/[.,!?]/g, "");
  const sizes = { idle: await box(page) };

  // ① 미확정 글자가 POST 전에 보임 · ② 확정 뒤 조용해지면 POST 1번 · 판정 · Try +1
  await setScript(page, [
    { at: 300, type: "interim", text: words.slice(0, 2).join(" ") },
    { at: 900, type: "interim", text: words.slice(0, 4).join(" ") },
    { at: 2600, type: "final", text: plain },
  ]);
  const try0 = await tryCount(page);
  await start(page);
  await page.waitForSelector('[data-testid="course-live-interim"]', { timeout: 10000 });
  const interimText = await text(page, "course-live-interim");
  const postsAtInterim = posts.length;
  const phaseAtInterim = await phase(page);
  sizes.listening = await box(page);
  await page.screenshot({ path: `${OUT}live-interim-${width}.png` });
  verdict("①", width, "POST 전에 course-live-interim 에 미확정 글자", `interim="${interimText}" posts=${postsAtInterim} phase=${phaseAtInterim}`, Boolean(interimText) && postsAtInterim === 0 && phaseAtInterim === "repeat");

  await waitPhase(page, "done", 15000);
  await page.waitForTimeout(300);
  const transcript = await text(page, "course-transcript");
  const verdictCount = await page.locator('[data-testid="course-spoken"] [data-verdict]').count();
  const try1 = await tryCount(page);
  const liveGone = (await $(page, "course-live").count()) === 0;
  sizes.result = await box(page);
  await page.screenshot({ path: `${OUT}live-result-${width}.png` });
  const startCall = (await page.evaluate(() => window.__sr.calls.find((c) => c[0] === "start")))?.[2];
  verdict(
    "②",
    width,
    "확정 뒤 조용해지면 POST 1번(본문=확정 문장) · 판정 표시 · 실시간 줄 지움 · Try 갱신 · 인식기 설정 en-US/continuous/interim · PCM 경로 없음",
    `posts=${posts.length} body=${JSON.stringify(posts[0]?.body)} transcript="${transcript}" verdicts=${verdictCount} liveGone=${liveGone} try ${try0}->${try1} config=${JSON.stringify(startCall)} pcm=${pcmPosts.length}`,
    posts.length === 1 && posts[0].body.transcript === plain && transcript === plain && verdictCount === words.length && liveGone && try1 === 101 && startCall?.lang === "en-US" && startCall?.continuous === true && startCall?.interim === true && pcmPosts.length === 0,
  );

  // ③ 앞부분(원문의 60 % 미만)을 확정한 뒤 2초 쉬고 나머지를 말해도 잘리지 않음
  const cut = Math.max(1, Math.floor(words.length * 0.6 - 0.01));
  const head = plain.split(/\s+/).slice(0, cut).join(" ");
  const tail = plain.split(/\s+/).slice(cut).join(" ");
  await setScript(page, [
    { at: 200, type: "final", text: head },
    { at: 2200, type: "final", text: tail },
  ]);
  const before3 = posts.length;
  await start(page);
  await waitPhase(page, "done", 15000);
  const body3 = posts[before3]?.body;
  verdict("③", width, `앞 ${cut}/${words.length} 낱말 확정 · 2초 쉼 · 나머지 → POST 본문이 전체 문장`, `posts+${posts.length - before3} body=${JSON.stringify(body3)}`, posts.length - before3 === 1 && body3?.transcript === `${head} ${tail}`);

  // ④ 말이 없으면 6초 안에 「안 들렸어요」 · POST 없음 · Try 그대로
  await setScript(page, []);
  const before4 = posts.length;
  const try4 = await tryCount(page);
  await start(page);
  const t4 = Date.now();
  await page.waitForFunction(() => /couldn't hear you/.test(document.querySelector('[data-testid="course-notice"]')?.textContent ?? ""), null, { timeout: 8000 }).catch(() => {});
  const elapsed4 = Date.now() - t4;
  const notice4 = await text(page, "course-notice");
  verdict("④", width, "6초 안에 unheard 안내 · POST 없음(말 없음은 세지 않음) · Try 그대로", `notice="${notice4}" elapsed=${elapsed4}ms posts+${posts.length - before4} try ${try4}->${await tryCount(page)}`, /couldn't hear you/.test(notice4 ?? "") && elapsed4 < 6500 && posts.length === before4 && (await tryCount(page)) === try4);

  // ⑤ not-allowed → 마이크 안내 · POST 없음 · idle
  await setScript(page, [{ at: 200, type: "error", error: "not-allowed" }]);
  const before5 = posts.length;
  await start(page);
  await page.waitForTimeout(1500);
  const notice5 = await text(page, "course-notice");
  const phase5 = await phase(page);
  verdict("⑤", width, "not-allowed → 마이크 안내 · POST 없음 · 단계 idle", `notice="${notice5}" phase=${phase5} posts+${posts.length - before5}`, /allow the mic/.test(notice5 ?? "") && phase5 === "idle" && posts.length === before5);

  // ⑥ network → 판정 불가 안내 · POST 없음
  await setScript(page, [{ at: 200, type: "error", error: "network" }]);
  const before6 = posts.length;
  await start(page);
  await page.waitForTimeout(1500);
  const notice6 = await text(page, "course-notice");
  verdict("⑥", width, "network → unavailable 안내 · POST 없음", `notice="${notice6}" posts+${posts.length - before6}`, /can't check your speaking/.test(notice6 ?? "") && posts.length === before6);

  // ⑧ 긴 미확정 글자에서도 카드 크기가 같음(아래에서 네 상태를 견줌)
  const long = Array.from({ length: 12 }, () => plain).join(" ");
  await setScript(page, [{ at: 200, type: "interim", text: long }]);
  await start(page);
  await page.waitForSelector('[data-testid="course-live-interim"]', { timeout: 10000 });
  await page.waitForTimeout(200);
  sizes.longInterim = await box(page);
  const scrolled = await page.evaluate(() => {
    const slot = document.querySelector('[data-testid="course-result-slot"]');
    return { scrollTop: Math.round(slot.scrollTop), overflow: slot.scrollHeight > slot.clientHeight, atBottom: Math.abs(slot.scrollHeight - slot.clientHeight - slot.scrollTop) < 2 };
  });
  await page.screenshot({ path: `${OUT}live-long-${width}.png` });

  // ⑦ 듣는 중에 Next → abort · POST 없음 (위 ⑧ 의 듣기를 그대로 끊음)
  const before7 = posts.length;
  const callsBefore7 = (await calls(page)).length;
  await $(page, "course-next").click();
  await page.waitForTimeout(2500);
  const after7 = (await calls(page)).slice(callsBefore7);
  verdict("⑦", width, "듣는 중 Next → abort 호출 · POST 없음 · 단계 idle", `calls=${JSON.stringify(after7)} posts+${posts.length - before7} phase=${await phase(page)}`, after7.includes("abort") && posts.length === before7 && (await phase(page)) === "idle");

  const same = [sizes.listening, sizes.longInterim, sizes.result].every((s) => s && sizes.idle && s.w === sizes.idle.w && s.h === sizes.idle.h);
  verdict("⑧", width, "course-card 크기가 idle·듣는 중·긴 미확정·결과 네 상태에서 같음 · 긴 글은 자리 안에서 맨 아래로 스크롤", `sizes=${JSON.stringify(sizes)} slot=${JSON.stringify(scrolled)}`, same && scrolled.overflow && scrolled.atBottom);

  // ⑨ 판정 응답 전에 Next → 서버가 센 횟수를 화면이 그래도 적용함(설계서 §5 결함 수정)
  // ⑦ 에서 다음 문장으로 왔으므로 Back 으로 그 문장에 돌아가 Try 를 읽음.
  await setScript(page, [{ at: 200, type: "final", text: "hello there" }]);
  delay.ms = 2500;
  const before9 = posts.length;
  const try9 = await tryCount(page);
  await start(page);
  await waitPhase(page, "judge", 10000);
  await $(page, "course-next").click();
  await page.waitForTimeout(3500);
  await $(page, "course-prev").click();
  await page.waitForTimeout(300);
  const try9b = await tryCount(page);
  delay.ms = 0;
  verdict("⑨", width, "판정 응답 전에 Next → 돌아오면 Try 가 서버 값으로 갱신돼 있음", `posts+${posts.length - before9} try ${try9}->${try9b}`, posts.length - before9 === 1 && try9b === 101);

  // ⑩ 판정 응답의 몸통이 JSON 이 아님 → 판정 불가 안내 · ③ Check 에 멈추지 않음(codex 리뷰 MEDIUM)
  await setScript(page, [{ at: 200, type: "final", text: "hello there" }]);
  delay.invalid = true;
  const try10 = await tryCount(page);
  await start(page);
  await page.waitForFunction(() => /can't check your speaking/.test(document.querySelector('[data-testid="course-notice"]')?.textContent ?? ""), null, { timeout: 6000 }).catch(() => {});
  const notice10 = await text(page, "course-notice");
  const phase10 = await phase(page);
  delay.invalid = false;
  verdict("⑩", width, "응답 몸통이 JSON 이 아니면 unavailable 안내 · 단계가 judge 에 남지 않음 · Try 그대로", `notice="${notice10}" phase=${phase10} try ${try10}->${await tryCount(page)}`, /can't check your speaking/.test(notice10 ?? "") && phase10 === "done" && (await tryCount(page)) === try10);

  // ⑪ 앞 시도의 응답이 늦게 와도 Try 가 줄지 않음(codex 리뷰 MEDIUM) — 첫 요청(작은 횟수)을 늦게 돌려줌.
  // ⚠️ 원문 전체를 확정으로 줌 — 짧은 글이면 조용함 기준이 3초가 되어 둘째 요청이 첫 응답 뒤에 나감.
  const plain11 = (await sentenceText(page)).replace(/[.,!?]/g, "");
  await setScript(page, [{ at: 200, type: "final", text: plain11 }]);
  delay.queue = [6000, 0];
  const before11 = posts.length;
  await start(page);
  await waitPhase(page, "judge", 10000);
  await $(page, "course-retry").click(); // 첫 판정이 오기 전에 다시 함
  await waitPhase(page, "done", 10000);
  const tryFresh = await tryCount(page);
  await page.waitForTimeout(6000); // 늦은 첫 응답이 도착함
  const tryAfterLate = await tryCount(page);
  const sent11 = posts.slice(before11).length;
  verdict("⑪", width, "늦게 온 앞 응답(작은 횟수)이 Try 를 낮추지 않음", `posts+${sent11} try fresh=${tryFresh} afterLate=${tryAfterLate}`, sent11 === 2 && tryAfterLate === tryFresh && tryFresh > 0);

  // ⑫ 말한 내용이 문장과 같은 글자 크기 · 가장 긴 문장(61자)의 결과도 결과 자리에 다 듦 · 카드 크기 그대로(`TASK-326`).
  const longest = "We deploy on Fridays This week we are deploying on Thursday";
  await setScript(page, [{ at: 200, type: "final", text: longest }]);
  delay.queue = [];
  await start(page);
  await waitPhase(page, "done", 15000);
  await page.waitForTimeout(300);
  const fit12 = await page.evaluate(() => {
    const slot = document.querySelector('[data-testid="course-result-slot"]');
    const fs = (sel) => { const e = document.querySelector(sel); return e ? getComputedStyle(e).fontSize + "/" + getComputedStyle(e).fontWeight : null; };
    return { slotH: slot.clientHeight, contentH: slot.scrollHeight, sentence: fs('[data-testid="course-sentence"]'), transcript: fs('[data-testid="course-transcript"]'), word: fs('[data-testid="course-spoken"] [data-verdict]') };
  });
  const box12 = await box(page);
  await page.screenshot({ path: `${OUT}live-longest-${width}.png` });
  verdict("⑫", width, "말한 내용 = 문장 글자(크기·굵기) · 가장 긴 결과가 자리에 다 듦 · 카드 크기 그대로", `${JSON.stringify(fit12)} card=${JSON.stringify(box12)} idle=${JSON.stringify(sizes.idle)}`, fit12.transcript === fit12.sentence && fit12.word === fit12.sentence && fit12.contentH <= fit12.slotH && box12?.h === sizes.idle?.h);

  writeFileSync(`${OUT}requests-${width}.json`, JSON.stringify({ posts, progress, pcmPosts }, null, 1));
  await page.close();
}

try {
  for (const width of [1400, 390]) await runWidth(width);
} finally {
  writeFileSync(`${OUT}verdicts.json`, JSON.stringify(rows, null, 1));
  const failed = rows.filter((r) => r.verdict !== "통과").length;
  console.log(`합계 ${rows.length}건 · 통과 ${rows.length - failed} · 실패 ${failed}`);
  await browser.close().catch(() => {});
}
process.exit(rows.some((r) => r.verdict !== "통과") ? 1 : 0);
