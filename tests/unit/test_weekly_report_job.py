"""`weekly_report.process_weekly` 와 그 배선 (`TASK-26.4`).

설계: `docs/design/2026-09-14-weekly-report-design.md` §6.

⛔ **재는 것 가운데 둘이 판별력용이다.** 「정상 응답이 저장된다」만 재면 **무엇을 넣어도 저장하는
구현**도 통과하고, 「0건 주가 닫힌다」만 재면 **모델을 늘 부르는 구현**도 통과한다. 그래서 모델
호출 여부와 토큰 기록을 함께 관측한다.

⚠️ 이 파일은 `db_pool`(커밋되는 픽스처)을 쓴다 — `process_weekly` 가 pool 을 받고 저장이 job 완료와
**한 트랜잭션**이어야 하므로 롤백 픽스처로는 그 결합을 잴 수 없다.

⛔⛔ **`db_pool` 은 아무것도 정리하지 않는다 — 손으로 지운다.** 순서가 중요하다: **사용자를 먼저**
지워야 세션·발화·job·리포트가 cascade 된다.
"""

from __future__ import annotations

import json
from typing import cast
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio

from app.models.weekly_report import EMPTY_INSIGHTS, MAX_INSIGHT_POINTS
from app.services.jobs import JOB_TYPE_SUMMARIZE_WEEK, ClaimedJob
from app.services.weekly_report import last_week_start, process_weekly

# 이 모듈이 만든 행의 표지. ⛔ 정리가 이 값에 걸리므로 다른 파일과 겹치지 않는 이름이어야 한다.
_MARK = "weekly-job-test"


def _reply(**overrides: object) -> str:
    body: dict[str, object] = {
        "improving": ["관사를 붙인 문장이 지난 주보다 늘었어요."],
        "next_scenarios": ["업무 상태 보고에서 과거 시제를 연습해요."],
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


class _StubClaude:
    """고정 응답을 돌려주는 대역.

    ⛔ **단정을 여기서 하지 않는다** — `process_weekly` 의 broad `except` 가 `AssertionError` 를
    삼켜 「저장 실패」로 잘못 보고한다. 관측만 하고 판정은 테스트 본문에서 한다.
    """

    def __init__(self, response: str) -> None:
        self._response = response
        self.prompts: list[str] = []
        self.purposes: list[str | None] = []

    async def analyze(self, prompt: str, **kwargs: object) -> str:
        self.prompts.append(prompt)
        purpose = kwargs.get("purpose")
        self.purposes.append(purpose if isinstance(purpose, str) else None)
        return self._response


@pytest_asyncio.fixture
async def user_id(db_pool: asyncpg.Pool):
    """표지가 붙은 사용자 하나 — 끝나면 지워 cascade 시킨다."""
    async with db_pool.acquire() as conn:
        created = await conn.fetchval(
            "insert into users (display_name, timezone, current_level) "
            "values ($1, 'Asia/Seoul', 'A2') returning id",
            _MARK,
        )
    yield created
    async with db_pool.acquire() as conn:
        await conn.execute("delete from users where display_name = $1", _MARK)


async def _session(conn: asyncpg.Connection, owner: UUID) -> UUID:
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        owner,
    )


async def _claimed(conn: asyncpg.Connection, session_id: UUID) -> ClaimedJob:
    """job 을 넣고 claim 된 모양으로 만든다 — 워커 루프를 돌리지 않고 그 자리만 흉내 낸다."""
    token = uuid4().hex
    job_id = await conn.fetchval(
        "insert into analysis_jobs (job_type, session_id, status, locked_by, locked_at, attempts) "
        "values ($1, $2, 'running', $3, now(), 1) returning id",
        JOB_TYPE_SUMMARIZE_WEEK,
        session_id,
        token,
    )
    return ClaimedJob(
        id=job_id,
        job_type=JOB_TYPE_SUMMARIZE_WEEK,
        utterance_id=None,
        session_id=session_id,
        lease_token=token,
        attempts=1,
    )


@pytest.mark.asyncio
async def test_a_quiet_week_is_closed_without_calling_the_model(
    db_pool: asyncpg.Pool, user_id: UUID
) -> None:
    """⛔ 사실이 0건이면 **모델을 부르지 않고** 빈 모양으로 닫는다.

    ⚠️ 그 값이 `{}`(아직 없음)와 달라야 한다 — 「만들었고 담을 것이 없었다」를 값의 **모양**으로
    말하는 것이 총평이 세운 규약이고, 화면까지 그 구별이 도달한다.
    ⚠️ 모델을 부르기 **전에** 이 갈래를 두는 이유: 뒤에 두면 빈 기록으로 토큰이 나간다.
    """
    async with db_pool.acquire() as conn:
        session_id = await _session(conn, user_id)
        job = await _claimed(conn, session_id)
        week = await last_week_start(conn, user_id)
    claude = _StubClaude(_reply())

    await process_weekly(db_pool, cast("object", claude), job)  # ty: ignore[invalid-argument-type]

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "select insights, metrics, computed_at from weekly_reports "
            "where user_id = $1 and week_start = $2",
            user_id,
            week,
        )
        status = await conn.fetchval("select status from analysis_jobs where id = $1", job.id)

    assert claude.prompts == [], "0건 주인데 모델을 불렀다"
    assert row is not None
    insights = row["insights"]
    assert (json.loads(insights) if isinstance(insights, str) else insights) == EMPTY_INSIGHTS
    assert row["computed_at"] is not None
    assert status == "done"


