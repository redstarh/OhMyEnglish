/**
 * 백엔드 주소 — 하드코딩하지 않는다. `NEXT_PUBLIC_API_BASE`가 없으면
 * 로컬 개발 기본값(`http://localhost:8000`)으로 떨어진다.
 */
export const API_BASE: string = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/**
 * 세션 하나가 어느 문으로 들어왔는지 (`TASK-10.2` · 진입점 설계서
 * `docs/design/2026-09-12-additional-learning-entry-design.md`).
 *
 * ⛔ **값을 여기서 발명하지 않는다** — `mode` 는 `api/ws.py` 가 아는 값이고 `source` 는 001 의
 * `learning_sessions_learning_source_check` 가 가둔다. 그 값역을 문자열 리터럴로 좁혀 두는 이유는
 * 오타가 **조용히 말하기 세션으로 떨어지는 것**을 타입 검사에서 잡기 위함이다.
 *
 * ⚠️ 세 표면만 있다: 모드 없음(자유 대화·약점 패턴 집중·질문 답변 5개) · `pronunciation` · `shadowing`.
 * 셋으로 갈리는 기준은 **지시문이 실제로 달라지는가**이고 그 판정은 설계서 §2 가 소유한다.
 */
export interface SessionEntry {
  mode?: "pronunciation" | "shadowing";
  source?: "recommended" | "additional";
}

/**
 * `/ws/session` WebSocket 주소. `API_BASE`의 http(s) 스킴만 ws(s)로 바꾼다.
 *
 * 진입 정보는 **쿼리 문자열**로 실린다 — 소켓 열기 전에 서버가 알아야 하는 값이라(세션 행과
 * 지시문이 그 값으로 갈린다) 첫 프레임으로 보낼 수 없다.
 */
export function sessionSocketUrl(entry: SessionEntry = {}): string {
  const base = `${API_BASE.replace(/^http/, "ws")}/ws/session`;
  const params = new URLSearchParams();
  if (entry.mode) params.set("mode", entry.mode);
  if (entry.source) params.set("source", entry.source);
  const query = params.toString();
  return query ? `${base}?${query}` : base;
}
