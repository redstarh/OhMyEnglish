/**
 * 결과 API 클라이언트 — `GET /api/sessions/{id}/results`.
 * 응답 계약은 `app/backend/app/api/results.py` + `app/backend/app/services/results.py`가
 * 정본이다 (R2 상태 판정, R1 상위 2개, R3 부분 실패 플래그).
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

export async function fetchSessionResults(sessionId: string): Promise<SessionResultPayload> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/results`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`결과 API가 ${response.status}을 반환했습니다`);
  }
  return (await response.json()) as SessionResultPayload;
}
