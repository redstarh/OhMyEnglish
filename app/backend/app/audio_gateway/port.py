"""음성 어댑터 포트 (G3) — 게이트웨이가 아는 유일한 음성 계약.

데이터 경로만 고정한다: 연결 → 오디오 밀어넣기 → 이벤트 받기 → 닫기.
barge-in·세션 재개 같은 수명 협상은 Phase 2에서 확장하며, 지금 넣으면 스텁이
구현할 수 없는 표면만 늘어난다 (YAGNI).

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


# 어댑터가 흘리는 이벤트: 전사문 또는 오디오 응답 프레임(raw bytes).
AdapterEvent = TranscriptEvent | bytes


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
