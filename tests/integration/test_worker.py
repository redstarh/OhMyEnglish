"""Task 7 — 분석 워커 루프 테스트 (AC W1 전체 연결, 설계서 §5.4).

동시성 1 단일 루프다: `claim_next` → `process_analysis` → 반복. 여기서 검증할
것은 파이프라인 내부가 아니라 **루프의 수명**이다 — 큐에 들어간 job이 아무도
깨우지 않아도 처리되는가, `stop` 이벤트로 즉시 멈추는가, 꺼진 상태에서는 정말
아무것도 claim하지 않는가.

실시간 대기는 쓰지 않는다. `poll_interval`을 0.01초로 주입하고 상태를 폴링해
조건이 성립하면 즉시 진행하며, 종료 검증은 `poll_interval`을 일부러 5초로 크게
주고 1초 안에 끝나는지 본다 — `stop`을 무시하고 주기를 통째로 자는 구현이라면
그 단정에서 걸린다.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from datetime import timedelta
from typing import Any
from uuid import UUID

import asyncpg
import pytest
from conftest import backdate_session, default_finding

from app import db as db_module
from app.api import main as main_module
from app.api.main import create_app
from app.audio_gateway.fixtures import FIXTURE_TURNS
from app.config import get_settings
from app.services.sessions import end_session
from app.services.utterances import flush_pending_analysis, save_final_transcript
from app.workers import analysis_worker
from app.workers.analysis_worker import run_worker
from app.workers.claude_client import FakeClaudeClient

# 픽스처 발화의 소유자는 `app.audio_gateway.fixtures` 하나다 (문장 중복 정의 금지).
GYM_ANSWER = FIXTURE_TURNS[0][1]


def _response(**overrides: Any) -> str:
    return json.dumps({"findings": [default_finding(**overrides)]})


async def _wait_until(
    condition: Callable[[], Awaitable[bool]], *, timeout: float = 5.0, what: str = "condition"
) -> None:
    """조건이 성립할 때까지 폴링한다 (타임아웃은 실패 시에만 소모된다)."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not await condition():
        assert loop.time() < deadline, f"{what} did not happen within {timeout}s"
        await asyncio.sleep(0.01)


async def _job_status(pool: asyncpg.Pool, utterance_id: UUID) -> str | None:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "select status from analysis_jobs where utterance_id = $1", utterance_id
        )


async def _job_is_done(pool: asyncpg.Pool, utterance_id: UUID) -> bool:
    return await _job_status(pool, utterance_id) == "done"


async def _session_status(pool: asyncpg.Pool, session_id: UUID) -> str | None:
    sql = "select status from learning_sessions where id = $1"
    async with pool.acquire() as conn:
        return await conn.fetchval(sql, session_id)


async def _session_is_failed(pool: asyncpg.Pool, session_id: UUID) -> bool:
    return await _session_status(pool, session_id) == "failed"


async def _save(pool: asyncpg.Pool, session_id: UUID, text: str = GYM_ANSWER) -> UUID:
    """사용자 발화를 저장하고 **턴을 닫아** 그 발화에 분석 job을 건다.

    I-1 이후 job은 저장이 아니라 턴 경계에서 걸린다 — agent final을 하나 끼우지
    않으면 워커가 claim할 것이 없다(게이트웨이와 같은 순서).
    """
    async with pool.acquire() as conn:
        utterance = await save_final_transcript(conn, session_id, text)
        await save_final_transcript(conn, session_id, "Tell me more.", speaker="agent")
        await flush_pending_analysis(conn, session_id)
    return utterance.id


