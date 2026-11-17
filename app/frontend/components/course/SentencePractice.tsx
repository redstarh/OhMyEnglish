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
import { useShowTranslation } from "@/lib/translationSetting";

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
  /** 열리자마자 저장된 자리에서 듣기를 시작함 — 홈의 Start speaking 한 번으로 시작(`TASK-348` 사용자 결정). */
  autoStart?: boolean;
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

/** 진도 저장의 같음 비교 열쇠 — 단원 · 문장 · 재생 위치가 모두 같으면 같은 진도임(`TASK-347`). */
function progressKey(unit: number | undefined, sentenceIndex: number, positionSec: number): string {
  return `${unit ?? ""}|${sentenceIndex}|${positionSec}`;
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
// 아주 좁은 칸(12.5rem 미만 · 320 폭 196 px)은 글자가 최저 12 px 에 멈춰 판정 줄도 세 줄이 되므로 한 줄을 더 잡고
// 두 줄 안내문 몫으로 여백을 0.25rem 늘림(`TASK-337` — 61자 문장이 틀리면 내용 150 > 자리 132). 글자가 칸 너비를
// 따르는 12.5rem 이상에서는 줄 수가 폭과 무관해 390·1400 의 자리 높이는 그대로임.
const RESULT_SLOT_HEIGHT =
  "h-[calc(5.6em+3rem)] @max-[18rem]:h-[calc(7em+3rem)] @max-[12.5rem]:h-[calc(8.4em+3.25rem)]";

// 판정 줄 앞의 이름표와 다 맞았을 때의 한 줄 (`TASK-333` N2 · 사용자 결정 2026-11-14). 「You said:」 바로
// 아래에 원문이 이름표 없이 다시 나와 다 맞으면 같은 말이 두 번 보였음(회차 b18 N2).
const SENTENCE_LABEL = "Sentence: ";
const ALL_MATCHED = "All words matched";
const LABEL_STYLE = { fontSize: "0.72rem", fontWeight: 400, color: "var(--foreground-muted)" } as const;

function Spoken({ words, transcript }: { words: ReadbackWord[]; transcript: string }) {
  const allMatched = words.length > 0 && words.every((item) => item.verdict === "match");
  return (
    <div
      data-testid="course-spoken"
      data-all-matched={allMatched}
      style={{ padding: "6px 10px", borderRadius: 10, background: "var(--accent-soft)", fontWeight: 600, lineHeight: 1.4 }}
    >
      <span style={LABEL_STYLE}>You said: </span>
      <span data-testid="course-transcript">{transcript}</span>
      {allMatched ? (
        <p data-testid="course-all-matched" style={{ marginTop: 2 }}>
          {ALL_MATCHED}
        </p>
      ) : null}
      {words.length > 0 ? (
        // 낱말 사이에 실제 공백을 둠 — 여백만 두면 줄을 끊을 자리가 없어 좁은 화면에서 카드가 넓어졌음(회차 b13 r2 D1).
        // ⚠️ 다 맞으면 이 줄을 숨기고 위 한 줄만 보임 — 낱말 판정(`data-verdict`)은 시험이 읽으므로 DOM 에 남김.
        <div hidden={allMatched} style={{ marginTop: 2, overflowWrap: "anywhere" }}>
          <span style={LABEL_STYLE}>{SENTENCE_LABEL}</span>
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

/**
 * 말하는 동안의 글자 — 들은 그대로 보임(실시간 표시 설계서 §6 · §12).
 * ⛔ 「You're saying:」 꼬리표와 미확정 글자의 흐린 기울임꼴은 뺐음 — 「작은 글씨는 듣고 있는중이라고 표시하지 않아도 돼.
 *    내가 읽는 문장을 그대로 표시」(`TASK-348` 사용자 지시). 확정·미확정의 testid 는 시험이 읽으므로 남김.
 */
function LiveLine({ live }: { live: ListenUpdate }) {
  return (
    <p data-testid="course-live" style={{ fontWeight: 600, lineHeight: 1.4, overflowWrap: "anywhere" }}>
      {live.final ? <span data-testid="course-live-final">{live.final}</span> : null}
      {live.final && live.interim ? " " : null}
      {live.interim ? <span data-testid="course-live-interim">{live.interim}</span> : null}
    </p>
  );
}

/** 읽어 주는 동안의 문장 — 읽기 시작한 낱말까지 강조 색으로 칠함(`TASK-348`). `spoken` 이 `null` 이면 평소 문장. */
function SpokenSentence({ text, spoken }: { text: string; spoken: number | null }) {
  if (spoken === null) return <>{text}</>;
  const parts = text.match(/\S+|\s+/g) ?? [];
  return (
    <>
      {parts.map((part, at) => {
        if (/^\s+$/.test(part)) return part;
        // 이 조각이 몇 번째 낱말인가 — 앞 조각 중 낱말 수 + 1.
        const order = parts.slice(0, at + 1).filter((item) => !/^\s+$/.test(item)).length;
        const lit = order <= spoken;
        return (
          <span key={at} data-spoken={lit ? "true" : undefined} style={{ color: lit ? "var(--accent)" : undefined, transition: "color 120ms" }}>
            {part}
          </span>
        );
      })}
    </>
  );
}

export function SentencePractice({ detail, day, onDayFinished, autoStart = false }: Props) {
  const [unitIndex, setUnitIndex] = useState(() => savedPosition(detail).unitIndex);
  const [sentenceIndex, setSentenceIndex] = useState(() => savedPosition(detail).sentenceIndex);
  const [mode, setMode] = useState<Mode>(readMode);
  const [showTranslation, setShowTranslation] = useShowTranslation();
  const [phase, setPhase] = useState<Phase>("idle");
  // 읽어 주는 동안 읽기 시작한 낱말 수 — 듣기 단계 밖에서는 `null`(`TASK-348`).
  const [spokenWords, setSpokenWords] = useState<number | null>(null);
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

  // 마지막으로 서버에 쓴(처음에는 불러온) 자리 — 같은 자리는 다시 쓰지 않음(`TASK-347`).
  // ⛔ 가만히 열려 있는 화면이 5초마다 자기 자리를 다시 쓰면, 다른 기기·탭에서 나아간 진도를 예전 자리로
  //    덮었음(실측: 아이폰은 u017 까지 갔는데 진도는 unit 16 · 1 — 열려 있던 다른 화면들의 저장 3895건).
  const lastSavedRef = useRef(
    progressKey(detail.progress?.unit ?? detail.units[0]?.unit, detail.progress?.sentence_index ?? 0, detail.progress?.position_sec ?? 0),
  );

  const save = useCallback(
    (completed = false, at?: Position) => {
      const position = at ?? positionRef.current;
      const current = detail.units[position.unitIndex];
      if (!current) return;
      const unit = completed ? detail.units[0].unit : current.unit;
      const sentenceIndex = completed ? 0 : position.sentenceIndex;
      const positionSec = completed ? 0 : lastTimeRef.current;
      const key = progressKey(unit, sentenceIndex, positionSec);
      if (!completed && key === lastSavedRef.current) return;
      // ⛔ 성공한 뒤에만 「썼음」으로 기억함(`TASK-349` codex 리뷰 HIGH) — 먼저 기억하면 한 번 실패한 자리를
      //    다음 주기 저장 · 떠날 때 저장이 같은 자리로 보고 건너뛰어 진도를 잃었음.
      void saveCourseProgress(day, { positionSec, unit, sentenceIndex, completed, completedCount: completedRef.current }).then(
        (ok) => {
          if (ok) lastSavedRef.current = key;
        },
      );
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
      // 틀린 뒤 같은 문장을 다시 들을 때는 읽어 주지 않음(`TASK-348` 사용자 결정 「바로 다시 들음」).
      let relisten = false;
      let spokenMs = 0;
      for (;;) {
        const item = detail.units[position.unitIndex].sentences[position.sentenceIndex];
        if (!relisten) {
          setUnitIndex(position.unitIndex);
          setSentenceIndex(position.sentenceIndex);
          positionRef.current = position;
          setResult(null);
          setLive(null);
          // 앞 문장의 안내(안 들렸어요 · 판정을 쓸 수 없어요)가 이 문장의 결과로 읽히지 않게 지움(회차 b7).
          setNotice(null);

          setPhase("listen");
          setSpokenWords(0);
          spokenMs = await speak(item.text, { signal, onWords: (count) => !signal.aborted && setSpokenWords(count) });
          // ⛔ 끊긴 연습은 색칠 상태를 건드리지 않음 — 그 사이 시작된 새 연습의 색칠을 지웠음(`TASK-349` codex 리뷰 LOW).
          if (signal.aborted) return;
          setSpokenWords(null);
        }
        relisten = false;

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

        if (readMode() !== "auto") {
          save();
          return;
        }
        // 자동 모드(`TASK-348` · 설계서 §12): 다 맞으면 다음 문장 · 틀리면 같은 문장을 바로 다시 들음 ·
        // 말 없음 · 판정 불가는 멈춤(다시 들으면 마이크가 끝없이 켜져 있게 됨). 못 넘어가면 학습자가 Next 를 누름.
        const matched =
          judged !== "unheard" &&
          judged.ok &&
          judged.value.words.length > 0 &&
          judged.value.words.every((word) => word.verdict === "match");
        if (matched) {
          const next = nextPosition(position);
          // ⛔ 다음 자리를 지금 저장함 — 판정을 보여 주는 동안 닫아도 다음에 열면 그 문장부터임(「이전 공부한 것 이후부터」).
          // ⛔ 현재 자리도 지금 옮김(`TASK-349` codex 리뷰 HIGH) — 판정을 보여 주는 1.5초 동안 닫거나 주기 저장이
          //    돌면 `positionRef`(방금 끝낸 문장)를 다시 써서 다음에 같은 문장부터 열렸음. 화면 번호는 기다린 뒤 바뀜.
          if (next) positionRef.current = next;
          save(false, next ?? position);
          await sleep(ADVANCE_DELAY_MS, signal);
          if (signal.aborted) return;
          if (next === null) {
            finishDay();
            return;
          }
          position = next;
          continue;
        }
        save();
        if (judged !== "unheard" && judged.ok && judged.value.transcript) {
          relisten = true;
          continue;
        }
        return;
      }
    },
    [cancelRun, detail, ensureMic, finishDay, judgeLive, judgeRecorded, nextPosition, save],
  );

  // 홈의 Start speaking 으로 열렸으면 바로 시작함(`TASK-348`) — 카드 안 Start 를 또 누르지 않음.
  // ⚠️ 개발 모드의 이중 마운트에서는 첫 마운트의 정리가 연습을 끊고(`cancelRun`) 두 번째 마운트가 다시 시작함.
  // ⛔ 마운트 때 한 번만 — `run` 은 부모 콜백(`onDayFinished`)에 달려 바뀔 수 있어, 그것을 의존으로 두면 연습 도중
  //    처음부터 다시 시작했음. 최신 `run` 은 ref 로 부름. 개발 모드의 이중 마운트는 `run` 이 앞 연습을 끊고 새로 시작함.
  const runLatest = useRef(run);
  useEffect(() => {
    runLatest.current = run;
  }, [run]);
  useEffect(() => {
    if (autoStart) void runLatest.current(positionRef.current);
  }, [autoStart]);

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
        <span style={{ display: "inline-flex", flexShrink: 0, gap: 6 }}>
        {/* KO — 문장 아래 한국어 번역을 켜고 끔. Auto/Manual 과 같은 모양으로 그 왼쪽에 둠(`TASK-328` 사용자 결정). */}
        <span style={{ display: "inline-flex", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}>
          <button
            type="button"
            data-testid="course-translation"
            aria-pressed={showTranslation}
            aria-label="Show Korean translation"
            // `TASK-333` X3 — 글자가 「KO」뿐이라 처음 보면 무엇을 켜는지 모름. 마우스를 올리면 같은 이름을 보임.
            title="Show Korean translation"
            onClick={() => setShowTranslation(!showTranslation)}
            style={{
              padding: "4px 12px",
              fontSize: "0.8rem",
              border: 0,
              background: showTranslation ? "var(--accent)" : "transparent",
              color: showTranslation ? "var(--on-accent)" : "var(--foreground)",
            }}
          >
            KO
          </button>
        </span>
        <span
          role="group"
          aria-label="Mode"
          style={{ display: "inline-flex", border: "1px solid var(--border)", borderRadius: 8, overflow: "hidden" }}
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
          <SpokenSentence text={sentence.text} spoken={phase === "listen" ? spokenWords : null} />
        </p>
        {/* 한국어 번역 — KO 를 켰을 때만 두 줄 자리를 잡음. 가장 긴 번역(39자)이 두 줄에 드는 크기임(`TASK-328`). */}
        {showTranslation ? (
          <p
            data-testid="course-translation-text"
            lang="ko"
            className="text-[clamp(0.7rem,4.5cqi,0.95rem)]"
            style={{ marginTop: 2, lineHeight: 1.4, height: "2.8em", overflow: "hidden", color: "var(--foreground-muted)" }}
          >
            {sentence.translation ?? ""}
          </p>
        ) : null}
        {/* Listen·Slow 는 제거했음(`TASK-318` 사용자 결정) — 다시 듣기는 Try again 이 같은 동작이었음. */}
        {/* 결과·듣기 안내·알림이 한 고정 자리를 나눠 씀 — 넘치면 이 자리 안에서만 스크롤함. */}
        <div
          ref={slotRef}
          data-testid="course-result-slot"
          className={`${SENTENCE_FONT} ${RESULT_SLOT_HEIGHT}`}
          style={{ marginTop: 10, overflowY: "auto", overscrollBehavior: "contain" }}
        >
          {/* 다시 듣는 중 새 글자가 오면 앞 시도의 결과를 감춤 — 같은 자리에 두 줄이 겹치지 않게 함(`TASK-348`). */}
          {result && !((phase === "repeat" || phase === "judge") && live && (live.final || live.interim)) ? (
            <Spoken words={result.words} transcript={result.transcript} />
          ) : null}
          {/* 말하는 동안의 글자는 판정이 올 때까지 남음 — ③ Check 뒤에 `Spoken` 으로 바뀜(설계서 §6). */}
          {(phase === "repeat" || phase === "judge") && live && (live.final || live.interim) ? (
            <LiveLine live={live} />
          ) : null}
          {notice ? (
            <p data-testid="course-notice" style={{ marginTop: result ? 6 : 0, fontSize: "0.85rem" }}>
              {notice}
            </p>
          ) : null}
        </div>
        {/* 아래 버튼 셋 — 아주 좁은 칸에서는 `omy-course-nav` 가 여백·글자를 줄여 칸 안에 둠(`TASK-340` · `globals.css`). */}
        <div className="omy-course-nav" style={{ display: "flex", justifyContent: "space-between", marginTop: 12 }}>
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
