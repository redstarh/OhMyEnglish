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
from typing import Any, cast
from uuid import UUID

import asyncpg
import pytest

from app.api import ws as ws_module
from app.audio_gateway import session as session_module
from app.audio_gateway.factory import (
    NOVA_ADAPTER,
    STUB_ADAPTER,
    STUB_UNRESPONSIVE_ADAPTER,
    create_voice_adapter,
)
from app.audio_gateway.fixtures import FIXTURE_TURNS, TONE_WAV_FRAME
from app.audio_gateway.nova import SYSTEM_PROMPT, NovaVoiceAdapter
from app.audio_gateway.port import (
    AdapterEvent,
    InterruptionEvent,
    PronunciationEvent,
    SpeechBoundaryEvent,
    TranscriptEvent,
    VoiceAdapter,
)
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
from app.models.plan import InstructionFocus, SessionInstruction

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


class FlakyPool:
    """`acquire()`의 **N번째 호출만** 실패시키는 pool 프록시.

    `SessionRunner`가 pool에서 쓰는 것은 `acquire()` 하나뿐이라 이 대역으로 충분하다.
    `asyncpg.Pool` 인스턴스에 monkeypatch를 걸지 않는 이유는 그쪽이 `__slots__`를
    쓸 수 있어 속성 치환이 구현 세부에 의존하기 때문이다 — 프록시는 그 가정이 없다.
    """

    def __init__(self, inner: asyncpg.Pool, *, fail_on: int) -> None:
        self._inner = inner
        self._fail_on = fail_on
        self.calls = 0

    def acquire(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        if self.calls == self._fail_on:
            raise RuntimeError("injected pool.acquire failure")
        return self._inner.acquire(*args, **kwargs)


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


# I-1 T0④ — 대화가 사용자 발화로 끝나는 것이 정상이다. agent final이 뒤따르지
# 않으므로 턴 경계 flush가 걸리지 않고, 종료 경로에서 한 번 더 flush하지 않으면
# 마지막 묶음은 영원히 분석되지 않는다.
async def test_session_ending_with_user_speech_enqueues_its_analysis_on_close(
    db_pool, committed_session
):
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="i'm going to", speaker="user"),
        TranscriptEvent(kind="final", text="have a meeting.", speaker="user"),
    )

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, FakeClient()).run(), timeout=5.0
    )

    assert await _job_count(db_pool, committed_session.session_id) == 1
    async with db_pool.acquire() as conn:
        target = await conn.fetchval(
            "select u.sequence_no from analysis_jobs j join utterances u on u.id = j.utterance_id "
            "where u.session_id = $1",
            committed_session.session_id,
        )
    assert target == 2, "job은 묶음의 **마지막** 발화에 걸려야 한다 (병합 입력의 기준점)"


# I-1 T3 — flush가 터져도 대화와 종료 기록은 살아남는다.
# 저장과 등록이 갈라진 뒤(`save_final_transcript`가 더 이상 enqueue하지 않는다)
# 남은 위험은 flush 실패가 이벤트 펌프나 종료 경로를 끌고 내려가는 것이다. 분석
# 1건을 잃는 편이 전사문을 잃거나 세션을 `active` 고아로 남기는 것보다 낫다.
async def test_a_failing_flush_loses_only_the_analysis_not_the_session(
    db_pool, committed_session, monkeypatch: pytest.MonkeyPatch
):
    async def boom(conn: asyncpg.Connection, session_id: UUID) -> list[UUID]:
        raise RuntimeError("injected flush failure")

    monkeypatch.setattr(session_module, "flush_pending_analysis", boom)
    client = FakeClient()

    await asyncio.wait_for(
        _runner(StubVoiceAdapter(), db_pool, committed_session.session_id, client).run(),
        timeout=5.0,
    )

    assert client.types[-1] == "session_ended"
    session = await _session_row(db_pool, committed_session.session_id)
    assert session["status"] == "completed"
    assert session["ended_at"] is not None
    # 전사문은 한 행도 잃지 않는다 — 질문 3 + 응답 3.
    assert len(await _utterances(db_pool, committed_session.session_id)) == len(FIXTURE_TURNS) * 2
    assert await _job_count(db_pool, committed_session.session_id) == 0


