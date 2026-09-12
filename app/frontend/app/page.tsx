"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchNextPlan, type NextPlanSummary } from "@/lib/api";
import type { SessionEntry } from "@/lib/config";
import { VoiceIo, base64ToBytes, bytesToBase64 } from "@/lib/audio";
import {
  SessionSocket,
  type PronunciationOutcome,
  type ServerEvent,
  type Speaker,
} from "@/lib/ws";

type ScreenState = "idle" | "connecting" | "active" | "ending" | "failed";

// 발음 배지 문구 (A-5). **새로 만들지 않고 결과 화면 카드의 어휘를 그대로 쓴다**
// (`app/results/[sessionId]/page.tsx:44-48`) — 같은 판정을 두 화면이 다른 말로 부르면
// 학습자가 다른 것으로 읽는다. `pending`만 이 화면에 있는 상태이고 문구는
// `docs/storyboard.html` 03b(:108)를 따른다. 점수·정답률은 쓰지 않는다 — "채점하지
// 않습니다. 시범합니다"(:101)가 톤 계약이다.
const PRONUNCIATION_BADGE: Record<PronunciationOutcome, string> = {
  pending: "🔊 발음 교정 중",
  correct: "✓ 좋아요",
  incorrect: "다시 연습해요",
  unclear: "잘 안 들렸어요",
};

// 색은 `app/globals.css`의 토큰만 쓴다 — 하드코딩 색이 다크모드 위계를 뒤집은 1차수 F-1의
// 재발 방지. `unclear`는 오류가 아니라 미판정이라 danger가 아니라 muted다(결과 화면과 동일).
const PRONUNCIATION_BADGE_COLOR: Record<PronunciationOutcome, string> = {
  pending: "var(--foreground-muted)",
  correct: "var(--foreground)",
  incorrect: "var(--danger)",
  unclear: "var(--foreground-muted)",
};

// 추천 이유 한 줄의 머리말 (R11-3). "왜 이 연습인지"를 학습자 말로 붙인다 — 이유 문장은
// 계획이 소유하므로 여기서 문구를 만들지 않는다.
const NEXT_PLAN_PREFIX = "오늘 이걸 연습해요:";

// 추가 학습 메뉴 (`TASK-10.2` · 진입점 설계서
// `docs/design/2026-09-12-additional-learning-entry-design.md` §2).
//
// ⛔ **항목이 다섯이 아니라 여섯이다.** PRD §7(:74)은 다섯을 열거하는데 R10-5(:145)가
// *"발음 집중 연습은 §7 Additional Learning 메뉴의 «독립 항목»으로 둔다"*를 글자로 요구한다.
// 설계서 §1 이 그 어긋남을 적었고 여기서 여섯으로 둔다 — 접으면 그 요구가 조용히 사라진다.
//
// ⛔ **`entry: null` 은 「아직 표면이 없다」다.** 항목을 지우지 않는 이유가 설계서 §2 에 있다:
// 지우면 다음 사람이 「원래 다섯이었다」로 읽고 위 어긋남이 되살아난다. 비활성 버튼이 그 사실을
// 화면에서도 말한다.
//
// ⚠️ **셋이 같은 표면(모드 없음)을 쓰는 것은 의도다** — 그 셋의 차이는 지시문이 아니라 **계획
// 데이터**에 있다(초점·질문·무대). 모드로 갈라도 조립되는 지시문이 같으므로 값역만 늘어난다.
const ADDITIONAL_LEARNING: ReadonlyArray<{
  label: string;
  entry: SessionEntry | null;
  note?: string;
}> = [
  { label: "자유 대화", entry: { source: "additional" } },
  { label: "약점 패턴 집중", entry: { source: "additional" } },
  // `TASK-5` Task 6(사용자 결정 79) — 이 항목이 **무대 정하기 진입**이다. ⛔ 이전에는 `mode` 가 없어
  // 위 둘과 구별되지 않았고, 그래서 백엔드가 이 세션을 가릴 수단이 없었다(그 설계서 §5).
  { label: "질문 답변 5개", entry: { mode: "scenario_intake", source: "additional" } },
  { label: "발음 집중", entry: { mode: "pronunciation", source: "additional" } },
  { label: "쉐도잉", entry: { mode: "shadowing", source: "additional" } },
  { label: "업무 역할극", entry: null, note: "무대를 고르는 화면이 아직 없어요" },
];

