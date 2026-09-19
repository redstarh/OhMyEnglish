#!/usr/bin/env python3
"""B4 회차 드라이버 4 — TS-32(복습 주기 1·3·7일 · 재발 되돌림 · 패턴 이름 재사용).

⚠️ **모델 호출만 스텁이다** — `process_analysis` 를 실제로 부르므로 패턴 upsert·발생 저장·
   `store_attempts`·`review.recompute`·`review_tasks` 사다리·일일 요약이 **전부 실제 경로**다.
⛔ 내가 만든 사용자의 행만 쓰고 끝에 사용자 1행을 지워 cascade 로 걷는다.
⚠️ 시각은 발화 행의 `created_at` 을 **내가 만들 때** 박는다 — 저장된 값을 나중에 변환·UPDATE
   하지 않는다(전역 시각 규약 4항).
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

from app.models.plan import PlanValidationError, parse_plan  # noqa: E402
from app.services import jobs  # noqa: E402
from app.services.analysis import process_analysis  # noqa: E402
from app.services.review import STAGE_DAYS  # noqa: E402

MARK = "b4-review-driver"
KEY = "article_b4_marker_stage"
KEY_RECASED = "Article_B4_Marker_Stage"
OUT: dict[str, object] = {}


def dsn() -> str:
    for line in (BACKEND / ".env").read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL not found")


class StubClaude:
    def __init__(self) -> None:
        self.payload: dict[str, object] = {"findings": []}
        self.calls = 0

    async def analyze(self, prompt: str, *, purpose: str = "", job_id: UUID | None = None) -> str:
        self.calls += 1
        return json.dumps(self.payload, ensure_ascii=False)


def finding(pattern_key: str) -> dict[str, object]:
    return {
        "category": "article",
        "pattern_key": pattern_key,
        "target_form": "go to the gym",
        "original_span": "go to gym",
        "correction": "go to the gym",
        "explanation": "장소를 가리키는 명사 앞에는 정관사 the 가 필요합니다.",
        "severity": "medium",
        "confidence": 0.9,
    }


async def add_utterance(
    pool: asyncpg.Pool, sid: UUID, seq: int, at: datetime, text: str
) -> UUID:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
            "values ($1, 'user', $2, $3, $4) returning id",
            sid,
            text,
            seq,
            at,
        )


async def run_analysis(pool: asyncpg.Pool, stub: StubClaude, utt: UUID) -> str:
    async with pool.acquire() as conn:
        job_id = await jobs.enqueue_analyze(conn, utt)
        await conn.execute(
            "update analysis_jobs set available_at='1970-01-02T00:00:00Z' where id=$1", job_id
        )
    async with pool.acquire() as conn, conn.transaction():
        claimed = await jobs.claim_next(conn)
    assert claimed is not None and claimed.id == job_id, f"claimed someone else: {claimed}"
    await process_analysis(pool, stub, claimed)
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "select status || coalesce(' / ' || last_error, '') from analysis_jobs where id=$1",
            job_id,
        )


async def pattern_state(pool: asyncpg.Pool, uid: UUID) -> dict[str, object]:
    async with pool.acquire() as conn:  # noqa: PLR0915
        rows = await conn.fetch(
            "select id, pattern_key, frequency, mastery_score, next_review_at "
            "from error_patterns where user_id=$1 order by pattern_key",
            uid,
        )
        ladder = []
        if rows:
            ladder = [
                dict(r)
                for r in await conn.fetch(
                    "select review_stage, status, due_at, completed_at, cycle_started_at "
                    "from review_tasks where pattern_id=$1 "
                    "order by cycle_started_at, review_stage",
                    rows[0]["id"],
                )
            ]
        occurrences = [
            dict(r)
            for r in await conn.fetch(
                "select eo.original_span, eo.correction, p.pattern_key "
                "from error_occurrences eo join error_patterns p on p.id = eo.pattern_id "
                "where p.user_id = $1 order by eo.id",
                uid,
            )
        ]
    return {
        "patterns": [{k: str(v) for k, v in dict(r).items()} for r in rows],
        "ladder": [{k: str(v) for k, v in row.items()} for row in ladder],
        "occurrences": [{k: str(v) for k, v in row.items()} for row in occurrences],
    }


async def leg_cycle(pool: asyncpg.Pool, uid: UUID, sid: UUID, stub: StubClaude) -> None:
    """AC#1·#2 — 1·3·7일 사다리가 실제로 전진하고 재발이 1일로 되돌리는지."""
    t0 = datetime.now(UTC) - timedelta(days=20)
    OUT["stage_days_const"] = list(STAGE_DAYS)
    steps: list[dict[str, object]] = []

    # ① 첫 오류 — 단계 1, 예정일 = 발화 시각 + 1일
    u1 = await add_utterance(pool, sid, 1, t0, "I usually go to gym after work.")
    stub.payload = {"findings": [finding(KEY)]}
    job1 = await run_analysis(pool, stub, u1)
    st = await pattern_state(pool, uid)
    steps.append(
        {
            "step": "1 첫 오류",
            "job": job1,
            "utterance_at": str(t0),
            "expected_next_review_at": str(t0 + timedelta(days=1)),
            **st,
        }
    )

    # ②③④ 예정일을 넘긴 정답 — 단계가 1→2→3 으로 접히고 마지막에 완주한다.
    schedule = [
        ("2 1일 뒤 정답", t0 + timedelta(days=1, minutes=1), 3),
        ("3 3일 더 뒤 정답", t0 + timedelta(days=4, minutes=5), 7),
        ("4 7일 더 뒤 정답", t0 + timedelta(days=11, minutes=10), None),
    ]
    seq = 2
    for label, at, next_gap in schedule:
        utt = await add_utterance(pool, sid, seq, at, "I usually go to the gym after work.")
        seq += 1
        stub.payload = {"findings": [], "attempts": [{"pattern_key": KEY, "outcome": "correct"}]}
        job = await run_analysis(pool, stub, utt)
        st = await pattern_state(pool, uid)
        steps.append(
            {
                "step": label,
                "job": job,
                "utterance_at": str(at),
                "expected_next_review_at": (
                    None if next_gap is None else str(at + timedelta(days=next_gap))
                ),
                **st,
            }
        )

    # ⑤ 재발 — **표기만 다른 key** 로 온다. 주기가 1일로 되돌려지고 쌍둥이 패턴이 생기지 않아야 한다.
    relapse_at = t0 + timedelta(days=12)
    u5 = await add_utterance(pool, sid, seq, relapse_at, "I go to gym on Sunday.")
    stub.payload = {"findings": [finding(KEY_RECASED)]}
    job5 = await run_analysis(pool, stub, u5)
    st = await pattern_state(pool, uid)
    steps.append(
        {
            "step": "5 재발(표기만 다른 key)",
            "job": job5,
            "utterance_at": str(relapse_at),
            "expected_next_review_at": str(relapse_at + timedelta(days=1)),
            **st,
        }
    )
    OUT["steps"] = steps

    # 판정 요약 — 기대값과 실제를 같은 자리에서 대조한다.
    def nra(step: dict[str, object]) -> str | None:
        pats = step["patterns"]  # type: ignore[index]
        return pats[0]["next_review_at"] if pats else None  # type: ignore[index]

    OUT["cycle_1_day"] = nra(steps[0]) == steps[0]["expected_next_review_at"]
    OUT["cycle_3_day"] = nra(steps[1]) == steps[1]["expected_next_review_at"]
    OUT["cycle_7_day"] = nra(steps[2]) == steps[2]["expected_next_review_at"]
    OUT["cycle_completed_clears_due"] = nra(steps[3]) == "None"
    OUT["cycle_mastery_after_completion"] = steps[3]["patterns"][0]["mastery_score"]  # type: ignore[index]
    OUT["relapse_back_to_1_day"] = nra(steps[4]) == steps[4]["expected_next_review_at"]
    OUT["relapse_mastery_reset"] = steps[4]["patterns"][0]["mastery_score"]  # type: ignore[index]
    OUT["pattern_row_count_after_recased_key"] = len(steps[4]["patterns"])  # type: ignore[arg-type]
    OUT["pattern_key_stored"] = steps[4]["patterns"][0]["pattern_key"]  # type: ignore[index]
    OUT["frequency_after_relapse"] = steps[4]["patterns"][0]["frequency"]  # type: ignore[index]
    OUT["ladder_stages_recorded"] = [row["review_stage"] for row in steps[3]["ladder"]]  # type: ignore[index]
    OUT["wrong_sentence_stored"] = steps[4]["occurrences"]  # type: ignore[index]

    # 음성 대조 — **규격 밖 신규 key** 는 저장되지 않아야 한다. 이것이 「재사용할 수 있는 이름」의
    # 반쪽이다: 형식 검사가 없으면 쌍둥이 패턴이 조용히 쌓인다.
    bad_at = t0 + timedelta(days=13)
    u6 = await add_utterance(pool, sid, 20, bad_at, "I go to gym again.")
    stub.payload = {"findings": [finding("Bad Key With Spaces")]}
    job6 = await run_analysis(pool, stub, u6)
    st6 = await pattern_state(pool, uid)
    OUT["malformed_new_key_job"] = job6
    OUT["malformed_new_key_pattern_rows"] = len(st6["patterns"])  # type: ignore[arg-type]
    OUT["malformed_new_key_rejected"] = len(st6["patterns"]) == 1  # type: ignore[arg-type]