# I-1 T3 보강 — flush의 **연결 획득**이 실패해도 close와 종료 기록은 반드시 돈다.
# 위 테스트는 `flush_pending_analysis`만 raise시키므로 acquire 실패 경로를 덮지 못한다.
# 코드 리뷰가 가짜 pool로 실측한 결함이다: acquire를 가드 밖에 두면 `adapter.close()`가
# 한 번도 불리지 않고(실물에서는 Nova 양방향 스트림 누수) 세션이 `active` 고아로 남는다.
async def test_a_failing_flush_connection_still_closes_the_adapter_and_records_the_end(
    db_pool, committed_session
):
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="i'm going to have a meeting.", speaker="user")
    )
    # acquire 순서: ① 발화 저장 ② 종료 경로 flush ③ 종료 기록. ②만 실패시킨다.
    pool = FlakyPool(db_pool, fail_on=2)
    # `asyncpg.Pool`은 Protocol이 아니라 구상 클래스라 프록시가 구조적으로 맞지 않는다.
    # 러너가 쓰는 것은 `acquire()` 하나뿐이므로 여기서만 좁힌다.
    await asyncio.wait_for(
        _runner(
            adapter, cast(asyncpg.Pool, pool), committed_session.session_id, FakeClient()
        ).run(),
        timeout=5.0,
    )

    assert pool.calls >= 3, "종료 기록 acquire까지 도달하지 못했다 — 앞에서 터졌다"
    assert adapter.closed, "flush 연결 획득 실패가 어댑터 정리를 건너뛰었다"
    session = await _session_row(db_pool, committed_session.session_id)
    assert session["status"] == "completed", "세션이 active 고아로 남았다"
    assert session["ended_at"] is not None
    # 잃는 것은 분석 job 하나뿐이다 — 전사문은 남는다.
    assert len(await _utterances(db_pool, committed_session.session_id)) == 1
    assert await _job_count(db_pool, committed_session.session_id) == 0


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
    # 종료 기록은 이제 `end_session(conn, …)`이다 — 발음 시도 수렴과 한 트랜잭션으로
    # 묶기 위해 연결을 받는 원시 함수를 쓴다(`services/sessions.py`).
    original = session_module.end_session

    async def spy(conn: asyncpg.Connection, session_id: UUID, status: SessionEndStatus) -> None:
        calls.append("session.end_record")
        await original(conn, session_id, status)

    monkeypatch.setattr(session_module, "end_session", spy)

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


def _stub_event_label(event: AdapterEvent) -> str:
    """스텁이 흘린 이벤트 하나의 라벨. 스텁은 전사문·오디오만 흘린다 —
    포트가 확장돼도(3차수) 그 계약은 그대로여서, 그 밖의 타입은 여기서 즉시 실패한다."""
    if isinstance(event, bytes):
        return "audio"
    if isinstance(event, TranscriptEvent):
        return f"{event.kind}:{event.speaker}"
    raise AssertionError(f"스텁이 예상 밖 이벤트를 흘렸다: {event!r}")


async def test_stub_replays_the_fixture_turns_in_order():
    adapter = StubVoiceAdapter()
    await adapter.start()

    events = [event async for event in adapter.events()]

    kinds = [_stub_event_label(event) for event in events]
    # 각 턴은 질문(agent final) → 사용자 partial 1~2개 → 사용자 final → 오디오 프레임.
    assert kinds[0] == "final:agent"
    assert kinds[-1] == "audio"
    assert kinds.count("final:agent") == len(FIXTURE_TURNS)
    assert kinds.count("final:user") == len(FIXTURE_TURNS)
    assert kinds.count("audio") == len(FIXTURE_TURNS)
    assert len(FIXTURE_TURNS) <= kinds.count("partial:user") <= len(FIXTURE_TURNS) * 2
    for event in events:
        # `sequence_no`는 서버(DB)가 부여한다 — 어댑터가 채우면 소유자가 둘이 된다.
        if isinstance(event, TranscriptEvent):
            assert event.sequence_no is None


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


# Nova 실연동(3차수). 분기는 이 함수 한 곳에만 있다 (G3) — 팩토리는 어댑터를 만들 뿐
# 스트림을 열지 않으므로, 이 테스트는 자격증명·네트워크를 만지지 않는다.
def test_factory_builds_the_nova_adapter():
    adapter = create_voice_adapter(_settings(voice_adapter=NOVA_ADAPTER))

    assert isinstance(adapter, NovaVoiceAdapter)


