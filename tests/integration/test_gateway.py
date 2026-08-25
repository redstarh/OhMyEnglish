"""Task 9 — Audio Gateway 세션 수명주기 테스트 (AC G1~G4, 설계서 §5.3).

여기서 검증하는 것은 **어댑터 이벤트와 DB 사이의 규칙**이다:

* `final`만 저장된다 — `partial`은 브로드캐스트만 하고 한 행도 남기지 않는다.
* 저장은 `save_final_transcript`가 하므로 사용자 learning 발화에만 분석 job이
  붙는다(W6) — agent 질문은 전사문으로 남지만 교정 대상이 아니다.
* 종료 시 `adapter.close()`가 **세션 종료 기록보다 먼저** 일어난다(G1).
* 연결이 안 되면 세션은 `failed`로 닫히고 클라이언트는 그 사실을 통보받는다(G2).

WebSocket 계층은 여기에 없다. `SessionRunner`를 어댑터 대역과 가짜 클라이언트
큐로 직접 돌린다 — 실서버를 띄우지 않고, 실시간 대기 없이(타임아웃 주입) 규칙만
관측하기 위한 선택이다. 소켓 배선은 `tests/integration/test_ws.py`가 본다.
"""

from __future__ import annotations

import ast
import asyncio
import base64
import inspect
from collections.abc import AsyncIterator
from types import ModuleType
from typing import Any
from uuid import UUID

import asyncpg
import pytest

from app.api import ws as ws_module
from app.audio_gateway import session as session_module
from app.audio_gateway.factory import (
    STUB_ADAPTER,
    STUB_UNRESPONSIVE_ADAPTER,
    create_voice_adapter,
)
from app.audio_gateway.fixtures import FIXTURE_TURNS, TONE_WAV_FRAME
from app.audio_gateway.port import AdapterEvent, TranscriptEvent, VoiceAdapter
from app.audio_gateway.session import (
    CONNECT_ERROR_REASON,
    CONNECT_TIMEOUT,
    CONNECT_TIMEOUT_REASON,
    DRAIN_TIMEOUT,
    SessionEndStatus,
    SessionRunner,
)
from app.audio_gateway.stub import StubVoiceAdapter
from app.config import Settings

# 연결 타임아웃 주입값. 실시간 대기 금지 — 무응답 경로도 0.1초 안에 판정된다.
FAST_CONNECT_TIMEOUT = 0.1
# 드레인 데드라인 주입값. 어댑터가 스트림을 닫지 않는 대역(`hold_open=True`)에서
# 종료 경로를 보는 테스트는 데드라인 자체가 관심사가 아니라, 기다릴 이유가 없다.
FAST_DRAIN_TIMEOUT = 0.05


def _settings(*, voice_adapter: str) -> Settings:
    """자격증명·DSN을 실제로 쓰지 않는 Settings 인스턴스 (팩토리 분기 검증용)."""
    return Settings(
        database_url="postgresql://unused/unused",
        aws_region="us-west-2",
        voice_adapter=voice_adapter,
    )


class FakeClient:
    """가짜 클라이언트 큐.

    서버가 보낸 이벤트를 `sent`에 모으고, 미리 넣어둔 클라이언트 메시지를 순서대로
    돌려준다. 대본에 `None`을 넣으면 그 지점에서 연결이 끊긴 것으로 취급한다.

    대본이 **비어 있으면 영원히 대기한다** — 조용히 듣고만 있는 클라이언트다.
    빈 큐를 "끊김"으로 오해하면 러너가 어댑터 이벤트를 다 받기 전에 세션을
    닫아버리므로, 이 구분이 이 대역의 핵심이다.
    """

    def __init__(self, *inbound: dict[str, Any] | None) -> None:
        self.sent: list[dict[str, Any]] = []
        self._inbound = list(inbound)

    async def send_event(self, event: dict[str, Any]) -> None:
        self.sent.append(event)

    async def receive_event(self) -> dict[str, Any] | None:
        if self._inbound:
            return self._inbound.pop(0)
        await asyncio.Event().wait()  # 조용한 클라이언트 — 러너가 취소해준다
        raise AssertionError("unreachable")

    @property
    def types(self) -> list[str]:
        return [event["type"] for event in self.sent]

    def of_type(self, event_type: str) -> list[dict[str, Any]]:
        return [event for event in self.sent if event["type"] == event_type]


