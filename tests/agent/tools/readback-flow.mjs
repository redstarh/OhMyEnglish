// 따라 읽기 흐름 시험(`TASK-348` · 실시간 표시 설계서 §12) — 프런트 :3000 이 떠 있을 때
// `node tests/agent/tools/readback-flow.mjs`. 가짜 인식기 · 가짜 음성 합성으로 돌림(시험 Chrome 은 진짜 인식을 못 함).
// ⛔ 쓰기 요청은 모두 막음 — 판정은 가짜 응답(첫 시도 틀림 · 둘째 시도 맞음), 진도 저장은 기록만 하고 dev DB 에 닿지 않음.
// 판정: ① Start speaking 한 번으로 듣기 시작 ② 낱말 색칠이 차례로 늘어남 ③ 틀리면 같은 문장을 다시 들음(다시 읽어 주지 않음)
//       ④ 맞으면 다음 문장 · 다음 자리를 바로 저장 ⑤ 듣는 중 작은 글씨 없음 ⑥ 말 없음이면 멈춤. 어기면 종료 코드 1.
import { chromium } from "playwright";

const SAID = "We used to deploy by hand";
function fakes() {
  window.__sr = { starts: 0, speaks: 0 };
  window.__mode = "say";
  class FakeRecognition {
    constructor() { this.segments = []; this.ended = false; }
    emit(text, isFinal) {
      this.segments = [...this.segments.filter((s) => s.isFinal), { text, isFinal }];
      const results = this.segments.map((s) => Object.assign([{ transcript: s.text }], { isFinal: s.isFinal }));
      this.onresult?.({ results, resultIndex: 0 });
    }
    end() { if (this.ended) return; this.ended = true; this.onend?.(); }
    start() {
      window.__sr.starts += 1;
      setTimeout(() => this.onaudiostart?.(), 100);
      if (window.__mode === "silent") { setTimeout(() => this.onerror?.({ error: "no-speech" }), 300); setTimeout(() => this.end(), 350); return; }
      setTimeout(() => this.emit("We used", false), 400);
      setTimeout(() => this.emit(window.__said, true), 900);
      setTimeout(() => this.end(), 1200);
    }
    stop() { setTimeout(() => this.end(), 30); }
    abort() { setTimeout(() => { this.onerror?.({ error: "aborted" }); this.end(); }, 10); }
  }
  window.SpeechRecognition = FakeRecognition;
  window.webkitSpeechRecognition = FakeRecognition;
  // 음성 합성은 2.5초 읽고 끝남 — 낱말 경계 신호는 주지 않음(시간 비례 색칠 경로를 잼).
  window.speechSynthesis.speak = (u) => { window.__sr.speaks += 1; setTimeout(() => u.onstart?.(), 10); setTimeout(() => u.onend?.(), 2500); };
  window.speechSynthesis.cancel = () => {};
}

const failures = [];
const check = (ok, msg) => { console.log(`${ok ? "ok  " : "FAIL"} ${msg}`); if (!ok) failures.push(msg); };
const b = await chromium.launch({ args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] });
const ctx = await b.newContext({ viewport: { width: 393, height: 659 }, isMobile: true, hasTouch: true });
await ctx.grantPermissions(["microphone"], { origin: "http://localhost:3000" });
const page = await ctx.newPage();
await page.addInitScript(`(${fakes.toString()})(); window.__said = ${JSON.stringify(SAID)};`);
let judgeCalls = 0;
const saves = [];
// 판정 요청이 온 순간의 읽어 주기 횟수 · 문장 번호 — 「다시 들음」을 인식기 재시작과 가르려면 판정 단위로 셈.
const judgeLog = [];
await page.route("**/api/**", async (r) => {
  const req = r.request();
  if (req.url().includes("/attempts/text")) {
    judgeCalls += 1;
    judgeLog.push(await page.evaluate(() => ({
      speaks: window.__sr.speaks,
      sentence: document.querySelector('[data-testid="course-sentence-number"]')?.textContent ?? "",
    })));
    const said = req.postDataJSON().transcript;
    const words = said.split(" ").map((word, i) => ({ word, verdict: judgeCalls === 1 && i === 1 ? "different" : "match" }));
    return r.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ transcript: said, words, attempts: judgeCalls }) });
  }
  if (req.method() !== "GET") {
    if (req.url().includes("/progress")) saves.push(req.postDataJSON());
    return r.fulfill({ status: 204, body: "" });
  }
  return r.continue();
});
const state = () => page.evaluate(() => ({
  phase: document.querySelector('[data-testid="course-phase"]')?.dataset.phase ?? "idle",
  sentence: document.querySelector('[data-testid="course-sentence-number"]')?.textContent ?? "",
  lit: document.querySelectorAll('[data-testid="course-sentence"] [data-spoken="true"]').length,
  slot: document.querySelector('[data-testid="course-result-slot"]')?.textContent ?? "",
  speaks: window.__sr.speaks, starts: window.__sr.starts,
}));

