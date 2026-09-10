"""일일 오류 요약의 배선 — 저장 경로와 조회 엔드포인트 (PRD §13 · `TASK-1`).

두 가지를 잰다.

* 분석 파이프라인이 그 날짜의 요약을 **함께** 남기는가(R13-1·R13-6). 단위 테스트
  (`tests/unit/test_daily_summary.py`)는 함수를 직접 불러 재므로 「아무도 그 함수를 부르지
  않는다」를 잡지 못한다 — 이 파일이 그 자리를 막는다.
* `GET /api/daily-summary`가 그 행을 화면 계약으로 옮기는가(R13-4·R13-7).

`db_conn`이 아니라 `db_pool`을 쓰는 이유는 `test_pipeline.py`와 같다 — `process_analysis`가
자기 트랜잭션을 여러 개 열고, 라우터는 테스트와 다른 커넥션으로 읽는다.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

import asyncpg
import httpx
import pytest_asyncio
from conftest import default_finding

from app.api.ws import FIXED_USER_ID
from app.audio_gateway.fixtures import FIXTURE_TURNS
from app.services.analysis import process_analysis
from app.services.jobs import ClaimedJob, enqueue_analyze
from app.services.utterances import UtteranceRow, flush_pending_analysis, save_final_transcript
from app.workers.analysis_worker import claim_one

DAILY_SUMMARY_PATH = "/api/daily-summary"

GYM_ANSWER = FIXTURE_TURNS[0][1]
AGENT_ACK = "Tell me more."
ARTICLE_PATTERN_KEY = "article_missing_before_place_noun"


@pytest_asyncio.fixture
async def committed_fixed_user(db_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """고정 사용자 1행을 커밋해두고 teardown 에서 지운다.

    라우터는 `FIXED_USER_ID`로 조회한다(단일 사용자 로컬 도구 — 인증 계층이 없다).
    `test_plan_api.py`가 같은 픽스처를 갖는데 그 파일의 것을 공유 자산으로 올리지 않았다 —
    옮기려면 그 파일도 함께 고쳐야 하고, 이 태스크의 범위가 아니다. 값은 그쪽과 같게 둔다
    (`scripts/migrate.py`의 시드값과 같은 값이라 행 수를 재는 테스트를 깨지 않는다).
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into users (id, display_name, timezone) values ($1, 'Learner', 'Asia/Seoul') "
            "on conflict (id) do nothing",
            FIXED_USER_ID,
        )
    try:
        yield
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", FIXED_USER_ID)


def _response(*findings: dict[str, Any]) -> str:
    return json.dumps({"findings": list(findings)})


async def _claim(pool: asyncpg.Pool) -> ClaimedJob:
    job = await claim_one(pool)
    assert job is not None, "claim할 job이 없다"
    return job


async def _say_and_close_turn(pool: asyncpg.Pool, session_id: UUID, text: str) -> UtteranceRow:
    """사용자 발화 저장 + 턴 닫기까지 — `test_pipeline.py`의 `_save`와 같은 순서다."""
    async with pool.acquire() as conn:
        row = await save_final_transcript(conn, session_id, text)
        await save_final_transcript(conn, session_id, AGENT_ACK, speaker="agent")
        await flush_pending_analysis(conn, session_id)
    return row


async def _summary_row(pool: asyncpg.Pool, user_id: UUID) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            "select summary_date, timezone, occurrence_count, pattern_count, patterns "
            "from daily_error_summary where user_id = $1",
            user_id,
        )


async def _insert_summary(
    pool: asyncpg.Pool,
    user_id: UUID,
    *,
    patterns: list[dict[str, Any]],
    occurrence_count: int,
) -> None:
    """오늘(사용자 타임존) 날짜로 요약 1건을 직접 심는다 — 라우터만 재는 테스트용."""
    today = datetime.now(UTC).astimezone(ZoneInfo("Asia/Seoul")).date()
    async with pool.acquire() as conn:
        await conn.execute(
            "insert into daily_error_summary (user_id, summary_date, timezone, "
            "occurrence_count, pattern_count, patterns) values ($1, $2, 'Asia/Seoul', $3, $4, $5)",
            user_id,
            today,
            occurrence_count,
            len(patterns),
            json.dumps(patterns, ensure_ascii=False),
        )


