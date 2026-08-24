/**
 * `/ws/session` 클라이언트 — 백엔드 프로토콜은 `app/backend/app/api/ws.py` +
 * `app/backend/app/audio_gateway/session.py`가 정본이다.
 *
 * 서버→클라이언트: session_started | partial | final | audio | session_failed
 * | session_ended
 * 클라이언트→서버: {"type":"audio","data":<base64>} | {"type":"end_session"}
 */

import { sessionSocketUrl } from "./config";

export type Speaker = "user" | "agent";

export type ServerEvent =
  | { type: "session_started"; session_id: string }
  | { type: "partial"; text: string; speaker: Speaker }
  | { type: "final"; text: string; speaker: Speaker; sequence_no: number }
  | { type: "audio"; data: string }
  | { type: "session_failed"; reason: string }
  | { type: "session_ended"; session_id: string };

function isServerEvent(value: unknown): value is ServerEvent {
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    typeof (value as { type: unknown }).type === "string"
  );
}

export interface SessionSocketHandlers {
  onEvent: (event: ServerEvent) => void;
  onClose?: () => void;
}

/** 세션 WebSocket 하나를 감싼다. 연결이 끊긴 뒤 전송은 조용히 무시한다. */
export class SessionSocket {
  private readonly socket: WebSocket;

  constructor(handlers: SessionSocketHandlers) {
    this.socket = new WebSocket(sessionSocketUrl());
    this.socket.onmessage = (message: MessageEvent<string>) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(message.data);
      } catch {
        return; // 해석할 수 없는 프레임은 무시한다 — 서버 계약 위반이 아니라면 오지 않는다.
      }
      if (isServerEvent(parsed)) {
        handlers.onEvent(parsed);
      }
    };
    this.socket.onclose = () => handlers.onClose?.();
  }

  sendAudio(base64Data: string): void {
    this.send({ type: "audio", data: base64Data });
  }

  endSession(): void {
    this.send({ type: "end_session" });
  }

  close(): void {
    this.socket.close();
  }

  private send(payload: Record<string, unknown>): void {
    if (this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }
}
