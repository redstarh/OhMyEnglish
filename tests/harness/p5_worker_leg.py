#!/usr/bin/env python
"""P5·P6 의 워커 구간을 **가장 좁게** 켠다 — job 1건만 처리하고 끝낸다.

⛔ **`run_worker` 를 부르지 않는다.** 그 루프는 큐가 비면 `sweep_lost_runs` →
`flush_ended_sessions` 를 부르고, 그것이 보존 세션에 job 을 **새로 만들어 처리한다**
(`H-AT` 경로 ②). 2026-09-09 에 그 경로로 보존 세션 두 개가 파괴됐고, 파괴는
`learning_sessions.status` 에 드러나지 않아 **결과 API 를 조회해야** 보인다.
이 스크립트는 `claim_one` 을 1회 부르고 job 이 없으면 즉시 끝낸다 — 그 함수를
import 하지 않으므로 경로 ②를 **구조적으로** 지나가지 않는다.

`H-AT` 경로 ①(claim 이 기존 job 을 집는다)은 `guard` 로 막는다. ⛔ **막는 방법이
2026-09-11 에 바뀌었다** (`TASK-101`) — 아래 두 결함이 실측돼서다.

**결함 1 — 남의 job 을 막지 못했다.** 초판은 **보존 세션 6개의 job 만** 비켜 뒀는데
`claim_next` 는 **claim 가능한 모든 job 중 `available_at` 이 가장 이른 것**을 집는다.
동료 세션이 실제로 걸렸다: `24597f0f` 의 `analyze_utterance` 가 집혀
`status=running`·`attempts=1`·`lock` 이 **커밋됐다.** `--expect-session` 은 **처리만** 막고
claim 자체를 막지 못한다. 그리고 남의 job 을 손으로 밀고 나서 `guard` 를 돌리면 `guard` 가
**밀린 값을 「원값」으로 스냅샷해 `restore` 가 거짓 복원**을 한다(순서 함정).

⛔ **결함 2 — `running`·임대만료 갈래에 눈이 멀었다.** `app/services/jobs.py` 의 claim 술어는
**두 갈래**다: `(pending and available_at <= now())` **또는**
`(running and locked_at < now() - LEASE and attempts < MAX_ATTEMPTS)`. 뒷 갈래의 claim
가능성은 **`available_at` 과 무관**하다. 그런데 초판의 `claimable_now` 는
`available_at <= now()` 하나였다 — **`available_at` 을 30일 뒤로 밀어도 그 job 은 여전히
집힌다.** 즉 초판의 「전건 claim 불가 확인」이 그 갈래를 **구조적으로** 통과시켰다.

**그래서 방향을 뒤집었다 — 남의 행을 밀지 않고 «내 job 하나»를 앞으로 당긴다.**
`claim_next` 가 `order by available_at limit 1` 이므로 내 job 이 **전역 최소**이면 내 것이
집힌다. 그 결과 셋이 따라온다: ⑴ **남의 job 에 UPDATE 가 0건**이다 ⑵ 밀 것이 없으므로
**순서 함정이 사라진다** ⑶ claim 가능 집합을 **제품 술어 두 갈래로** 계산하므로 결함 2 가
닫힌다. `guard` 와 `claim` 이 **같은 단정**을 갖는다 — 전역 최소가 기대 세션 것이 아니면
둘 다 거부한다.

⚠️ **스냅샷 파일의 모양은 바꾸지 않았다** — 과거 회차의 `p5-guard.json`(보존 job 15건 판)을
`restore` 가 그대로 읽는다.

⛔ **소유 세션은 `coalesce(j.session_id, u.session_id)` 로 해소한다 — `j.session_id` 만 보면
`analyze_utterance` 를 통째로 놓친다.** 2026-09-10 에 초판이 그 결함을 갖고 있었고, 위임된 회차가
`claim` 을 돌리기 «전에» SELECT 로 찾아 멈춰서 `C3a`(`210233be`) 손상을 면했다. 근거와 판별
출력은 `runs/2026-09-10-task82-p5-p6.md` §2 가 소유한다.

⛔ **스냅샷을 `/tmp` 에 두지 않는다.** 지워지면 보존 job 이 **영구히 30일 뒤로 밀린 채** 남고
되돌릴 근거가 사라진다. 회차 디렉터리에 두고 커밋한다.

방어를 규율이 아니라 코드에 둔다: `claim` 팔은 **보존 세션 job 이 전부 비켜져 있는지
먼저 검사하고, 하나라도 claim 가능하면 실행을 거부한다.** guard 를 잊는 것이 이 절차의
유일한 치명적 실수라서 그렇게 했다.

**결함 3 — 종류를 지목할 수 없어 «항상 분석 job» 이 당겨졌다** (2026-09-11 · `TASK-105` 회차가
실측했다). `guard` 는 내 job 중 **가장 이른 것**을 당기는데, 비보존 세션 넷 전부
`analyze_utterance` 가 `plan_next_session` 보다 이르다. 그러면 「계획 job 만 처리한다」를
표현할 수 없고, 분석을 지나가면 `error_patterns`·`review_tasks` 가 움직여 **필요 없는 `H-AY` 가
재현된다**(그 회차가 실제로 그 자리를 밟고 `restore` 로 되돌렸다). → `guard --job-type` 을 더했다.
⚠️ **그 옵션은 «좁히기만» 한다** — 남의 job 을 후보에 넣지 않으므로 위 단정 셋이 그대로 산다.

    P5=../../tests/harness/p5_worker_leg.py
    .venv/bin/python $P5 guard   --expect-session <uuid> --out <회차>/p5-guard.json \
                                 [--job-type analyze_utterance|plan_next_session]
    .venv/bin/python $P5 claim   --expect-session <uuid>
    .venv/bin/python $P5 restore --in <회차>/p5-guard.json
    .venv/bin/python $P5 verify

⛔ **`--expect-session` 은 `guard`·`claim` 둘 다에서 필수다.** 없이 돌 수 있게 두면 「부분만
막고 통과하는」 초판의 결함이 되살아난다.
⚠️ **처리할 종류가 정해져 있으면 `--job-type` 을 «항상» 준다** — 빠뜨리면 결함 3 을 다시 밟는다.

cwd 는 `app/backend` 다(`H-A` 와 같은 이유 — 설정과 `.env` 가 거기 있다).
⚠️ `verify` 는 백엔드가 `:8002` 에 떠 있어야 한다. 상태는 결과 API 로만 읽는다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app" / "backend"))

import asyncpg  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.services.analysis import process_analysis  # noqa: E402
from app.services.jobs import (  # noqa: E402
    JOB_TYPE_ANALYZE,
    JOB_TYPE_GENERATE_SCENARIO,
    JOB_TYPE_PLAN,
    JOB_TYPE_SUMMARIZE,
    LEASE,
    MAX_ATTEMPTS,
    claim_next,
)
from app.services.plan import process_plan  # noqa: E402
from app.services.scenario_generator import process_scenario  # noqa: E402
from app.services.session_summary import process_summary  # noqa: E402
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

# ⛔ **`analyze_utterance` 는 `session_id` 가 NULL 이고 `utterance_id` 로만 세션에 매인다**
# (2026-09-10 실측: `analyze_utterance` 43건 **전부** 그렇다. `plan_next_session` 6건은 반대다).
# 그래서 `j.session_id` 만 보는 술어는 **보존 세션의 `analyze_utterance` 를 통째로 놓친다** —
# 초판이 그랬고, 그 상태로 `claim` 을 돌리면 `claim_next` 가 `order by available_at limit 1` 로
# **C3a(`210233be`) 의 가장 오래된 job 을 먼저 집어** `attempts` 를 태우고 `running` 으로 만든다.
# ⚠️ **그 손상은 `verify` 로 안 보인다** — `results.py` 가 `pending`·`running` 을 함께
# non_terminal 로 세므로 결과 API 는 그대로 `analyzing` 을 낸다
# (`H-AT` 의 「피해가 눈에 안 보인다」와 같은 형태다).
# → **소유 세션은 `coalesce(j.session_id, u.session_id)` 로 해소한다.**
# ⚠️ **`claimable_now` 를 여기서도 제품 술어로 계산한다.** 초판은 `available_at <= now()` 하나였고,
# 그래서 `restore` 의 출력이 **`done` job 을 `claimable=True` 로 찍었다**(2026-09-11 관측).
# 판정에 쓰이지 않는 출력이라도 틀린 값을 찍으면 읽는 사람이 그것을 근거로 삼는다.
_PRESERVED_JOBS_SQL = """
select j.id, coalesce(j.session_id, u.session_id) as session_id, j.job_type, j.status,
       j.attempts, j.available_at,
       (   (j.status = 'pending' and j.available_at <= clock_timestamp())
        or (j.status = 'running'
            and j.locked_at < clock_timestamp() - $2::interval
            and j.attempts::int < $3::int)) as claimable_now
  from analysis_jobs j
  left join utterances u on u.id = j.utterance_id
 where left(coalesce(j.session_id, u.session_id)::text, 8) = any($1::text[])
 order by j.created_at
