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
from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import asyncpg
import pytest

from app import db as db_module
from app.api import main as main_module
from app.api.main import create_app
from app.config import get_settings
from app.services.utterances import save_final_transcript
from app.workers import analysis_worker
from app.workers.analysis_worker import run_worker
from app.workers.claude_client import FakeClaudeClient

GYM_ANSWER = "I usually go to gym after work."


def _response(**overrides: Any) -> str:
    finding = {
        "category": "article",
        "pattern_key": "article_missing_before_place_noun",
        "target_form": "go to the gym",
        "original_span": "go to gym",
        "correction": "go to the gym",
        "severity": "medium",
        "confidence": 0.9,
    }
    finding.update(overrides)
    return json.dumps({"findings": [finding]})


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


async def _save(pool: asyncpg.Pool, session_id: UUID, text: str = GYM_ANSWER) -> UUID:
    async with pool.acquire() as conn:
        utterance = await save_final_transcript(conn, session_id, text)
    return utterance.id


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

    def configure(*, worker_enabled: bool) -> None:
        monkeypatch.setenv("DATABASE_URL", test_database)
        monkeypatch.setenv("AWS_REGION", "us-west-2")
        monkeypatch.setenv("WORKER_ENABLED", "true" if worker_enabled else "false")
        monkeypatch.setattr(db_module, "_pool", None)
        # 실물 Bedrock 클라이언트를 만들지 않는다(자격증명·실제 호출 금지).
        monkeypatch.setattr(
            main_module, "BedrockClaudeClient", lambda settings: FakeClaudeClient([])
        )
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