# I-1 회복 — 종료 flush를 놓친 묶음을 워커가 스스로 걷어 끝까지 분석한다.
# 이것이 없으면 결과 화면이 terminal 상태 "분석 대상 없음"에 고정된다.
async def test_worker_recovers_a_run_whose_end_of_session_flush_was_lost(
    db_pool, committed_session, fake_claude
):
    # 종료 경로 flush가 실패한 상태를 그대로 만든다: 발화는 있고 job은 없다.
    async with db_pool.acquire() as conn:
        utterance = await save_final_transcript(conn, committed_session.session_id, GYM_ANSWER)
        await end_session(conn, committed_session.session_id, "completed")
    assert await _job_status(db_pool, utterance.id) is None, "job이 이미 있으면 회복을 볼 수 없다"
    claude: FakeClaudeClient = fake_claude(_response())
    stop = asyncio.Event()
    task = asyncio.create_task(run_worker(db_pool, claude, stop=stop, poll_interval=0.01))

    try:
        await _wait_until(lambda: _job_is_done(db_pool, utterance.id), what="스윕 후 job이 done")
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=1.0)

    async with db_pool.acquire() as conn:
        occurrences = await conn.fetchval(
            "select count(*) from error_occurrences where utterance_id = $1", utterance.id
        )
    assert occurrences == 1, "회복된 job이 분석까지 끝나지 않았다"


# I-1 회복 — 스윕은 **진행 중** 세션을 건드리지 않는다. 워커가 도는 동안 사용자가
# 아직 말하고 있으면 그 묶음은 자란다 — 여기서 걸면 조각이 따로 분석되는 결함이 되살아난다.
async def test_worker_sweep_leaves_an_active_session_alone(db_pool, committed_session, fake_claude):
    async with db_pool.acquire() as conn:
        utterance = await save_final_transcript(conn, committed_session.session_id, GYM_ANSWER)
    stop = asyncio.Event()
    task = asyncio.create_task(run_worker(db_pool, fake_claude(), stop=stop, poll_interval=0.01))

    try:
        await asyncio.sleep(0.1)  # 여러 유휴 사이클을 돌 만한 시간
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=1.0)

    assert await _job_status(db_pool, utterance.id) is None, "active 세션의 묶음에 job이 걸렸다"


# I-4 리퍼 — 종료 기록 전에 프로세스가 죽어 `active`로 남은 고아 세션을 워커가 닫고,
# **같은 유휴 사이클의** 스윕이 그 묶음을 걷어 끝까지 분석한다. 리퍼가 없으면 스윕은
# 정의상 `active`를 건너뛰므로 그 발화는 영구히 분석되지 않는다.
async def test_worker_reaps_an_orphan_session_and_then_recovers_its_run(
    db_pool, committed_session, fake_claude
):
    # 죽은 프로세스가 남긴 상태를 그대로 만든다: 세션은 `active`, 발화는 있고 job은 없다.
    async with db_pool.acquire() as conn:
        utterance = await save_final_transcript(conn, committed_session.session_id, GYM_ANSWER)
        await backdate_session(conn, committed_session.session_id, by=timedelta(minutes=10))
    assert await _job_status(db_pool, utterance.id) is None, "job이 이미 있으면 회복을 볼 수 없다"
    claude: FakeClaudeClient = fake_claude(_response())
    stop = asyncio.Event()
    task = asyncio.create_task(
        run_worker(db_pool, claude, stop=stop, poll_interval=0.01, live_sessions=set())
    )

    try:
        await _wait_until(
            lambda: _job_is_done(db_pool, utterance.id),
            what="리퍼가 닫은 뒤 스윕이 걸은 job이 done",
        )
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=1.0)

    assert await _session_status(db_pool, committed_session.session_id) == "failed", (
        "리퍼가 고아 세션을 닫지 않았다"
    )


