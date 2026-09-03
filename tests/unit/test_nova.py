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
    SYSTEM_PROMPT,
    NovaEventTranslator,
    NovaVoiceAdapter,
    build_system_prompt,
)
from app.audio_gateway.port import (
    InterruptionEvent,
    PronunciationEvent,
    SpeechBoundaryEvent,
    TranscriptEvent,
)
from app.config import Settings
from app.models.pronunciation import PRONUNCIATION_TOOL_NAME

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


# I-6 — **한 턴은 한 행이다.** 실물 마이크 계측(2026-09-03,
# `tests/harness/runs/2026-09-03-nova-turn-events.log`)에서 Nova는 한 agent 턴의 텍스트를
# **두 번** 보냈다: 먼저 `SPECULATIVE` 블록들로, 그 다음 **같은 텍스트를 `FINAL`로 재전송**한다
# (len·내용이 정확히 같다). 그 세션에는 `completionEnd`가 **한 번도 오지 않았고**
# `completionStart`는 1회였다 — 즉 턴 경계 신호는 ASSISTANT 오디오의
# `contentEnd(stopReason=END_TURN)` 하나뿐이다.
#
# 이 픽스처가 없으면 같은 검증에 **마이크 세션과 Nova 과금**이 매번 필요하다.
LIVE_TURN_BLOCK_A = "That is good! Can you tell me what you talked about?"
LIVE_TURN_BLOCK_B = "  For example, was it about your work or something else?"
_LIVE_IDS = (
    "live-spec-a",
    "live-audio-a",
    "live-spec-b",
    "live-audio-b",
    "live-fin-a",
    "live-fin-b",
)


def _live_agent_turn() -> list[tuple[str, dict[str, Any]]]:
    spec_a, audio_a, spec_b, audio_b, fin_a, fin_b = _LIVE_IDS
    return [
        _content_start(spec_a, "ASSISTANT", "SPECULATIVE"),
        _text_output(spec_a, "ASSISTANT", LIVE_TURN_BLOCK_A),
        _content_end(spec_a, "PARTIAL_TURN"),
        _content_start(audio_a, "ASSISTANT", None, content_type="AUDIO"),
        _content_end(audio_a, "PARTIAL_TURN"),
        _content_start(spec_b, "ASSISTANT", "SPECULATIVE"),
        _text_output(spec_b, "ASSISTANT", LIVE_TURN_BLOCK_B),
        _content_end(spec_b, "PARTIAL_TURN"),
        _content_start(audio_b, "ASSISTANT", None, content_type="AUDIO"),
        _content_end(audio_b, "END_TURN"),
        # 여기서부터가 재전송이다. 블록마다 행을 만들면 한 턴이 두 행이 된다.
        _content_start(fin_a, "ASSISTANT", "FINAL"),
        _text_output(fin_a, "ASSISTANT", LIVE_TURN_BLOCK_A),
        _content_end(fin_a, "END_TURN"),
        _content_start(fin_b, "ASSISTANT", "FINAL"),
        _text_output(fin_b, "ASSISTANT", LIVE_TURN_BLOCK_B),
        _content_end(fin_b, "PARTIAL_TURN"),
    ]


def test_a_live_agent_turn_becomes_exactly_one_final_transcript():
    finals = [
        event
        for event in _translate_all(_live_agent_turn())
        if isinstance(event, TranscriptEvent) and event.kind == "final"
    ]

    whole_turn = LIVE_TURN_BLOCK_A + LIVE_TURN_BLOCK_B
    assert finals == [TranscriptEvent(kind="final", text=whole_turn, speaker="agent")], (
        "한 턴이 여러 행으로 갈렸다 (I-6) — FINAL 재전송을 블록마다 저장하고 있다"
    )


# I-6 — 재전송된 FINAL은 **버린다**. 위 테스트가 개수를 보므로 이 테스트는 **내용 중복**을 본다:
# 같은 문장이 두 번 저장되면 학습자 전사문이 부풀고 "학습자 65% 발화" 지표가 왜곡된다.
def test_the_resent_final_blocks_do_not_duplicate_the_turn_text():
    texts = [
        event.text
        for event in _translate_all(_live_agent_turn())
        if isinstance(event, TranscriptEvent) and event.kind == "final"
    ]

    assert texts.count(LIVE_TURN_BLOCK_A) == 0, "블록 A가 그대로 한 행으로 남았다"
    assert sum(text.count(LIVE_TURN_BLOCK_A) for text in texts) == 1, "블록 A가 두 번 실렸다"


