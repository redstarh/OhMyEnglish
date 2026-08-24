"""`analysis_jobs` — PostgreSQL-backed job queue with lease tokens (설계서 §5.4).

No broker: the queue is one table claimed with `for update skip locked`, which
is what keeps "at most one worker per job" true without a second piece of
infrastructure. Three properties carry the correctness of the whole pipeline:

* **멱등 등록** — the partial unique index `uq_analysis_jobs_pending_utterance`
  covers only `status in ('pending','running')`, so re-registering an utterance
  that is still queued is a no-op (`None`), while re-registering one whose job
  already finished is allowed (re-analysis).
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
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import asyncpg

# --- 설계 발명값 (design-invented values, see module docstring) ---
LEASE = timedelta(minutes=5)
MAX_ATTEMPTS = 5
BACKOFF = timedelta(minutes=1)

JOB_TYPE_ANALYZE = "analyze_utterance"

# reaper가 좀비 job에 남기는 사유 (아래 `_REAP_ZOMBIES_SQL` 참조).
LEASE_EXPIRED_ERROR = "max attempts exceeded (lease expired without report)"


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    """One successful claim. `lease_token` is only valid until `LEASE` elapses.

    `utterance_id` is optional because `analysis_jobs` also carries
    `summarize_session` jobs (target columns are mutually exclusive per the
    `analysis_jobs_target_matches_job_type` CHECK). Jobs produced by
    `enqueue_analyze` always have it set.
    """

    id: UUID
    utterance_id: UUID | None
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
    is deliberate: the caller in `utterances.save_final_transcript` runs inside
    the same transaction as the transcript insert, and a raised violation would
    abort that transaction — losing the transcript over a duplicate job.
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
           and locked_at < coalesce($1::timestamptz, now()) - $2::interval
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
               locked_at = coalesce($1::timestamptz, now()),
               locked_by = $2,
               attempts = attempts + 1
         where id = (
                 select id
                   from analysis_jobs
                  where (status = 'pending' and available_at <= coalesce($1::timestamptz, now()))
                     or (status = 'running'
                         and locked_at < coalesce($1::timestamptz, now()) - $3::interval
                         and attempts::int < $4::int)
                  order by available_at
                  limit 1
                  for update skip locked
               )
        returning id, utterance_id, attempts
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
        utterance_id=row["utterance_id"],
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
    conn: asyncpg.Connection, job_id: UUID, lease_token: str, error: str
) -> bool:
    """Record a failed run: requeue with linear backoff, or give up at the cap.

    At `attempts >= MAX_ATTEMPTS` the job becomes terminal `failed` and keeps
    `last_error` for the results view (partial_failure). Below the cap it goes
    back to `pending` at `now() + attempts * BACKOFF` and the lease is cleared.
    Same lease gate as `complete`: `False` means the outcome was not recorded.
    """
    updated = await conn.fetchval(
        """
        update analysis_jobs
           set status = case when attempts::int >= $4::int then 'failed' else 'pending' end,
               last_error = $3,
               available_at = case
                                when attempts::int >= $4::int then available_at
                                else now() + attempts::int * $5::interval
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
    )
    return updated is not None
