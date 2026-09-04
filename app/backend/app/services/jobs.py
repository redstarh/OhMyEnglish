"""`analysis_jobs` — PostgreSQL-backed job queue with lease tokens (설계서 §5.4).

No broker: the queue is one table claimed with `for update skip locked`, which
is what keeps "at most one worker per job" true without a second piece of
infrastructure. Three properties carry the correctness of the whole pipeline:

* **멱등 등록** — the partial unique index `uq_analysis_jobs_pending_utterance`
  covers only `status in ('pending','running')`, so re-registering an utterance
  that is still queued is a no-op (`None`), while re-registering one whose job
  already finished is allowed (re-analysis). `uq_analysis_jobs_pending_session`
  is the same shape for `session_id` — it is what makes `enqueue_plan_next_session`
  idempotent while a `plan_next_session` job for that session is still pending/running.
* **lease token** — a fresh `uuid4().hex` is minted *per claim*, not per worker.
  Every terminal update is gated on `status='running' and locked_by=$token`, so
  a worker whose lease expired and whose job was reclaimed by someone else can
  no longer write the outcome: it gets `False` and must drop the work.
* **회수(recovery)** — a `running` job whose `locked_at` is older than `LEASE`
  and that still has attempts left is claimable again by the very same query
  that claims `pending` jobs, so a crashed worker's job resumes on its own.
  One whose attempts are exhausted is instead reaped to terminal `failed` at
  the top of `claim_next`, so it can neither run a 6th time nor sit in
  `running` forever (both would be visible to the user: the first as duplicate
  Claude spend, the second as a session stuck on "analyzing").

설계 발명값 (PRD/요구사항에 없는 운영 파라미터 — 이 세 상수는 설계 단계에서
정한 값이며, 근거는 "5분이면 Claude 1회 호출이 확실히 끝난다 / 5회면 일시적
장애는 흡수하고 영구 장애는 빨리 포기한다"는 판단이다):

* `LEASE = 5분`
* `MAX_ATTEMPTS = 5`  (attempts는 claim 시점에 증가하므로 최대 5회 실행)
* `BACKOFF = 1분` × attempts (선형 백오프: 1분, 2분, 3분, 4분)

The SQL keeps these as bound parameters rather than inlined literals so the
Python constants above stay the single source of truth.

**호출 계약 — 큐 함수는 각각 짧은 자기 트랜잭션에서 호출한다.** 워커는
`claim_next` → (분석) → `complete`/`fail_or_retry`를 하나의 긴 트랜잭션으로
묶지 않는다. lease를 잡은 뒤 Claude 호출이 끝날 때까지 트랜잭션을 열어두면
① 그 시간 내내 행 잠금과 스냅샷을 붙들어 다른 워커의 claim을 방해하고
② 실패 보고가 커밋되지 못한 채 프로세스가 죽으면 lease 만료까지 아무 진전이
없다. 시계도 마찬가지 이유로 `now()`(=transaction_timestamp, 문장 사이에
전진하지 않는다)가 아니라 `clock_timestamp()`를 기본값으로 쓴다 — 긴
트랜잭션에서 백오프가 0으로 붕괴하는 것을 막는다. 테스트/재현을 위해
`claim_next`와 `fail_or_retry`는 aware datetime을 `now=`로 주입받는다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import asyncpg

logger = logging.getLogger(__name__)

# --- 설계 발명값 (design-invented values, see module docstring) ---
LEASE = timedelta(minutes=5)
MAX_ATTEMPTS = 5
BACKOFF = timedelta(minutes=1)

JOB_TYPE_ANALYZE = "analyze_utterance"
JOB_TYPE_PLAN = "plan_next_session"

# reaper가 좀비 job에 남기는 사유 (아래 `_REAP_ZOMBIES_SQL` 참조).
LEASE_EXPIRED_ERROR = "max attempts exceeded (lease expired without report)"


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    """One successful claim. `lease_token` is only valid until `LEASE` elapses.

    `job_type`을 함께 돌려주는 이유: 큐 하나에 종류가 셋이고
    (`analyze_utterance`·`summarize_session`·`plan_next_session`) 대상 컬럼이
    상호배타적이라, **종류를 모르면 어느 대상을 읽어야 하는지 알 수 없다.**
    이전에는 `utterance_id`의 유무로 추측했는데 그러면 계획 job이 "대상 없음"으로
    실패했다(계획서 Task 3).
    """

    id: UUID
    job_type: str
    utterance_id: UUID | None
    session_id: UUID | None
    lease_token: str
    attempts: int


def _require_aware(value: datetime | None) -> datetime | None:
    """Reject naive datetimes at the boundary — every timestamp in this system
    is `timestamptz`/aware, and silently binding a naive value would shift the
    clock by the server's timezone offset."""
    if value is not None and value.tzinfo is None:
        raise ValueError("`now` must be timezone-aware (naive datetime is not allowed)")
    return value


