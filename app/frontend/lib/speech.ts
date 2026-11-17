/**
 * 문법 코스의 문장 읽기 — 브라우저 내장 음성 합성 (`TASK-286` · 설계서 §4).
 *
 * ⛔ **WAV 를 미리 만들지 않은 이유**: 문장 565개면 리포에 약 45MB 가 들어간다. 학습자의 브라우저가
 * 읽게 하면 자산이 0 이다.
 * ⚠️ **돌려주는 값이 「실제로 읽은 시간」이다** — 자동 모드가 그만큼 기다리므로(사용자 결정 4)
 * 어림이 아니라 잰 값을 쓴다. 음성 합성이 없거나 끝 신호가 오지 않으면 낱말 수로 어림한다.
 */

import { wordCountAt, wordSchedule } from "./speechHighlight";

const SECONDS_PER_WORD = 0.4;
// 끝 신호가 오지 않는 브라우저(헤드리스 등)에서 영원히 기다리지 않게 하는 상한.
const MAX_WAIT_FACTOR = 3;

export function estimateSpeechMs(text: string, rate = 1): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(800, (words * SECONDS_PER_WORD * 1000) / rate);
}

function pickVoice(synth: SpeechSynthesis): SpeechSynthesisVoice | null {
  const voices = synth.getVoices();
  return (
    voices.find((voice) => voice.lang === "en-US" && voice.localService) ??
    voices.find((voice) => voice.lang.startsWith("en")) ??
    null
  );
}

type SpeakOptions = {
  rate?: number;
  signal?: AbortSignal;
  /** 지금까지 읽기 시작한 낱말 수 — 읽어 주는 낱말 색칠에 씀(`TASK-348`). 끝나면 전체 낱말 수가 옴. */
  onWords?: (count: number) => void;
};

/**
 * 낱말 진행 알림 — 경계 신호가 오면 그것을 따르고, 오지 않으면 어림 시간에 비례한 일정으로 알림(`TASK-348`).
 * ⚠️ 경계 신호가 한 번이라도 오면 일정 타이머는 멈춤 — 둘이 섞이면 색칠이 앞뒤로 흔들림.
 */
function wordProgress(text: string, estimate: number, onWords?: (count: number) => void) {
  const timers: ReturnType<typeof setTimeout>[] = [];
  let shown = 0;
  let started = false;
  let heardBoundary = false;
  const show = (count: number) => {
    if (!onWords || count <= shown) return;
    shown = count;
    onWords(count);
  };
  const stopTimers = () => timers.splice(0).forEach(clearTimeout);
  return {
    /**
     * 소리가 시작될 때 일정을 켬(`TASK-349` codex 리뷰 MEDIUM) — `speak()` 를 부른 때 켜면 합성이 늦게 시작하는
     * 기기에서 소리보다 색칠이 앞섰음. 경계 신호가 이미 왔으면 켜지 않음.
     */
    start() {
      if (started || heardBoundary) return;
      started = true;
      wordSchedule(text, estimate).forEach((at, index) => timers.push(setTimeout(() => show(index + 1), at)));
    },
    boundary(charIndex: number) {
      heardBoundary = true;
      stopTimers();
      show(wordCountAt(text, charIndex));
    },
    end() {
      stopTimers();
      show(wordCountAt(text, Number.MAX_SAFE_INTEGER));
    },
    cancel: stopTimers,
  };
}

/** 문장을 읽고, 읽은 시간(ms)을 돌려준다. `signal` 이 끊기면 바로 멈추고 어림값을 돌려준다. */
export function speak(text: string, options: SpeakOptions = {}): Promise<number> {
  const rate = options.rate ?? 1;
  const estimate = estimateSpeechMs(text, rate);
  const synth = typeof window !== "undefined" ? window.speechSynthesis : undefined;
  if (!synth || typeof SpeechSynthesisUtterance === "undefined") {
    const progress = wordProgress(text, estimate, options.onWords);
    progress.start();
    // ⛔ 끊기면 바로 끝냄(`TASK-349` codex 리뷰 LOW) — 끊겨도 어림 시간 뒤에 풀려 새 연습의 색칠을 지웠음.
    return new Promise((resolve) => {
      const timer = setTimeout(() => {
        options.signal?.removeEventListener("abort", onAbort);
        progress.end();
        resolve(estimate);
      }, estimate);
      const onAbort = () => {
        clearTimeout(timer);
        progress.cancel();
        resolve(estimate);
      };
      if (options.signal?.aborted) onAbort();
      else options.signal?.addEventListener("abort", onAbort, { once: true });
    });
  }
  return new Promise((resolve) => {
    const progress = wordProgress(text, estimate, options.onWords);
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "en-US";
    utterance.rate = rate;
    const voice = pickVoice(synth);
    if (voice) utterance.voice = voice;
    let startedAt: number | null = null;
    let settled = false;
    const finish = (measured: number | null) => {
      if (settled) return;
      settled = true;
      clearTimeout(guard);
      options.signal?.removeEventListener("abort", onAbort);
      if (measured === null && options.signal?.aborted) progress.cancel();
      else progress.end();
      resolve(measured !== null && measured > 200 ? measured : estimate);
    };
    const onAbort = () => {
      synth.cancel();
      finish(null);
    };
    const guard = setTimeout(() => finish(null), estimate * MAX_WAIT_FACTOR);
    utterance.onstart = () => {
      startedAt = performance.now();
      progress.start();
    };
    utterance.onboundary = (event) => {
      // 낱말 경계만 씀 — 문장 경계(`sentence`)는 색칠 위치가 아님. 이름이 비어 오는 브라우저는 낱말로 봄.
      if (!event.name || event.name === "word") progress.boundary(event.charIndex);
    };
    utterance.onend = () => finish(startedAt === null ? null : performance.now() - startedAt);
    utterance.onerror = () => finish(null);
    options.signal?.addEventListener("abort", onAbort, { once: true });
    synth.cancel();
    synth.speak(utterance);
  });
}

export function stopSpeaking(): void {
  if (typeof window !== "undefined") window.speechSynthesis?.cancel();
}
