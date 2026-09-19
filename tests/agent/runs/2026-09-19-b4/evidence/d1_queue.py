#!/usr/bin/env python3
"""B4 회차 드라이버 1 — TS-31 의 큐 층(라우팅·claim 술어·회복·lease)을 dev DB 에서 잰다.

⛔ **워커 루프를 띄우지 않는다**(함정 H-CD). `claim_next`·`dispatch`·`complete` 를 직접 부른다.
⛔ **남의 job 을 건드리지 않는다.** claim 을 부르는 자리는 전부 **롤백되는 트랜잭션** 안이고,
   커밋하는 것은 내가 만든 사용자(`display_name` 이 b4 표지)의 행뿐이며 끝에 지운다.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import asyncpg

BACKEND = Path("/Users/redstar/MyProject/OhMyEnglish/app/backend")
sys.path.insert(0, str(BACKEND))

from app.services import jobs  # noqa: E402
from app.workers.analysis_worker import _HANDLERS, dispatch  # noqa: E402

MARK = "b4-queue-driver"
OUT: dict[str, object] = {}


class RollbackNow(Exception):
    """관측만 하고 트랜잭션을 되돌리기 위한 신호."""


def dsn() -> str:
    for line in (BACKEND / ".env").read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL not found")


async def seed(pool: asyncpg.Pool) -> tuple[UUID, UUID, UUID]:
    async with pool.acquire() as conn:
        uid = await conn.fetchval(
            "insert into users (display_name, timezone, current_level) "
            "values ($1, 'Asia/Seoul', 'B1') returning id",
            MARK,
        )
        sid = await conn.fetchval(
            "insert into learning_sessions (user_id, mode, status, ended_at) "
            "values ($1, 'speaking', 'completed', now()) returning id",
            uid,
        )
        utt = await conn.fetchval(
            "insert into utterances (session_id, speaker, transcript, sequence_no) "
            "values ($1, 'user', 'I usually go to gym after work.', 1) returning id",
            sid,
        )
    return uid, sid, utt


async def m_a_handler_table(pool: asyncpg.Pool) -> None:
    """AC#5 전반 — DB CHECK 의 값역과 `_HANDLERS` 의 키를 대조한다."""
    async with pool.acquire() as conn:
        src = await conn.fetchval(
            "select pg_get_constraintdef(oid) from pg_constraint "
            "where conname = 'analysis_jobs_job_type_check'"
        )
    domain = sorted({part.split("'")[1] for part in src.split("::text") if "'" in part})
    OUT["A_db_domain"] = domain
    OUT["A_handlers"] = sorted(_HANDLERS)
    OUT["A_match"] = domain == sorted(_HANDLERS)
    OUT["A_constraint_src"] = src


async def m_b_routing(pool: asyncpg.Pool, utt: UUID) -> UUID:
    """AC#1 — 표에 없는 종류가 큐에 사유를 남기는지. before 값을 함께 읽어 관측력을 보인다."""
    async with pool.acquire() as conn:
        job_id = await conn.fetchval(
            "insert into analysis_jobs (job_type, utterance_id, available_at) "
            "values ('analyze_utterance', $1, '1970-01-02T00:00:00Z') returning id",
            utt,
        )
        before = await conn.fetchrow(
            "select status, attempts, last_error from analysis_jobs where id = $1", job_id
        )
    OUT["B_before"] = dict(before)

    # 내 job 의 available_at 이 전역 최소이므로 `order by available_at limit 1` 이 내 것을 집는다.
    async with pool.acquire() as conn, conn.transaction():
        claimed = await jobs.claim_next(conn)
    assert claimed is not None and claimed.id == job_id, f"claimed someone else: {claimed}"
    OUT["B_claimed_is_mine"] = True

    bogus = jobs.ClaimedJob(
        id=claimed.id,
        job_type="b4_bogus_job_type",
        utterance_id=claimed.utterance_id,
        session_id=None,
        lease_token=claimed.lease_token,
        attempts=claimed.attempts,
    )
    await dispatch(pool, None, bogus)  # handler 가 없으므로 claude 는 쓰이지 않는다

    async with pool.acquire() as conn:
        after = await conn.fetchrow(
            "select status, attempts, last_error, locked_by, available_at "
            "from analysis_jobs where id = $1",
            job_id,
        )
    OUT["B_after"] = {k: (str(v) if k == "available_at" else v) for k, v in dict(after).items()}
    OUT["B_reason_names_the_type"] = (
        after["last_error"] == "no handler for job type: b4_bogus_job_type"
    )
    OUT["B_job_id"] = str(job_id)
    return job_id


