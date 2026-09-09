#!/usr/bin/env python
"""P5·P6 의 워커 구간을 **가장 좁게** 켠다 — job 1건만 처리하고 끝낸다.

⛔ **`run_worker` 를 부르지 않는다.** 그 루프는 큐가 비면 `sweep_lost_runs` →
`flush_ended_sessions` 를 부르고, 그것이 보존 세션에 job 을 **새로 만들어 처리한다**
(`H-AT` 경로 ②). 2026-09-09 에 그 경로로 보존 세션 두 개가 파괴됐고, 파괴는
`learning_sessions.status` 에 드러나지 않아 **결과 API 를 조회해야** 보인다.
이 스크립트는 `claim_one` 을 1회 부르고 job 이 없으면 즉시 끝낸다 — 그 함수를
import 하지 않으므로 경로 ②를 **구조적으로** 지나가지 않는다.

`H-AT` 경로 ①(claim 이 기존 `pending` job 을 집는다)은 `guard` 로 막는다. 보존 세션의
`available_at` 을 미래로 비켜 두고 원래 값을 JSON 으로 뜬다(`claim_next` 가
`available_at <= now()` 를 요구한다). `restore` 가 그것을 되돌린다.

방어를 규율이 아니라 코드에 둔다: `claim` 팔은 **보존 세션 job 이 전부 비켜져 있는지
먼저 검사하고, 하나라도 claim 가능하면 실행을 거부한다.** guard 를 잊는 것이 이 절차의
유일한 치명적 실수라서 그렇게 했다.

    .venv/bin/python ../../tests/harness/p5_worker_leg.py guard   --out /tmp/p5-guard.json
    .venv/bin/python ../../tests/harness/p5_worker_leg.py claim   --expect-session <uuid>
    .venv/bin/python ../../tests/harness/p5_worker_leg.py restore --in /tmp/p5-guard.json
    .venv/bin/python ../../tests/harness/p5_worker_leg.py verify

cwd 는 `app/backend` 다(`H-A` 와 같은 이유 — 설정과 `.env` 가 거기 있다).
⚠️ `verify` 는 백엔드가 `:8002` 에 떠 있어야 한다. 상태는 결과 API 로만 읽는다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from pathlib import Path
from typing import Any
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app" / "backend"))

import asyncpg  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.services.analysis import process_analysis  # noqa: E402
from app.services.jobs import JOB_TYPE_PLAN, claim_next  # noqa: E402
from app.services.plan import process_plan  # noqa: E402
from app.workers.claude_client import BedrockClaudeClient  # noqa: E402

# `browser_leg.md` §9 의 보존 세션. 지우지도, 그 job 을 처리하지도 않는다.
PRESERVED = (
    "210233be",
    "6225ddaf",
    "b2f0d169",
    "76d9ef31",
    "d127dece",
    "e0c5e580",
)

_PRESERVED_JOBS_SQL = """
select j.id, j.session_id, j.job_type, j.status, j.attempts, j.available_at,
       (j.available_at <= now()) as claimable_now
  from analysis_jobs j
 where left(j.session_id::text, 8) = any($1::text[])
 order by j.created_at