# I-4 리퍼 — **살아있는 연결이 소유한 세션은 유예를 넘겨도 닫지 않는다.** 닫히면 그 직후
# 스윕이 아직 자라는 중인 묶음을 걷어 조각이 따로 분석되는 I-1 오탐이 되살아난다.
async def test_worker_reaper_leaves_a_live_session_alone(db_pool, committed_session, fake_claude):
    async with db_pool.acquire() as conn:
        utterance = await save_final_transcript(conn, committed_session.session_id, GYM_ANSWER)
        await backdate_session(conn, committed_session.session_id, by=timedelta(minutes=10))
    stop = asyncio.Event()
    task = asyncio.create_task(
        run_worker(
            db_pool,
            fake_claude(),
            stop=stop,
            poll_interval=0.01,
            live_sessions={committed_session.session_id},
        )
    )

    try:
        await asyncio.sleep(0.1)  # 여러 유휴 사이클을 돌 만한 시간
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=1.0)

    assert await _session_status(db_pool, committed_session.session_id) == "active", (
        "live 집합에 있는 세션을 리퍼가 닫았다"
    )
    assert await _job_status(db_pool, utterance.id) is None, "닫힌 세션의 묶음에 job이 걸렸다"


# I-4 관측성 — 리퍼가 걷었다는 신호는 **WARNING 이상**이어야 실물에서 보인다. 문서가 지정한
# 실행 명령(`docs/ops/local-run.md`)은 root 로거에 핸들러를 두지 않아 `logging.lastResort`가
# WARNING 이상만 흘린다(2026-09-03 실측). 레벨을 INFO로 내리면 이 테스트가 red가 된다.
async def test_the_reaper_reports_above_info_so_the_documented_run_shows_it(
    db_pool, committed_session, fake_claude, caplog
):
    async with db_pool.acquire() as conn:
        await save_final_transcript(conn, committed_session.session_id, GYM_ANSWER)
        await backdate_session(conn, committed_session.session_id, by=timedelta(minutes=10))
    stop = asyncio.Event()

    with caplog.at_level(logging.INFO):
        task = asyncio.create_task(
            run_worker(
                db_pool,
                fake_claude(_response()),
                stop=stop,
                poll_interval=0.01,
                live_sessions=set(),
            )
        )
        try:
            await _wait_until(
                lambda: _session_is_failed(db_pool, committed_session.session_id),
                what="리퍼가 고아 세션을 닫는다",
            )
        finally:
            stop.set()
            await asyncio.wait_for(task, timeout=1.0)

    reaped_lines = [record for record in caplog.records if "(I-4)" in record.getMessage()]
    assert reaped_lines, "리퍼가 세션을 닫았는데 아무 로그도 남기지 않았다"
    assert all(record.levelno >= logging.WARNING for record in reaped_lines), (
        "리퍼 로그가 INFO라 문서 실행 경로에서는 보이지 않는다"
    )


# ① active 세션에서 enqueue된 job이 워커 1사이클 후 done이 된다 (W1 관측형)
async def test_enqueued_job_is_processed_and_marked_done(db_pool, committed_session, fake_claude):
    utterance_id = await _save(db_pool, committed_session.session_id)
    async with db_pool.acquire() as conn:
        assert (
            await conn.fetchval(
                "select status from learning_sessions where id = $1",
                committed_session.session_id,
            )
            == "active"
        )
    claude: FakeClaudeClient = fake_claude(_response())
    stop = asyncio.Event()
    task = asyncio.create_task(run_worker(db_pool, claude, stop=stop, poll_interval=0.01))

    try:
        await _wait_until(lambda: _job_is_done(db_pool, utterance_id), what="job reaching done")
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=1.0)

    async with db_pool.acquire() as conn:
        occurrences = await conn.fetchval(
            "select count(*) from error_occurrences where utterance_id = $1", utterance_id
        )
        patterns = await conn.fetchval(
            "select count(*) from error_patterns where user_id = $1", committed_session.user_id
        )
    assert occurrences == 1
    assert patterns == 1
    assert len(claude.prompts) == 1


