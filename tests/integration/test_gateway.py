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
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any, cast
from uuid import UUID, uuid4

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
    SessionCommandEvent,
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
from app.models.plan import InstructionFocus, PlanQuestion, SessionInstruction
from app.models.scenario import SessionScenario
from app.services.recordings import (
    ShadowingClip,
    ShadowingTurns,
    recording_dir,
    recording_path,
    recording_url,
)

# 연결 타임아웃 주입값. 실시간 대기 금지 — 무응답 경로도 0.1초 안에 판정된다.
FAST_CONNECT_TIMEOUT = 0.1
# 드레인 데드라인 주입값. 어댑터가 스트림을 닫지 않는 대역(`hold_open=True`)에서
# 종료 경로를 보는 테스트는 데드라인 자체가 관심사가 아니라, 기다릴 이유가 없다.
FAST_DRAIN_TIMEOUT = 0.05


def _settings(*, voice_adapter: str, **overrides) -> Settings:
    """자격증명·DSN을 실제로 쓰지 않는 Settings 인스턴스 (팩토리 분기 검증용).

    ⛔ `_env_file=None` — 이것 없이는 `app/backend/.env`가 이 인스턴스를 먹인다 (TASK-35).
    `env_file=".env"`는 **프로세스 cwd 기준**이고 게이트는 `app/backend`에서 돌며 그 파일이
    실재한다. ⚠️ `.env.example` 첫 줄이 *"Copy this file to app/backend/.env"*이므로
    **표준 온보딩이 그 창을 연다.**
    """
    return Settings(
        # `ty`(alpha)는 pydantic-settings가 런타임에 합성하는 `__init__`을 모델링하지
        # 못한다 — 같은 이유의 억제가 이 리포에 이미 있다(`missing-argument`).
        _env_file=None,  # ty: ignore[unknown-argument]
        database_url="postgresql://unused/unused",
        aws_region="us-west-2",
        voice_adapter=voice_adapter,
        **overrides,
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
        # 결정 118 — 게이트웨이가 「실행했는가」를 보고한 내역.
        self.outcomes: list[tuple[str, bool, str | None]] = []

    async def start(self) -> None:
        if self.start_error is not None:
            raise self.start_error

    async def send_audio(self, frame: bytes) -> None:
        self.frames.append(frame)

    async def report_command_outcome(
        self, tool_use_id: str, *, executed: bool, reason: str | None = None
    ) -> None:
        """게이트웨이의 실행 보고를 **기록한다** (결정 118) — 단정이 이 목록을 읽는다."""
        self.outcomes.append((tool_use_id, executed, reason))

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

    async def report_command_outcome(
        self, tool_use_id: str, *, executed: bool, reason: str | None = None
    ) -> None:
        await self._inner.report_command_outcome(tool_use_id, executed=executed, reason=reason)

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


# ── 쉐도잉 낭독 턴 (`TASK-45` · 설계서 §12 요구 4·5 · 캡틴 결정 35) ────────────────
#
# ⛔ **여기서 만드는 것은 신호를 「받는 쪽」뿐이다.** 어느 화면·어느 버튼이 그 신호를 보내는지는
# `TASK-10` 이 소유한다(결정 35 의 팀리드 제약) — `start_shadowing_session` 이 호출 표면을 갖지
# 않은 것과 같은 형태다.
#
# ⚠️ **낭독 프레임을 어댑터로 보내지 않는 것이 핵심 판단이다.** 쉐도잉은 학습자가 **주어진
# 문장**을 따라 읽는 것이라 전사가 필요 없고, Nova 로 보내면 그 전사가 `learning` 발화로 저장되어
# **학습자가 짓지 않은 문장이 오류 패턴을 오염시킨다** — 설계서 §4.1 이 `utterance_type` 을 나눈
# 목적이 정확히 그것이다.

SHADOWING_TRANSCRIPT = "I usually wake up at seven."


class AudioSpyAdapter:
    """픽스처 스텁을 감싸 **어댑터로 넘어간 프레임만** 기록한다 (낭독 분기 단정용)."""

    def __init__(self) -> None:
        self.frames: list[bytes] = []
        self._inner = StubVoiceAdapter()

    async def start(self) -> None:
        await self._inner.start()

    async def send_audio(self, frame: bytes) -> None:
        self.frames.append(frame)
        await self._inner.send_audio(frame)

    async def report_command_outcome(
        self, tool_use_id: str, *, executed: bool, reason: str | None = None
    ) -> None:
        await self._inner.report_command_outcome(tool_use_id, executed=executed, reason=reason)

    def events(self) -> AsyncIterator[AdapterEvent]:
        return self._inner.events()

    async def close(self) -> None:
        await self._inner.close()


def _shadowing_turns(root: Path, **kw: Any) -> ShadowingTurns:
    clip = ShadowingClip(
        id=uuid4(),
        source_title="A morning routine before work",
        transcript=SHADOWING_TRANSCRIPT,
        clip_start_sec=Decimal("0.00"),
        clip_end_sec=Decimal("30.00"),
        # 기본을 `True` 로 둔다 — 시드 클립이 오디오를 갖게 된 뒤(`TASK-66`)의 정상 상태다.
        # 뒤집어 재려면 `_shadowing_turns(root, has_audio=False)` 로 준다.
        has_audio=kw.get("has_audio", True),
    )
    return ShadowingTurns(
        clip=clip,
        audio_root=root,
        playback_rate=kw.get("playback_rate", 1.0),
        repeat_count=kw.get("repeat_count", 1),
    )


async def test_session_started_carries_the_clip_and_the_settings(
    db_pool, committed_session, tmp_path: Path
):
    """요구 5 — 화면은 **전달만** 받는다. 값의 정본은 `shadowing_items` 와 `Settings` 다."""
    turns = _shadowing_turns(tmp_path, playback_rate=1.5, repeat_count=3)
    client = FakeClient(None)

    await asyncio.wait_for(
        _runner(
            StubVoiceAdapter(), db_pool, committed_session.session_id, client, shadowing=turns
        ).run(),
        timeout=5.0,
    )

    started = client.sent[0]
    assert started["type"] == "session_started"
    assert started["shadowing"] == {
        "item_id": str(turns.clip.id),
        "source_title": "A morning routine before work",
        "transcript": SHADOWING_TRANSCRIPT,
        "clip_start_sec": 0.0,
        "clip_end_sec": 30.0,
        "playback_rate": 1.5,
        "repeat_count": 3,
        # `TASK-66` — 소리가 있는가. ⛔ 파일명은 실리지 않는다(경로는 서버의 것이다).
        "has_audio": True,
    }


async def test_session_started_omits_shadowing_for_a_speaking_session(db_pool, committed_session):
    """⛔ 말하기 세션에는 **키 자체를 넣지 않는다** — 이 리포의 기존 규약과 같다.

    `corrections`·`drill` 이 `None` 일 때 키를 지우는 것과 같은 형태다(`api/results.py`): 없는
    것과 「비었다」를 프론트가 구분해야 한다.
    """
    client = FakeClient(None)

    await asyncio.wait_for(
        _runner(StubVoiceAdapter(), db_pool, committed_session.session_id, client).run(),
        timeout=5.0,
    )

    assert "shadowing" not in client.sent[0]


async def test_a_shadowing_turn_stores_the_recording_and_its_pointer(
    db_pool, committed_session, tmp_path: Path
):
    """요구 4 + AC#3 의 1단계 — 턴 경계가 파일 수명을 정한다.

    턴이 닫히면 §4.5 의 3·4 가 이어 돌아 **`utterances` 행 + `audio_url` + 파일**이 생긴다.
    전사문은 **클립의 것**이다: 학습자가 지은 문장이 아니므로 새로 전사하지 않는다.
    """
    frame = b"\x11\x22" * 160
    encoded = base64.b64encode(frame).decode()
    client = FakeClient(
        {"type": "shadowing_turn_start"},
        {"type": "audio", "data": encoded},
        {"type": "shadowing_turn_end"},
        None,
    )
    turns = _shadowing_turns(tmp_path)

    await asyncio.wait_for(
        _runner(
            StubVoiceAdapter(), db_pool, committed_session.session_id, client, shadowing=turns
        ).run(),
        timeout=5.0,
    )

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "select id, transcript, audio_url from utterances "
            "where session_id = $1 and utterance_type = 'shadowing_recording'",
            committed_session.session_id,
        )
    assert row is not None, "낭독 턴이 닫혔는데 발화 행이 없다"
    assert row["transcript"] == SHADOWING_TRANSCRIPT
    assert row["audio_url"] == recording_url(committed_session.session_id, row["id"])
    stored = recording_path(tmp_path, committed_session.session_id, row["id"])
    assert stored.read_bytes() == frame
    assert list(recording_dir(tmp_path, committed_session.session_id).glob("*.part")) == []


