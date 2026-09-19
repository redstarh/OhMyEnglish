#!/usr/bin/env python3
"""B4 회차 드라이버 3 — TS-35(무대 생성·회전·진행·진입) + TS-31 AC#2 의 「결과를 커밋하지 않음」.

⚠️ **모델 호출만 스텁이다** — 프롬프트 조립·파서·저장·큐·회전 규칙은 실제 코드를 지나간다.
   Bedrock 을 부르지 않으므로 유료 호출은 0건이고 `llm_calls` 에도 남지 않는다.
⛔ 내가 만든 사용자와 생성 무대만 쓰고 끝에 지운다(픽스처 사용자를 건드리지 않는다).
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg

BACKEND = Path("/Users/redstar/MyProject/OhMyEnglish/app/backend")
sys.path.insert(0, str(BACKEND))

from app.services import jobs  # noqa: E402
from app.services.scenario_generator import process_scenario  # noqa: E402
from app.services.scenario_progress import load_scenario_progress  # noqa: E402
from app.services.scenario_rotation import (  # noqa: E402
    NEW,
    NEW_PER_WINDOW,
    WINDOW,
    Candidate,
    RecentPick,
    pick_scenario,
)
from app.services.sessions import create_session, load_session_scenario  # noqa: E402

MARK = "b4-scenario-driver"
TITLE = "B4 run marker stage at the airport counter"
OUT: dict[str, object] = {}


def dsn() -> str:
    for line in (BACKEND / ".env").read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL not found")


class StubClaude:
    """`ClaudeClient` 자리를 메운다 — `analyze` 하나만 쓰인다."""

    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.prompts: list[str] = []

    async def analyze(self, prompt: str, *, purpose: str = "", job_id: UUID | None = None) -> str:
        self.prompts.append(prompt)
        return json.dumps(self.payload, ensure_ascii=False)


async def seed(pool: asyncpg.Pool) -> tuple[UUID, UUID]:
    async with pool.acquire() as conn:
        uid = await conn.fetchval(
            "insert into users (display_name, timezone, current_level) "
            "values ($1, 'Asia/Seoul', 'B1') returning id",
            MARK,
        )
        sid = await conn.fetchval(
            "insert into learning_sessions (user_id, mode, status, ended_at) "
            "values ($1, 'scenario_intake', 'completed', now()) returning id",
            uid,
        )
        turns = [
            ("agent", "Where will you need English soon?"),
            ("user", "I have to check in at the airport counter next month."),
            ("agent", "Who will you talk to there?"),
            ("user", "The airline staff. I get nervous when they ask about my baggage."),
            ("user", "I want to sound polite but clear."),
        ]
        for i, (speaker, text) in enumerate(turns, start=1):
            await conn.execute(
                "insert into utterances (session_id, speaker, transcript, sequence_no) "
                "values ($1, $2, $3, $4)",
                sid,
                speaker,
                text,
                i,
            )
    return uid, sid


async def enqueue_and_claim(pool: asyncpg.Pool, sid: UUID) -> jobs.ClaimedJob:
    async with pool.acquire() as conn:
        job_id = await jobs.enqueue_generate_scenario(conn, sid)
        # 내 job 이 전역 최소가 되게 당긴다 — `claim_next` 는 `order by available_at limit 1` 이다.
        await conn.execute(
            "update analysis_jobs set available_at='1970-01-02T00:00:00Z' where id=$1", job_id
        )
    async with pool.acquire() as conn, conn.transaction():
        claimed = await jobs.claim_next(conn)
    assert claimed is not None and claimed.id == job_id, f"claimed someone else: {claimed}"
    return claimed


async def generated_rows(pool: asyncpg.Pool) -> list[dict[str, object]]:
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select id, category, level, title, source from learning_scenarios "
            "where source='generated'"
        )
    return [dict(r) for r in rows]


async def leg_lease_lost(pool: asyncpg.Pool, sid: UUID, stub: StubClaude) -> None:
    """TS-31 AC#2 의 나머지 절반 — 임대를 잃은 실제 호출자가 결과를 커밋하지 않는지."""
    claimed = await enqueue_and_claim(pool, sid)
    async with pool.acquire() as conn:
        await conn.execute(
            "update analysis_jobs set locked_by='b4-thief' where id=$1", claimed.id
        )
    before = len(await generated_rows(pool))
    await process_scenario(pool, stub, claimed)
    after = await generated_rows(pool)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select status, locked_by, last_error from analysis_jobs where id=$1", claimed.id
        )
    OUT["lease_lost_model_was_called"] = len(stub.prompts) == 1
    OUT["lease_lost_generated_before"] = before
    OUT["lease_lost_generated_after"] = len(after)
    OUT["lease_lost_result_not_committed"] = len(after) == before
    OUT["lease_lost_job_row"] = dict(row)
    OUT["lease_lost_no_failure_reported"] = row["last_error"] is None

    # 그 job 을 다시 pending 으로 풀어 다음 다리가 쓰게 한다(같은 세션에 중복 job 을 못 만든다).
    async with pool.acquire() as conn:
        await conn.execute(
            "update analysis_jobs set status='pending', locked_by=null, locked_at=null, "
            "attempts=0, available_at='1970-01-02T00:00:00Z' where id=$1",
            claimed.id,
        )
    return claimed.id


