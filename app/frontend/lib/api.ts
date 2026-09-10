/**
 * 조회 API 클라이언트 — `GET /api/sessions/{id}/results` · `GET /api/sessions/next-plan`.
 * 응답 계약은 `app/backend/app/api/results.py` + `app/backend/app/services/results.py`가
 * 정본이다 (R2 상태 판정, R1 상위 2개, R3 부분 실패 플래그, R11-3 추천 이유).
 */

import { API_BASE } from "./config";

export type SessionResultStatus =
  | "analyzing"
  | "final"
  | "partial_failure"
  | "connection_failed"
  | "no_utterances";

export interface Correction {
  pattern_key: string;
  category: string;
  original_span: string;
  correction: string;
  target_form: string;
  reason: string;
  occurrences: number;
}

/**
 * 발음 카드 1장 (Task 8). **기계 키는 이 계약에 없다** — 설계서 §10 미결 4 결정:
 * `th_as_s` 같은 키는 값역이 열려 있고 실물 왕복 0회라 관측된 값이 없어서, 표시 문구를
 * 지금 정하면 발명값이 된다. 그래서 백엔드가 아예 내려주지 않는다.
 */
export interface PronunciationAttempt {
  /** Nova가 시범한 문장. 단 `signal_source`가 `nova_tool`이 아니면 **설명 문구**다. */
  target_form: string;
  /** `null`이면 대답 없이 끝난 시도다 (종료 수렴). 키는 언제나 있다. */
  spoken_form: string | null;
  outcome: "correct" | "incorrect" | "unclear";
  signal_source: "nova_tool" | "korean_transcript" | "agent_reprompt";
}

/**
 * 드릴이 계획만큼 돌았는지 (설계서 §2.3 · 캡틴 결정 10).
 *
 * ⚠️ **이 두 수를 화면에 렌더하지 않는다.** 소비자는 서버와 로그다 — 결정 10이 정한 용도는
 * 「지시문을 고치는 입력」 하나다. 분자와 분모를 나란히 주면 `9 / 12`로 읽히고 그것이 가장
 * 점수처럼 보이는 모양인데, 미달의 주어는 학습자가 아니라 **대화 모델**이라 학습자가 손쓸 수
 * 없는 수를 자기 점수로 읽게 된다. API가 보내는 것과 화면이 그리는 것이 어긋나 보이는 이 계약은
 * 의도된 것이고, 화면은 미달일 때 사실 진술 한 문장만 그린다.
 */
export interface DrillTurns {
  exchanges_observed: number;
  exchanges_expected: number;
}

export interface SessionResultPayload {
  status: SessionResultStatus;
  partial_failure: boolean;
  // `analyzing`/`connection_failed`/`no_utterances`에서는 응답에 키 자체가 없다.
  corrections?: Correction[];
  // `corrections`와 달리 **항상 있다**(비면 `[]`) — R2 판정과 독립이다.
  pronunciation: PronunciationAttempt[];
  // `corrections`와 **같은 규약**으로 빠진다: 위 세 상태에서는 기대값이 기록돼 있어도 키가
  // 없고, 계획 없이 시작한 세션에서도 없다(관측 대상이 아니다).
  drill?: DrillTurns;
  // `TASK-79` — **분석 대상 발화는 있는데 그 job 이 아직 하나도 없다.** 종료 flush 가 실패한
  // 세션의 모양이고, 워커의 회복 스윕이 나중에 그 묶음을 걷으므로 그때의 `no_utterances`는
  // 영구가 아니다. 화면은 이 값이 참인 동안 폴링을 이어간다 — 이전 판은 프론트 상수(약 6초)로
  // 버텼는데 스윕이 언제 도는지 보장하는 계약이 없어 어떤 값도 맞을 수 없었다.
  // `pronunciation`처럼 **항상 있다** — 상태마다 키 존재를 갈라 읽지 않게 한다.
  awaiting_analysis: boolean;
}

/**
 * 다음 세션 계획의 요약 (R11-3). 계획이 없으면 두 값이 **모두 null**이다 — 오류가 아니라
 * "아직 계획이 없다"이고, 화면은 그 자리를 비운다. 초점 패턴·질문 목록은 이 계약에 없다:
 * 질문을 미리 보여주면 학습자가 답을 준비해 즉흥 발화 연습이 무의미해진다.
 */
export interface NextPlanSummary {
  reason: string | null;
  target_level: string | null;
}