await page.goto("http://localhost:3000/", { waitUntil: "networkidle" });
await page.evaluate(() => localStorage.setItem("omy.course.mode", "auto"));
await page.getByRole("button", { name: /Start speaking/ }).click();
await page.waitForSelector('[data-testid="course-card"]');
const first = await state();
const startSentence = first.sentence;
// ①② 읽어 주는 동안 색칠이 늘어남
const litSamples = [];
for (let i = 0; i < 8; i += 1) { const s = await state(); litSamples.push(`${s.phase}:${s.lit}`); await page.waitForTimeout(300); }
check(first.phase === "listen" || litSamples.some((x) => x.startsWith("listen")), `① Start speaking 한 번으로 듣기 시작 (${litSamples[0]})`);
const lits = litSamples.filter((x) => x.startsWith("listen")).map((x) => Number(x.split(":")[1]));
check(lits.length >= 3 && lits.at(-1) > lits[0] && lits.every((v, i) => i === 0 || v >= lits[i - 1]), `② 낱말 색칠이 차례로 늘어남 ${JSON.stringify(lits)}`);
// ③ 첫 판정 틀림 → 같은 문장을 다시 들음(읽어 주기 1회 그대로 · 인식 2회)
for (let i = 0; i < 60 && judgeLog.length < 2; i += 1) await page.waitForTimeout(250);
const afterWrong = await state();
const second = judgeLog[1];
check(second !== undefined && second.sentence === startSentence && second.speaks === 1, `③ 틀리면 같은 문장을 다시 들음 — 둘째 판정 ${JSON.stringify(second)} · 시작 문장 ${startSentence}`);
check(!/I'm listening|You're saying/.test(afterWrong.slot), `⑤ 듣는 중 작은 글씨 없음 (${afterWrong.slot.slice(0, 40)})`);
// ④ 둘째 판정 맞음 → 다음 자리를 바로 저장하고 다음 문장으로 감
const savesBefore = saves.length;
await page.waitForFunction(() => window.__sr.speaks >= 2, null, { timeout: 15000 }).catch(() => {});
const afterRight = await state();
// ⚠️ 다음 자리 저장은 맞음 판정 직후라 이 시점보다 앞설 수 있음 — 저장 목록 전체에서 「다음 문장」 자리를 찾음.
const startIndex = Number(startSentence.match(/Sentence (\d+)/)?.[1] ?? 0) - 1;
const savedNext = saves.find((save) => save.sentence_index === startIndex + 1);
check(afterRight.sentence !== startSentence && afterRight.speaks === 2, `④ 맞으면 다음 문장 (${startSentence} → ${afterRight.sentence})`);
check(savedNext !== undefined, `④ 다음 자리를 저장함 ${JSON.stringify(savedNext)} (저장 ${saves.length}건 · 그중 이 단계 뒤 ${saves.length - savesBefore}건)`);
// ⑥ 말 없음 → 멈춤
await page.evaluate(() => { window.__mode = "silent"; });
await page.waitForTimeout(6000);
const silent = await state();
await page.waitForTimeout(3000);
const later = await state();
check(later.starts === silent.starts && /couldn't hear/i.test(later.slot), `⑥ 말 없음이면 멈춤 (듣기 ${silent.starts} → ${later.starts} · ${later.slot.slice(0, 40)})`);
await b.close();
console.log(failures.length ? `FAILED ${failures.length}` : "ALL PASS");
process.exit(failures.length ? 1 : 0);
