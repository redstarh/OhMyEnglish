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


async def test_학습자의_final_전사문을_모아_돌려준다() -> None:
    """⛔ **첫 final 하나만 받으면 안 된다** (2026-09-18 실측 · `TASK-210`).

    실물 Nova 는 끊어 읽는 자리마다 final 을 낸다. 여섯 문장 클립을 낭독했을 때 저장된 전사가
    **첫 두 문장뿐**이었고, 그래서 학습자가 «읽은» 32낱말이 화면에서 「빠짐」으로 표시됐다.
    ⇒ 조용해질 때까지 모아 이어 붙인다. 스텁은 세 턴을 내므로 세 답이 다 들어온다.
    """
    adapter = StubVoiceAdapter()
    text = await transcribe_readback(_PCM, make_adapter=lambda: adapter)
    assert text == " ".join(answer for _, answer in FIXTURE_TURNS)


async def test_코치의_전사문을_돌려주지_않는다() -> None:
    """⛔ 빈 문자열만 단정하면 「아무것도 안 하는 구현」에서도 통과한다.

    그래서 흘려보낸 프레임 수도 함께 본다 — 그 단정이 이 테스트의 판별력이다.
    """
    adapter = _AgentOnlyAdapter()
    assert await transcribe_readback(_PCM, make_adapter=lambda: adapter) == ""
    assert adapter.received_frames > 0


async def test_PCM_이_남김없이_어댑터까지_닿는다() -> None:
    """⚠️ 침묵을 0 으로 두고 잰다 — 그러지 않으면 「PCM 이 다 갔는가」와 「침묵을 붙였는가」가 한
    수치에 섞여 어느 쪽이 깨졌는지 가릴 수 없다."""
    adapter = StubVoiceAdapter()
    await transcribe_readback(_PCM, make_adapter=lambda: adapter, frame_bytes=3000, silence_bytes=0)
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


async def test_끝에_침묵을_붙여_보낸다() -> None:
    """⛔ **침묵이 없으면 실물 Nova 가 전사를 아예 주지 않는다** (2026-09-18 실측 · `TASK-210`).

    같은 오디오를 침묵 없이 보냈을 때 전사가 **빈 문자열**이었고, 끝에 2초를 붙이자
    `'alright, so here we are in of the elephants.'` 가 왔다. VAD 가 침묵으로 발화를 닫기 때문이다.
    ⇒ 이 프레임 수 단정이 그 발견을 코드에 고정한다.
    """
    adapter = StubVoiceAdapter()
    await transcribe_readback(
        _PCM, make_adapter=lambda: adapter, frame_bytes=3200, silence_bytes=6400
    )
    assert adapter.received_frames == -(-(len(_PCM) + 6400) // 3200)


async def test_침묵_기본값이_0이_아니다() -> None:
    """⛔ 기본값이 0이면 실물에서 전사가 오지 않는다 — 그 갈래를 기본값으로 두지 않는다."""
    padded = StubVoiceAdapter()
    bare = StubVoiceAdapter()
    await transcribe_readback(_PCM, make_adapter=lambda: padded, frame_bytes=3200)
    await transcribe_readback(_PCM, make_adapter=lambda: bare, frame_bytes=3200, silence_bytes=0)
    assert padded.received_frames > bare.received_frames