// 발음 집중을 골랐을 때 화면이 말해야 하는 두 가지 (`TASK-10.2` AC#2 · `TASK-128.4`).
//
// ⛔ **둘 다 「발음 연습으로 시작했다」고 말한다** (사용자 결정 83). 이전 판은 `pronunciation_focus`
// 키의 **부재**를 「말하기로 떨어졌다」로 읽었는데, 사용자 결정 72 가 그 폴백을 없앴으므로 그 문장은
// **거짓**이 됐다 — 소리를 못 골라도 세션은 전용 모드로 열린다.
// ⚠️ **그 경로가 예외가 아니라 평시다** — 발음 기록이 0건이면 후보가 비고 그것이 지금 dev DB 의
// 상태다. 즉 거짓 문구가 **기본값으로** 뜨고 있었다.
// ⛔ **두 상태를 한 문구로 합치지 않는다**(결정 83 이 그 안을 기각했다) — 둘은 실제로 다르고 둘 다
// 참이다. ⚠️ 소리 키(`th_as_s`)는 기계 키라 렌더하지 않는다(설계서 §10 미결 4).
const PRONUNCIATION_ENTERED = "발음 연습으로 시작했어요. 소리를 시범하고 다시 말하기를 부탁할 거예요.";
const PRONUNCIATION_NO_CANDIDATE =
  "발음 연습으로 시작했어요. 오늘 다룰 소리는 대화에서 듣고 고를 거예요.";

interface TranscriptLine {
  id: number;
  speaker: Speaker;
  text: string;
}

/**
 * 서버 `audio` 프레임을 재생 큐에 붙인다. 디코딩 실패는 세션 진행을 막지 않는다 —
 * 프레임 하나를 잃는 것이 대화를 끊는 것보다 낫고, 전사문 경로가 더 중요하다.
 */
function enqueueAudioFrame(voice: VoiceIo | null, base64Data: string): void {
  if (!voice) return;
  try {
    voice.enqueueAudio(base64ToBytes(base64Data));
  } catch {
    // 무시한다 (위 주석).
  }
}

