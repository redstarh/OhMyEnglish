"""Task 3 — `app.services.jobs` PostgreSQL job queue tests (AC W3 후반·W4·W5).

Uses the `db_conn` fixture from `tests/conftest.py`: a connection to the
migrated `ohmyenglish_test` database inside a transaction that is always
rolled back.

Time-dependent behaviour (lease expiry, retry backoff) is never tested by
sleeping in real time — `locked_at` / `available_at` are pushed into the past
with SQL, and `claim_next(now=...)` injects the clock. Every timestamp that
crosses the Python boundary is timezone-aware (`timestamptz` / `UTC`).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest

from app.services.jobs import (
    BACKOFF,
    LEASE,
    MAX_ATTEMPTS,
    ClaimedJob,
    claim_next,
    complete,
    enqueue_analyze,
    fail_or_retry,
)


async def _new_utterance(conn: asyncpg.Connection, *, sequence_no: int = 1) -> UUID:
    """Insert user → session → utterance and return the utterance id."""
    user_id = await conn.fetchval(
        "insert into users (display_name) values ('Queue Test User') returning id"
    )
    session_id = await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        user_id,
    )
    return await conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no) "
        "values ($1, 'user', 'I usually go to gym after work.', $2) returning id",
        session_id,
        sequence_no,
    )


async def _job_row(conn: asyncpg.Connection, job_id: UUID) -> asyncpg.Record:
    row = await conn.fetchrow(
        "select status, attempts, locked_at, locked_by, last_error, available_at "
        "from analysis_jobs where id = $1",
        job_id,
    )
    assert row is not None, f"analysis_jobs row {job_id} disappeared"
    return row


async def _expire_lease(conn: asyncpg.Connection, job_id: UUID) -> None:
    """Push `locked_at` beyond the lease window instead of waiting for it."""
    await conn.execute(
        "update analysis_jobs set locked_at = now() - $2::interval where id = $1",
        job_id,
        LEASE + timedelta(minutes=1),
    )


# 설계 발명값 상수는 코드가 SoT다 — 테스트는 값을 재선언하지 않고 import해서 쓴다.
def test_queue_constants_are_the_documented_design_values():
    assert LEASE == timedelta(minutes=5)
    assert MAX_ATTEMPTS == 5
    assert BACKOFF == timedelta(minutes=1)


# ① 같은 발화를 다시 enqueue → None (partial unique uq_analysis_jobs_pending_utterance)
async def test_enqueue_analyze_returns_none_for_duplicate_pending_utterance(
    db_conn: asyncpg.Connection,
):
    utterance_id = await _new_utterance(db_conn)

    job_id = await enqueue_analyze(db_conn, utterance_id)
    duplicate = await enqueue_analyze(db_conn, utterance_id)

    assert isinstance(job_id, UUID)
    assert duplicate is None
    # 충돌이 트랜잭션을 죽이지 않아야 한다 (Task 4가 같은 트랜잭션 안에서 호출한다).
    assert await db_conn.fetchval("select count(*) from analysis_jobs") == 1


# ② claim이 lease token을 발급하고 attempts를 증가시킨다
async def test_claim_next_issues_lease_token_and_increments_attempts(
    db_conn: asyncpg.Connection,
):
    utterance_id = await _new_utterance(db_conn)
    job_id = await enqueue_analyze(db_conn, utterance_id)

    claimed = await claim_next(db_conn)

    assert isinstance(claimed, ClaimedJob)
    assert claimed.id == job_id
    assert claimed.utterance_id == utterance_id
    assert claimed.attempts == 1
    assert len(claimed.lease_token) == 32  # uuid4().hex

    row = await _job_row(db_conn, job_id)
    assert row["status"] == "running"
    assert row["attempts"] == 1
    assert row["locked_by"] == claimed.lease_token
    assert row["locked_at"] is not None
    assert row["locked_at"].tzinfo is not None

    assert await claim_next(db_conn) is None  # 큐가 비었다


# ② 보강 — claim은 available_at이 도래하지 않은 job을 집지 않는다 (now 주입)
async def test_claim_next_skips_job_whose_available_at_is_in_the_future(
    db_conn: asyncpg.Connection,
):
    utterance_id = await _new_utterance(db_conn)
    job_id = await enqueue_analyze(db_conn, utterance_id)
    await db_conn.execute(
        "update analysis_jobs set available_at = now() + interval '10 minutes' where id = $1",
        job_id,
    )

    assert await claim_next(db_conn) is None

    later = datetime.now(UTC) + timedelta(minutes=11)
    claimed = await claim_next(db_conn, now=later)
    assert claimed is not None
    assert claimed.id == job_id


# naive datetime은 경계에서 거부한다 (전역 제약: aware/timestamptz만)
async def test_claim_next_rejects_naive_now(db_conn: asyncpg.Connection):
    with pytest.raises(ValueError, match="aware"):
        await claim_next(db_conn, now=datetime(2026, 8, 25, 9, 0, 0))  # noqa: DTZ001


# ③ lease 만료된 running job은 회수되고, 이전 token의 complete는 False (W4)
async def test_expired_lease_is_reclaimed_and_stale_token_cannot_complete(
    db_conn: asyncpg.Connection,
):
    utterance_id = await _new_utterance(db_conn)
    job_id = await enqueue_analyze(db_conn, utterance_id)

    first = await claim_next(db_conn)
    assert first is not None
    await _expire_lease(db_conn, job_id)

    second = await claim_next(db_conn)
    assert second is not None
    assert second.id == job_id
    assert second.lease_token != first.lease_token  # claim 1회당 새 uuid4().hex
    assert second.attempts == 2  # 회수도 attempt를 소비한다

    assert await complete(db_conn, job_id, first.lease_token) is False
    assert (await _job_row(db_conn, job_id))["status"] == "running"

    assert await complete(db_conn, job_id, second.lease_token) is True
    assert (await _job_row(db_conn, job_id))["status"] == "done"


# ④ attempts 상한 도달 실패 → failed + last_error, 재claim 안 됨 (W5)
async def test_failure_at_attempt_limit_marks_failed_and_is_never_reclaimed(
    db_conn: asyncpg.Connection,
):
    utterance_id = await _new_utterance(db_conn)
    job_id = await enqueue_analyze(db_conn, utterance_id)
    await db_conn.execute(
        "update analysis_jobs set attempts = $2 where id = $1", job_id, MAX_ATTEMPTS - 1
    )

    claimed = await claim_next(db_conn)
    assert claimed is not None
    assert claimed.attempts == MAX_ATTEMPTS

    assert await fail_or_retry(db_conn, job_id, claimed.lease_token, "bedrock timeout") is True

    row = await _job_row(db_conn, job_id)
    assert row["status"] == "failed"
    assert row["last_error"] == "bedrock timeout"

    assert await claim_next(db_conn) is None
    await _expire_lease(db_conn, job_id)  # failed는 lease 회수 대상도 아니다
    assert await claim_next(db_conn) is None


# ⑤ 백오프: attempts=2에서 재큐되면 available_at ≈ now() + 2분
async def test_retry_before_limit_requeues_with_attempt_scaled_backoff(
    db_conn: asyncpg.Connection,
):
    utterance_id = await _new_utterance(db_conn)
    job_id = await enqueue_analyze(db_conn, utterance_id)
    await db_conn.execute("update analysis_jobs set attempts = 1 where id = $1", job_id)

    claimed = await claim_next(db_conn)
    assert claimed is not None
    assert claimed.attempts == 2

    assert await fail_or_retry(db_conn, job_id, claimed.lease_token, "transient error") is True

    row = await _job_row(db_conn, job_id)
    assert row["status"] == "pending"
    assert row["last_error"] == "transient error"
    assert row["locked_by"] is None
    delay = await db_conn.fetchval(
        "select available_at - now() from analysis_jobs where id = $1", job_id
    )
    assert timedelta(seconds=119) <= delay <= timedelta(seconds=121), delay

    # 백오프가 끝나기 전에는 집히지 않고, 지나면 attempts=3으로 집힌다.
    assert await claim_next(db_conn) is None
    reclaimed = await claim_next(
        db_conn, now=datetime.now(UTC) + 2 * BACKOFF + timedelta(minutes=1)
    )
    assert reclaimed is not None
    assert reclaimed.attempts == 3


# ⑤ 보강 — 만료된 token으로는 재큐도 불가 (0행 → False)
async def test_fail_or_retry_with_wrong_token_changes_nothing(db_conn: asyncpg.Connection):
    utterance_id = await _new_utterance(db_conn)
    job_id = await enqueue_analyze(db_conn, utterance_id)
    claimed = await claim_next(db_conn)
    assert claimed is not None

    assert await fail_or_retry(db_conn, job_id, uuid4().hex, "not my job") is False

    row = await _job_row(db_conn, job_id)
    assert row["status"] == "running"
    assert row["locked_by"] == claimed.lease_token
    assert row["last_error"] is None


# ⑥ done 이후 같은 발화 재enqueue는 허용된다 (partial unique는 pending/running만)
async def test_enqueue_is_allowed_again_after_job_is_done(db_conn: asyncpg.Connection):
    utterance_id = await _new_utterance(db_conn)
    first_job_id = await enqueue_analyze(db_conn, utterance_id)
    claimed = await claim_next(db_conn)
    assert claimed is not None
    assert await complete(db_conn, claimed.id, claimed.lease_token) is True

    second_job_id = await enqueue_analyze(db_conn, utterance_id)

    assert isinstance(second_job_id, UUID)
    assert second_job_id != first_job_id
    assert await db_conn.fetchval("select count(*) from analysis_jobs") == 2


# complete는 이미 done인 job에 두 번 성공하지 않는다 (멱등 경계)
async def test_complete_is_not_repeatable_for_the_same_lease(db_conn: asyncpg.Connection):
    utterance_id = await _new_utterance(db_conn)
    await enqueue_analyze(db_conn, utterance_id)
    claimed = await claim_next(db_conn)
    assert claimed is not None

    assert await complete(db_conn, claimed.id, claimed.lease_token) is True
    assert await complete(db_conn, claimed.id, claimed.lease_token) is False


# 존재하지 않는 job id로 호출해도 예외 없이 False
async def test_complete_and_fail_return_false_for_unknown_job(db_conn: asyncpg.Connection):
    unknown = uuid4()

    assert await complete(db_conn, unknown, uuid4().hex) is False
    assert await fail_or_retry(db_conn, unknown, uuid4().hex, "nope") is False


# enqueue는 존재하지 않는 발화를 받아들이지 않는다 (FK 경계)
async def test_enqueue_rejects_unknown_utterance(db_conn: asyncpg.Connection):
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await enqueue_analyze(db_conn, uuid4())
