"use client";

// 문법 코스 — 학습 화면 (`TASK-286` · 설계서 `docs/design/2026-10-26-grammar-course-design.md` §7).
//
// 한 문장을 크게 보여 주고 읽어 준 뒤, 학습자가 따라 말한 문장을 그 아래에 보인다(사용자 결정 2).
// 자동 모드는 「읽기 → 읽은 시간 + 1초 동안 녹음 → 판정 → 다음 문장」을 스스로 잇고, 수동 모드는
// 판정 뒤에 멈춘다(사용자 결정 4).
//
// ⛔ **문장 연습이 도는 동안 영상을 멈춘다** — 마이크가 영상 소리를 받으면 판정이 그 소리를 전사한다.
// 영상을 다시 재생하면 연습이 멈춘다. 둘이 같은 스피커·마이크를 두고 다투지 않게 하는 규칙이다.
// ⚠️ 문장은 영상·교재의 문장이 아니다 — 단원의 문법 패턴으로 새로 쓴 문장이다(설계서 §2).

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  fetchCourseDay,
  postCourseAttempt,
  saveCourseProgress,
  type CourseDayDetail,
  type ReadbackWord,
} from "@/lib/api";
import { VoiceIo } from "@/lib/audio";
import { speak, stopSpeaking } from "@/lib/speech";
import { CoursePlayer, type CoursePlayerHandle } from "./CoursePlayer";

type Mode = "auto" | "manual";
type Phase = "idle" | "listen" | "repeat" | "judge" | "done";

const MODE_STORAGE_KEY = "omy.course.mode";
const EXTRA_WAIT_MS = 1000; // 따라 말하기 시작까지의 틈 (설계서 §4)
const ADVANCE_DELAY_MS = 1500; // 판정을 보여 준 뒤 다음 문장까지
const SAVE_EVERY_MS = 5000;
const SLOW_RATE = 0.7;

const PAGE_STYLE = {
  maxWidth: 640,
  margin: "0 auto",
  padding: "2rem",
} as const;

const NOTICE = {
  mic: "I can't use the mic. Please allow the mic in your browser.",
  unavailable: "I can't check your speaking now. You can keep going.",
  unheard: "I couldn't hear you. Press \"Try again\" and say it again.",
  video: "This video can't play here right now.",
  dayDone: "You finished this Day!",
  loadFailed: "I couldn't load this Day.",
} as const;

const PHASE_LABEL: Record<Exclude<Phase, "idle">, string> = {
  listen: "① Listen",
  repeat: "② Say it",
  judge: "③ Check",
  done: "③ Check",
};

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

