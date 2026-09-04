"""`plan_next_session` job 처리 — Task 4~7이 이 모듈을 채운다.

지금은 워커가 job 종류로 분기할 수 있게 계약만 고정한다 (계획서 Task 3).
"""

from __future__ import annotations

import logging

import asyncpg

from app.services.jobs import ClaimedJob, report_failure
from app.workers.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

# Task 7이 저장까지 채우기 전까지 정상 대상 job이 수렴하는 사유. `raise`가 아니라
# 이 문구로 report_failure를 부르는 이유(리뷰 라운드 1, I4): `raise`는 워커의 바깥
# `except`로 새서 이 job을 `running`에 lease가 풀리지 않은 채 남기고(complete도
# fail_or_retry도 안 불린다), lease 만료(5분×5회)까지 걸리며, 기록되는 사유도
# "lease expired without report"라는 거짓 진단이 된다. `report_failure`는 큐를
# 정상 백오프로 재큐하고 참인 사유를 남긴다 — 가시성은 아래 `logger.warning`으로
# 옮긴다(이 리포는 지정된 실행에서 INFO가 안 보이는 함정 H-Z가 있어 WARNING 이상이어야 한다).
PLAN_NOT_IMPLEMENTED = "plan generation is not implemented yet (Task 7)"


async def process_plan(pool: asyncpg.Pool, claude: ClaudeClient, job: ClaimedJob) -> None:
    """계획 생성 job 하나를 처리한다. Task 4~7이 이 함수의 안을 채운다.

    지금은 대상 검증만 한다 — 계약을 먼저 고정해 워커 분기가 이 태스크에서 완결되게 한다.
    """
    if job.session_id is None:
        await report_failure(pool, job, f"plan job {job.id} has no session target")
        return
    logger.warning("job %s: plan generation not implemented yet (Task 7)", job.id)
    await report_failure(pool, job, PLAN_NOT_IMPLEMENTED)
