"use client";

// 문법 코스의 문장 연습 칸 — Day 화면의 영상 «아래» 부분 (`TASK-286` 에서 시작 · `TASK-304` 에서 분리).
// 설계서 `docs/design/2026-10-26-grammar-course-design.md` §4·§7 · 리디자인 설계서 §3(`TASK-304`).
//
// 한 문장을 크게 보여 주고 읽어 준 뒤, 학습자가 따라 말한 문장을 그 아래에 보임(사용자 결정 2).
// 자동 모드는 「읽기 → 읽은 시간 + 1초 동안 녹음 → 판정 → 다음 문장」을 스스로 잇고, 수동 모드는
// 판정 뒤에 멈춤(사용자 결정 4).
//
// ⛔ 쓰는 자리가 둘임 — Day 화면(`app/course/[day]/page.tsx`)은 영상 핸들을 넘기고, 홈의 오늘의 연습
//    카드는 넘기지 않음. 영상이 없어도 연습·판정·진도 저장은 같게 돎.
// ⛔ 영상이 있으면 문장 연습이 도는 동안 영상을 멈춤 — 마이크가 영상 소리를 받으면 판정이 그 소리를
//    전사함. 영상을 다시 재생하면 연습이 멈춤(`videoPlaying`).
// ⛔ 영상이 없으면 저장하는 재생 위치는 불러온 진도의 `position_sec` 그대로임 — Day 를 마친 때만 0 임.
//    0 을 보내면 Day 화면의 영상이 다음에 처음부터 열림.
// ⚠️ 문장은 영상·교재의 문장이 아님 — 단원의 문법 패턴으로 새로 쓴 문장임(설계서 §2).
// ⚠️ `data-testid`(`course-*`)·`data-phase`·`data-attempts`·`data-verdict` 는 이 칸이 가짐 — 어느 자리에
//    그려도 같은 이름임. 부모는 Day 가 바뀌면 `key` 로 이 칸을 새로 마운트해야 함(첫 렌더에서만 진도를 읽음).

import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type RefObject,
} from "react";
import { postCourseAttempt, saveCourseProgress, type CourseDayDetail, type ReadbackWord } from "@/lib/api";
import { VoiceIo } from "@/lib/audio";
import { speak, stopSpeaking } from "@/lib/speech";
import type { CoursePlayerHandle } from "@/app/course/[day]/CoursePlayer";

type Mode = "auto" | "manual";
type Phase = "idle" | "listen" | "repeat" | "judge" | "done";
type Position = { unitIndex: number; sentenceIndex: number };

const MODE_STORAGE_KEY = "omy.course.mode";
const EXTRA_WAIT_MS = 1000; // 따라 말하기 시작까지의 틈 (설계서 §4)
const ADVANCE_DELAY_MS = 1500; // 판정을 보여 준 뒤 다음 문장까지
const SAVE_EVERY_MS = 5000;
const SLOW_RATE = 0.7;

const NOTICE = {
  mic: "I can't use the mic. Please allow the mic in your browser.",
  unavailable: "I can't check your speaking now. You can keep going.",
  unheard: "I couldn't hear you. Press \"Try again\" and say it again.",
  video: "This video can't play here right now.",
  dayDone: "You finished this Day!",
} as const;

const PHASE_LABEL: Record<Exclude<Phase, "idle">, string> = {
  listen: "① Listen",
  repeat: "② Say it",
  judge: "③ Check",
  done: "③ Check",
};

/** 영상 쪽에서 이 칸으로 오는 알림 셋 — Day 화면이 `CoursePlayer` 의 이벤트를 그대로 넘김. */
export interface SentencePracticeHandle {
  /** 영상이 재생되기 시작함 — 도는 연습을 멈춤. */
  videoPlaying(): void;
  /** 영상이 끝남 — Day 를 마침(설계서 §4). */
  videoEnded(): void;
  /** 영상을 쓸 수 없음 — 안내만 보이고 연습은 이어짐. */
  videoUnavailable(): void;
}

interface Props {
  detail: CourseDayDetail;
  day: number;
  /** Day 화면의 영상 핸들. 없으면(홈) 영상 없이 돎. */
  player?: RefObject<CoursePlayerHandle | null>;
  /** Day 를 마친 직후 — 홈이 코스 개요(현재 Day·완료 수)를 다시 읽게 함(회차 b12 D1). */
  onDayFinished?: () => void;
}

function readMode(): Mode {
  if (typeof window === "undefined") return "auto";
  return window.localStorage.getItem(MODE_STORAGE_KEY) === "manual" ? "manual" : "auto";
}

function sleep(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        resolve();
      },
      { once: true },
    );
  });
}

