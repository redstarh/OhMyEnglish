"""주간 리포트의 주 경계와 조건부 트리거 (`TASK-26.2`).

설계: `docs/design/2026-09-14-weekly-report-design.md` §4·§6.

⚠️ **`db_conn`(롤백 트랜잭션)만 쓴다** — 커밋된 행을 남기지 않는다.
⛔ **주 경계를 상수로 고정하지 않는다** — 이 파일이 도는 날짜에 따라 값이 달라지므로 고정하면 하루
뒤 낡는다(`H-O` 의 부류). 대신 **성질**을 잰다: 월요일인가 · 이번 주보다 한 주 앞인가 · 타임존이
그 값을 가르는가.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
import pytest

from app.services.jobs import JOB_TYPE_SUMMARIZE_WEEK, enqueue_summarize_week
from app.services.weekly_report import last_week_start


async def _insert_user(conn: asyncpg.Connection, timezone: str) -> UUID:
    return await conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ('Weekly Test', $1, 'A2') returning id",
        timezone,
    )


async def _new_session(conn: asyncpg.Connection, user_id: UUID) -> UUID:
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        user_id,
    )


@pytest.mark.asyncio
async def test_last_week_start_is_a_monday_one_week_back(db_conn: asyncpg.Connection) -> None:
    """지난 주 월요일이다 — 사용자 타임존으로 구한다.

    ⛔ `current_date` 를 쓰지 않는다(R13-3 · 전역 규약). UTC 자정~09:00 구간에 그 값이 KST 날짜보다
    하루 이르므로, 그 구간에 주가 바뀌면 두 방식이 **다른 월요일**을 낸다.
    ⚠️ 값을 고정하지 않고 **성질**을 잰다: 월요일이고, 사용자 타임존의 「오늘」로부터 7~13일 전이다
    (오늘이 월요일이면 7일, 일요일이면 13일이다).
    """
    user_id = await _insert_user(db_conn, "Asia/Seoul")

    got = await last_week_start(db_conn, user_id)

    assert got.isoweekday() == 1, f"{got} 가 월요일이 아니다"
    today_kst = await db_conn.fetchval("select (now() at time zone 'Asia/Seoul')::date")
    assert 7 <= (today_kst - got).days <= 13


@pytest.mark.asyncio
async def test_the_timezone_can_move_the_week(db_conn: asyncpg.Connection) -> None:
    """타임존이 그 값을 가른다 — 같은 순간에 다른 주를 가리킬 수 있다.

    ⛔ **이 단정이 「타임존을 실제로 읽는가」의 판별력이다.** `now()` 를 그냥 쓰면(타임존을
    무시하면)
    두 사용자가 **언제나 같은 값**을 받아 이 성질이 사라진다.
    ⚠️ 어느 쪽이 앞인지는 이 단정이 도는 시각에 달렸으므로 **차이가 0 또는 7일**임만 잰다 —
    UTC+14 와 UTC-11 은 하루 차이까지 벌어질 수 있고 그 하루가 주 경계를 넘으면 7일이 된다.
    """
    east = await _insert_user(db_conn, "Pacific/Kiritimati")  # UTC+14
    west = await _insert_user(db_conn, "Pacific/Niue")  # UTC-11

    gap = (await last_week_start(db_conn, east)) - (await last_week_start(db_conn, west))

    assert gap.days in (0, 7), f"두 타임존의 주 시작 차이가 {gap.days}일이다"


@pytest.mark.asyncio
async def test_the_job_is_enqueued_when_last_week_has_no_row(db_conn: asyncpg.Connection) -> None:
    """지난 주 행이 없으면 job 이 걸린다 (결정 91)."""
    user_id = await _insert_user(db_conn, "Asia/Seoul")
    session_id = await _new_session(db_conn, user_id)

    job_id = await enqueue_summarize_week(db_conn, session_id)

    assert job_id is not None
    assert (
        await db_conn.fetchval("select job_type from analysis_jobs where id = $1", job_id)
        == JOB_TYPE_SUMMARIZE_WEEK
    )
    # 대상이 세션이다 — 「어떤 주」는 워커가 다시 구한다(설계서 §6).
    assert (
        await db_conn.fetchval("select session_id from analysis_jobs where id = $1", job_id)
        == session_id
    )


@pytest.mark.asyncio
async def test_the_job_is_not_enqueued_when_last_week_already_has_a_row(
    db_conn: asyncpg.Connection,
) -> None:
    """⛔ 결정 91 의 「지난 주 리포트가 없으면」이 이 단정에 걸린다.

    ⚠️ 조건을 **한 문장 안에** 두는 이유: 조회와 삽입을 나누면 그 사이에 다른 세션 종료가 같은 job
    을 넣는다.
    """
    user_id = await _insert_user(db_conn, "Asia/Seoul")
    session_id = await _new_session(db_conn, user_id)
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start, timezone) values ($1, $2, 'Asia/Seoul')",
        user_id,
        await last_week_start(db_conn, user_id),
    )

    assert await enqueue_summarize_week(db_conn, session_id) is None
    assert await db_conn.fetchval("select count(*) from analysis_jobs") == 0


@pytest.mark.asyncio
async def test_a_row_for_another_week_does_not_block_the_job(db_conn: asyncpg.Connection) -> None:
    """⛔ 「지난 주」가 아닌 주의 행은 가드에 걸리지 않는다.

    이 단정이 없으면 `not exists` 가 **주를 보지 않고** 「그 사용자의 행이 하나라도 있으면
    넘긴다」로 쓰여도 통과한다 — 그러면 둘째 주부터 리포트가 영원히 만들어지지 않는다.
    """
    user_id = await _insert_user(db_conn, "Asia/Seoul")
    session_id = await _new_session(db_conn, user_id)
    last_week = await last_week_start(db_conn, user_id)
    # ⚠️ 두 함정이 겹친 자리다: `date - interval` 은 `timestamp` 를 내고, `$2 - 7` 은 Postgres 가
    # `$2` 를 **정수로 추론**하게 만든다. 그래서 `$2::date - 7` 로 타입을 못박는다.
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start, timezone) "
        "values ($1, $2::date - 7, 'Asia/Seoul')",
        user_id,
        last_week,
    )

    assert await enqueue_summarize_week(db_conn, session_id) is not None


@pytest.mark.asyncio
async def test_another_users_row_does_not_block_the_job(db_conn: asyncpg.Connection) -> None:
    """⛔ 남의 리포트가 내 job 을 막지 않는다 — 가드가 `user_id` 를 함께 봐야 한다."""
    mine = await _insert_user(db_conn, "Asia/Seoul")
    other = await _insert_user(db_conn, "Asia/Seoul")
    session_id = await _new_session(db_conn, mine)
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start, timezone) values ($1, $2, 'Asia/Seoul')",
        other,
        await last_week_start(db_conn, other),
    )

    assert await enqueue_summarize_week(db_conn, session_id) is not None