class ScriptedAdapter:
    """대본대로 이벤트를 흘리는 어댑터 대역.

    스텁이 **만들지 않는** 경계 입력(빈 final, partial만 오는 흐름)을 러너에 넣기
    위한 것이다. `hold_open=True`면 대본을 다 흘린 뒤에도 스트림을 열어 둔다 —
    클라이언트가 `end_session`으로 끝내는 경로를 볼 때 쓴다. `delay`는 이벤트마다
    앞에 두는 지연으로, 종료 신호가 먼저 도착한 뒤에 도착하는 이벤트를 만든다(I3).

    `start_error`가 주어지면 `start()`가 그 예외를 던진다 — 타임아웃이 아닌 연결
    실패(Phase 2의 403이 이 모양)를 재현한다(I2).
    """

    def __init__(
        self,
        *events: AdapterEvent,
        hold_open: bool = False,
        delay: float = 0.0,
        start_error: Exception | None = None,
    ) -> None:
        self.script = list(events)
        self.hold_open = hold_open
        self.delay = delay
        self.start_error = start_error
        self.frames: list[bytes] = []
        self.closed = False

    async def start(self) -> None:
        if self.start_error is not None:
            raise self.start_error

    async def send_audio(self, frame: bytes) -> None:
        self.frames.append(frame)

    async def events(self) -> AsyncIterator[AdapterEvent]:
        for event in self.script:
            if self.delay:
                await asyncio.sleep(self.delay)
            yield event
        if self.hold_open:
            await asyncio.Event().wait()

    async def close(self) -> None:
        self.closed = True


class OrderSpyAdapter:
    """픽스처 스텁을 감싸 `close()` 호출 시점만 기록한다 (G1 순서 단정용)."""

    def __init__(self, calls: list[str]) -> None:
        self._calls = calls
        self._inner = StubVoiceAdapter()

    async def start(self) -> None:
        await self._inner.start()

    async def send_audio(self, frame: bytes) -> None:
        await self._inner.send_audio(frame)

    def events(self) -> AsyncIterator[AdapterEvent]:
        return self._inner.events()

    async def close(self) -> None:
        self._calls.append("adapter.close")
        await self._inner.close()


async def _utterances(pool: asyncpg.Pool, session_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "select speaker, transcript, sequence_no from utterances "
            "where session_id = $1 order by sequence_no",
            session_id,
        )


async def _job_count(pool: asyncpg.Pool, session_id: UUID) -> int:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "select count(*) from analysis_jobs j join utterances u on u.id = j.utterance_id "
            "where u.session_id = $1 and j.job_type = 'analyze_utterance'",
            session_id,
        )


async def _session_row(pool: asyncpg.Pool, session_id: UUID) -> asyncpg.Record:
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "select status, ended_at from learning_sessions where id = $1", session_id
        )
    assert record is not None
    return record


def _runner(
    adapter: VoiceAdapter, pool: asyncpg.Pool, session_id: UUID, client: FakeClient, **kw: Any
) -> SessionRunner:
    return SessionRunner(adapter, pool, session_id, client=client, **kw)


# ① 픽스처 완주 → 사용자 final 3행 + job 3건 (G4)
async def test_fixture_run_saves_user_finals_and_enqueues_three_jobs(db_pool, committed_session):
    adapter = StubVoiceAdapter()
    client = FakeClient()

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, client).run(), timeout=5.0
    )

    rows = await _utterances(db_pool, committed_session.session_id)
    user_rows = [row for row in rows if row["speaker"] == "user"]
    agent_rows = [row for row in rows if row["speaker"] == "agent"]
    assert [row["transcript"] for row in user_rows] == [answer for _, answer in FIXTURE_TURNS]
    assert [row["transcript"] for row in agent_rows] == [question for question, _ in FIXTURE_TURNS]
    # partial은 한 행도 남기지 않는다 — 저장된 것은 final 6개(질문 3 + 응답 3)뿐이다.
    assert len(rows) == len(FIXTURE_TURNS) * 2
    # 분석 job은 사용자 발화에만 붙는다 (W6).
    assert await _job_count(db_pool, committed_session.session_id) == len(FIXTURE_TURNS)


