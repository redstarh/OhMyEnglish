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
from conftest import job_row

from app.services import sessions as sessions_module
from app.services.jobs import (
    BACKOFF,
    JOB_TYPE_PLAN,
    LEASE,
    LEASE_EXPIRED_ERROR,
    MAX_ATTEMPTS,
    ClaimedJob,
    claim_next,
    complete,
    enqueue_analyze,
    enqueue_plan_next_session,
    fail_or_retry,
)
from app.services.sessions import end_session, mark_session_ended

# 고정 사용자 id — `tests/unit/test_schema.py`·`test_chronic.py`와 같은 패턴이다.
# `db_conn`은 매 테스트 롤백되는 트랜잭션이라 시딩된 사용자가 없다(§ conftest 참조).
_USER_ID = UUID("00000000-0000-0000-0000-000000000001")


async def _insert_user(conn: asyncpg.Connection) -> None:
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'Plan Job Test User', 'Asia/Seoul', 'A2')",
        _USER_ID,
    )


async def _insert_session(conn: asyncpg.Connection, session_id: UUID) -> None:
    await conn.execute(
        "insert into learning_sessions (id, user_id, mode) values ($1, $2, 'speaking')",
        session_id,
        _USER_ID,
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


async def _expire_lease(conn: asyncpg.Connection, job_id: UUID) -> None:
    """Push `locked_at` beyond the lease window instead of waiting for it."""
    await conn.execute(
        "update analysis_jobs set locked_at = now() - $2::interval where id = $1",
        job_id,
        LEASE + timedelta(minutes=1),
    )


async def _enqueued(conn: asyncpg.Connection) -> UUID:
    """New utterance → enqueue → assert registration succeeded, in one call.

    Most tests here only need the resulting job id, not the utterance id —
    this collapses the 3-line "insert utterance, enqueue, assert not None"
    sequence that would otherwise repeat with the same comment across the
    suite."""
    utterance_id = await _new_utterance(conn)
    job_id = await enqueue_analyze(conn, utterance_id)
    assert job_id is not None  # 등록 성공을 전제하는 테스트 — 이후 호출은 UUID를 받는다
    return job_id


# 설계 발명값 상수는 코드가 SoT다 — 테스트는 값을 재선언하지 않고 import해서 쓴다.
def test_queue_constants_are_the_documented_design_values():
    assert LEASE == timedelta(minutes=5)
    assert MAX_ATTEMPTS == 5
    assert BACKOFF == timedelta(minutes=1)
    assert LEASE_EXPIRED_ERROR == "max attempts exceeded (lease expired without report)"


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
    assert job_id is not None  # 등록 성공을 전제하는 테스트 — 이후 호출은 UUID를 받는다

    claimed = await claim_next(db_conn)

    assert isinstance(claimed, ClaimedJob)
    assert claimed.id == job_id
    assert claimed.utterance_id == utterance_id
    assert claimed.attempts == 1
    assert len(claimed.lease_token) == 32  # uuid4().hex

    row = await job_row(db_conn, job_id)
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
    job_id = await _enqueued(db_conn)
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
#
# ✅ **뮤테이션 KILL 확인 — W4** (`TASK-73` · 결정 48. 2026-09-10 직접 관측).
# `services/jobs.complete` 의 `where … and locked_by = $2` 를 `and ($2 = $2)` 로(인자 수를 유지한
# 항진식) 바꿔 **소유자 검증만** 무력화하니 **3건이 FAIL** 했다: 이 테스트 ·
# `test_pipeline.py::test_result_write_is_rolled_back_when_the_lease_was_lost` ·
# `test_plan_pipeline.py::test_a_lost_lease_rolls_everything_back_without_reporting_failure`.
# ⚠️ 단위 하나가 아니라 **세 계층이 같은 술어에 걸려 있다** — 분석·계획 두 파이프라인이 이 가드로
# 롤백을 판정한다.
async def test_expired_lease_is_reclaimed_and_stale_token_cannot_complete(
    db_conn: asyncpg.Connection,
):
    job_id = await _enqueued(db_conn)

    first = await claim_next(db_conn)
    assert first is not None
    await _expire_lease(db_conn, job_id)

    second = await claim_next(db_conn)
    assert second is not None
    assert second.id == job_id
    assert second.lease_token != first.lease_token  # claim 1회당 새 uuid4().hex
    assert second.attempts == 2  # 회수도 attempt를 소비한다

    assert await complete(db_conn, job_id, first.lease_token) is False
    assert (await job_row(db_conn, job_id))["status"] == "running"

    assert await complete(db_conn, job_id, second.lease_token) is True
    assert (await job_row(db_conn, job_id))["status"] == "done"


# Fix round — 좀비 회수(reaper): attempts 상한에 도달한 채 lease만 만료된 running job은
# 6회째 실행되지 않고 terminal `failed`로 수렴한다. 이 경로가 없으면 워커가 아무 보고도
# 못 하고 죽은 job이 영원히 running으로 남아 결과 API가 세션을 "분석 중"에 고정한다.
async def test_zombie_at_attempt_limit_is_reaped_to_failed_instead_of_reclaimed(
    db_conn: asyncpg.Connection,
):
    job_id = await _enqueued(db_conn)
    await db_conn.execute(
        "update analysis_jobs set attempts = $2 where id = $1", job_id, MAX_ATTEMPTS - 1
    )
    claimed = await claim_next(db_conn)  # attempts = MAX_ATTEMPTS, 마지막 실행 기회
    assert claimed is not None
    assert claimed.attempts == MAX_ATTEMPTS
    await _expire_lease(db_conn, job_id)  # 워커가 죽어 complete/fail 보고를 못 한 상태

    assert await claim_next(db_conn) is None  # 상한 초과 실행을 하지 않는다

    row = await job_row(db_conn, job_id)
    assert row["status"] == "failed"
    assert row["last_error"] == LEASE_EXPIRED_ERROR
    assert row["attempts"] == MAX_ATTEMPTS  # reaper는 attempt를 소비하지 않는다
    assert row["locked_at"] is None
    assert row["locked_by"] is None

    # terminal이므로 죽은 워커의 뒤늦은 보고도, 이후의 어떤 claim도 되살리지 못한다.
    assert await complete(db_conn, job_id, claimed.lease_token) is False
    assert await claim_next(db_conn) is None
    assert (await job_row(db_conn, job_id))["status"] == "failed"


# Fix round — 상한 미달 job의 회수는 그대로 유지된다 (reaper가 과잉 수확하지 않는다)
async def test_expired_lease_below_attempt_limit_is_still_reclaimed(
    db_conn: asyncpg.Connection,
):
    job_id = await _enqueued(db_conn)
    await db_conn.execute(
        "update analysis_jobs set attempts = $2 where id = $1", job_id, MAX_ATTEMPTS - 2
    )
    claimed = await claim_next(db_conn)  # attempts = MAX_ATTEMPTS - 1
    assert claimed is not None
    assert claimed.attempts == MAX_ATTEMPTS - 1
    await _expire_lease(db_conn, job_id)

    recovered = await claim_next(db_conn)

    assert recovered is not None
    assert recovered.id == job_id
    assert recovered.attempts == MAX_ATTEMPTS
    assert recovered.lease_token != claimed.lease_token
    row = await job_row(db_conn, job_id)
    assert row["status"] == "running"
    assert row["last_error"] is None  # reaper가 건드리지 않았다


# ④ attempts 상한 도달 실패 → failed + last_error, 재claim 안 됨 (W5)
#
# ✅ **뮤테이션 KILL 확인 — W5. ⛔ 그런데 두 변이가 서로 다른 테스트에 걸린다**
# (`TASK-73`. 2026-09-10 직접 관측 — 이것이 이 회차에서 가장 값어치 있는 발견이다).
#   ⑴ `MAX_ATTEMPTS` 를 `5` → `500` 으로 바꾸면 **이 테스트는 통과하고**
#      `test_queue_constants_are_the_documented_design_values` 만 FAIL 한다. 이 테스트가 상수를
#      참조해 기대값을 만들기 때문에 **상수를 따라가 버린다.**
#   ⑵ 상수를 그대로 두고 `fail_or_retry` 의 `attempts::int >= $4::int` 를 `>` 로 바꾸면(상한이 1
#      늘어난다) **이 테스트가 FAIL** 하고 상수 단정은 통과한다.
# ⛔ **그래서 둘 중 하나만 있으면 W5 의 절반이 무보호다.** 상수 단정은 「값이 5인가」를 지키고 이
# 테스트는 「경계 연산이 맞는가」를 지킨다 — 누군가 상수와 그 단정을 **함께** 고치면 이 테스트만
# 남고, 반대로 이 테스트만 있으면 상수가 조용히 바뀌어도 통과한다.
async def test_failure_at_attempt_limit_marks_failed_and_is_never_reclaimed(
    db_conn: asyncpg.Connection,
):
    job_id = await _enqueued(db_conn)
    await db_conn.execute(
        "update analysis_jobs set attempts = $2 where id = $1", job_id, MAX_ATTEMPTS - 1
    )

    claimed = await claim_next(db_conn)
    assert claimed is not None
    assert claimed.attempts == MAX_ATTEMPTS

    assert await fail_or_retry(db_conn, job_id, claimed.lease_token, "bedrock timeout") is True

    row = await job_row(db_conn, job_id)
    assert row["status"] == "failed"
    assert row["last_error"] == "bedrock timeout"

    assert await claim_next(db_conn) is None
    await _expire_lease(db_conn, job_id)  # failed는 lease 회수 대상도 아니다
    assert await claim_next(db_conn) is None


# ⑤ 백오프: attempts=2에서 재큐되면 available_at ≈ now() + 2분
async def test_retry_before_limit_requeues_with_attempt_scaled_backoff(
    db_conn: asyncpg.Connection,
):
    job_id = await _enqueued(db_conn)
    await db_conn.execute("update analysis_jobs set attempts = 1 where id = $1", job_id)

    claimed = await claim_next(db_conn)
    assert claimed is not None
    assert claimed.attempts == 2

    assert await fail_or_retry(db_conn, job_id, claimed.lease_token, "transient error") is True

    row = await job_row(db_conn, job_id)
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


# Fix round 2 (I-2) — 백오프 기준 시계는 주입 가능해야 한다
async def test_fail_or_retry_computes_backoff_from_injected_clock(db_conn: asyncpg.Connection):
    job_id = await _enqueued(db_conn)
    await db_conn.execute("update analysis_jobs set attempts = 1 where id = $1", job_id)
    claimed = await claim_next(db_conn)
    assert claimed is not None
    assert claimed.attempts == 2
    at = datetime.now(UTC) + timedelta(hours=2)

    assert (
        await fail_or_retry(db_conn, job_id, claimed.lease_token, "transient error", now=at) is True
    )

    available_at = await db_conn.fetchval(
        "select available_at from analysis_jobs where id = $1", job_id
    )
    assert available_at == at + 2 * BACKOFF


# Fix round 2 (I-2) — 기본 시계는 문장 시계(clock_timestamp)여야 한다.
# Postgres `now()`는 transaction_timestamp라 문장 사이에 전진하지 않는다: 한 트랜잭션
# 안에서 claim 후 분석에 4분이 걸렸다면 `now()` 기준 백오프는 이미 지나간 시각을 가리켜
# 사실상 0이 된다. available_at이 문장 시계 기준이면 트랜잭션 시작 이후 경과한 만큼
# `now()`와의 차이가 백오프보다 반드시 크다.
async def test_fail_or_retry_backoff_is_measured_from_statement_clock_not_transaction_start(
    db_conn: asyncpg.Connection,
):
    job_id = await _enqueued(db_conn)
    await db_conn.execute("update analysis_jobs set attempts = 1 where id = $1", job_id)
    claimed = await claim_next(db_conn)
    assert claimed is not None

    assert await fail_or_retry(db_conn, job_id, claimed.lease_token, "transient error") is True

    delay = await db_conn.fetchval(
        "select available_at - now() from analysis_jobs where id = $1", job_id
    )
    assert delay > 2 * BACKOFF, delay
    assert delay < 2 * BACKOFF + timedelta(minutes=1), delay


# ⑤ 보강 — 만료된 token으로는 재큐도 불가 (0행 → False)
async def test_fail_or_retry_with_wrong_token_changes_nothing(db_conn: asyncpg.Connection):
    job_id = await _enqueued(db_conn)
    claimed = await claim_next(db_conn)
    assert claimed is not None

    assert await fail_or_retry(db_conn, job_id, uuid4().hex, "not my job") is False

    row = await job_row(db_conn, job_id)
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


# Task 2 — plan_next_session job 등록 (설계서 §3.1). Task 1이 만든 CHECK/partial unique를
# 그대로 탄다: 대상 컬럼은 (session_id is not null and utterance_id is null), 중복 방지는
# uq_analysis_jobs_pending_session이 (job_type, session_id)로 이미 걸어 둔 것을 쓴다.
async def test_enqueue_plan_next_session_registers_one_job(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    job_id = await enqueue_plan_next_session(db_conn, session_id)

    assert job_id is not None
    row = await db_conn.fetchrow(
        "select job_type, session_id, utterance_id, status from analysis_jobs where id = $1",
        job_id,
    )
    assert row["job_type"] == JOB_TYPE_PLAN
    assert row["session_id"] == session_id
    assert row["utterance_id"] is None
    assert row["status"] == "pending"


async def test_enqueue_plan_next_session_is_idempotent_while_pending(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    first = await enqueue_plan_next_session(db_conn, session_id)
    second = await enqueue_plan_next_session(db_conn, session_id)

    assert first is not None
    assert second is None
    assert (
        await db_conn.fetchval(
            "select count(*) from analysis_jobs where job_type = $1", JOB_TYPE_PLAN
        )
        == 1
    )


# Task 3: claim_next 가 job_type·session_id 를 함께 돌려준다 — 이전에는 utterance_id의
# 유무로 종류를 추측했는데 그러면 계획 job이 "대상 없음"으로 즉시 실패했다.
async def test_claim_next_reports_job_type_and_session_target(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)
    await enqueue_plan_next_session(db_conn, session_id)

    claimed = await claim_next(db_conn)

    assert claimed is not None
    assert claimed.job_type == JOB_TYPE_PLAN
    assert claimed.session_id == session_id
    assert claimed.utterance_id is None


# 설계서 §3.1: 종료 기록과 job 등록이 한 트랜잭션이다. 분리하면 그 사이 크래시에서
# 다음 계획이 영구히 만들어지지 않는다.
async def test_end_session_enqueues_plan_job_in_same_transaction(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    await end_session(db_conn, session_id, "completed")

    assert (
        await db_conn.fetchval(
            "select count(*) from analysis_jobs where job_type = $1 and session_id = $2",
            JOB_TYPE_PLAN,
            session_id,
        )
        == 1
    )


# 이미 닫힌 세션을 다시 닫으려 하면 job 이 늘지 않는다 — end_session 의 active 가드가
# 실제로 닫았는지(`closed`)를 보기 때문이다.
#
# ⚠️ 리뷰 라운드 2(Important 2) — 첫 job을 pending에 둔 채로만 재호출하면 이 테스트는
# 가드를 재지 못한다: 두 번째 등록이 여전히 pending인 job과
# `uq_analysis_jobs_pending_session`에서 충돌하고 `on conflict do nothing`이 그것을
# 삼켜 count가 1로 유지된다 — `sessions.py`의 가드 `return`을 지워도 이 테스트는
# 그대로 초록이었다(부분 유니크가 대신 막아 준 것이라 가드 자체는 미검증). 첫 job을
# `done`으로 올려 부분 유니크의 범위(`status in ('pending','running')`) 밖으로
# 보내면 그 방어가 물러나고, 남는 것은 오직 `end_session`의 `closed is None` 가드뿐이다.
async def test_end_session_does_not_enqueue_when_already_closed(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    await end_session(db_conn, session_id, "failed")
    # 첫 job을 done으로 밀어 partial unique의 범위(pending/running) 밖으로 보낸다 —
    # 그래야 아래 재호출에서 job이 늘지 않는 이유가 가드 하나로 좁혀진다.
    await db_conn.execute(
        "update analysis_jobs set status = 'done' where job_type = $1 and session_id = $2",
        JOB_TYPE_PLAN,
        session_id,
    )

    await end_session(db_conn, session_id, "completed")

    assert (
        await db_conn.fetchval(
            "select count(*) from analysis_jobs where session_id = $1", session_id
        )
        == 1
    )


# Minor 1 (리뷰 라운드 2) — 위 `test_end_session_enqueues_plan_job_in_same_transaction`은
# `db_conn` 픽스처(트랜잭션 하나) 안에서 돈다. 그 안에서는 경계가 구조적으로 하나뿐이라
# "받은 연결로 job을 1건 건다"까지만 재고, 프로덕션 호출자(`mark_session_ended`)가 실제로
# 트랜잭션을 여는지는 재지 못한다 — Important 1에서 바로 그 경계가 빠져 있었다(`asyncpg`는
# 명시적 `conn.transaction()`이 없으면 문장마다 autocommit이라, 종료 UPDATE가 커밋된 뒤
# 계획 job INSERT 전에 죽으면 그 세션의 계획이 영구히 만들어지지 않는다). 이 테스트가 그
# 경계의 직접 증거다: `db_pool`로 실제 커밋 경로를 타고, 두 번째 쓰기(계획 job 등록)가
# 실패하면 첫 번째 쓰기(종료 UPDATE)까지 롤백되는지 — 즉 세션이 여전히 `active`인지 본다.
async def test_mark_session_ended_rolls_back_the_close_when_plan_enqueue_fails(
    db_pool: asyncpg.Pool, committed_session, monkeypatch: pytest.MonkeyPatch
):
    def _boom(conn: asyncpg.Connection, session_id: UUID) -> None:
        raise RuntimeError("simulated crash before the plan job commits")

    monkeypatch.setattr(sessions_module, "enqueue_plan_next_session", _boom)

    with pytest.raises(RuntimeError, match="simulated crash"):
        await mark_session_ended(db_pool, committed_session.session_id, "completed")

    async with db_pool.acquire() as conn:
        status = await conn.fetchval(
            "select status from learning_sessions where id = $1",
            committed_session.session_id,
        )
    assert status == "active", "종료 UPDATE가 계획 job 등록 실패에도 커밋됐다 — 트랜잭션이 없다"