def test_factory_rejects_an_unknown_adapter():
    # 오타를 조용히 스텁으로 흘리면 "실물이라 믿었던 세션이 픽스처였다"가 된다.
    with pytest.raises(ValueError, match="voice_adapter"):
        create_voice_adapter(_settings(voice_adapter="novva"))


_SOUNDS_HEADER = "Sounds this learner has missed before"


def _sounds_section(instructions: str) -> str:
    """놓친 소리 블록만 잘라낸다 — 고정부를 창에서 뺀다.

    `tests/unit/test_nova.py`의 `_plan_block`과 같은 이유이고 같은 형태다: 조용한 퇴화를
    시끄러운 실패로 바꾸려고 제목 부재를 먼저 단정한다(`_bullet` 관례).
    """
    assert _SOUNDS_HEADER in instructions, "지시문에 놓친 소리 블록이 없다"
    return instructions[instructions.index(_SOUNDS_HEADER) :]


# G-3 — 지시문 가변부가 지나가는 **유일한 통로**가 이 팩토리다. 두 가지를 함께 못박는다:
# ① `port.start()`를 넓히지 않는다(어댑터를 **만들 때** 넘기므로 포트 계약이 그대로다)
# ② 넘기는 것은 **데이터**(소리 목록)이고 조립은 여기서 한다 — 호출자가 프롬프트를 만들면
#    소켓 계층이 `nova`를 import해야 하고 G3 이음매가 사라진다.
#
# ⚠️ **소리 목록을 `"th_as_s"`·`"f_as_p"`로 재지 않는다** — 두 키는 고정부 규칙 10의 예시로
# **이미** 들어 있다(직접 확인: 각 1건). 그래서 이 단정은 팩토리가 목록을 **버려도** 초록이었다
# (S2-10 리뷰가 `if known_sounds:` → `if False:` 뮤테이션으로 증명했고 나도 재현했다).
# 블록 **제목**으로 잰다 — 그 문구는 고정부에 0건이라 판별력이 있다.
def test_factory_assembles_the_prompt_from_known_sounds_for_nova():
    adapter = create_voice_adapter(
        _settings(voice_adapter=NOVA_ADAPTER), known_sounds=["th_as_s", "f_as_p"]
    )

    assert isinstance(adapter, NovaVoiceAdapter)
    sounds = _sounds_section(adapter.instructions)
    assert "th_as_s" in sounds
    assert "f_as_p" in sounds


# 목록을 주지 않으면 기본 문구다 — dev DB의 현재 상태(기록 0건)가 이 경로다.
def test_factory_uses_the_base_prompt_when_there_are_no_known_sounds():
    adapter = create_voice_adapter(_settings(voice_adapter=NOVA_ADAPTER))

    assert isinstance(adapter, NovaVoiceAdapter)
    assert adapter.instructions == SYSTEM_PROMPT


# PS8(스텁 무손상) — 스텁도 조립된 지시문을 **받는다**(Task 10). 다만 보관만 하므로
# 모드가 그대로여야 1·2차수 판정이 재현된다. 지시문을 받는 이유는 AS6 판정 수단이
# 그것뿐이기 때문이다(아래 `test_factory_puts_the_plan_into_the_stub_instructions`).
def test_factory_gives_the_stub_the_instructions_without_changing_its_mode():
    adapter = create_voice_adapter(_settings(voice_adapter=STUB_ADAPTER), known_sounds=["th_as_s"])

    assert isinstance(adapter, StubVoiceAdapter)
    assert adapter.mode == "fixture"
    instructions = adapter.instructions
    assert instructions is not None
    # 위 nova 테스트와 같은 이유로 제목으로 잰다 — `"th_as_s"`는 고정부에 이미 있어서
    # 팩토리가 목록을 버려도 초록이었다(리뷰 I-2).
    assert "th_as_s" in _sounds_section(instructions)


# --- Task 10: 오늘의 계획이 지시문에 실린다 (AS6) ---
#
# 여기가 "지시문에 계획이 실린다"를 재는 자리다. 소켓 계층(`tests/integration/test_ws.py`)은
# **데이터**가 팩토리까지 가는 것만 잰다 — 조립은 팩토리가 소유하므로(G3 이음매) 조립 문구를
# 소켓에서 단정하면 그 이음매를 재는 테스트와 규약이 갈린다.


