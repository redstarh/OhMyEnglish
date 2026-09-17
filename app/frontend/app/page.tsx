"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { fetchNextPlan, type NextPlanSummary } from "@/lib/api";
import { entryFromQuery, type SessionEntry } from "@/lib/config";
import { VoiceIo, base64ToBytes, bytesToBase64 } from "@/lib/audio";
import {
  SessionSocket,
  type AdditionalTarget,
  type PronunciationOutcome,
  type ServerEvent,
  type ShadowingSetup,
  type Speaker,
} from "@/lib/ws";
import { ShadowingPanel } from "./ShadowingPanel";
import { WeeklyReportPanel } from "./WeeklyReportPanel";

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
// ⚠️ **`target` 은 음성 명령이 이 목록을 가리키는 키다** (`TASK-61.8` · 결정 110 ②). 매핑을 따로
// 두지 않고 이 목록에서 유도한다 — 두 곳에 적으면 화면 버튼과 음성 명령이 서로 다른 세션을 연다.
// ⚠️ 앞 두 항목이 **같은 `target`** 인 것은 의도다(entry 가 같고 차이가 계획 데이터에 있다 — 위 주석).
// ⛔ 「업무 역할극」에는 `target` 을 주지 않는다 — 열 수 없는 것을 음성으로 고를 수 있게 하면 안 된다.
// ⚠️ **`href` 는 `TASK-168` 이 더했다 — 세션을 열지 않고 «화면으로 가는» 항목의 자리다.** 영상 학습은
// 지시문이 달라지는 갈래가 아니라 화면과 자산 관리가 다른 갈래라서 세션 모드를 새로 만들지 않았다
// (`docs/design/2026-09-18-video-learning-design.md` §1 질문 5).
// ⛔ 그래서 항목의 상태가 셋이 됐다: `entry` 가 있으면 세션 · `href` 가 있으면 이동 · 둘 다 없으면
// 비활성(「업무 역할극」). 아래 렌더의 `disabled` 조건이 그 셋을 가른다.
const ADDITIONAL_LEARNING: ReadonlyArray<{
  label: string;
  entry: SessionEntry | null;
  href?: string;
  target?: AdditionalTarget;
  note?: string;
}> = [
  { label: "자유 대화", target: "conversation", entry: { source: "additional" } },
  { label: "약점 패턴 집중", target: "conversation", entry: { source: "additional" } },
  // `TASK-5` Task 6(사용자 결정 79) — 이 항목이 **무대 정하기 진입**이다. ⛔ 이전에는 `mode` 가 없어
  // 위 둘과 구별되지 않았고, 그래서 백엔드가 이 세션을 가릴 수단이 없었다(그 설계서 §5).
  {
    label: "질문 답변 5개",
    target: "scenario_intake",
    entry: { mode: "scenario_intake", source: "additional" },
  },
  {
    label: "발음 집중",
    target: "pronunciation",
    entry: { mode: "pronunciation", source: "additional" },
  },
  { label: "쉐도잉", target: "shadowing", entry: { mode: "shadowing", source: "additional" } },
  // ⛔ **「업무 역할극」의 빈 칸을 재사용하지 않았다** — 그 칸은 무대 선택 화면의 부재를 가리키는
  // 표식이고 소유가 `TASK-102`·`TASK-5` 다. 영상 학습은 **일곱째** 로 붙는다.
  // ⛔ `target` 을 주지 않는다 — 음성 명령으로 이 화면에 가려면 `AdditionalTarget` 값역과 백엔드
  // `ADDITIONAL_TARGETS` 를 함께 열어야 하고, 그것은 이 갈래의 요구가 아니다(설계서 §1 질문 5).
  { label: "영상으로 배우기", entry: null, href: "/videos" },
  { label: "업무 역할극", entry: null, note: "무대를 고르는 화면이 아직 없어요" },
];

/** 음성 명령이 고른 대상의 진입 정보. 없으면 `null` — 화면은 그때 새 세션을 열지 않는다. */
function entryForTarget(target: AdditionalTarget): SessionEntry | null {
  return ADDITIONAL_LEARNING.find((item) => item.target === target)?.entry ?? null;
}

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