async def test_shadowing_frames_do_not_reach_the_voice_adapter(
    db_pool, committed_session, tmp_path: Path
):
    """⛔ **낭독 프레임을 Nova 로 보내지 않는다.**

    보내면 그 전사가 `learning` 발화로 저장되어 **학습자가 짓지 않은 문장이 오류 패턴을
    오염시킨다** — 설계서 §4.1 이 `utterance_type` 을 나눈 목적이 그것이다. 대화 오디오는
    그대로 어댑터로 가야 하므로 **분기의 양쪽**을 함께 잰다.
    """
    shadowed = base64.b64encode(b"\x33\x44" * 160).decode()
    spoken = base64.b64encode(b"\x55\x66" * 160).decode()
    client = FakeClient(
        {"type": "shadowing_turn_start"},
        {"type": "audio", "data": shadowed},
        {"type": "shadowing_turn_end"},
        {"type": "audio", "data": spoken},
        None,
    )
    adapter = AudioSpyAdapter()

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            client,
            shadowing=_shadowing_turns(tmp_path),
        ).run(),
        timeout=5.0,
    )

    assert adapter.frames == [b"\x55\x66" * 160], "낭독 프레임이 어댑터로 새어 나갔다"


async def test_a_failed_recording_save_does_not_kill_the_session(
    db_pool, committed_session, tmp_path: Path, monkeypatch
):
    """⛔ **저장 실패가 세션을 죽이지 않는다** — 같은 모듈의 다른 실패 경로와 같은 규약이다.

    2026-09-09 리뷰가 이 경로만 갈라져 있던 것을 잡았다: DB 실패가 클라이언트 펌프를 죽여
    **세션이 `session_ended` 없이 사라졌다.** `_record_pronunciation`·`_flush_analysis` 는 정반대로
    정해 두고 근거까지 적어 뒀는데 낭독만 예외였다. 녹음 1건을 잃는 것이 대화를 끊는 것보다 낫고,
    남은 `.part` 는 2다리가 걷는다.
    """

    async def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("포인터 UPDATE 실패")

    monkeypatch.setattr(session_module, "finalize_recording", boom)
    encoded = base64.b64encode(b"\x99\xaa" * 160).decode()
    client = FakeClient(
        {"type": "shadowing_turn_start"},
        {"type": "audio", "data": encoded},
        {"type": "shadowing_turn_end"},
        None,
    )

    await asyncio.wait_for(
        _runner(
            StubVoiceAdapter(),
            db_pool,
            committed_session.session_id,
            client,
            shadowing=_shadowing_turns(tmp_path),
        ).run(),
        timeout=5.0,
    )

    assert client.types[-1] == "session_ended", "녹음 저장 실패가 세션을 통째로 죽였다"


async def test_frames_are_dropped_not_forwarded_when_the_file_cannot_be_opened(
    db_pool, committed_session, tmp_path: Path
):
    """⛔ **파일을 열 수 없어도 낭독 프레임이 어댑터로 새지 않는다.**

    2026-09-09 리뷰가 `mkdir`/`open` 의 `OSError` 가 세션을 죽이던 것을 잡았다. 그런데 단순히
    삼키고 턴을 열지 않으면 **더 나쁜 상태**가 된다: 이후 프레임이 어댑터로 흘러 낭독이 Nova 에
    들어가고 그 전사가 `learning` 발화로 저장돼 오류 패턴을 오염시킨다(§4.1). 그래서 「턴은 열려
    있고 바이트는 쓸 수 없다」(`handle=None`)를 표현하고 프레임을 **버린다.**

    여기서는 `audio_root` 자리에 **파일**을 둬서 `mkdir` 을 실패시킨다 — 권한 문제를 흉내내는
    가장 값싼 방법이다.
    """
    blocked_root = tmp_path / "root-is-a-file"
    blocked_root.write_text("디렉터리가 아니라 파일이다")
    adapter = AudioSpyAdapter()
    encoded = base64.b64encode(b"\xbb\xcc" * 160).decode()
    client = FakeClient(
        {"type": "shadowing_turn_start"},
        {"type": "audio", "data": encoded},
        {"type": "shadowing_turn_end"},
        None,
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            client,
            shadowing=_shadowing_turns(blocked_root),
        ).run(),
        timeout=5.0,
    )

    assert adapter.frames == [], "파일을 못 열자 낭독 프레임이 Nova 로 새어 나갔다"
    assert client.types[-1] == "session_ended", "파일 열기 실패가 세션을 죽였다"
    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select count(*) from utterances where session_id = $1 "
            "and utterance_type = 'shadowing_recording'",
            committed_session.session_id,
        )
    assert stored == 0, "저장된 바이트가 없는데 발화 행이 생겼다 — 비교할 수 없는 낭독이 남는다"


async def test_a_turn_left_open_is_abandoned_with_a_warning(
    db_pool, committed_session, tmp_path: Path, caplog: pytest.LogCaptureFixture
):
    """⛔ **`_abandon_open_recording_turn` 을 재는 유일한 단정이다.**

    2026-09-09 리뷰가 그 줄을 지워도 스위트가 전부 통과함을 확인했다 — 낭독 턴을 쓰는 단정이
    둘뿐이었고 **둘 다 `start`→`end` 짝을 맞춰 보냈기** 때문이다. 실물에서는 학습자가 낭독 중에
    창을 닫는 것이 정상 경로다.

    재는 것은 셋: `.part` 가 남는다(2다리가 걷을 대상) · **발화 행을 만들지 않는다**(끝났다는
    신호가 없으므로 완성된 녹음인지 알 수 없다) · **경고가 남는다**(그것이 이 상태의 유일한 신호다).
    """
    encoded = base64.b64encode(b"\x77\x88" * 160).decode()
    client = FakeClient(
        {"type": "shadowing_turn_start"},
        {"type": "audio", "data": encoded},
        None,  # 낭독 중에 끊긴다 — `turn_end` 가 오지 않는다
    )

    with caplog.at_level("WARNING"):
        await asyncio.wait_for(
            _runner(
                StubVoiceAdapter(),
                db_pool,
                committed_session.session_id,
                client,
                shadowing=_shadowing_turns(tmp_path),
            ).run(),
            timeout=5.0,
        )

    leftovers = list(recording_dir(tmp_path, committed_session.session_id).glob("*.pcm.part"))
    assert len(leftovers) == 1, "열린 채 끝난 턴의 `.part` 가 남지 않았다"
    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select count(*) from utterances where session_id = $1 "
            "and utterance_type = 'shadowing_recording'",
            committed_session.session_id,
        )
    assert stored == 0, "끝났다는 신호가 없는데 발화 행이 생겼다"
    assert "낭독 턴이 열린 채" in caplog.text


async def test_a_duplicate_turn_start_does_not_discard_the_bytes_so_far(
    db_pool, committed_session, tmp_path: Path
):
    """⛔ 중복 `start` 를 삼키는 판단을 재는 단정이다 (2026-09-09 리뷰가 미검증으로 지목).

    새로 열면 앞서 쓴 바이트가 고아 `.part` 로 버려진다 — **클라이언트의 신호 중복만으로 학습자의
    낭독을 잃는 것**이다. 재는 방법: 두 번 열고 프레임을 보낸 뒤 닫아서, `.part` 가 하나도 남지
    않고(두 번째 턴이 만들어지지 않았다) 저장된 바이트가 **두 프레임 전부**인지 본다.
    """
    first = base64.b64encode(b"\x01\x02" * 160).decode()
    second = base64.b64encode(b"\x03\x04" * 160).decode()
    client = FakeClient(
        {"type": "shadowing_turn_start"},
        {"type": "audio", "data": first},
        {"type": "shadowing_turn_start"},  # 중복 — 무해하게 삼켜야 한다
        {"type": "audio", "data": second},
        {"type": "shadowing_turn_end"},
        None,
    )

    await asyncio.wait_for(
        _runner(
            StubVoiceAdapter(),
            db_pool,
            committed_session.session_id,
            client,
            shadowing=_shadowing_turns(tmp_path),
        ).run(),
        timeout=5.0,
    )

    async with db_pool.acquire() as conn:
        utterance_id = await conn.fetchval(
            "select id from utterances where session_id = $1 "
            "and utterance_type = 'shadowing_recording'",
            committed_session.session_id,
        )
    assert utterance_id is not None
    stored = recording_path(tmp_path, committed_session.session_id, utterance_id)
    assert stored.read_bytes() == b"\x01\x02" * 160 + b"\x03\x04" * 160
    assert list(recording_dir(tmp_path, committed_session.session_id).glob("*.part")) == []