def _plan_instruction() -> SessionInstruction:
    """`SYSTEM_PROMPT`와 겹치지 않는 값만 쓴다 — 겹치면 단정이 항진명제가 된다.
    (`"B1"`·`"work update"`는 고정부에 이미 있어서 쓰지 않는다.)"""
    return SessionInstruction(
        target_level="C1",
        focus=[InstructionFocus(pattern_key="article_missing", target_form="a/an/the")],
        sentence_length="two or three short clauses",
        hint_timing="wait through one long pause before offering a starter",
        contexts=["weekend plan"],
    )


def test_factory_puts_the_plan_into_the_nova_instructions():
    adapter = create_voice_adapter(_settings(voice_adapter=NOVA_ADAPTER), plan=_plan_instruction())

    assert isinstance(adapter, NovaVoiceAdapter)
    assert adapter.instructions != SYSTEM_PROMPT
    assert "a/an/the" in adapter.instructions
    assert "weekend plan" in adapter.instructions


# AS6 — 전달 경로가 관통했는지 판정할 수단이 스텁의 보관값뿐이다.
# ⚠️ **`is not None`으로 끝내지 않는다.** Nova 는 `instructions or SYSTEM_PROMPT`로 falsy 를
# 강제하므로 빈 조립이 조용히 폴백되고, 스텁은 `""`를 그대로 기록한다 — non-None 단정은
# "지시문이 도달했다"가 아니라 "생성자가 인자를 받았다"만 증명한다(S2-9 리뷰 인계 1).
def test_factory_puts_the_plan_into_the_stub_instructions():
    adapter = create_voice_adapter(_settings(voice_adapter=STUB_ADAPTER), plan=_plan_instruction())

    assert isinstance(adapter, StubVoiceAdapter)
    instructions = adapter.instructions
    assert instructions is not None
    assert "a/an/the" in instructions
    assert "weekend plan" in instructions


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


# G-3 확장 — 같은 이음매를 **실물 어댑터 쪽으로도** 막는다. 소켓이 지시문을 조립하려면
# `build_system_prompt`(= `nova` 모듈)를 import해야 하고, 그 순간 "어떤 구현이 붙는지 소켓은
# 모른다"가 깨진다. 그래서 팩토리가 데이터를 받아 조립한다 — 이 테스트가 그 결정을 지킨다.
@pytest.mark.parametrize("module", [session_module, ws_module], ids=["session", "ws"])
def test_gateway_core_does_not_import_the_nova_adapter(module: ModuleType):
    assert all("nova" not in name.lower() for name in _imported_names(module))
    assert "NovaVoiceAdapter" not in inspect.getsource(module)


# --- Fix round 3 (N-4): Nova 신호를 담기 위한 포트 확장 ---
#
# Nova 2 Sonic이 주는 신호 중 `TranscriptEvent | bytes`에 매핑할 곳이 없던 셋을 포트에
# 더했다(설계서 §7이 예고한 확장). 여기서 고정하는 것은 **확장이 상위 로직에 파급되지
# 않는다**는 것이다 — 세션 수명·저장·job 등록은 스텁으로 검증된 그대로여야 한다(G3).


async def test_speech_boundary_events_are_broadcast_but_never_stored(db_pool, committed_session):
    adapter = ScriptedAdapter(
        SpeechBoundaryEvent(speaking=True, offset_ms=0),
        SpeechBoundaryEvent(speaking=False, offset_ms=1920),
    )
    client = FakeClient()

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, client).run(), timeout=5.0
    )

    assert client.types == ["session_started", "speech_start", "speech_end", "session_ended"]
    assert client.of_type("speech_start")[0]["offset_ms"] == 0
    assert client.of_type("speech_end")[0]["offset_ms"] == 1920
    # 발화 경계는 전사문이 아니다 — 한 행도 남기지 않는다.
    assert await _utterances(db_pool, committed_session.session_id) == []