// 음성 명령의 어긋남을 말하는 문구 셋 (결정 113 · `TASK-61.16`).
//
// ⛔ **이 자리가 있는 이유는 코치의 말이 앱의 상태를 보장하지 않기 때문이다.** 실측: 표지가 없어
// 버려진 명령에 코치가 「됐다」고 말한 것이 4/4 이고(`runs/2026-09-16-task61-15-…` §2-1) 확인이
// 오지 않아 세션이 갈리지 않은 것이 4/8 이다(`runs/2026-09-16-task61-13-…` §2-2). 학습자는 그
// 어긋남을 **들어서는** 알 수 없다 — 그래서 화면이 말한다.
//
// ⚠️ 문구가 **다음에 할 말**을 담는다: 무엇이 안 됐는지만 말하면 학습자가 빠져나갈 길이 없다.
// 실측에서 학습자의 「네」가 정지를 풀지 못했으므로(1/1) 「다시 말해 달라」가 유일한 출구다.
const COMMAND_IGNORED_NOTICE: Record<
  "end" | "start_additional" | "show_report" | "pause" | "resume",
  string
> = {
  end: "학습 종료를 알아듣지 못해 세션을 그대로 두었어요. 「헤이, 학습 종료」처럼 다시 말해 주세요.",
  start_additional:
    "연습 변경을 알아듣지 못해 지금 세션을 그대로 두었어요. 「헤이, 발음 연습으로 바꿔 줘」처럼 다시 말해 주세요.",
  show_report: "리포트 요청을 알아듣지 못했어요. 「헤이, 주간 리포트 보여 줘」처럼 다시 말해 주세요.",
  // ⚠️ 정지·재개가 버려진 경우의 문구가 **방향까지 말한다** — 「멈추지 못했다」와 「잇지 못했다」는
  // 학습자가 다음에 해야 할 일이 다르고, 기록이 계속되는지 멈춰 있는지도 다르다.
  pause: "일시 정지를 알아듣지 못해 계속 기록하고 있어요. 「헤이, 일시 정지」처럼 다시 말해 주세요.",
  resume:
    "학습 계속을 알아듣지 못해 아직 정지 중이에요. 「헤이, 학습 계속」처럼 다시 말해 주세요.",
};

// 정지 중임을 계속 말하는 줄 (결정 117). ⛔ **한 번 뜨고 사라지는 알림으로 두지 않는다** — 정지는
// 상태이고, 그 상태에서 학습자가 말한 것은 저장되지 않는다. 화면이 그 사실을 계속 말하지 않으면
// 학습자는 자기 발화가 사라진 이유를 알 수 없다.
const PAUSED_NOTICE = "일시 정지 중이에요. 지금 말하는 것은 기록하지 않아요 — 「헤이, 학습 계속」이라고 말하면 이어서 해요.";

