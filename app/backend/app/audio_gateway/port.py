"""음성 어댑터 포트 (G3) — 게이트웨이가 아는 유일한 음성 계약.

데이터 경로를 고정한다: 연결 → 오디오 밀어넣기 → 이벤트 받기 → 닫기.

**Phase 2 확장 (2026-08-26, N-1 실측 기준).** 첫 슬라이스의 포트는 `TranscriptEvent |
bytes`뿐이었다. Nova 2 Sonic 실연동에서 그 둘에 담을 수 없는 신호 둘이 나와 여기서
확장한다 — 설계서 §7이 예고한 확장이다:

* `SpeechBoundaryEvent` — Nova의 `userSpeechStart`/`userSpeechEnd`. **사용자 부분
  전사문이 없기 때문에**(사용자 ASR은 `generationStage: FINAL` 한 블록으로만 온다)
  "듣고 있다"를 화면에 표시할 근거가 이 경계뿐이다.
* `InterruptionEvent` — `contentEnd.stopReason = "INTERRUPTED"`. barge-in은 "이미
  받았지만 아직 재생하지 않은 오디오를 버리는 것"이라, 통보가 없으면 클라이언트는
  버릴 시점을 알 수 없다.

agent 텍스트의 **예고/확정 구분**(`generationStage`가 `SPECULATIVE`인지 `FINAL`인지)에는
새 타입을 만들지 않는다 — `kind`가 이미 그 구분이다. `partial`은 화면 표시용이고 저장되지
않으므로(`session.py` 계약 1) `SPECULATIVE`가 그대로 대응한다. 타입을 하나 더 만들면 같은
구분이 포트에 두 벌 생긴다.

`events()`가 `TranscriptEvent | bytes` 두 종류를 같은 스트림으로 흘리는 것은
의도된 것이다. 전사문과 오디오 응답은 **하나의 시간 순서**를 갖는다 — 스트림을
둘로 나누면 "질문 오디오가 그 질문의 전사문보다 먼저/나중"이라는 순서가 어댑터
바깥에서 재구성 불가능해진다.

`speaker`는 이벤트에 실려 온다. 전사문이 사용자의 발화인지 agent의 질문인지는
어댑터만 알 수 있고(같은 소켓으로 둘 다 온다), 그 구분이 곧 "분석 대상인가"를
결정한다(W6) — 게이트웨이가 추측할 수 있는 값이 아니다.

`sequence_no`는 어댑터가 채우지 않는다(`None`). 세션 안의 순번은 서버가 DB에서
단조 증가로 부여하는 값이라(`services.utterances`) 어댑터가 보낸 번호를 믿으면
두 소유자가 생긴다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Literal, Protocol

import pydantic

Speaker = Literal["user", "agent"]


class TranscriptEvent(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    kind: Literal["partial", "final"]
    text: str
    speaker: Speaker = "user"
    # 서버가 저장 시점에 부여한다. 어댑터가 만든 이벤트에서는 항상 None이다.
    sequence_no: int | None = None


class SpeechBoundaryEvent(pydantic.BaseModel):
    """사용자 발화의 시작/끝. 전사문이 아니므로 저장되지 않는다.

    `offset_ms`는 어댑터가 아는 값이면 실어 보내고(Nova의 `inputAudioOffsetMs`),
    모르면 `None`이다 — 경계 자체가 계약이고 오프셋은 진단용 부가 정보다.
    """

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    speaking: bool
    offset_ms: int | None = None


class InterruptionEvent(pydantic.BaseModel):
    """agent 출력이 사용자 발화로 끊겼다 (barge-in).

    필드가 없는 것은 의도다. 클라이언트가 이 통보로 하는 일은 하나뿐이고(재생 대기 중인
    오디오를 버린다) 그 판단에 "언제·어디까지"는 필요하지 않다 — 이미 재생된 것은
    되돌릴 수 없고, 남은 큐는 전부 버린다.
    """

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)


# 어댑터가 흘리는 이벤트: 전사문, 오디오 응답 프레임(raw bytes), 발화 경계, barge-in 통보.
AdapterEvent = TranscriptEvent | SpeechBoundaryEvent | InterruptionEvent | bytes


class VoiceAdapter(Protocol):
    async def start(self) -> None:
        """연결을 수립한다. 성공하기 전까지 반환하지 않는다 — 호출자가 상한을
        건다(`session.CONNECT_TIMEOUT`)."""
        ...

    async def send_audio(self, frame: bytes) -> None: ...

    def events(self) -> AsyncIterator[AdapterEvent]:
        """세션이 끝나면 스트림이 소진된다(= 대화 종료)."""
        ...

    async def close(self) -> None:
        """자원을 정리한다. 여러 번 불려도 안전해야 한다."""
        ...
