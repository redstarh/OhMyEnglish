"""만성 지표 — 설계서 §6.1. 숫자는 계산, 판정은 Claude(§6.2)라서 이 모듈은 사실만 돌려준다.

세 가지를 단정한다: **지속 기간이 음수가 되지 않는다**(§6.1 함정 — 라이브 DB에서 -3.8초가
나왔다), 휴면 후 재발의 최대 공백, 그리고 **재발 일수가 사용자 타임존 기준**이라는 것(함정 H-S).

기대값은 계산이 아니라 실측이다 — 2026-09-04에 dev DB의 실제 표에 같은 쿼리를 걸어 확인했다.

파일 끝에 AC11-2의 **깊이 순위**(`deepest_recurrence`)가 붙는다 — 그쪽은 이미 계산된 지표
목록 위의 순수 함수라 DB를 쓰지 않는다. 규칙의 정본은
`docs/design/2026-09-06-review-outcomes.md` §2다.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest
from conftest import chronic_metric

from app.services.chronic import deepest_recurrence, load_chronic_metrics

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


# ── 이연 LOW-12 — chronic SQL 세부 3개는 이 계획(계획서 Task 4)이 첫 소비자다 ──────────


# ① 정렬이 pattern_key 순인지 (뮤테이션: order by 제거)
@pytest.mark.asyncio
async def test_chronic_metrics_are_ordered_by_pattern_key(db_conn, seed_two_patterns):
    user_id = await seed_two_patterns(db_conn, keys=["zebra_last", "alpha_first"])

    metrics = await load_chronic_metrics(db_conn, user_id)

    assert [metric.pattern_key for metric in metrics] == ["alpha_first", "zebra_last"]


# ② 최대 공백은 **인접 간격의 최대값**이다 — 전체 지속기간(span, 44일)이 아니라 그 안의
#    간격들(2, 40, 2일) 중 최댓값(40일)인지를 본다.
#    ⚠️ 브리프가 제안한 뮤테이션("lag 의 tie-break 변경")은 **이 값에 관측 가능한 효과가
#    없다**(2026-09-04 실측) — 이 테스트 데이터에 동시각 발생이 없어 tie-break가 아예
#    갈리지 않는다. 실제로 이 테스트를 red로 만드는 뮤테이션은 `max(...)`를 `min(...)`으로
#    바꾸는 것이다(직접 확인: red).
@pytest.mark.asyncio
async def test_max_gap_is_largest_adjacent_interval(db_conn, seed_occurrences_on_days):
    user_id, _ = await seed_occurrences_on_days(db_conn, days=[0, 2, 42, 44])

    metrics = await load_chronic_metrics(db_conn, user_id)

    # 간격은 2, 40, 2 → 최대 40일
    assert metrics[0].max_gap == timedelta(days=40)


# ③ 발생이 1건이면 최대 공백이 없다.
#    ⚠️ 브리프가 제안한 뮤테이션("where prev_at is not null 제거")도 **이 값에 관측 가능한
#    효과가 없다**(2026-09-04 실측) — `gap`이 바깥 쿼리에 `left join`되고 `max()`가 NULL을
#    무시하므로, 그 필터가 있든 없든(단일 발생이면 prev_at이 애초에 NULL이라) `max_gap`은
#    항상 NULL로 귀결된다. 이 줄은 review.py `_HISTORY_SQL`의 strict `>`와 같은 종류의
#    무해한 중복 방어다 — 그래도 이 테스트는 "발생 1건 → 공백 없음"이라는 실제 불변조건은
#    지킨다(`span == 0`과 함께 그 자체로 의미 있는 단정이다).
@pytest.mark.asyncio
async def test_single_occurrence_has_no_max_gap(db_conn, seed_occurrences_on_days):
    user_id, _ = await seed_occurrences_on_days(db_conn, days=[0])

    metrics = await load_chronic_metrics(db_conn, user_id)

    assert metrics[0].max_gap is None
    assert metrics[0].span == timedelta(0)


# ── AC11-2 — "가장 깊은 재발"의 순위 ────────────────────────────────────────
#
# 규칙의 정본은 `docs/design/2026-09-06-review-outcomes.md` §2다: **최다 `frequency`이고,
# 동률이면 `recurring_sessions` → `recurring_days` 순으로 깬다.** 아래 4건은 DB 를 쓰지
# 않는다(`db_conn`을 요청하지 않는다) — `deepest_recurrence`는 이미 계산된 지표 목록 위의
# 순수 함수다.
#
# ⚠️ **최상위를 목록의 첫 자리에 두지 않는다.** 첫 항목을 그냥 돌려주는 구현이 그래도
# 통과하면 이 테스트는 순위를 재는 것이 아니라 목록 순서를 재는 것이 된다.


def test_deepest_recurrence_is_none_for_an_empty_list():
    # 콜드스타트 — 만성 목록이 비면 강제할 최상위가 존재하지 않는다(§2 경고 1).
    assert deepest_recurrence([]) is None


def test_deepest_recurrence_picks_the_highest_frequency():
    low = chronic_metric(uuid4(), frequency=1)
    high = chronic_metric(uuid4(), frequency=7)
    middle = chronic_metric(uuid4(), frequency=3)

    top = deepest_recurrence([low, middle, high])

    assert top is not None
    assert top.pattern_id == high.pattern_id


def test_a_frequency_tie_is_broken_by_recurring_sessions():
    fewer_sessions = chronic_metric(uuid4(), frequency=3, recurring_sessions=2, recurring_days=9)
    more_sessions = chronic_metric(uuid4(), frequency=3, recurring_sessions=5, recurring_days=1)

    top = deepest_recurrence([fewer_sessions, more_sessions])

    # `recurring_days`가 더 큰 쪽이 아니라 `recurring_sessions`가 더 큰 쪽이 이긴다 —
    # 두 축의 우선순위가 뒤집히면 이 단정이 깨진다.
    assert top is not None
    assert top.pattern_id == more_sessions.pattern_id


def test_a_frequency_and_session_tie_is_broken_by_recurring_days():
    fewer_days = chronic_metric(uuid4(), frequency=3, recurring_sessions=2, recurring_days=2)
    more_days = chronic_metric(uuid4(), frequency=3, recurring_sessions=2, recurring_days=6)

    top = deepest_recurrence([fewer_days, more_days])

    assert top is not None
    assert top.pattern_id == more_days.pattern_id


# 복습 예정(`due_reviews`)은 최심 판정에 섞이지 않는다 — 시간 축이지 깊이 축이 아니다(§2
# 근거 3). 그 경계는 **인터페이스로** 지켜진다: 이 함수는 `ChronicMetric`만 받으므로
# `DueReview`(애초에 `frequency`가 없다)를 넣을 자리가 없다.
def test_deepest_recurrence_only_reads_the_chronic_depth_fields():
    metrics = [chronic_metric(uuid4(), frequency=2), chronic_metric(uuid4(), frequency=4)]

    top = deepest_recurrence(metrics)

    assert top is not None
    # 순위에 쓰인 세 필드만으로 승자가 결정됐다 — `next_review_at`은 None 이고
    # `mastery_score`는 두 항목이 같다(전부 0.00 이라 판별력이 없다는 실측).
    assert top.next_review_at is None
    assert {metric.mastery_score for metric in metrics} == {0.0}
    assert top.frequency == 4
