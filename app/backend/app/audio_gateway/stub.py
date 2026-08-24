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
    """`VoiceAdapter` 픽스처 구현. `received_frames`로 수신 프레임 수를 노출한다."""

    def __init__(self, mode: StubMode = "fixture") -> None:
        if mode not in get_args(StubMode):
            raise ValueError(f"알 수 없는 스텁 모드: {mode!r}")
        self.mode = mode
        self.closed = False
        self._received_frames = 0

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