async def enqueue_analyze(conn: asyncpg.Connection, utterance_id: UUID) -> UUID | None:
    """Register an `analyze_utterance` job, or return `None` if one is already
    queued for this utterance.

    `on conflict do nothing` (rather than letting the unique violation raise)
    is deliberate: **호출자가 다른 쓰기와 한 트랜잭션에 있을 수 있고**, 올라온
    violation은 그 트랜잭션을 abort시켜 중복 job 하나 때문에 무관한 쓰기를 잃게
    한다. ⚠️ **원래 근거는 `utterances.save_final_transcript`가 전사문 insert와
    같은 트랜잭션에서 이것을 부른다는 것이었는데, 그 호출자는 I-1(2026-09-01)에서
    사라졌다** — 지금 앱 코드에 이 함수의 호출처는 없고(등록은
    `utterances.flush_pending_analysis`의 SQL이 직접 한다) 남은 호출처는 재분석
    경로(하네스 E6·테스트)다. 그래도 위 이유는 유효하므로 유지한다: 재분석을
    다른 쓰기와 묶어 부르는 호출자가 생기면 같은 함정을 다시 만난다.
    """
    return await conn.fetchval(
        """
        insert into analysis_jobs (job_type, utterance_id)
        values ($1, $2)
        on conflict do nothing
        returning id
        """,
        JOB_TYPE_ANALYZE,
        utterance_id,
    )


_ENQUEUE_PLAN_SQL = """
insert into analysis_jobs (job_type, session_id)
values ($1, $2)
on conflict do nothing
returning id
"""


async def enqueue_plan_next_session(conn: asyncpg.Connection, session_id: UUID) -> UUID | None:
    """끝난 세션 하나를 근거로 **다음** 세션 계획을 만들 job을 건다 (설계서 §3.1).

    `None`은 실패가 아니라 **이미 걸려 있다**는 뜻이다 — partial unique
    `uq_analysis_jobs_pending_session`이 `(job_type, session_id)`를 pending/running
    동안 하나로 묶는다. 재시도되는 호출자가 중복을 만들지 않는다.

    ⚠️ 연결을 받는다(pool이 아니다). 세션 종료 기록과 **한 트랜잭션**이어야 하기 때문이다 —
    분리하면 그 사이 크래시에서 다음 계획이 영구히 만들어지지 않는다.
    """
    return await conn.fetchval(_ENQUEUE_PLAN_SQL, JOB_TYPE_PLAN, session_id)


