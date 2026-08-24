/**
 * 백엔드 주소 — 하드코딩하지 않는다. `NEXT_PUBLIC_API_BASE`가 없으면
 * 로컬 개발 기본값(`http://localhost:8000`)으로 떨어진다.
 */
export const API_BASE: string = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/** `/ws/session` WebSocket 주소. `API_BASE`의 http(s) 스킴만 ws(s)로 바꾼다. */
export function sessionSocketUrl(): string {
  return `${API_BASE.replace(/^http/, "ws")}/ws/session`;
}
