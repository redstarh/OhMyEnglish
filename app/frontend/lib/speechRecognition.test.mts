// 말 끝 감지 시험 — 가짜 인식기와 가짜 시계로 잼(`TASK-317` · 설계서 §4·§7·§8).
// 실행: node --test lib/speechRecognition.test.mts (Node 24 의 타입 제거로 .ts 를 바로 불러옴)
// ⚠️ 시험 Chrome 에서는 실물 인식기를 자동으로 잴 수 없음(설계서 §2-2) — 그래서 논리는 여기서 잼.
import assert from "node:assert/strict";
import test from "node:test";

import {
  FINAL_GRACE_MS,
  listen,
  MAX_RESTARTS,
  listenLimitMs,
  NO_SPEECH_MS,
  QUIET_LONG_MS,
  QUIET_MS,
  quietThresholdMs,
  type Clock,
  type ListenOutcome,
  type ListenUpdate,
  type RecognitionLike,
} from "./speechRecognition.ts";

/** 손으로 돌리는 시계 — `advance` 만큼 시간이 흐르고 그 안의 타이머가 차례로 불림. */
class FakeClock implements Clock {
  now = 0;
  private timers = new Map<number, { at: number; callback: () => void }>();
  private nextId = 1;

  setTimeout(callback: () => void, ms: number): unknown {
    const id = this.nextId++;
    this.timers.set(id, { at: this.now + ms, callback });
    return id;
  }

  clearTimeout(handle: unknown): void {
    this.timers.delete(handle as number);
  }

  advance(ms: number): void {
    const until = this.now + ms;
    for (;;) {
      const due = [...this.timers.entries()]
        .filter(([, timer]) => timer.at <= until)
        .sort((a, b) => a[1].at - b[1].at)[0];
      if (!due) break;
      this.timers.delete(due[0]);
      this.now = due[1].at;
      due[1].callback();
    }
    this.now = until;
  }
}

type Segment = { text: string; isFinal: boolean };

class FakeRecognition implements RecognitionLike {
  lang = "";
  continuous = false;
  interimResults = false;
  onresult: RecognitionLike["onresult"] = null;
  onerror: RecognitionLike["onerror"] = null;
  onend: RecognitionLike["onend"] = null;
  onaudiostart: RecognitionLike["onaudiostart"] = null;
  calls: string[] = [];
  /** `stop()` 을 받으면 이 확정 글자를 낸 뒤 끝냄 — 실물이 남은 final 을 내는 모양. */
  finalOnStop: string | null = null;
  endOnStop = true;
  private segments: Segment[] = [];

  start(): void {
    this.calls.push("start");
  }
  stop(): void {
    this.calls.push("stop");
    if (this.finalOnStop !== null) {
      this.segments = this.segments.filter((item) => item.isFinal);
      this.say(this.finalOnStop, true);
    }
    if (this.endOnStop) this.onend?.();
  }
  abort(): void {
    this.calls.push("abort");
  }

  /** 결과 하나 — 미확정이면 앞의 미확정을 갈아 끼우고, 확정이면 그 자리를 굳힘. */
  say(text: string, isFinal: boolean): void {
    const kept = this.segments.filter((item) => item.isFinal);
    this.segments = [...kept, { text, isFinal }];
    const results = this.segments.map((item) => ({ isFinal: item.isFinal, 0: { transcript: item.text } }));
    this.onresult?.({ results });
  }
}

function setup(options: { expectedWords?: number; maxMs?: number } = {}) {
  const clock = new FakeClock();
  const recognition = new FakeRecognition();
  // 다시 시작할 때마다 새 인식기를 만듦 — 첫 것은 `recognition`, 모두는 `instances`.
  const instances: FakeRecognition[] = [];
  const controller = new AbortController();
  const updates: ListenUpdate[] = [];
  let outcome: ListenOutcome | undefined;
  let audioStarted = false;
  const pending = listen({
    signal: controller.signal,
    expectedWords: options.expectedWords ?? 5,
    maxMs: options.maxMs ?? 15000,
    onUpdate: (update) => updates.push(update),
    onAudioStart: () => {
      audioStarted = true;
    },
    create: () => {
      const next = instances.length === 0 ? recognition : new FakeRecognition();
      instances.push(next);
      return next;
    },
    clock,
  }).then((value) => {
    outcome = value;
    return value;
  });
  const settled = async () => {
    await Promise.resolve();
    await Promise.resolve();
    return outcome;
  };
  return { clock, recognition, instances, controller, updates, pending, settled, audioStarted: () => audioStarted };
}

test("인식기를 en-US · continuous · interim 으로 켜고 audiostart 를 알림", () => {
  const { recognition, audioStarted } = setup();
  assert.equal(recognition.lang, "en-US");
  assert.equal(recognition.continuous, true);
  assert.equal(recognition.interimResults, true);
  assert.deepEqual(recognition.calls, ["start"]);
  recognition.onaudiostart?.();
  assert.equal(audioStarted(), true);
});