async def test_turn_signals_in_a_speaking_session_are_ignored(
    db_pool, committed_session, caplog: pytest.LogCaptureFixture
):
    """⛔ **말하기 세션에 낭독 턴 신호가 오는 것은 실물에서 도달 가능한 경로다.**

    프론트가 그 메서드를 갖고 있고 어느 화면이 부르는지는 `TASK-10` 이 정하므로, 모드 없이 붙은
    연결에 신호가 올 수 있다. 가드가 없으면 `self._shadowing.audio_root` 에서 `AttributeError` 가
    나 **세션이 통째로 죽는다.** 2026-09-09 리뷰가 이 경로의 미검증을 지목했다.
    """
    client = FakeClient(
        {"type": "shadowing_turn_start"},
        {"type": "shadowing_turn_end"},
        None,
    )

    with caplog.at_level("WARNING"):
        await asyncio.wait_for(
            _runner(StubVoiceAdapter(), db_pool, committed_session.session_id, client).run(),
            timeout=5.0,
        )

    assert client.types[-1] == "session_ended", "낭독 턴 신호가 말하기 세션을 죽였다"
    assert "쉐도잉 세션이 아닌데" in caplog.text


# ① 픽스처 완주 → 사용자 final 3행 + job 3건 (G4)
#
# ✅ **뮤테이션 KILL 확인 — G4** (`TASK-73` · 결정 48. 2026-09-10 직접 관측).
# `audio_gateway/session._flush_analysis` 의 본문 앞에 `if True: return` 을 넣어 job 등록을 통째로
# 건너뛰게 하니 **2건이 FAIL** 했다: 이 테스트와 `test_ws.py` 의
# `..._ws_session_stores_user_finals_and_enqueues_jobs`. 후자가 `assert 0 == 3` 으로 떨어졌다.
# ⚠️ 두 계층(러너·소켓)이 같은 변이에 함께 반응한다 — G4 가 한 계층만 지키는 단정이 아니다.
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


# ⛔ **연결 뒤에 어댑터가 터지면 세션은 `failed`다 — `completed`가 아니다** (G2 · 2026-09-09
# codex 리뷰 HIGH). 이전 판은 `finally`가 무조건 `completed`를 기록해서 **실제 연결 장애가
# 정상 종료로 남았다**. 그러면 결과 조회의 R2 우선순위가 `connection_failed`에 걸리지 못하고
# `final`이나 `no_utterances`로 떨어져 **학습자가 장애를 성공으로 본다**.
# ⚠️ **`active` 고아를 막는 원래 의도는 그대로다** — 닫는 것은 여전히 닫고 상태만 사실에 맞춘다.
# ⚠️ flush 실패와 구별한다: `_flush_analysis`는 예외를 삼켜 `_relay()`가 터지지 않으므로 그 경로는
# `completed`가 맞다(바로 아래 T3 테스트가 그것을 고정한다).
async def test_an_adapter_error_after_connect_records_the_session_as_failed(
    db_pool, committed_session
):
    class ExplodingAdapter:
        """연결은 성공하고 **이벤트 스트림에서** 터진다 — Phase 2의 스트림 중단 모양이다."""

        def __init__(self) -> None:
            self.closed = False

        async def start(self) -> None:
            return None

        async def events(self):
            yield TranscriptEvent(kind="final", text="i went to gym.", speaker="user")
            raise RuntimeError("injected adapter stream failure")

        async def send_audio(self, frame: bytes) -> None:
            return None

        async def close(self) -> None:
            self.closed = True

    adapter = ExplodingAdapter()
    client = FakeClient()

    with pytest.raises(RuntimeError, match="injected adapter stream failure"):
        await asyncio.wait_for(
            _runner(
                cast(VoiceAdapter, adapter), db_pool, committed_session.session_id, client
            ).run(),
            timeout=5.0,
        )

    session = await _session_row(db_pool, committed_session.session_id)
    assert session["status"] == "failed", "실행 중 어댑터 오류가 정상 종료로 기록됐다"
    assert session["ended_at"] is not None, "세션이 active 고아로 남았다"
    assert adapter.closed, "어댑터 정리를 건너뛰었다"
    assert "session_ended" not in client.types, "장애인데 정상 종료 이벤트를 보냈다"


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
#
# ✅ **뮤테이션 KILL 확인 — G2** (`TASK-73`. 2026-09-10 직접 관측).
# `TimeoutError` 핸들러의 `return CONNECT_TIMEOUT_REASON` 을 `return None` 으로 바꿔 **타임아웃을
# 실패로 보고하지 않게** 하니 이 테스트가 FAIL 했다.
# ⛔ **`wait_for` 자체를 제거하는 변이는 쓰지 않았다** — 이 리포에 `pytest-timeout` 이 없어서 무한
# 대기가 그대로 테스트를 매달리게 한다. 그 회차 로그에서 주입 타임아웃이 **0.1초**로 확인됐고
# (무응답 스텁은 영원히 응답하지 않는다) 그 판단이 맞았다. 변이는 「감지」가 아니라 「보고」를 끊는
# 쪽으로 골랐고, 그것으로도 이 단정이 반응한다.
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
#
# ✅ **뮤테이션 KILL 확인 — G1** (`TASK-73`. 2026-09-10 직접 관측).
# `_close_and_record` 의 종료 기록 블록(`end_session` + `resolve_dangling`)을 `adapter.close()`
# **앞으로 옮기니** 이 테스트가 FAIL 했다 — 실패 메시지가 `At index 0 diff: 'session.end_record'
# != 'adapter.close'` 로, 순서 자체를 잡는다는 것이 그 출력에 그대로 드러난다.
# ⚠️ 「close 를 아예 부르지 않는」 변이가 아니라 **순서만 바꾼** 변이를 골랐다 — 전자는 「호출
# 여부」를 재고 G1 이 요구하는 것은 순서다.
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


# ⛔ **배선 가드 — 호출 여부가 아니라 «순서»를 잰다** (`TASK-116.1` · 사용자 결정 82).
#
# `check_recorded_sounds` 는 `resolve_dangling` **뒤**에 와야 한다: 그 함수가 남은 `pending` 을
# `incorrect` 로 수렴시키므로 먼저 부르면 **수렴된 행이 판정을 못 받는다.** 그것은 「대답 없이 끝난
# 시도」이고 어긋난 키를 담을 수 있으므로 빠뜨리면 이 변경이 절반만 돈다.
# ⚠️ 「호출 여부」만 재면 **순서를 뒤집는 변이가 통과한다** — 바로 위 G1 가드가 같은 이유로 순서를
# 골랐고 그 판단을 그대로 쓴다.
async def test_the_sound_check_pass_runs_after_the_pending_convergence(
    db_pool, committed_session, monkeypatch: pytest.MonkeyPatch
):
    calls: list[str] = []
    original_resolve = session_module.resolve_dangling
    original_check = session_module.check_recorded_sounds

    async def resolve_spy(conn: asyncpg.Connection, session_id: UUID) -> int:
        calls.append("resolve_dangling")
        return await original_resolve(conn, session_id)

    async def check_spy(conn: asyncpg.Connection, session_id: UUID) -> int:
        calls.append("check_recorded_sounds")
        return await original_check(conn, session_id)

    monkeypatch.setattr(session_module, "resolve_dangling", resolve_spy)
    monkeypatch.setattr(session_module, "check_recorded_sounds", check_spy)

    await asyncio.wait_for(
        _runner(ScriptedAdapter(), db_pool, committed_session.session_id, FakeClient()).run(),
        timeout=5.0,
    )

    assert calls == ["resolve_dangling", "check_recorded_sounds"]


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
    adapter = create_voice_adapter(_settings(voice_adapter=setting), questions=(), scenario=None)

    assert isinstance(adapter, StubVoiceAdapter)
    assert adapter.mode == expected_mode