# I-5 — **제어 페이로드를 전사문으로 만들지 않는다.** barge-in 때 Nova가
# `{ "interrupted" : true }`를 ASSISTANT `textOutput`으로 보낸다(마이크 2회 세션 `182e7d49`의
# seq 9·15가 그 행이다). agent 발화라 분석 대상은 아니지만 전사문에 기계 문자열이 섞이고 agent
# 발화 수를 부풀려 "학습자 65% 발화" 지표를 왜곡한다. 지시문 규칙 6("Never read JSON … out
# loud")과 같은 계열의 누출이다.
# ⚠️ **문자열 상수로 박지 말 것** — 실물은 공백이 들어간 형태로 왔다. JSON 객체인지로 판정한다.
@pytest.mark.parametrize(
    "payload",
    ['{ "interrupted" : true }', '{"interrupted": true}', '{"foo": {"bar": 1}}'],
)
def test_a_json_control_payload_never_becomes_a_transcript(payload: str):
    translated = _translate_all(
        [
            _content_start("ctl", "ASSISTANT", "FINAL"),
            _text_output("ctl", "ASSISTANT", payload),
            _content_end("ctl", "END_TURN"),
        ]
    )

    assert [e for e in translated if isinstance(e, TranscriptEvent)] == [], (
        f"제어 페이로드가 전사문이 됐다 (I-5): {payload!r}"
    )


# I-5 — 반대쪽 못: 중괄호가 들어간 **사람 말**은 그대로 저장된다. 판정을 문자 포함으로 하면
# 정상 발화를 잃는다.
def test_speech_that_merely_mentions_braces_is_still_a_transcript():
    spoken = "I said {like this} in the meeting."
    translated = _translate_all(
        [
            _content_start("spk", "ASSISTANT", "FINAL"),
            _text_output("spk", "ASSISTANT", spoken),
            _content_end("spk", "END_TURN"),
        ]
    )

    assert [e.text for e in translated if isinstance(e, TranscriptEvent)] == [spoken]


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


def _settings(**overrides: Any) -> Settings:
    # ⚠️ `nova_endpointing_sensitivity`를 명시하지 않으면 pydantic이 개발자의
    # `app/backend/.env`를 읽어 테스트가 주변 환경에 의존한다. 실제로 2026-09-01에
    # `.env`를 `LOW`로 튜닝했더니 `turnDetectionConfiguration` 단정이 깨졌다 —
    # 회귀가 아니라 픽스처 결함이었다. 이 값은 **환경변수로 튜닝하도록 설계된 노브**(N13)라서
    # 테스트가 고정해야 한다. `overrides`가 이기도록 dict로 합친다(키워드 중복 방지).
    kwargs: dict[str, Any] = {
        "database_url": "postgresql://unused/unused",
        "aws_region": "us-west-2",
        "voice_adapter": "nova",
        "nova_endpointing_sensitivity": "MEDIUM",
    }
    kwargs.update(overrides)
    return Settings(**kwargs)


def _adapter(stream: _FakeStream, **kwargs: Any) -> NovaVoiceAdapter:
    return NovaVoiceAdapter(_settings(), open_stream=stream.open, **kwargs)


def _adapter_with(stream: _FakeStream, **setting_overrides: Any) -> NovaVoiceAdapter:
    """설정을 바꿔 끼운 어댑터 — 환경변수 노브가 실제로 전달되는지 보는 테스트용."""
    return NovaVoiceAdapter(_settings(**setting_overrides), open_stream=stream.open)


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