@pytest.mark.asyncio
async def test_the_model_reply_is_stored_and_the_token_record_lands(
    db_pool: asyncpg.Pool, user_id: UUID
) -> None:
    """정상 응답이 `insights` 로 들어가고 **토큰 기록이 행으로 남는다**.

    ⚠️ `TASK-134` 가 토큰 기록이 **조용히 사라지는** 결함을 잡았으므로 「값역이 열렸다」가 아니라
    **행이 남는지**를 센다. 이 테스트의 대역은 사용량을 보고하지 않으므로 여기서 재는 것은
    `purpose` 가 무엇으로 넘어가는지다 — 실제 행은 `ClaudeClient` 가 남긴다.
    """
    async with db_pool.acquire() as conn:
        session_id = await _session(conn, user_id)
        job = await _claimed(conn, session_id)
        week = await last_week_start(conn, user_id)
        # 그 주에 발화 하나와 오류 하나를 심어 사실을 0건이 아니게 만든다.
        pattern_id = await conn.fetchval(
            "insert into error_patterns (user_id, category, pattern_key, target_form) "
            "values ($1, 'article', 'article_missing', 'the report') returning id",
            user_id,
        )
        utterance_id = await conn.fetchval(
            "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
            "values ($1, 'user', 'I sent report.', 1, "
            "($2::date + time '12:00') at time zone 'Asia/Seoul') returning id",
            session_id,
            week,
        )
        await conn.execute(
            "insert into error_occurrences (utterance_id, pattern_id, original_span, correction, "
            "explanation, severity, confidence) "
            "values ($1, $2, 'sent report', 'sent the report', '관사 누락', 'medium', 0.9)",
            utterance_id,
            pattern_id,
        )
    claude = _StubClaude(_reply())

    await process_weekly(db_pool, cast("object", claude), job)  # ty: ignore[invalid-argument-type]

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "select metrics, insights from weekly_reports where user_id = $1 and week_start = $2",
            user_id,
            week,
        )
        status = await conn.fetchval("select status from analysis_jobs where id = $1", job.id)

    assert claude.purposes == [JOB_TYPE_SUMMARIZE_WEEK], "토큰 기록의 purpose 가 어긋난다"
    assert row is not None
    insights = row["insights"]
    parsed = json.loads(insights) if isinstance(insights, str) else insights
    assert parsed["improving"] == ["관사를 붙인 문장이 지난 주보다 늘었어요."]
    metrics = row["metrics"]
    facts = json.loads(metrics) if isinstance(metrics, str) else metrics
    # ⛔ 사실이 판단과 **같은 행**에 있다 — 나누면 재분석이 사실을 바꿔 판단과 어긋난다(설계서 §5).
    assert facts["occurrence_count"] == 1
    assert facts["top_patterns"][0]["pattern_key"] == "article_missing"
    assert status == "done"


@pytest.mark.asyncio
async def test_processing_twice_keeps_one_row(db_pool: asyncpg.Pool, user_id: UUID) -> None:
    """멱등이다 — 재시도가 행을 늘리지 않는다(`unique (user_id, week_start)` 가 뿌리다)."""
    async with db_pool.acquire() as conn:
        session_id = await _session(conn, user_id)
        first = await _claimed(conn, session_id)
    await process_weekly(db_pool, cast("object", _StubClaude(_reply())), first)  # ty: ignore[invalid-argument-type]
    async with db_pool.acquire() as conn:
        second = await _claimed(conn, await _session(conn, user_id))
    await process_weekly(db_pool, cast("object", _StubClaude(_reply())), second)  # ty: ignore[invalid-argument-type]

    async with db_pool.acquire() as conn:
        count = await conn.fetchval(
            "select count(*) from weekly_reports where user_id = $1", user_id
        )

    assert count == 1


@pytest.mark.asyncio
async def test_a_broken_reply_is_not_stored(db_pool: asyncpg.Pool, user_id: UUID) -> None:
    """⛔ **판별력** — 규격을 벗어난 응답은 저장되지 않는다.

    이 단정이 없으면 「무엇을 받아도 저장하는」 구현이 통과한다. 그때 `weekly_reports` 행은 만들어
    지지 않고 job 이 실패로 보고돼 재시도에 맡겨진다.
    """
    async with db_pool.acquire() as conn:
        session_id = await _session(conn, user_id)
        job = await _claimed(conn, session_id)
        week = await last_week_start(conn, user_id)
        # ⛔ 사실을 0건이 아니게 만든다 — 그렇지 않으면 모델을 부르지 않고 닫혀서 이 단정이
        # **모델 응답과 무관한 것을 잰다.** ⚠️ 그러려면 발화가 «지난 주»에 있어야 한다: `now()` 로
        # 심었더니 이번 주라 0건 갈래가 먼저 걸렸다(이 테스트를 쓰다가 실제로 그랬다).
        await conn.execute(
            "update learning_sessions set started_at = "
            "($2::date + time '12:00') at time zone 'Asia/Seoul' where id = $1",
            session_id,
            week,
        )
        await conn.execute(
            "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
            "values ($1, 'user', 'I sent report.', 1, "
            "($2::date + time '12:00') at time zone 'Asia/Seoul')",
            session_id,
            week,
        )
    broken = _StubClaude(_reply(score=90))

    await process_weekly(db_pool, cast("object", broken), job)  # ty: ignore[invalid-argument-type]

    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select count(*) from weekly_reports where user_id = $1", user_id
        )
        status = await conn.fetchval("select status from analysis_jobs where id = $1", job.id)

    assert stored == 0, "규격을 벗어난 응답이 저장됐다"
    assert status != "done"


def test_the_insight_cap_matches_the_prompt() -> None:
    """상한이 프롬프트와 파서에서 같은 수다 — 어긋나면 정상 응답이 매번 거부된다."""
    assert MAX_INSIGHT_POINTS == 3
