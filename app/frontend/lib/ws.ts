/**
 * `/ws/session` 클라이언트 — 백엔드 프로토콜은 `app/backend/app/api/ws.py` +
 * `app/backend/app/audio_gateway/session.py`가 정본이다.
 *
 * 서버→클라이언트: session_started | partial | final | audio | speech_start |
 * speech_end | interrupted | pronunciation | session_failed | session_ended
 * 클라이언트→서버: {"type":"audio","data":<base64>} | {"type":"end_session"}
 *
 * `speech_start`/`speech_end`(Nova `userSpeechStart`/`userSpeechEnd`)와 `interrupted`
 * (barge-in, `stopReason=INTERRUPTED`)는 3차수 포트 확장에서 추가됐다. 스텁 어댑터는
 * 이 셋을 보내지 않으므로 스텁 모드 화면 거동은 그대로다.
 *
 * `pronunciation`(요구사항 v1.1 §10)은 Task 6에서 백엔드가 방송하기 시작했는데 이 union에
 * 없어서 화면이 조용히 버리고 있었다(A-5). **스텁 어댑터는 이 프레임을 만들지 않는다** —
 * `VOICE_ADAPTER=nova`에서만 온다. 스텁 모드 거동이 그대로인 이유이고, 그래서 이 경로는
 * 자동 테스트로 덮이지 않아 실물 마이크 1회로 검증한다(G-4).
 */

import { sessionSocketUrl } from "./config";

export type Speaker = "user" | "agent";

/**
 * 정본은 `app/backend/app/models/pronunciation.py:30`의 `PronunciationOutcome`이다.
 * `pending`은 오류가 아니라 "시범은 했고 재발화는 아직"이며, 세션이 끝날 때 서버가
 * `unclear`로 수렴시킨다(설계서 §3.2).
 */
export type PronunciationOutcome = "pending" | "correct" | "incorrect" | "unclear";

/**
 * 쉐도잉 세션이 시작될 때 서버가 넘기는 재료 (`TASK-45` · 설계서 §12 요구 5).
 *
 * ⛔ **화면은 자기 기본값을 갖지 않는다** — 재생 속도·반복 횟수의 정본은 서버 `Settings` 이고
 * 여기 실려 오는 값을 그대로 쓴다. 값이 없으면 쉐도잉 세션이 아니다(키 자체가 없다).
 *
 * ⚠️ `transcript` 는 **클립 전체**다. PRD §7 의 「문장 단위로 제공한다」는 화면의 몫이고 쪼개는
 * 규칙은 `TASK-10` 이 정한다 — 서버가 색인을 저장하지 않는 것과 같은 이유다(설계서 §3.2).
 */
export interface ShadowingSetup {
  item_id: string;
  source_title: string;
  transcript: string;
  clip_start_sec: number;
  clip_end_sec: number;
  playback_rate: number;
  repeat_count: number;
}

export type ServerEvent =
  | { type: "session_started"; session_id: string; shadowing?: ShadowingSetup }
  | { type: "partial"; text: string; speaker: Speaker }
  | { type: "final"; text: string; speaker: Speaker; sequence_no: number }
  | { type: "audio"; data: string }
  | { type: "speech_start"; offset_ms: number | null }
  | { type: "speech_end"; offset_ms: number | null }
  | { type: "interrupted" }
  // `target_sound`(예: `th_as_s`)는 기계 키다 — **화면에 렌더하지 않는다**(설계서 §10 미결 4,
  // 2026-08-30 캡틴 결정). 프레임에서 빼지 않는 이유는 이미 있던 계약이고 관측 도구가 쓸
  // 값이기 때문이다. `spoken_form`은 저장만 되고 이 프레임에는 실리지 않는다.
  | {
      type: "pronunciation";
      outcome: PronunciationOutcome;
      target_form: string;
      target_sound: string | null;
    }
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

  /**
   * 낭독 턴을 연다 (`TASK-45` · 설계서 §12 요구 4).
   *
   * ⛔ **이 두 신호가 파일 수명을 정한다.** 서버는 열린 동안 들어온 오디오를 Nova 로 보내지 않고
   * 파일에 쌓으므로, 알려주지 않으면 **세션 전체가 녹음된다**(§12 가 그 위험을 적었다).
   *
   * ⚠️ **어느 버튼이 이것을 부르는지는 아직 없다** — 추가 학습 5종의 배치·화면 구성은
   * `TASK-10` 이 소유한다(캡틴 결정 34·35 의 제약). 여기 있는 것은 프로토콜뿐이다.
   */
  startShadowingTurn(): void {
    this.send({ type: "shadowing_turn_start" });
  }

  /** 낭독 턴을 닫는다 — 서버가 녹음을 저장하고 포인터를 마지막에 쓴다(설계서 §4.5). */
  endShadowingTurn(): void {
    this.send({ type: "shadowing_turn_end" });
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
