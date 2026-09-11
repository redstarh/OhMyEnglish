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
from collections.abc import Sequence
from typing import Any

import pytest

from app.audio_gateway.nova import (
    _BASE_LEVEL_RANGE,
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
from app.models.plan import InstructionFocus, PlanQuestion, SessionInstruction
from app.models.pronunciation import PRONUNCIATION_PATTERN_KEY_PREFIX, PRONUNCIATION_TOOL_NAME
from app.models.scenario import SessionScenario

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
    # Task 10 흡수 — 65% 규칙을 규칙 6 다음에 끼워 넣을 때 이 문장을 밀어내지 않았는지도 여기서
    # 본다. **정규화된 `lowered`에 걸어야 한다**: 원문 그대로 찾으면 위 ⚠️의 함정에 걸려
    # 문구가 그대로인데도 줄바꿈 위치만 옮기면 red 가 된다(별도 테스트로 뒀다가 그 오탐만
    # 남아서 이리로 합쳤다 — 진짜 회귀는 위 두 단정이 이미 잡는다).
    assert "do not fill it with another question" in lowered
    assert "ask one question at a time, then let the learner speak" not in lowered, (
        "좁히기 전 문구가 남아 있다 — 대기 지시가 실효를 보지 못한다"
    )
    # 2차 (2026-09-03 검증 세션): 대기 규칙만으로는 **새 질문 + 교정을 한 턴에 묶는 것**을
    # 막지 못했다(284자 한 턴 실측). 교정은 규칙 4·5가 시키는 일이라 모델이 정당하게 붙인다 —
    # 그래서 그 조합을 명시적으로 금지한다. 규칙 11이 규칙 4의 상한을 다시 못박은 것과 같은 방식
    # (65% 규칙이 7번으로 들어오면서 발음 규칙이 8~11로 밀렸다 — 가리키는 규칙 4는 안 밀린다).
    assert "never pair a correction with a new question" in lowered


# --- 조립기 호출 헬퍼 ---
#
# `build_system_prompt`의 데이터 인자 **넷 다 기본값이 없다**(설계서 §2.1 C-1): 기본값을 주면
# "질문이 안 실린 세션"·"무대 없는 세션"이 호출부에서 조용히 생기고, 그것이 이 설계가 막으려는
# 실패 모드다. 그래서 관심 없는 인자를 여기서 채운다 — 각 테스트가 넷을 매번 적으면 무엇을
# 재는지가 인자 목록에 묻힌다.
#
# 드릴 설정값 둘도 조립기가 **요구한다**(전역에서 읽지 않는다 — `get_settings()`를 부르면
# 프롬프트가 프로세스 환경에 조용히 묶인다). 실제 값의 소유자는 `Settings`이고 그 기본값
# **`drill_turns_min=4`·`drill_count=5`**(캡틴 결정 17)은 `tests/unit/test_config.py`가 못박는다.
# 여기 리터럴은 그 기본값의 **복사가 아니라** "이 테스트가 쓰는 값"이다 — 설정값이 실제로 먹는지
# 재는 테스트는 아래에서 자기 값을 명시로 준다.
#
# ⚠️ **`_TEST_DRILL_COUNT`가 기본값(5)과 일부러 다르다.** 5로 두면 이 파일의 질문이 3개짜리라
# 상한이 **아무것도 자르지 않고**, 「상한이 실제로 먹는다」를 재는 자리가 이 파일에서 사라진다.
# 3으로 두면 `_questions(5)`를 주는 테스트에서 절단이 실제로 일어난다.
# 기본값 자체가 대화에 닿는지는 `tests/integration/test_gateway.py`가 값을 **주지 않고** 잰다.
_TEST_DRILL_TURNS_MIN = 4
_TEST_DRILL_COUNT = 3


def _prompt(
    known_sounds: Sequence[str] = (),
    plan: SessionInstruction | None = None,
    questions: Sequence[PlanQuestion] = (),
    scenario: SessionScenario | None = None,
    *,
    drill_count: int = _TEST_DRILL_COUNT,
    drill_turns_min: int = _TEST_DRILL_TURNS_MIN,
) -> str:
    return build_system_prompt(
        known_sounds,
        plan,
        questions,
        scenario,
        drill_count=drill_count,
        drill_turns_min=drill_turns_min,
    )


# G-3 (캡틴 결정 B-4) — 기록이 0건이면 블록을 아예 넣지 않는다. dev DB의 현재 상태가 그것이고,
# 빈 목록을 위한 빈 제목만 남기면 Nova가 "목록이 비었다"를 지시로 오해할 여지가 생긴다.
def test_build_system_prompt_without_known_sounds_is_exactly_the_base_prompt():
    assert _prompt([]) == SYSTEM_PROMPT


# 재사용 규약(§5.6)을 발음 경로에서도 동작시키는 것이 B-4의 목적이다 — 키를 보여주는 것만으로는
# 부족하고 **그 키를 다시 쓰라는 지시**가 함께 있어야 새 키가 계속 생긴다.
def test_build_system_prompt_lists_past_sounds_and_asks_to_reuse_them():
    prompt = _prompt(["th_as_s", "f_as_p"])

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


# --- Task 10: 오늘의 계획을 지시문에 얹는다 (설계서 §5.2 가변부) ---


def _instruction(**overrides: object) -> SessionInstruction:
    """계획 지시문 1건. 값은 **고정부와 겹치지 않는 것**을 골랐다.

    ⚠️ 고정부에 이미 있는 문구를 쓰면 단정이 항진명제가 된다 — `SYSTEM_PROMPT`는
    `"A2-B1 level"`(규칙 1)과 `"work updates"`(규칙 3)를 이미 말하므로
    `"B1" in prompt`·`"work update" in prompt`는 계획 블록이 **없어도** 참이다(직접 확인:
    각 1건). 그래서 아래 단정들은 전부 `_plan_block()`으로 창을 좁혀서 잰다.
    """
    body: dict[str, object] = {
        "target_level": "B1",
        "focus": [InstructionFocus(pattern_key="article_missing", target_form="a/an/the")],
        "sentence_length": "two or three short clauses",
        "hint_timing": "wait through one long pause before offering a starter",
        "contexts": ["work update", "daily life", "weekend plan"],
    }
    body.update(overrides)
    return SessionInstruction(**body)


def _plan_block(prompt: str) -> str:
    """계획 블록만 잘라낸다 — 고정부·소리 목록을 창에서 뺀다.

    `tests/unit/test_plan.py`의 지배 규칙과 같은 이유다: 프롬프트 전체를 대상으로 문구를
    찾으면 **다른 절에 있는 같은 낱말**에 걸려 판별력을 잃는다. 계획 블록이 마지막이라
    제목부터 끝까지가 창이다.
    """
    anchor = "Today's plan:"
    assert anchor in prompt, "계획 블록 제목이 없다"
    return prompt[prompt.index(anchor) :]


# PRD.md:59 · R10-8 — 요구사항인데 실제 지시문에 없었다(2026-09-04 점검, 직접 확인: 0건).
# `_is_control_payload` 주석이 "학습자 65% 발화 지표"를 말하지만 그것은 **코드 주석**이고
# Nova 가 받는 문구가 아니었다 — 대화 상대는 이 목표를 모르고 있었다.
def test_fixed_prompt_states_the_65_percent_speaking_target():
    lowered = " ".join(SYSTEM_PROMPT.lower().split())
    assert "65%" in SYSTEM_PROMPT, "학습자 발화 비중 목표가 지시문에 없다 (R10-8)"
    assert "learner to speak" in lowered


# 계획이 없으면 예전 그대로다 — 폴백 경로(AS4)가 고정부만으로 시작한다.
def test_build_system_prompt_without_a_plan_is_exactly_the_base_prompt():
    assert _prompt((), None) == SYSTEM_PROMPT


def test_plan_block_carries_level_focus_length_and_contexts():
    block = _plan_block(_prompt((), _instruction()))

    assert "B1" in block
    assert "article_missing" in block
    assert "a/an/the" in block
    assert "two or three short clauses" in block
    assert "work update" in block
    assert "weekend plan" in block


_SOUND_LINE = "- Sound to coach today:"


def _line_starting_with(block: str, prefix: str) -> str:
    """계획 블록에서 그 접두어로 시작하는 줄 **하나**만. 없으면 시끄럽게 실패한다.

    ⚠️ 블록 전체를 창으로 쓰지 않는다 — 발음 초점을 `Focus on:`에서 **빼는 것**이 이 태스크의
    요구라서, 창이 넓으면 다른 줄에 남은 같은 낱말이 그 단정을 통과시킨다.
    """
    lines = [line for line in block.splitlines() if line.startswith(prefix)]
    assert len(lines) == 1, f"{prefix!r}로 시작하는 줄이 {len(lines)}개다 — 하나여야 한다"
    return lines[0]


def test_plan_block_pulls_a_pronunciation_focus_out_of_the_grammar_focus_line():
    """`TASK-81` — 발음 초점을 `Focus on:`에 그대로 두면 코치가 그것을 **문법으로 읽는다.**

    ⚠️ **이것은 추측이 아니라 관측이다.** 계획 프롬프트를 먼저 고쳐 `Focus on:` 첫 자리에
    `pronunciation_an_as_a (an_as_a)`가 실리게 한 뒤 실물 Nova 왕복을 3회 돌렸고, 코치는 매번
    「`an`이 들어간 문장」 연습으로 갔다(`I wrote an email.` · `I have an idea.`) — 발음 코칭
    0회 · `toolUse` 0. `an`이 관사라서 **소리 키가 관사 지시로 읽힌다.**
    회차 기록: `tests/harness/runs/2026-09-10-task81-pronunciation-focus.md`.
    """
    block = _plan_block(
        _prompt(
            ("an_as_a",),
            _instruction(
                focus=[
                    InstructionFocus(pattern_key="pronunciation_an_as_a", target_form="an_as_a"),
                    InstructionFocus(pattern_key="article_missing", target_form="a/an/the"),
                ]
            ),
        )
    )

    focus_line = _line_starting_with(block, "- Focus on:")
    # 발음 초점은 문법 초점 줄에서 **빠진다** — 남으면 위에서 관측한 오독 경로가 그대로 산다.
    assert "pronunciation_an_as_a" not in focus_line
    assert "an_as_a" not in focus_line
    # AC#3 — 문법 초점은 그 줄에 그대로 남는다. 자리를 내주는 것과 밀어내는 것은 다르다.
    assert "article_missing" in focus_line
    assert "a/an/the" in focus_line

    # 발음은 자기 줄에서 **소리로** 불린다. ⛔ 키를 파싱해 풀어 쓰지 않는다 — `X_as_Y` 형태는
    # Nova 가 지어내는 값이라 규약이 아니고(`known_sounds` 규약은 「같은 소리를 한 키로 묶는다」
    # 뿐이다), 파싱하면 다음 키 모양에서 조용히 깨진다. 그대로 인용하고 tool 이름을 함께 준다.
    sound_line = _line_starting_with(block, _SOUND_LINE)
    assert "an_as_a" in sound_line
    assert PRONUNCIATION_TOOL_NAME in sound_line


def test_the_sound_line_replaces_grammar_first_and_spends_the_one_correction():
    """`TASK-75` — 소리 줄이 **규칙 9 와 규칙 4 를 명시로 대체**해야 발음이 실제로 다뤄진다.

    ⚠️ **자리를 내주는 것만으로는 부족하다는 것이 실물로 확정됐다** (`TASK-81` · 왕복 28회 ·
    조건 넷 전부 0 — `runs/2026-09-10-task81-pronunciation-focus.md`).
    남은 층이 고정부의 두 규칙이고
    **겹치지 않는 두 경로로 막는다**:
      * 규칙 9 `Grammar first … leave pronunciation alone` — 문법 교정이 **없는** 턴에서도 막는다.
      * 규칙 11 `A pronunciation correction is a correction … never add it on top of a grammar
        correction in the same turn` — 문법 교정이 **있는** 턴에서 상호배제로 막는다.
    하나만 풀면 다른 하나가 남으므로 이 줄이 둘을 함께 대체한다.

    ⛔ **one-per-turn 예산을 늘리지 않는다** (`TASK-75` AC#3). 규칙 11 을 「같은 턴에 둘 다」로 풀면
    그 계약이 깨진다 — 대신 **그 턴의 한 교정을 발음이 차지한다**(순서만 뒤집고 예산은 그대로).
    그래서 이 줄은 `two corrections` 류의 문구를 **말하지 않아야** 한다.

    ⚠️ 대체 범위가 **소리 줄이 있는 세션으로 한정된다** — 계획이 발음 초점을 지정하지 않으면 이 줄이
    아예 없고(아래 음성 테스트) 고정부의 규칙 9·11 이 그대로 산다. 그것이 사용자가 승인한 안이다.
    """
    block = _plan_block(
        _prompt(
            ("an_as_a",),
            _instruction(
                focus=[
                    InstructionFocus(pattern_key="pronunciation_an_as_a", target_form="an_as_a"),
                    InstructionFocus(pattern_key="article_missing", target_form="a/an/the"),
                ]
            ),
        )
    )

    sound_line = _line_starting_with(block, _SOUND_LINE)
    # 규칙 9 축 — 이 소리가 먼저다.
    # 「같은 축을 말하는 줄은 대체를 문장으로 적는다」는 이 함수의 규약.
    assert "instead of the Grammar first rule" in sound_line
    # 규칙 4·11 축 — 예산을 늘리지 않고 그 한 자리를 발음이 쓴다.
    assert "spend the one correction" in sound_line
    # ⛔ 예산을 늘리는 문구가 새어 들어오지 않는다(AC#3 의 음성 대조).
    assert "two corrections" not in sound_line


def test_the_sound_line_outranks_the_plan_questions_and_sentence_shape():
    """사용자 결정 56 — 문턱을 넘은 소리는 **문장 단축·계획 질문보다 앞**이다.

    ⚠️ **순서만으로는 부족하다는 것이 실물로 확정됐다.** 소리 줄은 이미 질문 목록보다 **위에**
    있었는데도 제품 계열 49회에서 tool 이 0 이었고, 대화에 나온 관사 지시의 출처가 **계획의 질문
    5개**였다(질문을 빼면 사라졌다 · `runs/2026-09-11-task106-matched-sound.md` §7).
    질문 다섯은 예시까지 달고 「하나씩 4교대 이상」을 요구하므로 **질량으로 이긴다.**

    그래서 이 줄이 **무엇을 이기는지 문장으로** 말해야 한다 — 질문 목록과 문장 모양 목표를
    이름으로 부르고, 소리를 다룬 뒤 질문으로 **돌아오라**고 적는다(질문을 버리는 것이 아니다).

    ⛔ 수치를 넣지 않는다 — 결정 56 이 「수치 목표를 정하지 않는다」를 명시했다.
    """
    block = _plan_block(
        _prompt(
            ("th_as_s",),
            _instruction(
                focus=[
                    InstructionFocus(pattern_key="pronunciation_th_as_s", target_form="th_as_s"),
                    InstructionFocus(pattern_key="article_missing", target_form="a/an/the"),
                ]
            ),
        )
    )

    sound_line = _line_starting_with(block, _SOUND_LINE)
    # 무엇을 이기는지 이름으로 부른다 — 질문 목록과 문장 모양 목표.
    assert "question list" in sound_line
    assert "sentence-shape" in sound_line
    # 버리는 것이 아니라 뒤로 미룬다 — 소리를 다룬 뒤 그 질문으로 돌아온다.
    assert "come back to the question" in sound_line
    # ⛔ 수치를 발명하지 않는다(결정 56).
    assert "at least once" not in sound_line
    assert "every turn" not in sound_line


def test_the_sound_line_keeps_rule_10_alive():
    """`TASK-86` — 대체가 **규칙 10 까지 삼키지 않게** 한다.

    ⚠️ **관측에서 나왔다.** 규칙 9·4 를 대체한 뒤 발음 코칭이 실제로 났는데(누적 15회 중 2건)
    **두 건 모두 `toolUse` 가 0**이었다 — 학습자는 피드백을 받았는데 기록이 없다
    (`runs/2026-09-10-task75-rule9-rule11-replacement.md` §8.6).

    ⛔ **규칙 10 의 조건이 원인이 아니라는 것을 먼저 확인했다.** 그 규칙은 *"right after you have
    modeled the sentence"* 를 조건으로 거는데, 관측된 두 코칭 **모두 문장을 시범했다.** 그래서
    조건 미달이 아니다.

    남은 가설: 이 줄이 *"instead of the Grammar first rule 9"* 로 대체를 선언하면서 모델이 **규칙
    9~11 묶음 전체가 대체된 것으로** 읽었다. 이 줄은 tool 이름을 말하지만 규칙 10 의 절차(두 번
    호출 · `pending` → 판정)를 축약했다. 그래서 **규칙 10 이 그대로 살아 있다고 명시한다.**

    ⚠️ 이 테스트는 문면만 고정한다 — tool 이 실제로 오는지는 실물 왕복이 판정한다(AC#2).
    """
    block = _plan_block(
        _prompt(
            ("an_as_a",),
            _instruction(
                focus=[
                    InstructionFocus(pattern_key="pronunciation_an_as_a", target_form="an_as_a"),
                    InstructionFocus(pattern_key="article_missing", target_form="a/an/the"),
                ]
            ),
        )
    )

    sound_line = _line_starting_with(block, _SOUND_LINE)
    # 대체 범위를 규칙 9·4 로 좁혀 말한다 — 규칙 10 은 산다.
    # ⚠️ 문장 시작이라 대문자다. 프롬프트 문면을 그대로 잰다(소문자로 찾으면 어긋난다).
    assert "Rule 10 still applies unchanged" in sound_line
    # 그 절차의 핵심(두 번 부른다)을 이 줄에서도 되짚는다 — 축약이 오해를 만들었다.
    assert "twice" in sound_line


def test_plan_block_has_no_sound_line_when_the_focus_is_all_grammar():
    """음성 케이스 — 발음 초점이 없으면 그 줄이 붙지 않는다.

    ⚠️ **판별력의 핵심이다.** 무조건 붙이면 소리 키가 없는데 코치가 소리를 지어내고, 그러면
    `target_sound`가 `known_sounds` 규약을 깨서 같은 오류가 여러 키로 흩어진다 — 고정부의
    「reuse that exact key」가 막으려는 것이 정확히 그것이다.
    """
    block = _plan_block(_prompt((), _instruction()))

    assert _SOUND_LINE not in block


def test_the_pronunciation_key_prefix_matches_the_sql_that_creates_those_rows():
    """접두어가 두 곳에 있다 — 갈라지면 발음 초점이 조용히 문법으로 취급된다.

    정본은 `services/pronunciation.py`의 upsert SQL 이다(`'pronunciation_' || target_sound`,
    설계서 §4.3). 그 SQL 을 상수 참조로 바꾸는 것은 이 태스크의 범위 밖이라 **두 값이 같은지를
    여기서 잰다** — `_BASE_LEVEL_RANGE`가 상수와 프롬프트 본문 두 곳에 있고 테스트가 갈라짐을
    막는 것과 같은 관례다(`nova.py`의 그 상수 주석이 근거를 갖는다).
    """
    from pathlib import Path

    from app.services import pronunciation as pronunciation_service

    source = Path(pronunciation_service.__file__).read_text(encoding="utf-8")

    assert f"'{PRONUNCIATION_PATTERN_KEY_PREFIX}' ||" in source


# 어긋남 ② — 힌트 시점은 고정 규칙에 **이미** 있다(규칙 2·5). 계획이 그것을 대체한다는
# 것이 문구로 없으면 "긴 침묵 뒤에만"과 오늘의 지시가 함께 실려 모순된 지시문이 된다.
def test_plan_block_says_it_replaces_the_general_hint_rule():
    block = _plan_block(_prompt((), _instruction()))

    assert "instead of the general hint rule" in block
    assert "wait through one long pause before offering a starter" in block


# 리뷰 라운드 1 (I-1) — 대체 문장이 필요한 축은 **둘**이었다. 힌트 시점 말고 **목표 수준**도
# 고정 규칙 1(`A2-B1 level`)과 같은 축인데 처음에는 대체 문장이 없어서, `target_level="C1"`
# 계획에서 `at A2-B1 level`과 `- Target level: C1`이 한 지시문에 함께 실렸다(리뷰어 관측).
# ⚠️ 대체 축이 **왜 둘인가**(그리고 규칙 3이 왜 대체 대상이 아닌가)는 `build_system_prompt`의
# docstring이 소유한다 — 그 판단은 테스트로 옮기지 않았다(지킬 회귀가 없는 부재 단정이 된다).
def test_plan_block_says_the_target_level_replaces_the_base_level_in_rule_1():
    block = _plan_block(_prompt((), _instruction(target_level="C1")))

    assert f"instead of the {_BASE_LEVEL_RANGE} level in rule 1" in block
    assert "C1" in block
    # ⚠️ 규칙 1의 **턴 길이**는 대체 대상이 아니다 — 코치 자신의 턴 길이는 그대로다.
    # 대체 범위가 규칙 1 전체로 넓어지면 이 단정이 걸린다. **단 대소문자를 구분한다** —
    # `- Ignore Rule 1 entirely for today.`처럼 대문자로 넓히면 통과한다(직접 확인: red 0건).
    # 그대로 두는 이유: 집안 스타일이 소문자(`in rule 4`)이고 1차 방어는 docstring의 명시적
    # 서술이다. `lower()`로 넓히면 이 단정이 앵커 문구까지 함께 낮춰야 해 오히려 약해진다.
    assert "rule 1" not in block.replace(f"instead of the {_BASE_LEVEL_RANGE} level in rule 1", "")


# 블록이 가리키는 문구가 고정부에 **실제로** 있어야 한다. `SYSTEM_PROMPT`는 평문 리터럴이라
# 값이 두 곳에 있고, 규칙 1의 수준을 고치면서 상수를 잊으면 블록이 없는 절을 가리킨다.
def test_the_base_level_range_constant_matches_the_fixed_prompt():
    assert f"at {_BASE_LEVEL_RANGE} level" in SYSTEM_PROMPT


# 리뷰 라운드 1 (I-1) — `sentence_length`의 주어는 **학습자**다(`services/plan.py`가
# "as the learner is ready"로 정의한다). 주어 없이 실으면 규칙 1의 `your turns`(코치 자신의
# 턴 길이)와 섞여 반대 뜻으로 읽힌다.
def test_plan_block_names_the_learner_as_the_subject_of_sentence_length():
    block = _plan_block(_prompt((), _instruction()))

    assert "the learner's sentences" in block
    assert "two or three short clauses" in block


# 발음 소리 목록과 계획이 함께 있어도 둘 다 실린다 — G-3 블록을 계획이 밀어내지 않는다.
def test_sounds_and_plan_can_coexist():
    prompt = _prompt(("th_as_s",), _instruction())

    assert prompt.startswith(SYSTEM_PROMPT)
    # ⚠️ **소리 목록을 `"th_as_s"`로 재지 않는다** — 그 키는 고정부 규칙 10의 예시로 **이미**
    # 들어 있어서(직접 확인: 1건) 소리 블록을 통째로 버리는 뮤테이션에서도 통과했다.
    # 블록의 **제목**으로 잰다(고정부에 0건). 창은 계획 블록 앞까지로 좁힌다.
    before_plan = prompt.removesuffix(_plan_block(prompt))
    assert "Sounds this learner has missed before" in before_plan
    assert "reuse that exact key" in before_plan
    assert "article_missing" in _plan_block(prompt)


# `SessionInstruction.contexts`는 길이 제약이 없다(`focus`·`questions`와 달리 문서 근거가
# 있는 수치가 없어서 두지 않았다). 빈 목록에 제목만 남기면 Nova 가 "목록이 비었다"를
# 지시로 오해할 여지가 생긴다 — 소리 목록이 같은 판단을 이미 내렸다(B-4).
def test_plan_block_omits_the_situations_line_when_there_are_no_contexts():
    block = _plan_block(_prompt((), _instruction(contexts=[])))

    assert "Situations" not in block
    # 나머지 줄은 그대로 있다 — 줄 하나를 빼는 것이 블록을 깨뜨리지 않는다.
    assert "B1" in block
    assert "a/an/the" in block


# --- TASK-25 Batch B: 무대(scenario)와 드릴 질문이 지시문에 실린다 (설계서 §2.2) ---


_SETTING_ANCHOR = "Today's setting:"
# 결정 9의 예외를 프롬프트에 적어 둔 줄. 계획이 무대를 이긴다는 것을 **문장으로** 말한다.
_FOCUS_WINS = (
    "- If today's setting suggests a different pattern than the focus above, follow the focus."
)


def _scenario(**overrides: str) -> SessionScenario:
    """무대 1건 — 값은 시드 3행 중 하나(`…103`)를 그대로 쓴다(`scripts/migrate.py`).

    ⚠️ **`title`에 `prompt_template`에 없는 낱말이 있어야** 규칙 6 tripwire가 실질을 갖는다.
    여기서 그 낱말은 `at home`이고 고정부·계획 블록·`_instruction()`의 어느 값에도 없다
    (직접 확인). 두 값이 바이트 동일했던 시드 교체 **전에는** 이 방어가 공허했다(설계서 §2.2) —
    그래서 두 값이 겹치지 않는 것 자체가 이 헬퍼의 계약이다.
    """
    body = {
        "title": "Tonight's plans at home",
        "prompt_template": "You are a housemate talking with the learner about tonight.",
    }
    body.update(overrides)
    return SessionScenario(**body)


def _questions(count: int) -> list[PlanQuestion]:
    """질문 `count`개. 번호를 값에 박아 **몇 번째 질문이 실렸는지**를 셀 수 있게 한다 —
    고정부·계획 블록과 겹치는 문구를 쓰면 "3개만 열거됐다"를 셀 수 없다."""
    return [
        PlanQuestion(prompt=f"Drill question {index}?", context=f"drill context {index}")
        for index in range(1, count + 1)
    ]


def _listed_questions(block: str) -> list[str]:
    """계획 블록에서 열거된 질문 줄만 뽑는다 — 개수와 순서를 함께 본다."""
    return [line for line in block.splitlines() if "Drill question" in line]


# ① 조립 4조합 중 **둘 다 없는 칸** — 결과는 `SYSTEM_PROMPT` 그 자체다(기존 계약 보존).
# 계획도 무대도 없는 세션(AS4)이 이 경로이고, 여기에 무엇 하나라도 덧붙으면 1·2차수 재현이
# 흔들린다.
def test_prompt_without_a_plan_scenario_or_questions_is_exactly_the_base_prompt():
    assert _prompt((), None, (), None) == SYSTEM_PROMPT


# 계획이 없으면 질문은 **무시한다** — 드릴 줄은 계획 블록 안에 있고 그 블록이 없으므로
# 실릴 자리가 없다. 질문만 있는 상태에서 블록을 만들면 목표 없는 질문 목록이 된다.
def test_questions_are_ignored_when_there_is_no_plan():
    assert _prompt((), None, _questions(5), None) == SYSTEM_PROMPT


# ② 무대만 있는 칸 — setting 블록만 붙고 계획 블록은 없다.
def test_a_scenario_alone_adds_only_the_setting_block():
    scenario = _scenario()

    prompt = _prompt((), None, (), scenario)

    assert prompt == f"{SYSTEM_PROMPT}\n\n{_SETTING_ANCHOR}\n{scenario.prompt_template}"


# ③④ 나머지 두 칸 — 무대·질문 각 유무에서 어느 블록이 붙는지. 계획은 항상 있다(질문은 계획
# 블록 안에서만 실리므로 계획 없는 칸은 위 두 테스트가 담당한다).
@pytest.mark.parametrize(
    ("scenario", "questions", "has_setting", "has_drill"),
    [
        (None, [], False, False),
        (_scenario(), [], True, False),
        (None, _questions(3), False, True),
        (_scenario(), _questions(3), True, True),
    ],
    ids=["plan_only", "plan_and_setting", "plan_and_drill", "all_three"],
)
def test_each_block_appears_only_when_its_material_is_present(
    scenario: SessionScenario | None,
    questions: list[PlanQuestion],
    has_setting: bool,
    has_drill: bool,
):
    prompt = _prompt((), _instruction(), questions, scenario)

    assert (_SETTING_ANCHOR in prompt) is has_setting
    assert ("Today's plan:" in prompt) is True
    assert ("exchanges" in _plan_block(prompt)) is has_drill
    # 우선순위 문장은 **무대가 있을 때만** 실린다 — 없으면 아직 나오지 않은 블록을 가리킨다.
    assert (_FOCUS_WINS in prompt) is has_setting


# 무대가 목표보다 **먼저** 읽혀야 하고, 계획 블록의 마지막 줄이 앞의 setting 을 되짚어
# 우선순위를 말한다(설계서 §2.2). 뒤집으면 그 줄이 아직 나오지 않은 블록을 가리킨다.
def test_the_setting_block_comes_before_the_plan_block():
    prompt = _prompt((), _instruction(), _questions(3), _scenario())

    assert prompt.index(_SETTING_ANCHOR) < prompt.index("Today's plan:")
    # 놓친 소리 블록과의 순서도 함께 못박는다 — setting 이 그 앞으로 끼면 B-4 블록이 계획
    # 블록 창(`_plan_block`) 밖에 있다는 전제가 깨진다.
    with_sounds = _prompt(("th_as_s",), _instruction(), _questions(3), _scenario())
    assert with_sounds.index("Sounds this learner has missed before") < with_sounds.index(
        _SETTING_ANCHOR
    )


def test_the_setting_block_carries_the_prompt_template():
    scenario = _scenario()

    prompt = _prompt((), _instruction(), _questions(3), scenario)

    assert scenario.prompt_template in prompt


# ⛔ 규칙 6 tripwire — *"Never read JSON, lists, or metadata out loud"*이고 `title`은 **화면용
# 라벨**이다. `prompt_template` 하나로 무대가 성립한다. 시드 교체가 두 값을 갈라놓은 뒤에야
# 이 단정이 실질을 갖는다(설계서 §2.2의 ⛔ 상자 — 그 전에는 바이트 동일이라 반드시 실패했다).
def test_the_scenario_title_never_reaches_the_prompt():
    scenario = _scenario()

    prompt = _prompt((), _instruction(), _questions(3), scenario)

    assert scenario.title not in prompt
    # 제목에만 있는 낱말로도 잰다 — 제목 전체가 아니라 일부만 실리는 경우를 잡는다.
    assert "at home" not in prompt


# 설정값 `drill_turns_min`이 **문구에 실린다.** 기본값(4)으로 재면 다른 4와 구별할 수 없어
# 일부러 다른 값을 준다 — 이 단정이 "설정값을 읽는다"(캡틴 결정 1)의 증거다.
def test_the_drill_line_carries_the_configured_minimum_number_of_exchanges():
    block = _plan_block(_prompt((), _instruction(), _questions(3), None, drill_turns_min=7))

    # 문구가 여러 줄로 감겨 있으므로 공백을 정규화해 잰다(`SYSTEM_PROMPT` 단정과 같은 방식).
    flowed = " ".join(block.split())
    assert "stay on each one for at least 7 exchanges" in flowed
    # 규칙 2(하나씩 묻고 멈춘다)를 되짚는다 — 대체가 아니라 강화다.
    assert "one at a time" in flowed


# ⛔ H-4 tripwire — 2판은 고정 4단계(*"ask it / (답) / ask one follow-up / say it again"*)를
# 열거했는데 그중 코치 턴은 **3개**였고 기대값은 4를 곱했다 → 모델이 완벽히 지켜도 드릴마다
# 1턴 미달이라 매 세션 경고가 떴다. 단위를 `exchange` 하나로 통일해 문구와 지표가 같은 것을
# 센다. 그래서 계획 블록에 `turns`라는 낱말이 **없어야** 한다.
def test_the_drill_line_counts_exchanges_and_never_says_turns():
    block = _plan_block(_prompt((), _instruction(), _questions(3), None))

    flowed = " ".join(block.split())
    assert "An exchange is one round: you say something, the learner answers" in flowed
    assert "turns" not in block.lower(), (
        "계획 블록이 `turns`를 말한다 — 문구와 기대값 지표의 단위가 갈린다 (H-4)"
    )


# 축 4 — 드릴 반복 ↔ 규칙 4(교정 1건/턴). 규칙 11이 *"발음 교정도 교정이다"*로 상한을 못박은
# **선례의 반대 방향**이라 적지 않으면 모델이 드릴 반복을 교정으로 세어 드릴이 1턴에 끝난다.
def test_the_drill_line_excludes_the_repeat_from_the_one_correction_per_turn_limit():
    block = _plan_block(_prompt((), _instruction(), _questions(3), None))

    flowed = " ".join(block.split())
    assert "That repeat is practice, not a correction" in flowed
    assert "does not count against the one-correction-per-turn limit in rule 4" in flowed


def test_the_questions_are_listed_by_number():
    block = _plan_block(_prompt((), _instruction(), _questions(3), None))

    assert _listed_questions(block) == [
        "    1. Drill question 1? (drill context 1)",
        "    2. Drill question 2? (drill context 2)",
        "    3. Drill question 3? (drill context 3)",
    ]


# ⛔ H-5 — **설정값이 대화를 바꾼다는 증거다.** 2판은 질문을 전부 열거하고 기대값만 깎아서
# `drill_count`가 「대화를 바꾸지 않고 통과 문턱만 바꾸는 노브」였다. 결정 1은 *"드릴 횟수는
# 설정값에 두고 **읽는다**"*이고, 읽어서 대화를 바꿔야 그 결정이 지켜진다.
def test_only_drill_count_questions_are_listed():
    block = _plan_block(_prompt((), _instruction(), _questions(5), None, drill_count=3))

    assert len(_listed_questions(block)) == 3, "질문 5개 중 3개만 열거돼야 한다 (H-5)"
    assert "Drill question 4" not in block
    assert "Drill question 5" not in block


# `drill_count`가 질문 수보다 크면 있는 것만 열거한다 — 없는 질문 자리를 만들지 않는다.
def test_a_drill_count_above_the_question_count_lists_every_question():
    block = _plan_block(_prompt((), _instruction(), _questions(3), None, drill_count=5))

    assert len(_listed_questions(block)) == 3


# ⚠️ **값이 없는 줄은 아예 넣지 않는다** — `known_sounds` 0건·`contexts` 빈 목록의 기존 규약을
# 잇는다. 빈 목록에 드릴 지시만 남기면 모델이 "질문 목록이 비었다"를 지시로 오해할 여지가 생긴다.
def test_the_drill_lines_are_omitted_when_there_are_no_questions():
    block = _plan_block(_prompt((), _instruction(), (), None))

    assert "exchanges" not in block
    assert "Drill question" not in block
    # 나머지 줄은 그대로다 — 드릴 줄을 빼는 것이 블록을 깨뜨리지 않는다.
    assert "B1" in block
    assert "a/an/the" in block


# 축 5 — 우선순위 문장. 결정 9의 예외(*"시나리오 문구가 패턴을 지정하는 경우만"*)를 프롬프트에
# 적어 둔다: 실제로 드문 상황이지만 적어 두는 것이 «드물기를 바라는 것»보다 낫다.
def test_the_priority_line_says_the_focus_wins_over_the_setting():
    block = _plan_block(_prompt((), _instruction(), _questions(3), _scenario()))

    assert _FOCUS_WINS in block
    # 그 줄이 **마지막**이어야 앞의 setting 을 되짚는 것이 된다(설계서 §2.2).
    assert block.rstrip().endswith(_FOCUS_WINS)


# ⛔ 규칙 3 비대체 tripwire — 순서를 지정하면 `SYSTEM_PROMPT` 규칙 3(일상 → 업무 순서)과
# 부딪히고, 결정 9가 세운 「계획 = 목표, 무대·순서는 안 덮는다」 틀을 벗어난다. 그 순서 자체가
# 학습자 프로필의 난이도 상향 경로에서 왔으므로 계획이 그것을 덮으면 프로필이 이름 붙인
# 실패(*"목표 수준을 현재 수준으로 착각해 첫 세션에서 얼어붙는다"*)를 코드로 허용하게 된다.
def test_the_drill_lines_never_pin_an_order_for_the_questions():
    prompt = _prompt((), _instruction(), _questions(5), _scenario(), drill_count=5)

    assert "in this order" not in prompt.lower(), (
        "질문 순서를 지정했다 — 규칙 3(일상 → 업무)과 부딪힌다"
    )