// 확인을 기다리는 중임을 말하는 문구 둘. 대상은 확인을 거치는 명령 둘이다 — `show_report` 는
// 확인을 타지 않으므로(결정 107 ③) 이 자리에 오지 않는다.
const COMMAND_PENDING_NOTICE: Record<"end" | "start_additional", string> = {
  end: "학습 종료를 확인하고 있어요. 「네」라고 답하면 종료해요 — 아직 종료되지 않았어요.",
  start_additional:
    "연습 변경을 확인하고 있어요. 「네」라고 답하면 바꿔요 — 아직 바뀌지 않았어요.",
};

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
  // 음성 명령의 어긋남 한 줄 (결정 113 · `TASK-61.16`). ⛔ `entryNotice` 와 **합치지 않는다** —
  // 진입 안내는 세션이 열릴 때 한 번 쓰이고 이 자리는 세션 중에 여러 번 바뀐다. 한 상태로 두면
  // 명령 알림이 진입 안내를 덮고 그 안내는 다시 돌아오지 않는다.
  const [commandNotice, setCommandNotice] = useState<string | null>(null);
  // 정지 중인가 (결정 117). ⛔ `commandNotice` 와 **가른다** — 그것은 한 번 말하고 마는 알림이고
  // 이것은 **상태**다. 합치면 다른 알림이 정지 표시를 덮고 학습자는 기록이 멈춘 것을 잊는다.
  const [paused, setPaused] = useState(false);
  // 서버가 고른 쉐도잉 클립 (`TASK-66.7`). ⛔ **키의 부재는 「쉐도잉 세션이 아니다」다** —
  // `pronunciation_focus` 가 세운 규약과 같아서 요청하지 않은 세션에서는 `null` 로 남는다.
  const [shadowing, setShadowing] = useState<ShadowingSetup | null>(null);
  // 음성 명령으로 열리는 주간 리포트 패널 (`TASK-61.6` · 결정 107). 화면을 옮기지 않는 이유는
  // `WeeklyReportPanel` 의 머리말이 갖는다 — 이동하면 소켓이 닫혀 세션이 끝난다.
  const [reportOpen, setReportOpen] = useState(false);
  // 「추가 학습」 음성 명령이 확인을 거치면 **다음 세션의 진입**을 여기 담는다 (결정 110 ③).
  const pendingEntryRef = useRef<SessionEntry | null>(null);
  // ⛔ **`startSession` 을 ref 로 잡는 이유** — `session_ended` 처리에서 직접 부르려면
  // `handleServerEvent` 가 `startSession` 에 의존해야 하고 `startSession` 은 다시
  // `handleServerEvent` 에 의존해 순환이 된다. ⚠️ **effect 로 여는 판을 먼저 썼고 그것은
  // `react-hooks/set-state-in-effect` 에 막혔다**(실측: `startSession` 이 첫머리에서 동기로
  // `setState` 를 부르므로 lint 가 effect 본문의 setState 로 본다). 그래서 ref 로 끊는다.
  const startSessionRef = useRef<((entry: SessionEntry) => Promise<void>) | null>(null);

  const socketRef = useRef<SessionSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const voiceRef = useRef<VoiceIo | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const terminalHandledRef = useRef(false);
  // 이 세션이 **요청한** 모드. `session_started` 가 오면 그것과 서버가 실제로 준 것을 대조한다 —
  // 요청하지 않았으면 대조할 것이 없다.
  const requestedModeRef = useRef<SessionEntry["mode"]>(undefined);

  const stopMedia = useCallback(() => {
    // 클립 패널도 함께 내린다 — 언마운트가 소리를 끄므로 세션이 끝나면 재생이 멈춘다(`TASK-66.7`).
    setShadowing(null);
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
          // 쉐도잉 세션이면 클립이 실려 온다 (`TASK-66.7`). 키가 없으면 `null` 로 두어 패널을
          // 렌더하지 않는다 — 「없음」과 「비었음」을 구분하는 이 리포의 규약이다.
          setShadowing(event.shadowing ?? null);
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
        case "voice_command":
          // ⛔ **화면이 수행하는 명령은 `show_report` 하나다** — 종료는 서버가 `session_ended` 로
          // 알리는 것이 정본이고, 화면이 앞질러 처리하면 확인 절차가 두 곳에 생긴다(`lib/ws.ts`).
          // ⚠️ **`requested` 만 본다**: 확인을 타지 않는 명령이라 뒤 단계가 오지 않는 것이
          // 정상이고, 모델이 `confirmed` 를 덧붙여 불러도 패널이 두 번 열리지 않는다(결정 107 ③).
          if (event.command === "show_report" && event.stage === "requested") {
            setReportOpen(true);
          }
          // 추가 학습 — 확인이 끝난 뒤에만 기억한다. ⛔ **세션을 화면이 닫지 않는다**: 서버가
          // `confirmed` 에서 닫고 `session_ended` 를 보내며, 그때 아래 처리가 결과 화면 대신
          // 새 세션을 연다(결정 110 ③). `requested` 에서 기억하면 학습자가 물렸을 때도 열린다.
          if (event.command === "start_additional" && event.stage === "confirmed") {
            pendingEntryRef.current = entryForTarget(event.target);
          }
          // 확인 대기를 화면이 말한다 (결정 113 · `TASK-61.16`). ⛔ **확인을 거치는 둘만이다** —
          // `show_report` 는 뒤 단계가 오지 않는 것이 정상이라(결정 107 ③) 그 문구를 띄우면
          // 영원히 남는다. `next_question` 도 같은 이유로 이 자리에 오지 않는다(결정 108 ②).
          // ⚠️ **`confirmed`·`cancelled` 에서 지운다** — 지우지 않으면 실제로 바뀐 뒤에도 화면이
          // 「아직 안 바뀜」을 말한다. 실측이 잡은 것은 그 반대 방향이었지만(정지) 같은 자리다.
          if (event.command === "end" || event.command === "start_additional") {
            setCommandNotice(
              event.stage === "requested" ? COMMAND_PENDING_NOTICE[event.command] : null,
            );
          }
          // 정지·재개 (결정 117). ⛔ **서버가 상태를 적은 뒤에만 이 프레임이 온다** — 앱이 DB 를
          // 못 적으면 프레임을 보내지 않으므로 화면이 앞질러 「멈췄다」고 말하지 않는다.
          // ⚠️ `requested` 하나만 보는 것은 확인을 타지 않는 명령의 규약이다(결정 107 ③).
          if (
            (event.command === "pause" || event.command === "resume") &&
            event.stage === "requested"
          ) {
            setPaused(event.command === "pause");
          }
          break;
        case "voice_command_ignored":
          // 서버가 표지를 못 찾아 **실행하지 않은** 명령이다. 코치는 이미 「됐다」고 말한 뒤이므로
          // (어댑터가 tool 결과를 앱의 판정보다 먼저 돌려준다) 이 한 줄이 학습자가 그것을 알 수 있는
          // 유일한 자리다. ⛔ 여기서 아무 명령도 수행하지 않는다.
          setCommandNotice(COMMAND_IGNORED_NOTICE[event.command]);
          break;
        case "session_failed":
          if (terminalHandledRef.current) return;
          terminalHandledRef.current = true;
          stopMedia();
          setFailureReason(event.reason);
          setState("failed");
          break;
        case "session_ended": {
          if (terminalHandledRef.current) return;
          terminalHandledRef.current = true;
          const next = pendingEntryRef.current;
          if (next) {
            // ⛔ **결과 화면으로 가지 않는다** (결정 110 ③) — 학습자가 「추가 학습」을 말한 것은
            // 계속하겠다는 뜻이고, 여기서 결과 화면으로 보내면 화면을 다시 눌러야 해서
            // 「음성으로 제어한다」가 중단된다. 지난 세션의 분석 job 은 종료 시점에 걸려 그대로 돈다.
            pendingEntryRef.current = null;
            stopMedia();
            void startSessionRef.current?.(next);
            return;
          }
          goToResults(event.session_id || sessionIdRef.current || "");
          break;
        }
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
    // 명령 알림도 세션 사이에 남기지 않는다 — 「아직 안 바뀜」이 **바뀐 뒤의 새 세션**에 남으면
    // 화면이 정확히 거꾸로 말한다(추가 학습이 확인되면 이 함수가 새 세션을 연다).
    setCommandNotice(null);
    // 정지 상태도 세션 사이에 남기지 않는다 — 새 세션은 정지가 아니고, 남으면 화면이 「기록하지
    // 않는다」고 말하는 채 기록이 돈다.
    setPaused(false);
    // 리포트 패널은 세션 사이에 남기지 않는다 — 앞 세션의 수치를 새 세션 화면에 띄워 두면
    // 그것이 이번 세션의 것으로 읽힌다.
    setReportOpen(false);
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
          // ⛔ **자기 소켓이 아직 현재 것인지 먼저 본다** (결정 110 ③의 경합). 추가 학습이 새
          // 세션을 열면 `startSession` 이 `terminalHandledRef` 를 `false` 로 되돌리므로, 그
          // 뒤에 도착한 **이전 소켓의 close** 가 아래 처리를 통과해 **새 세션을 종료 처리한다.**
          // ⚠️ 프론트에 테스트 러너가 없어 이 경합은 회차가 판별력을 갖는다.
          if (socketRef.current !== socket) return;
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

  /**
   * 낭독 턴을 열고 닫는다 (설계서 `2026-09-08-shadowing-task-design.md` §12 요구 4).
   *
   * ⛔ **여는 신호와 닫는 신호가 파일 수명을 정한다.** 서버는 열린 동안 들어온 오디오를 Nova 로
   * 보내지 않고 파일에 쌓으므로(`session.py` `_forward_audio`), 닫아 주지 않으면 **세션 전체가
   * 녹음된다.** 그래서 조작 주체를 `ShadowingPanel` 에 두고 여기서는 신호만 넘긴다.
   *
   * ⚠️ 두 함수를 `useCallback` 으로 안정화하는 것이 계약이다 — 패널이 언마운트 정리에서 이것을
   * 부르므로, 매 렌더에 새 함수를 주면 그 정리가 렌더마다 돌아 **녹음이 끊긴다.**
   */
  const startShadowingTurn = useCallback(() => {
    socketRef.current?.startShadowingTurn();
  }, []);

  const endShadowingTurn = useCallback(() => {
    socketRef.current?.endShadowingTurn();
  }, []);

  // 「추가 학습」 명령이 확인을 거친 뒤 **새 세션을 여는 자리** (결정 110 ③).
  //
  // ⛔ **`session_ended` 처리 안에서 바로 열지 않는다** — 그러면 `handleServerEvent` 가
  // `startSession` 에 의존하고 `startSession` 이 다시 `handleServerEvent` 에 의존해 순환이 된다.
  // 상태를 한 번 거치면 그 사슬이 끊기고, 여는 시점이 「앞 세션의 정리가 끝난 뒤」로 분명해진다.
  // `startSession` 의 최신 판을 ref 에 담아 둔다 — `session_ended` 처리가 그것을 부른다.
  // ⚠️ effect 본문이 **ref 대입 하나**여서 `set-state-in-effect` 에 걸리지 않는다.
  useEffect(() => {
    startSessionRef.current = startSession;
  }, [startSession]);

  // 영상 학습의 [연습하기] 가 이 화면에 **문장을 지정해** 들어오는 자리 (`TASK-168`).
  //
  // ⛔ **세션 화면을 영상 화면에 복제하지 않는 대신 여기로 보낸다** — 소켓을 여는 코드가 둘이 되면
  // 한쪽만 고쳐질 자리가 생긴다. 그래서 `/videos/[id]` 의 [연습하기] 는
  // `/?mode=shadowing&source=additional&item=<문장 id>` 로 이동하고 이 effect 가 그것을 받는다.
  //
  // ⛔ **`useSearchParams` 를 쓰지 않는 이유**: prerender 된 경로에서 그 훅은 가장 가까운
  // `Suspense` 경계까지를 클라이언트 렌더로 떨어뜨린다. ⚠️ 그런데 **개발에서는 그것이 드러나지
  // 않아**(Next.js 문서: *"In development, routes are rendered on-demand, so `useSearchParams`
  // doesn't suspend and things may appear to work without `Suspense`"*) 우리 게이트(`tsc`·`eslint`)
  // 로는 잡히지 않는다. effect 안의 `location.search` 는 클라이언트에서만 도므로 그 함정을 비껀다.
  //
  // ⚠️ **URL 을 즉시 비운다** — 비우지 않으면 새로고침이 세션을 또 연다. `history.replaceState` 를
  // 쓰는 것은 라우터 이동을 일으키지 않아 이 화면이 다시 그려지지 않기 때문이다.
  const autoStartedRef = useRef(false);
  useEffect(() => {
    if (autoStartedRef.current) {
      return;
    }
    // ⛔ 질의 필드 이름을 여기서 적지 않는다 — `entryFromQuery` 가 `sessionSocketUrl` 과 **같은 표**를
    //    본다. 첫 판은 이 자리가 `mode`·`item` 만 읽고 `source` 를 다시 하드코딩했고, 그러면 진입
    //    정보를 만드는 쪽과 읽는 쪽이 조용히 갈린다.
    const entry = entryFromQuery(window.location.search);
    if (entry === null) {
      return;
    }
    autoStartedRef.current = true;
    window.history.replaceState({}, "", "/");
    void startSessionRef.current?.(entry);
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
                    if (item.entry) {
                      void startSession(item.entry);
                    } else if (item.href) {
                      router.push(item.href);
                    }
                  }}
                  // ⚠️ **조건을 좁혔다**(`TASK-168`) — 이전에는 `item.entry === null` 하나였고, 그러면
                  // 화면으로 가는 새 항목이 비활성으로 그려진다. 「업무 역할극」의 비활성과 `note` 는
                  // 그대로다: 그 칸은 `entry` 도 `href` 도 없다.
                  disabled={item.entry === null && item.href === undefined}
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
            {/* 음성 명령의 어긋남 (결정 113 · `TASK-61.16`). ⛔ **muted 로 두지 않는다** — 이 줄은
                코치의 말을 «정정»하는 자리라 전사문보다 약하게 보이면 읽히지 않는다. `aria-live` 는
                위 안내와 같은 이유로 붙인다(소리로는 알 수 없는 사실이다). */}
            {commandNotice && (
              <p
                aria-live="polite"
                style={{ color: "var(--foreground)", fontWeight: 600, margin: "0 0 0.6rem" }}
              >
                {commandNotice}
              </p>
            )}
            {/* 정지 중 표시 (결정 117). 상태이므로 **정지가 풀릴 때까지 남는다** — 그 사이 학습자가
                말한 것은 저장되지 않고, 화면이 그 이유를 계속 말해야 학습자가 사라진 줄을 이해한다. */}
            {paused && (
              <p
                aria-live="polite"
                style={{ color: "var(--foreground)", fontWeight: 600, margin: "0 0 0.6rem" }}
              >
                {PAUSED_NOTICE}
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
          {/* 쉐도잉 클립 (`TASK-66.7`). 대화 상자 **아래**에 두는 이유: 클립은 세션이 시작할 때
              한 번 정해지는 재료이고 대화는 흐르는 것이라 위계가 다르다. */}
          {shadowing ? (
            <ShadowingPanel
              setup={shadowing}
              onRecordingStart={startShadowingTurn}
              onRecordingEnd={endShadowingTurn}
            />
          ) : null}
          {/* 주간 리포트 (`TASK-61.6`). 음성 명령으로만 열리고 **버튼으로 닫는다** — 닫기까지
              음성으로 두면 명령이 둘로 늘고 그것은 이 조각의 범위가 아니다(결정 107 ①). */}
          {reportOpen ? <WeeklyReportPanel onClose={() => setReportOpen(false)} /> : null}
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
