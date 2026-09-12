"""`llm_calls` 기록 (`TASK-60` · 사용자 결정 66 · 마이그레이션 013).

여기서 재는 것은 **행이 실제로 쌓이는가**와 **실패가 호출을 막지 않는가** 둘이다. 사용량 값을
읽어내는 것(`extract_usage`)과 호출 시점(절단된 호출도 적는가)은 `tests/unit/test_claude_schema.py`
가 잰다 — DB 없이 재는 쪽이 그 계약의 자리다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import asyncpg
import pytest

from app.models.usage import PROVIDER_BEDROCK, PURPOSE_NOVA, PURPOSE_SPIKE, TokenUsage
from app.services.jobs import JOB_TYPE_GENERATE_SCENARIO, JOB_TYPE_SUMMARIZE
from app.services.usage import load_usage_summary, pool_usage_sink, record_llm_call

pytestmark = pytest.mark.asyncio

_USER_ID = uuid4()


async def _insert_user(conn: asyncpg.Connection, *, timezone: str) -> None:
    """이 파일 전용 사용자 1행. `db_conn` 은 롤백되는 트랜잭션이라 teardown 이 필요 없다."""
    await conn.execute(
        "insert into users (id, display_name, timezone) values ($1, 'Usage', $2)",
        _USER_ID,
        timezone,
    )


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


async def test_record_llm_call_stores_the_nova_token_split(db_conn: asyncpg.Connection):
    """`TASK-124`(결정 68) — Nova 는 speech·text 분해를 함께 적는다.

    ⛔ 합계와 분해가 **서로를 대신하지 않는다**: 합계 열은 `usageEvent.totalInputTokens` 이고 분해는
    `details.total` 이다. 단가가 다를 수 있어 분해가 없으면 금액을 재구성할 수 없다(015 머리말).
    """
    await record_llm_call(
        db_conn,
        TokenUsage(
            input_tokens=172,
            output_tokens=34,
            input_speech_tokens=150,
            input_text_tokens=22,
            output_speech_tokens=30,
            output_text_tokens=4,
        ),
        provider=PROVIDER_BEDROCK,
        model_id="amazon.nova-2-sonic-v1:0",
        purpose=PURPOSE_NOVA,
        job_id=None,
    )

    row = await db_conn.fetchrow("select * from llm_calls")
    assert row is not None
    assert (row["input_tokens"], row["output_tokens"]) == (172, 34)
    assert (row["input_speech_tokens"], row["input_text_tokens"]) == (150, 22)
    assert (row["output_speech_tokens"], row["output_text_tokens"]) == (30, 4)


async def test_a_claude_call_leaves_the_split_null_instead_of_zero(db_conn: asyncpg.Connection):
    """⛔ Claude 는 그 축이 **아예 없다** — 0 을 적으면 「speech 토큰을 쓰지 않았다」를 발명한다.

    ⚠️ 이 음성 케이스가 위 테스트의 판별력을 만든다: 없으면 분해를 0 으로 채우는 구현도 통과하고,
    그러면 「분해 없음」과 「분해가 0」이 구분되지 않아 Nova 집계가 조용히 오염된다.
    """
    await record_llm_call(
        db_conn,
        TokenUsage(input_tokens=30, output_tokens=9),
        provider=PROVIDER_BEDROCK,
        model_id="us.anthropic.claude-opus-5",
        purpose=PURPOSE_SPIKE,
        job_id=None,
    )

    row = await db_conn.fetchrow("select * from llm_calls")
    assert row is not None
    assert row["input_speech_tokens"] is None
    assert row["input_text_tokens"] is None
    assert row["output_speech_tokens"] is None
    assert row["output_text_tokens"] is None


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


# ── `TASK-134` — job 갈래의 기록이 «실제로 남는지» 잰다 ────────────────────────────
#
# ⛔ **「호출했다」를 재면 이 결함이 초록으로 지나간다.** `pool_usage_sink` 가 `PostgresError` 를
# 삼키고 `exception` 으로만 찍으므로 값역 밖 `purpose` 는 **호출은 성공하고 기록만 사라진다.**
# 실측(2026-09-13): 013 의 값역이 넷뿐인데 `scenario_generator` 가 `generate_scenario` 를 넘겨
# 그 job 의 토큰 기록이 **0건**이었다 — 결정 66 이 요구한 것이 조용히 꺼져 있었다.
# ⇒ 재는 축은 **`llm_calls` 에 행이 생기는가** 하나다.


async def test_the_job_purposes_actually_land_a_row(db_pool: asyncpg.Pool):
    """⛔ job 갈래 둘이 실제로 기록된다 — 021 이 값역에 넣은 값들이다.

    ⚠️ `db_pool`(커밋되는 픽스처)을 쓰는 이유: sink 가 **풀에서 자기 연결을 잡는다.** 롤백
    트랜잭션으로는 그 경로를 지나갈 수 없다. ⇒ 심은 행을 손으로 지운다.
    """
    sink = pool_usage_sink(db_pool)
    model_id = f"task134-{uuid4().hex[:8]}"
    try:
        for purpose in (JOB_TYPE_GENERATE_SCENARIO, JOB_TYPE_SUMMARIZE):
            await sink(
                TokenUsage(input_tokens=7, output_tokens=3),
                model_id=model_id,
                purpose=purpose,
                job_id=None,
            )
        async with db_pool.acquire() as conn:
            landed = await conn.fetch(
                "select purpose, input_tokens, output_tokens from llm_calls"
                " where model_id = $1 order by purpose",
                model_id,
            )
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from llm_calls where model_id = $1", model_id)

    assert [row["purpose"] for row in landed] == [
        JOB_TYPE_GENERATE_SCENARIO,
        JOB_TYPE_SUMMARIZE,
    ], "job 갈래의 기록이 남지 않았다 — 값역이 그 값을 막고 sink 가 그것을 삼켰다"
    assert [(row["input_tokens"], row["output_tokens"]) for row in landed] == [(7, 3), (7, 3)]


async def test_the_sink_swallows_a_rejected_purpose_and_says_so(
    db_pool: asyncpg.Pool, caplog: pytest.LogCaptureFixture
):
    """⛔ **삼키는 것을 유지하되 «말하게» 한다** (`TASK-134` AC#3 의 판단).

    삼키는 이유는 바뀌지 않는다 — 기록 실패로 job 을 실패시키면 「비용은 나갔고 결과는 잃는다」가
    된다. ⚠️ 다만 값역 위반은 **설정 오류**라 운영 중 조용히 넘길 것이 아니므로 `exception` 이
    남는 것을 이 단정이 지킨다. 그 로그가 없으면 이 부류를 **다시** 눈으로 찾아야 한다.
    """
    sink = pool_usage_sink(db_pool)
    with caplog.at_level("ERROR"):
        await sink(
            TokenUsage(input_tokens=1, output_tokens=1),
            model_id="task134-rejected",
            purpose="ㅁ분류없음",
            job_id=None,
        )

    async with db_pool.acquire() as conn:
        rows = await conn.fetchval(
            "select count(*) from llm_calls where model_id = $1", "task134-rejected"
        )
    assert rows == 0, "값역 밖인데 행이 생겼다 — CHECK 가 막지 못했다"
    assert any("사용량을 적지 못했다" in record.message for record in caplog.records), (
        "삼키면서 아무 말도 하지 않았다 — 이 부류를 다시 눈으로 찾게 된다"
    )


# ── `TASK-126` — 읽는 쪽. ⛔ 날짜의 정본은 `users.timezone` 이다 ─────────────────────


async def _seed_call(
    conn: asyncpg.Connection,
    *,
    called_at: datetime,
    purpose: str = PURPOSE_SPIKE,
    usage: TokenUsage | None = None,
) -> None:
    """`called_at` 을 직접 심는다 — 날짜 경계를 재려면 기본값(`now()`)으로는 못 잰다."""
    used = usage or TokenUsage(input_tokens=10, output_tokens=2)
    await conn.execute(
        "insert into llm_calls (provider, model_id, purpose, input_tokens, output_tokens,"
        " input_speech_tokens, input_text_tokens, output_speech_tokens, output_text_tokens,"
        " called_at) values ($1, 'm', $2, $3, $4, $5, $6, $7, $8, $9)",
        PROVIDER_BEDROCK,
        purpose,
        used.input_tokens,
        used.output_tokens,
        used.input_speech_tokens,
        used.input_text_tokens,
        used.output_speech_tokens,
        used.output_text_tokens,
        called_at,
    )


async def test_the_rollup_uses_the_users_timezone_not_the_server_date(
    db_conn: asyncpg.Connection,
):
    """⛔ **UTC 자정~09:00(KST) 구간의 행이 KST 날짜로 묶여야 한다** (전역 시각 규약 3항).

    ⚠️ 이 단정이 이 파일에서 가장 값어치 있는 자리다: `at time zone` 을 빼거나 `current_date` 로
    바꾸면 이 행이 **하루 이른 날짜**로 묶여 깨진다. 실측 함정이 그 구간에서 관측됐다.
    """
    await _insert_user(db_conn, timezone="Asia/Seoul")
    # 2026-09-11 23:30 UTC = 2026-09-12 08:30 KST — UTC 날짜와 KST 날짜가 «다른» 순간이다.
    await _seed_call(db_conn, called_at=datetime(2026, 9, 11, 23, 30, tzinfo=UTC))

    rollups = await load_usage_summary(db_conn, _USER_ID, days=3650)

    assert len(rollups) == 1
    assert rollups[0].day.isoformat() == "2026-09-12", "UTC 날짜(09-11)로 묶였다 — 규약 3항 위반"


async def test_the_rollup_splits_by_purpose_and_sums_the_token_split(
    db_conn: asyncpg.Connection,
):
    await _insert_user(db_conn, timezone="Asia/Seoul")
    nova = TokenUsage(
        input_tokens=216,
        output_tokens=0,
        input_speech_tokens=150,
        input_text_tokens=66,
        output_speech_tokens=0,
        output_text_tokens=0,
    )
    await _seed_call(
        db_conn, called_at=datetime(2026, 9, 12, 1, 0, tzinfo=UTC), purpose=PURPOSE_NOVA, usage=nova
    )
    await _seed_call(
        db_conn, called_at=datetime(2026, 9, 12, 2, 0, tzinfo=UTC), purpose=PURPOSE_NOVA, usage=nova
    )
    await _seed_call(
        db_conn, called_at=datetime(2026, 9, 12, 3, 0, tzinfo=UTC), purpose=PURPOSE_SPIKE
    )

    rollups = await load_usage_summary(db_conn, _USER_ID, days=3650)
    by_purpose = {row.purpose: row for row in rollups}

    # 두 Nova 행이 한 갈래로 합쳐지고 분해도 합산된다.
    assert by_purpose[PURPOSE_NOVA].calls == 2
    assert by_purpose[PURPOSE_NOVA].input_tokens == 432
    assert by_purpose[PURPOSE_NOVA].input_speech_tokens == 300
    assert by_purpose[PURPOSE_NOVA].input_text_tokens == 132
    # ⛔ 갈래가 섞이지 않는다 — 섞이면 비용이 틀린 축에 얹힌다.
    assert by_purpose[PURPOSE_SPIKE].calls == 1
    assert by_purpose[PURPOSE_SPIKE].input_tokens == 10


async def test_a_purpose_without_any_split_stays_null_not_zero(db_conn: asyncpg.Connection):
    """⛔ 분해가 전부 없는 갈래(Claude)는 `None` 으로 남는다 — 0 으로 바꾸면 사실이 달라진다.

    ⚠️ 이 음성 케이스가 위 테스트의 판별력을 만든다: `coalesce(sum(...), 0)` 로 바꿔도 위는
    통과하고, 그러면 「분해 없음」과 「분해가 0」이 구분되지 않는다.
    """
    await _insert_user(db_conn, timezone="Asia/Seoul")
    await _seed_call(db_conn, called_at=datetime(2026, 9, 12, 3, 0, tzinfo=UTC))

    rollups = await load_usage_summary(db_conn, _USER_ID, days=3650)

    assert rollups[0].input_speech_tokens is None
    assert rollups[0].output_text_tokens is None


async def test_the_rollup_refuses_to_guess_a_timezone_for_a_missing_user(
    db_conn: asyncpg.Connection,
):
    """⛔ 사용자가 없으면 조용히 UTC 로 떨어지지 않는다 — 틀린 날짜가 틀린 집계보다 나쁘다."""
    with pytest.raises(LookupError, match="timezone"):
        await load_usage_summary(db_conn, uuid4(), days=7)


async def test_the_window_excludes_rows_outside_the_requested_days(
    db_conn: asyncpg.Connection,
):
    await _insert_user(db_conn, timezone="Asia/Seoul")
    await _seed_call(db_conn, called_at=datetime(2020, 1, 1, tzinfo=UTC))

    assert await load_usage_summary(db_conn, _USER_ID, days=7) == []


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