async def test_endpointing_sensitivity_setting_reaches_nova():
    """환경변수 노브(N13)가 실제로 `sessionStart`에 실리는지 본다.

    앞 테스트는 값을 `MEDIUM`으로 **고정**해 놓았으므로 "설정이 전달된다"를 증명하지
    못한다 — 기본값과 우연히 같을 수 있기 때문이다. 2026-09-01에 `.env`를 `LOW`로
    튜닝했을 때 이 성질을 지키는 테스트가 없어서 실패를 회귀로 오인했다.
    """
    stream = _FakeStream()
    adapter = _adapter_with(stream, nova_endpointing_sensitivity="LOW")

    await adapter.start()
    await adapter.close()

    assert stream.payloads("sessionStart")[0]["turnDetectionConfiguration"] == {
        "endpointingSensitivity": "LOW"
    }


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


# --- 발음 tool (설계서 §4.2 · 계획 Task 5 · 2026-08-27 스파이크) ---
#
# 아래 리터럴의 근거는 `tests/harness/runs/2026-08-27-P-tooluse-spike/
# P-tooluse-nova-events.json`이다 — 실제 왕복에서 받은 이벤트를 그대로 옮겼다.
# 이 파일의 규약대로 필드 이름을 손으로 다듬지 않았다.

TOOL_CONTENT_ID = "744c42db-d205-4d52-89d9-2e42cae7cc94"
TOOL_USE_ID = "fb0a993c-6798-4574-ade9-077667ec3336"
# 스파이크가 실제로 받은 페이로드 (그대로). `pending`은 우리가 준 enum 밖이었다가
# 정식 값으로 승격됐다 — Nova는 재발화 **전에** tool을 부른다(설계서 F3·F4).
TOOL_PAYLOAD = (
    '{"target_form":"I think I found three very useful videos.",'
    '"spoken_form":"[awaiting user repetition]","outcome":"pending"}'
)
TOOL_TARGET_FORM = "I think I found three very useful videos."
# 스파이크의 agent 응답 2블록 (둘 다 SPECULATIVE로만 왔다).
TOOL_AGENT_TEXT_1 = "Great! Let's work on that sentence. Say this after me: \"I think I found"
TOOL_AGENT_TEXT_2 = " \n\nNow you repeat that sentence for me."


def _tool_content_start() -> tuple[str, dict[str, Any]]:
    """실측 TOOL 블록의 여는 이벤트 — `toolUseOutputConfiguration`까지 그대로 둔다."""
    return (
        "contentStart",
        _envelope(
            extra={
                "contentId": TOOL_CONTENT_ID,
                "role": "TOOL",
                "type": "TOOL",
                "toolUseOutputConfiguration": {"mediaType": "application/json"},
            }
        ),
    )


def _tool_use(
    content: str, *, tool_name: str = "report_pronunciation_coaching"
) -> tuple[str, dict[str, Any]]:
    return (
        "toolUse",
        _envelope(
            extra={
                "contentId": TOOL_CONTENT_ID,
                "role": "TOOL",
                "toolName": tool_name,
                "toolUseId": TOOL_USE_ID,
                "content": content,
            }
        ),
    )


# 4차수는 지시가 없어서 Nova가 발음을 지적하지 않았다. 스파이크는 지시하면 한다는 것을
# 보였다 — 그 지시가 프롬프트에 실제로 있는지 못박는다.
def test_system_prompt_instructs_pronunciation_modeling():
    lowered = SYSTEM_PROMPT.lower()
    assert "pronunc" in lowered
    assert "repeat" in lowered
    # 판정을 DB로 가져오는 수단이 tool 호출뿐이다 — 이름을 프롬프트가 불러야 한다.
    assert PRONUNCIATION_TOOL_NAME in SYSTEM_PROMPT
    # `target_sound`를 요구하지 않으면 Nova가 생략해도 정상 통과하고, 그러면 Task 7의
    # `error_patterns` upsert가 **한 번도 실행되지 않는다**(설계서 §4.2: target_sound가
    # 비면 pattern_key 생성을 건너뛴다). 스키마도 required가 아니라 프롬프트가 유일한 요구다.
    assert "target_sound" in SYSTEM_PROMPT
    assert "name the sound" in lowered


