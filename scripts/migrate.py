#!/usr/bin/env python3
"""Apply `db/migrations/*.sql` in order, then seed fixed dev/demo data.

Standalone ops script — no dependency on the `app.backend` package, so it
can run with just `asyncpg` installed (e.g. `app/backend/.venv/bin/python`).

    app/backend/.venv/bin/python scripts/migrate.py

Seeding is idempotent (`on conflict ... do nothing`): re-running never
creates duplicate rows.

주의: 적용 추적은 파일명 기준이다 — pre-release 중 001을 재작성한 경우 이
스크립트는 (파일명이 그대로라) 재적용하지 않으므로 dev DB를 drop/재생성해야
한다 (`scripts/db_utils.recreate_database`).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from uuid import UUID

import asyncpg
from db_utils import base_dsn

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

# Single-user local tool (§2 확정 실행 환경) — a fixed, deterministic id.
USER_ID = UUID("00000000-0000-0000-0000-000000000001")

# Fixed ids so `on conflict (id) do nothing` makes re-seeding idempotent.
# The 3 daily_life questions are verbatim from the task brief / design doc §1.
SEED_SCENARIOS: list[tuple[UUID, str, str, str, str]] = [
    (
        UUID("00000000-0000-0000-0000-000000000101"),
        "daily_life",
        "A2",
        "What do you usually do after work?",
        "What do you usually do after work?",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000102"),
        "daily_life",
        "A2",
        "What do you usually do on weekends?",
        "What do you usually do on weekends?",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000103"),
        "daily_life",
        "A2",
        "What do you need to do tonight?",
        "What do you need to do tonight?",
    ),
]


async def _ensure_migrations_table(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        create table if not exists schema_migrations (
            filename text primary key,
            applied_at timestamptz not null default now()
        )
        """
    )


async def apply_migrations(conn: asyncpg.Connection) -> None:
    """Apply each `db/migrations/*.sql` file at most once, tracked by
    filename in `schema_migrations` — running this script again (e.g. on
    every backend startup, per design doc §7 Dependency init order) must
    not fail with "relation already exists".

    Deliberately not `db_utils.recreate_database`: this applies to the dev DB
    in place (no drop), accumulating idempotently — the destructive drop/create
    is only ever correct for disposable test/smoke databases.
    """
    await _ensure_migrations_table(conn)
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        already_applied = await conn.fetchval(
            "select exists(select 1 from schema_migrations where filename = $1)",
            sql_file.name,
        )
        if already_applied:
            continue
        async with conn.transaction():
            await conn.execute(sql_file.read_text())
            await conn.execute(
                "insert into schema_migrations (filename) values ($1)", sql_file.name
            )


async def seed(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        insert into users (id, display_name, timezone, current_level)
        values ($1, 'Learner', 'Asia/Seoul', 'A2')
        on conflict (id) do nothing
        """,
        USER_ID,
    )
    for scenario_id, category, level, title, prompt_template in SEED_SCENARIOS:
        await conn.execute(
            """
            insert into learning_scenarios (id, category, level, title, prompt_template)
            values ($1, $2, $3, $4, $5)
            on conflict (id) do nothing
            """,
            scenario_id,
            category,
            level,
            title,
            prompt_template,
        )


async def main() -> None:
    conn = await asyncpg.connect(dsn=base_dsn())
    try:
        await apply_migrations(conn)
        await seed(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