export default function SessionPage() {
  const router = useRouter();
  const [state, setState] = useState<ScreenState>("idle");
  const [failureReason, setFailureReason] = useState<string | null>(null);
  const [lines, setLines] = useState<TranscriptLine[]>([]);
  const [partialLine, setPartialLine] = useState<TranscriptLine | null>(null);
  // Nova는 **사용자 부분 전사문을 주지 않는다** — 사용자 ASR은 `generationStage: FINAL`
  // 한 블록으로만 온다(N-1 실측). 그래서 부분 전사문 자리를 `userSpeechStart`~`End`
  // 구간의 "듣고 있어요"로 대체한다. 스텁 어댑터는 그 경계를 보내지 않으므로 스텁 모드의
  // 부분 전사문 거동(1·2차수 C2가 검증하는 회색→확정 전환)은 그대로 남는다.
  const [listening, setListening] = useState(false);
  // 진행 중인 발음 시도 1건의 판정. 한 번에 하나만 흐르므로(시범 → 재발화 → 판정)
  // 목록이 아니라 최신 1건만 들고 있는다. 세션이 끝나면 결과 화면의 카드가 전건을 보여준다.
  const [pronunciation, setPronunciation] = useState<PronunciationOutcome | null>(null);
  // 다음 세션의 추천 이유 (R11-3). 초기값이 "계획 없음"이라 조회가 끝나기 전에는 그 자리가
  // 비어 있다 — 로딩 문구를 두지 않는다: 이유는 시작 버튼을 막지 않는 부가 정보다.
  const [nextPlan, setNextPlan] = useState<NextPlanSummary>({ reason: null, target_level: null });
  // 진입 안내 한 줄 (`TASK-10.2` AC#2). 발음 집중을 고른 세션에만 값이 생긴다 — 그 밖에는 `null`
  // 이고 아무것도 렌더하지 않는다(추천 이유와 같은 규약: 빈 자리가 「해당 없음」의 표현이다).
  const [entryNotice, setEntryNotice] = useState<string | null>(null);

  const socketRef = useRef<SessionSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const voiceRef = useRef<VoiceIo | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const terminalHandledRef = useRef(false);
  // 이 세션이 **요청한** 모드. `session_started` 가 오면 그것과 서버가 실제로 준 것을 대조한다 —
  // 요청하지 않았으면 대조할 것이 없다.
  const requestedModeRef = useRef<SessionEntry["mode"]>(undefined);

  const stopMedia = useCallback(() => {
    const voice = voiceRef.current;
    voiceRef.current = null;
    void voice?.close();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  }, []);

  const goToResults = useCallback(
    (sessionId: string) => {
      stopMedia();
      router.push(`/results/${sessionId}`);
    },
    [router, stopMedia],
  );

  const handleServerEvent = useCallback(
    (event: ServerEvent) => {
      switch (event.type) {
        case "session_started":
          sessionIdRef.current = event.session_id;
          // ⛔ **키의 «부재»는 「후보가 아직 없다」다 — 폴백이 아니다** (결정 72·83 ·
          // `lib/ws.ts` 의 `pronunciation_focus` 주석). 요청하지 않은 세션에서는 이 자리를
          // 건드리지 않는다.
          if (requestedModeRef.current === "pronunciation") {
            setEntryNotice(
              event.pronunciation_focus ? PRONUNCIATION_ENTERED : PRONUNCIATION_NO_CANDIDATE,
            );
          }
          break;
        case "partial":
          setPartialLine({ id: -1, speaker: event.speaker, text: event.text });
          break;
        case "final": {
          setPartialLine(null);
          setListening(false);
          const { speaker, text } = event;
          setLines((prev) => {
            const last = prev.at(-1);
            // I-8 — **같은 화자의 연속 final은 한 줄로 이어 붙인다.** Nova의 발화 종료 감지가
            // 이르면(임계 약 480ms 실측) 한 문장이 여러 final로 쪼개져 화면에 두 줄로 보인다
            // (캡틴 관측 2026-09-03: "살짝만 늦게 말해도 문장이 두 줄로 표시된다").
            // 분석은 이미 그 조각들을 한 묶음으로 합치므로(I-1) 화면을 합치는 것이 분석과
            // **일치하는** 쪽이다. 이어붙일 때 공백 하나를 넣는 것도 백엔드와 같은 규약이다
            // (`services/analysis.py`의 `string_agg(u.transcript, ' ')`).
            // ⚠️ **저장은 건드리지 않는다** — 조각이 몇 번 생기는지가 함정 H-U·I-1의 유일한
            // 관측 수단이라 DB에는 쪼개진 그대로 남긴다. 이 병합은 표시 계층에만 있다.
            if (last && last.speaker === speaker) {
              return [...prev.slice(0, -1), { ...last, text: `${last.text} ${text}` }];
            }
            // id는 배열에서 파생한다 — ref를 state 업데이터 안에서 증가시키면 StrictMode의
            // 이중 호출에서 번호가 두 칸씩 뛴다.
            return [...prev, { id: (last?.id ?? 0) + 1, speaker, text }];
          });
          break;
        }
        case "speech_start":
          setListening(true);
          break;
        case "speech_end":
          setListening(false);
          break;
        case "audio":
          enqueueAudioFrame(voiceRef.current, event.data);
          break;
        case "interrupted":
          // barge-in — 이미 받았지만 아직 재생하지 않은 응답 오디오를 버린다.
          voiceRef.current?.dropQueuedAudio();
          break;
        case "pronunciation":
          // `target_sound`는 기계 키라 읽지 않는다 (설계서 §10 미결 4).
          setPronunciation(event.outcome);
          break;
        case "session_failed":
          if (terminalHandledRef.current) return;
          terminalHandledRef.current = true;
          stopMedia();
          setFailureReason(event.reason);
          setState("failed");
          break;
        case "session_ended":
          if (terminalHandledRef.current) return;
          terminalHandledRef.current = true;
          goToResults(event.session_id || sessionIdRef.current || "");
          break;
      }
    },
    [goToResults, stopMedia],
  );

  const startSession = useCallback(async (entry: SessionEntry = {}) => {
    setFailureReason(null);
    setLines([]);
    setPartialLine(null);
    setListening(false);
    setEntryNotice(null);
    terminalHandledRef.current = false;
    sessionIdRef.current = null;
    requestedModeRef.current = entry.mode;
    setState("connecting");

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setFailureReason("microphone_permission_denied");
      setState("failed");
      return;
    }
    streamRef.current = stream;

    const socket = new SessionSocket(
      {
        onEvent: handleServerEvent,
        onClose: () => {
          if (terminalHandledRef.current) return;
          terminalHandledRef.current = true;
          stopMedia();
          const sessionId = sessionIdRef.current;
          if (sessionId) {
            goToResults(sessionId);
          } else {
            setFailureReason("connection_lost");
            setState("failed");
          }
        },
      },
      // 진입 정보는 소켓을 열 때 쿼리로 실린다 — 세션 행과 지시문이 그 값으로 갈리므로
      // 첫 프레임으로 보낼 수 없다(`lib/config.ts` 의 `sessionSocketUrl` 주석).
      entry,
    );
    socketRef.current = socket;

    // Nova는 raw LPCM(16kHz·16bit·mono, 32ms 프레임)만 받는다 — `MediaRecorder`의
    // webm/opus로는 붙일 수 없다. AudioWorklet으로 원시 PCM을 그대로 캡처해 보낸다.
    try {
      voiceRef.current = await VoiceIo.start(stream, (frame) => {
        socketRef.current?.sendAudio(bytesToBase64(frame));
      });
    } catch {
      // 캡처를 못 만들면 세션은 성립하지 않는다 — 조용히 무음 세션을 만들지 않고 알린다.
      terminalHandledRef.current = true;
      socket.close();
      stopMedia();
      setFailureReason("audio_capture_unavailable");
      setState("failed");
      return;
    }

    setState("active");
  }, [goToResults, handleServerEvent, stopMedia]);

  const endSession = useCallback(() => {
    setState("ending");
    socketRef.current?.endSession();
  }, []);

  // 시작 화면에 보여줄 추천 이유를 **마운트당 한 번** 읽는다 (R11-3). 폴링하지 않는다.
  // ⚠️ **근거를 2026-09-06에 정정했다.** 원래 "계획은 세션 *사이*에만 바뀌고 이 화면은 세션이
  // 끝나면 언마운트된다"고 적었는데, 계획이 **쓰이는** 시점이 바로 그 "세션 사이"라서 근거가
  // 사실과 반대였다: 종료 트랜잭션이 계획 job 을 걸고(`services/sessions.py`
  // `enqueue_plan_next_session`) 워커가 Claude 왕복 뒤에 `session_plans`를 INSERT 하므로,
  // 학습자가 브라우저 뒤로가기로 이 화면에 돌아와 마운트한 **뒤에** job 이 끝나면 화면은 계획
  // N-1 을 계속 보여주고 시작 버튼이 연 세션은 계획 N 을 읽는다(`api/ws.py`가 시작 시점에
  // 다시 조회한다). ⚠️ **2026-09-09 에 이 경로가 흔해졌다** — `TASK-55` 가 결과 화면에 홈으로
  // 가는 인앱 링크를 넣었으므로 브라우저 내비게이션 없이도 이 화면으로 돌아온다. 이전 주석은
  // 「인앱 링크가 없어 브라우저 조작으로만 닿는다」고 적었는데 그것이 지금은 거짓이다.
  // **그래도 폴링하지 않는다** — 단일 사용자 로컬 도구에서 이 staleness 창은 받아들일 만하고,
  // 화면과 대화 상대가 같은 계획의 **다른 필드**를 보는 일은 없다: 둘 다 **같은 함수**
  // `load_prepared_plan`을 불러(`api/results.py`와 `api/ws.py`) 그 시점의 최신 1행에서
  // **같은 필드**(`instruction.target_level`)를 읽는다. 표시가 한 세션 늦을 수 있다는 것이
  // 전부다.
  useEffect(() => {
    let cancelled = false;

    async function loadNextPlan(): Promise<void> {
      try {
        const plan = await fetchNextPlan();
        if (!cancelled) setNextPlan(plan);
      } catch {
        // 백엔드가 안 떠 있으면 `fetch` 자체가 reject 한다(응답 상태가 아니라 네트워크
        // 실패다). 계획 표시는 학습을 막지 않으므로 그 자리를 비운 채 둔다.
      }
    }

    void loadNextPlan();
    return () => {
      cancelled = true;
    };
  }, []);

  // 언마운트 시 마이크·소켓 자원을 반드시 정리한다.
  useEffect(() => {
    return () => {
      stopMedia();
      socketRef.current?.close();
    };
  }, [stopMedia]);

  return (
    <main style={{ maxWidth: 640, margin: "0 auto", padding: "2rem", fontFamily: "sans-serif" }}>
      <h1>OhMyEnglish — 학습 세션</h1>

      {state === "idle" && (
        <>
          {/* 추천 이유 한 줄 (R11-3). 이유가 없으면 **아무것도 렌더하지 않는다** — 빈 자리가
              "계획 없음"의 표현이다. 시작 버튼보다 덜 강조하므로 색은 muted 토큰이고,
              난이도는 있을 때만 괄호로 붙인다(계획에 이유는 있고 수준이 비는 경우는 없지만
              HTTP 응답은 외부 경계다). */}
          {nextPlan.reason && (
            <p style={{ color: "var(--foreground-muted)", marginBottom: "1rem" }}>
              {NEXT_PLAN_PREFIX} {nextPlan.reason}
              {nextPlan.target_level ? ` (${nextPlan.target_level})` : null}
            </p>
          )}
          {/* 추천 학습. ⛔ `source` 를 «명시»한다 — 001 의 기본값이 `recommended` 라 넘기지 않아도
              같은 값이 되지만, 그러면 「기본값이라 그렇게 됐다」와 「이 문으로 들어왔다」가
              구분되지 않는다. 진입점 설계서 §4 가 두 값을 문으로 가른다. */}
          <button
            onClick={() => void startSession({ source: "recommended" })}
            style={{ padding: "0.75rem 1.5rem" }}
          >
            학습 시작
          </button>

          {/* 추가 학습 (PRD §7 · `TASK-10.2`). ⛔ **권장량 완료와 무관하게 항상 보인다** —
              `PRD.md:73` 이 「완료 여부와 무관하게 항상 제공한다」를 글자로 정했고, 진입점 설계서
              §3 이 그것을 「이 문은 게이트가 아니다」로 못박았다. */}
          <section style={{ marginTop: "2rem" }}>
            <h2 style={{ fontSize: "1rem", marginBottom: "0.5rem" }}>추가 학습</h2>
            <p style={{ color: "var(--foreground-muted)", marginTop: 0, marginBottom: "0.75rem" }}>
              권장량과 상관없이 언제든 골라도 돼요.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
              {ADDITIONAL_LEARNING.map((item) => (
                <button
                  key={item.label}
                  onClick={() => {
                    if (item.entry) void startSession(item.entry);
                  }}
                  disabled={item.entry === null}
                  title={item.note}
                  style={{ padding: "0.5rem 1rem" }}
                >
                  {item.label}
                  {item.note ? ` (${item.note})` : null}
                </button>
              ))}
            </div>
          </section>
        </>
      )}

      {state === "connecting" && <p>마이크 권한을 요청하는 중입니다...</p>}

      {(state === "active" || state === "ending") && (
        <>
          <div
            style={{
              border: "1px solid #ccc",
              borderRadius: 8,
              padding: "1rem",
              minHeight: 220,
              marginTop: "1rem",
            }}
          >
            {/* 진입 안내 (`TASK-10.2` AC#2). 발음 집중을 골랐을 때 **무엇을 받았는지** 말한다 —
                서버가 소리를 못 골라 말하기로 떨어뜨렸을 때 화면이 침묵하면 사용자가 다른 세션을
                받은 것을 모른다. `aria-live` 는 발음 배지와 같은 이유로 붙인다. */}
            {entryNotice && (
              <p
                aria-live="polite"
                style={{ color: "var(--foreground-muted)", margin: "0 0 0.6rem" }}
              >
                {entryNotice}
              </p>
            )}
            {lines.length === 0 && !partialLine && !listening && (
              <p style={{ color: "var(--foreground-muted)" }}>대화를 기다리는 중...</p>
            )}
            {/* 확정 전사문이 강조 대상이다 — 부분 전사문(muted)보다 배경 대비가 높아야
                AC U1의 위계가 성립한다. 색은 테마 토큰에서만 온다(globals.css). */}
            {lines.map((line) => (
              <p key={line.id} style={{ color: "var(--foreground)", margin: "0.4rem 0" }}>
                <strong>{line.speaker === "agent" ? "질문" : "답변"}: </strong>
                {line.text}
              </p>
            ))}
            {partialLine ? (
              <p style={{ color: "var(--foreground-muted)", margin: "0.4rem 0" }}>
                <strong>{partialLine.speaker === "agent" ? "질문" : "답변"}: </strong>
                {partialLine.text}
              </p>
            ) : (
              listening && (
                <p style={{ color: "var(--foreground-muted)", margin: "0.4rem 0" }}>
                  듣고 있어요...
                </p>
              )
            )}
            {/* 발음 배지 (A-5 · 요구사항 v1.1 §10). 다음 `pronunciation` 프레임이 올 때까지
                최신 판정을 남긴다 — 한 번에 한 시도만 흐르기 때문이다. 스텁 모드에서는
                프레임이 오지 않아 이 자리가 비어 있는 것이 정상이다. */}
            {pronunciation && (
              <p
                aria-live="polite"
                style={{
                  color: PRONUNCIATION_BADGE_COLOR[pronunciation],
                  margin: "0.4rem 0",
                  fontWeight: 600,
                }}
              >
                {PRONUNCIATION_BADGE[pronunciation]}
              </p>
            )}
          </div>
          <button
            onClick={endSession}
            disabled={state === "ending"}
            style={{ padding: "0.75rem 1.5rem", marginTop: "1rem" }}
          >
            {state === "ending" ? "종료 중..." : "학습 종료"}
          </button>
        </>
      )}

      {state === "failed" && (
        <div style={{ marginTop: "1rem" }}>
          <p>연결에 실패했습니다.</p>
          {failureReason && (
            <p style={{ color: "var(--foreground-muted)" }}>사유: {failureReason}</p>
          )}
          <button onClick={() => void startSession()} style={{ padding: "0.75rem 1.5rem" }}>
            다시 시도
          </button>
        </div>
      )}
    </main>
  );
}