/**
 * `fetchSessionResults`와 달리 **던지지 않는다** — 계획 표시는 학습을 막지 않으므로
 * 응답이 실패면 조용히 빈 요약을 돌려준다. 단 네트워크 자체가 끊기면 `fetch`가 reject
 * 하므로 호출자가 그 경로를 잡아야 한다(`app/page.tsx`).
 */
export async function fetchNextPlan(): Promise<NextPlanSummary> {
  // 이유는 세션이 끝날 때마다 바뀐다 — 브라우저 휴리스틱 캐시에 걸리면 지난 계획이 남는다.
  const response = await fetch(`${API_BASE}/api/sessions/next-plan`, { cache: "no-store" });
  if (!response.ok) {
    return { reason: null, target_level: null };
  }
  return (await response.json()) as NextPlanSummary;
}

/** 그날 그 패턴을 틀린 자리 1건 (PRD §13 R13-2). 전부가 아니라 예시 하나다. */
export interface DailyErrorExample {
  original_span: string;
  correction: string;
  reason: string;
}

/** 그날 패턴 1종의 집계. 판정(만성 여부·개선 여부)은 이 계약에 없다 — R13-5. */
export interface DailyErrorPattern {
  pattern_key: string;
  category: string;
  target_form: string;
  occurrences: number;
  example: DailyErrorExample;
}

/**
 * 오늘(학습자 타임존) 오류 요약 (PRD §13). 계약의 정본은
 * `app/backend/app/api/daily.py` + `app/backend/app/services/daily_summary.py`다.
 *
 * `analyzed`가 「그날 분석이 돌고 오류 0건」과 「그날 학습이 없었다」를 가른다(R13-7) — 두 개수만
 * 보면 구별되지 않는다. `patterns`·두 개수는 항상 있다(비면 `[]`·`0`).
 */
export interface DailySummaryPayload {
  summary_date: string;
  analyzed: boolean;
  occurrence_count: number;
  pattern_count: number;
  patterns: DailyErrorPattern[];
}

/**
 * `fetchNextPlan`과 같은 규약으로 **던지지 않는다** — 하루 요약은 세션 교정 표시를 막지 않는다.
 * 실패하면 `analyzed: false`를 돌려주고 화면은 그 절을 그리지 않는다.
 *
 * ⚠️ 그래서 조회 실패와 「그날 학습이 없었다」가 화면에서 같은 결과를 낸다. 의도한 것이다 —
 * 결과 화면의 주 내용은 방금 세션의 교정이고, 하루 요약을 못 읽었다고 그것을 가리지 않는다.
 */
export async function fetchDailySummary(): Promise<DailySummaryPayload> {
  const empty: DailySummaryPayload = {
    summary_date: "",
    analyzed: false,
    occurrence_count: 0,
    pattern_count: 0,
    patterns: [],
  };
  // 하루 요약은 분석이 끝날 때마다 바뀐다 — 캐시에 걸리면 지난 판독이 남는다.
  const response = await fetch(`${API_BASE}/api/daily-summary`, { cache: "no-store" });
  if (!response.ok) {
    return empty;
  }
  return (await response.json()) as DailySummaryPayload;
}

/**
 * 결과 API가 실패 상태를 응답했을 때 던진다 (TASK-55·TASK-56).
 *
 * ⛔ **`status`는 화면 문구가 아니라 분류용이다.** 이전 판은 `결과 API가 ${status}을
 * 반환했습니다`를 던졌고 결과 화면이 그것을 그대로 그려서 학습자가 `404`를 봤다. 학습자 문구는
 * 화면이 소유하고(`app/results/[sessionId]/page.tsx`), 이 `message`는 콘솔·로그용이라 영어다 —
 * 한국어로 쓰면 다음 사람이 화면에 그려도 되는 문장으로 착각한다.
 *
 * 폴링을 멈출지 판단하는 근거도 이 `status`다: 4xx는 같은 요청을 되풀이해도 같은 답이 온다.
 */
export class SessionResultsError extends Error {
  readonly status: number;

  constructor(status: number) {
    super(`session results request failed: HTTP ${status}`);
    this.name = "SessionResultsError";
    this.status = status;
  }
}

export async function fetchSessionResults(sessionId: string): Promise<SessionResultPayload> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/results`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new SessionResultsError(response.status);
  }
  return (await response.json()) as SessionResultPayload;
}