async def claim_next(conn: asyncpg.Connection, *, now: datetime | None = None) -> ClaimedJob | None:
    """Claim the next runnable job, minting a new lease token for this claim.

    Two statements, in this order:

    1. **reaper** — a `running` job that already spent every attempt and whose
       lease expired is made terminal `failed`. Without this the job is a
       zombie: the recovery leg below refuses to re-run it (attempt cap), and
       nothing else ever moves it out of `running`, so `results` would report
       that session as "analyzing" forever.
    2. **claim** — either a due `pending` job or a `running` job whose lease
       expired *and* still has attempts left (crash recovery). `attempts` is
       incremented at claim time, so a recovered job spends an attempt exactly
       like a normal run: a job that repeatedly kills its worker converges on
       `failed` (via the reaper) instead of being retried forever.

    The reaper runs on every call rather than in a separate loop — it is one
    indexed UPDATE that matches nothing in the normal case, and keeping it here
    means "no job stays claimable-but-uncompletable" holds without a second
    moving part to deploy and supervise.

    `now` (aware) overrides the database clock; it exists so lease/backoff
    behaviour is testable without sleeping.
    """
    at = _require_aware(now)
    await conn.execute(
        """
        update analysis_jobs
           set status = 'failed',
               locked_at = null,
               locked_by = null,
               last_error = $4
         where status = 'running'
           and locked_at < coalesce($1::timestamptz, clock_timestamp()) - $2::interval
           and attempts::int >= $3::int
        """,
        at,
        LEASE,
        MAX_ATTEMPTS,
        LEASE_EXPIRED_ERROR,
    )

    lease_token = uuid4().hex
    row = await conn.fetchrow(
        """
        update analysis_jobs
           set status = 'running',
               locked_at = coalesce($1::timestamptz, clock_timestamp()),
               locked_by = $2,
               attempts = attempts + 1
         where id = (
                 select id
                   from analysis_jobs
                  where (status = 'pending'
                         and available_at <= coalesce($1::timestamptz, clock_timestamp()))
                     or (status = 'running'
                         and locked_at < coalesce($1::timestamptz, clock_timestamp()) - $3::interval
                         and attempts::int < $4::int)
                  order by available_at
                  limit 1
                  for update skip locked
               )
        returning id, job_type, utterance_id, session_id, attempts
        """,
        at,
        lease_token,
        LEASE,
        MAX_ATTEMPTS,
    )
    if row is None:
        return None
    return ClaimedJob(
        id=row["id"],
        job_type=row["job_type"],
        utterance_id=row["utterance_id"],
        session_id=row["session_id"],
        lease_token=lease_token,
        attempts=row["attempts"],
    )


async def complete(conn: asyncpg.Connection, job_id: UUID, lease_token: str) -> bool:
    """Mark a claimed job `done`. `False` means the lease was not ours anymore
    (expired and reclaimed, or already finished) — the caller must not treat
    its work as recorded."""
    updated = await conn.fetchval(
        """
        update analysis_jobs
           set status = 'done'
         where id = $1 and status = 'running' and locked_by = $2
        returning id
        """,
        job_id,
        lease_token,
    )
    return updated is not None


async def fail_or_retry(
    conn: asyncpg.Connection,
    job_id: UUID,
    lease_token: str,
    error: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Record a failed run: requeue with linear backoff, or give up at the cap.

    At `attempts >= MAX_ATTEMPTS` the job becomes terminal `failed` and keeps
    `last_error` for the results view (partial_failure). Below the cap it goes
    back to `pending` at `clock_timestamp() + attempts * BACKOFF` and the lease
    is cleared. Same lease gate as `complete`: `False` means the outcome was not
    recorded.

    The backoff is measured from the *statement* clock, not `now()`
    (=transaction_timestamp): the latter does not advance between statements, so
    a worker that spent four minutes on Claude inside one transaction would get
    a backoff that has already elapsed. `now` (aware) overrides the clock for
    tests and replay, mirroring `claim_next`.
    """
    updated = await conn.fetchval(
        """
        update analysis_jobs
           set status = case when attempts::int >= $4::int then 'failed' else 'pending' end,
               last_error = $3,
               available_at = case
                                when attempts::int >= $4::int then available_at
                                else coalesce($6::timestamptz, clock_timestamp())
                                     + attempts::int * $5::interval
                              end,
               locked_at = null,
               locked_by = null
         where id = $1 and status = 'running' and locked_by = $2
        returning id
        """,
        job_id,
        lease_token,
        error,
        MAX_ATTEMPTS,
        BACKOFF,
        _require_aware(now),
    )
    return updated is not None


async def report_failure(pool: asyncpg.Pool, job: ClaimedJob, error: str) -> None:
    """실패를 큐에 보고한다 — 짧은 자기 트랜잭션(이 모듈의 호출 계약).

    `analysis.py`의 private 함수였는데 계획 생성 job 도 같은 보고가 필요해져 여기로 옮겼다.
    내용은 job 수명주기 로직뿐이라 이 모듈이 원래 자리다. 복제하면 두 경로의 보고 방식이
    조용히 갈라진다.
    """
    async with pool.acquire() as conn, conn.transaction():
        recorded = await fail_or_retry(conn, job.id, job.lease_token, error)
    if not recorded:
        logger.warning("job %s: failure report discarded (lease no longer ours)", job.id)
