"""`app.services.scenario_progress` — 어느 상황을 몇 번 했는지 (`TASK-102` AC#4).

⚠️ **재는 것은 「행이 있다」가 아니라 «미학습 상황도 보인다»다** — 완료 현황이므로 0회인 상황이
목록에서 빠지면 「무엇이 남았는지」를 알 수 없고, 그것이 이 집계의 존재 이유다.

⛔ **날짜는 `users.timezone` 이 정한다**(전역 시각 규약 3항). UTC 자정~09:00(KST) 구간에서 두 날짜가
하루 어긋나므로 아래 `test_last_studied_on_uses_the_user_timezone` 이 그 구간을 직접 심어 잰다 —
그 테스트가 없으면 「날짜를 변환한다」는 단정이 무보호다.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import asyncpg
import pytest

from app.services.scenario_progress import ScenarioProgress, load_scenario_progress

_USER = UUID("00000000-0000-0000-0000-00000000a101")


async def _make_user(conn: asyncpg.Connection, *, timezone: str = "Asia/Seoul") -> UUID:
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'progress', $2, 'A2')",
        _USER,
        timezone,
    )
    return _USER


async def _make_scenario(
    conn: asyncpg.Connection,
    title: str,
    *,
    category: str = "daily_life",
    created_at: datetime | None = None,
):
    """⛔ 순서를 재는 테스트는 `created_at` 을 **명시로** 준다.

    `db_conn` 은 한 트랜잭션이고 PostgreSQL 의 `now()` 는 **트랜잭션 시작 시각에 고정**되므로,
    기본값에 맡기면 연달아 넣은 행들의 `created_at` 이 **완전히 같아지고** 순서가 `id`(랜덤
    UUID)로 정해진다 — 즉 테스트가 불안정해진다. 2026-09-12 에 실제로 그렇게 통과했다가
    다음 실행에서 깨졌다.
    """
    if created_at is None:
        return await conn.fetchval(
            "insert into learning_scenarios (category, level, title, prompt_template) "
            "values ($1, 'A2', $2, 'You are someone.') returning id",
            category,
            title,
        )
    return await conn.fetchval(
        "insert into learning_scenarios (category, level, title, prompt_template, created_at) "
        "values ($1, 'A2', $2, 'You are someone.', $3) returning id",
        category,
        title,
        created_at,
    )


async def _make_session(
    conn: asyncpg.Connection,
    user_id: UUID,
    scenario_id,
    *,
    pick: str | None = None,
    started_at: datetime | None = None,
):
    if started_at is None:
        return await conn.fetchval(
            "insert into learning_sessions (user_id, mode, scenario_id, scenario_pick) "
            "values ($1, 'speaking', $2, $3) returning id",
            user_id,
            scenario_id,
            pick,
        )
    # ⛔ naive datetime 을 넘기지 않는다 — 앱 경계에서 거부하는 것이 전역 시각 규약 2항이고,
    # 여기서도 tz 를 붙여 넘긴다(그러지 않으면 서버 오프셋만큼 밀린 값을 재게 된다).
    assert started_at.tzinfo is not None, "naive datetime 을 심으면 이 테스트의 판별력이 사라진다"
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode, scenario_id, scenario_pick, started_at) "
        "values ($1, 'speaking', $2, $3, $4) returning id",
        user_id,
        scenario_id,
        pick,
        started_at,
    )


@pytest.mark.asyncio
async def test_unstudied_scenarios_appear_with_zero(db_conn: asyncpg.Connection):
    """아직 안 한 상황도 목록에 있다 — 그것이 「완료 현황」의 요구다."""
    user_id = await _make_user(db_conn)
    await _make_scenario(db_conn, "first")
    await _make_scenario(db_conn, "second")

    rows = await load_scenario_progress(db_conn, user_id)

    assert len(rows) == 2, "미학습 상황이 빠졌다 — 무엇이 남았는지 알 수 없게 된다"
    assert all(isinstance(row, ScenarioProgress) for row in rows)
    assert [row.sessions for row in rows] == [0, 0]
    assert [row.new_picks for row in rows] == [0, 0]
    assert [row.last_studied_on for row in rows] == [None, None]


@pytest.mark.asyncio
async def test_counts_sessions_and_new_picks(db_conn: asyncpg.Connection):
    """세션 수와 «신규로 골라진» 횟수를 따로 센다 — 둘은 다른 정보다."""
    user_id = await _make_user(db_conn)
    scenario_id = await _make_scenario(db_conn, "counted")
    other_id = await _make_scenario(db_conn, "untouched")

    await _make_session(db_conn, user_id, scenario_id, pick="new")
    await _make_session(db_conn, user_id, scenario_id, pick="repeat")
    await _make_session(db_conn, user_id, scenario_id, pick=None)  # 016 이전 행

    rows = {row.scenario_id: row for row in await load_scenario_progress(db_conn, user_id)}

    assert rows[scenario_id].sessions == 3
    assert rows[scenario_id].new_picks == 1, "null 이나 repeat 을 신규로 셌다"
    assert rows[other_id].sessions == 0


@pytest.mark.asyncio
async def test_other_users_sessions_are_not_counted(db_conn: asyncpg.Connection):
    """⛔ 다른 사용자의 세션이 섞이지 않는다 — 단일 사용자 도구여도 집계는 사용자별이다."""
    user_id = await _make_user(db_conn)
    stranger = await db_conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ('stranger', 'Asia/Seoul', 'A2') returning id"
    )
    scenario_id = await _make_scenario(db_conn, "shared stage")

    await _make_session(db_conn, stranger, scenario_id, pick="new")

    rows = {row.scenario_id: row for row in await load_scenario_progress(db_conn, user_id)}
    assert rows[scenario_id].sessions == 0, "남의 세션이 내 현황에 섞였다"


@pytest.mark.asyncio
async def test_rows_follow_the_seed_order(db_conn: asyncpg.Connection):
    """정렬은 `created_at` 이다 — 그것이 시드 배열 순서이고 «다음에 나올 순서»다(결정 76)."""
    user_id = await _make_user(db_conn)
    # 제목을 일부러 역순으로 둔다 — 제목순으로 정렬하면 이 단정이 깨진다.
    first = await _make_scenario(
        db_conn, "zzz inserted first", created_at=datetime(2026, 9, 1, tzinfo=UTC)
    )
    second = await _make_scenario(
        db_conn, "aaa inserted second", created_at=datetime(2026, 9, 2, tzinfo=UTC)
    )

    rows = await load_scenario_progress(db_conn, user_id)

    assert [row.scenario_id for row in rows] == [first, second], (
        "제목순이나 임의 순서로 냈다 — 노출 순서를 볼 수 없게 된다"
    )


@pytest.mark.asyncio
async def test_last_studied_on_uses_the_user_timezone(db_conn: asyncpg.Connection):
    """⛔ 달력 날짜는 `users.timezone` 으로 정한다 — UTC 날짜와 하루 어긋나는 구간을 심는다.

    `2026-09-11 23:30+00` 은 UTC 로 **9월 11일**이고 `Asia/Seoul` 로 **9월 12일 08:30** 이다.
    ⇒ 이 단정이 통과하면 변환이 실제로 일어났다는 뜻이다. UTC 를 그대로 냈다면 11일이 나온다.
    """
    user_id = await _make_user(db_conn, timezone="Asia/Seoul")
    scenario_id = await _make_scenario(db_conn, "boundary")

    await _make_session(
        db_conn,
        user_id,
        scenario_id,
        pick="new",
        started_at=datetime(2026, 9, 11, 23, 30, tzinfo=UTC),
    )

    rows = {row.scenario_id: row for row in await load_scenario_progress(db_conn, user_id)}

    assert rows[scenario_id].last_studied_on == date(2026, 9, 12), (
        "UTC 날짜를 그대로 냈다 — users.timezone 변환이 빠졌다"
    )


@pytest.mark.asyncio
async def test_missing_user_raises(db_conn: asyncpg.Connection):
    """타임존 정본이 없으면 조용히 기본값을 쓰지 않고 실패한다 — `usage.py` 와 같은 규약이다."""
    with pytest.raises(LookupError):
        await load_scenario_progress(db_conn, UUID("00000000-0000-0000-0000-0000000000ff"))