test("미확정 글자가 갱신마다 그대로 넘어감", () => {
  const { recognition, updates } = setup();
  recognition.say("I am", false);
  recognition.say("I am a soft", false);
  assert.deepEqual(updates.at(-1), { final: "", interim: "I am a soft" });
});

test("확정 뒤 조용함 기준(1.5초)이 지나면 멈추고 남은 final 로 heard", async () => {
  const { clock, recognition, settled } = setup({ expectedWords: 5 });
  recognition.say("I am a software tester", true);
  clock.advance(QUIET_MS - 1);
  assert.equal(await settled(), undefined);
  assert.deepEqual(recognition.calls, ["start"]);
  clock.advance(1);
  assert.ok(recognition.calls.includes("stop"));
  assert.deepEqual(await settled(), { kind: "heard", text: "I am a software tester" });
});

test("확정 낱말이 60 % 미만이면 2초 쉼에서 자르지 않음 — 「we walk where we」 잘림 방지", async () => {
  const { clock, recognition, settled } = setup({ expectedWords: 10 });
  recognition.say("we walk where we", true); // 4 / 10 낱말
  clock.advance(2000);
  assert.equal(await settled(), undefined, "2초 쉼에서 끝나면 문장이 중간에서 잘림");
  recognition.say("live and work every day here", true);
  clock.advance(QUIET_MS);
  assert.deepEqual(await settled(), {
    kind: "heard",
    text: "we walk where we live and work every day here",
  });
});

test("조용함 기준은 확정 낱말 비율로 갈림", () => {
  assert.equal(quietThresholdMs(5, 10), QUIET_LONG_MS);
  assert.equal(quietThresholdMs(6, 10), QUIET_MS);
  assert.equal(quietThresholdMs(0, 5), QUIET_LONG_MS);
});

test("결과가 하나도 없으면 NO_SPEECH_MS 에 silent 이고 인식기를 끊음", async () => {
  const { clock, recognition, settled } = setup();
  clock.advance(NO_SPEECH_MS - 1);
  assert.equal(await settled(), undefined);
  clock.advance(1);
  assert.deepEqual(await settled(), { kind: "silent" });
  assert.ok(recognition.calls.includes("abort"));
});

test("Chrome 의 no-speech 오류도 silent 임", async () => {
  const { recognition, settled } = setup();
  recognition.onerror?.({ error: "no-speech" });
  assert.deepEqual(await settled(), { kind: "silent" });
});

test("not-allowed 는 denied · network 는 unavailable", async () => {
  const denied = setup();
  denied.recognition.onerror?.({ error: "not-allowed" });
  assert.deepEqual(await denied.settled(), { kind: "denied" });
  for (const error of ["network", "service-not-allowed", "audio-capture"]) {
    const failed = setup();
    failed.recognition.onerror?.({ error });
    assert.deepEqual(await failed.settled(), { kind: "unavailable" }, error);
  }
});

test("signal 이 끊기면 abort 를 부르고 aborted", async () => {
  const { controller, recognition, settled } = setup();
  recognition.say("I am", false);
  controller.abort();
  assert.deepEqual(await settled(), { kind: "aborted" });
  assert.ok(recognition.calls.includes("abort"));
});

test("미확정만 있는 채로 멈추면 stop 뒤 온 final 을 씀", async () => {
  const { clock, recognition, settled } = setup({ expectedWords: 5 });
  recognition.finalOnStop = "I am a software tester";
  recognition.say("I am a software test", false);
  clock.advance(QUIET_LONG_MS);
  assert.deepEqual(await settled(), { kind: "heard", text: "I am a software tester" });
});

test("stop 뒤 final 도 end 도 오지 않으면 1초 뒤 마지막 미확정 문장을 씀", async () => {
  const { clock, recognition, settled } = setup({ expectedWords: 5 });
  recognition.endOnStop = false;
  recognition.say("I am a software", false);
  clock.advance(QUIET_LONG_MS);
  assert.equal(await settled(), undefined);
  clock.advance(FINAL_GRACE_MS);
  assert.deepEqual(await settled(), { kind: "heard", text: "I am a software" });
});

test("계속 말해도 maxMs 에서 멈추고 그때까지의 글자로 판정함", async () => {
  const { clock, recognition, settled } = setup({ expectedWords: 50, maxMs: 8000 });
  recognition.endOnStop = false;
  for (let step = 0; step < 9; step += 1) {
    recognition.say(`word${step}`, true);
    clock.advance(1000);
  }
  assert.ok(recognition.calls.includes("stop"));
  clock.advance(FINAL_GRACE_MS);
  const outcome = await settled();
  assert.equal(outcome?.kind, "heard");
});

test("듣기 상한은 max(8000, 읽은 시간 × 3)", () => {
  assert.equal(listenLimitMs(1000), 8000);
  assert.equal(listenLimitMs(4000), 12000);
});

test("인식기를 만들지 못하면 unavailable", async () => {
  const outcome = await listen({
    signal: new AbortController().signal,
    expectedWords: 5,
    maxMs: 8000,
    create: () => {
      throw new Error("no recognizer");
    },
    clock: new FakeClock(),
  });
  assert.deepEqual(outcome, { kind: "unavailable" });
});