# ① 보강 — 같은 완주에서 클라이언트가 받는 프로토콜(순서·필드·base64)
async def test_fixture_run_broadcasts_the_full_protocol(db_pool, committed_session):
    client = FakeClient()

    await asyncio.wait_for(
        _runner(StubVoiceAdapter(), db_pool, committed_session.session_id, client).run(),
        timeout=5.0,
    )

    assert client.types[0] == "session_started"
    assert client.sent[0]["session_id"] == str(committed_session.session_id)
    assert client.types[-1] == "session_ended"
    finals = client.of_type("final")
    assert [event["speaker"] for event in finals] == ["agent", "user"] * len(FIXTURE_TURNS)
    # sequence_no는 서버(DB)가 부여한 값이 그대로 나간다.
    assert [event["sequence_no"] for event in finals] == list(range(1, len(FIXTURE_TURNS) * 2 + 1))
    assert len(client.of_type("partial")) >= len(FIXTURE_TURNS)
    audio = client.of_type("audio")
    assert len(audio) == len(FIXTURE_TURNS)
    assert base64.b64decode(audio[0]["data"]) == TONE_WAV_FRAME


# ② 무응답 어댑터 → status='failed' + 실패 이벤트, 무한 대기 없음 (G2)
async def test_unresponsive_adapter_fails_the_session_without_hanging(db_pool, committed_session):
    adapter = StubVoiceAdapter(mode="unresponsive")
    client = FakeClient()
    loop = asyncio.get_running_loop()
    started = loop.time()

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            client,
            connect_timeout=FAST_CONNECT_TIMEOUT,
        ).run(),
        timeout=2.0,
    )

    assert loop.time() - started < 1.0, "주입한 타임아웃을 무시하고 매달렸다"
    assert client.types == ["session_started", "session_failed"]
    assert client.of_type("session_failed")[0]["reason"] == CONNECT_TIMEOUT_REASON
    session = await _session_row(db_pool, committed_session.session_id)
    assert session["status"] == "failed"
    assert session["ended_at"] is not None
    assert adapter.closed, "연결 실패 경로에서도 어댑터 자원은 정리돼야 한다"
    assert await _utterances(db_pool, committed_session.session_id) == []


# ③ 정상 종료 → close가 종료 기록보다 먼저 (G1) + ended_at·completed
async def test_adapter_close_precedes_the_session_end_record(
    db_pool, committed_session, monkeypatch: pytest.MonkeyPatch
):
    calls: list[str] = []
    original = session_module.mark_session_ended

    async def spy(pool: asyncpg.Pool, session_id: UUID, status: SessionEndStatus) -> None:
        calls.append("session.end_record")
        await original(pool, session_id, status)

    monkeypatch.setattr(session_module, "mark_session_ended", spy)

    await asyncio.wait_for(
        _runner(OrderSpyAdapter(calls), db_pool, committed_session.session_id, FakeClient()).run(),
        timeout=5.0,
    )

    assert calls == ["adapter.close", "session.end_record"]
    session = await _session_row(db_pool, committed_session.session_id)
    assert session["status"] == "completed"
    assert session["ended_at"] is not None


# 빈/공백 final은 저장하지 않는다 — 분석 파이프라인의 "0건 done" 처리와 이중 방어
async def test_blank_final_is_neither_stored_nor_broadcast(db_pool, committed_session):
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="   "),
        TranscriptEvent(kind="final", text=""),
    )
    client = FakeClient()

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, client).run(), timeout=5.0
    )

    assert await _utterances(db_pool, committed_session.session_id) == []
    assert await _job_count(db_pool, committed_session.session_id) == 0
    assert client.of_type("final") == []


# partial은 브로드캐스트만 — 저장 금지
async def test_partial_events_are_broadcast_but_never_stored(db_pool, committed_session):
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="partial", text="I usually"),
        TranscriptEvent(kind="partial", text="I usually go to"),
    )
    client = FakeClient()

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, client).run(), timeout=5.0
    )

    assert [event["text"] for event in client.of_type("partial")] == [
        "I usually",
        "I usually go to",
    ]
    assert await _utterances(db_pool, committed_session.session_id) == []


