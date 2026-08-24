"""Task 2 — schema + seed tests.

Verifies the rewritten `db/migrations/001_initial_schema.sql` (design doc
§6/§6.1a) and `scripts/migrate.py`'s idempotent seed. Uses the `db_conn`
fixture from `tests/conftest.py`, which recreates `ohmyenglish_test` and
applies `db/migrations/*.sql` once per session, then hands each test a
connection inside a transaction that is always rolled back.
"""

from __future__ import annotations

import importlib.util
import types
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATE_PATH = REPO_ROOT / "scripts" / "migrate.py"


def _load_migrate_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("migrate", MIGRATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migrate = _load_migrate_module()


async def _insert_user(conn: asyncpg.Connection) -> None:
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'Test User', 'Asia/Seoul', 'A2')",
        migrate.USER_ID,
    )


async def _insert_session(conn: asyncpg.Connection, session_id) -> None:
    await conn.execute(
        "insert into learning_sessions (id, user_id, mode) values ($1, $2, 'speaking')",
        session_id,
        migrate.USER_ID,
    )


async def _insert_utterance(conn: asyncpg.Connection, utterance_id, session_id, sequence_no=1):
    await conn.execute(
        "insert into utterances (id, session_id, speaker, transcript, sequence_no) "
        "values ($1, $2, 'user', 'I go to gym.', $3)",
        utterance_id,
        session_id,
        sequence_no,
    )


# ① 001이 빈 DB에 오류 없이 적용된다 (conftest의 session fixture가 이미 적용을
#    시도하므로, 여기서는 기대하는 8개 테이블이 실제로 존재하는지 확인한다).
@pytest.mark.asyncio
async def test_001_migration_creates_expected_tables(db_conn: asyncpg.Connection):
    rows = await db_conn.fetch(
        "select table_name from information_schema.tables "
        "where table_schema = 'public' order by table_name"
    )
    table_names = {row["table_name"] for row in rows}
    assert table_names == {
        "analysis_jobs",
        "error_occurrences",
        "error_patterns",
        "learning_scenarios",
        "learning_sessions",
        "review_tasks",
        "users",
        "utterances",
    }


# ② analysis_jobs — 같은 (job_type, utterance_id)가 pending인 동안 중복 등록 차단
@pytest.mark.asyncio
async def test_analysis_jobs_pending_duplicate_violates_unique(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    utterance_id = uuid4()
    await _insert_session(db_conn, session_id)
    await _insert_utterance(db_conn, utterance_id, session_id)

    await db_conn.execute(
        "insert into analysis_jobs (job_type, utterance_id) values ('analyze_utterance', $1)",
        utterance_id,
    )

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_conn.execute(
            "insert into analysis_jobs (job_type, utterance_id) values ('analyze_utterance', $1)",
            utterance_id,
        )


# ③ error_patterns.category에 'noun' insert가 CHECK 위반
@pytest.mark.asyncio
async def test_error_patterns_category_check_rejects_unknown_code(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into error_patterns (user_id, category, pattern_key, target_form) "
            "values ($1, 'noun', 'noun_test_key', 'the noun')",
            migrate.USER_ID,
        )


# ④ learning_sessions.status='wrong' 거부
@pytest.mark.asyncio
async def test_learning_sessions_status_check_rejects_invalid_value(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into learning_sessions (user_id, mode, status) "
            "values ($1, 'speaking', 'wrong')",
            migrate.USER_ID,
        )


# ⑤ 시드 후 users 1행 · learning_scenarios 3행(질문 3개), 재실행해도 중복 없음(멱등)
@pytest.mark.asyncio
async def test_seed_creates_fixed_user_and_three_scenarios_idempotently(
    db_conn: asyncpg.Connection,
):
    await migrate.seed(db_conn)
    await migrate.seed(db_conn)  # re-run — must stay idempotent (on conflict do nothing)

    user_count = await db_conn.fetchval("select count(*) from users")
    assert user_count == 1

    seeded_user = await db_conn.fetchrow(
        "select display_name, timezone, current_level from users where id = $1",
        migrate.USER_ID,
    )
    assert seeded_user["timezone"] == "Asia/Seoul"
    assert seeded_user["current_level"] == "A2"

    scenario_rows = await db_conn.fetch(
        "select title from learning_scenarios where category = 'daily_life' order by title"
    )
    assert len(scenario_rows) == 3
    titles = {row["title"] for row in scenario_rows}
    assert titles == {
        "What do you usually do after work?",
        "What do you usually do on weekends?",
        "What do you need to do tonight?",
    }
