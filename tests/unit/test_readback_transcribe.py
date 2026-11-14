"""낭독 녹음의 PCM 에서 전사문만 얻는다 — `audio_gateway/transcribe` (`TASK-206`).

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

import asyncio
import time
from collections.abc import AsyncIterator

import pytest

from app.audio_gateway.fixtures import FIXTURE_TURNS
from app.audio_gateway.port import (
    AdapterEvent,
    SpeechBoundaryEvent,
    TranscriberUnavailable,
    TranscriptEvent,
)
from app.audio_gateway.stub import StubVoiceAdapter
from app.audio_gateway.transcribe import readback_timeout_s, transcribe_readback

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


class _FailedAdapter(_AgentOnlyAdapter):
    """출력 스트림이 실패로 끝난 어댑터 — 실물 Nova 의 `failure` 모양만 흉내낸다(`TASK-288`)."""

    def __init__(self) -> None:
        super().__init__()
        self.failure: BaseException | None = PermissionError("denied")

    async def events(self) -> AsyncIterator[AdapterEvent]:
        return
        yield  # pragma: no cover — 비동기 생성기로 만들기 위한 자리


async def test_어댑터가_실패로_끝나면_빈_전사가_아니라_예외다() -> None:
    """⛔ 인증 거부를 「안 들렸다」로 읽으면 시도가 기록되고 학습자는 다시 말해 본다(회차 b6 D1)."""
    adapter = _FailedAdapter()
    with pytest.raises(TranscriberUnavailable):
        await transcribe_readback(_PCM, make_adapter=lambda: adapter)
    assert adapter.closed is True


class _UnreachableAdapter(_AgentOnlyAdapter):
    """연결을 열지 못하는 어댑터 — 스트림 열기·초기화 전송의 실패를 흉내낸다."""

    async def start(self) -> None:
        raise PermissionError("denied")


async def test_연결을_열지_못하면_예외다() -> None:
    """⛔ 500 이 아니라 503 으로 가야 한다.

    라우터는 `TranscriberUnavailable` 만 옮긴다(codex 리뷰).
    """
    adapter = _UnreachableAdapter()
    with pytest.raises(TranscriberUnavailable):
        await transcribe_readback(_PCM, make_adapter=lambda: adapter)
    assert adapter.closed is True


# ── 말 시작이 없는 녹음의 조기 종료 · 녹음 길이에 맞춘 상한 (`TASK-317` · 설계서 §7-⑥) ──
# ⛔ 이전에는 학습자 final 이 하나도 오지 않으면 30초 상한을 다 기다렸다.
# 시도 간격 약 37초의 원인이다.


class _SilentAdapter(_AgentOnlyAdapter):
    """아무 이벤트도 내지 않고 스트림을 열어 두는 어댑터 — 실물 Nova 가 말을 못 들은 모양이다."""

    async def events(self) -> AsyncIterator[AdapterEvent]:
        await asyncio.Event().wait()
        yield TranscriptEvent(kind="final", text="never", speaker="user")  # pragma: no cover


class _LateFinalAdapter(_AgentOnlyAdapter):
    """말 시작을 알린 뒤 `delay_s` 가 지나서 학습자 final 을 낸다."""

    def __init__(self, delay_s: float) -> None:
        super().__init__()
        self.delay_s = delay_s

    async def events(self) -> AsyncIterator[AdapterEvent]:
        yield SpeechBoundaryEvent(speaking=True)
        await asyncio.sleep(self.delay_s)
        yield TranscriptEvent(kind="final", text="we walk where we live", speaker="user")
        await asyncio.Event().wait()


class _SpeakingForeverAdapter(_AgentOnlyAdapter):
    """말 시작만 알리고 final 을 내지 않는 어댑터 — 상한만이 이 호출을 끝낸다."""

    async def events(self) -> AsyncIterator[AdapterEvent]:
        yield SpeechBoundaryEvent(speaking=True)
        await asyncio.Event().wait()


async def test_말_시작이_없으면_상한까지_기다리지_않고_빈_전사다() -> None:
    adapter = _SilentAdapter()
    started = time.monotonic()
    text = await transcribe_readback(
        _PCM, make_adapter=lambda: adapter, timeout_s=5.0, no_speech_s=0.05
    )
    assert text == ""
    assert time.monotonic() - started < 1.0
    assert adapter.closed is True


async def test_말_시작이_오면_조기_종료하지_않는다() -> None:
    """⛔ 판별력: 조기 종료 창(0.05초)보다 final 이 늦게(0.3초) 와도 그 final 을 받는다."""
    adapter = _LateFinalAdapter(delay_s=0.3)
    text = await transcribe_readback(
        _PCM, make_adapter=lambda: adapter, no_speech_s=0.05, quiet_s=0.05
    )
    assert text == "we walk where we live"


async def test_상한은_녹음_길이를_따른다() -> None:
    """말 시작은 왔으나 final 이 없을 때 — 30초가 아니라 「녹음 초 + 여유」에서 끝난다."""
    adapter = _SpeakingForeverAdapter()
    started = time.monotonic()
    text = await transcribe_readback(_PCM, make_adapter=lambda: adapter, length_slack_s=0.1)
    assert text == ""
    # 녹음 1초 + 여유 0.1초 — 30초 상한이 그대로면 여기서 30초를 기다린다.
    assert time.monotonic() - started < 3.0


def test_상한_계산은_녹음_초_더하기_10초이고_30초를_넘지_않는다() -> None:
    """⚠️ 쉐도잉 낭독 판정도 같은 함수를 쓴다 — 긴 클립은 30초 상한이 그대로 남는다(`min`)."""
    one_second = 16_000 * 2
    assert readback_timeout_s(one_second) == 11.0
    assert readback_timeout_s(one_second * 25) == 30.0
    assert readback_timeout_s(one_second, timeout_s=0.05) == 0.05


class _EndlessFinalsAdapter(_AgentOnlyAdapter):
    """말 시작 뒤 학습자 final 을 `gap_s` 마다 끝없이 낸다 — 조용해지지 않아 상한만이 끝낸다."""

    def __init__(self, gap_s: float) -> None:
        super().__init__()
        self.gap_s = gap_s

    async def events(self) -> AsyncIterator[AdapterEvent]:
        yield SpeechBoundaryEvent(speaking=True)
        index = 0
        while True:
            await asyncio.sleep(self.gap_s)
            index += 1
            yield TranscriptEvent(kind="final", text=f"part{index}", speaker="user")


async def test_상한이_끝내도_이미_모은_final_은_버리지_않는다() -> None:
    """codex 리뷰 HIGH(`TASK-317`) — 상한이 짧아진 뒤 이 갈래가 들린 말을 빈 전사로 만들었다.

    ⛔ 상한은 그대로 지킨다 — 시간 단정이 그 판별력이다.
    """
    adapter = _EndlessFinalsAdapter(gap_s=0.05)
    started = time.monotonic()
    text = await transcribe_readback(
        _PCM, make_adapter=lambda: adapter, quiet_s=1.0, length_slack_s=0.0
    )
    elapsed = time.monotonic() - started
    # 녹음 1초 + 여유 0초 = 상한 1초.
    assert elapsed < 2.0
    assert text.startswith("part1 part2")
    assert adapter.closed is True
