/**
 * 문장 연습의 실시간 따라 말하기 — 브라우저 내장 음성 인식(`TASK-317`).
 * 설계서 `docs/design/2026-11-14-live-readback-transcript-design.md` §3·§4·§7.
 *
 * 말하는 동안 확정·미확정 글자를 `onUpdate` 로 넘기고, 말 끝을 스스로 감지해 끝냄.
 * 고정 녹음 창(읽은 시간 + 1초)이 늦게·천천히 읽는 학습자의 문장을 중간에서 잘랐음(설계서 §1 ②).
 *
 * ⛔ Chrome 의 인식은 소리를 Google 서버로 보냄 — 사용자가 승인했음(2026-11-14 · 설계서 §11-1).
 * ⛔ `continuous=false` 를 쓰지 않음 — 첫 쉼에서 끝나 「중간에 잘림」이 같은 모양으로 돌아옴(설계서 §3).
 * ⛔ 인식기는 시도마다 새로 만듦 — 앞 시도의 결과 목록이 다음 시도에 섞이지 않게 함.
 * ⚠️ 이 파일은 `node --test` 가 타입 제거로 바로 불러옴(`speechRecognition.test.mts`) — `@/` 별칭과
 *    enum 같은 지울 수 없는 문법을 쓰지 않음.
 * ⚠️ 아래 수치는 이 설계가 새로 정한 값임(근거 문서 없음) — 실물 측정으로 고침(설계서 §4·§10).
 */

/** 마지막 결과(확정·미확정 모두) 뒤로 이만큼 조용하고 확정 부분이 있으면 끝냄. */
export const QUIET_MS = 1500;
/** 확정 낱말이 원문의 60 % 미만이면 조용함 기준을 늘림 — 늦게·천천히 읽는 학습자를 자르지 않게 함. */
export const QUIET_LONG_MS = 3000;
export const SHORT_RATIO = 0.6;
/** 시작한 뒤 결과가 하나도 없으면 「안 들렸어요」로 끝냄. */
export const NO_SPEECH_MS = 5000;
/** `stop()` 뒤 남은 final 을 기다리는 상한. */
export const FINAL_GRACE_MS = 1000;
/**
 * 멈추라 하지 않았는데 인식기가 끝났을 때 다시 시작하는 최대 횟수(codex 리뷰 HIGH · `TASK-317`).
 * ⚠️ 발명한 수치임 — 바로 끝나기를 되풀이하는 환경에서 끝없이 다시 시작하지 않게 하는 상한임.
 */
export const MAX_RESTARTS = 3;
/** 듣기 상한의 바닥 — 실제 상한은 `max(이 값, 읽은 시간 × 3)` 임(`listenLimitMs`). */
export const MIN_LISTEN_MS = 8000;

export type ListenOutcome =
  | { kind: "heard"; text: string }
  | { kind: "silent" }
  | { kind: "denied" }
  | { kind: "unavailable" }
  | { kind: "aborted" };

/** 화면에 보일 글자 — `final` 은 확정 부분, `interim` 은 아직 바뀔 수 있는 부분. */
export interface ListenUpdate {
  final: string;
  interim: string;
}

/** 이 모듈이 쓰는 `SpeechRecognition` 의 좁은 면 — 시험은 같은 모양의 가짜를 넘김. */
export interface RecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: RecognitionResultEventLike) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  onaudiostart: (() => void) | null;
  start(): void;
  stop(): void;
  abort(): void;
}

export interface RecognitionResultEventLike {
  results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }>;
}

/** 시간을 다루는 자리 — 시험은 가짜 시계를 넘겨 실제로 기다리지 않음. */
export interface Clock {
  setTimeout(callback: () => void, ms: number): unknown;
  clearTimeout(handle: unknown): void;
}

export interface ListenOptions {
  signal: AbortSignal;
  /** 원문 낱말 수 — 조용함 기준을 고르는 데 씀. */
  expectedWords: number;
  maxMs: number;
  onUpdate?: (update: ListenUpdate) => void;
  /** 마이크 소리가 인식기에 들어오기 시작함 — 화면이 이때 「듣는 중」으로 바뀜(설계서 §3 ②). */
  onAudioStart?: () => void;
  /** 시험용 — 없으면 브라우저의 인식기·타이머를 씀. */
  create?: () => RecognitionLike;
  clock?: Clock;
}

type RecognitionConstructor = new () => RecognitionLike;

function recognitionConstructor(): RecognitionConstructor | null {
  if (typeof window === "undefined") return null;
  const scope = window as unknown as {
    SpeechRecognition?: RecognitionConstructor;
    webkitSpeechRecognition?: RecognitionConstructor;
  };
  return scope.SpeechRecognition ?? scope.webkitSpeechRecognition ?? null;
}