function joinPcm(chunks: Uint8Array[]): Uint8Array {
  const total = chunks.reduce((sum, chunk) => sum + chunk.byteLength, 0);
  const out = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    out.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return out;
}

/** 저장된 진도가 가리키는 자리. 단원을 찾지 못하면 첫 단원임. */
function savedPosition(detail: CourseDayDetail): Position {
  const saved = detail.progress;
  if (!saved) return { unitIndex: 0, sentenceIndex: 0 };
  return {
    unitIndex: Math.max(0, detail.units.findIndex((unit) => unit.unit === saved.unit)),
    sentenceIndex: saved.sentence_index ?? 0,
  };
}

function Spoken({ words, transcript }: { words: ReadbackWord[]; transcript: string }) {
  return (
    <div
      data-testid="course-spoken"
      style={{ marginTop: 12, padding: "10px 12px", borderRadius: 10, background: "var(--accent-soft)" }}
    >
      <span style={{ display: "block", fontSize: "0.72rem", color: "var(--foreground-muted)" }}>
        You said:
      </span>
      <span data-testid="course-transcript">{transcript}</span>
      {words.length > 0 ? (
        <div style={{ marginTop: 4, fontSize: "0.85rem" }}>
          {words.map((item, index) => (
            <span
              key={`${item.word}-${index}`}
              data-verdict={item.verdict}
              style={{
                marginRight: 4,
                textDecoration:
                  item.verdict === "missing"
                    ? "line-through"
                    : item.verdict === "different"
                      ? "underline"
                      : "none",
                color: item.verdict === "missing" ? "var(--foreground-muted)" : "var(--foreground)",
              }}
            >
              {item.word}
            </span>
          ))}
          <span style={{ display: "block", fontSize: "0.72rem", color: "var(--foreground-muted)" }}>
            Underline: you said a different word. Strikethrough: you missed the word.
          </span>
        </div>
      ) : null}
    </div>
  );
}

