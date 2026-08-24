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

export interface SessionResultPayload {
  status: SessionResultStatus;
  partial_failure: boolean;
  // `analyzing`/`connection_failed`/`no_utterances`에서는 응답에 키 자체가 없다.
  corrections?: Correction[];
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