# Nova 실연동(3차수). 분기는 이 함수 한 곳에만 있다 (G3) — 팩토리는 어댑터를 만들 뿐
# 스트림을 열지 않으므로, 이 테스트는 자격증명·네트워크를 만지지 않는다.
def test_factory_builds_the_nova_adapter():
    adapter = create_voice_adapter(
        _settings(voice_adapter=NOVA_ADAPTER), questions=(), scenario=None
    )

    assert isinstance(adapter, NovaVoiceAdapter)


# `TASK-124`(결정 68) — 팩토리→어댑터 구간의 배선. ⚠️ **이 구간이 무보호였다**: 팩토리에서
# `usage_sink` 인자를 떼는 뮤테이션에서 138건이 전부 초록이었다(2026-09-12 직접 확인).
def test_factory_hands_the_usage_sink_to_the_nova_adapter():
    async def sink(*_: object, **__: object) -> None:
        return None

    adapter = create_voice_adapter(
        _settings(voice_adapter=NOVA_ADAPTER), questions=(), scenario=None, usage_sink=sink
    )

    assert isinstance(adapter, NovaVoiceAdapter)
    assert adapter.records_usage is True


def test_the_nova_adapter_records_nothing_when_the_factory_gets_no_sink():
    """⚠️ 음성 케이스 — 없으면 「항상 기록」으로 바꿔도 위 테스트가 통과한다."""
    adapter = create_voice_adapter(
        _settings(voice_adapter=NOVA_ADAPTER), questions=(), scenario=None
    )

    assert isinstance(adapter, NovaVoiceAdapter)
    assert adapter.records_usage is False


def test_the_stub_never_gets_a_usage_sink():
    """⛔ 스텁은 토큰을 쓰지 않는다 — 행을 만들면 「쓰지 않은 비용」을 발명한다.

    스텁에 그 개념이 아예 없다는 것을 이 자리에서 못 박는다: 나중에 스텁이 sink 를 받게 되면
    이 단정이 깨지고, 그때 「왜 안 되는가」를 다시 읽게 된다.
    """

    async def sink(*_: object, **__: object) -> None:
        return None

    adapter = create_voice_adapter(
        _settings(voice_adapter=STUB_ADAPTER), questions=(), scenario=None, usage_sink=sink
    )

    assert isinstance(adapter, StubVoiceAdapter)
    assert not hasattr(adapter, "records_usage")


def test_factory_rejects_an_unknown_adapter():
    # 오타를 조용히 스텁으로 흘리면 "실물이라 믿었던 세션이 픽스처였다"가 된다.
    with pytest.raises(ValueError, match="voice_adapter"):
        create_voice_adapter(_settings(voice_adapter="novva"), questions=(), scenario=None)


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
        _settings(voice_adapter=NOVA_ADAPTER),
        known_sounds=["th_as_s", "f_as_p"],
        questions=(),
        scenario=None,
    )

    assert isinstance(adapter, NovaVoiceAdapter)
    sounds = _sounds_section(adapter.instructions)
    assert "th_as_s" in sounds
    assert "f_as_p" in sounds


# 목록을 주지 않으면 기본 문구다 — dev DB의 현재 상태(기록 0건)가 이 경로다.
def test_factory_uses_the_base_prompt_when_there_are_no_known_sounds():
    adapter = create_voice_adapter(
        _settings(voice_adapter=NOVA_ADAPTER), questions=(), scenario=None
    )

    assert isinstance(adapter, NovaVoiceAdapter)
    assert adapter.instructions == SYSTEM_PROMPT


# PS8(스텁 무손상) — 스텁도 조립된 지시문을 **받는다**(Task 10). 다만 보관만 하므로
# 모드가 그대로여야 1·2차수 판정이 재현된다. 지시문을 받는 이유는 AS6 판정 수단이
# 그것뿐이기 때문이다(아래 `test_factory_puts_the_plan_into_the_stub_instructions`).
def test_factory_gives_the_stub_the_instructions_without_changing_its_mode():
    adapter = create_voice_adapter(
        _settings(voice_adapter=STUB_ADAPTER),
        known_sounds=["th_as_s"],
        questions=(),
        scenario=None,
    )

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
    adapter = create_voice_adapter(
        _settings(voice_adapter=NOVA_ADAPTER),
        plan=_plan_instruction(),
        questions=(),
        scenario=None,
    )

    assert isinstance(adapter, NovaVoiceAdapter)
    assert adapter.instructions != SYSTEM_PROMPT
    assert "a/an/the" in adapter.instructions
    assert "weekend plan" in adapter.instructions


# AS6 — 전달 경로가 관통했는지 판정할 수단이 스텁의 보관값뿐이다.
# ⚠️ **`is not None`으로 끝내지 않는다.** Nova 는 `instructions or SYSTEM_PROMPT`로 falsy 를
# 강제하므로 빈 조립이 조용히 폴백되고, 스텁은 `""`를 그대로 기록한다 — non-None 단정은
# "지시문이 도달했다"가 아니라 "생성자가 인자를 받았다"만 증명한다(S2-9 리뷰 인계 1).
def test_factory_puts_the_plan_into_the_stub_instructions():
    adapter = create_voice_adapter(
        _settings(voice_adapter=STUB_ADAPTER),
        plan=_plan_instruction(),
        questions=(),
        scenario=None,
    )

    assert isinstance(adapter, StubVoiceAdapter)
    instructions = adapter.instructions
    assert instructions is not None
    assert "a/an/the" in instructions
    assert "weekend plan" in instructions


# --- TASK-25 Batch B: 무대·질문도 같은 통로로 간다 (설계서 §2.1) ---
#
# 조립 **문구**는 `tests/unit/test_nova.py`가 소유한다. 여기서 재는 것은 팩토리가 그 재료를
# 조립기까지 **넘기는가**다: 넘기지 않으면 조립기 테스트는 전부 초록인데 실제 세션은 고정
# 문구로 시작한다 — 그것이 이 배치가 메우는 공백의 모양 그대로다.


def _drill_questions(count: int = 3) -> list[PlanQuestion]:
    """`SYSTEM_PROMPT`·`_plan_instruction()`과 겹치지 않는 값만 쓴다 — 겹치면 항진명제가 된다."""
    return [
        PlanQuestion(prompt=f"Gateway drill {index}?", context=f"gateway context {index}")
        for index in range(1, count + 1)
    ]


def _listed_drills(instructions: str) -> list[str]:
    return [line for line in instructions.splitlines() if "Gateway drill" in line]


def _stage() -> SessionScenario:
    return SessionScenario(
        title="Tonight's plans at home",
        prompt_template="You are a housemate talking with the learner about tonight.",
    )


def test_factory_puts_the_scenario_and_the_questions_into_the_nova_instructions():
    adapter = create_voice_adapter(
        _settings(voice_adapter=NOVA_ADAPTER),
        plan=_plan_instruction(),
        questions=_drill_questions(),
        scenario=_stage(),
    )

    assert isinstance(adapter, NovaVoiceAdapter)
    assert "You are a housemate talking with the learner about tonight." in adapter.instructions
    assert "Gateway drill 1?" in adapter.instructions
    # 규칙 6 — 화면용 라벨은 지시문에 실리지 않는다. 팩토리가 `SessionScenario`를 통째로
    # 문자열화하는 구현에서 이 단정이 걸린다.
    assert "at home" not in adapter.instructions


def test_factory_puts_the_scenario_and_the_questions_into_the_stub_instructions():
    adapter = create_voice_adapter(
        _settings(voice_adapter=STUB_ADAPTER),
        plan=_plan_instruction(),
        questions=_drill_questions(),
        scenario=_stage(),
    )

    assert isinstance(adapter, StubVoiceAdapter)
    instructions = adapter.instructions
    assert instructions is not None
    assert "You are a housemate talking with the learner about tonight." in instructions
    assert "Gateway drill 1?" in instructions


