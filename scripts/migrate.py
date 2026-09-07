#!/usr/bin/env python3
"""Apply `db/migrations/*.sql` in order, then seed fixed dev/demo data.

Standalone ops script — no dependency on the `app.backend` package, so it
can run with just `asyncpg` installed (e.g. `app/backend/.venv/bin/python`).

    app/backend/.venv/bin/python scripts/migrate.py

Seeding is idempotent, but not the same way for every table. `users` uses
`on conflict (id) do nothing` — re-running never touches an existing row.
`learning_scenarios` uses `on conflict (id) do update` — re-running never
creates a duplicate row either, but it does overwrite `title` and
`prompt_template` back to the constants in `SEED_SCENARIOS` below. Why
`do update` was chosen anyway (fixed ids would otherwise stay stale
forever): `docs/design/2026-09-07-scenario-and-drill-turns-design.md` §7
유도 8.

⚠️ **손으로 고친 시나리오 행은 다음 실행에서 덮인다** — 그것이 위 선택의 대가다.

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

# Fixed ids so the upsert below makes re-seeding idempotent.
#
# ⚠️ **이 3행은 「무대(상황·역할)」이고 질문이 아니다** — 캡틴 결정 14 (2026-09-07).
# 이전 판은 task brief 의 질문 3개를 그대로 넣고 `title`과 `prompt_template`에 **같은 문자열**을
# 썼다. 그 상태에서 지시문에 실으면 두 가지가 깨진다: ① 대화 지시문의 `Today's setting:` 자리에
# **질문**이 박혀 계획이 소유한 질문 3~5개와 종류가 겹친다 ② 「`title`은 지시문에 싣지 않는다」는
# 방어(SYSTEM_PROMPT 규칙 6: 메타데이터를 소리내어 읽지 마라)가 **공허해진다** — 같은 문자열이
# `prompt_template`으로 들어가므로. 근거의 정본은
# `docs/design/2026-09-07-scenario-and-drill-turns-design.md` §2.1·§2.2 다.
#
# **화제는 보존하고 종류만 바꿨다**(퇴근 후 · 주말 · 오늘 밤) — 원래 brief 의 화제를 잃지 않는다.
# 문구가 따른 학습자 프로필(h-doc) 규약은 **둘**이다: 난이도 상향 경로의 첫 칸(일상)에 머무르고
# **목표 수준(AWS 보고) 문형을 쓰지 않는다** — 그 문형으로 만들면 첫 세션에서 얼어붙는다.
# ⚠️ **셋 다 단문·단일 절인 것은 h-doc 규약이 아니라 판단이다** — h-doc 의 그 제약은 학습자가
# 말할 예문·질문에 걸린 것이고, 이 문장들은 학습자가 아니라 코치(모델)에게 가는 지시문이다.
# 짧게 쓴 이유는 짧을수록 모델이 무대를 덜 오해한다는 것뿐이다. 적용/비적용의 정본은
# `docs/design/2026-09-07-scenario-and-drill-turns-design.md` §2.1 의 갈라 적기다.
#
# ⛔ `category`·`level`을 바꾸지 마라. `_CREATE_SESSION_SQL`이 `users.current_level`(=`A2`)로
# 시나리오를 고르므로 `A2`가 아니면 그 경로가 폴백으로 떨어진다. 업무 시나리오 추가는
# 캡틴 결정 5의 몫이고 `TASK-4`·`TASK-5`가 소유한다 — 여기서 행을 늘리지 않는다.
SEED_SCENARIOS: list[tuple[UUID, str, str, str, str]] = [
    (
        UUID("00000000-0000-0000-0000-000000000101"),
        "daily_life",
        "A2",
        "After work with a colleague",
        "You are a friendly colleague chatting with the learner after work.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000102"),
        "daily_life",
        "A2",
        "Weekend plans with a friend",
        "You are a friend catching up with the learner about the weekend.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000103"),
        "daily_life",
        "A2",
        "Tonight's plans at home",
        "You are a housemate talking with the learner about tonight.",
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
            -- ⚠️ `do nothing` 이 아니라 **`do update`** 다 (캡틴 결정 14 · 설계서 §7 유도 8).
            -- id 가 고정이므로 `do nothing` 이면 **상수를 고쳐도 이미 시드된 행은 영원히 낡은
            -- 값으로 남는다** — 2026-09-07 에 실제로 그랬다(개발 DB 3행이 질문 문구인 채였다).
            -- ⛔ `category`·`level` 은 갱신 대상에서 뺀다. 그 둘은 세션 시작이 시나리오를 고르는
            -- 키이고(`_CREATE_SESSION_SQL` 이 `users.current_level` 로 고른다), 여기서 덮으면
            -- 학습자 수준과 시나리오 값역의 관계를 시드가 조용히 바꾼다.
            on conflict (id) do update
               set title = excluded.title,
                   prompt_template = excluded.prompt_template
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