# `toolConfiguration`이 없으면 Nova는 tool을 부를 수 없다 — 스파이크가 실증한 형태다.
async def test_prompt_start_carries_the_pronunciation_tool():
    stream = _FakeStream()
    adapter = _adapter(stream)

    await adapter.start()
    await adapter.close()

    tools = stream.payloads("promptStart")[0]["toolConfiguration"]["tools"]
    assert len(tools) == 1
    spec = tools[0]["toolSpec"]
    assert spec["name"] == PRONUNCIATION_TOOL_NAME
    assert spec["description"]
    # Sonic은 `inputSchema.json`을 **문자열**로 받는다 (스파이크 실측).
    assert isinstance(spec["inputSchema"]["json"], str)
    assert json.loads(spec["inputSchema"]["json"])["type"] == "object"


# 스파이크가 실제로 받은 TOOL 블록이 발음 이벤트 1건으로 번역된다.
# `contentStart(type=TOOL, role=TOOL)`이 전사문을 만들어내지 않는 것도 함께 본다 —
# role이 `_ROLE_TO_SPEAKER`에 없는 값이라 조용히 user로 떨어질 수 있는 자리다.
def test_the_recorded_tool_block_translates_into_one_pronunciation_event():
    translated = _translate_all(
        [_tool_content_start(), _tool_use(TOOL_PAYLOAD), _content_end(TOOL_CONTENT_ID, "TOOL_USE")]
    )

    assert translated == [
        PronunciationEvent(
            target_form=TOOL_TARGET_FORM,
            outcome="pending",
            spoken_form="[awaiting user repetition]",
        )
    ]


# TOOL 블록이 ASSISTANT 텍스트 **앞**에 온다(실측 순서). TOOL 블록이 그 뒤의 텍스트
# 블록을 삼키거나 순서를 뒤집지 않는 것을 본다. 확정 행은 두 청크가 이어붙은 하나여야
# 한다 — **시범 문장이 거기 살아 있는 것이 이 기능의 핵심 산출물이다.**
def test_a_tool_block_does_not_disturb_the_agent_text_promotion():
    translated = _translate_all(
        [
            _content_start(USER_CONTENT_ID, "USER", "FINAL"),
            _text_output(USER_CONTENT_ID, "USER", USER_TRANSCRIPT),
            _content_end(USER_CONTENT_ID, "PARTIAL_TURN"),
            _tool_content_start(),
            _tool_use(TOOL_PAYLOAD),
            _content_end(TOOL_CONTENT_ID, "TOOL_USE"),
            _content_start(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "SPECULATIVE"),
            _text_output(AGENT_TEXT_CONTENT_ID, "ASSISTANT", TOOL_AGENT_TEXT_1),
            _content_end(AGENT_TEXT_CONTENT_ID, "PARTIAL_TURN"),
            _content_start("second-block", "ASSISTANT", "SPECULATIVE"),
            _text_output("second-block", "ASSISTANT", TOOL_AGENT_TEXT_2),
            _content_end("second-block", "PARTIAL_TURN"),
            ("completionEnd", _envelope(extra={"stopReason": "END_TURN"})),
        ]
    )

    assert translated == [
        TranscriptEvent(kind="final", text=USER_TRANSCRIPT, speaker="user"),
        PronunciationEvent(
            target_form=TOOL_TARGET_FORM,
            outcome="pending",
            spoken_form="[awaiting user repetition]",
        ),
        TranscriptEvent(kind="partial", text=TOOL_AGENT_TEXT_1, speaker="agent"),
        TranscriptEvent(kind="partial", text=TOOL_AGENT_TEXT_2, speaker="agent"),
        TranscriptEvent(kind="final", text=TOOL_AGENT_TEXT_1 + TOOL_AGENT_TEXT_2, speaker="agent"),
    ]


# 다른 tool이 생겨도 발음 경로가 오작동하지 않아야 한다.
def test_an_unknown_tool_name_is_ignored():
    translated = _translate_all([_tool_use(TOOL_PAYLOAD, tool_name="something_else")])

    assert translated == []


