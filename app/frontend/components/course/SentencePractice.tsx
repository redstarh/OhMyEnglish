"use client";

// 문법 코스의 문장 연습 칸 — 홈 「Today's practice」 카드 안 (`TASK-286` 에서 시작 · `TASK-304` 에서 분리).
// 설계서 `docs/design/2026-10-26-grammar-course-design.md` §4·§7 · 리디자인 설계서 §3(`TASK-304`) ·
// 실시간 표시 설계서 `docs/design/2026-11-14-live-readback-transcript-design.md`(`TASK-317`).
//
// 한 문장을 크게 보여 주고 읽어 준 뒤, 학습자가 따라 말하는 문장을 «말하는 동안» 그 아래에 보임
// (사용자 결정 2 · 2026-11-14 사용자 결정). 자동 모드는 「읽기 → 말 끝까지 듣기 → 판정 → 다음 문장」을
// 스스로 잇고, 수동 모드는 판정 뒤에 멈춤(사용자 결정 4).
//
// ⛔ 듣기는 브라우저 인식기(`lib/speechRecognition.ts`)가 맡고 확정 문장을 텍스트로 보냄 — 서버는
//    다시 전사하지 않음(실시간 표시 설계서 §5). 인식기가 없는 브라우저만 옛 PCM 경로로 내려감(§7 ⑥).
// ⛔ 말 없음은 시도로 세지 않음(2026-11-14 사용자 결정) — `silent` 이면 보내지 않고 안내만 보임.
// ⛔ 영상 연동은 없앴음(`TASK-317`) — 영상과 함께 하던 옛 Day 화면은 홈으로 넘김(`TASK-323`).
// ⛔ 저장하는 재생 위치는 불러온 진도의 `position_sec` 그대로임 — Day 를 마친 때만 0 임.
// ⚠️ 문장은 영상·교재의 문장이 아님 — 단원의 문법 패턴으로 새로 쓴 문장임(설계서 §2).
// ⚠️ `data-testid`(`course-*`)·`data-phase`·`data-attempts`·`data-verdict` 는 이 칸이 가짐 — 어느 자리에
//    그려도 같은 이름임. 부모는 Day 가 바뀌면 `key` 로 이 칸을 새로 마운트해야 함(첫 렌더에서만 진도를 읽음).

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  postCourseAttempt,
  postCourseTextAttempt,
  saveCourseProgress,
  type CourseAttempt,
  type CourseDayDetail,
  type ReadbackWord,
  type WriteResult,
} from "@/lib/api";
import { VoiceIo } from "@/lib/audio";
import { speak, stopSpeaking } from "@/lib/speech";
import {
  listen,
  listenLimitMs,
  recognitionAvailable,
  wordCount,
  type ListenUpdate,
} from "@/lib/speechRecognition";

type Mode = "auto" | "manual";
type Phase = "idle" | "listen" | "repeat" | "judge" | "done";
type Position = { unitIndex: number; sentenceIndex: number };

const MODE_STORAGE_KEY = "omy.course.mode";
const ADVANCE_DELAY_MS = 1500; // 판정을 보여 준 뒤 다음 문장까지
const SAVE_EVERY_MS = 5000;

const NOTICE = {
  mic: "I can't use the mic. Please allow the mic in your browser.",
  unavailable: "I can't check your speaking now. You can keep going.",
  unheard: "I couldn't hear you. Press \"Try again\" and say it again.",
  dayDone: "You finished this Day!",
} as const;

const PHASE_LABEL: Record<Exclude<Phase, "idle">, string> = {
  listen: "① Listen",
  repeat: "② Say it",
  judge: "③ Check",
  done: "③ Check",
};

