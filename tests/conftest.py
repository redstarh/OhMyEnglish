"""Shared pytest fixtures for the OhMyEnglish backend test suite.

DB fixtures recreate the `ohmyenglish_test` database against the same
PostgreSQL server used for local development (see `scripts/dev_db.sh`) and
apply `db/migrations/*.sql` in order. The default `db_conn` fixture is not
pool-based on purpose: each test gets its own connection inside a rolled-back
transaction, so tests never leak state into each other regardless of
execution order.

`db_pool` exists for the code that **owns its own transactions** — the
analysis pipeline and the worker loop commit and re-read across several short
transactions, which a single rolled-back transaction cannot express. Anything
using it writes committed rows, so it must clean up after itself:
`committed_session` deletes its user on teardown and the cascade takes
sessions → utterances → analysis_jobs → error_occurrences (and
error_patterns) with it. Other tests assert on global row counts, so a
committed row that survives its test breaks them.

Task 1 tests (`tests/unit/test_config.py`) do not depend on any fixture
defined here — pytest fixtures are lazy, so no database is touched unless a
test explicitly requests one. Schema-level verification lives in Task 2
(`tests/unit/test_schema.py`).
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import NamedTuple
from uuid import UUID

import asyncpg
import pytest
import pytest_asyncio

# 공통 픽스처 발화 (AC 문서 §공통 픽스처) — 스텁·W-live·E2E-S가 같은 상수를 본다.
# 소유자는 `app.audio_gateway.fixtures` 하나다: 스텁이 재생하는 문장과 테스트가
# 기대하는 문장이 갈라지는 경로를 아예 만들지 않기 위해 여기서는 재수출만 한다.
from app.audio_gateway.fixtures import FIXTURE_TURNS as FIXTURE_TURNS
from app.workers.claude_client import FakeClaudeClient

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"
TEST_DB_NAME = "ohmyenglish_test"

# `scripts/db_utils.py`는 앱 패키지에 의존하지 않는 독립 모듈이라 일반 패키지
# 경로에 있지 않다 — pytest가 이 conftest를 최상위 모듈로 import할 때는
# 스크립트 실행과 달리 `scripts/`가 자동으로 sys.path에 오르지 않으므로 직접 넣는다.
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db_utils import recreate_database  # noqa: E402


@pytest.fixture(scope="session")
def test_database() -> str:
    """Recreate `ohmyenglish_test` and apply migrations once per test session.

    Returns the DSN of the freshly migrated test database.
    """
    return asyncio.run(recreate_database(TEST_DB_NAME, MIGRATIONS_DIR))


@pytest_asyncio.fixture
async def db_conn(test_database: str) -> AsyncIterator[asyncpg.Connection]:
    """A connection to the migrated test database, wrapped in a transaction
    that is always rolled back — each test starts from a clean, seeded
    baseline and never leaks writes to the next test."""
    conn = await asyncpg.connect(dsn=test_database)
    transaction = conn.transaction()
    await transaction.start()
    try:
        yield conn
    finally:
        await transaction.rollback()
        await conn.close()


@pytest_asyncio.fixture
async def db_pool(test_database: str) -> AsyncIterator[asyncpg.Pool]:
    """A pool over the migrated test database, for code that owns its own
    transactions (`services.analysis`, `workers.analysis_worker`).

    Writes here **commit** — pair it with `committed_session` (or clean up by
    hand) so nothing survives the test.
    """
    pool = await asyncpg.create_pool(dsn=test_database, min_size=1, max_size=5)
    assert pool is not None
    try:
        yield pool
    finally:
        await pool.close()


class CommittedSession(NamedTuple):
    user_id: UUID
    session_id: UUID


@pytest_asyncio.fixture
async def committed_session(db_pool: asyncpg.Pool) -> AsyncIterator[CommittedSession]:
    """A committed user + `active` learning session, dropped again on teardown.

    Deleting the user cascades to the session → utterances → analysis_jobs →
    error_occurrences and to error_patterns, so the test leaves the database
    exactly as it found it even though its writes were committed.
    """
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval(
            "insert into users (display_name) values ('Pipeline Test User') returning id"
        )
        session_id = await conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
            user_id,
        )
    try:
        yield CommittedSession(user_id=user_id, session_id=session_id)
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", user_id)


@pytest.fixture
def fake_claude() -> Callable[..., FakeClaudeClient]:
    """Factory for the Claude 대역: `fake_claude(resp1, resp2)` answers the
    calls in order and records the prompts it received (`.prompts`)."""

    def make(*responses: str) -> FakeClaudeClient:
        return FakeClaudeClient(list(responses))

    return make


def default_finding(**overrides: object) -> dict[str, object]:
    """공통 픽스처 발화 1("I usually go to gym after work.")에 대한 유효한
    finding 리터럴 — 관사 누락 오류. `tests/unit/test_claude_schema.py`·
    `test_analysis.py`, `tests/integration/test_pipeline.py`·`test_worker.py`가
    이 8필드 리터럴을 각자 복붙해 갈라지지 않도록 여기 하나로 묻는다."""
    finding: dict[str, object] = {
        "category": "article",
        "pattern_key": "article_missing_before_place_noun",
        "target_form": "go to the gym",
        "original_span": "go to gym",
        "correction": "go to the gym",
        "explanation": "장소를 가리키는 명사 앞에는 정관사 the가 필요합니다.",
        "severity": "medium",
        "confidence": 0.9,
    }
    finding.update(overrides)
    return finding


async def job_row(conn: asyncpg.Connection, job_id: UUID) -> asyncpg.Record:
    """`analysis_jobs` 한 행을 조회한다 — 사라졌으면 즉시 실패시킨다.
    `tests/unit/test_jobs.py`·`tests/integration/test_pipeline.py`가 공유한다."""
    row = await conn.fetchrow("select * from analysis_jobs where id = $1", job_id)
    assert row is not None, f"analysis_jobs row {job_id} disappeared"
    return row