"""

# ⛔ **claim 가능성의 정의를 제품에서 베껴 온다 — 두 갈래 전부다** (`TASK-101` 결함 2).
# 정본은 `app/services/jobs.py` 의 claim UPDATE 이고 그 술어가 이것이다:
#   (status='pending' and available_at <= clock_timestamp())
#   or (status='running' and locked_at < clock_timestamp() - LEASE and attempts < MAX_ATTEMPTS)
# ⚠️ **`now()` 가 아니라 `clock_timestamp()` 를 쓴다** — 제품이 그것을 쓴다. `now()` 는 트랜잭션
# 시작 시각이라 긴 트랜잭션에서 갈린다.
# ⚠️ `LEASE`·`MAX_ATTEMPTS` 를 숫자로 적지 않고 **제품 상수를 import 해 파라미터로 넘긴다** —
# 적으면 제품이 값을 바꿀 때 이 판정이 조용히 낡는다.
# `order by j.available_at` 도 제품과 같다 — **집히는 순서가 판정의 근거**이기 때문이다.
_CLAIMABLE_JOBS_SQL = """
select j.id, coalesce(j.session_id, u.session_id) as session_id, j.job_type, j.status,
       j.attempts, j.available_at, j.locked_at,
       (   (j.status = 'pending' and j.available_at <= clock_timestamp())
        or (j.status = 'running'
            and j.locked_at < clock_timestamp() - $1::interval
            and j.attempts::int < $2::int)) as claimable_now
  from analysis_jobs j
  left join utterances u on u.id = j.utterance_id
 where j.status in ('pending', 'running')
 order by j.available_at, j.id
