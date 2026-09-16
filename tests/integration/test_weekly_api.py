"""주간 리포트 조회 엔드포인트 (`TASK-26.5`).

설계: `docs/design/2026-09-14-weekly-report-design.md` §7.

⚠️ **재는 것은 라우터의 몫뿐이다** — 사실 집계와 모델 판단은 `tests/unit/test_weekly_report*.py` 가
소유한다. 여기서는 그 산출물이 HTTP 로 나가는 모양과 **없을 때의 모양**을 잰다.

`api_client` 는 커밋된 행만 본다(라우터가 자기 커넥션을 연다) — 그래서 `db_pool` 로 심고 스스로
지운다. ⛔ 고정 사용자(`FIXED_USER_ID`)의 행을 쓰므로 **끝나면 반드시 지운다**: 남기면 다음 실행이
「이미 있다」를 보고 다른 갈래를 탄다.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import date

import asyncpg
import httpx
import pytest_asyncio

from app.models.user import FIXED_USER_ID

# 월요일 하나를 고정으로 쓴다 — 2026-09-07 은 월요일이다(023 의 CHECK 가 그것을 요구한다).
# ⚠️ 이 값이 「지난 주」일 필요는 없다: 라우터는 **가장 최근에 계산된 주**를 주므로 어느 월요일이든
# 한 행만 있으면 그것이 답이다.
_WEEK = date(2026, 9, 7)


@pytest_asyncio.fixture
async def clean_reports(db_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """고정 사용자를 심고, 이 파일이 만든 리포트 행을 앞뒤로 지운다.

    라우터가 `FIXED_USER_ID` 로 조회한다(단일 사용자 로컬 도구 — 인증 계층이 없다).
    `test_daily_summary_api.py` 가 같은 픽스처를 갖고 그 파일의 주석이 「공유 자산으로 올리지
    않은」 근거를 갖는다 — 여기서도 같은 판단을 따른다(옮기면 그 파일들을 함께 고쳐야 한다).
    ⛔ **앞에서도 지운다** — 앞선 실행이 남긴 행이 있으면 「없을 때」를 재는 단정이 조용히 통과한다.
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into users (id, display_name, timezone) values ($1, 'Learner', 'Asia/Seoul') "
            "on conflict (id) do nothing",
            FIXED_USER_ID,
        )
        await conn.execute("delete from weekly_reports where user_id = $1", FIXED_USER_ID)
    try:
        yield
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from weekly_reports where user_id = $1", FIXED_USER_ID)
            await conn.execute("delete from users where id = $1", FIXED_USER_ID)


async def test_a_computed_week_is_served_with_facts_and_insights(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, clean_reports: None
) -> None:
    """계산된 주가 있으면 사실과 판단을 함께 준다.

    ⛔ **`metrics`·`insights` 가 dict 로 나가는지 잰다** — asyncpg 는 jsonb 를 **문자열**로 주고,
    `TASK-62` 가 그 자리에서 API 가 총평을 한 번도 싣지 못한 결함을 겪었다. 그 변환이 빠지면 화면이
    문자열을 받아 아무 것도 그리지 못한다.
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into weekly_reports "
            "(user_id, week_start, timezone, metrics, insights, computed_at) "
            "values ($1, $2, 'Asia/Seoul', $3::jsonb, $4::jsonb, now())",
            FIXED_USER_ID,
            _WEEK,
            json.dumps(
                {
                    "session_count": 3,
                    "occurrence_count": 5,
                    "pattern_count": 2,
                    "top_patterns": [
                        {
                            "category": "article",
                            "pattern_key": "article_missing",
                            "target_form": "the report",
                            "occurrences": 3,
                        }
                    ],
                }
            ),
            json.dumps({"improving": ["관사가 늘었어요."], "next_scenarios": ["상태 보고"]}),
        )

    response = await api_client.get("/api/weekly-report")

    assert response.status_code == 200
    body = response.json()
    assert body["week_start"] == _WEEK.isoformat()
    assert body["analyzed"] is True
    assert body["metrics"]["occurrence_count"] == 5
    assert body["metrics"]["top_patterns"][0]["pattern_key"] == "article_missing"
    assert body["insights"]["improving"] == ["관사가 늘었어요."]


async def test_no_report_yet_is_two_hundred_with_an_empty_shape(
    api_client: httpx.AsyncClient, clean_reports: None
) -> None:
    """⛔ 행이 없어도 **404 가 아니다** — `daily.py` 가 세운 규약이다.

    404 로 만들면 화면이 「오류」와 「아직 없음」을 구별해야 하고, 그 구별은 화면의 일이 아니다.
    ⚠️ `analyzed` 가 그 구별을 값으로 말한다.
    """
    response = await api_client.get("/api/weekly-report")

    assert response.status_code == 200
    body = response.json()
    assert body["analyzed"] is False
    assert body["week_start"] is None
    assert body["metrics"] == {}
    assert body["insights"] == {}


async def test_the_latest_week_wins(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, clean_reports: None
) -> None:
    """주가 여럿이면 **가장 최근** 주를 준다 — 화면이 열리는 자리가 최신이다.

    ⛔ 이 단정이 없으면 「아무 한 행」을 주는 구현이 통과하고, 그러면 화면이 몇 주 전 리포트를
    최신처럼 보인다.
    """
    async with db_pool.acquire() as conn:
        for week in (_WEEK, _WEEK.fromordinal(_WEEK.toordinal() + 7)):
            await conn.execute(
                "insert into weekly_reports "
                "(user_id, week_start, timezone, metrics, insights, computed_at) "
                "values ($1, $2, 'Asia/Seoul', '{}'::jsonb, '{}'::jsonb, now())",
                FIXED_USER_ID,
                week,
            )

    response = await api_client.get("/api/weekly-report")

    assert response.json()["week_start"] == _WEEK.fromordinal(_WEEK.toordinal() + 7).isoformat()


async def test_an_uncomputed_row_reports_analyzed_false(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, clean_reports: None
) -> None:
    """⛔ 행이 있어도 `computed_at` 이 null 이면 「아직 계산 안 됨」이다.

    그 구별이 `{}`(아직 없음)와 빈 배열(담을 것이 없었음)의 구별과 **다른 축**이다 — 이쪽은 「행은
    만들었지만 아직 채우지 않았다」다.
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into weekly_reports (user_id, week_start, timezone) "
            "values ($1, $2, 'Asia/Seoul')",
            FIXED_USER_ID,
            _WEEK,
        )

    body = (await api_client.get("/api/weekly-report")).json()

    assert body["analyzed"] is False
    assert body["week_start"] == _WEEK.isoformat()