# 클라이언트 오디오는 어댑터로 릴레이되고, end_session이 세션을 끝낸다
async def test_client_audio_is_relayed_and_end_session_closes_the_session(
    db_pool, committed_session
):
    frames = [b"\x01\x02\x03", b"\x04"]
    adapter = ScriptedAdapter(hold_open=True)
    client = FakeClient(
        *({"type": "audio", "data": base64.b64encode(frame).decode("ascii")} for frame in frames),
        {"type": "end_session"},
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            client,
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    assert adapter.frames == frames
    assert adapter.closed
    assert client.types[-1] == "session_ended"
    assert (await _session_row(db_pool, committed_session.session_id))["status"] == "completed"


# 클라이언트 연결이 끊기면(대본의 None) 세션은 정상 종료로 닫힌다
async def test_client_disconnect_ends_the_session(db_pool, committed_session):
    adapter = ScriptedAdapter(hold_open=True)

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            FakeClient(None),
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    assert adapter.closed
    assert (await _session_row(db_pool, committed_session.session_id))["status"] == "completed"


# 깨진 오디오 프레임(base64 아님)은 무시된다 — 세션을 죽이지 않는다
async def test_malformed_client_message_does_not_kill_the_session(db_pool, committed_session):
    adapter = ScriptedAdapter(hold_open=True)
    client = FakeClient(
        {"type": "audio", "data": "not-base64!!"},
        {"type": "audio"},
        {"type": "who-knows"},
        {"type": "end_session"},
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            client,
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    assert adapter.frames == []
    assert client.types[-1] == "session_ended"


# Fix round 1 (I1) — 비ASCII 문자열은 `binascii.Error`가 아니라 순수 `ValueError`다
# (`b64decode`가 ascii 인코딩에서 먼저 실패한다). 그 예외를 놓치면 오디오 프레임
# 하나가 펌프를 죽이고 세션 전체가 끝난다.
async def test_non_ascii_audio_frame_does_not_kill_the_session(db_pool, committed_session):
    adapter = ScriptedAdapter(hold_open=True)
    good_frame = b"\x07\x08"
    client = FakeClient(
        {"type": "audio", "data": "한글데이터"},
        {"type": "audio", "data": base64.b64encode(good_frame).decode("ascii")},
        {"type": "end_session"},
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            client,
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    # 깨진 프레임 뒤의 정상 프레임이 도착했다 = 세션이 살아 있었다.
    assert adapter.frames == [good_frame]
    assert client.types[-1] == "session_ended"
    assert (await _session_row(db_pool, committed_session.session_id))["status"] == "completed"


# Fix round 1 (I2) — 타임아웃이 아닌 연결 실패(예: 권한 거부)도 세션을 닫고 알려야
# 한다. 예외가 그대로 새어나가면 세션은 `active` 고아로 남고 클라이언트는 통보를
# 받지 못해 U2의 "연결 실패" 화면이 뜨지 않는다.
async def test_failing_adapter_start_fails_the_session(db_pool, committed_session):
    adapter = ScriptedAdapter(start_error=RuntimeError("403 forbidden"))
    client = FakeClient()

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, client).run(), timeout=5.0
    )

    assert client.types == ["session_started", "session_failed"]
    assert client.of_type("session_failed")[0]["reason"] == CONNECT_ERROR_REASON
    session = await _session_row(db_pool, committed_session.session_id)
    assert session["status"] == "failed"
    assert session["ended_at"] is not None
    assert adapter.closed
    assert await _utterances(db_pool, committed_session.session_id) == []


# Fix round 1 (I3) — 종료 신호 뒤에 도착하는 이벤트를 버리지 않는다. 사용자가
# 말을 마치고 종료를 눌렀을 때 마지막 발화의 final은 아직 오는 중이다 — 즉시
# 취소하면 그 발화가 통째로 사라진다(전사문·분석 모두).
async def test_end_signal_drains_pending_adapter_events(db_pool, committed_session):
    late = "I need to finish my homework tonight."
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text=late),
        hold_open=True,  # 드레인이 데드라인으로 끝나는지도 함께 본다
        delay=0.05,
    )
    client = FakeClient({"type": "end_session"})
    loop = asyncio.get_running_loop()
    started = loop.time()

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, client, drain_timeout=0.2).run(),
        timeout=5.0,
    )

    assert loop.time() - started < 1.0, "드레인에 상한이 없다"
    rows = await _utterances(db_pool, committed_session.session_id)
    assert [row["transcript"] for row in rows] == [late]
    assert await _job_count(db_pool, committed_session.session_id) == 1
    assert client.types[-1] == "session_ended"


# Fix round 1 (I3 후반) — 드레인 마감이 **저장 도중**에 걸려도 그 저장은 끝까지 간다.
# shield가 없으면 취소가 `save_final_transcript`의 트랜잭션 한복판에서 터져 전사문과
# 분석 job이 함께 롤백된다 — 발화가 흔적 없이 사라지는 유일한 경로다.
async def test_a_save_in_flight_survives_the_drain_deadline(
    db_pool, committed_session, monkeypatch: pytest.MonkeyPatch
):
    original = session_module.save_final_transcript

    async def slow_save(conn, session_id, text, **kwargs):
        # 드레인 데드라인(0.05초)보다 오래 걸리는 저장을 만든다.
        await asyncio.sleep(0.1)
        return await original(conn, session_id, text, **kwargs)

    monkeypatch.setattr(session_module, "save_final_transcript", slow_save)
    adapter = ScriptedAdapter(TranscriptEvent(kind="final", text="I go to gym."), hold_open=True)

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            FakeClient({"type": "end_session"}),
            drain_timeout=0.05,
        ).run(),
        timeout=5.0,
    )

    rows = await _utterances(db_pool, committed_session.session_id)
    assert [row["transcript"] for row in rows] == ["I go to gym."]
    assert await _job_count(db_pool, committed_session.session_id) == 1


