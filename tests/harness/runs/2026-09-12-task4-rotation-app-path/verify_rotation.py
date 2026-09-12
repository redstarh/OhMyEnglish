"""TASK-4 배치 규칙을 dev DB 에서 실제 앱 코드로 확인한다.

⛔ `scripts/migrate.py` 의 `seed()` 를 돌리지 않는다 — 그 함수는 `users`·`shadowing_items` 도
건드린다. 여기서는 `learning_scenarios` 만 upsert 한다(그 표의 `category`·`level` 은 덮지 않는
`seed()` 와 같은 규약을 쓴다).
⛔ 캡틴 사용자 데이터를 건드리지 않는다 — 전용 실험 사용자를 만들고 끝나면 지운다.
"""

import asyncio
import sys
from uuid import UUID

sys.path.insert(0, "/Users/redstar/MyProject/OhMyEnglish/scripts")

import asyncpg
from migrate import SEED_SCENARIOS

from app.services.sessions import create_session

DSN = "postgresql://ohmy:ohmy@localhost:5432/ohmyenglish"
PROBE_USER = UUID("00000000-0000-0000-0000-0000000009f4")
ROUNDS = 40

_UPSERT_SCENARIO = """
insert into learning_scenarios (id, category, level, title, prompt_template)
values ($1, $2, $3, $4, $5)
on conflict (id) do update
   set title = excluded.title,
       prompt_template = excluded.prompt_template
"""


async def main() -> None:
    pool = await asyncpg.create_pool(DSN)
    assert pool is not None

    async with pool.acquire() as conn:
        for sid, category, level, title, template in SEED_SCENARIOS:
            await conn.execute(_UPSERT_SCENARIO, sid, category, level, title, template)
        counts = await conn.fetch(
            "select category, count(*) as n from learning_scenarios group by category "
            "order by category"
        )
        print("시나리오:", {row["category"]: row["n"] for row in counts})

        await conn.execute(
            "insert into users (id, display_name, timezone, current_level) "
            "values ($1, 'rotation probe', 'Asia/Seoul', 'A2') on conflict (id) do nothing",
            PROBE_USER,
        )

    for _ in range(ROUNDS):
        await create_session(pool, PROBE_USER)

    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select sc.title, sc.category, ls.scenario_pick "
            "  from learning_sessions ls "
            "  join learning_scenarios sc on sc.id = ls.scenario_id "
            " where ls.user_id = $1 "
            " order by ls.started_at, ls.id",
            PROBE_USER,
        )
        print(f"\n{ROUNDS}회 연속 세션 — 실제 앱 경로(create_session)")
        for i, row in enumerate(rows, start=1):
            print(f"  {i:2d}. [{row['scenario_pick']:6s}] {row['category']:10s} {row['title']}")

        picks = [row["scenario_pick"] for row in rows]
        titles = [row["title"] for row in rows]
        print(f"\n신규 {picks.count('new')}회 · 반복 {picks.count('repeat')}회")
        print(f"서로 다른 상황 {len(set(titles))}종")
        back_to_back = sum(1 for a, b in zip(titles, titles[1:], strict=False) if a == b)
        print(f"연달아 같은 상황 {back_to_back}회")
        by_category: dict[str, int] = {}
        for row in rows:
            by_category[row["category"]] = by_category.get(row["category"], 0) + 1
        print(f"계열별 등장: {dict(sorted(by_category.items()))}")

        # ⚠️ 노출 속도를 함께 낸다 — 상황을 30개 담아도 신규는 주기 11회에 3개씩만 열린다.
        total_stages = await conn.fetchval("select count(*) from learning_scenarios")
        print(f"전체 상황 {total_stages}개 중 {len(set(titles))}종이 {ROUNDS}회 안에 나왔다")

        # 정리 — 실험 사용자와 그 세션만 지운다(세션은 cascade).
        await conn.execute("delete from users where id = $1", PROBE_USER)
        left = await conn.fetchval(
            "select count(*) from learning_sessions where user_id = $1", PROBE_USER
        )
        print(f"\n정리 뒤 남은 실험 세션 {left}건")

    await pool.close()


asyncio.run(main())