# ① 배선 — 분석이 끝나면 그 날짜의 요약이 함께 남는다. 이 단정이 없으면 서비스 함수가
#    아무에게도 불리지 않는 상태로 통과한다.
async def test_analysis_records_the_daily_summary(
    db_pool: asyncpg.Pool, committed_session, fake_claude
) -> None:
    claude = fake_claude(_response(default_finding(pattern_key=ARTICLE_PATTERN_KEY)))
    await _say_and_close_turn(db_pool, committed_session.session_id, GYM_ANSWER)

    await process_analysis(db_pool, claude, await _claim(db_pool))

    row = await _summary_row(db_pool, committed_session.user_id)
    assert row is not None
    assert row["occurrence_count"] == 1
    assert row["pattern_count"] == 1
    assert row["timezone"] == "Asia/Seoul"
    patterns = json.loads(row["patterns"])
    assert [item["pattern_key"] for item in patterns] == [ARTICLE_PATTERN_KEY]


# ② 배선 — 같은 발화를 다시 분석해도 그 날짜의 요약이 부풀지 않는다(R13-6).
async def test_reanalysis_keeps_the_summary_in_step(
    db_pool: asyncpg.Pool, committed_session, fake_claude
) -> None:
    claude = fake_claude(
        _response(default_finding(pattern_key=ARTICLE_PATTERN_KEY)),
        _response(default_finding(pattern_key=ARTICLE_PATTERN_KEY)),
    )
    utterance = await _say_and_close_turn(db_pool, committed_session.session_id, GYM_ANSWER)
    await process_analysis(db_pool, claude, await _claim(db_pool))

    # done 이후 재등록은 허용된다(partial unique 는 pending/running 만) — 크래시 뒤 같은 발화가
    # 다시 분석되는 상황과 같은 입력이다. `test_pipeline.py`의 멱등 테스트와 같은 배선이다.
    async with db_pool.acquire() as conn, conn.transaction():
        assert await enqueue_analyze(conn, utterance.id) is not None
    await process_analysis(db_pool, claude, await _claim(db_pool))

    row = await _summary_row(db_pool, committed_session.user_id)
    assert row is not None
    assert row["occurrence_count"] == 1


# ③ 라우터 — 오늘 요약이 있으면 그 값을 화면 계약으로 옮긴다(R13-4).
async def test_endpoint_returns_todays_summary(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_fixed_user
) -> None:
    await _insert_summary(
        db_pool,
        FIXED_USER_ID,
        occurrence_count=3,
        patterns=[
            {
                "pattern_key": ARTICLE_PATTERN_KEY,
                "category": "article",
                "target_form": "go to the + 장소 명사",
                "occurrences": 2,
                "example": {
                    "original_span": "I go to gym",
                    "correction": "I go to the gym",
                    "reason": "정관사가 필요합니다.",
                },
            }
        ],
    )

    response = await api_client.get(DAILY_SUMMARY_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["analyzed"] is True
    assert payload["occurrence_count"] == 3
    assert payload["pattern_count"] == 1
    assert payload["patterns"][0]["pattern_key"] == ARTICLE_PATTERN_KEY
    assert payload["patterns"][0]["example"]["correction"] == "I go to the gym"


# ④ 라우터 — 요약 행이 없으면 「그날 학습이 없었다」다. 404 가 아니고 `analyzed`가 거짓이다
#    (R13-7 · 계획 부재를 404 로 만들지 않는 `next-plan`과 같은 판단).
async def test_endpoint_reports_not_analyzed_when_no_row_exists(
    api_client: httpx.AsyncClient, committed_fixed_user
) -> None:
    response = await api_client.get(DAILY_SUMMARY_PATH)

    assert response.status_code == 200
    payload = response.json()
    assert payload["analyzed"] is False
    assert payload["occurrence_count"] == 0
    assert payload["pattern_count"] == 0
    assert payload["patterns"] == []


# ⑤ 라우터 — 남의 요약을 내려주지 않는다. `user_id` 조건이 빠지면 이 테스트가 잡는다.
async def test_endpoint_ignores_another_learners_summary(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_fixed_user
) -> None:
    async with db_pool.acquire() as conn:
        other = await conn.fetchval(
            "insert into users (display_name, timezone) values ('Someone Else', 'Asia/Seoul') "
            "returning id"
        )
    try:
        await _insert_summary(
            db_pool,
            other,
            occurrence_count=9,
            patterns=[
                {
                    "pattern_key": "word_order_in_question",
                    "category": "word_order",
                    "target_form": "의문문 어순",
                    "occurrences": 9,
                    "example": {
                        "original_span": "Where I can find it",
                        "correction": "Where can I find it",
                        "reason": "의문문은 조동사가 주어 앞에 옵니다.",
                    },
                }
            ],
        )

        response = await api_client.get(DAILY_SUMMARY_PATH)

        assert response.status_code == 200
        assert response.json()["analyzed"] is False
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", other)