# PS6 — 깨진 페이로드에 세션이 살아남는다. 뒤따라온 전사문이 흐르는 것이 그 증거다.
@pytest.mark.parametrize(
    "payload",
    [
        "not json at all",
        "",
        '{"target_form":',  # 잘린 JSON
        '{"outcome":"correct"}',  # target_form이 없다 → 시범 없는 시범 기록
        '{"target_form":"   ","outcome":"correct"}',  # 공백만
        '["not", "an", "object"]',
    ],
)
def test_a_broken_tool_payload_does_not_kill_the_stream(payload: str):
    translated = _translate_all(
        [
            _tool_content_start(),
            _tool_use(payload),
            _content_end(TOOL_CONTENT_ID, "TOOL_USE"),
            _content_start(USER_CONTENT_ID, "USER", "FINAL"),
            _text_output(USER_CONTENT_ID, "USER", USER_TRANSCRIPT),
        ]
    )

    assert translated == [TranscriptEvent(kind="final", text=USER_TRANSCRIPT, speaker="user")]


# 판정 페이로드도 그대로 실린다 (재발화를 들은 뒤의 두 번째 호출 — 설계서 §3.2).
def test_a_verdict_payload_carries_its_fields():
    translated = _translate_all(
        [
            _tool_use(
                '{"target_form":"I think.","spoken_form":"I sink.",'
                '"outcome":"incorrect","target_sound":"th_as_s"}'
            )
        ]
    )

    assert translated == [
        PronunciationEvent(
            target_form="I think.",
            outcome="incorrect",
            spoken_form="I sink.",
            target_sound="th_as_s",
        )
    ]


# TOOL content는 발화가 아니다. `role: "TOOL"`이 `_ROLE_TO_SPEAKER`에 없어서 그대로 두면
# `.get(role, "user")` 폴백이 tool JSON을 **학습자 발화로** 저장하고 분석 job까지 등록한다
# (코드 리뷰 실측 재현). 스파이크에서는 TOOL content에 textOutput이 오지 않았지만,
# Task 5가 toolConfiguration을 보내기 시작해 TOOL 블록이 실제 스트림에 등장하게 됐다.
def test_text_on_a_tool_content_is_not_stored_as_learner_speech():
    translated = _translate_all(
        [
            _tool_content_start(),
            # role이 실려 오는 경우와 안 오는 경우 둘 다 — 후자는 contentStart에서 이어 온다.
            ("textOutput", _envelope(extra={"contentId": TOOL_CONTENT_ID, "content": "{}"})),
            _text_output(TOOL_CONTENT_ID, "TOOL", TOOL_PAYLOAD),
        ]
    )

    assert translated == []


# 반대 방향 가드: 모르는 role이 user로 떨어지는 기존 관용은 유지한다. USER/ASSISTANT가
# 이름을 바꿔도 전사문을 잃지 않는 쪽이 낫다는 판단이 이미 `_on_text_output`에 있다.
def test_an_unknown_non_tool_role_still_falls_back_to_the_learner():
    translated = _translate_all(
        [
            _content_start(USER_CONTENT_ID, "LEARNER", "FINAL"),
            _text_output(USER_CONTENT_ID, "LEARNER", USER_TRANSCRIPT),
        ]
    )

    assert translated == [TranscriptEvent(kind="final", text=USER_TRANSCRIPT, speaker="user")]


# 한 completion에 agent 텍스트가 **여러 블록**으로 오면 이어붙여 한 행으로 확정한다.
#
# 실측(`runs/2026-08-27-P-tooluse-spike/`)에서 발음 교정 턴이 정확히 그랬다: completion
# 1개에 SPECULATIVE 텍스트 2블록, FINAL 재전송 없음. 두 번째 블록의 선행 공백과 `\n\n`이
# 이것이 **한 턴의 연속 청크**임을 보여준다(별개 메시지가 아니다). 그런데 예전 구현은
# `_pending_agent_text`를 덮어써서 마지막 블록만 승격했고, 그 결과 **시범 문장
# "Say this after me: …"가 전사문에 한 행도 남지 않았다** — 이 기능에서 학습 가치가 가장
# 높은 문장이고 설계 §5.1 S4가 "큰 글씨로 강조"라고 정한 그 문장이다.
def test_agent_text_chunks_in_one_completion_are_joined_into_one_final_row():
    translated = _translate_all(
        [
            _content_start(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "SPECULATIVE"),
            _text_output(AGENT_TEXT_CONTENT_ID, "ASSISTANT", TOOL_AGENT_TEXT_1),
            _content_end(AGENT_TEXT_CONTENT_ID, "PARTIAL_TURN"),
            _content_start("second-block", "ASSISTANT", "SPECULATIVE"),
            _text_output("second-block", "ASSISTANT", TOOL_AGENT_TEXT_2),
            _content_end("second-block", "PARTIAL_TURN"),
            ("completionEnd", _envelope(extra={"stopReason": "END_TURN"})),
        ]
    )

    finals = [e for e in translated if isinstance(e, TranscriptEvent) and e.kind == "final"]
    assert len(finals) == 1, "한 턴은 한 행이다 — 청크마다 행이 생기면 전사문이 부풀어 오른다"
    # 시범 문장이 살아 있어야 한다. 이것이 이 수정의 목적이다.
    assert "Say this after me" in finals[0].text
    assert "Now you repeat that sentence for me." in finals[0].text
    assert finals[0].speaker == "agent"


