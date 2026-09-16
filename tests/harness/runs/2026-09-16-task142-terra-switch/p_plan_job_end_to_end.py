#!/usr/bin/env python3
"""`TASK-142` AC#6 — 추천 job 을 **실물 terra 로** 돌려 계획이 저장되는지 본다.

⛔ 앱의 job 경로를 그대로 탄다 — `claim_next` → `process_plan` → `session_plans` insert.
프롬프트도 앱의 `build_plan_prompt` 가 만들고 검증도 앱의 `parse_plan` 이 한다.

    cd app/backend && DATABASE_URL=…/ohmyenglish_t142 \
      ./.venv/bin/python ../../tests/harness/runs/2026-09-16-task142-terra-switch/p_plan_job_end_to_end.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, "/Users/redstar/MyProject/OhMyEnglish/app/backend")

import asyncpg  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.models.usage import TokenUsage  # noqa: E402
from app.services.jobs import claim_next, enqueue_plan_next_session  # noqa: E402
from app.services.plan import process_plan  # noqa: E402
from app.services.usage import pool_usage_sink  # noqa: E402
from app.workers.claude_client import BedrockClaudeClient  # noqa: E402

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
TURNS = [
    "Yesterday I go to the gym and I run three kilometer.",
    "My team have a meeting tomorrow about the new project.",
    "I want improve my speaking for work presentation.",
]


async def _seed(conn: asyncpg.Connection) -> UUID:
    """끝난 세션 하나 · 학습 발화 셋 · 초점 후보 둘. 계획 job 이 읽을 최소 재료다.

    ⚠️ 후보가 0건이면 job 이 `no focus candidates yet` 으로 되돌아간다(첫 실행에서 관측했다) —
    즉 이 심기는 편의가 아니라 **그 경로에 도달하기 위한 조건**이다.
    """
    for key, category, target in (
        ("article_missing_before_place_noun", "article", "go to the gym"),
        ("verb_tense_past_simple_for_yesterday", "verb_tense", "I went"),
    ):
        await conn.execute(
            "insert into error_patterns (user_id, category, pattern_key, target_form, frequency, "
            "last_seen_at, next_review_at) values ($1, $2, $3, $4, 2, now(), now())",
            USER_ID,
            category,
            key,
            target,
        )
    session_id = await conn.fetchval(
        "insert into learning_sessions (user_id, mode, status, ended_at) "
        "values ($1, 'speaking', 'completed', now()) returning id",
        USER_ID,
    )
    for index, text in enumerate(TURNS, start=1):
        await conn.execute(
            "insert into utterances (session_id, speaker, utterance_type, transcript, sequence_no) "
            "values ($1, 'user', 'learning', $2, $3)",
            session_id,
            text,
            index,
        )
    return session_id


async def main() -> None:
    settings = get_settings()
    pool = await asyncpg.create_pool(dsn=os.environ["DATABASE_URL"], min_size=1, max_size=2)
    assert pool is not None
    calls: list[tuple[TokenUsage, str, str]] = []
    # 앱이 배선하는 sink 를 그대로 쓰고, 관측용으로 한 겹만 감싼다 (`llm_calls` 기록은 그쪽이 한다).
    app_sink = pool_usage_sink(pool)

    async def sink(usage, *, model_id, purpose, job_id):  # noqa: ANN001, ANN202
        calls.append((usage, model_id, purpose))
        await app_sink(usage, model_id=model_id, purpose=purpose, job_id=job_id)

    try:
        async with pool.acquire() as conn:
            session_id = await _seed(conn)
            await enqueue_plan_next_session(conn, session_id)
        job = None
        async with pool.acquire() as conn, conn.transaction():
            job = await claim_next(conn)
        assert job is not None, "계획 job 을 집지 못했다"
        print(f"집은 job: {job.job_type} · 세션 {job.session_id}")

        claude = BedrockClaudeClient(settings, usage_sink=sink)
        await process_plan(pool, claude, job)

        async with pool.acquire() as conn:
            plan = await conn.fetchrow(
                "select target_level, source, jsonb_array_length(questions) as questions, "
                "cardinality(focus_pattern_ids) as focus, instruction "
                "from session_plans where session_id = $1",
                session_id,
            )
            llm = await conn.fetch(
                "select model_id, purpose, input_tokens, output_tokens from llm_calls"
            )
            job_row = await conn.fetchrow(
                "select status, attempts, last_error from analysis_jobs where id = $1", job.id
            )
        result = {
            "job": dict(job_row) if job_row else None,
            "plan": {
                key: plan[key] for key in ("target_level", "source", "questions", "focus")
            }
            if plan
            else None,
            "instruction_keys": sorted(json.loads(plan["instruction"]).keys()) if plan else None,
            "llm_calls": [dict(row) for row in llm],
            "usage_sink_calls": [(u.input_tokens, u.output_tokens, m, p) for u, m, p in calls],
        }
        out = Path(__file__).with_name("plan_job_end_to_end.json")
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print(f"-> {out}")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