// ── codex 리뷰 HIGH(`TASK-317`) — Chrome 이 문장 중간에 세션을 스스로 끝내도 문장을 잃지 않음 ──

test("멈추라 하지 않았는데 끝나면 새 인식기로 다시 듣고 앞의 확정 글자를 이어 붙임", async () => {
  const { clock, recognition, instances, settled, updates } = setup({ expectedWords: 10 });
  recognition.say("we walk where we", true);
  recognition.onend?.(); // Chrome 이 스스로 끝냄
  assert.equal(await settled(), undefined, "끝났다고 바로 판정하면 나머지 문장을 잃음");
  assert.equal(instances.length, 2);
  assert.deepEqual(instances[1].calls, ["start"]);
  assert.equal(instances[1].continuous, true);
  instances[1].say("live and work", true);
  assert.equal(updates.at(-1)?.final, "we walk where we live and work");
  clock.advance(QUIET_MS);
  assert.deepEqual(await settled(), { kind: "heard", text: "we walk where we live and work" });
});

test("다시 시작한 뒤에도 60 % 규칙은 모은 확정 낱말로 셈", async () => {
  const { clock, recognition, instances, settled } = setup({ expectedWords: 10 });
  recognition.say("we walk", true);
  recognition.onend?.();
  instances[1].say("where we", true); // 모두 4 / 10 낱말
  clock.advance(2000);
  assert.equal(await settled(), undefined, "모은 낱말이 60 % 미만이면 2초 쉼에서 끝나지 않음");
});

test("앞 인식기의 늦은 이벤트는 무시함", async () => {
  const { recognition, instances, updates } = setup({ expectedWords: 10 });
  const staleResult = recognition.onresult;
  const staleEnd = recognition.onend;
  recognition.say("we walk", true);
  recognition.onend?.();
  const count = updates.length;
  staleResult?.({ results: [{ isFinal: true, 0: { transcript: "ghost" } }] });
  staleEnd?.();
  assert.equal(updates.length, count);
  assert.equal(instances.length, 2, "앞 인식기의 끝 신호가 또 다시 시작하게 하면 안 됨");
});

test("계속 바로 끝나면 MAX_RESTARTS 번 뒤 그때까지의 글자로 판정함", async () => {
  const { recognition, instances, settled } = setup({ expectedWords: 10 });
  recognition.say("we walk", true);
  for (let index = 0; index <= MAX_RESTARTS; index += 1) {
    instances.at(-1)?.onend?.();
  }
  assert.equal(instances.length, MAX_RESTARTS + 1);
  assert.deepEqual(await settled(), { kind: "heard", text: "we walk" });
});

test("상한(maxMs)이 지난 뒤의 끝은 다시 시작하지 않음", async () => {
  const { clock, recognition, instances, settled } = setup({ expectedWords: 50, maxMs: 8000 });
  recognition.endOnStop = false;
  recognition.say("word", true);
  clock.advance(1000);
  recognition.say("word more", true);
  clock.advance(7000); // 상한 → stop
  recognition.onend?.();
  assert.equal(instances.length, 1);
  assert.deepEqual(await settled(), { kind: "heard", text: "word word more" });
});

// ── codex 리뷰 MEDIUM(`TASK-317`) — 확정 글자 뒤의 미확정 꼬리를 버리지 않음 ──

test("확정 뒤 미확정 꼬리가 남은 채 끝나면 둘을 이어 판정함", async () => {
  const { clock, recognition, settled } = setup({ expectedWords: 5 });
  recognition.endOnStop = false;
  recognition.say("I am a", true);
  recognition.say("software test", false);
  clock.advance(QUIET_LONG_MS + FINAL_GRACE_MS);
  assert.deepEqual(await settled(), { kind: "heard", text: "I am a software test" });
});

// ── 한글 발음 조각 (`TASK-327` · 사용자 실기기 2026-11-14: 처음 표시 때 「Did you 디드 유」처럼 섞여 나옴) ──

test("미확정에 섞인 한글 발음 조각은 표시에서 뺌", () => {
  const { recognition, updates } = setup();
  recognition.say("Did you 디드 유", false);
  assert.deepEqual(updates.at(-1), { final: "", interim: "Did you" });
});

test("확정에 섞인 한글 조각도 판정 텍스트에서 뺌", async () => {
  const { clock, recognition, settled } = setup({ expectedWords: 5 });
  recognition.say("I am 아이 소프트 a software tester", true);
  clock.advance(QUIET_MS);
  clock.advance(FINAL_GRACE_MS);
  assert.deepEqual(await settled(), { kind: "heard", text: "I am a software tester" });
});

test("한글뿐인 결과는 들은 것으로 치지 않음 — 말 없음 시한이 그대로 돎", async () => {
  const { clock, recognition, updates, settled } = setup();
  recognition.say("디드 유 푸시", false);
  assert.equal(updates.length, 0, "한글뿐인 결과로 화면을 갱신하지 않음");
  clock.advance(NO_SPEECH_MS);
  assert.deepEqual(await settled(), { kind: "silent" });
});