"""

# 내 대상 job 을 전역 최소로 만드는 값. 과거 어떤 job 보다 이르다.
_PULL_TO = datetime(2000, 1, 1, tzinfo=UTC)

API_BASE = "http://127.0.0.1:8002"


async def _pool() -> asyncpg.Pool:
    pool = await asyncpg.create_pool(get_settings().database_url, min_size=1, max_size=2)
    if pool is None:  # pragma: no cover - asyncpg 는 실패 시 예외를 올린다
        raise SystemExit("커넥션 풀을 만들지 못했다")
    return pool


async def _preserved_jobs(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(_PRESERVED_JOBS_SQL, list(PRESERVED), LEASE, MAX_ATTEMPTS)


def _owner8(record: asyncpg.Record) -> str | None:
    return str(record["session_id"])[:8] if record["session_id"] else None


async def _claimable(pool: asyncpg.Pool) -> list[asyncpg.Record]:
    """제품 술어로 **지금 claim 가능한** job 만, 제품과 같은 순서로 돌려준다."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(_CLAIMABLE_JOBS_SQL, LEASE, MAX_ATTEMPTS)
    return [r for r in rows if r["claimable_now"]]


def _describe(record: asyncpg.Record) -> str:
    return (
        f"{_owner8(record)} {record['job_type']} {record['status']} "
        f"attempts={record['attempts']} available_at={record['available_at'].isoformat()}"
    )