"""

API_BASE = "http://127.0.0.1:8002"


async def _pool() -> asyncpg.Pool:
    pool = await asyncpg.create_pool(get_settings().database_url, min_size=1, max_size=2)
    if pool is None:  # pragma: no cover - asyncpg 는 실패 시 예외를 올린다
        raise SystemExit("커넥션 풀을 만들지 못했다")
    return pool


async def _preserved_jobs(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(_PRESERVED_JOBS_SQL, list(PRESERVED))


async def cmd_guard(args: argparse.Namespace) -> int:
    """보존 세션 job 의 `available_at` 을 스냅샷하고 미래로 비켜 둔다."""
    pool = await _pool()
    try:
        rows = await _preserved_jobs(pool)
        snapshot = [
            {
                "job_id": str(r["id"]),
                "session": str(r["session_id"])[:8] if r["session_id"] else None,
                "job_type": r["job_type"],
                "status": r["status"],
                "attempts": r["attempts"],
                "available_at": r["available_at"].isoformat(),
            }
            for r in rows
        ]
        out = Path(args.out)
        out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"스냅샷 {len(snapshot)}건 → {out}")
        for item in snapshot:
            print(f"  {item['session']} {item['job_type']} {item['status']} {item['available_at']}")

        async with pool.acquire() as conn:
            moved = await conn.execute(
                "update analysis_jobs set available_at = now() + interval '30 days' "
                "where left(session_id::text, 8) = any($1::text[])",
                list(PRESERVED),
            )
        print(f"비켜 둠: {moved}")

        after = await _preserved_jobs(pool)
        still = [r for r in after if r["claimable_now"]]
        if still:
            print(f"⛔ 아직 claim 가능한 보존 job {len(still)}건 — 진행하지 마라", file=sys.stderr)
            return 1
        print("확인: 보존 job 전건이 claim 불가 상태다")
        return 0
    finally:
        await pool.close()


async def cmd_restore(args: argparse.Namespace) -> int:
    """스냅샷의 `available_at` 을 되돌린다."""
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    pool = await _pool()
    try:
        async with pool.acquire() as conn:
            for item in snapshot:
                await conn.execute(
                    "update analysis_jobs set available_at = $2::timestamptz where id = $1::uuid",
                    item["job_id"],
                    item["available_at"],
                )
        print(f"복원 {len(snapshot)}건")
        for r in await _preserved_jobs(pool):
            sess = str(r["session_id"])[:8] if r["session_id"] else None
            print(f"  {sess} {r['job_type']} {r['status']} claimable={r['claimable_now']}")
        return 0
    finally:
        await pool.close()


async def cmd_claim(args: argparse.Namespace) -> int:
    """job 1건만 claim 해 처리한다. 보존 job 이 비켜져 있지 않으면 **거부한다**."""
    pool = await _pool()
    try:
        unguarded = [r for r in await _preserved_jobs(pool) if r["claimable_now"]]
        if unguarded:
            print(
                f"⛔ 거부한다 — 보존 세션 job {len(unguarded)}건이 claim 가능하다. "
                "먼저 `guard` 를 돌려라 (H-AT 경로 ①)",
                file=sys.stderr,
            )
            return 2

        async with pool.acquire() as conn:
            job = await claim_next(conn)
        if job is None:
            print("claim 할 job 이 없다 — 아무것도 하지 않았다")
            return 0

        sess = str(job.session_id)[:8] if job.session_id else None
        print(f"claim: job={job.id} type={job.job_type} session={sess}")
        if sess in PRESERVED:
            print(
                f"⛔ 보존 세션의 job 을 집었다({sess}) — 처리하지 않는다. "
                "guard 가 새지 않았는지 확인하라",
                file=sys.stderr,
            )
            return 3
        if args.expect_session and sess != args.expect_session[:8]:
            print(
                f"⛔ 기대한 세션({args.expect_session[:8]})이 아니다 — 처리하지 않는다",
                file=sys.stderr,
            )
            return 4

        claude = BedrockClaudeClient(get_settings())
        if job.job_type == JOB_TYPE_PLAN:
            await process_plan(pool, claude, job)
        else:
            await process_analysis(pool, claude, job)

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "select status, attempts, last_error from analysis_jobs where id = $1", job.id
            )
        print(f"처리 후: status={row['status']} attempts={row['attempts']}")
        if row["last_error"]:
            print(f"last_error: {row['last_error']}")
        return 0
    finally:
        await pool.close()


def _results(session_id: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{API_BASE}/api/sessions/{session_id}/results") as resp:  # noqa: S310
        return json.loads(resp.read())


async def cmd_verify(_: argparse.Namespace) -> int:
    """보존 세션 6개의 결과 API 상태를 찍는다 — 켜기 전·끈 뒤에 각각 돌려 대조한다."""
    pool = await _pool()
    try:
        async with pool.acquire() as conn:
            ids: list[UUID] = [
                r["id"]
                for r in await conn.fetch(
                    "select id from learning_sessions "
                    "where left(id::text, 8) = any($1::text[]) order by left(id::text, 8)",
                    list(PRESERVED),
                )
            ]
        if len(ids) != len(PRESERVED):
            print(
                f"⛔ 보존 세션이 {len(ids)}건뿐이다 — {len(PRESERVED)}건이어야 한다",
                file=sys.stderr,
            )
        for session_id in ids:
            payload = _results(str(session_id))
            corrections = payload.get("corrections")
            count = "키없음" if corrections is None else str(len(corrections))
            print(f"{str(session_id)[:8]} {payload.get('status')} corrections={count}")
        return 0
    finally:
        await pool.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_guard = sub.add_parser("guard", help="보존 job 의 available_at 을 비켜 두고 스냅샷한다")
    p_guard.add_argument("--out", default="/tmp/p5-guard.json")
    p_guard.set_defaults(fn=cmd_guard)

    p_restore = sub.add_parser("restore", help="스냅샷을 되돌린다")
    p_restore.add_argument("--in", dest="snapshot", default="/tmp/p5-guard.json")
    p_restore.set_defaults(fn=cmd_restore)

    p_claim = sub.add_parser("claim", help="job 1건만 claim 해 처리한다")
    p_claim.add_argument("--expect-session", default=None, help="이 세션의 job 만 처리한다")
    p_claim.set_defaults(fn=cmd_claim)

    p_verify = sub.add_parser("verify", help="보존 세션 6개의 결과 API 상태를 찍는다")
    p_verify.set_defaults(fn=cmd_verify)

    args = parser.parse_args()
    return asyncio.run(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
