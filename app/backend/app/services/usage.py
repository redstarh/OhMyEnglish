"""LLM 호출 사용량을 `llm_calls`에 적는다 (`TASK-60` · 사용자 결정 66 · 마이그레이션 013).

왜 이 표인가: 호출 **1건 = 행 1건**이라 job 경로 밖 호출까지 담는다. `analysis_jobs`에 컬럼 둘을
더하는 안이 기각된 근거는 실측이다 — 2026-09-12 세션이 계획 생성 스파이크로 Claude 16회를 돌렸고
그 어느 것도 job 이 아니어서 그 표에는 한 행도 남지 않는다(013 머리말이 정본).

⛔ **기록 실패가 호출을 막지 않는다.** 사용량은 관측용 부가 정보이고, INSERT 가 깨졌다고 학습
세션이나 계획 생성이 멈추면 손해가 더 크다 — `api/ws.py`의 `_record_drill_turns_or_continue`가 세운
규약을 그대로 잇는다. ⚠️ 다만 `exception`으로 찍는다: 문서가 지정한 실행이 `--log-level warning`
이라 그 아래는 한 줄도 보이지 않는다(H-Z). 그리고 **잃는 것이 있다** — 놓친 호출의 비용은 복원할
수 없다(응답을 다시 받을 수 없다).
"""

from __future__ import annotations

import logging
from uuid import UUID

import asyncpg

from app.models.usage import PROVIDER_BEDROCK, TokenUsage, UsageSink

logger = logging.getLogger(__name__)

# ⛔ `called_at`을 넘기지 않는다 — 013 의 기본값 `now()`가 SoT다. 앱에서 시각을 만들어 넣으면
# 서버 시계와 DB 시계가 갈라지고, 그 차이는 조용하다(전역 시각 규약).
_INSERT_LLM_CALL_SQL = """
insert into llm_calls (provider, model_id, purpose, job_id, input_tokens, output_tokens)
values ($1, $2, $3, $4, $5, $6)
"""


async def record_llm_call(
    conn: asyncpg.Connection,
    usage: TokenUsage,
    *,
    provider: str,
    model_id: str,
    purpose: str,
    job_id: UUID | None,
) -> None:
    """사용량 1건을 적는다. 실패를 삼키지 않는다 — 삼키는 자리는 아래 sink 다.

    이 함수를 따로 두는 이유: 이미 연결을 잡고 있는 호출자(마이그레이션 검증·하네스)가 자기
    트랜잭션 안에서 부를 수 있어야 한다.
    """
    await conn.execute(
        _INSERT_LLM_CALL_SQL,
        provider,
        model_id,
        purpose,
        job_id,
        usage.input_tokens,
        usage.output_tokens,
    )


def pool_usage_sink(pool: asyncpg.Pool, *, provider: str = PROVIDER_BEDROCK) -> UsageSink:
    """풀에서 연결을 잡아 사용량을 적는 sink. **실패를 로그로 갚고 삼킨다**(모듈 docstring).

    함수를 돌려주는 형태인 이유: `workers/claude_client`는 `UsageSink` **프로토콜만** 알아야 하고
    `asyncpg`도 이 서비스도 몰라야 한다 — 그 경계가 단위 테스트를 DB 없이 돌게 한다.
    """

    async def sink(
        usage: TokenUsage,
        *,
        model_id: str,
        purpose: str,
        job_id: UUID | None,
    ) -> None:
        try:
            async with pool.acquire() as conn:
                await record_llm_call(
                    conn,
                    usage,
                    provider=provider,
                    model_id=model_id,
                    purpose=purpose,
                    job_id=job_id,
                )
        except (asyncpg.PostgresError, OSError):
            logger.exception(
                "LLM 사용량을 적지 못했다 — purpose=%s job=%s in=%d out=%d"
                " (이 비용은 복원할 수 없다)",
                purpose,
                job_id,
                usage.input_tokens,
                usage.output_tokens,
            )

    return sink
