#!/usr/bin/env python3
"""B4 회차 드라이버 3b — TS-35 AC#2 의 **앱 경로** 절.

d3 의 DB 절은 내 사용자를 `B1` 로 만들어 **후보가 1행**이었고(시드 30행은 전부 `A2`), 그래서
비율을 재지 못했다. 여기서는 시드와 같은 수준(`A2`)의 새 사용자로 `create_session` 을 12회
불러 실제 배치 규칙이 지나가는지 잰다. 이력이 빈 사용자이므로 설계서 §「30회 표」에 따라
**앞 3회가 신규**여야 한다.
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

from app.services.scenario_rotation import NEW, NEW_PER_WINDOW, WINDOW  # noqa: E402
from app.services.sessions import create_session  # noqa: E402

MARK = "b4-rotation-app-path"
TURNS = 12
OUT: dict[str, object] = {}


def dsn() -> str:
    for line in (BACKEND / ".env").read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL not found")


async def main() -> None:
    pool = await asyncpg.create_pool(dsn(), min_size=1, max_size=3)
    uid: UUID | None = None
    try:
        async with pool.acquire() as conn:
            uid = await conn.fetchval(
                "insert into users (display_name, timezone, current_level) "
                "values ($1, 'Asia/Seoul', 'A2') returning id",
                MARK,
            )
            OUT["candidates_at_A2"] = await conn.fetchval(
                "select count(*) from learning_scenarios where level='A2'"
            )
        picks: list[str] = []
        stages: list[str] = []
        for _ in range(TURNS):
            sid = await create_session(pool, uid, mode="speaking")
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "select scenario_pick, scenario_id from learning_sessions where id=$1", sid
                )
            picks.append(row["scenario_pick"])
            stages.append(str(row["scenario_id"])[-4:])
        OUT["sequence"] = "".join("N" if p == NEW else "R" for p in picks)
        OUT["new_total"] = picks.count(NEW)
        OUT["first_window_new"] = picks[:WINDOW].count(NEW)
        OUT["threshold"] = {"WINDOW": WINDOW, "NEW_PER_WINDOW": NEW_PER_WINDOW}
        OUT["new_quota_respected"] = picks[:WINDOW].count(NEW) == NEW_PER_WINDOW
        OUT["distinct_stages_used"] = len(set(stages))
        OUT["stage_sequence"] = stages
    finally:
        if uid is not None:
            async with pool.acquire() as conn:
                await conn.execute("delete from users where id=$1", uid)
                OUT["cleanup_users_left"] = await conn.fetchval(
                    "select count(*) from users where display_name=$1", MARK
                )
        await pool.close()
    print(json.dumps(OUT, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
