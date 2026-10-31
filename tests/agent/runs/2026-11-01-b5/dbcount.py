"""읽기 전용 — 문법 코스 표의 행 수와 진도 행을 찍는다 (회차 2026-11-01-b5)."""

import asyncio
import os
import sys

import asyncpg


def dsn() -> str:
    for line in open("/Users/redstar/MyProject/OhMyEnglish/app/backend/.env", encoding="utf-8"):
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip().strip('"')
    return os.environ["DATABASE_URL"]


async def main() -> None:
    conn = await asyncpg.connect(dsn())
    try:
        await conn.execute("set default_transaction_read_only = on")
        print("schema", await conn.fetchval("select current_schema()"))
        print("now", await conn.fetchval("select now()"))
        print("user_timezones", [dict(r) for r in await conn.fetch("select id, timezone from ohmyenglish.users")])
        print("attempts", await conn.fetchval("select count(*) from ohmyenglish.course_attempts"))
        rows = await conn.fetch("select * from ohmyenglish.course_day_progress order by day")
        print("progress_rows", len(rows))
        for row in rows:
            print(dict(row))
    finally:
        await conn.close()


if __name__ == "__main__":
    print("label", sys.argv[1] if len(sys.argv) > 1 else "")
    asyncio.run(main())