def leg_level_step() -> None:
    """AC#3 — 난이도(CEFR)가 한 단계씩만 움직이고 하향도 허용되는지. 순수 함수 경로."""
    pattern_id = UUID(int=0x0B4)
    base = {
        "focus": [
            {
                "pattern_id": str(pattern_id),
                "pattern_key": KEY,
                "target_form": "go to the gym",
            }
        ],
        "questions": [
            {"prompt": "What did you do at work today?", "context": "work update"},
            {"prompt": "Tell me about your morning.", "context": "daily life"},
            {"prompt": "What will you do tomorrow?", "context": "plan"},
        ],
        "reason": "관사를 계속 빼먹어서 오늘은 그것만 봅니다.",
        "notes": ["짧은 문장에서는 관사를 붙이는데 길어지면 빼먹는다"],
    }

    def payload(level: str, action: str) -> str:
        body = dict(base)
        body["target_level"] = level
        body["instruction"] = {
            "target_level": level,
            "focus": [{"pattern_key": KEY, "target_form": "go to the gym"}],
            "sentence_length": "two short clauses",
            "hint_timing": "offer a starter after one long pause",
            "contexts": ["work update", "daily life", "plan"],
        }
        body["level"] = {
            "action": action,
            "target_level": level,
            "reason": "정답률이 근거입니다.",
        }
        return json.dumps(body, ensure_ascii=False)

    results: dict[str, object] = {}
    for label, level, action in (
        ("same_B1", "B1", "keep"),
        ("up_one_B2", "B2", "up"),
        ("down_one_A2", "A2", "down"),
        ("up_two_C1", "C1", "up"),
        ("down_two_A1", "A1", "down"),
    ):
        try:
            parsed = parse_plan(
                payload(level, action),
                current_level="B1",
                allowed_pattern_ids={pattern_id},
                deepest_pattern_id=None,
            )
            results[label] = f"accepted → {parsed.level.target_level}"
        except PlanValidationError as exc:
            results[label] = f"rejected: {exc}"
    OUT["level_steps"] = results
    OUT["level_one_step_up_allowed"] = str(results["up_one_B2"]).startswith("accepted")
    OUT["level_one_step_down_allowed"] = str(results["down_one_A2"]).startswith("accepted")
    OUT["level_two_step_up_rejected"] = str(results["up_two_C1"]).startswith("rejected")
    OUT["level_two_step_down_rejected"] = str(results["down_two_A1"]).startswith("rejected")


async def main() -> None:
    pool = await asyncpg.create_pool(dsn(), min_size=1, max_size=4)
    uid = None
    try:
        async with pool.acquire() as conn:
            uid = await conn.fetchval(
                "insert into users (display_name, timezone, current_level) "
                "values ($1, 'Asia/Seoul', 'B1') returning id",
                MARK,
            )
            sid = await conn.fetchval(
                "insert into learning_sessions (user_id, mode, status, ended_at, started_at) "
                "values ($1, 'speaking', 'completed', now(), now() - interval '20 days') "
                "returning id",
                uid,
            )
        OUT["user_id"] = str(uid)
        stub = StubClaude()
        await leg_cycle(pool, uid, sid, stub)
        leg_level_step()
        OUT["model_calls_stubbed"] = stub.calls
    finally:
        if uid is not None:
            async with pool.acquire() as conn:
                await conn.execute("delete from users where id=$1", uid)
                OUT["cleanup_users_left"] = await conn.fetchval(
                    "select count(*) from users where display_name=$1", MARK
                )
                OUT["cleanup_patterns_left"] = await conn.fetchval(
                    "select count(*) from error_patterns where pattern_key ilike $1", KEY
                )
        await pool.close()
    print(json.dumps(OUT, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