# barge-in 통보. 클라이언트가 **이미 받았지만 아직 재생하지 않은** 오디오를 버릴 근거는
# 이 이벤트뿐이다 — 통보가 없으면 사용자가 말을 시작한 뒤에도 agent 목소리가 계속 나온다.
async def test_interruption_is_broadcast_so_the_client_can_drop_queued_audio(
    db_pool, committed_session
):
    adapter = ScriptedAdapter(TONE_WAV_FRAME, InterruptionEvent())
    client = FakeClient()

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, client).run(), timeout=5.0
    )

    assert client.types == ["session_started", "audio", "interrupted", "session_ended"]
    assert await _utterances(db_pool, committed_session.session_id) == []


async def test_new_event_types_do_not_disturb_saving_or_the_session_lifecycle(
    db_pool, committed_session
):
    answer = FIXTURE_TURNS[0][1]
    adapter = ScriptedAdapter(
        SpeechBoundaryEvent(speaking=True, offset_ms=0),
        TranscriptEvent(kind="final", text=answer, speaker="user"),
        SpeechBoundaryEvent(speaking=False, offset_ms=1920),
        InterruptionEvent(),
    )
    client = FakeClient()

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, client).run(), timeout=5.0
    )

    rows = await _utterances(db_pool, committed_session.session_id)
    assert [row["transcript"] for row in rows] == [answer]
    assert await _job_count(db_pool, committed_session.session_id) == 1
    session = await _session_row(db_pool, committed_session.session_id)
    assert session["status"] == "completed"
    assert session["ended_at"] is not None


# 스텁은 새 이벤트를 만들지 않는다 — 1·2차수 회귀(C2: 회색 부분 전사문 → 확정 전환)가
# 스텁 거동을 검증하고 있어서, 스텁이 발화 경계를 흘리기 시작하면 그 화면 거동이 바뀐다.
async def test_stub_emits_only_transcripts_and_audio():
    adapter = StubVoiceAdapter()
    await adapter.start()

    events = [event async for event in adapter.events()]

    assert not any(isinstance(event, SpeechBoundaryEvent | InterruptionEvent) for event in events)
    assert all(isinstance(event, TranscriptEvent | bytes) for event in events)


# --- 발음 시도 기록 (계획 Task 6 · 설계서 §3.2 · PS1·PS4·PS5·PS8) ---
#
# 감지 경로는 **둘**이다: Nova tool(정확) + 한글 전사(확실). 세 번째였던 "agent가 되묻는
# 문구를 잡기"는 **캡틴 결정(2026-08-28)으로 만들지 않는다** — 문구 매칭이라 케이스가 불어나고,
# 지시문 규칙 9(발음 시범)가 매번 "repeat"를 만들어 시범과 되묻기를 가르는 규칙이 계속
# 자란다. ⚠️ 번호는 Task 10에서 밀렸다 — 65% 규칙이 7번으로 들어와 발음 규칙이 8~11이 됐다.
# 그래서 R10-4의 절반은 의도적으로 미충족이다.

# 4차수 P4 실측: 한국어 억양이 강하면 ASR 언어 판별이 뒤집혀 영어 문장이 한글로 전사된다.
KOREAN_TRANSCRIPT = "아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈"
PRONUNCIATION_TARGET = "I think I found three very useful videos."


async def _pronunciation_rows(pool: asyncpg.Pool, session_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "select outcome, target_form, spoken_form, target_sound, signal_source "
            "from pronunciation_attempts where session_id = $1 order by attempt_seq",
            session_id,
        )


# ① PS1 — tool 이벤트가 저장되고 화면에도 나간다
async def test_pronunciation_event_is_stored_and_broadcast(db_pool, committed_session):
    client = FakeClient()
    adapter = ScriptedAdapter(
        PronunciationEvent(
            target_form=PRONUNCIATION_TARGET,
            outcome="pending",
            spoken_form="[awaiting user repetition]",
            target_sound="th_as_s",
        )
    )

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, client).run(), timeout=5.0
    )

    rows = await _pronunciation_rows(db_pool, committed_session.session_id)
    assert len(rows) == 1
    assert rows[0]["signal_source"] == "nova_tool"
    assert rows[0]["target_form"] == PRONUNCIATION_TARGET
    assert rows[0]["target_sound"] == "th_as_s"
    frames = client.of_type("pronunciation")
    assert len(frames) == 1
    assert frames[0]["target_form"] == PRONUNCIATION_TARGET
    assert frames[0]["outcome"] == "pending", "방송은 그 순간의 값이다 — 수렴은 나중 일이다"