async def leg_generate(pool: asyncpg.Pool, job_id: UUID, stub: StubClaude) -> UUID:
    """TS-35 AC#1 전반 — 무대가 만들어지고 job 이 닫히는지."""
    async with pool.acquire() as conn, conn.transaction():
        claimed = await jobs.claim_next(conn)
    assert claimed is not None and claimed.id == job_id, f"claimed someone else: {claimed}"
    await process_scenario(pool, stub, claimed)
    rows = await generated_rows(pool)
    async with pool.acquire() as conn:
        status = await conn.fetchval("select status from analysis_jobs where id=$1", claimed.id)
    OUT["generate_job_status"] = status
    OUT["generate_rows"] = rows
    mine = [r for r in rows if r["title"] == TITLE]
    OUT["generate_row_is_mine"] = len(mine) == 1
    OUT["generate_level_from_app_not_model"] = mine[0]["level"] == "B1" if mine else None
    OUT["generate_prompt_mentions_axes"] = "다섯 축" in stub.prompts[-1]
    return mine[0]["id"]


async def leg_attach_and_progress(pool: asyncpg.Pool, uid: UUID, scenario_id: UUID) -> None:
    """TS-35 AC#1 후반·AC#3 — 다음 세션이 그 무대에 올라서고 진행 상태가 이어지는지."""
    new_sid = await create_session(pool, uid, mode="speaking")
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select scenario_id, scenario_pick from learning_sessions where id=$1", new_sid
        )
        OUT["attach_session_scenario_is_generated"] = row["scenario_id"] == scenario_id
        OUT["attach_pick"] = row["scenario_pick"]

        # 턴이 흘러도 같은 무대를 읽는지 — 발화를 넣고 두 번 읽는다.
        first = await load_session_scenario(conn, new_sid)
        for i, (speaker, text) in enumerate(
            [("agent", "Good evening."), ("user", "Hello, I would like to check in.")], start=1
        ):
            await conn.execute(
                "insert into utterances (session_id, speaker, transcript, sequence_no) "
                "values ($1, $2, $3, $4)",
                new_sid,
                speaker,
                text,
                i,
            )
        second = await load_session_scenario(conn, new_sid)
        OUT["progress_scenario_stable_across_turns"] = (
            first is not None and second is not None and first.title == second.title == TITLE
        )
        OUT["progress_title_across_turns"] = None if second is None else second.title
        OUT["progress_scenario_id_unchanged_in_row"] = await conn.fetchval(
            "select scenario_id from learning_sessions where id=$1", new_sid
        ) == scenario_id

        progress = await load_scenario_progress(conn, uid)
        mine = [p for p in progress if p.scenario_id == scenario_id]
        OUT["progress_row"] = (
            None
            if not mine
            else {
                "sessions": mine[0].sessions,
                "new_picks": mine[0].new_picks,
                "last_studied_on": str(mine[0].last_studied_on),
            }
        )
        OUT["progress_lists_unstudied_too"] = any(p.sessions == 0 for p in progress)
        OUT["progress_rows_total"] = len(progress)
    return new_sid


