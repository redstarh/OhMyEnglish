"""`llm_calls` 기록 (`TASK-60` · 사용자 결정 66 · 마이그레이션 013).

여기서 재는 것은 **행이 실제로 쌓이는가**와 **실패가 호출을 막지 않는가** 둘이다. 사용량 값을
읽어내는 것(`extract_usage`)과 호출 시점(절단된 호출도 적는가)은 `tests/unit/test_claude_schema.py`
가 잰다 — DB 없이 재는 쪽이 그 계약의 자리다.
"""

from __future__ import annotations

from uuid import uuid4

import asyncpg
import pytest

from app.models.usage import PROVIDER_BEDROCK, PURPOSE_SPIKE, TokenUsage
from app.services.usage import pool_usage_sink, record_llm_call

pytestmark = pytest.mark.asyncio


async def test_record_llm_call_stores_the_counts_and_the_attribution(
    db_conn: asyncpg.Connection,
):
    await record_llm_call(
        db_conn,
        TokenUsage(input_tokens=3690, output_tokens=412),
        provider=PROVIDER_BEDROCK,
        model_id="us.anthropic.claude-opus-5",
        purpose=PURPOSE_SPIKE,
        job_id=None,
    )

    row = await db_conn.fetchrow("select * from llm_calls")
    assert row is not None
    assert row["provider"] == PROVIDER_BEDROCK
    assert row["model_id"] == "us.anthropic.claude-opus-5"
    assert row["purpose"] == PURPOSE_SPIKE
    # ⚠️ job 밖 호출이 null 인 것이 **정상**이다 — 그 호출을 담는 것이 이 표의 존재 이유다.
    assert row["job_id"] is None
    assert row["input_tokens"] == 3690
    assert row["output_tokens"] == 412
    # 013 의 기본값이 시각의 SoT 다(앱에서 만들어 넣지 않는다).
    assert row["called_at"] is not None
    assert row["called_at"].tzinfo is not None, "절대 시각이어야 한다 — naive 면 tz 를 잃는다"


async def test_the_purpose_value_range_is_guarded_by_the_migration_not_by_code(
    db_conn: asyncpg.Connection,
):
    """⛔ 값역 밖 값은 **조용히 다른 갈래로 바뀌지 않고** DB 에서 막힌다.

    이 단정이 있는 이유: 코드가 값역을 복제하지 않기로 했으므로(`models/usage.py`) 그 결정이
    성립하려면 **CHECK 가 실제로 막는다**는 것이 게이트로 남아 있어야 한다.
    """
    with pytest.raises(asyncpg.IntegrityConstraintViolationError):
        await record_llm_call(
            db_conn,
            TokenUsage(input_tokens=1, output_tokens=1),
            provider=PROVIDER_BEDROCK,
            model_id="m",
            purpose="ㅁ분류없음",
            job_id=None,
        )


async def test_the_pool_sink_swallows_a_failure_so_the_call_is_not_lost(
    db_pool: asyncpg.Pool,
    caplog: pytest.LogCaptureFixture,
):
    """⛔ 기록 실패가 학습 세션·계획 생성을 멈추면 손해가 더 크다 — 삼키고 `exception` 으로 갚는다.

    ⚠️ 이 음성 케이스가 그 규약의 판별력을 만든다. 없으면 sink 가 예외를 그대로 올리도록 바꿔도
    초록이고, 그러면 `llm_calls` 하나 때문에 계획 job 이 실패로 떨어진다.
    """
    sink = pool_usage_sink(db_pool)

    with caplog.at_level("ERROR"):
        # `purpose` 가 값역 밖이라 INSERT 가 깨진다 — 그래도 예외가 밖으로 나오지 않아야 한다.
        await sink(
            TokenUsage(input_tokens=1, output_tokens=2),
            model_id="m",
            purpose="ㅁ분류없음",
            job_id=uuid4(),
        )

    assert "LLM 사용량을 적지 못했다" in caplog.text
