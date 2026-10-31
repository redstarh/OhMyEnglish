"""회차 2026-11-01-b3 정리 — 이 회차가 만든 문법 코스 행만 지운다(회차 시작 기준선 0·0).

지우는 범위: 고정 사용자 · 회차 시작(2026-10-31 15:24:12 UTC) 이후에 쓰인 행.
"""

import asyncio
from datetime import datetime, timezone

import asyncpg

from dbcount import dsn

START = datetime(2026, 10, 31, 15, 24, 12, tzinfo=timezone.utc)
USER = __import__("uuid").UUID("00000000-0000-0000-0000-000000000001")


async def main() -> None:
    conn = await asyncpg.connect(dsn())
    try:
        async with conn.transaction():
            older = await conn.fetchval(
                "select count(*) from ohmyenglish.course_day_progress where user_id = $1 and updated_at < $2",
                USER, START)
            print("progress_rows_older_than_round", older)
            print("delete progress", await conn.execute(
                "delete from ohmyenglish.course_day_progress where user_id = $1 and updated_at >= $2", USER, START))
            print("delete attempts", await conn.execute(
                "delete from ohmyenglish.course_attempts where user_id = $1 and created_at >= $2", USER, START))
    finally:
        await conn.close()


asyncio.run(main())