def _reject_preserved_expectation(expect8: str) -> bool:
    """기대 세션이 **보존 세션이면 즉시 거부**한다 — `guard`·`claim` 둘 다 이것을 먼저 부른다.

    ⛔ **이 검사가 없으면 새 단정이 오히려 위험해진다.** `_front_runner_is` 는 「전역 최소가 기대
    세션 것인가」만 보므로, 보존 세션을 기대로 주면 **통과한 뒤** `claim_next` 가 실제로 그 job 을
    집는다 — `attempts`·`status`·`lock` 이 커밋된 다음에야 사후 `PRESERVED` 검사가 막는다.
    2026-09-11 에 판별력 시험을 설계하다가 그 경로를 발견해 앞단에 막았다.
    """
    if expect8 in PRESERVED:
        print(
            f"⛔ 거부한다 — {expect8} 는 보존 세션이다. 그 job 은 어떤 경우에도 처리하지 않는다 "
            "(browser_leg.md §9)",
            file=sys.stderr,
        )
        return True
    return False


def _front_runner_is(rows: list[asyncpg.Record], expect8: str) -> tuple[bool, str]:
    """**전역 최소가 기대 세션 것인지** 판정한다. `guard` 와 `claim` 이 이 함수를 공유한다.

    ⛔ **동률을 통과시키지 않는다.** `order by available_at` 이 같은 값 둘을 만나면 어느 쪽이
    집히는지 보장이 없다 — 그 상태에서 통과시키면 「대체로 내 것이 집힌다」가 된다.
    """
    if not rows:
        return False, "claim 가능한 job 이 0건이다"
    first = rows[0]
    if _owner8(first) != expect8:
        return False, f"전역 최소가 남의 job 이다 — {_describe(first)}"
    tied = [r for r in rows[1:] if r["available_at"] == first["available_at"]]
    if tied:
        return False, f"available_at 동률이 {len(tied)}건 있다 — {_describe(tied[0])}"
    return True, f"전역 최소가 기대 세션 것이다 — {_describe(first)}"


async def cmd_guard(args: argparse.Namespace) -> int:
    """**내 job 하나만** 전역 최소로 당기고 그 원값을 스냅샷한다 — 남의 행은 쓰지 않는다.

    ⛔ 초판은 반대였다(남의 job 을 미래로 밀었다). 뒤집은 근거는 모듈 docstring 이 갖는다.
    """
    expect8 = args.expect_session[:8]
    if _reject_preserved_expectation(expect8):
        return 1
    pool = await _pool()
    try:
        rows = await _claimable(pool)
        print(f"claim 가능 job {len(rows)}건 (제품 술어 두 갈래로 계산)")
        for r in rows:
            print(f"  {'*' if _owner8(r) == expect8 else ' '} {_describe(r)}")

        mine = [r for r in rows if _owner8(r) == expect8]
        # `--job-type` 은 **좁히기만** 한다 — 남의 job 을 후보에 넣지 않는다.
        wanted = getattr(args, "job_type", None)
        if wanted is not None:
            mine = [r for r in mine if r["job_type"] == wanted]
        if not mine:
            kind = "" if wanted is None else f" 종류 {wanted} 인"
            print(
                f"⛔ 거부한다 — 기대 세션({expect8})의{kind} claim 가능한 job 이 0건이다. "
                "당길 대상이 없으므로 guard 는 아무 의미가 없다 "
                "(job 이 running·임대유효이거나 available_at 이 미래일 수 있다)",
                file=sys.stderr,
            )
            return 1

        # 내 것이 여럿이면 **가장 이른 것 하나**만 당긴다 — claim 은 1회에 1건이다.
        target = mine[0]
        snapshot = [
            {
                "job_id": str(target["id"]),
                "session": _owner8(target),
                "job_type": target["job_type"],
                "status": target["status"],
                "attempts": target["attempts"],
                "available_at": target["available_at"].isoformat(),
            }
        ]
        out = Path(args.out)
        out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"스냅샷 1건 → {out}  ({_describe(target)})")

        async with pool.acquire() as conn:
            pulled = await conn.execute(
                "update analysis_jobs set available_at = $2 where id = $1::uuid",
                str(target["id"]),
                _PULL_TO,
            )
        print(f"당김: {pulled} → {_PULL_TO.isoformat()}")

        # ⛔ **당긴 «뒤에» 다시 계산해 단정한다.** 당기기 전 계산으로 통과시키면 그 사이에 남의
        #    job 이 claim 가능해진 것을 놓친다.
        ok, why = _front_runner_is(await _claimable(pool), expect8)
        print(("확인: " if ok else "⛔ ") + why, file=sys.stdout if ok else sys.stderr)
        if not ok:
            print(
                "⛔ 되돌려라 — `restore --in <스냅샷>` 을 먼저 돌린 뒤 원인을 본다",
                file=sys.stderr,
            )
            return 1
        return 0
    finally:
        await pool.close()