# --- 스텁 자체의 계약 ---


async def test_stub_counts_the_audio_frames_it_receives():
    adapter = StubVoiceAdapter()
    await adapter.start()

    await adapter.send_audio(b"\x00")
    await adapter.send_audio(b"\x01\x02")

    assert adapter.received_frames == 2


async def test_stub_replays_the_fixture_turns_in_order():
    adapter = StubVoiceAdapter()
    await adapter.start()

    events = [event async for event in adapter.events()]

    kinds = [
        "audio" if isinstance(event, bytes) else f"{event.kind}:{event.speaker}" for event in events
    ]
    # 각 턴은 질문(agent final) → 사용자 partial 1~2개 → 사용자 final → 오디오 프레임.
    assert kinds[0] == "final:agent"
    assert kinds[-1] == "audio"
    assert kinds.count("final:agent") == len(FIXTURE_TURNS)
    assert kinds.count("final:user") == len(FIXTURE_TURNS)
    assert kinds.count("audio") == len(FIXTURE_TURNS)
    assert len(FIXTURE_TURNS) <= kinds.count("partial:user") <= len(FIXTURE_TURNS) * 2
    assert all(isinstance(event, bytes) or event.sequence_no is None for event in events)


async def test_unresponsive_stub_never_completes_its_start():
    adapter = StubVoiceAdapter(mode="unresponsive")

    with pytest.raises(TimeoutError):
        await asyncio.wait_for(adapter.start(), timeout=FAST_CONNECT_TIMEOUT)


# Fix round 1 (I5) — 무음이면 프론트엔드 재생을 귀로 판정할 수 없다. 들리는 톤이어야
# "소리가 났는가"가 사람이 확인할 수 있는 사실이 된다.
def test_fixture_audio_frame_is_audible():
    header, body = TONE_WAV_FRAME[:44], TONE_WAV_FRAME[44:]
    assert header.startswith(b"RIFF")
    assert set(body) != {0}, "무음 프레임은 귀로 판정할 수 없다"


def test_connect_timeout_is_a_documented_design_value():
    assert CONNECT_TIMEOUT == 10


def test_drain_timeout_is_a_documented_design_value():
    assert DRAIN_TIMEOUT == 1.0


# Fix round 1 (I4) — E2E-S 6(연결 실패 시나리오)은 서버를 코드 수정 없이 무응답
# 모드로 띄울 수 있어야 실행 가능하다. 그 선택은 설정값 하나로 끝난다.
@pytest.mark.parametrize(
    ("setting", "expected_mode"),
    [(STUB_ADAPTER, "fixture"), (STUB_UNRESPONSIVE_ADAPTER, "unresponsive")],
)
def test_factory_builds_the_stub_mode_from_settings(setting: str, expected_mode: str):
    adapter = create_voice_adapter(_settings(voice_adapter=setting))

    assert isinstance(adapter, StubVoiceAdapter)
    assert adapter.mode == expected_mode


def test_factory_rejects_an_unknown_adapter():
    with pytest.raises(ValueError, match="voice_adapter"):
        create_voice_adapter(_settings(voice_adapter="nova"))


# ④ import 그래프 — 러너와 소켓 계층은 스텁을 모른다 (G3)


def _imported_names(module: ModuleType) -> list[str]:
    tree = ast.parse(inspect.getsource(module))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
            names.extend(alias.name for alias in node.names)
    return names


@pytest.mark.parametrize("module", [session_module, ws_module], ids=["session", "ws"])
def test_gateway_core_does_not_import_the_stub(module: ModuleType):
    """스텁은 **주입**된다. 러너·소켓이 스텁을 import하면 테스트 대역이 프로덕션
    의존성이 되고, Nova 어댑터로 갈아끼울 이음매가 사라진다 (G3).

    `StubVoiceAdapter`라는 식별자 자체를 원문에서 금지한다 — 주석·docstring에
    적어두는 것도 결국 그 모듈을 아는 상태라, 검사를 우회할 여지를 남기지 않는다.
    """
    assert all("stub" not in name.lower() for name in _imported_names(module))
    assert "StubVoiceAdapter" not in inspect.getsource(module)