# ⛔ 설정값 둘이 **팩토리를 지나 문구까지** 간다 — 조립기는 전역(`get_settings()`)을 읽지 않고
# 인자로 받는다. 그래서 이 경로가 끊기면 설정값이 아무것도 바꾸지 않는다(캡틴 결정 1이 요구한
# "읽는다"가 죽는다). 기본값(`drill_turns_min=4`·`drill_count=**5**` — 캡틴 결정 17)과 **다른 값**을
# 줘야 판별력이 있다. 아래가 `7`·`1`이라 둘 다 기본값과 다르다.
def test_factory_forwards_the_drill_settings_to_the_assembled_prompt():
    # `_settings`를 넓히지 않고 여기서 직접 만든다 — 드릴 설정값을 쓰는 테스트가 이 하나뿐이다.
    settings = Settings(
        database_url="postgresql://unused/unused",
        aws_region="us-west-2",
        voice_adapter=NOVA_ADAPTER,
        drill_count=1,
        drill_turns_min=7,
    )

    adapter = create_voice_adapter(
        settings, plan=_plan_instruction(), questions=_drill_questions(), scenario=None
    )

    assert isinstance(adapter, NovaVoiceAdapter)
    flowed = " ".join(adapter.instructions.split())
    assert "at least 7 exchanges" in flowed, "`drill_turns_min`이 문구까지 가지 않았다"
    assert "Gateway drill 1?" in adapter.instructions
    assert "Gateway drill 2?" not in adapter.instructions, "`drill_count`가 열거를 줄이지 않았다"


# ⛔ **캡틴 결정 2의 회귀 방어** (캡틴 결정 17). 결정 2는 *"계획이 만든 질문 3~5개를 대화 상대에게
# 전달한다"*인데, `drill_count` 기본값이 `3`이던 동안에는 지시문이 `questions[:3]`만 열거해
# **질문 4~5개인 계획의 질문이 대화에 도달하지 않았다.** 기본값 5는
# `session_plans.questions`의 CHECK 상한(`007:42-43`)과 같아 기본 설정에서 절단이 원리적으로
# 일어나지 않는다.
# ⚠️ **`drill_count`를 명시하지 않는 것이 이 테스트의 요점이다** — 재려는 것이 `Settings`의
# **기본값**이 실제로 대화에 닿는지이므로, 값을 주면 위 테스트와 같은 것을 두 번 재게 된다.
# ⚠️ H-5 tripwire는 그대로 살아 있다 — 「질문 5개·`drill_count=3`이면 3개만 열거」는
# `tests/unit/test_nova.py`가 값을 **명시 주입**해 계속 단정한다.
# ⛔ **주변 환경 격리가 이 테스트의 전제조건이다** (TASK-35). 값을 주지 않는 것이 요점이라
# **주변 환경이 그 자리를 대신 채울 수 있다** — 창이 둘이고 `_settings`의 `_env_file=None`이
# `.env`를, 아래 `delenv`가 셸을 닫는다. 실측(2026-09-08): `DRILL_COUNT=3`으로 이 테스트를
# 돌리면 열거가 3개로 줄어 **red 가 났다.** ⚠️ 그때 `.env`에 `DRILL_COUNT=9`를 넣은 실험은
# **통과했다 — 9 > 5라서 운으로 통과한 것**이고 창이 닫혀 있다는 증거가 아니었다.
def test_the_default_drill_count_lists_every_question_a_plan_can_carry(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("DRILL_COUNT", raising=False)
    adapter = create_voice_adapter(
        _settings(voice_adapter=NOVA_ADAPTER),
        plan=_plan_instruction(),
        questions=_drill_questions(5),
        scenario=None,
    )

    assert isinstance(adapter, NovaVoiceAdapter)
    assert len(_listed_drills(adapter.instructions)) == 5, (
        "기본 설정에서 질문 5개가 전부 열거되지 않았다 — 결정 2가 다시 덮였다"
    )


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


# ✅ **뮤테이션 KILL 확인 — G3** (`TASK-73`. 2026-09-10 직접 관측).
# `audio_gateway/session.py` 에 `from app.audio_gateway.nova import SYSTEM_PROMPT` 를 넣고 그 값을
# 모듈 상수에 대입하니 아래 nova 판정이 **`[session]` 파라미터에서만** FAIL 했다(`ws` 는 통과).
# 즉 이 단정이 모듈별로 정확히 나뉘어 반응한다 — 한 모듈의 오염이 다른
# 모듈 이름으로 보고되지 않는다.
# ⚠️ import 그래프 단정은 **소스 텍스트를 읽는** 방식이라 런타임 뮤테이션으로는 재지 못한다. 변이를
# import 문 자체로 준 것이 그 이유다.
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
#
# ⚠️ **행 수 단정이 둘에서 하나로 바뀌었다** (`TASK-125`). 이 대본이 바로 그 결함의 봉투다 —
# 두 호출이 모두 `pending` 이고 판정이 오지 않는다. 이제 둘째 pending 이 열린 행에 **접히므로**
# 한 코칭 사건이 행 하나가 된다(그 전에는 둘이었고 화면에 카드가 두 장 떴다).
# ⛔ **재는 축은 그대로다** — 「대답 없이 끝나면 `incorrect`」와 「`spoken_form` 을 비운다」.
# ⚠️ 그리고 접힌 행의 `target_form` 이 **나중 값**임을 함께 잰다 — 그것이 없으면 「접혔지만 옛
# 무너진 전사가 남았다」가 통과한다(그 잔재가 이 결함의 사용자에게 보이는 얼굴이었다).
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
    assert [row["outcome"] for row in rows] == ["incorrect"]
    assert all(row["spoken_form"] is None for row in rows)
    assert rows[0]["target_form"] == "Other sentence."


# ④ 한글 전사문에는 **아무 행도 생기지 않는다** — 보조 신호 경로를 지웠다(`TASK-78.1` · 결정 120)
#
# ⛔ **이 단정이 「지운 상태」를 지킨다.** 이전 판은 같은 입력에 `korean_transcript` 행 1건을
# 단정했고(PS5), 그 감지기가 51세션에서 한 번도 입력을 받지 못해 사용자가 제거를 결정했다.
# 되살리려면 이 단정을 먼저 뒤집어야 한다 — 조용히 되돌아오지 않게 하는 것이 목적이다.
# ⚠️ 저장·job 등록은 **그대로** 일어나야 한다. 감지기를 걷어낸 것이 전사문 경로를 건드리지
# 않았다는 증거가 그 두 줄이다.
async def test_korean_transcript_records_no_pronunciation_row(db_pool, committed_session):
    adapter = ScriptedAdapter(TranscriptEvent(kind="final", text=KOREAN_TRANSCRIPT, speaker="user"))

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, FakeClient()).run(), timeout=5.0
    )

    assert await _pronunciation_rows(db_pool, committed_session.session_id) == []
    assert len(await _utterances(db_pool, committed_session.session_id)) == 1
    assert await _job_count(db_pool, committed_session.session_id) == 1


# ⑦ PS8 — 스텁 모드는 발음 행을 만들지 않는다. 스텁 화면 판정(1·2차수 C2)이 바뀌면 안 된다
async def test_stub_mode_produces_no_pronunciation_rows(db_pool, committed_session):
    client = FakeClient()

    await asyncio.wait_for(
        _runner(StubVoiceAdapter(), db_pool, committed_session.session_id, client).run(),
        timeout=10.0,
    )

    assert await _pronunciation_rows(db_pool, committed_session.session_id) == []
    assert client.of_type("pronunciation") == []


# 발음 전용 모드 (`TASK-10.1` · 사용자 결정 64) — 팩토리가 **다른 지시문**을 조립한다.
#
# ⛔ 형태의 근거는 `nova.PRONUNCIATION_MODE_PROMPT` 위 주석이 소유한다(실측 4/4 대 일반 세션
# 규모 0/76). 여기서 재는 것은 **배선 하나**다: 모드 플래그가 오면 그 지시문이 어댑터까지 가는가.
#
# ⛔ **판정 재료가 결정 72(`TASK-128.2`)로 바뀌었다** — 「소리 키가 오면 그 모드다」에서
# 「`pronunciation_mode` 면 그 모드다」로. 소리는 이제 모드를 여는 조건이 아니라 **후보**다.
def test_factory_builds_the_pronunciation_prompt_when_the_mode_is_asked_for():
    adapter = create_voice_adapter(
        _settings(voice_adapter=STUB_ADAPTER),
        known_sounds=["an_as_a"],
        questions=(),
        scenario=None,
        pronunciation_mode=True,
    )

    assert isinstance(adapter, StubVoiceAdapter)
    instructions = adapter.instructions
    assert instructions is not None
    assert "Pronunciation coaching:" in instructions
    # ⛔ **후보 목록이 전용 지시문까지 도달한다** — 결정 72 이전에는 팩토리가 이 목록을 **뺐고**
    # 그래서 전용 모드에는 소리 재료가 하나도 없었다. 그 자리를 이 단정이 잰다.
    assert "an_as_a" in instructions
    # 전용 모드는 대화 규칙을 싣지 않는다 — 그것이 이 모드의 전부다.
    assert "Ask one question at a time" not in instructions
    assert "Aim for the learner to speak at least 65%" not in instructions


