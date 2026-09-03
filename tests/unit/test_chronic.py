"""만성 지표 — 설계서 §6.1. 숫자는 계산, 판정은 Claude(§6.2)라서 이 모듈은 사실만 돌려준다.

세 가지를 단정한다: **지속 기간이 음수가 되지 않는다**(§6.1 함정 — 라이브 DB에서 -3.8초가
나왔다), 휴면 후 재발의 최대 공백, 그리고 **재발 일수가 사용자 타임존 기준**이라는 것(함정 H-S).

기대값은 계산이 아니라 실측이다 — 2026-09-04에 dev DB의 실제 표에 같은 쿼리를 걸어 확인했다.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import asyncpg
import pytest

from app.services.chronic import load_chronic_metrics

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
PATTERN_KEY = "article_missing_before_place_noun"

_SEQ = iter(range(1, 10_000))


async def _seed(conn: asyncpg.Connection) -> tuple[UUID, UUID]:
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'Chronic Test', 'Asia/Seoul', 'A2')",
        USER_ID,
    )
    session_id = await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        USER_ID,
    )
    pattern_id = await conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'article', $2, 'go to the + 장소 명사') returning id",
        USER_ID,
        PATTERN_KEY,
    )
    return session_id, pattern_id


async def _said_wrong(
    conn: asyncpg.Connection, session_id: UUID, pattern_id: UUID, at: datetime
) -> None:
    """지정한 시각에 그 패턴의 오류를 1건 말했다 — 발화 + occurrence 한 벌."""
    utterance_id = await conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
        "values ($1, 'user', 'I go to gym.', $2, $3) returning id",
        session_id,
        next(_SEQ),
        at,
    )
    await conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, 'go to gym', 'go to the gym', '정관사가 필요합니다.', 'medium', 0.9)",
        utterance_id,
        pattern_id,
    )


# ① AS2 — 지속 기간이 **음수가 되지 않는다**. error_patterns.created_at 을 시작으로 쓰면
#    라이브 DB에서 -3.8초가 나왔다(§6.1 실측 함정). 발화 시각의 min/max 로만 계산한다.
@pytest.mark.asyncio
async def test_span_uses_utterance_times_and_never_goes_negative(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    first = datetime.fromisoformat("2026-06-01T12:00:00+09:00")
    last = datetime.fromisoformat("2026-09-01T12:00:00+09:00")
    await _said_wrong(db_conn, session_id, pattern_id, first)
    await _said_wrong(db_conn, session_id, pattern_id, last)

    metrics = await load_chronic_metrics(db_conn, USER_ID)

    assert len(metrics) == 1
    metric = metrics[0]
    assert metric.first_seen == first
    assert metric.last_seen == last
    assert metric.span == last - first
    assert metric.span > timedelta(0)


# ② AS2 — 휴면 후 재발. 40일 공백이 가장 위험한 신호다(§6.1)
@pytest.mark.asyncio
async def test_max_gap_finds_the_dormant_period(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    base = datetime.fromisoformat("2026-06-01T12:00:00+09:00")
    for offset_days in (0, 1, 41, 42):  # 1일 → 40일 공백 → 1일
        await _said_wrong(db_conn, session_id, pattern_id, base + timedelta(days=offset_days))

    metrics = await load_chronic_metrics(db_conn, USER_ID)

    assert metrics[0].max_gap == timedelta(days=40)


# ③ 발생이 1건이면 공백이 없다 — lag() 의 첫 행은 null 이다
@pytest.mark.asyncio
async def test_max_gap_is_none_for_a_single_occurrence(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _said_wrong(
        db_conn, session_id, pattern_id, datetime.fromisoformat("2026-06-01T12:00:00+09:00")
    )

    metrics = await load_chronic_metrics(db_conn, USER_ID)

    assert metrics[0].max_gap is None


# ④ **함정 H-S** — 재발 일수는 사용자 타임존의 달력 날짜다. 같은 KST 날짜에 속한 두 발화를
#    UTC 로 세면 2일이 된다(2026-09-04 실측). 이 한 칸에 복습 주기·일일 계획이 걸린다.
@pytest.mark.asyncio
async def test_recurring_days_counts_calendar_days_in_the_user_timezone(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    # 둘 다 KST 2026-09-02 이지만 UTC 로는 09-01 과 09-02 로 갈린다
    for moment in ("2026-09-02T08:00:00+09:00", "2026-09-02T23:30:00+09:00"):
        await _said_wrong(db_conn, session_id, pattern_id, datetime.fromisoformat(moment))

    metrics = await load_chronic_metrics(db_conn, USER_ID)

    assert metrics[0].recurring_days == 1, "UTC 로 셌다 — users.timezone 을 쓰지 않았다 (H-S)"
    assert metrics[0].frequency == 0, "frequency 는 분석 워커가 재계산한다 — 이 쿼리는 읽기만 한다"


# ⑤ 발생이 없는 패턴은 목록에 없다 — 만성 지표는 실제 발생에서만 나온다
@pytest.mark.asyncio
async def test_a_pattern_without_occurrences_is_absent(db_conn: asyncpg.Connection):
    await _seed(db_conn)

    assert await load_chronic_metrics(db_conn, USER_ID) == []


# ⑥ **AS2 전체** — "서로 다른 4개 날짜 · 약 3개월 지속 · 40일 공백"을 한 번에 단정한다.
#    조각별로만 보면 recurring_days·recurring_sessions 가 아무 테스트에도 걸리지 않는다.
#    간격을 40·30·20일로 잡아 합이 90일(≈3개월)이면서 최대 공백이 40일이 되게 한다.
@pytest.mark.asyncio
async def test_as2_counts_days_sessions_span_and_gap_together(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    second_session = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        USER_ID,
    )
    base = datetime.fromisoformat("2026-06-01T12:00:00+09:00")
    await _said_wrong(db_conn, session_id, pattern_id, base)
    await _said_wrong(db_conn, session_id, pattern_id, base + timedelta(days=40))
    await _said_wrong(db_conn, second_session, pattern_id, base + timedelta(days=70))
    await _said_wrong(db_conn, second_session, pattern_id, base + timedelta(days=90))

    metric = (await load_chronic_metrics(db_conn, USER_ID))[0]

    assert metric.recurring_days == 4
    assert metric.recurring_sessions == 2
    assert metric.span == timedelta(days=90)
    assert metric.max_gap == timedelta(days=40)


# ⑦ 사용자가 없으면 타임존의 SoT 가 없다 — 조용히 UTC 로 떨어지지 않고 실패한다
@pytest.mark.asyncio
async def test_missing_user_raises_instead_of_defaulting_the_timezone(
    db_conn: asyncpg.Connection,
):
    with pytest.raises(LookupError):
        await load_chronic_metrics(db_conn, UUID("00000000-0000-0000-0000-0000000000ff"))
