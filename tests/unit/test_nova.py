"""Fix round 3 (N-4) — Nova 2 Sonic 어댑터 계약 테스트.

실물을 호출하지 않는다. 대신 **실측 이벤트를 그대로 재생한다** —
`tests/harness/runs/2026-08-26-N1/N1-nova-protocol.json`(N-1 PASS)에서 옮긴 이벤트
이름·필드·값 모양을 리터럴로 두고, 그것을 어댑터가 포트 이벤트로 어떻게 바꾸는지만 본다.
스키마를 다시 추측하지 않기 위해 필드 이름을 손으로 다듬지 않았다.

가짜 스트림은 SDK의 실제 입력 객체(`InvokeModelWithBidirectionalStreamInputChunk`)를
그대로 받는다 — 직렬화 경로까지 테스트가 지나가게 하려는 것이다. 대역이 dict를 받으면
"테스트는 통과하는데 실물은 4xx"가 되는 경로가 남는다.
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import pytest

from app.audio_gateway.nova import (
    FRAME_BYTES,
    NovaEventTranslator,
    NovaVoiceAdapter,
)
from app.audio_gateway.port import InterruptionEvent, SpeechBoundaryEvent, TranscriptEvent
from app.config import Settings

# --- N-1 실측에서 옮긴 값 ---

PROMPT_NAME = "6544ae5b-33e2-4c92-8f3c-1725c81846ac"
SESSION_ID = "b56646ec-3c27-4410-a389-5dfc6262083c"
COMPLETION_ID = "76b22bb5-ad74-4f75-87b1-95e146a54d1b"
USER_CONTENT_ID = "0ecf77f7-e520-4689-a2c0-5d14da133426"
AGENT_TEXT_CONTENT_ID = "e45dcf13-affa-45ee-9b28-cf8a056e9d00"
AGENT_AUDIO_CONTENT_ID = "50c01f05-f439-4ff2-8646-e6a5ec1021d7"

USER_TRANSCRIPT = "i usually go to gym after work."  # u1.wav 픽스처와 일치했다
AGENT_TEXT = "That's a great routine."
# 실측 audioOutput은 헤더 없는 raw LPCM이었다(앞 4바이트가 RIFF가 아니었다).
AGENT_AUDIO = b"+\x00,\x00-\x00.\x00"


def _envelope(*, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {"promptName": PROMPT_NAME, "sessionId": SESSION_ID, "completionId": COMPLETION_ID}
    body.update(extra or {})
    return body


def _content_start(
    content_id: str, role: str, stage: str | None, content_type: str = "TEXT"
) -> tuple[str, dict[str, Any]]:
    extra: dict[str, Any] = {"contentId": content_id, "role": role, "type": content_type}
    if stage is not None:
        # 실측: 문자열로 온다(dict가 아니다).
        extra["additionalModelFields"] = json.dumps({"generationStage": stage})
    return ("contentStart", _envelope(extra=extra))


def _text_output(content_id: str, role: str, content: str) -> tuple[str, dict[str, Any]]:
    extra = {"contentId": content_id, "role": role, "content": content}
    return ("textOutput", _envelope(extra=extra))


def _content_end(content_id: str, stop_reason: str) -> tuple[str, dict[str, Any]]:
    return ("contentEnd", _envelope(extra={"contentId": content_id, "stopReason": stop_reason}))


RECORDED_RUN: list[tuple[str, dict[str, Any]]] = [
    ("userSpeechStart", _envelope(extra={"inputAudioOffsetMs": 0})),
    ("completionStart", _envelope()),
    (
        "userSpeechEnd",
        _envelope(extra={"inputAudioOffsetMs": 1920, "inputAudioDetectionOffsetMs": 2400}),
    ),
    _content_start(USER_CONTENT_ID, "USER", "FINAL"),
    _text_output(USER_CONTENT_ID, "USER", USER_TRANSCRIPT),
    _content_end(USER_CONTENT_ID, "PARTIAL_TURN"),
    _content_start(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "SPECULATIVE"),
    _text_output(AGENT_TEXT_CONTENT_ID, "ASSISTANT", AGENT_TEXT),
    _content_end(AGENT_TEXT_CONTENT_ID, "PARTIAL_TURN"),
    _content_start(AGENT_AUDIO_CONTENT_ID, "ASSISTANT", None, content_type="AUDIO"),
    (
        "audioOutput",
        _envelope(
            extra={
                "contentId": AGENT_AUDIO_CONTENT_ID,
                "role": "ASSISTANT",
                "content": base64.b64encode(AGENT_AUDIO).decode("ascii"),
            }
        ),
    ),
    _content_end(AGENT_AUDIO_CONTENT_ID, "END_TURN"),
    ("usageEvent", _envelope(extra={"totalTokens": 42})),
    ("completionEnd", _envelope(extra={"stopReason": "END_TURN"})),
]


def _translate_all(events: list[tuple[str, dict[str, Any]]]) -> list[Any]:
    translator = NovaEventTranslator()
    return [event for name, body in events for event in translator.translate(name, body)]


# --- 번역 계약 ---


def test_the_recorded_run_translates_into_port_events():
    assert _translate_all(RECORDED_RUN) == [
        SpeechBoundaryEvent(speaking=True, offset_ms=0),
        SpeechBoundaryEvent(speaking=False, offset_ms=1920),
        # 사용자 ASR은 FINAL 한 블록으로만 온다 — 그래서 저장·job 등록으로 이어진다.
        TranscriptEvent(kind="final", text=USER_TRANSCRIPT, speaker="user"),
        # ASSISTANT의 SPECULATIVE는 예고다 — 화면에만 뜨고 저장되지 않는다.
        TranscriptEvent(kind="partial", text=AGENT_TEXT, speaker="agent"),
        AGENT_AUDIO,
        # 턴이 끝나면 실제로 말한 그 문장을 확정으로 올린다(아래 테스트에서 근거를 적었다).
        TranscriptEvent(kind="final", text=AGENT_TEXT, speaker="agent"),
    ]


# Nova는 단일 턴 실측에서 ASSISTANT 텍스트를 SPECULATIVE로만 보냈다. 승격하지 않으면
# agent 질문이 전사문에 한 행도 남지 않아, 스텁으로 검증한 거동(질문 3 + 응답 3행)과
# 실연동이 갈라진다. completionEnd는 Nova 자신이 "이 턴은 끝났다"고 알리는 신호다.
def test_speculative_agent_text_is_promoted_to_final_when_the_turn_ends():
    translated = _translate_all(
        [
            _content_start(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "SPECULATIVE"),
            _text_output(AGENT_TEXT_CONTENT_ID, "ASSISTANT", AGENT_TEXT),
            ("completionEnd", _envelope(extra={"stopReason": "END_TURN"})),
        ]
    )

    assert translated == [
        TranscriptEvent(kind="partial", text=AGENT_TEXT, speaker="agent"),
        TranscriptEvent(kind="final", text=AGENT_TEXT, speaker="agent"),
    ]


# FINAL이 실제로 오는 대화에서는 승격이 일어나선 안 된다 — 같은 질문이 두 행 저장된다.
def test_a_final_agent_text_is_not_stored_twice_at_the_end_of_the_turn():
    translated = _translate_all(
        [
            _content_start(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "SPECULATIVE"),
            _text_output(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "That's a great"),
            _content_start("later-content", "ASSISTANT", "FINAL"),
            _text_output("later-content", "ASSISTANT", AGENT_TEXT),
            ("completionEnd", _envelope(extra={"stopReason": "END_TURN"})),
        ]
    )

    assert translated == [
        TranscriptEvent(kind="partial", text="That's a great", speaker="agent"),
        TranscriptEvent(kind="final", text=AGENT_TEXT, speaker="agent"),
    ]


# barge-in. 이 통보가 없으면 클라이언트는 재생 대기 중인 오디오를 버릴 시점을 알 수 없다.
def test_interrupted_content_end_is_reported_as_a_barge_in():
    translated = _translate_all([_content_end(AGENT_AUDIO_CONTENT_ID, "INTERRUPTED")])

    assert translated == [InterruptionEvent()]


# 문서에 없는 이벤트가 실제로 온다(`userSpeechStart`/`userSpeechEnd`가 그랬다).
# 파서가 모르는 이벤트에 죽으면 다음 필드 추가가 세션을 끊는다.
@pytest.mark.parametrize(
    ("name", "body"),
    [
        ("brandNewEventNobodyDocumented", {"whatever": 1}),
        ("usageEvent", {"totalTokens": 12}),
        ("completionStart", {}),
        ("contentStart", {}),
        ("textOutput", {}),
        ("textOutput", {"content": "", "role": "USER"}),
        ("audioOutput", {"content": "not-base64!!"}),
        ("contentEnd", {}),
        ("completionEnd", {}),
    ],
)
def test_unknown_or_malformed_events_are_survived(name: str, body: dict[str, Any]):
    assert NovaEventTranslator().translate(name, body) == []


# 경계 자체가 계약이고 오프셋은 부가 정보다 — 오프셋이 없거나 모양이 바뀌어도 경계는
# 그대로 흘러야 한다. 화면의 "듣고 있어요"가 이 경계에만 매달려 있다.
@pytest.mark.parametrize("body", [{"promptName": PROMPT_NAME}, {"inputAudioOffsetMs": "바뀜"}])
def test_a_boundary_survives_a_missing_or_reshaped_offset(body: dict[str, Any]):
    translated = NovaEventTranslator().translate("userSpeechStart", body)

    assert translated == [SpeechBoundaryEvent(speaking=True, offset_ms=None)]


# --- 어댑터: 스트림 배선 ---


class _FakeReceiver:
    def __init__(self, chunks: list[Any]) -> None:
        self._chunks = list(chunks)

    async def receive(self) -> Any:
        if self._chunks:
            return self._chunks.pop(0)
        await asyncio.Event().wait()  # 조용한 스트림 — 상한이 끝낸다
        raise AssertionError("unreachable")


class _FakeOutputChunk:
    """SDK 출력 청크의 모양만 흉내낸다 (`chunk.value.bytes_`)."""

    class _Value:
        def __init__(self, raw: bytes) -> None:
            self.bytes_ = raw

    def __init__(self, payload: dict[str, Any]) -> None:
        self.value = self._Value(json.dumps(payload).encode())


class _FakeInputStream:
    def __init__(self, owner: _FakeStream) -> None:
        self._owner = owner

    async def send(self, chunk: Any) -> None:
        # SDK 입력 객체를 그대로 받아 직렬화된 본문을 되읽는다.
        self._owner.sent.append(json.loads(chunk.value.bytes_))
        self._owner.input_arrived.set()


class _FakeStream:
    """양방향 스트림 대역.

    `output_requires_input=True`가 실측 함정을 재현한다 — `await_output()`은 클라이언트가
    초기화 이벤트를 보내기 전에는 반환하지 않는다. 어댑터가 수신을 먼저 기다리면 여기서
    영원히 멈춘다.
    """

    def __init__(self, *chunks: dict[str, Any], output_requires_input: bool = True) -> None:
        self.sent: list[dict[str, Any]] = []
        self.closed = False
        self.input_stream = _FakeInputStream(self)
        self.input_arrived = asyncio.Event()
        self._chunks = [_FakeOutputChunk(chunk) for chunk in chunks]
        self._output_requires_input = output_requires_input

    async def open(self) -> _FakeStream:
        return self

    async def await_output(self) -> tuple[None, _FakeReceiver]:
        if self._output_requires_input:
            await self.input_arrived.wait()
        return None, _FakeReceiver([*self._chunks, None])

    async def close(self) -> None:
        self.closed = True

    @property
    def event_names(self) -> list[str]:
        return [next(iter(payload["event"])) for payload in self.sent]

    def payloads(self, name: str) -> list[dict[str, Any]]:
        return [payload["event"][name] for payload in self.sent if name in payload["event"]]


def _settings() -> Settings:
    return Settings(
        database_url="postgresql://unused/unused",
        aws_region="us-west-2",
        voice_adapter="nova",
    )


def _adapter(stream: _FakeStream, **kwargs: Any) -> NovaVoiceAdapter:
    return NovaVoiceAdapter(_settings(), open_stream=stream.open, **kwargs)


async def test_start_sends_the_initialization_sequence_in_the_recorded_order():
    stream = _FakeStream()
    adapter = _adapter(stream)

    await adapter.start()
    await adapter.close()

    assert stream.event_names[:6] == [
        "sessionStart",
        "promptStart",
        "contentStart",
        "textInput",
        "contentEnd",
        "contentStart",
    ]


async def test_start_configures_the_audio_formats_nova_requires():
    stream = _FakeStream()
    adapter = _adapter(stream)

    await adapter.start()
    await adapter.close()

    # barge-in(AC2) 민감도는 Nova 2에서 여기서 정해진다.
    assert stream.payloads("sessionStart")[0]["turnDetectionConfiguration"] == {
        "endpointingSensitivity": "MEDIUM"
    }
    output_config = stream.payloads("promptStart")[0]["audioOutputConfiguration"]
    audio_start = stream.payloads("contentStart")[-1]
    input_config = audio_start["audioInputConfiguration"]
    for config in (output_config, input_config):
        assert config["mediaType"] == "audio/lpcm"
        assert config["sampleRateHertz"] == 16_000
        assert config["sampleSizeBits"] == 16
        assert config["channelCount"] == 1
        assert config["encoding"] == "base64"
        assert config["audioType"] == "SPEECH"
    # 사용자 오디오는 대화 중 끼어들 수 있어야 한다.
    assert audio_start["type"] == "AUDIO"
    assert audio_start["role"] == "USER"
    assert audio_start["interactive"] is True


# 실측 함정: `await_output()`은 초기화 이벤트를 보내기 전에 반환하지 않는다(HTTP 응답
# 헤더 자체가 오지 않는다) — 먼저 기다리면 20초 타임아웃이었다. 송수신을 동시에 시작한다.
async def test_receiving_starts_before_the_initialization_events_are_sent():
    stream = _FakeStream(output_requires_input=True)
    adapter = _adapter(stream)

    await asyncio.wait_for(adapter.start(), timeout=1.0)
    await adapter.close()


async def test_audio_frames_are_sent_as_base64_audio_input():
    stream = _FakeStream()
    adapter = _adapter(stream)
    frame = bytes(FRAME_BYTES)
    await adapter.start()

    await adapter.send_audio(frame)
    await adapter.close()

    audio_inputs = stream.payloads("audioInput")
    assert len(audio_inputs) == 1
    assert base64.b64decode(audio_inputs[0]["content"]) == frame
    # 오디오 프레임은 자기 contentStart가 연 content에 붙어야 한다.
    assert audio_inputs[0]["contentName"] == stream.payloads("contentStart")[-1]["contentName"]
    assert audio_inputs[0]["promptName"] == stream.payloads("promptStart")[0]["promptName"]


# N12(포맷 불일치 방어)의 최소선: 16bit 샘플 경계에 맞지 않는 프레임은 raw LPCM이 아니다.
# 조용히 흘려보내면 Nova가 잡음을 전사하고 원인을 어디서도 알 수 없다.
async def test_a_frame_that_breaks_the_sample_boundary_is_dropped():
    stream = _FakeStream()
    adapter = _adapter(stream)
    await adapter.start()

    await adapter.send_audio(b"\x01")
    await adapter.send_audio(b"")
    await adapter.close()

    assert stream.payloads("audioInput") == []


async def test_events_are_the_translation_of_the_stream_output():
    stream = _FakeStream(
        *({"event": {name: body}} for name, body in RECORDED_RUN),
        output_requires_input=False,
    )
    adapter = _adapter(stream)
    await adapter.start()

    received = [event async for event in adapter.events()]

    await adapter.close()
    assert received == _translate_all(RECORDED_RUN)


# 사용자가 종료를 누르면 프레임이 끊기므로 endpointing이 발동하지 않을 수 있다 —
# contentEnd로 명시적으로 닫는다. close는 여러 번 불려도 안전해야 한다(포트 계약).
async def test_close_sends_the_explicit_end_sequence_and_is_idempotent():
    stream = _FakeStream()
    adapter = _adapter(stream)
    await adapter.start()

    await adapter.close()
    sent_after_first_close = list(stream.event_names)
    await adapter.close()

    assert sent_after_first_close[-3:] == ["contentEnd", "promptEnd", "sessionEnd"]
    assert stream.event_names == sent_after_first_close
    assert stream.closed


# 연결 실패 경로에서도 세션은 `adapter.close()`를 부른다(`session._close_and_record`).
async def test_close_before_start_does_not_raise():
    await _adapter(_FakeStream()).close()


# 스트림 상한은 8분이다(SDK docstring). 롤오버는 이번 범위가 아니지만, 상한에 닿았을 때
# 조용히 매달려 있으면 세션이 영원히 `active`로 남는다 — 스트림을 끝내 세션을 닫게 한다.
async def test_the_stream_time_limit_ends_the_event_stream_instead_of_hanging():
    stream = _FakeStream(output_requires_input=False)
    adapter = _adapter(stream, stream_limit_seconds=0.05)
    await adapter.start()

    received = await asyncio.wait_for(_collect(adapter), timeout=2.0)

    await adapter.close()
    assert received == []


async def _collect(adapter: NovaVoiceAdapter) -> list[Any]:
    return [event async for event in adapter.events()]