export default function CourseDayPage() {
  const params = useParams<{ day: string }>();
  const day = Number(params.day);
  const [detail, setDetail] = useState<CourseDayDetail | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [unitIndex, setUnitIndex] = useState(0);
  const [sentenceIndex, setSentenceIndex] = useState(0);
  const [mode, setMode] = useState<Mode>(readMode);
  const [phase, setPhase] = useState<Phase>("idle");
  const [waitMs, setWaitMs] = useState(0);
  const [result, setResult] = useState<{ transcript: string; words: ReadbackWord[] } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [videoUnit, setVideoUnit] = useState<number | null>(null);

  const playerRef = useRef<CoursePlayerHandle | null>(null);
  const runRef = useRef<AbortController | null>(null);
  const voiceRef = useRef<VoiceIo | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recordRef = useRef<Uint8Array[] | null>(null);
  // 진행 중인 마이크 획득 — 두 연습이 동시에 getUserMedia 를 부르면 스트림 하나가 버려진 채 켜져 남는다.
  const micRef = useRef<Promise<boolean> | null>(null);
  const mountedRef = useRef(true);
  const positionRef = useRef({ unitIndex: 0, sentenceIndex: 0 });
  // 화면이 아는 완료 횟수 — 저장마다 보내 서버가 완료 전에 보낸 늦은 저장을 버리게 한다(TASK-287).
  const completedRef = useRef(0);
  // 핸들이 살아 있을 때 읽은 마지막 재생 위치(회차 b3·b4 D3) — React 는 언마운트 때 ref 를 effect 정리보다
  // 먼저 떼므로, 언마운트 저장 시점에는 `playerRef.current` 가 이미 null 이다.
  const lastTimeRef = useRef(0);

  useEffect(() => {
    positionRef.current = { unitIndex, sentenceIndex };
  }, [unitIndex, sentenceIndex]);

  // Day 를 읽고 저장된 자리로 옮긴다.
  useEffect(() => {
    let cancelled = false;
    fetchCourseDay(day)
      .then((value) => {
        if (cancelled) return;
        if (!value) {
          setLoadFailed(true);
          return;
        }
        const saved = value.progress;
        const index = saved ? Math.max(0, value.units.findIndex((unit) => unit.unit === saved.unit)) : 0;
        completedRef.current = saved?.completed_count ?? 0;
        lastTimeRef.current = saved?.position_sec ?? 0;
        setDetail(value);
        setUnitIndex(index);
        setSentenceIndex(saved?.sentence_index ?? 0);
        setCounts(
          Object.fromEntries(
            value.units.flatMap((unit) => unit.sentences.map((item) => [item.key, item.attempts])),
          ),
        );
      })
      .catch(() => {
        if (!cancelled) setLoadFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [day]);

  const unit = detail?.units[unitIndex] ?? null;
  const sentence = unit?.sentences[sentenceIndex] ?? null;
  const startAt = useMemo(() => detail?.progress?.position_sec ?? 0, [detail]);

  // Day 를 끝냈을 때 — 서버는 처음으로 되감으므로 화면도 처음으로 되감는다(codex 리뷰 HIGH 2).
  // ⛔ 되감지 않으면 이어지는 5초 저장·언마운트 저장이 끝 위치를 다시 써서 다음 회차가 끝 근처에서 열린다.
  const rewindAfterCompletion = useCallback(() => {
    playerRef.current?.rewind();
    lastTimeRef.current = 0;
    positionRef.current = { unitIndex: 0, sentenceIndex: 0 };
    setUnitIndex(0);
    setSentenceIndex(0);
    setResult(null);
  }, []);

  const save = useCallback(
    (completed = false) => {
      if (!detail) return;
      const position = positionRef.current;
      const current = detail.units[position.unitIndex];
      if (!current) return;
      const live = playerRef.current?.currentTime();
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
    [day, detail],
  );

  // 재생 위치를 5초마다 저장하고, 영상이 지나는 단원을 읽는다. 화면을 떠날 때도 한 번 저장한다.
  useEffect(() => {
    if (!detail) return;
    const timer = setInterval(() => {
      const time = playerRef.current?.currentTime() ?? 0;
      const found = detail.units.find((item) => time < item.end_sec) ?? detail.units.at(-1);
      setVideoUnit(found?.unit ?? null);
      save();
    }, SAVE_EVERY_MS);
    const onLeave = () => save();
    window.addEventListener("pagehide", onLeave);
    return () => {
      clearInterval(timer);
      window.removeEventListener("pagehide", onLeave);
      save();
    };
  }, [detail, save]);

  const cancelRun = useCallback(() => {
    runRef.current?.abort();
    runRef.current = null;
    recordRef.current = null;
    stopSpeaking();
  }, []);

  // Day 완료 — 영상이 끝났거나 마지막 문장을 마쳤을 때(설계서 §4). 자동·수동·영상 세 경로가 함께 쓴다.
  const finishDay = useCallback(() => {
    cancelRun();
    setPhase("idle");
    save(true);
    rewindAfterCompletion();
    setNotice(NOTICE.dayDone);
  }, [cancelRun, rewindAfterCompletion, save]);

  // 언마운트 — 연습과 마이크를 모두 정리한다.
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      cancelRun();
      void voiceRef.current?.close();
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, [cancelRun]);

  // ⛔ **획득을 한 번만 하고, 화면을 떠난 뒤 끝난 획득은 바로 닫는다**(codex 리뷰 HIGH 1) — 권한
  // 대기 중에 떠나면 언마운트 정리가 먼저 돌아, 뒤늦게 붙은 스트림이 켜진 채 남았다.
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

  /** 다음 자리 — 단원의 마지막 문장 뒤는 다음 단원의 첫 문장이다. Day 끝이면 `null`. */
  const nextPosition = useCallback(
    (from: { unitIndex: number; sentenceIndex: number }) => {
      if (!detail) return null;
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
    async (start: { unitIndex: number; sentenceIndex: number }, rate = 1) => {
      if (!detail) return;
      cancelRun();
      const controller = new AbortController();
      runRef.current = controller;
      const { signal } = controller;
      playerRef.current?.pause();
      setNotice(null);
      const micReady = await ensureMic();
      // ⚠️ 끊긴 연습은 화면 상태를 건드리지 않는다 — 그 사이 시작된 새 연습의 단계를 덮게 된다.
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
        // 앞 문장의 안내(안 들렸어요 · 판정을 쓸 수 없어요)가 이 문장의 결과로 읽히지 않게 지운다(회차 b7).
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
    [cancelRun, detail, ensureMic, finishDay, nextPosition, save],
  );

  const chooseMode = useCallback((value: Mode) => {
    window.localStorage.setItem(MODE_STORAGE_KEY, value);
    setMode(value);
  }, []);

  const goTo = useCallback(
    (target: { unitIndex: number; sentenceIndex: number } | null) => {
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

  const previous = useMemo(() => {
    if (!detail) return null;
    if (sentenceIndex > 0) return { unitIndex, sentenceIndex: sentenceIndex - 1 };
    if (unitIndex > 0) {
      return { unitIndex: unitIndex - 1, sentenceIndex: detail.units[unitIndex - 1].sentences.length - 1 };
    }
    return null;
  }, [detail, unitIndex, sentenceIndex]);

  // 영상을 다시 재생하면 연습을 멈추고, 연습이 쉬고 있으면 영상이 지나는 단원으로 문장을 옮긴다.
  const onVideoPlaying = useCallback(() => {
    if (runRef.current) {
      cancelRun();
      setPhase("idle");
    }
  }, [cancelRun]);

  const followVideo = useMemo(() => {
    if (!detail || videoUnit === null || phase !== "idle") return null;
    const index = detail.units.findIndex((item) => item.unit === videoUnit);
    return index >= 0 && index !== unitIndex ? index : null;
  }, [detail, videoUnit, phase, unitIndex]);

  const onVideoEnded = finishDay;

  const onVideoUnavailable = useCallback(() => setNotice(NOTICE.video), []);

  if (loadFailed || !Number.isInteger(day)) {
    return (
      <main style={PAGE_STYLE}>
        <Link href="/course" data-testid="course-back">
          ← Back
        </Link>
        <p style={{ marginTop: 16 }}>{NOTICE.loadFailed}</p>
      </main>
    );
  }
  // 마지막 문장에서는 「다음 문장」 자리가 「Day 마치기」가 된다 — 수동 모드가 Day 를 끝낼 길(회차 b3 D4).
  const hasNext = nextPosition({ unitIndex, sentenceIndex }) !== null;

  if (!detail || !unit || !sentence) {
    return (
      <main style={PAGE_STYLE}>
        <p>Loading…</p>
      </main>
    );
  }

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
    <main style={PAGE_STYLE}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem" }}>
        <Link href="/course" data-testid="course-back" style={{ color: "var(--foreground-muted)" }}>
          ← Back
        </Link>
        <span style={{ color: "var(--foreground-muted)" }}>
          Day {detail.day} · Unit {detail.units[0].unit}–{detail.units.at(-1)?.unit}
        </span>
      </div>

      <div className="omy-course-player" style={{ marginTop: 10 }}>
        <CoursePlayer
          ref={playerRef}
          youtubeId={detail.youtube_id}
          startAt={startAt}
          onPlaying={onVideoPlaying}
          onEnded={onVideoEnded}
          onUnavailable={onVideoUnavailable}
        />
      </div>
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
          {/* 같은 자리의 두 상태를 testid 로 가른다(리디자인 설계서 §4) — 문구에 기대지 않게 함. */}
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
    </main>
  );
}
