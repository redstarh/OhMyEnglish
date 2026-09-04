"""`plan_next_session` job 처리 — Task 4~7이 이 모듈을 채운다.

지금은 워커가 job 종류로 분기할 수 있게 계약만 고정한다 (계획서 Task 3).
"""

from __future__ import annotations

import asyncpg

from app.services.jobs import ClaimedJob, report_failure
from app.workers.claude_client import ClaudeClient


async def process_plan(pool: asyncpg.Pool, claude: ClaudeClient, job: ClaimedJob) -> None:
    """계획 생성 job 하나를 처리한다. Task 4~7이 이 함수의 안을 채운다.

    지금은 대상 검증만 한다 — 계약을 먼저 고정해 워커 분기가 이 태스크에서 완결되게 한다.
    """
    if job.session_id is None:
        await report_failure(pool, job, f"plan job {job.id} has no session target")
        return
    raise NotImplementedError("Task 7이 저장까지 채운다")