async def cmd_restore(args: argparse.Namespace) -> int:
    """스냅샷의 `available_at` 을 되돌린다."""
    snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    pool = await _pool()
    restored = 0
    try:
        async with pool.acquire() as conn:
            for item in snapshot:
                # ⛔ **`$2::timestamptz` 에 문자열을 넘기면 asyncpg 가 거부한다** — 캐스트를
                #    보고 파라미터 타입을 timestamptz 로 «먼저» 정하므로 `str` 이 들어갈
                #    자리가 없다. 2026-09-10 실측: `DataError: invalid input for query
                #    argument $2 … got 'str'`.
                #    ⚠️ 초판이 그랬고, 그래서 **`guard` 는 성공하는데 `restore` 만 죽었다** —
                #    스냅샷한 보존 job 전건이 +30일로 밀린 채 남는 가장 위험한 상태다
                #    (그 회차의 스냅샷은 15건이었다). aware datetime 으로 바꾼다.
                tag = await conn.execute(
                    "update analysis_jobs set available_at = $2 where id = $1::uuid",
                    item["job_id"],
                    datetime.fromisoformat(item["available_at"]),
                )
                touched = int(tag.rsplit(" ", 1)[-1])
                restored += touched
                if touched == 0:
                    # ⚠️ **행이 사라진 것을 조용히 넘기지 않는다.** teardown 이 job 을 지운 뒤
                    #    restore 를 돌리면 정상이지만, 그렇지 않은데 0행이면 **누가 지운 것**이고
                    #    그것은 알아야 한다. 초판은 스냅샷 건수를 그대로 「복원 N건」으로 찍어
                    #    0행 UPDATE 를 성공처럼 보고했다(2026-09-11 관측).
                    print(f"  ⚠️ 행이 없다: {item['job_id']} ({item.get('session')})")
        print(f"복원 {restored}건 / 스냅샷 {len(snapshot)}건")
        for r in await _preserved_jobs(pool):
            sess = str(r["session_id"])[:8] if r["session_id"] else None
            print(f"  {sess} {r['job_type']} {r['status']} claimable={r['claimable_now']}")
        return 0
    finally:
        await pool.close()