# ② 판정이 오면 같은 행이 닫힌다 — 시도 수가 부풀지 않는다
async def test_a_verdict_closes_the_same_attempt(db_pool, committed_session):
    adapter = ScriptedAdapter(
        PronunciationEvent(target_form=PRONUNCIATION_TARGET, outcome="pending"),
        PronunciationEvent(
            target_form=PRONUNCIATION_TARGET,
            outcome="correct",
            spoken_form="I think I found three very useful videos.",
        ),
    )

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, FakeClient()).run(), timeout=5.0
    )

    rows = await _pronunciation_rows(db_pool, committed_session.session_id)
    assert len(rows) == 1, "두 tool 호출은 한 시도다"
    assert rows[0]["outcome"] == "correct"
    assert rows[0]["spoken_form"] == "I think I found three very useful videos."


# ③ PS4 + 캡틴 결정 — 대답 없이 끝나면 `incorrect`다. 이후 학습도 그냥 틀림으로 본다.
#    `spoken_form`은 비운다: 재발화를 실제로 못 들었으므로 Nova의 placeholder 문구를
#    "학습자가 이렇게 들렸다"로 남겨두면 결과 화면이 그 문구를 보여준다.
async def test_pending_converges_to_incorrect_when_the_session_ends(db_pool, committed_session):
    adapter = ScriptedAdapter(
        PronunciationEvent(
            target_form=PRONUNCIATION_TARGET,
            outcome="pending",
            spoken_form="[awaiting user repetition]",
        ),
        PronunciationEvent(target_form="Other sentence.", outcome="pending"),
    )

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, FakeClient()).run(), timeout=5.0
    )

    rows = await _pronunciation_rows(db_pool, committed_session.session_id)
    assert [row["outcome"] for row in rows] == ["incorrect", "incorrect"]
    assert all(row["spoken_form"] is None for row in rows)


# ④ PS5 — 한글 전사문이 보조 신호로 기록되고, 저장·job 등록은 그대로 일어난다
async def test_korean_transcript_records_an_assist_signal(db_pool, committed_session):
    adapter = ScriptedAdapter(TranscriptEvent(kind="final", text=KOREAN_TRANSCRIPT, speaker="user"))

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, FakeClient()).run(), timeout=5.0
    )

    rows = await _pronunciation_rows(db_pool, committed_session.session_id)
    assert len(rows) == 1
    assert rows[0]["signal_source"] == "korean_transcript"
    assert rows[0]["outcome"] == "unclear"
    assert rows[0]["spoken_form"] == KOREAN_TRANSCRIPT
    # 파이프라인이 죽지 않았다는 증거 — 전사문도 남고 분석 job도 붙는다
    assert len(await _utterances(db_pool, committed_session.session_id)) == 1
    assert await _job_count(db_pool, committed_session.session_id) == 1


# ⑤ 정상 영어 전사문에는 신호가 붙지 않는다 — 오탐 방지
async def test_ascii_transcript_records_no_assist_signal(db_pool, committed_session):
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text=FIXTURE_TURNS[0][1], speaker="user")
    )

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, FakeClient()).run(), timeout=5.0
    )

    assert await _pronunciation_rows(db_pool, committed_session.session_id) == []


# ⑥ 한글이 섞여도 **agent** 발화에는 신호를 붙이지 않는다 — 신호는 학습자 발음에 대한 것이다
async def test_korean_in_agent_text_records_no_assist_signal(db_pool, committed_session):
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="좋아요, " + KOREAN_TRANSCRIPT, speaker="agent")
    )

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, FakeClient()).run(), timeout=5.0
    )

    assert await _pronunciation_rows(db_pool, committed_session.session_id) == []


# ⑦ PS8 — 스텁 모드는 발음 행을 만들지 않는다. 스텁 화면 판정(1·2차수 C2)이 바뀌면 안 된다
async def test_stub_mode_produces_no_pronunciation_rows(db_pool, committed_session):
    client = FakeClient()

    await asyncio.wait_for(
        _runner(StubVoiceAdapter(), db_pool, committed_session.session_id, client).run(),
        timeout=10.0,
    )

    assert await _pronunciation_rows(db_pool, committed_session.session_id) == []
    assert client.of_type("pronunciation") == []