export const SentencePractice = forwardRef<SentencePracticeHandle, Props>(function SentencePractice(
  { detail, day, player, onDayFinished },
  ref,
) {
  const [unitIndex, setUnitIndex] = useState(() => savedPosition(detail).unitIndex);
  const [sentenceIndex, setSentenceIndex] = useState(() => savedPosition(detail).sentenceIndex);
  const [mode, setMode] = useState<Mode>(readMode);
  const [phase, setPhase] = useState<Phase>("idle");
  const [waitMs, setWaitMs] = useState(0);
  const [result, setResult] = useState<{ transcript: string; words: ReadbackWord[] } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>(() =>
    Object.fromEntries(detail.units.flatMap((unit) => unit.sentences.map((item) => [item.key, item.attempts]))),
  );
  const [videoUnit, setVideoUnit] = useState<number | null>(null);

  const runRef = useRef<AbortController | null>(null);
  const voiceRef = useRef<VoiceIo | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recordRef = useRef<Uint8Array[] | null>(null);
  // 진행 중인 마이크 획득 — 두 연습이 동시에 getUserMedia 를 부르면 스트림 하나가 버려진 채 켜져 남음.
  const micRef = useRef<Promise<boolean> | null>(null);
  const mountedRef = useRef(true);
  const positionRef = useRef<Position>(savedPosition(detail));
  // 화면이 아는 완료 횟수 — 저장마다 보내 서버가 완료 전에 보낸 늦은 저장을 버리게 함(TASK-287).
  const completedRef = useRef(detail.progress?.completed_count ?? 0);
  // 핸들이 살아 있을 때 읽은 마지막 재생 위치(회차 b3·b4 D3) — React 는 언마운트 때 ref 를 effect 정리보다
  // 먼저 떼므로, 언마운트 저장 시점에는 영상 핸들이 이미 null 임. 영상이 없는 자리(홈)에서는 불러온
  // 진도의 위치가 끝까지 이 값으로 남음 — 그래서 저장이 Day 화면의 영상 위치를 0 으로 덮지 않음.
  const lastTimeRef = useRef(detail.progress?.position_sec ?? 0);

  useEffect(() => {
    positionRef.current = { unitIndex, sentenceIndex };
  }, [unitIndex, sentenceIndex]);

  const unit = detail.units[unitIndex] ?? null;
  const sentence = unit?.sentences[sentenceIndex] ?? null;

  // Day 를 끝냈을 때 — 서버는 처음으로 되감으므로 화면도 처음으로 되감음(codex 리뷰 HIGH 2).
  // ⛔ 되감지 않으면 이어지는 5초 저장·언마운트 저장이 끝 위치를 다시 써서 다음 회차가 끝 근처에서 열림.
  const rewindAfterCompletion = useCallback(() => {
    player?.current?.rewind();
    lastTimeRef.current = 0;
    positionRef.current = { unitIndex: 0, sentenceIndex: 0 };
    setUnitIndex(0);
    setSentenceIndex(0);
    setResult(null);
  }, [player]);

  const save = useCallback(
    (completed = false) => {
      const position = positionRef.current;
      const current = detail.units[position.unitIndex];
      if (!current) return;
      const live = player?.current?.currentTime();
      if (live !== undefined) lastTimeRef.current = live;
      void saveCourseProgress(day, {
        positionSec: completed ? 0 : lastTimeRef.current,
        unit: completed ? detail.units[0].unit : current.unit,
        sentenceIndex: completed ? 0 : position.sentenceIndex,
        completed,
        completedCount: completedRef.current,
      });
      if (completed) completedRef.current += 1;
    },
    [day, detail, player],
  );

  // 진도를 5초마다 저장하고, 영상이 있으면 영상이 지나는 단원을 읽음. 화면을 떠날 때도 한 번 저장함.
  useEffect(() => {
    const timer = setInterval(() => {
      const handle = player?.current;
      if (handle) {
        const time = handle.currentTime();
        const found = detail.units.find((item) => time < item.end_sec) ?? detail.units.at(-1);
        setVideoUnit(found?.unit ?? null);
      }
      save();
    }, SAVE_EVERY_MS);
    const onLeave = () => save();
    window.addEventListener("pagehide", onLeave);
    return () => {
      clearInterval(timer);
      window.removeEventListener("pagehide", onLeave);
      save();
    };
  }, [detail, player, save]);

  const cancelRun = useCallback(() => {
    runRef.current?.abort();
    runRef.current = null;
    recordRef.current = null;
    stopSpeaking();
  }, []);

  // Day 완료 — 영상이 끝났거나 마지막 문장을 마쳤을 때(설계서 §4). 자동·수동·영상 세 경로가 함께 씀.
  const finishDay = useCallback(() => {
    cancelRun();
    setPhase("idle");
    save(true);
    rewindAfterCompletion();
    setNotice(NOTICE.dayDone);
    // 완료 저장은 기다리지 않지만, 코스 조회(`fetchCourse`)가 진행 중인 저장을 기다리므로 새 값을 읽음.
    onDayFinished?.();
  }, [cancelRun, onDayFinished, rewindAfterCompletion, save]);

  // 언마운트 — 연습과 마이크를 모두 정리함.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cancelRun();
      void voiceRef.current?.close();
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, [cancelRun]);

  // ⛔ 획득을 한 번만 하고, 칸이 내려간 뒤 끝난 획득은 바로 닫음(codex 리뷰 HIGH 1) — 권한 대기 중에
  //    떠나면 언마운트 정리가 먼저 돌아, 뒤늦게 붙은 스트림이 켜진 채 남았음.
  const ensureMic = useCallback((): Promise<boolean> => {
    if (voiceRef.current) return Promise.resolve(true);
    if (micRef.current) return micRef.current;
    const pending = (async () => {
      let stream: MediaStream | null = null;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const voice = await VoiceIo.start(stream, (frame) => {
          recordRef.current?.push(frame.slice());
        });
        if (!mountedRef.current) {
          void voice.close();
          stream.getTracks().forEach((track) => track.stop());
          return false;
        }
        streamRef.current = stream;
        voiceRef.current = voice;
        return true;
      } catch {
        stream?.getTracks().forEach((track) => track.stop());
        if (mountedRef.current) setNotice(NOTICE.mic);
        return false;
      } finally {
        micRef.current = null;
      }
    })();
    micRef.current = pending;
    return pending;
  }, []);

  /** 다음 자리 — 단원의 마지막 문장 뒤는 다음 단원의 첫 문장임. Day 끝이면 `null`. */
  const nextPosition = useCallback(
    (from: Position): Position | null => {
      const current = detail.units[from.unitIndex];
      if (from.sentenceIndex + 1 < current.sentences.length) {
        return { unitIndex: from.unitIndex, sentenceIndex: from.sentenceIndex + 1 };
      }
      if (from.unitIndex + 1 < detail.units.length) {
        return { unitIndex: from.unitIndex + 1, sentenceIndex: 0 };
      }
      return null;
    },
    [detail],
  );

  const run = useCallback(
    async (start: Position, rate = 1) => {
      cancelRun();
      const controller = new AbortController();
      runRef.current = controller;
      const { signal } = controller;
      player?.current?.pause();
      setNotice(null);
      const micReady = await ensureMic();
      // ⚠️ 끊긴 연습은 화면 상태를 건드리지 않음 — 그 사이 시작된 새 연습의 단계를 덮게 됨.
      if (signal.aborted) return;
      if (!micReady) {
        setPhase("idle");
        return;
      }
      let position = start;
      for (;;) {
        const item = detail.units[position.unitIndex].sentences[position.sentenceIndex];
        setUnitIndex(position.unitIndex);
        setSentenceIndex(position.sentenceIndex);
        positionRef.current = position;
        setResult(null);
        // 앞 문장의 안내(안 들렸어요 · 판정을 쓸 수 없어요)가 이 문장의 결과로 읽히지 않게 지움(회차 b7).
        setNotice(null);

        setPhase("listen");
        const spokenMs = await speak(item.text, { rate, signal });
        if (signal.aborted) return;

        const windowMs = spokenMs + EXTRA_WAIT_MS;
        setWaitMs(windowMs);
        setPhase("repeat");
        recordRef.current = [];
        await sleep(windowMs, signal);
        const chunks = recordRef.current ?? [];
        recordRef.current = null;
        if (signal.aborted) return;

        setPhase("judge");
        const pcm = joinPcm(chunks);
        const judged = pcm.byteLength > 0 ? await postCourseAttempt(item.key, pcm) : null;
        if (signal.aborted) return;
        if (judged?.ok) {
          setResult({ transcript: judged.value.transcript, words: judged.value.words });
          setCounts((prev) => ({ ...prev, [item.key]: judged.value.attempts }));
          setNotice(judged.value.transcript ? null : NOTICE.unheard);
        } else {
          setNotice(NOTICE.unavailable);
        }
        setPhase("done");
        save();

        if (readMode() !== "auto") return;
        await sleep(ADVANCE_DELAY_MS, signal);
        if (signal.aborted) return;
        const next = nextPosition(position);
        if (next === null) {
          finishDay();
          return;
        }
        position = next;
        rate = 1;
      }
    },
    [cancelRun, detail, ensureMic, finishDay, nextPosition, player, save],
  );

  const chooseMode = useCallback((value: Mode) => {
    window.localStorage.setItem(MODE_STORAGE_KEY, value);
    setMode(value);
  }, []);

  const goTo = useCallback(
    (target: Position | null) => {
      if (!target) return;
      cancelRun();
      setResult(null);
      // 앞 문장의 안내가 이 문장의 결과로 읽히지 않게 지움 — 자동 흐름과 같은 규칙(회차 b9 관찰).
      setNotice(null);
      setPhase("idle");
      setUnitIndex(target.unitIndex);
      setSentenceIndex(target.sentenceIndex);
      positionRef.current = target;
      save();
      if (mode === "auto") void run(target);
    },
    [cancelRun, mode, run, save],
  );

  const previous = useMemo((): Position | null => {
    if (sentenceIndex > 0) return { unitIndex, sentenceIndex: sentenceIndex - 1 };
    if (unitIndex > 0) {
      return { unitIndex: unitIndex - 1, sentenceIndex: detail.units[unitIndex - 1].sentences.length - 1 };
    }
    return null;
  }, [detail, unitIndex, sentenceIndex]);

  // 영상을 다시 재생하면 연습을 멈춤. 연습이 쉬고 있으면 영상이 지나는 단원으로 옮길 길을 보임.
  const videoPlaying = useCallback(() => {
    if (runRef.current) {
      cancelRun();
      setPhase("idle");
    }
  }, [cancelRun]);

  const videoUnavailable = useCallback(() => setNotice(NOTICE.video), []);

  useImperativeHandle(
    ref,
    () => ({ videoPlaying, videoEnded: finishDay, videoUnavailable }),
    [videoPlaying, finishDay, videoUnavailable],
  );

  const followVideo = useMemo(() => {
    if (videoUnit === null || phase !== "idle") return null;
    const index = detail.units.findIndex((item) => item.unit === videoUnit);
    return index >= 0 && index !== unitIndex ? index : null;
  }, [detail, videoUnit, phase, unitIndex]);

  if (!unit || !sentence) {
    return <p>Loading…</p>;
  }
  // 마지막 문장에서는 「다음 문장」 자리가 「Day 마치기」가 됨 — 수동 모드가 Day 를 끝낼 길(회차 b3 D4).
  const hasNext = nextPosition({ unitIndex, sentenceIndex }) !== null;

  const button = {
    padding: "7px 13px",
    borderRadius: 8,
    border: "1px solid var(--border)",
    background: "var(--surface)",
    color: "var(--foreground)",
    fontSize: "0.85rem",
  } as const;
  const primaryButton = {
    ...button,
    background: "var(--accent)",
    color: "var(--on-accent)",
    borderColor: "var(--accent)",
  } as const;

  return (
    <div data-testid="sentence-practice">
      {followVideo !== null ? (
        <button
          type="button"
          onClick={() => goTo({ unitIndex: followVideo, sentenceIndex: 0 })}
          style={{ ...button, marginTop: 8 }}
        >
          Go to Unit {detail.units[followVideo].unit} (where the video is)
        </button>
      ) : null}

      <div style={{ marginTop: 14, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span data-testid="course-unit" style={{ fontSize: "0.85rem", color: "var(--foreground-muted)" }}>
          Unit {unit.unit} · {unit.topic}
        </span>
        <span role="group" aria-label="Mode" style={{ display: "inline-flex", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
          {(["auto", "manual"] as const).map((value) => (
            <button
              key={value}
              type="button"
              data-testid={`course-mode-${value}`}
              aria-pressed={mode === value}
              onClick={() => chooseMode(value)}
              style={{
                padding: "4px 12px",
                fontSize: "0.8rem",
                border: 0,
                background: mode === value ? "var(--accent)" : "transparent",
                color: mode === value ? "var(--on-accent)" : "var(--foreground)",
              }}
            >
              {value === "auto" ? "Auto" : "Manual"}
            </button>
          ))}
        </span>
      </div>

      <section
        data-testid="course-card"
        style={{ marginTop: 8, border: "1px solid var(--border)", borderRadius: 14, padding: 16 }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "var(--foreground-muted)" }}>
          <span data-testid="course-sentence-number">
            Sentence {sentenceIndex + 1} / {unit.sentences.length}
          </span>
          <span data-testid="course-attempts">Try {counts[sentence.key] ?? 0}</span>
        </div>
        {phase !== "idle" ? (
          <div data-testid="course-phase" data-phase={phase} style={{ marginTop: 8, fontSize: "0.75rem" }}>
            {PHASE_LABEL[phase]}
            {phase === "repeat" ? ` · ${(waitMs / 1000).toFixed(1)}s` : null}
          </div>
        ) : null}
        {phase === "repeat" ? (
          <div style={{ height: 4, borderRadius: 99, background: "var(--surface)", marginTop: 6, overflow: "hidden" }}>
            <div
              key={`${sentence.key}-${waitMs}`}
              className="omy-course-wait"
              style={{ height: "100%", background: "var(--accent)", animationDuration: `${waitMs}ms` }}
            />
          </div>
        ) : null}
        <p data-testid="course-sentence" style={{ fontSize: "1.25rem", fontWeight: 600, marginTop: 8 }}>
          {sentence.text}
        </p>
        <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
          <button type="button" data-testid="course-listen" style={button} onClick={() => void run(positionRef.current)}>
            🔊 Listen
          </button>
          <button
            type="button"
            data-testid="course-slow"
            style={button}
            onClick={() => void run(positionRef.current, SLOW_RATE)}
          >
            Slow
          </button>
        </div>
        {result ? <Spoken words={result.words} transcript={result.transcript} /> : null}
        {phase === "repeat" ? (
          <p style={{ marginTop: 10, fontSize: "0.85rem", color: "var(--foreground-muted)" }}>
            {"I'm listening. Say it, and you will see it below."}
          </p>
        ) : null}
        {notice ? (
          <p data-testid="course-notice" style={{ marginTop: 10, fontSize: "0.85rem" }}>
            {notice}
          </p>
        ) : null}
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 14 }}>
          <button
            type="button"
            data-testid="course-prev"
            style={button}
            disabled={!previous}
            onClick={() => goTo(previous)}
          >
            ← Back
          </button>
          {/* 같은 자리의 두 상태를 testid 로 가름(리디자인 설계서 §4) — 문구에 기대지 않게 함. */}
          {phase === "idle" ? (
            <button type="button" data-testid="course-start" style={button} onClick={() => void run(positionRef.current)}>
              Start
            </button>
          ) : (
            <button type="button" data-testid="course-retry" style={button} onClick={() => void run(positionRef.current)}>
              Try again
            </button>
          )}
          {hasNext ? (
            <button
              type="button"
              data-testid="course-next"
              style={primaryButton}
              onClick={() => goTo(nextPosition({ unitIndex, sentenceIndex }))}
            >
              Next →
            </button>
          ) : (
            <button
              type="button"
              data-testid="course-finish"
              style={primaryButton}
              disabled={phase !== "done"}
              onClick={() => finishDay()}
            >
              Finish Day
            </button>
          )}
        </div>
      </section>
    </div>
  );
});