async def cmd_claim(args: argparse.Namespace) -> int:
    """job 1건만 claim 해 처리한다. **전역 최소가 기대 세션 것이 아니면 거부한다.**

    ⛔ 초판은 「보존 세션 job 이 claim 가능한가」만 봤다. 그 검사는 **남의(보존 아닌) 세션 job 을
    통째로 통과시키고** `running`·임대만료 갈래에도 눈이 멀었다 — 둘 다 실측됐다(docstring).
    지금은 `guard` 와 **같은 단정**(`_front_runner_is`)을 쓴다.
    """
    expect8 = args.expect_session[:8]
    if _reject_preserved_expectation(expect8):
        return 2
    pool = await _pool()
    try:
        rows = await _claimable(pool)
        ok, why = _front_runner_is(rows, expect8)
        if not ok:
            print(f"⛔ 거부한다 — {why}", file=sys.stderr)
            print(
                "먼저 `guard --expect-session <uuid>` 를 돌려라 (H-AT 경로 ① · TASK-101)",
                file=sys.stderr,
            )
            for r in rows[:5]:
                print(f"  {_describe(r)}", file=sys.stderr)
            return 2
        print(f"확인: {why}")

        async with pool.acquire() as conn:
            job = await claim_next(conn)
        if job is None:
            print("claim 할 job 이 없다 — 아무것도 하지 않았다")
            return 0

        # ⛔ **`ClaimedJob.session_id` 만 보면 `analyze_utterance` 에 대해 눈이 먼다** — 그 job 은
        #    `session_id` 가 NULL 이다. 여기서 해소하지 않으면 아래 `exit 3` 방어가 **보존 세션의
        #    `analyze_utterance` 를 영구히 통과시킨다.** ①과 같은 결함이 이 자리에도 있었다.
        owner = job.session_id
        if owner is None and job.utterance_id is not None:
            async with pool.acquire() as conn:
                owner = await conn.fetchval(
                    "select session_id from utterances where id = $1", job.utterance_id
                )
        sess = str(owner)[:8] if owner else None
        print(f"claim: job={job.id} type={job.job_type} session={sess}")
        if sess in PRESERVED:
            print(
                f"⛔ 보존 세션의 job 을 집었다({sess}) — 처리하지 않는다. "
                "guard 가 새지 않았는지 확인하라",
                file=sys.stderr,
            )
            return 3
        if sess != expect8:
            print(
                f"⛔ 기대한 세션({expect8})이 아니다 — 처리하지 않는다. "
                "⚠️ claim 자체는 이미 커밋됐다(attempts·status) — 되돌려라",
                file=sys.stderr,
            )
            return 4

        claude = BedrockClaudeClient(get_settings())
        # ⛔ **종류마다 «지목»한다 — 마지막 갈래를 `else` 로 두면 새 종류가 조용히 그리로 간다.**
        # `TASK-102.1`(2026-09-13)에서 실제로 그랬다: `generate_scenario` 를 더하기 전에는 그 job 이
        # `process_analysis` 로 갔고, 그 함수는 종류가 다르면 **실패로 보고**하므로 5회 재시도 뒤
        # 영원히 `failed` 가 된다. ⚠️ 조용히 «잘못 처리»되지는 않지만 회차가 헛돈다.
        if job.job_type == JOB_TYPE_PLAN:
            await process_plan(pool, claude, job)
        elif job.job_type == JOB_TYPE_GENERATE_SCENARIO:
            await process_scenario(pool, claude, job)
        elif job.job_type == JOB_TYPE_SUMMARIZE:
            await process_summary(pool, claude, job)
        elif job.job_type == JOB_TYPE_ANALYZE:
            await process_analysis(pool, claude, job)
        else:
            print(
                f"⛔ 이 실행체가 모르는 job 종류다: {job.job_type!r} — 처리하지 않는다. "
                "제품에 종류가 늘었으면 이 분기를 함께 더하라",
                file=sys.stderr,
            )
            return 5

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

    p_guard = sub.add_parser("guard", help="내 job 하나를 전역 최소로 당기고 원값을 스냅샷한다")
    p_guard.add_argument("--expect-session", required=True, help="이 세션의 job 을 당긴다")
    p_guard.add_argument("--out", required=True, help="⛔ /tmp 에 두지 마라 — 회차 디렉터리에 둔다")
    # `TASK-105` — 종류를 지목하지 못하면 「계획 job 만 처리한다」를 표현할 수 없다. 실측: 비보존
    # 세션 넷 전부 `analyze_utterance` 가 `plan_next_session` 보다 이르므로 종류 없이는 **항상
    # 분석 job 이 당겨진다.** 분석을 지나가면 `error_patterns`·`review_tasks` 가 움직여
    # baseline 이 drift 하고(`H-AY`) 그것은 이 회차가 필요로 하지 않는 변경이다.
    p_guard.add_argument(
        "--job-type",
        choices=(
            JOB_TYPE_ANALYZE,
            JOB_TYPE_PLAN,
            JOB_TYPE_GENERATE_SCENARIO,
            JOB_TYPE_SUMMARIZE,
        ),
        help="당길 job 의 종류를 좁힌다 (없으면 그 세션의 가장 이른 job)",
    )
    p_guard.set_defaults(fn=cmd_guard)

    p_restore = sub.add_parser("restore", help="스냅샷을 되돌린다")
    p_restore.add_argument("--in", dest="snapshot", default="/tmp/p5-guard.json")
    p_restore.set_defaults(fn=cmd_restore)

    p_claim = sub.add_parser("claim", help="job 1건만 claim 해 처리한다")
    p_claim.add_argument("--expect-session", required=True, help="이 세션의 job 만 처리한다")
    p_claim.set_defaults(fn=cmd_claim)

    p_verify = sub.add_parser("verify", help="보존 세션 6개의 결과 API 상태를 찍는다")
    p_verify.set_defaults(fn=cmd_verify)

    args = parser.parse_args()
    return asyncio.run(args.fn(args))


if __name__ == "__main__":
    raise SystemExit(main())
