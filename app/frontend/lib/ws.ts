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

import { sessionSocketUrl, type SessionEntry } from "./config";

export type Speaker = "user" | "agent";

/**
 * 정본은 `app/backend/app/models/pronunciation.py:30`의 `PronunciationOutcome`이다.
 * `pending`은 오류가 아니라 "시범은 했고 재발화는 아직"이며, 세션이 끝날 때 서버가
 * `unclear`로 수렴시킨다(설계서 §3.2).
 */
export type PronunciationOutcome = "pending" | "correct" | "incorrect" | "unclear";

/**
 * 「추가 학습」 음성 명령이 열 수 있는 것 (`TASK-61.8` · 결정 110 ②).
 *
 * ⛔ **값역의 정본은 백엔드 `app/models/voice_command.py:AdditionalTarget` 이다** — 서버가 그
 * 값역으로 tool 페이로드를 검증하고 모르는 값은 버린다. 여기 목록이 그보다 넓으면 화면이 서버가
 * 절대 보내지 않는 갈래를 들고 있게 되고, 좁으면 타입 검사가 정상 프레임을 거부한다.
 */
export type AdditionalTarget = "conversation" | "scenario_intake" | "pronunciation" | "shadowing";

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
  /**
   * 이 클립에 합성 오디오가 있는가 (`TASK-66` · 결정 90).
   *
   * ⛔ **파일명이 아니다** — 경로는 서버의 것이고 화면은 재생 버튼을 보일지만 정한다. 소리를
   * 받으려면 `/api/shadowing/clips/{item_id}/audio` 를 부른다.
   * ⚠️ 이 값이 `false` 면 버튼을 **숨긴다** — 눌러 보고 404 를 받는 화면은 학습자를 기다리게 한다.
   */
  has_audio: boolean;
}

export type ServerEvent =
  | {
      type: "session_started";
      session_id: string;
      shadowing?: ShadowingSetup;
      /**
       * 발음 전용 모드의 **오늘의 소리 후보 첫 항목** (`TASK-10.2` · 결정 72·83).
       *
       * ⛔ **키가 없는 것을 「폴백」으로 읽지 않는다.** 사용자 결정 72 가 그 폴백을 없앴다 —
       * `?mode=pronunciation` 이면 소리를 못 골라도 전용 모드로 열린다. 그래서 이 키의 부재는
       * **「오늘 다룰 소리가 아직 없다」**만 뜻한다. `shadowing` 과 같은 규약이다: 없는 것과
       * 「비었다」를 구분한다.
       * ⚠️ 그 부재가 예외가 아니라 **평시다** — 발음 기록이 0건이면 후보가 비고, 그것이 지금 dev
       * DB 의 상태다. 화면은 그때도 「발음 연습으로 시작했다」고 말해야 한다(결정 83).
       * ⚠️ 소리 키(`th_as_s`)는 기계 키다 — 그대로 렌더하지 않고 사람 말로 바꾼다
       * (설계서 §10 미결 4 와 같은 판단).
       */
      pronunciation_focus?: string;
    }
  | { type: "partial"; text: string; speaker: Speaker }
  /**
   * 확정된 전사문 한 줄.
   *
   * `utterance_type` 은 서버가 정한 발화의 종류다 — `learning`(학습 발화) · `voice_command`
   * (표지가 붙은 명령) · `command_confirmation`(확인 답). ⛔ 화면이 이 값을 **다시 판정하지
   * 않는다**: 표지 판정은 앱(서버)이 소유한다(`TASK-61.1` · 결정 102 ①).
   * ⚠️ 지금 화면은 이 값으로 갈라 그리지 않고 **줄을 남기는 것까지만** 한다 — 앞 판은 명령 발화에
   * 프레임 자체를 보내지 않아 화면이 비었고(`TASK-61.4` D4) 그 결함의 고침이 프레임의 존재다.
   */
  | {
      type: "final";
      text: string;
      speaker: Speaker;
      sequence_no: number;
      utterance_type?: string;
    }
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
  // 음성 명령 (`TASK-61.1` · 결정 102 · `TASK-61.6` · 결정 107). 서버가 명령을 **들었다는
  // 사실**을 알린다.
  //
  // ⛔ 화면이 이 프레임으로 세션을 끝내지 않는다 — 종료는 서버가 `stage: "confirmed"` 뒤에
  // 보내는 `session_ended` 가 정본이다. 확인을 화면이 앞질러 처리하면 확인 절차(결정 102 ③)가
  // 두 곳에 생긴다.
  //
  // ⚠️ **`show_report` 는 화면이 수행하는 유일한 명령이다** — 서버 상태가 바뀌지 않으므로
  // 서버가 뒤이어 보낼 프레임이 없다(결정 107 ②). 화면은 `stage: "requested"` 하나만 보고
  // 움직인다 — 확인을 타지 않는 명령이라 뒤 단계가 오지 않는 것이 정상이다(결정 107 ③).
  //
  // ⛔ **`next_question` 에 화면이 반응하지 않는 것은 «누락이 아니라 계약»이다**(결정 108 ②) —
  // 코치가 다음 질문을 말하므로 학습자가 들어서 안다. 화면 표시를 더하면 같은 사실을 두 곳이
  // 말하게 되고, 그 둘이 갈릴 때 어느 쪽이 참인지 정할 근거가 없다.
  //
  // ⛔ **`start_additional` 만 `target` 을 갖는다 — 갈래를 나눠 두는 이유가 그것이다.** 하나의
  // 모양에 옵셔널 키로 두면 화면이 `target` 이 없는 상태로도 새 세션을 열 수 있게 되고, 그것은
  // 「어느 학습을 열지 모르는 채 여는 것」이다(서버는 그 페이로드를 이미 버린다).
  | {
      type: "voice_command";
      command: "end" | "show_report" | "next_question";
      stage: "requested" | "confirmed" | "cancelled";
    }
  | {
      type: "voice_command";
      command: "start_additional";
      stage: "requested" | "confirmed" | "cancelled";
      target: AdditionalTarget;
    }
  // 표지가 없어 서버가 **실행하지 않은** 명령 (결정 113 · `TASK-61.16`).
  //
  // ⛔ **왜 `voice_command` 에 플래그로 붙이지 않는가** — 그 프레임의 처리부는 `show_report` 를
  // 열고 `start_additional` 을 기억한다. 같은 모양에 「실행 안 됨」 키를 두면 그 검사를 빠뜨리는
  // 순간 **버린 명령이 수행된다.** 별도 종류는 빠뜨려도 아무것도 수행되지 않는다.
  //
  // ⚠️ **이 프레임은 알림이고 명령이 아니다.** 화면이 할 일은 「되지 않았다」고 말하는 것 하나다 —
  // 코치는 이 시점에 이미 「됐다」고 말한 뒤다(어댑터가 tool 결과를 앱의 판정보다 먼저 돌려준다).
  //
  // ⛔ **`next_question` 은 오지 않는다** — 값역의 정본은 백엔드
  // `models/voice_command.SURFACED_ON_MARKER_MISS` 다. 위 「화면이 반응하지 않는 것은 계약이다」와
  // 같은 근거다: 그 명령은 버려져도 코치가 다음 질문을 하므로 화면이 어긋나지 않는다.
  | {
      type: "voice_command_ignored";
      command: "end" | "start_additional" | "show_report";
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

  constructor(handlers: SessionSocketHandlers, entry: SessionEntry = {}) {
    this.socket = new WebSocket(sessionSocketUrl(entry));
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