/** 이 브라우저에 인식기가 있는가 — 없으면(Firefox) 화면이 PCM 경로로 내려감(설계서 §7 ⑥). */
export function recognitionAvailable(): boolean {
  return recognitionConstructor() !== null;
}

export function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

/** 확정 낱말 수에 따른 조용함 기준(설계서 §4). */
export function quietThresholdMs(finalWords: number, expectedWords: number): number {
  return finalWords < expectedWords * SHORT_RATIO ? QUIET_LONG_MS : QUIET_MS;
}

/** 듣기 상한 — `max(8000, 읽은 시간 × 3)`(설계서 §4). PCM 경로의 녹음 창도 이 값을 씀(§7 ⑥). */
export function listenLimitMs(spokenMs: number): number {
  return Math.max(MIN_LISTEN_MS, spokenMs * 3);
}

// 한글 — 연습 대상은 영어 문장이므로 인식기가 영어 소리를 한글로 적은 조각은 뺌(`TASK-327`).
// ⚠️ 사용자 실기기(한국어 맥 · Chrome)에서 처음 표시 때 「Did you 디드 유」처럼 섞여 나왔음. 원인은 미확인.
const HANGUL = /[ㄱ-ㆎ가-힣]+/g;

/** 한글 조각을 빼고 공백을 하나로 모음. */
function withoutHangul(text: string): string {
  return text.replace(HANGUL, " ").replace(/\s+/g, " ").trim();
}

/** 글 조각을 한 칸 띄어 이음 — 빈 조각은 뺌. */
function joinText(...parts: string[]): string {
  return parts.map((part) => part.trim()).filter(Boolean).join(" ");
}

function readResults(event: RecognitionResultEventLike): ListenUpdate {
  const finals: string[] = [];
  const interims: string[] = [];
  for (let index = 0; index < event.results.length; index += 1) {
    const result = event.results[index];
    const text = withoutHangul(result[0]?.transcript ?? "");
    if (!text) continue;
    (result.isFinal ? finals : interims).push(text);
  }
  return { final: finals.join(" "), interim: interims.join(" ") };
}

// 인식기 오류의 갈래(설계서 §7) — 여기 없는 오류는 판정 불가로 봄.
const SILENT_ERRORS = new Set(["no-speech"]);
const DENIED_ERRORS = new Set(["not-allowed"]);

const defaultClock: Clock = {
  setTimeout: (callback, ms) => globalThis.setTimeout(callback, ms),
  clearTimeout: (handle) => globalThis.clearTimeout(handle as ReturnType<typeof setTimeout>),
};

/**
 * 한 번 듣고 결과 갈래를 돌려줌. 끝나는 길은 다섯임.
 *
 * - 확정 부분이 있고 마지막 결과 뒤로 조용함 기준만큼 지남 → `stop()` 뒤 남은 final 을 기다려 `heard`.
 * - 미확정만 있는 채로 조용해짐(기준은 긴 쪽) · `maxMs` → 그때까지의 글자로 `heard`.
 *   확정 뒤에 남은 미확정 꼬리도 이어 씀 — 빈 값·잘린 값보다 낫다는 판단임(설계서 §4).
 * - 멈추라 하지 않았는데 인식기가 끝남 → 새 인식기로 이어 들음(최대 `MAX_RESTARTS` 번). 모은 글자는 남음.
 * - 결과 없이 `NO_SPEECH_MS` · `no-speech` 오류 → `silent`. ⛔ 화면은 이때 서버에 보내지 않음(§11-1).
 * - `not-allowed` → `denied` · 그 밖의 오류·시작 실패 → `unavailable`.
 * - `signal` 이 끊김 → `abort()` 를 부르고 `aborted`.
 */