def test_factory_builds_the_pronunciation_prompt_even_without_candidates():
    """⛔ 결정 72 — **소리가 없어도 전용 모드가 열린다.** 그 뜻이 뒤집힌 자리다.

    이전 규약은 「소리를 못 고르면 말하기로 떨어진다」였다. 결정 72 가 전용 모드의 뜻을 「오늘의
    소리를 다룬다」에서 **「발음만 다룬다」**로 바꿨으므로 소리의 유무가 모드를 정하지 않는다.
    """
    adapter = create_voice_adapter(
        _settings(voice_adapter=STUB_ADAPTER),
        known_sounds=[],
        questions=(),
        scenario=None,
        pronunciation_mode=True,
    )

    assert isinstance(adapter, StubVoiceAdapter)
    instructions = adapter.instructions
    assert instructions is not None
    assert "Pronunciation coaching:" in instructions
    assert "Ask one question at a time" not in instructions


def test_factory_keeps_the_speaking_prompt_when_the_mode_is_not_asked_for():
    """⚠️ 음성 케이스 — 인자를 무조건 전용 지시문으로 읽으면 **모든 세션이** 발음 세션이 된다."""
    adapter = create_voice_adapter(
        _settings(voice_adapter=STUB_ADAPTER),
        known_sounds=["an_as_a"],
        questions=(),
        scenario=None,
    )

    assert isinstance(adapter, StubVoiceAdapter)
    instructions = adapter.instructions
    assert instructions is not None
    assert "Ask one question at a time" in instructions


# ⑩ ⛔ **부가 조회 실패가 종료 기록을 되돌리지 않는다** (`TASK-137` · 확정 결함).
#
# **확정 경위**: 발음 축이 두 팔로 갈라 재서 확정했다(2026-09-14) — `sound_check` 컬럼이 있으면
# 세션이 `completed` 로 닫히고, 그 컬럼을 drop 해 019 상태를 재현하면 `UndefinedColumnError` 와 함께
# **세션이 `active`·`ended_at` null 로 남았다.** 기전은 `check_recorded_sounds` 가 종료 기록과 같은
# 트랜잭션에 있고 그 블록에 `try` 가 없다는 것이다.
# ⛔ **020 을 적용해 그 컬럼의 직접 위험은 사라졌지만 구조는 그대로였다** — 그 조회에 어떤 이유로든
# 오류가 나면(스키마 드리프트·일시 장애) 종료 기록이 함께 되돌아간다. 이 단정이 그것을 막는다.
# ⚠️ **`resolve_dangling` 은 트랜잭션 안에 그대로 둔다** — 그것은 종료 «상태»의 일부다(남은
# `pending` 이 학습 계산에 섞이는 것을 막는다는 그 함수의 근거). 부가 기록인 것은
# `check_recorded_sounds`(결정 82 의 어긋남 표시)뿐이고, 그 실패는 복습 큐가 그 행을 유지하는
# **되돌릴 수 있는 상태**로 끝난다 — 반면 종료 기록의 손실은 고아 세션을 만든다.
async def test_a_failing_sound_check_still_records_the_session_end(
    db_pool, committed_session, monkeypatch
):
    async def _boom(*_args: object, **_kwargs: object) -> int:
        raise RuntimeError("sound check exploded")

    # 러너가 부르는 이름을 그 모듈에서 갈아 끼운다 — 서비스 원본을 건드리지 않는다.
    monkeypatch.setattr(session_module, "check_recorded_sounds", _boom)
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="i sent the report.", speaker="user")
    )

    await asyncio.wait_for(
        _runner(adapter, db_pool, committed_session.session_id, FakeClient()).run(),
        timeout=5.0,
    )

    session = await _session_row(db_pool, committed_session.session_id)
    assert session["status"] == "completed", "부가 조회 실패가 종료 기록을 되돌렸다"
    assert session["ended_at"] is not None
    # 전사문도 남는다 — 잃는 것은 어긋남 «표시» 하나뿐이다.
    assert len(await _utterances(db_pool, committed_session.session_id)) == 1


# ── 음성 명령 (`TASK-61.1` · 결정 102) ─────────────────────────────────────────────
#
# ⛔ **닫는 것은 `confirmed` 하나다.** 결정 102 ③이 확인 절차를 요구하므로, `requested` 로 닫히면
# 오인식 한 번이 세션을 끝낸다 — 그것이 이 두 테스트가 반대 방향으로 못 박는 것이다.


async def _typed_utterances(pool: asyncpg.Pool, session_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "select speaker, utterance_type, transcript from utterances "
            "where session_id = $1 order by sequence_no",
            session_id,
        )


async def test_a_confirmed_end_command_closes_the_session(db_pool, committed_session):
    """⚠️ 표지가 든 발화가 **앞에** 있어야 한다 — `TASK-61.4`(사용자 결정 104)가 그 검사를 더했다."""
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Oh My English, end the session.", speaker="user"),
        SessionCommandEvent(command="end", stage="requested"),
        TranscriptEvent(kind="final", text="Yes, end it now.", speaker="user"),
        SessionCommandEvent(command="end", stage="confirmed"),
        hold_open=True,
    )
    client = FakeClient()

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

    assert adapter.closed
    assert client.types[-1] == "session_ended"
    assert (await _session_row(db_pool, committed_session.session_id))["status"] == "completed"
    assert client.of_type("voice_command") == [
        {"type": "voice_command", "command": "end", "stage": "requested"},
        {"type": "voice_command", "command": "end", "stage": "confirmed"},
    ]


async def test_the_confirmation_is_stored_as_a_command_confirmation(db_pool, committed_session):
    """스키마가 `command_confirmation` 을 둔 이유가 오인식 방어의 «기록»이다.

    ⛔ **행이 발화마다 하나여야 한다** (`TASK-61.4` D1·D2). 앞 판은 전사문 경로와 tool 경로가
    각각 적어 같은 발화가 두 행이 됐고, 확인 답이 `learning` 으로도 남아 분석 대상이 됐다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="오마이 잉글리시, 종료할게.", speaker="user"),
        SessionCommandEvent(command="end", stage="requested"),
        TranscriptEvent(kind="final", text="네 종료해 주세요.", speaker="user"),
        SessionCommandEvent(command="end", stage="confirmed"),
        hold_open=True,
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            FakeClient(),
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["speaker"], row["utterance_type"], row["transcript"]) for row in rows] == [
        ("user", "voice_command", "오마이 잉글리시, 종료할게."),
        ("user", "command_confirmation", "네 종료해 주세요."),
    ]


async def test_a_requested_end_command_does_not_close_the_session(db_pool, committed_session):
    """⛔ 확인 전에 닫히면 결정 102 ③이 무너진다 — 뒤에 온 발화가 저장되는 것으로 확인한다."""
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="오마이 잉글리시 종료", speaker="user"),
        SessionCommandEvent(command="end", stage="requested"),
        TranscriptEvent(kind="final", text="Actually let's keep going.", speaker="user"),
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            FakeClient(),
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("voice_command", "오마이 잉글리시 종료"),
        # 확인을 기다리는 중에 온 답이므로 `learning` 이 아니다 — 물린 답도 확인의 기록이다.
        ("command_confirmation", "Actually let's keep going."),
    ]


async def test_a_report_command_runs_at_once_and_keeps_the_session_open(db_pool, committed_session):
    """둘째 조각의 명령은 확인을 거치지 않는다 (`TASK-61.6` · 결정 107 ③).

    ⛔ **판별력은 셋째 발화에 있다** — 종료였다면 그 발화가 `command_confirmation` 으로 저장된다
    (위 `test_a_requested_end_command_does_not_close_the_session`). 리포트는 확인을 기다리지
    않으므로 **`learning` 으로 남아야** 한다. 그것이 「확인 절차를 타지 않는다」의 관측 가능한 형태다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Oh My English, show my weekly report.", speaker="user"),
        SessionCommandEvent(command="show_report", stage="requested"),
        TranscriptEvent(kind="final", text="I had a busy week at work.", speaker="user"),
    )
    client = FakeClient()

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

    assert client.of_type("voice_command") == [
        {"type": "voice_command", "command": "show_report", "stage": "requested"},
    ]
    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("voice_command", "Oh My English, show my weekly report."),
        ("learning", "I had a busy week at work."),
    ]