# 각 청크는 화면용 partial로 그대로 흘러야 한다 — 이어붙이기가 실시간 표시를 바꾸지 않는다.
def test_joining_does_not_change_the_partial_frames():
    translated = _translate_all(
        [
            _content_start(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "SPECULATIVE"),
            _text_output(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "First chunk."),
            _content_start("second-block", "ASSISTANT", "SPECULATIVE"),
            _text_output("second-block", "ASSISTANT", " Second chunk."),
        ]
    )

    assert translated == [
        TranscriptEvent(kind="partial", text="First chunk.", speaker="agent"),
        TranscriptEvent(kind="partial", text=" Second chunk.", speaker="agent"),
    ]


# FINAL이 오면 그때까지 쌓인 청크를 버린다 — FINAL이 그 턴의 정본이다. 안 버리면
# 같은 내용이 두 번(청크 + FINAL) 이어붙여진다.
def test_a_real_final_discards_the_accumulated_chunks():
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


# 다음 턴이 앞 턴의 청크를 물고 가지 않는다 — completionEnd가 버퍼를 비워야 한다.
def test_chunks_do_not_leak_across_turns():
    translated = _translate_all(
        [
            _content_start(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "SPECULATIVE"),
            _text_output(AGENT_TEXT_CONTENT_ID, "ASSISTANT", "Turn one."),
            ("completionEnd", _envelope(extra={"stopReason": "END_TURN"})),
            _content_start("turn-two", "ASSISTANT", "SPECULATIVE"),
            _text_output("turn-two", "ASSISTANT", "Turn two."),
            ("completionEnd", _envelope(extra={"stopReason": "END_TURN"})),
        ]
    )

    finals = [e for e in translated if isinstance(e, TranscriptEvent) and e.kind == "final"]
    assert [e.text for e in finals] == ["Turn one.", "Turn two."]


# --- G-1·G-3: 개입 조건 좁히기 + 학습자의 기존 소리 주입 ---


# G-1 (캡틴 결정 B-2) — 일반 세션에서 발음 개입은 무조건이 아니다. 우리 감지기(한글 전사문)는
# 전사가 온 **뒤에** 서버가 보는 것이라 Nova가 볼 수 없으므로, 조건을 **Nova가 스스로 적용할 수
# 있는 문장**으로 좁힌다(2026-08-30 캡틴 선택). 좁히기 전 문구가 남아 있으면 코드가 결정과
# 어긋난 상태 그대로다.
def test_system_prompt_narrows_pronunciation_to_hard_to_understand_speech():
    lowered = SYSTEM_PROMPT.lower()
    assert "hard to understand" in lowered
    assert "grammar first" in lowered
    assert "when a sound is clearly off" not in lowered, (
        "무조건 개입 문구가 남아 있다 — B-2 결정(문법 우선)과 어긋난다"
    )


