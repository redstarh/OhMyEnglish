"""Shared pytest fixtures for the OhMyEnglish backend test suite.

DB fixtures recreate the `ohmyenglish_test` database against the same
PostgreSQL server used for local development (see `scripts/dev_db.sh`) and
apply `db/migrations/*.sql` in order. Nothing here is asyncpg-pool-based on
purpose: each test gets its own connection inside a rolled-back transaction,
so tests never leak state into each other regardless of execution order.

Task 1 tests (`tests/unit/test_config.py`) do not depend on any fixture
defined here — pytest fixtures are lazy, so no database is touched unless a
test explicitly requests `db_conn`. Schema-level verification lives in
Task 2 (`tests/unit/test_schema.py`).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import asyncpg
import pytest
import pytest_asyncio

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