async def m_c_claim_predicate(pool: asyncpg.Pool, job_id: UUID) -> None:
    """AC#5 후반 — claim 쿼리가 `failed` 를 집지 않는지. 양성 대조(pending)가 관측력이다."""
    async with pool.acquire() as conn:
        await conn.execute(
            "update analysis_jobs set status='failed', attempts=0, locked_at=null, "
            "locked_by=null, available_at='1970-01-01T00:00:00Z' where id = $1",
            job_id,
        )
        try:
            async with conn.transaction():
                got = await jobs.claim_next(conn)
                OUT["C_failed_claimed_mine"] = got is not None and got.id == job_id
                OUT["C_failed_claim_returned"] = (
                    None if got is None else {"id": str(got.id), "type": got.job_type}
                )
                raise RollbackNow  # 남의 job 을 집었을 수 있으므로 반드시 되돌린다
        except RollbackNow:
            pass

        try:
            async with conn.transaction():
                await conn.execute("update analysis_jobs set status='pending' where id=$1", job_id)
                got = await jobs.claim_next(conn)
                OUT["C_pending_claimed_mine"] = got is not None and got.id == job_id
                raise RollbackNow
        except RollbackNow:
            pass

        OUT["C_status_after_rollback"] = await conn.fetchval(
            "select status from analysis_jobs where id=$1", job_id
        )


async def m_d_recovery(pool: asyncpg.Pool, job_id: UUID) -> None:
    """AC#4 — running 으로 시한을 넘긴 job 이 되돌려지는지. 음성 대조: 시한 안에서는 안 집힌다."""
    now = datetime.now(UTC)
    for label, age in (("expired", timedelta(minutes=6)), ("alive", timedelta(minutes=1))):
        async with pool.acquire() as conn:
            await conn.execute(
                "update analysis_jobs set status='running', attempts=1, locked_by='b4-stale', "
                "locked_at=$2, last_error=null, available_at='1970-01-01T00:00:00Z' where id=$1",
                job_id,
                now - age,
            )
            try:
                async with conn.transaction():
                    got = await jobs.claim_next(conn, now=now)
                    mine = got is not None and got.id == job_id
                    OUT[f"D_{label}_reclaimed_mine"] = mine
                    if mine:
                        row = await conn.fetchrow(
                            "select attempts, locked_by from analysis_jobs where id=$1", job_id
                        )
                        OUT[f"D_{label}_attempts_after"] = row["attempts"]
                        OUT[f"D_{label}_lease_rotated"] = row["locked_by"] != "b4-stale"
                    raise RollbackNow
            except RollbackNow:
                pass

    # 시도 소진 + 임대 만료 → reaper 가 terminal failed 로 닫는다(회복의 상한).
    async with pool.acquire() as conn:
        await conn.execute(
            "update analysis_jobs set status='running', attempts=5, locked_by='b4-stale', "
            "locked_at=$2 where id=$1",
            job_id,
            now - timedelta(minutes=6),
        )
        try:
            async with conn.transaction():
                await jobs.claim_next(conn, now=now)
                row = await conn.fetchrow(
                    "select status, last_error from analysis_jobs where id=$1", job_id
                )
                OUT["D_reaped_status"] = row["status"]
                OUT["D_reaped_error"] = row["last_error"]
                raise RollbackNow
        except RollbackNow:
            pass


async def m_e_lease(pool: asyncpg.Pool, job_id: UUID) -> None:
    """AC#2 — 임대를 잃은 뒤 `complete` 가 `LeaseLost` 를 올리는지. 양성 대조: 내 토큰이면 done."""
    async with pool.acquire() as conn:
        await conn.execute(
            "update analysis_jobs set status='running', attempts=1, locked_by='token-owner', "
            "locked_at=now() where id=$1",
            job_id,
        )
        try:
            async with conn.transaction():
                try:
                    await jobs.complete(conn, job_id, "token-stolen")
                    OUT["E_lease_lost_raised"] = False
                except jobs.LeaseLost:
                    OUT["E_lease_lost_raised"] = True
                raise RollbackNow
        except RollbackNow:
            pass

        try:
            async with conn.transaction():
                await jobs.complete(conn, job_id, "token-owner")
                OUT["E_owner_token_completes"] = await conn.fetchval(
                    "select status from analysis_jobs where id=$1", job_id
                )
                raise RollbackNow
        except RollbackNow:
            pass

        OUT["E_status_after_rollback"] = await conn.fetchval(
            "select status from analysis_jobs where id=$1", job_id
        )
        try:
            async with conn.transaction():
                OUT["E_fail_or_retry_lost_lease"] = not await jobs.fail_or_retry(
                    conn, job_id, "token-stolen", "b4 probe"
                )
                raise RollbackNow
        except RollbackNow:
            pass


async def cleanup(pool: asyncpg.Pool, uid: UUID) -> None:
    async with pool.acquire() as conn:
        await conn.execute("delete from users where id = $1", uid)
        OUT["cleanup_users_left"] = await conn.fetchval(
            "select count(*) from users where display_name = $1", MARK
        )
        OUT["cleanup_jobs_left"] = await conn.fetchval(
            "select count(*) from analysis_jobs where last_error like '%b4_bogus_job_type%'"
        )


async def main() -> None:
    pool = await asyncpg.create_pool(dsn(), min_size=1, max_size=3)
    uid = None
    try:
        uid, _sid, utt = await seed(pool)
        OUT["user_id"] = str(uid)
        await m_a_handler_table(pool)
        job_id = await m_b_routing(pool, utt)
        await m_c_claim_predicate(pool, job_id)
        await m_d_recovery(pool, job_id)
        await m_e_lease(pool, job_id)
    finally:
        if uid is not None:
            await cleanup(pool, uid)
        await pool.close()
    print(json.dumps(OUT, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