async def leg_rotation_pure() -> None:
    """TS-35 AC#2 — 순수 함수로 30회를 돌려 창마다 신규 몫이 지켜지는지 센다."""
    base = datetime(2026, 1, 1, tzinfo=UTC)
    candidates = [
        Candidate(
            scenario_id=UUID(int=i),
            last_used_at=None,
            created_at=base + timedelta(minutes=i),
            display_order=i,
        )
        for i in range(1, 11)
    ]
    history: list[RecentPick] = []
    used: dict[UUID, datetime] = {}
    picks: list[str] = []
    for turn in range(30):
        window = history[:WINDOW]
        pick = pick_scenario(
            recent=window,
            candidates=[
                Candidate(
                    scenario_id=c.scenario_id,
                    last_used_at=used.get(c.scenario_id),
                    created_at=c.created_at,
                    display_order=c.display_order,
                )
                for c in candidates
            ],
        )
        assert pick is not None
        picks.append(pick.pick)
        used[pick.scenario_id] = base + timedelta(hours=turn)
        history.insert(0, RecentPick(scenario_id=pick.scenario_id, pick=pick.pick))
    OUT["rotation_picks_30"] = "".join("N" if p == NEW else "R" for p in picks)
    OUT["rotation_new_total_30"] = picks.count(NEW)
    OUT["rotation_new_per_window"] = [
        picks[i : i + WINDOW].count(NEW) for i in range(0, 30, WINDOW)
    ]
    OUT["rotation_threshold"] = {"WINDOW": WINDOW, "NEW_PER_WINDOW": NEW_PER_WINDOW}
    OUT["rotation_ratio_holds"] = all(
        n <= NEW_PER_WINDOW for n in OUT["rotation_new_per_window"]  # type: ignore[union-attr]
    )


async def leg_rotation_db(pool: asyncpg.Pool, uid: UUID) -> None:
    """TS-35 AC#2 의 배선 절 — 실제 세션 생성이 그 규칙을 지나가는지(창 자르기 포함)."""
    seq: list[str] = []
    for _ in range(11):
        sid = await create_session(pool, uid, mode="speaking")
        async with pool.acquire() as conn:
            seq.append(
                await conn.fetchval("select scenario_pick from learning_sessions where id=$1", sid)
            )
    OUT["rotation_db_sequence"] = "".join("N" if p == NEW else "R" for p in seq)
    async with pool.acquire() as conn:
        OUT["rotation_db_candidate_count"] = await conn.fetchval(
            "select count(*) from learning_scenarios where level = 'B1'"
        )
        OUT["rotation_db_new_in_last_window"] = await conn.fetchval(
            "select count(*) from (select scenario_pick from learning_sessions "
            "where user_id=$1 and scenario_id is not null "
            "order by started_at desc, id desc limit $2) w where scenario_pick='new'",
            uid,
            WINDOW,
        )


async def cleanup(pool: asyncpg.Pool, uid: UUID) -> None:
    async with pool.acquire() as conn:
        await conn.execute("delete from users where id=$1", uid)  # 세션·job 은 cascade
        await conn.execute("delete from learning_scenarios where title=$1 and source='generated'", TITLE)
        OUT["cleanup_users_left"] = await conn.fetchval(
            "select count(*) from users where display_name=$1", MARK
        )
        OUT["cleanup_generated_left"] = await conn.fetchval(
            "select count(*) from learning_scenarios where source='generated'"
        )


async def main() -> None:
    pool = await asyncpg.create_pool(dsn(), min_size=1, max_size=4)
    uid = None
    try:
        uid, sid = await seed(pool)
        OUT["user_id"] = str(uid)
        stub = StubClaude(
            {
                "category": "travel",
                "title": TITLE,
                "prompt_template": "You are an airline check-in agent at a busy airport counter.",
            }
        )
        job_id = await leg_lease_lost(pool, sid, stub)
        scenario_id = await leg_generate(pool, job_id, stub)
        await leg_attach_and_progress(pool, uid, scenario_id)
        await leg_rotation_pure()
        await leg_rotation_db(pool, uid)
    finally:
        if uid is not None:
            await cleanup(pool, uid)
        await pool.close()
    print(json.dumps(OUT, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