# ① 보강 — 동시성 1로도 큐에 쌓인 여러 job이 순차적으로 모두 처리된다
async def test_worker_drains_every_queued_job(db_pool, committed_session, fake_claude):
    first = await _save(db_pool, committed_session.session_id)
    second = await _save(db_pool, committed_session.session_id, "I usually go to office by subway.")
    claude = fake_claude(_response(), _response(original_span="go to office"))
    stop = asyncio.Event()
    task = asyncio.create_task(run_worker(db_pool, claude, stop=stop, poll_interval=0.01))

    try:
        for utterance_id in (first, second):
            await _wait_until(
                lambda uid=utterance_id: _job_is_done(db_pool, uid), what="both jobs reaching done"
            )
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=1.0)

    async with db_pool.acquire() as conn:
        assert (
            await conn.fetchval(
                "select count(*) from error_occurrences eo join utterances u on u.id = "
                "eo.utterance_id where u.session_id = $1",
                committed_session.session_id,
            )
            == 2
        )


# ② stop 이벤트로 루프가 1초 내 종료된다
async def test_stop_event_shuts_the_loop_down_within_a_second(db_pool, fake_claude):
    stop = asyncio.Event()
    # poll_interval을 5초로 크게 준다 — stop을 기다리지 않고 주기를 통째로 자는
    # 구현이라면 아래 1초 단정에서 걸린다.
    task = asyncio.create_task(run_worker(db_pool, fake_claude(), stop=stop, poll_interval=5.0))
    await asyncio.sleep(0.05)  # 빈 큐를 확인하고 대기 상태로 들어가게 한다

    stop.set()

    await asyncio.wait_for(task, timeout=1.0)
    assert task.done()
    assert task.exception() is None


# ③ 꺼진 워커는 아무것도 claim하지 않는다 (WORKER_ENABLED=false를 루프에 전달한 경우)
async def test_disabled_worker_returns_without_claiming(db_pool, committed_session, fake_claude):
    utterance_id = await _save(db_pool, committed_session.session_id)
    claude: FakeClaudeClient = fake_claude(_response())

    await asyncio.wait_for(
        run_worker(db_pool, claude, stop=asyncio.Event(), poll_interval=0.01, enabled=False),
        timeout=1.0,
    )

    assert await _job_status(db_pool, utterance_id) == "pending"
    assert claude.prompts == []