async def test_a_confirmed_additional_learning_command_closes_the_session_with_its_target(
    db_pool, committed_session
):
    """넷째 조각 (`TASK-61.8` · 결정 110) — 확인을 거쳐 세션을 닫고 **대상을 화면에 알린다.**

    ⛔ **`target` 은 이 명령에만 실린다 — 없으면 키를 아예 넣지 않는다.** 「없음」과 「빈 값」을
    가르는 이 리포의 규약이고(`session_started` 의 `shadowing`·`pronunciation_focus` 와 같음),
    화면이 그 키로 새 세션의 진입을 정하므로 빈 값이 흘러가면 엉뚱한 세션이 열린다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="오마이 잉글리시, 쉐도잉 추가 학습.", speaker="user"),
        SessionCommandEvent(command="start_additional", stage="requested", target="shadowing"),
        TranscriptEvent(kind="final", text="네 해 주세요.", speaker="user"),
        SessionCommandEvent(command="start_additional", stage="confirmed", target="shadowing"),
        hold_open=True,
    )
    client = FakeClient()

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

    assert adapter.closed
    assert client.types[-1] == "session_ended"
    assert (await _session_row(db_pool, committed_session.session_id))["status"] == "completed"
    assert client.of_type("voice_command") == [
        {
            "type": "voice_command",
            "command": "start_additional",
            "stage": "requested",
            "target": "shadowing",
        },
        {
            "type": "voice_command",
            "command": "start_additional",
            "stage": "confirmed",
            "target": "shadowing",
        },
    ]
    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("voice_command", "오마이 잉글리시, 쉐도잉 추가 학습."),
        ("command_confirmation", "네 해 주세요."),
    ]


async def test_an_unmarked_report_command_is_not_run_either(db_pool, committed_session):
    """표지 요구(사용자 결정 104 D5)가 **둘째 명령에도** 걸린다 (`TASK-61.6` AC#2).

    ⛔ 확인 절차가 없는 명령이라 표지가 유일한 방어다 — 종료는 확인이 한 겹 더 있지만 리포트는
    이 검사를 통과하면 그대로 수행된다. 그래서 표지 없는 tool 은 방송조차 되지 않아야 한다.
    ⚠️ 이 단정은 무력화로 판별력을 확인했다 — `_handle_command` 의 표지 검사를 끄면 실패한다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Show me my report from last week.", speaker="user"),
        SessionCommandEvent(command="show_report", stage="requested"),
    )
    client = FakeClient()

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

    assert client.of_type("voice_command") == []
    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("learning", "Show me my report from last week."),
    ]


async def _session_status(pool: asyncpg.Pool, session_id: UUID) -> str:
    async with pool.acquire() as conn:
        return await conn.fetchval("select status from learning_sessions where id = $1", session_id)


async def test_a_pause_command_stops_saving_learning_speech(db_pool, committed_session):
    """결정 117 (`TASK-61.9`) — 정지 중에는 학습 발화를 저장하지 않는다.

    ⛔ **이 단정이 이 기능의 값어치 전부다.** 코치가 조용히 기다리는 것은 문면이고 문면은 거동을
    보장하지 않는다(결정 112) — 앱이 지키는 것은 「정지 중 말한 것이 학습 기록에 남지 않는다」 하나다.
    학습자가 「잠깐」이라 말하는 상황은 옆 사람과 말하거나 자리를 비우는 것이고, 그것이 교정 대상
    발화로 저장되면 오류 패턴과 복습 시계가 오염된다.
    ⚠️ 정지는 **부드러운 정지**다 — 소켓과 어댑터는 살아 있다. 코치가 「학습 계속」을 들어야 하기
    때문이고, 그래서 표지가 든 발화는 정지 중에도 저장된다(다음 테스트가 그것을 쓴다).
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Hey, pause the session.", speaker="user"),
        SessionCommandEvent(command="pause", stage="requested"),
        TranscriptEvent(kind="final", text="I went to the store yesterday.", speaker="user"),
    )
    client = FakeClient()

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

    assert client.of_type("voice_command") == [
        {"type": "voice_command", "command": "pause", "stage": "requested"},
    ]
    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("voice_command", "Hey, pause the session."),
    ]


async def test_a_resume_command_puts_the_session_back_to_active(db_pool, committed_session):
    """결정 117 — 「학습 계속」은 **그 세션을 그대로 잇는다**(새 세션을 열지 않는다).

    ⛔ 재개 뒤 학습 발화가 다시 저장되는 것까지 한 단정에서 본다 — 상태만 되돌리고 저장 게이트가
    남아 있으면 학습자는 「계속됐다」고 듣고 기록은 비는, 결정 112 가 고친 그 갈림이 된다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Hey, pause the session.", speaker="user"),
        SessionCommandEvent(command="pause", stage="requested"),
        TranscriptEvent(kind="final", text="This one must not be saved.", speaker="user"),
        TranscriptEvent(kind="final", text="Hey, resume the session.", speaker="user"),
        SessionCommandEvent(command="resume", stage="requested"),
        TranscriptEvent(kind="final", text="I went to the store yesterday.", speaker="user"),
    )
    client = FakeClient()

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

    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("voice_command", "Hey, pause the session."),
        ("voice_command", "Hey, resume the session."),
        ("learning", "I went to the store yesterday."),
    ]
    # 세션은 러너가 끝에 `completed` 로 닫으므로 여기서 `active` 를 볼 수 없다 — 재개가 상태를
    # 되돌렸다는 것은 **닫힌 상태가 `completed`** 라는 사실이 보증한다(정지 상태로 남았으면
    # `end_session` 이 그것을 덮지 않고 `paused` 가 남는다).
    assert await _session_status(db_pool, committed_session.session_id) == "completed"


async def test_a_pause_command_without_the_marker_is_not_applied(db_pool, committed_session):
    """표지 요구(결정 104 D5)가 새 명령 둘에도 걸린다 — 그리고 그 버려짐은 화면에 뜬다.

    ⛔ 정지가 표지 없이 걸리면 **오인식 한 번이 학습 기록을 조용히 멈춘다** — 종료와 방향은 다르지만
    되돌릴 수 없는 손실이라는 점이 같다(정지 중 말한 것은 저장되지 않는다).
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Let us pause for a moment.", speaker="user"),
        SessionCommandEvent(command="pause", stage="requested"),
        TranscriptEvent(kind="final", text="I went to the store yesterday.", speaker="user"),
    )
    client = FakeClient()

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

    assert client.of_type("voice_command") == []
    assert client.of_type("voice_command_ignored") == [
        {"type": "voice_command_ignored", "command": "pause"},
    ]
    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("learning", "Let us pause for a moment."),
        ("learning", "I went to the store yesterday."),
    ]


async def test_a_dropped_command_is_surfaced_to_the_screen(db_pool, committed_session):
    """결정 113 (`TASK-61.16`) — 표지가 없어 버린 명령을 **화면이 알 수 있게** 방송한다.

    ⛔ 여기까지 오면 코치는 이미 「됐다」고 말한 뒤다 — 어댑터가 `{"status":"accepted"}` 를 tool 결과로
    돌려주는 자리가 앱의 이 판정보다 **앞**이기 때문이다(`audio_gateway/nova.py`
    `_flush_tool_results`). 그래서 warning 만 남기면 학습자는 되지 않은 것을 됐다고 듣는다 —
    실물로 4/4 관측했다(`runs/2026-09-16-task61-15-accepted-without-execution` §2-1).
    ⚠️ **실행하지 않는 것은 그대로다** — 이 프레임은 알림이고 명령이 아니다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="End the session now, please.", speaker="user"),
        SessionCommandEvent(command="end", stage="requested"),
    )
    client = FakeClient()

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

    assert client.of_type("voice_command") == []
    assert client.of_type("voice_command_ignored") == [
        {"type": "voice_command_ignored", "command": "end"},
    ]


