"""픽스처 음성 어댑터 (AC 문서 §공통 픽스처) — 실제 음성 없이 세션 규칙을 관측한다.

두 가지 모드만 있다. `fixture`는 `FIXTURE_TURNS`를 순서대로 재생하고,
`unresponsive`는 `start()`가 영원히 pending 상태로 남아 **연결 실패 경로(G2)**를
만든다. 무응답을 예외로 표현하지 않는 것이 핵심이다 — 실제 장애는 예외가 아니라
"응답이 오지 않는 것"이고, 상한 없이 기다리는 구현은 그때만 매달린다. 예외를
던지는 대역으로는 그 버그를 절대 잡을 수 없다.

재생 순서는 한 턴당: **질문(agent final) → 사용자 partial 1~2개 → 사용자 final →
오디오 프레임**. partial을 여러 개 흘리는 것도 계약이다 — partial이 저장되면
행 수가 즉시 어긋나므로 "partial 미저장" 규칙이 관측 가능해진다.

이 모듈은 **주입으로만** 세션에 들어간다(`audio_gateway/factory.py`). 세션 러너나
소켓 계층이 이 파일을 import하면 테스트 대역이 프로덕션 의존성이 된다 (G3).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Literal, get_args

from app.audio_gateway.fixtures import FIXTURE_TURNS, TONE_WAV_FRAME
from app.audio_gateway.port import AdapterEvent, TranscriptEvent

StubMode = Literal["fixture", "unresponsive"]


def _partial_prefixes(answer: str) -> list[str]:
    """응답을 앞에서 자른 1~2개의 중간 전사문. 실제 STT의 partial처럼 같은 문장이
    점점 자라는 모양이라, 마지막 final만 저장되는지 확인할 수 있다."""
    words = answer.split()
    cuts = sorted({max(1, len(words) // 3), max(1, 2 * len(words) // 3)})
    return [" ".join(words[:cut]) for cut in cuts]


class StubVoiceAdapter:
    """`VoiceAdapter` 픽스처 구현. 수신 프레임 수와 받은 지시문을 속성으로 노출한다."""

    def __init__(self, mode: StubMode = "fixture", *, instructions: str | None = None) -> None:
        if mode not in get_args(StubMode):
            raise ValueError(f"알 수 없는 스텁 모드: {mode!r}")
        self.mode = mode
        self.closed = False
        self._received_frames = 0
        # 받아서 보관만 한다 — 재생 발화는 `FIXTURE_TURNS`가 결정한다(설계서 §5.2).
        # 스텁이 쓰지도 않는 값을 받는 이유: 조립 지점에서 어댑터까지 지시문이 실제로
        # 도달했는지 판정할 수단이 이것뿐이다(설계서 AS6). 팩토리(`factory.py`)가 스텁에도
        # 조립된 지시문을 넘기므로 그 판정이 스텁 모드에서 성립한다.
        # 실물 Nova의 응대가 지시문에 따라 달라지는지는 별개 확인이고 이 슬라이스의 범위가 아니다.
        # 키워드 전용인 것도 계약이다 — 위치로 받으면 기존 `StubVoiceAdapter("fixture")`·
        # `("unresponsive")` 호출 옆에 두 번째 값이 조용히 끼어들 수 있다.
        self._instructions = instructions

    @property
    def instructions(self) -> str | None:
        """생성 시점에 받은 지시문. 스텁은 이 값을 읽지 않으므로 쓰기를 열지 않는다 —
        `NovaVoiceAdapter.instructions`가 public 속성인 것과 갈리는 지점이다."""
        return self._instructions

    @property
    def received_frames(self) -> int:
        """클라이언트가 밀어넣은 오디오 프레임 수 — 릴레이가 실제로 어댑터까지
        닿았는지 확인하는 유일한 관측 지점이다."""
        return self._received_frames

    async def start(self) -> None:
        if self.mode == "unresponsive":
            # 영원히 pending. 취소(= 호출자의 타임아웃)로만 끝난다.
            await asyncio.Event().wait()

    async def send_audio(self, frame: bytes) -> None:
        self._received_frames += 1

    async def events(self) -> AsyncIterator[AdapterEvent]:
        for question, answer in FIXTURE_TURNS:
            yield TranscriptEvent(kind="final", text=question, speaker="agent")
            for prefix in _partial_prefixes(answer):
                yield TranscriptEvent(kind="partial", text=prefix, speaker="user")
            yield TranscriptEvent(kind="final", text=answer, speaker="user")
            yield TONE_WAV_FRAME

    async def close(self) -> None:
        self.closed = True