# I-7 (캡틴 관측 2026-09-03) — 튜터가 학습자를 기다리지 않았다. 마이크 2회 계측에서 한 턴에
# 질문 + 예시 질문이 함께 실렸고, 노브(`NOVA_ENDPOINTING_SENSITIVITY`)는 **이미 `LOW`**로 끝까지
# 내려가 있다(`.env`). 남은 레버가 지시문이므로 **대기 지시가 실제로 있는지** 못박는다.
# ⚠️ LLM 준수는 확률적이다 — 이 테스트는 "지시가 있다"만 보증하고 "지켜진다"는 마이크 검증이 본다.
def test_system_prompt_tells_the_tutor_to_wait_through_a_pause():
    # ⚠️ **공백을 정규화해서 본다.** 지시문은 소스 줄 길이 때문에 문장 중간에서 줄바꿈되므로,
    # 원문 그대로 부분문자열을 찾으면 **문구가 있는데도 red가 된다**(실제로 한 번 걸렸다).
    # 단정은 문구에 걸어야 하고 줄바꿈 위치에 걸려선 안 된다.
    lowered = " ".join(SYSTEM_PROMPT.lower().split())
    assert "then stop and wait" in lowered, "대기 지시가 없다 — 침묵을 다음 질문으로 메운다 (I-7)"
    # 침묵을 **다른 질문·예시로 메우는 것**을 금지하는 문구가 핵심이다. "질문 하나" 규칙만으로는
    # 관측된 거동(질문 + 예시 질문을 한 턴에)을 막지 못했다.
    assert "do not fill" in lowered
    assert "ask one question at a time, then let the learner speak" not in lowered, (
        "좁히기 전 문구가 남아 있다 — 대기 지시가 실효를 보지 못한다"
    )
    # 2차 (2026-09-03 검증 세션): 대기 규칙만으로는 **새 질문 + 교정을 한 턴에 묶는 것**을
    # 막지 못했다(284자 한 턴 실측). 교정은 규칙 4·5가 시키는 일이라 모델이 정당하게 붙인다 —
    # 그래서 그 조합을 명시적으로 금지한다. 규칙 10이 규칙 4의 상한을 다시 못박은 것과 같은 방식.
    assert "never pair a correction with a new question" in lowered


# G-3 (캡틴 결정 B-4) — 기록이 0건이면 블록을 아예 넣지 않는다. dev DB의 현재 상태가 그것이고,
# 빈 목록을 위한 빈 제목만 남기면 Nova가 "목록이 비었다"를 지시로 오해할 여지가 생긴다.
def test_build_system_prompt_without_known_sounds_is_exactly_the_base_prompt():
    assert build_system_prompt([]) == SYSTEM_PROMPT


# 재사용 규약(§5.6)을 발음 경로에서도 동작시키는 것이 B-4의 목적이다 — 키를 보여주는 것만으로는
# 부족하고 **그 키를 다시 쓰라는 지시**가 함께 있어야 새 키가 계속 생긴다.
def test_build_system_prompt_lists_past_sounds_and_asks_to_reuse_them():
    prompt = build_system_prompt(["th_as_s", "f_as_p"])

    assert prompt.startswith(SYSTEM_PROMPT)
    assert "th_as_s" in prompt
    assert "f_as_p" in prompt
    assert "reuse" in prompt.lower()


# 조립한 문구가 **실제 전송 페이로드**에 실리는지까지 본다 — 조립만 맞고 배선이 빠지면
# 지시문은 코드에만 있고 Nova는 못 본다.
#
# `build_system_prompt(...)`의 결과를 넣지 않고 **base와 확실히 다른 리터럴**을 넣는다:
# 조립기가 base를 그대로 돌려주는 동안에는 두 값이 같아서, 어댑터가 인자를 무시해도
# 이 단정이 통과해 버린다(관측됨).
async def test_start_sends_the_assembled_instructions_when_given():
    stream = _FakeStream()
    instructions = "SENTINEL INSTRUCTIONS — not the base prompt"
    adapter = _adapter(stream, instructions=instructions)

    await adapter.start()
    await adapter.close()

    assert stream.payloads("textInput")[0]["content"] == instructions


# 인자를 주지 않으면 기존 거동 그대로다(스텁·기존 차수 재현이 흔들리지 않는다).
async def test_start_sends_the_base_prompt_when_no_instructions_are_given():
    stream = _FakeStream()
    adapter = _adapter(stream)

    await adapter.start()
    await adapter.close()

    assert stream.payloads("textInput")[0]["content"] == SYSTEM_PROMPT