interface Props {
  detail: CourseDayDetail;
  day: number;
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

// 표시된 문장의 글자 크기 — 칸 너비의 6 %(390 폭 266 px 에서 16 px)이고 20 px 에서 멈춤. 말한 내용(실시간 줄 ·
// You said · 낱말 판정)도 이 크기를 씀(`TASK-326` 사용자 지시 — 「표시되는 문장과 동일한 크기와 폰트」).
const SENTENCE_FONT = "text-[clamp(0.75rem,6cqi,1.25rem)]";
// 결과 자리 높이 — 문장 글자 단위(em)로 잡아 폭이 바뀌어도 글자를 따라감(`TASK-326`).
// 전사 두 줄 + 낱말 판정 두 줄(줄 높이 1.4 × 4 = 5.6em)에 안내 줄 · 여백(3rem)을 더함.
// 좁은 칸(18rem 미만)은 「You said:」 꼬리표 때문에 전사가 세 줄이 되므로 한 줄(1.4em)을 더 잡음(회차 b17 ⑫).
const RESULT_SLOT_HEIGHT = "h-[calc(5.6em+3rem)] @max-[18rem]:h-[calc(7em+3rem)]";

function Spoken({ words, transcript }: { words: ReadbackWord[]; transcript: string }) {
  return (
    <div
      data-testid="course-spoken"
      style={{ padding: "6px 10px", borderRadius: 10, background: "var(--accent-soft)", fontWeight: 600, lineHeight: 1.4 }}
    >
      <span style={{ fontSize: "0.72rem", fontWeight: 400, color: "var(--foreground-muted)" }}>You said: </span>
      <span data-testid="course-transcript">{transcript}</span>
      {words.length > 0 ? (
        // 낱말 사이에 실제 공백을 둠 — 여백만 두면 줄을 끊을 자리가 없어 좁은 화면에서 카드가 넓어졌음(회차 b13 r2 D1).
        <div style={{ marginTop: 2, overflowWrap: "anywhere" }}>
          {words.map((item, index) => (
            <Fragment key={`${item.word}-${index}`}>
            <span
              data-verdict={item.verdict}
              style={{
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
            </span>{" "}
            </Fragment>
          ))}
          <span style={{ display: "block", fontSize: "0.72rem", fontWeight: 400, lineHeight: 1.5, color: "var(--foreground-muted)" }}>
            Underline: you said a different word. Strikethrough: you missed the word.
          </span>
        </div>
      ) : null}
    </div>
  );
}

/** 말하는 동안의 글자 — 확정 부분은 보통 색, 미확정 부분은 흐린 기울임꼴(실시간 표시 설계서 §6). */
function LiveLine({ live }: { live: ListenUpdate }) {
  return (
    <p data-testid="course-live" style={{ fontWeight: 600, lineHeight: 1.4, overflowWrap: "anywhere" }}>
      <span style={{ fontSize: "0.72rem", fontWeight: 400, color: "var(--foreground-muted)" }}>{"You're saying: "}</span>
      {live.final ? <span data-testid="course-live-final">{live.final}</span> : null}
      {live.final && live.interim ? " " : null}
      {live.interim ? (
        <span data-testid="course-live-interim" style={{ color: "var(--foreground-muted)", fontStyle: "italic" }}>
          {live.interim}
        </span>
      ) : null}
    </p>
  );
}

export function SentencePractice({ detail, day, onDayFinished }: Props) {
  const [unitIndex, setUnitIndex] = useState(() => savedPosition(detail).unitIndex);
  const [sentenceIndex, setSentenceIndex] = useState(() => savedPosition(detail).sentenceIndex);
  const [mode, setMode] = useState<Mode>(readMode);
  const [phase, setPhase] = useState<Phase>("idle");
  // PCM 경로(인식기 없음)의 녹음 창 — 0 이면 인식기 경로이고 끝이 정해져 있지 않음(남은 초를 보이지 않음).
  const [waitMs, setWaitMs] = useState(0);
  const [live, setLive] = useState<ListenUpdate | null>(null);
  const [result, setResult] = useState<{ transcript: string; words: ReadbackWord[] } | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>(() =>
    Object.fromEntries(detail.units.flatMap((unit) => unit.sentences.map((item) => [item.key, item.attempts]))),
  );

  const runRef = useRef<AbortController | null>(null);
  const voiceRef = useRef<VoiceIo | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const recordRef = useRef<Uint8Array[] | null>(null);
  // 진행 중인 마이크 획득 — 두 연습이 동시에 getUserMedia 를 부르면 스트림 하나가 버려진 채 켜져 남음.
  const micRef = useRef<Promise<boolean> | null>(null);
  const mountedRef = useRef(true);
  const slotRef = useRef<HTMLDivElement | null>(null);
  const positionRef = useRef<Position>(savedPosition(detail));
  // 화면이 아는 완료 횟수 — 저장마다 보내 서버가 완료 전에 보낸 늦은 저장을 버리게 함(TASK-287).
  const completedRef = useRef(detail.progress?.completed_count ?? 0);
  // 저장할 재생 위치 — 불러온 진도의 위치가 끝까지 이 값으로 남고 Day 를 마칠 때만 0 이 됨.
  // ⚠️ 영상이 없어진 뒤에도 서버의 `position_sec` 을 0 으로 덮지 않으려고 둠(`TASK-317`).
  const lastTimeRef = useRef(detail.progress?.position_sec ?? 0);

  useEffect(() => {
    positionRef.current = { unitIndex, sentenceIndex };
  }, [unitIndex, sentenceIndex]);

  const unit = detail.units[unitIndex] ?? null;
  const sentence = unit?.sentences[sentenceIndex] ?? null;

  // Day 를 끝냈을 때 — 서버는 처음으로 되감으므로 화면도 처음으로 되감음(codex 리뷰 HIGH 2).
  // ⛔ 되감지 않으면 이어지는 5초 저장·언마운트 저장이 끝 위치를 다시 써서 다음 회차가 끝 근처에서 열림.
  const rewindAfterCompletion = useCallback(() => {
    lastTimeRef.current = 0;
    positionRef.current = { unitIndex: 0, sentenceIndex: 0 };
    setUnitIndex(0);
    setSentenceIndex(0);
    setResult(null);
    setLive(null);
  }, []);

  const save = useCallback(
    (completed = false) => {
      const position = positionRef.current;
      const current = detail.units[position.unitIndex];
      if (!current) return;
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

  // 진도를 5초마다 저장함. 화면을 떠날 때도 한 번 저장함.
  useEffect(() => {
    const timer = setInterval(() => save(), SAVE_EVERY_MS);
    const onLeave = () => save();
    window.addEventListener("pagehide", onLeave);
    return () => {
      clearInterval(timer);
      window.removeEventListener("pagehide", onLeave);
      save();
    };
  }, [save]);

  const cancelRun = useCallback(() => {
    runRef.current?.abort();
    runRef.current = null;
    recordRef.current = null;
    stopSpeaking();
  }, []);

  // Day 완료 — 마지막 문장을 마쳤을 때(설계서 §4). 자동·수동 두 경로가 함께 씀.
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

  // 말하는 동안 글자가 늘면 결과 자리를 맨 아래로 내림 — 넘친 글은 이 자리 안에서만 스크롤함(설계서 §6).
  useEffect(() => {
    const slot = slotRef.current;
    if (slot && live) slot.scrollTop = slot.scrollHeight;
  }, [live]);

  /**
   * 브라우저 인식기로 한 번 듣고 판정함(실시간 표시 설계서 §3).
   * `null` 이면 이 문장에서 멈춤(마이크 거부·인식 불가·끊김) — 화면 상태는 여기서 이미 정했음.
   * ⛔ `silent` 은 서버에 보내지 않음 — 말 없음은 시도로 세지 않음(2026-11-14 사용자 결정).
   */
  const judgeLive = useCallback(
    async (key: string, text: string, spokenMs: number, signal: AbortSignal) => {
      setWaitMs(0);
      setLive(null);
      // ⛔ 단계 표시는 `onaudiostart` 뒤에 「② Say it」으로 바꿈 — 켜지는 동안 학습자가 먼저 말해
      //    첫 낱말이 잘리지 않게 함(설계서 §3 ②).
      const outcome = await listen({
        signal,
        expectedWords: wordCount(text),
        maxMs: listenLimitMs(spokenMs),
        onAudioStart: () => {
          if (!signal.aborted) setPhase("repeat");
        },
        onUpdate: (update) => {
          if (signal.aborted) return;
          setPhase("repeat");
          setLive(update);
        },
      });
      if (signal.aborted || outcome.kind === "aborted") return null;
      if (outcome.kind === "denied") {
        setLive(null);
        setNotice(NOTICE.mic);
        setPhase("idle");
        return null;
      }
      if (outcome.kind === "unavailable") {
        // ⚠️ 자동 모드도 여기서 멈춤 — 인식 서비스가 죽었으면 다음 문장도 같은 오류로 끝남.
        setLive(null);
        setNotice(NOTICE.unavailable);
        setPhase("done");
        return null;
      }
      if (outcome.kind === "silent") {
        setLive(null);
        return "unheard" as const;
      }
      setPhase("judge");
      return postCourseTextAttempt(key, outcome.text);
    },
    [],
  );

  /** 인식기가 없는 브라우저(Firefox)의 옛 경로 — 녹음 창은 듣기 상한을 씀(실시간 표시 설계서 §7 ⑥). */
  const judgeRecorded = useCallback(async (key: string, spokenMs: number, signal: AbortSignal) => {
    const windowMs = listenLimitMs(spokenMs);
    setWaitMs(windowMs);
    setPhase("repeat");
    recordRef.current = [];
    await sleep(windowMs, signal);
    const chunks = recordRef.current ?? [];
    recordRef.current = null;
    if (signal.aborted) return null;
    setPhase("judge");
    const pcm = joinPcm(chunks);
    return pcm.byteLength > 0 ? postCourseAttempt(key, pcm) : ("unheard" as const);
  }, []);

  const run = useCallback(
    async (start: Position) => {
      cancelRun();
      const controller = new AbortController();
      runRef.current = controller;
      const { signal } = controller;
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
        setLive(null);
        // 앞 문장의 안내(안 들렸어요 · 판정을 쓸 수 없어요)가 이 문장의 결과로 읽히지 않게 지움(회차 b7).
        setNotice(null);

        setPhase("listen");
        const spokenMs = await speak(item.text, { signal });
        if (signal.aborted) return;

        let judged: WriteResult<CourseAttempt> | "unheard" | null;
        try {
          judged = recognitionAvailable()
            ? await judgeLive(item.key, item.text, spokenMs, signal)
            : await judgeRecorded(item.key, spokenMs, signal);
        } catch {
          // ⛔ 뜻밖의 거부도 판정 불가로 받음(codex 리뷰 MEDIUM) — 받지 않으면 단계가 ③ Check 에
          //    멈춘 채 안내도 없었음.
          judged = { ok: false, reason: "unavailable" };
        }
        // ⛔ 끊겨도 서버가 센 횟수는 적용함(실시간 표시 설계서 §5 결함 수정) — 응답 전에 Next 를 누르면
        //    서버에는 기록되고 화면의 Try 만 낡았음. 문장 키 단위라 다른 문장을 덮지 않음.
        // ⛔ 큰 쪽만 남김(codex 리뷰 MEDIUM) — 앞 시도의 늦은 응답이 더 작은 횟수로 Try 를 낮췄음.
        if (judged !== null && judged !== "unheard" && judged.ok) {
          const { attempts } = judged.value;
          setCounts((prev) => ({ ...prev, [item.key]: Math.max(prev[item.key] ?? 0, attempts) }));
        }
        if (signal.aborted || judged === null) return;
        setLive(null);
        if (judged === "unheard") {
          setNotice(NOTICE.unheard);
        } else if (judged.ok) {
          setResult({ transcript: judged.value.transcript, words: judged.value.words });
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
      }
    },
    [cancelRun, detail, ensureMic, finishDay, judgeLive, judgeRecorded, nextPosition, save],
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
      setLive(null);
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

  if (!unit || !sentence) {
    return <p>Loading…</p>;
  }
  // 마지막 문장에서는 「다음 문장」 자리가 「Day 마치기」가 됨 — 수동 모드가 Day 를 끝낼 길(회차 b3 D4).
  const hasNext = nextPosition({ unitIndex, sentenceIndex }) !== null;

  return (
    <div data-testid="sentence-practice">
      {/* 좁은 화면은 주제가 두 줄이 되는 단원이 있어 두 줄 자리를 늘 잡음 — 단원마다 카드 높이가 바뀌지 않게(`TASK-310`). */}
      <div
        className="min-h-[2.55rem] sm:min-h-0"
        style={{ marginTop: 14, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}
      >
        <span data-testid="course-unit" style={{ fontSize: "0.85rem", color: "var(--foreground-muted)", minWidth: 0 }}>
          Unit {unit.unit} · {unit.topic}
        </span>
        {/* ⛔ 전환 묶음은 줄어들지 않음 — 긴 단원 이름이 Auto 를 밀어 잘랐음(`TASK-324`). 줄어드는 쪽은 단원 이름임. */}
        <span
          role="group"
          aria-label="Mode"
          style={{ display: "inline-flex", flexShrink: 0, border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}
        >
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

      {/* 칸 너비가 컨테이너임 — 아래 글자 크기·자리 높이는 화면 폭이 아니라 이 칸의 너비를 따름(codex 리뷰 ①②). */}
      <section
        data-testid="course-card"
        className="@container"
        style={{ marginTop: 8, border: "1px solid var(--border)", borderRadius: 14, padding: 16 }}
      >
        {/* ⛔ 이 칸은 상태·문장 길이와 무관하게 같은 크기임(`TASK-310` 사용자 지시) — 단계 표시는 번호 줄에
            올리고, 녹음 막대·문장(두 줄)·결과 자리는 비어 있어도 높이를 차지함. */}
        {/* 좁은 칸(16rem 미만)은 단계 표시가 둘째 줄로 내려가므로 두 줄 자리를 늘 잡음 — 상태마다 높이가 바뀌지 않게. */}
        <div
          className="@max-[16rem]:min-h-[2.4rem]"
          style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8, fontSize: "0.8rem", color: "var(--foreground-muted)" }}
        >
          <span style={{ minWidth: 0 }}>
            <span data-testid="course-sentence-number">
              Sentence {sentenceIndex + 1} / {unit.sentences.length}
            </span>
            {phase !== "idle" ? (
              <span data-testid="course-phase" data-phase={phase} style={{ color: "var(--foreground)" }}>
                {" · "}
                {PHASE_LABEL[phase]}
                {phase === "repeat" && waitMs > 0 ? ` · ${(waitMs / 1000).toFixed(1)}s` : null}
              </span>
            ) : null}
          </span>
          <span data-testid="course-attempts" style={{ whiteSpace: "nowrap" }}>Try {counts[sentence.key] ?? 0}</span>
        </div>
        <div style={{ height: 4, borderRadius: 99, background: phase === "repeat" ? "var(--surface)" : "transparent", marginTop: 6, overflow: "hidden" }}>
          {/* 인식기 경로는 끝이 정해져 있지 않아 맥박 막대를 보이고, PCM 경로만 줄어드는 막대를 보임(설계서 §4). */}
          {phase === "repeat" && waitMs > 0 ? (
            <div
              key={`${sentence.key}-${waitMs}`}
              className="omy-course-wait"
              style={{ height: "100%", background: "var(--accent)", animationDuration: `${waitMs}ms` }}
            />
          ) : phase === "repeat" ? (
            <div data-testid="course-listen-bar" className="omy-course-listen" style={{ height: "100%", background: "var(--accent)" }} />
          ) : null}
        </div>
        {/* 가장 긴 문장(61자)이 두 줄에 드는 크기임 — 글자를 칸 너비의 6 %(390 폭 266 px 에서 16 px)로 맞추고
            20 px 에서 멈춤. 줄 높이 1.4 × 2줄 = 2.8em. */}
        <p
          data-testid="course-sentence"
          className={SENTENCE_FONT}
          style={{ fontWeight: 600, marginTop: 6, lineHeight: 1.4, height: "2.8em", overflow: "hidden" }}
        >
          {sentence.text}
        </p>
        {/* Listen·Slow 는 제거했음(`TASK-318` 사용자 결정) — 다시 듣기는 Try again 이 같은 동작이었음. */}
        {/* 결과·듣기 안내·알림이 한 고정 자리를 나눠 씀 — 넘치면 이 자리 안에서만 스크롤함. */}
        <div
          ref={slotRef}
          data-testid="course-result-slot"
          className={`${SENTENCE_FONT} ${RESULT_SLOT_HEIGHT}`}
          style={{ marginTop: 10, overflowY: "auto", overscrollBehavior: "contain" }}
        >
          {result ? <Spoken words={result.words} transcript={result.transcript} /> : null}
          {/* 말하는 동안의 글자는 판정이 올 때까지 남음 — ③ Check 뒤에 `Spoken` 으로 바뀜(설계서 §6). */}
          {(phase === "repeat" || phase === "judge") && live && (live.final || live.interim) ? (
            <LiveLine live={live} />
          ) : phase === "repeat" ? (
            <p style={{ fontSize: "0.85rem", color: "var(--foreground-muted)" }}>
              {"I'm listening. Say it, and you will see it below."}
            </p>
          ) : null}
          {notice ? (
            <p data-testid="course-notice" style={{ marginTop: result ? 6 : 0, fontSize: "0.85rem" }}>
              {notice}
            </p>
          ) : null}
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12 }}>
          <button
            type="button"
            data-testid="course-prev"
            className="omy-button"
            disabled={!previous}
            onClick={() => goTo(previous)}
          >
            {/* 이전 문장임(`TASK-329`) — 「← Back」은 카드 머리 「← Close」와 같은 화살표라 홈으로 가는 버튼으로 읽혔음. */}
            ← Previous
          </button>
          {/* 같은 자리의 두 상태를 testid 로 가름(리디자인 설계서 §4) — 문구에 기대지 않게 함. */}
          {phase === "idle" ? (
            <button type="button" data-testid="course-start" className="omy-button" onClick={() => void run(positionRef.current)}>
              Start
            </button>
          ) : (
            <button type="button" data-testid="course-retry" className="omy-button" onClick={() => void run(positionRef.current)}>
              Try again
            </button>
          )}
          {hasNext ? (
            <button
              type="button"
              data-testid="course-next"
              className="omy-button omy-button-primary"
              onClick={() => goTo(nextPosition({ unitIndex, sentenceIndex }))}
            >
              Next →
            </button>
          ) : (
            <button
              type="button"
              data-testid="course-finish"
              className="omy-button omy-button-primary"
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
}