# 한 사이클의 실패가 루프를 죽이면 안 된다 — 워커가 조용히 사라지면 그 세션은
# 영원히 "분석 중"에 머문다 (§5.5 확정 표시 규칙).
async def test_worker_survives_a_failing_cycle(db_pool, fake_claude, monkeypatch):
    calls = 0
    original = analysis_worker.claim_next

    async def flaky_claim_next(conn, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise asyncpg.ConnectionDoesNotExistError("connection reset")
        return await original(conn, **kwargs)

    async def retried_after_the_failure() -> bool:
        return calls >= 2

    monkeypatch.setattr(analysis_worker, "claim_next", flaky_claim_next)
    stop = asyncio.Event()
    task = asyncio.create_task(run_worker(db_pool, fake_claude(), stop=stop, poll_interval=0.01))

    await _wait_until(retried_after_the_failure, what="the loop retrying after a failure")
    stop.set()
    await asyncio.wait_for(task, timeout=1.0)

    assert task.exception() is None


# --- lifespan 배선 (pool + 워커 기동/정지) ---


@pytest.fixture
def app_settings(monkeypatch: pytest.MonkeyPatch, test_database: str):
    """`create_app()`의 lifespan이 테스트 DB를 보게 만드는 환경 구성 팩토리.

    `get_settings`는 프로세스 전역 lru_cache이고 `db._pool`도 전역이므로 둘 다
    비워야 한다 — 비우지 않으면 앞선 테스트의 값이 살아남는다.
    """

    def configure(
        *,
        worker_enabled: bool,
        claude: object | None = None,
        shutdown_timeout: float | None = None,
    ) -> None:
        monkeypatch.setenv("DATABASE_URL", test_database)
        monkeypatch.setenv("AWS_REGION", "us-west-2")
        monkeypatch.setenv("WORKER_ENABLED", "true" if worker_enabled else "false")
        monkeypatch.setattr(db_module, "_pool", None)
        # 실물 Bedrock 클라이언트를 만들지 않는다(자격증명·실제 호출 금지).
        stand_in = claude if claude is not None else FakeClaudeClient([])
        monkeypatch.setattr(main_module, "BedrockClaudeClient", lambda settings: stand_in)
        if shutdown_timeout is not None:
            monkeypatch.setattr(main_module, "WORKER_SHUTDOWN_TIMEOUT", shutdown_timeout)
        get_settings.cache_clear()

    get_settings.cache_clear()
    yield configure
    get_settings.cache_clear()


# ③ WORKER_ENABLED=false면 lifespan이 루프를 띄우지 않는다
async def test_lifespan_does_not_start_the_worker_when_disabled(app_settings):
    app_settings(worker_enabled=False)
    app = create_app()

    async with app.router.lifespan_context(app):
        assert app.state.worker_task is None
        assert app.state.db_pool is not None  # pool은 워커와 무관하게 필요하다

    assert get_settings().worker_enabled is False


# 기본값(true)에서는 워커가 뜨고, lifespan 종료가 루프를 멈춘다
async def test_lifespan_starts_and_stops_the_worker_by_default(app_settings):
    app_settings(worker_enabled=True)
    app = create_app()

    async with app.router.lifespan_context(app):
        task = app.state.worker_task
        assert task is not None
        assert not task.done()

    assert task.done(), "lifespan 종료 후에도 워커가 돌면 프로세스가 내려가지 않는다"
    assert task.exception() is None
    assert db_module._pool is None, "pool도 함께 닫혀야 한다"


# Fix round 1 (I-4) — 종료 대기에 상한이 있어야 한다. Claude 호출 한복판에서
# shutdown이 걸리면 워커는 stop을 확인하지 못하므로, 상한 없이 await하면 프로세스가
# 응답 없이 매달린다. 상한을 넘기면 cancel한다 — 그 job은 lease 만료로 회수된다.
async def test_lifespan_shutdown_cancels_a_worker_that_will_not_stop(
    app_settings, db_pool: asyncpg.Pool, committed_session
):
    class _HangingClaude:
        def __init__(self) -> None:
            self.started = asyncio.Event()

        async def analyze(self, prompt: str) -> str:
            self.started.set()
            await asyncio.sleep(3600)  # 응답이 오지 않는 호출
            raise AssertionError("unreachable")

    hanging = _HangingClaude()
    app_settings(worker_enabled=True, claude=hanging, shutdown_timeout=0.1)
    utterance_id = await _save(db_pool, committed_session.session_id)
    app = create_app()
    loop = asyncio.get_running_loop()

    context = app.router.lifespan_context(app)
    await context.__aenter__()
    try:
        task = app.state.worker_task
        await asyncio.wait_for(hanging.started.wait(), timeout=5.0)
        shutdown_started = loop.time()
    finally:
        # 종료 시간을 재려면 컨텍스트 종료를 직접 호출해야 한다.
        await asyncio.wait_for(context.__aexit__(None, None, None), timeout=5.0)

    assert loop.time() - shutdown_started < 1.0, "종료가 상한 안에 끝나지 않았다"
    assert task.cancelled(), "상한을 넘긴 워커는 cancel되어야 한다"
    assert db_module._pool is None, "cancel 후에도 pool은 닫혀야 한다"
    # 취소된 시도의 job은 running으로 남고 lease 만료 후 회수된다 (§5.4).
    assert await _job_status(db_pool, utterance_id) == "running"


def test_worker_shutdown_timeout_is_a_documented_design_value():
    assert main_module.WORKER_SHUTDOWN_TIMEOUT == 15.0