export function listen(options: ListenOptions): Promise<ListenOutcome> {
  const clock = options.clock ?? defaultClock;
  const create =
    options.create ??
    (() => {
      const Constructor = recognitionConstructor();
      if (!Constructor) throw new Error("SpeechRecognition is not available");
      return new Constructor();
    });
  if (options.signal.aborted) return Promise.resolve({ kind: "aborted" });

  return new Promise<ListenOutcome>((resolve) => {
    // 앞 인식기들이 확정한 글자 — 다시 시작해도 남음. 화면에 넘기는 `final` 은 이것 + 지금 인식기의 확정임.
    let committed = "";
    let latest: ListenUpdate = { final: "", interim: "" };
    let settled = false;
    let stopping = false;
    let restarts = 0;
    let quietTimer: unknown = null;
    let graceTimer: unknown = null;
    let recognition: RecognitionLike | null = null;

    const clearTimers = () => {
      for (const handle of [quietTimer, graceTimer, noSpeechTimer, maxTimer]) {
        if (handle !== null) clock.clearTimeout(handle);
      }
    };
    const detach = (target: RecognitionLike | null) => {
      if (!target) return;
      target.onresult = null;
      target.onerror = null;
      target.onend = null;
      target.onaudiostart = null;
    };
    const settle = (outcome: ListenOutcome) => {
      if (settled) return;
      settled = true;
      clearTimers();
      detach(recognition);
      options.signal.removeEventListener("abort", onAbort);
      resolve(outcome);
    };
    // ⛔ 확정 뒤에 남은 미확정 꼬리도 씀(codex 리뷰 MEDIUM) — 확정만 쓰면 마지막 낱말들이 빠졌음.
    const fromLatest = (): ListenOutcome => {
      const text = joinText(latest.final, latest.interim);
      return text ? { kind: "heard", text } : { kind: "silent" };
    };
    // 말 끝 — 인식기를 멈추고 남은 final 을 `FINAL_GRACE_MS` 까지 기다림. `onend` 가 먼저 오면 바로 끝냄.
    const finish = () => {
      if (settled || stopping) return;
      stopping = true;
      if (quietTimer !== null) clock.clearTimeout(quietTimer);
      graceTimer = clock.setTimeout(() => {
        recognition?.abort();
        settle(fromLatest());
      }, FINAL_GRACE_MS);
      try {
        recognition?.stop();
      } catch {
        settle(fromLatest());
      }
    };
    const onAbort = () => {
      recognition?.abort();
      settle({ kind: "aborted" });
    };

    /**
     * 인식기 하나를 만들어 켬. 처음과, 멈추라 하지 않았는데 끝났을 때(다시 시작) 부름.
     * ⛔ 앞 인식기의 처리기는 떼고, 처리기마다 자기 인식기가 지금 것인지 확인함 — 늦게 온 앞 인식기의
     *    이벤트가 글자를 덮거나 또 다시 시작하게 하지 않게 함(codex 리뷰 HIGH).
     */
    const begin = (): boolean => {
      let current: RecognitionLike;
      try {
        current = create();
      } catch {
        return false;
      }
      detach(recognition);
      recognition = current;
      const live = () => recognition === current && !settled;
      current.lang = "en-US";
      current.continuous = true;
      current.interimResults = true;
      current.onaudiostart = () => {
        if (live()) options.onAudioStart?.();
      };
      current.onresult = (event) => {
        if (!live()) return;
        const read = readResults(event);
        // 한글뿐인 결과는 들은 것으로 치지 않음 — 화면도 타이머도 건드리지 않아 말 없음 시한이 그대로 돎.
        if (!read.final && !read.interim) return;
        latest = { final: joinText(committed, read.final), interim: read.interim };
        options.onUpdate?.(latest);
        clock.clearTimeout(noSpeechTimer);
        if (stopping) return;
        if (quietTimer !== null) clock.clearTimeout(quietTimer);
        quietTimer = clock.setTimeout(
          finish,
          quietThresholdMs(wordCount(latest.final), options.expectedWords),
        );
      };
      current.onerror = (event) => {
        if (!live()) return;
        if (SILENT_ERRORS.has(event.error)) {
          // 들린 것이 있으면 그것으로 판정함 — Chrome 은 말이 끝난 뒤에도 이 오류를 낼 수 있음.
          settle(fromLatest());
        } else if (DENIED_ERRORS.has(event.error)) {
          settle({ kind: "denied" });
        } else if (event.error === "aborted" && (stopping || options.signal.aborted)) {
          settle(stopping ? fromLatest() : { kind: "aborted" });
        } else {
          settle({ kind: "unavailable" });
        }
      };
      current.onend = () => {
        if (!live()) return;
        // 멈추라 했거나(말 끝 · 상한) 다시 시작할 횟수를 다 썼으면 그때까지의 글자로 판정함.
        if (stopping || restarts >= MAX_RESTARTS) {
          settle(fromLatest());
          return;
        }
        // ⛔ Chrome 은 continuous 세션도 스스로 끝낼 수 있음 — 바로 판정하면 문장의 나머지를 잃고
        //    60 % 규칙도 쓰이지 않음. 들은 글자(미확정 포함)를 굳혀 두고 새 인식기로 이어 들음.
        restarts += 1;
        committed = joinText(latest.final, latest.interim);
        latest = { final: committed, interim: "" };
        if (!begin()) settle(fromLatest());
      };
      try {
        current.start();
      } catch {
        return false;
      }
      return true;
    };

    const noSpeechTimer: unknown = clock.setTimeout(() => {
      // 결과가 하나도 없었음 — 남은 final 을 기다릴 것이 없으므로 바로 끝냄.
      recognition?.abort();
      settle({ kind: "silent" });
    }, NO_SPEECH_MS);
    const maxTimer: unknown = clock.setTimeout(finish, options.maxMs);

    options.signal.addEventListener("abort", onAbort, { once: true });
    if (!begin()) settle({ kind: "unavailable" });
  });
}
