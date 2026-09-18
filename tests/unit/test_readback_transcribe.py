"""`services/readback.transcribe_readback` — 낭독 녹음의 PCM 에서 전사문만 얻는다 (`TASK-206`).

설계: `docs/design/2026-09-18-read-aloud-judgment-design.md` §4-2.

⛔ **코치 응답을 버리는 것이 계약이다.** 어댑터는 대화형이라 agent 전사문과 오디오를 함께 내는데
낭독 판정에 필요한 것은 **학습자의 final 전사문 하나**뿐이다. 그래서 이 파일은 「agent 것을 돌려주지
않는다」와 「학습자 것이 없으면 빈 문자열이다」를 각각 고정한다.

⚠️ **응답이 없는 어댑터에서 매달리지 않는 것도 계약이다** — 실물 Nova 가 조용할 수 있고
(`stub_unresponsive` 가 그 형태다) 그러면 엔드포인트가 영원히 열린다.

⛔ **WAV 가 아니라 PCM 을 넘긴다** — 접근 규칙의 소유자(`recordings.load_recording`)가 헤더 없는
PCM 을 돌려주므로 그 산출물을 그대로 받는 것이 계약이다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.audio_gateway.fixtures import FIXTURE_TURNS
from app.audio_gateway.port import AdapterEvent, TranscriptEvent
from app.audio_gateway.stub import StubVoiceAdapter
from app.services.readback import transcribe_readback

_PCM = b"\x00\x01" * 8000  # 16kHz·16bit 기준 1초


class _AgentOnlyAdapter:
    """agent 전사문만 내고 학습자 것은 내지 않는 어댑터 — 계약의 반쪽을 시험한다."""

    def __init__(self) -> None:
        self.closed = False
        self.received_frames = 0

    async def start(self) -> None:
        return None

    async def send_audio(self, frame: bytes) -> None:
        self.received_frames += 1

    async def events(self) -> AsyncIterator[AdapterEvent]:
        yield TranscriptEvent(kind="final", text="Nice reading!", speaker="agent")

    async def report_command_outcome(
        self, tool_use_id: str, *, executed: bool, reason: str | None = None
    ) -> None:
        return None

    async def close(self) -> None:
        self.closed = True


async def test_학습자의_final_전사문을_돌려준다() -> None:
    adapter = StubVoiceAdapter()
    assert await transcribe_readback(_PCM, make_adapter=lambda: adapter) == FIXTURE_TURNS[0][1]


async def test_코치의_전사문을_돌려주지_않는다() -> None:
    """⛔ 빈 문자열만 단정하면 「아무것도 안 하는 구현」에서도 통과한다.

    그래서 흘려보낸 프레임 수도 함께 본다 — 그 단정이 이 테스트의 판별력이다.
    """
    adapter = _AgentOnlyAdapter()
    assert await transcribe_readback(_PCM, make_adapter=lambda: adapter) == ""
    assert adapter.received_frames > 0


async def test_PCM_이_남김없이_어댑터까지_닿는다() -> None:
    adapter = StubVoiceAdapter()
    await transcribe_readback(_PCM, make_adapter=lambda: adapter, frame_bytes=3000)
    expected_frames = -(-len(_PCM) // 3000)  # 마지막 조각이 짧아도 보낸다
    assert expected_frames == 6, "픽스처가 나누어떨어지면 마지막 조각을 시험하지 못한다"
    assert adapter.received_frames == expected_frames


async def test_전사를_얻은_뒤_어댑터를_닫는다() -> None:
    adapter = StubVoiceAdapter()
    await transcribe_readback(_PCM, make_adapter=lambda: adapter)
    assert adapter.closed is True


async def test_전사를_얻지_못해도_어댑터를_닫는다() -> None:
    adapter = _AgentOnlyAdapter()
    await transcribe_readback(_PCM, make_adapter=lambda: adapter)
    assert adapter.closed is True


async def test_응답이_없는_어댑터에서_매달리지_않고_빈_문자열이다() -> None:
    adapter = StubVoiceAdapter("unresponsive")
    assert await transcribe_readback(_PCM, make_adapter=lambda: adapter, timeout_s=0.05) == ""
    assert adapter.closed is True
