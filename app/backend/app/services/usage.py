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

from app.models.usage import PROVIDER_BEDROCK, TokenUsage, UsageRollup, UsageSink

logger = logging.getLogger(__name__)

# ⛔ `called_at`을 넘기지 않는다 — 013 의 기본값 `now()`가 SoT다. 앱에서 시각을 만들어 넣으면
# 서버 시계와 DB 시계가 갈라지고, 그 차이는 조용하다(전역 시각 규약).
_INSERT_LLM_CALL_SQL = """
insert into llm_calls (provider, model_id, purpose, job_id, input_tokens, output_tokens,
                       input_speech_tokens, input_text_tokens,
                       output_speech_tokens, output_text_tokens)
values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
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
        # 분해 넷은 Nova 만 채운다 — `None` 이 「분해 없음」이다(015 머리말 · `TokenUsage`).
        usage.input_speech_tokens,
        usage.input_text_tokens,
        usage.output_speech_tokens,
        usage.output_text_tokens,
    )


# ⛔ **날짜의 정본은 `users.timezone` 컬럼이다** (`TASK-126` · 전역 시각 규약 3항).
# `current_date` 를 쓰지 않는다 — 서버 세션 타임존의 날짜라 **UTC 자정~09:00(KST) 구간에서**
# **하루 이른 값**을 낸다.
# `daily_summary.py`·`chronic.py` 가 같은 판단을 이미 했고 그 이유를 그 파일들이 소유한다.
_TIMEZONE_SQL = "select timezone from users where id = $1"

# 하루·갈래별 집계. ⚠️ **분해 넷을 `coalesce` 로 0 으로 만들지 않는다** — `sum()` 이 전부 NULL 이면
# NULL 을 내고 그것이 「그 갈래에 분해가 없다」는 사실이다(Claude 행). 0 으로 바꾸면 「분해가 0」과
# 구분되지 않고 Nova 단가 계산이 거기서 어긋난다.
# ⛔ 금액을 계산하지 않는다 — 단가의 자리는 아직 결정되지 않았다(`TASK-126` AC#4).
_ROLLUP_SQL = """
select (called_at at time zone $1)::date as day,
       purpose,
       count(*)                    as calls,
       sum(input_tokens)           as input_tokens,
       sum(output_tokens)          as output_tokens,
       sum(input_speech_tokens)    as input_speech_tokens,
       sum(input_text_tokens)      as input_text_tokens,
       sum(output_speech_tokens)   as output_speech_tokens,
       sum(output_text_tokens)     as output_text_tokens
  from llm_calls
 where (called_at at time zone $1)::date > (now() at time zone $1)::date - $2::int
 group by 1, 2
 order by 1 desc, 2
"""


async def load_usage_summary(
    conn: asyncpg.Connection, user_id: UUID, *, days: int = 7
) -> list[UsageRollup]:
    """최근 `days` 일의 사용량을 **사용자 타임존 달력 날짜 × 갈래**로 집계한다 (`TASK-126`).

    타임존을 인자로 받지 않고 **여기서 읽는 이유**: 인자로 받으면 호출자가 하드코딩한 값이나
    호스트 시각을 넘길 수 있고, 그 어긋남은 조용하다. 정본은 컬럼이므로 이 함수가 컬럼을 본다
    (`load_chronic_metrics`·`daily_summary` 와 같은 형태). 사용자가 없으면 조용히 UTC 로 떨어지지
    않고 `LookupError` 를 올린다.

    ⚠️ `llm_calls` 에는 `user_id` 가 없다 — 단일 사용자 로컬 도구의 **비용** 표이고 학습자별로
    가르는 값이 아니다. 그래서 `user_id` 는 **날짜 경계를 정하는 용도**로만 쓴다.

    `days=7` 은 「오늘을 포함한 최근 7일」이다(경계는 `> 오늘 - days`).
    """
    timezone = await conn.fetchval(_TIMEZONE_SQL, user_id)
    if timezone is None:
        raise LookupError(f"user {user_id} not found — no timezone source of truth")

    records = await conn.fetch(_ROLLUP_SQL, timezone, days)
    return [
        UsageRollup(
            day=record["day"],
            purpose=record["purpose"],
            calls=record["calls"],
            input_tokens=record["input_tokens"],
            output_tokens=record["output_tokens"],
            input_speech_tokens=record["input_speech_tokens"],
            input_text_tokens=record["input_text_tokens"],
            output_speech_tokens=record["output_speech_tokens"],
            output_text_tokens=record["output_text_tokens"],
        )
        for record in records
    ]


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
