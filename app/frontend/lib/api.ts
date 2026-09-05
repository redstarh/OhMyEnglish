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

export interface SessionResultPayload {
  status: SessionResultStatus;
  partial_failure: boolean;
  // `analyzing`/`connection_failed`/`no_utterances`에서는 응답에 키 자체가 없다.
  corrections?: Correction[];
  // `corrections`와 달리 **항상 있다**(비면 `[]`) — R2 판정과 독립이다.
  pronunciation: PronunciationAttempt[];
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

export async function fetchSessionResults(sessionId: string): Promise<SessionResultPayload> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/results`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`결과 API가 ${response.status}을 반환했습니다`);
  }
  return (await response.json()) as SessionResultPayload;
}
