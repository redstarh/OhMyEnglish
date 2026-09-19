#!/usr/bin/env python3
"""B4 회차 드라이버 6 — 후보 풀의 경계를 잰다(가설 반증 시도 · §7-9).

가설: **수준이 올라간 사용자**는 무대 후보가 「그 수준의 행」으로 좁혀져 회전이 성립하지 않는다.
반증 시도: 그 수준의 행이 **0행이면** `_pick_scenario_for_user` 가 전체로 떨어지므로(폴백)
문제가 안 난다. 그러면 경계는 「행이 적다」가 아니라 **「1행 이상이면 폴백이 꺼진다」** 다.

두 팔을 같은 방법으로 돌려 그 경계를 가른다:
  A. `current_level='B1'` · B1 무대 0행 → 폴백이 돌아 시드 30행이 후보다
  B. `current_level='B1'` · B1 무대 **1행**(생성 무대 1건) → 후보가 1행이다
⛔ 내가 만든 사용자와 무대만 쓰고 끝에 지운다.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

import asyncpg

BACKEND = Path("/Users/redstar/MyProject/OhMyEnglish/app/backend")
sys.path.insert(0, str(BACKEND))

from app.services.sessions import create_session  # noqa: E402

MARK = "b4-pool-boundary"
TITLE = "B4 pool boundary marker stage"
TURNS = 6
OUT: dict[str, object] = {}


def dsn() -> str:
    for line in (BACKEND / ".env").read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL not found")


async def arm(pool: asyncpg.Pool, label: str, *, with_generated_b1: bool) -> None:
    async with pool.acquire() as conn:
        uid = await conn.fetchval(
            "insert into users (display_name, timezone, current_level) "
            "values ($1, 'Asia/Seoul', 'B1') returning id",
            f"{MARK}-{label}",
        )
        scenario_id = None
        if with_generated_b1:
            scenario_id = await conn.fetchval(
                "insert into learning_scenarios (category, level, title, prompt_template, source) "
                "values ('travel', 'B1', $1, 'You are a hotel receptionist at a small inn.', "
                "'generated') returning id",
                TITLE,
            )
        OUT[f"{label}_b1_rows"] = await conn.fetchval(
            "select count(*) from learning_scenarios where level='B1'"
        )
    picks: list[str] = []
    stages: list[str] = []
    try:
        for _ in range(TURNS):
            sid = await create_session(pool, uid, mode="speaking")
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "select scenario_pick, scenario_id from learning_sessions where id=$1", sid
                )
            picks.append(row["scenario_pick"] or "?")
            stages.append(str(row["scenario_id"])[-4:])
        OUT[f"{label}_sequence"] = "".join("N" if p == "new" else "R" for p in picks)
        OUT[f"{label}_distinct_stages"] = len(set(stages))
        OUT[f"{label}_stages"] = stages
    finally:
        async with pool.acquire() as conn:
            await conn.execute("delete from users where id=$1", uid)
            if scenario_id is not None:
                await conn.execute("delete from learning_scenarios where id=$1", scenario_id)


async def main() -> None:
    pool = await asyncpg.create_pool(dsn(), min_size=1, max_size=3)
    try:
        await arm(pool, "A_zero_b1_rows", with_generated_b1=False)
        await arm(pool, "B_one_b1_row", with_generated_b1=True)
        async with pool.acquire() as conn:
            OUT["cleanup_users_left"] = await conn.fetchval(
                "select count(*) from users where display_name like $1", f"{MARK}%"
            )
            OUT["cleanup_generated_left"] = await conn.fetchval(
                "select count(*) from learning_scenarios where source='generated'"
            )
    finally:
        await pool.close()
    print(json.dumps(OUT, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