async def test_a_dropped_command_is_reported_to_the_adapter_as_rejected(db_pool, committed_session):
    """결정 118 (`TASK-61.15`) — 앱이 버린 명령은 어댑터에 **거절로** 보고된다.

    ⛔ **그 보고가 코치의 「됐다」를 막는 유일한 수단이다.** 이전에는 어댑터가 번역 직후 「받았다」를
    보냈고 앱의 판정이 그 뒤였다 — 실물에서 코치가 4/4 로 완료를 말했다
    (`runs/2026-09-16-task61-15-accepted-without-execution` §2-1).
    ⚠️ **이유를 함께 보고한다** — 학습자가 할 일이 다르다(표지를 붙여 다시 말하기).
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="End the session now, please.", speaker="user"),
        SessionCommandEvent(command="end", stage="requested", tool_use_id="tool-1"),
    )
    client = FakeClient()

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

    assert adapter.outcomes == [("tool-1", False, "no_wake_word")]


async def test_an_executed_command_is_reported_to_the_adapter_as_executed(
    db_pool, committed_session
):
    """정상 명령은 **실행했다**로 보고된다 — 그때 어댑터가 `accepted` 를 보낸다 (결정 118).

    ⛔ 이 단정이 없으면 위 거절 단정만으로 「전부 거절로 보고한다」는 구현이 통과한다. 그러면 결정
    109 가 고친 침묵(결과가 없어 코치가 그 턴을 이어 말하지 못하는 것)이 다른 모양으로 되돌아온다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Hey, show my weekly report.", speaker="user"),
        SessionCommandEvent(command="show_report", stage="requested", tool_use_id="tool-2"),
    )
    client = FakeClient()

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

    assert adapter.outcomes == [("tool-2", True, None)]


async def test_a_dropped_next_question_is_not_surfaced(db_pool, committed_session):
    """결정 113 ② — `next_question` 은 두 표면 어디에도 들어가지 않는다 (`TASK-61.16` AC#3).

    ⛔ **이것이 이 표면의 판별력이다** — 「전부 알린다」로 넓히면 알림이 잡음이 되고, 잡음이 되면
    학습자가 그 자리를 보지 않는다. 근거는 실측이다: 이 명령은 프레임이 버려져도 코치가 실제로 다음
    질문을 하므로 화면이 어긋나지 않는다(`runs/2026-09-16-task61-15-accepted-without-execution` §4).
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Next question, please.", speaker="user"),
        SessionCommandEvent(command="next_question", stage="requested"),
    )
    client = FakeClient()

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

    assert client.of_type("voice_command") == []
    assert client.of_type("voice_command_ignored") == []


async def test_a_marked_command_is_not_surfaced_as_ignored(db_pool, committed_session):
    """표지가 있는 정상 명령에는 알림이 붙지 않는다 — 안 그러면 매 명령마다 잡음이 뜬다."""
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Hey, end the session.", speaker="user"),
        SessionCommandEvent(command="end", stage="requested"),
    )
    client = FakeClient()

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

    assert client.of_type("voice_command") == [
        {"type": "voice_command", "command": "end", "stage": "requested"},
    ]
    assert client.of_type("voice_command_ignored") == []


async def test_a_marked_user_final_is_stored_as_a_command_not_learning(db_pool, committed_session):
    """표지가 붙은 발화는 학습 발화가 아니다 — 분석에 넘기면 명령을 교정하게 된다.

    ⛔ 이 판정은 **앱이** 한다(결정 102 ①). 모델의 규율에 맡기면 명령이 `learning` 으로 저장되고
    분석기가 그것을 교정 대상으로 본다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Oh My English, end the session.", speaker="user"),
        TranscriptEvent(kind="final", text="I need to finish the report.", speaker="user"),
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            FakeClient(),
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("voice_command", "Oh My English, end the session."),
        ("learning", "I need to finish the report."),
    ]


async def test_a_tool_call_without_the_marker_in_the_turn_is_ignored(db_pool, committed_session):
    """⛔ 사용자 결정 104(D5) — 모델이 표지 없는 학습 발화를 명령으로 읽은 것이 실측이다.

    실측 근거: `runs/2026-09-15-task61-3-voice-command-app-leg` ARM-C 에서 코치가
    `i want to end the meeting early tomorrow.` 에 확인을 물었고 tool 을 불렀다. 그때 세션이
    닫히지 않은 것은 확인이 오지 않았기 때문이고, 이 검사는 **그 한 겹을 더 두는 것**이다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(
            kind="final", text="I want to end the meeting early tomorrow.", speaker="user"
        ),
        SessionCommandEvent(command="end", stage="requested"),
        SessionCommandEvent(command="end", stage="confirmed"),
        TranscriptEvent(kind="final", text="Anyway, about the report.", speaker="user"),
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            client := FakeClient(),
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("learning", "I want to end the meeting early tomorrow."),
        ("learning", "Anyway, about the report."),
    ], "표지가 없는 턴의 tool 이 발화 유형을 바꿨다"
    assert client.of_type("voice_command") == [], "무시한 명령을 화면에 알렸다"


async def test_a_command_utterance_is_broadcast_so_the_screen_can_show_it(
    db_pool, committed_session
):
    """⛔ `TASK-61.4` D4 — 앞 판은 명령 발화에 프레임을 보내지 않아 화면이 비었다.

    실측: ARM-A2·ARM-B 의 화면 줄이 빈 배열이었고 학습자는 명령이 접수됐는지 알 수 없었다.
    """
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="Oh My English, end the session.", speaker="user"),
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            client := FakeClient(),
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    finals = client.of_type("final")
    assert [(event["text"], event.get("utterance_type")) for event in finals] == [
        ("Oh My English, end the session.", "voice_command")
    ]


# ⛔ **`cancelled` 뒤의 다음 학습 발화가 `learning` 으로 남아야 한다** (`TASK-144.5` 정리 회차).
#
# **왜 이 단정이 새로 필요했나 — 변이로 확인한 구멍이다.** 정리에서 `_marker_seen`·
# `_awaiting_confirmation` 을 함께 끄는 두 줄을 `_end_command_exchange()` 로 묶은 뒤, 그 헬퍼에서
# 확인 대기 리셋을 **일부러 빼 보았더니 217건이 그대로 통과했다** — 즉 그 방어를 재는 단정이
# 없었다. 이 파일에 `cancelled` 단계를 밟는 테스트가 **0건**이었던 것이 원인이다.
#
# 그 구멍이 실제로 무엇을 잃게 하나: `requested` 로 확인 대기가 세워진 뒤 학습자 발화 없이
# `cancelled` 가 오면 대기가 남고, **다음 학습 발화가 `command_confirmation` 으로 저장되어 오류
# 분석에서 통째로 빠진다**(`utterance_type='learning'` 이 분석 대상의 유일한 조건이다).
async def test_a_cancelled_command_lets_the_next_utterance_be_learning_again(
    db_pool, committed_session
):
    adapter = ScriptedAdapter(
        TranscriptEvent(kind="final", text="오마이 잉글리시 종료", speaker="user"),
        SessionCommandEvent(command="end", stage="requested"),
        # 학습자 발화 없이 물러난다 — 모델이 스스로 물리는 형태이고,
        # 그때 확인 대기가 남으면 안 된다.
        SessionCommandEvent(command="end", stage="cancelled"),
        TranscriptEvent(kind="final", text="I had a busy week at work.", speaker="user"),
    )

    await asyncio.wait_for(
        _runner(
            adapter,
            db_pool,
            committed_session.session_id,
            FakeClient(),
            drain_timeout=FAST_DRAIN_TIMEOUT,
        ).run(),
        timeout=5.0,
    )

    rows = await _typed_utterances(db_pool, committed_session.session_id)
    assert [(row["utterance_type"], row["transcript"]) for row in rows] == [
        ("voice_command", "오마이 잉글리시 종료"),
        ("learning", "I had a busy week at work."),
    ]
