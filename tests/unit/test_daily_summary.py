"""일일 오류 요약 — PRD §13 · 설계서 `docs/design/2026-09-11-daily-error-summary-design.md`.

이 파일이 단정하는 것 넷.

* 요약의 날짜가 **사용자 타임존의 달력 날짜**다(R13-3 · AC13-2). 한국 시각 자정 직후의 발화가
  UTC 날짜로 하루 앞의 요약에 들어가지 않는다.
* 앵커가 **발화 시각**이다(설계서 §6). `error_occurrences.created_at`(분석 저장 시각)을 쓰면
  새벽에 돌아간 분석이 발화를 다음 날짜로 밀어 넣는다.
* 다시 계산해도 값이 부풀지 않는다(R13-6 · AC13-3) — 재분석이 같은 함수를 지난다.
* 「분석이 돌고 오류 0건」과 「그날 학습이 없음」이 구별된다(R13-7).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import asyncpg
import pytest

from app.services.daily_summary import (
    load_daily_completion,
    load_daily_summary,
    load_history,
    load_streak,
    refresh_summary_for_utterance,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
KST = ZoneInfo("Asia/Seoul")

_SEQ = iter(range(1, 10_000))


async def _seed_user(conn: asyncpg.Connection, *, tz: str = "Asia/Seoul") -> None:
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'Daily Summary Test', $2, 'A2')",
        USER_ID,
        tz,
    )


async def _seed_session(conn: asyncpg.Connection) -> UUID:
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        USER_ID,
    )


async def _seed_pattern(
    conn: asyncpg.Connection,
    *,
    key: str,
    category: str = "article",
    target_form: str = "the + 명사",
) -> UUID:
    return await conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, $2, $3, $4) returning id",
        USER_ID,
        category,
        key,
        target_form,
    )


async def _said_wrong(
    conn: asyncpg.Connection,
    session_id: UUID,
    pattern_id: UUID,
    at: datetime,
    *,
    original_span: str = "I sent report",
    correction: str = "I sent the report",
    explanation: str = "특정 문서를 가리키므로 the 가 필요합니다.",
) -> UUID:
    """지정한 시각에 그 패턴의 오류를 1건 말했다 — 발화 + occurrence 한 벌. 발화 id를 준다."""
    utterance_id = await conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
        "values ($1, 'user', $2, $3, $4) returning id",
        session_id,
        original_span,
        next(_SEQ),
        at,
    )
    await conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, $3, $4, $5, 'medium', 0.9)",
        utterance_id,
        pattern_id,
        original_span,
        correction,
        explanation,
    )
    return utterance_id


# ① 기본 — 그 발화의 날짜 1건이 기록되고 두 개수가 실제 행 수와 같다 (AC13-1).
async def test_refresh_records_counts_for_the_utterance_local_date(
    db_conn: asyncpg.Connection,
) -> None:
    await _seed_user(db_conn)
    session_id = await _seed_session(db_conn)
    pattern_id = await _seed_pattern(db_conn, key="article_missing_before_singular_noun")
    utterance_id = await _said_wrong(
        db_conn, session_id, pattern_id, datetime(2026, 9, 9, 10, 0, tzinfo=KST)
    )

    await refresh_summary_for_utterance(db_conn, USER_ID, utterance_id)

    row = await db_conn.fetchrow(
        "select summary_date, timezone, occurrence_count, pattern_count "
        "from daily_error_summary where user_id = $1",
        USER_ID,
    )
    assert row is not None
    assert row["summary_date"] == date(2026, 9, 9)
    assert row["timezone"] == "Asia/Seoul"
    assert row["occurrence_count"] == 1
    assert row["pattern_count"] == 1


# ② AC13-2 — 한국 시각 자정 직후의 발화는 **그날** 요약에 들어간다. UTC 로 세면 하루 앞이다.
async def test_summary_date_follows_user_timezone_not_utc(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    session_id = await _seed_session(db_conn)
    pattern_id = await _seed_pattern(db_conn, key="article_missing_before_place_noun")
    # 2026-09-11 00:30 KST = 2026-09-10 15:30 UTC — UTC 날짜와 KST 날짜가 갈리는 시각이다.
    utterance_id = await _said_wrong(
        db_conn, session_id, pattern_id, datetime(2026, 9, 11, 0, 30, tzinfo=KST)
    )

    await refresh_summary_for_utterance(db_conn, USER_ID, utterance_id)

    dates = [
        record["summary_date"]
        for record in await db_conn.fetch(
            "select summary_date from daily_error_summary where user_id = $1", USER_ID
        )
    ]
    assert dates == [date(2026, 9, 11)]


# ③ AC13-3 — 두 번 계산해도 부풀지 않는다. 재분석이 이 함수를 다시 지난다.
async def test_refresh_is_idempotent(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    session_id = await _seed_session(db_conn)
    pattern_id = await _seed_pattern(db_conn, key="preposition_on_vs_in_for_month")
    utterance_id = await _said_wrong(
        db_conn, session_id, pattern_id, datetime(2026, 9, 9, 21, 0, tzinfo=KST)
    )

    await refresh_summary_for_utterance(db_conn, USER_ID, utterance_id)
    await refresh_summary_for_utterance(db_conn, USER_ID, utterance_id)

    rows = await db_conn.fetch(
        "select occurrence_count from daily_error_summary where user_id = $1", USER_ID
    )
    assert [row["occurrence_count"] for row in rows] == [1]


# ④ R13-2 — 패턴별 상세와 예시 문장. 정렬은 발생 수 내림차순이고 예시는 그날 가장 이른 발화다.
async def test_patterns_hold_details_sorted_by_occurrences(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    session_id = await _seed_session(db_conn)
    article = await _seed_pattern(
        db_conn, key="article_missing_before_singular_noun", target_form="the + 단수 명사"
    )
    tense = await _seed_pattern(
        db_conn, key="past_tense_in_work_update", category="verb_tense", target_form="동사 과거형"
    )
    utterance_id = await _said_wrong(
        db_conn,
        session_id,
        article,
        datetime(2026, 9, 9, 9, 0, tzinfo=KST),
        original_span="I sent report",
        correction="I sent the report",
        explanation="특정 문서를 가리키므로 the 가 필요합니다.",
    )
    await _said_wrong(
        db_conn,
        session_id,
        article,
        datetime(2026, 9, 9, 20, 0, tzinfo=KST),
        original_span="I opened ticket",
        correction="I opened the ticket",
    )
    await _said_wrong(
        db_conn,
        session_id,
        tense,
        datetime(2026, 9, 9, 21, 0, tzinfo=KST),
        original_span="Yesterday I work on API",
        correction="Yesterday I worked on the API",
        explanation="어제 일이므로 과거형을 씁니다.",
    )

    await refresh_summary_for_utterance(db_conn, USER_ID, utterance_id)

    summary = await load_daily_summary(
        db_conn, USER_ID, now=datetime(2026, 9, 9, 23, 0, tzinfo=KST)
    )
    assert summary.occurrence_count == 3
    assert summary.pattern_count == 2
    assert [item.pattern_key for item in summary.patterns] == [
        "article_missing_before_singular_noun",
        "past_tense_in_work_update",
    ]
    first = summary.patterns[0]
    assert first.category == "article"
    assert first.target_form == "the + 단수 명사"
    assert first.occurrences == 2
    # 예시는 그날 가장 이른 발화다 — 학습자가 하루를 되짚을 때 처음 틀린 자리가 기준이다.
    assert first.example.original_span == "I sent report"
    assert first.example.correction == "I sent the report"
    assert first.example.reason == "특정 문서를 가리키므로 the 가 필요합니다."


# ⑤ R13-7 — 요약 행이 없으면 「그날 학습이 없었다」다. 0건 요약과 같은 모양으로 뭉개지 않는다.
async def test_load_returns_zero_summary_when_no_row_exists(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)

    summary = await load_daily_summary(
        db_conn, USER_ID, now=datetime(2026, 9, 11, 8, 0, tzinfo=KST)
    )

    assert summary.summary_date == date(2026, 9, 11)
    assert summary.timezone == "Asia/Seoul"
    assert summary.occurrence_count == 0
    assert summary.pattern_count == 0
    assert summary.patterns == []
    assert summary.computed_at is None


# ⑥ 타임존의 정본이 없으면 조용히 UTC 로 떨어지지 않는다 — `load_chronic_metrics` 와 같은 판단.
async def test_load_raises_when_user_is_unknown(db_conn: asyncpg.Connection) -> None:
    with pytest.raises(LookupError):
        await load_daily_summary(db_conn, uuid4(), now=datetime(2026, 9, 11, 8, 0, tzinfo=KST))


# ⑦ naive datetime 을 받지 않는다 — 서버 오프셋만큼 날짜가 밀린다(`recordings.py` 와 같은 규약).
async def test_load_rejects_naive_now(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)

    with pytest.raises(ValueError):
        await load_daily_summary(db_conn, USER_ID, now=datetime(2026, 9, 11, 8, 0))


# ⑧ 발화가 사라졌으면(재분석 중 삭제) 아무 것도 쓰지 않고 조용히 지난다 — 저장 트랜잭션을
#    이 집계 때문에 실패시키지 않는다.
async def test_refresh_does_nothing_for_unknown_utterance(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)

    await refresh_summary_for_utterance(db_conn, USER_ID, uuid4())

    assert await db_conn.fetchval("select count(*) from daily_error_summary") == 0


# ⑨ 다른 날짜를 건드리지 않는다 — 갱신 범위는 그 발화의 날짜 1건이다(설계서 §4).
async def test_refresh_touches_only_the_utterance_date(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    session_id = await _seed_session(db_conn)
    pattern_id = await _seed_pattern(db_conn, key="word_order_in_question")
    older = await _said_wrong(
        db_conn, session_id, pattern_id, datetime(2026, 9, 8, 10, 0, tzinfo=KST)
    )
    newer = await _said_wrong(
        db_conn, session_id, pattern_id, datetime(2026, 9, 9, 10, 0, tzinfo=KST)
    )

    await refresh_summary_for_utterance(db_conn, USER_ID, older)
    await refresh_summary_for_utterance(db_conn, USER_ID, newer)

    rows = await db_conn.fetch(
        "select summary_date, occurrence_count from daily_error_summary "
        "where user_id = $1 order by summary_date",
        USER_ID,
    )
    assert [(row["summary_date"], row["occurrence_count"]) for row in rows] == [
        (date(2026, 9, 8), 1),
        (date(2026, 9, 9), 1),
    ]


# ⑩ 발생이 0건으로 줄면 요약도 0건이 된다 — 재분석으로 교정이 사라진 날이 그대로 남지 않는다.
async def test_refresh_records_zero_when_occurrences_are_gone(
    db_conn: asyncpg.Connection,
) -> None:
    await _seed_user(db_conn)
    session_id = await _seed_session(db_conn)
    pattern_id = await _seed_pattern(db_conn, key="verb_form_after_modal")
    utterance_id = await _said_wrong(
        db_conn, session_id, pattern_id, datetime(2026, 9, 9, 10, 0, tzinfo=KST)
    )
    await refresh_summary_for_utterance(db_conn, USER_ID, utterance_id)

    await db_conn.execute("delete from error_occurrences where utterance_id = $1", utterance_id)
    await refresh_summary_for_utterance(db_conn, USER_ID, utterance_id)

    summary = await load_daily_summary(
        db_conn, USER_ID, now=datetime(2026, 9, 9, 23, 0, tzinfo=KST)
    )
    assert summary.occurrence_count == 0
    assert summary.pattern_count == 0
    assert summary.patterns == []
    # 행 자체는 남는다 — 「분석이 돌고 0건」이므로 「학습이 없었다」와 다르다(R13-7).
    assert summary.computed_at is not None


# ── TASK-2 · PRD §14 — 일일 학습 완료 판정 ─────────────────────────────────────
#
# 「마쳤다」는 **시나리오가 붙은 세션이 정상 종료된 것**이다(R14-2). 드릴 교대 수를 조건에 넣지
# 않는다 — 미달의 주어가 학습자가 아니라 대화 모델이기 때문이고(캡틴 결정 10) 그 근거는
# `docs/design/2026-09-11-daily-completion-design.md` §3.1 이 소유한다.


async def _seed_scenario(conn: asyncpg.Connection) -> UUID:
    return await conn.fetchval(
        "insert into learning_scenarios (category, level, title, prompt_template) "
        "values ('daily_life', 'A2', 'Completion Test', 'chat with a colleague') returning id"
    )


async def _ended_session(
    conn: asyncpg.Connection,
    *,
    ended_at: datetime,
    status: str = "completed",
    scenario_id: UUID | None,
) -> UUID:
    """⛔ `started_at` 을 **끝난 날과 다른 날**로 박는다 — 그것이 앵커 단정의 판별력이다.

    기본값(`now()`)에 맡기면 시작·종료가 같은 날짜가 되어 `ended_at` 을 `started_at` 으로 바꾼
    변이가 테스트를 그대로 통과한다(2026-09-11 실측: 실제로 통과했다).
    """
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode, scenario_id, status, started_at, ended_at) "
        "values ($1, 'speaking', $2, $3, $4, $5) returning id",
        USER_ID,
        scenario_id,
        status,
        ended_at - timedelta(days=3),
        ended_at,
    )


# ⑪ AC14-1 — 시나리오가 붙은 세션이 정상 종료되면 그날은 완료다.
async def test_completed_scenario_session_marks_the_day_done(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    await _ended_session(
        db_conn, ended_at=datetime(2026, 9, 11, 21, 0, tzinfo=KST), scenario_id=scenario_id
    )

    completion = await load_daily_completion(
        db_conn, USER_ID, now=datetime(2026, 9, 11, 23, 0, tzinfo=KST)
    )

    assert completion.completed_today is True
    assert completion.completed_scenarios == 1
    assert completion.summary_date == date(2026, 9, 11)


# ⑫ AC14-3 — 실패로 끝난 세션은 완료로 세지 않는다.
async def test_failed_session_does_not_count(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    await _ended_session(
        db_conn,
        ended_at=datetime(2026, 9, 11, 21, 0, tzinfo=KST),
        status="failed",
        scenario_id=scenario_id,
    )

    completion = await load_daily_completion(
        db_conn, USER_ID, now=datetime(2026, 9, 11, 23, 0, tzinfo=KST)
    )

    assert completion.completed_today is False
    assert completion.completed_scenarios == 0


# ⑬ 시나리오가 없는 세션은 세지 않는다 — 요구사항이 「시나리오를 마치면」이다(R14-1).
async def test_session_without_scenario_does_not_count(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    await _ended_session(
        db_conn, ended_at=datetime(2026, 9, 11, 21, 0, tzinfo=KST), scenario_id=None
    )

    completion = await load_daily_completion(
        db_conn, USER_ID, now=datetime(2026, 9, 11, 23, 0, tzinfo=KST)
    )

    assert completion.completed_today is False


# ⑭ AC14-4 — 한국 시각 자정을 넘겨 끝난 세션은 «끝난 날»의 것으로 센다.
async def test_completion_is_counted_on_the_day_it_ended(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    # 2026-09-11 00:30 KST = 2026-09-10 15:30 UTC — UTC 날짜와 KST 날짜가 갈리는 시각이다.
    await _ended_session(
        db_conn, ended_at=datetime(2026, 9, 11, 0, 30, tzinfo=KST), scenario_id=scenario_id
    )

    on_the_day = await load_daily_completion(
        db_conn, USER_ID, now=datetime(2026, 9, 11, 9, 0, tzinfo=KST)
    )
    day_before = await load_daily_completion(
        db_conn, USER_ID, now=datetime(2026, 9, 10, 23, 0, tzinfo=KST)
    )

    assert on_the_day.completed_today is True
    assert day_before.completed_today is False, "UTC 날짜로 세면 하루 앞으로 밀린다"


# ⑮ R14-5 — 여러 개를 마쳐도 판정은 그대로이고 개수는 사실로 남는다.
async def test_multiple_completions_keep_the_verdict_and_count(
    db_conn: asyncpg.Connection,
) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    for hour in (10, 21):
        await _ended_session(
            db_conn,
            ended_at=datetime(2026, 9, 11, hour, 0, tzinfo=KST),
            scenario_id=scenario_id,
        )

    completion = await load_daily_completion(
        db_conn, USER_ID, now=datetime(2026, 9, 11, 23, 0, tzinfo=KST)
    )

    assert completion.completed_today is True
    assert completion.completed_scenarios == 2


# ⑯ 「오늘」의 규약은 요약과 같은 모듈이 소유한다 — 사용자 부재는 `LookupError`, naive 는 거부다.
async def test_completion_follows_the_same_today_rules(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)

    with pytest.raises(LookupError):
        await load_daily_completion(db_conn, uuid4(), now=datetime(2026, 9, 11, 8, 0, tzinfo=KST))
    with pytest.raises(ValueError):
        await load_daily_completion(db_conn, USER_ID, now=datetime(2026, 9, 11, 8, 0))


# ── TASK-107 · PRD §15 — 연속 학습일과 히스토리 ────────────────────────────────
#
# 「학습한 날」의 술어는 완료 판정과 **같다** — 두 곳에서 갈리면 화면의 연속일과 완료 문구가
# 서로 어긋난다(R15-1). 그래서 같은 모듈이 둘을 소유한다.


async def _completed_on(conn: asyncpg.Connection, scenario_id: UUID, *days: int) -> None:
    """2026-09-11 을 기준으로 `days` 만큼 «이전» 날짜에 완료 세션을 하나씩 심는다."""
    for offset in days:
        await _ended_session(
            conn,
            ended_at=datetime(2026, 9, 11, 21, 0, tzinfo=KST) - timedelta(days=offset),
            scenario_id=scenario_id,
        )


# ⑰ AC15-1 — 이틀 연속이면 현재 연속일이 2다.
async def test_two_consecutive_days_make_a_streak_of_two(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    await _completed_on(db_conn, scenario_id, 0, 1)

    streak = await load_streak(db_conn, USER_ID, now=datetime(2026, 9, 11, 23, 0, tzinfo=KST))

    assert streak.current == 2
    assert streak.longest == 2
    assert streak.today_done is True


# ⑱ AC15-2 — 마지막 학습일이 어제면 오늘 아직 안 했어도 연속이 «살아 있다».
async def test_yesterday_keeps_the_streak_alive(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    await _completed_on(db_conn, scenario_id, 1, 2)

    streak = await load_streak(db_conn, USER_ID, now=datetime(2026, 9, 11, 9, 0, tzinfo=KST))

    assert streak.current == 2, "「오늘 아직 안 했다」를 끊김으로 세면 0이 된다"
    assert streak.today_done is False


# ⑲ AC15-3 — 마지막 학습일이 그저께면 현재 연속일은 0이다(최장은 남는다).
async def test_the_day_before_yesterday_breaks_the_streak(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    await _completed_on(db_conn, scenario_id, 2, 3, 4)

    streak = await load_streak(db_conn, USER_ID, now=datetime(2026, 9, 11, 9, 0, tzinfo=KST))

    assert streak.current == 0
    assert streak.longest == 3


# ⑳ AC15-4 — 하루에 셋을 마쳐도 1일로 센다.
async def test_three_sessions_in_one_day_count_as_one_day(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    await _completed_on(db_conn, scenario_id, 0, 0, 0)

    streak = await load_streak(db_conn, USER_ID, now=datetime(2026, 9, 11, 23, 0, tzinfo=KST))

    assert streak.current == 1
    assert streak.longest == 1


# ㉑ 기록이 없으면 0이고 오류가 아니다 — 첫 사용자의 화면이 비는 것이 정상이다.
async def test_no_history_is_zero_not_an_error(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)

    streak = await load_streak(db_conn, USER_ID, now=datetime(2026, 9, 11, 9, 0, tzinfo=KST))

    assert streak.current == 0
    assert streak.longest == 0
    assert streak.today_done is False


# ㉒ AC15-5 — 히스토리는 날짜별로 「학습했는가」와 그날 오류 요약을 함께 준다.
async def test_history_pairs_learning_with_that_days_summary(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    session_id = await _seed_session(db_conn)
    pattern_id = await _seed_pattern(db_conn, key="article_missing_before_singular_noun")
    await _completed_on(db_conn, scenario_id, 1)
    # 어제 오류 1건을 분석해 요약을 만든다.
    utterance_id = await _said_wrong(
        db_conn, session_id, pattern_id, datetime(2026, 9, 10, 20, 0, tzinfo=KST)
    )
    await refresh_summary_for_utterance(db_conn, USER_ID, utterance_id)

    history = await load_history(
        db_conn, USER_ID, days=3, now=datetime(2026, 9, 11, 9, 0, tzinfo=KST)
    )

    assert [row.day for row in history] == [date(2026, 9, 11), date(2026, 9, 10), date(2026, 9, 9)]
    today, yesterday, before = history
    assert today.learned is False and today.analyzed is False
    assert yesterday.learned is True and yesterday.completed_scenarios == 1
    assert yesterday.analyzed is True and yesterday.occurrence_count == 1
    # ⛔ 학습은 했는데 요약이 없는 날이 실재한다(012 이전) — 두 값을 **갈라** 준다.
    assert before.learned is False and before.analyzed is False


# ㉓ 「학습은 했는데 요약이 없다」와 「학습이 없었다」가 구별된다 — 설계서 §6 의 미결 ⑴.
async def test_history_separates_learned_from_analyzed(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    await _completed_on(db_conn, scenario_id, 1)

    history = await load_history(
        db_conn, USER_ID, days=2, now=datetime(2026, 9, 11, 9, 0, tzinfo=KST)
    )

    yesterday = history[1]
    assert yesterday.learned is True, "완료 세션이 있으므로 학습한 날이다"
    assert yesterday.analyzed is False, "요약 행이 없으므로 분석 기록은 없다"


# ㉔ 최장 연속일이 **마지막 구간이 아닐 때**를 잰다 — 그 표본이 없으면 `longest` 를 마지막 구간
#    길이로 바꾼 변이가 통과한다(2026-09-11 실측: 실제로 통과했다).
async def test_longest_streak_can_be_an_earlier_island(db_conn: asyncpg.Connection) -> None:
    await _seed_user(db_conn)
    scenario_id = await _seed_scenario(db_conn)
    # 10·9·8일 전에 3일 연속, 그리고 2일 전에 하루.
    await _completed_on(db_conn, scenario_id, 10, 9, 8, 2)

    streak = await load_streak(db_conn, USER_ID, now=datetime(2026, 9, 11, 9, 0, tzinfo=KST))

    assert streak.longest == 3, "마지막 구간(1일)이 아니라 앞 구간이 최장이다"
    assert streak.current == 0, "마지막 학습일이 그저께보다 오래됐다"
