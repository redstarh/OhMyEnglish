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
import os
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import NamedTuple
from urllib.parse import urlsplit, urlunsplit
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
DEFAULT_DEV_DSN = "postgresql://ohmy:ohmy@localhost:5433/ohmyenglish"


def _base_dsn() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DEV_DSN)


def _dsn_for(db_name: str) -> str:
    parts = urlsplit(_base_dsn())
    return urlunsplit((parts.scheme, parts.netloc, f"/{db_name}", parts.query, parts.fragment))


async def _recreate_test_database() -> None:
    admin_conn = await asyncpg.connect(dsn=_dsn_for("postgres"))
    try:
        await admin_conn.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
        await admin_conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await admin_conn.close()

    conn = await asyncpg.connect(dsn=_dsn_for(TEST_DB_NAME))
    try:
        for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
            await conn.execute(sql_file.read_text())
    finally:
        await conn.close()


@pytest.fixture(scope="session")
def test_database() -> str:
    """Recreate `ohmyenglish_test` and apply migrations once per test session.

    Returns the DSN of the freshly migrated test database.
    """
    asyncio.run(_recreate_test_database())
    return _dsn_for(TEST_DB_NAME)


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
