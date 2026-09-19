"""주간 리포트의 주 경계와 조건부 트리거 (`TASK-26.2`).

설계: `docs/design/2026-09-14-weekly-report-design.md` §4·§6.

⚠️ **`db_conn`(롤백 트랜잭션)만 쓴다** — 커밋된 행을 남기지 않는다.
⛔ **주 경계를 상수로 고정하지 않는다** — 이 파일이 도는 날짜에 따라 값이 달라지므로 고정하면 하루
뒤 낡는다(`H-O` 의 부류). 대신 **성질**을 잰다: 월요일인가 · 이번 주보다 한 주 앞인가 · 타임존이
그 값을 가르는가.
"""

from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

import asyncpg
import pytest

from app.models.weekly_report import WeeklyValidationError, parse_weekly_insights
from app.services.jobs import JOB_TYPE_SUMMARIZE_WEEK, enqueue_summarize_week
from app.services.weekly_report import (
    TopPattern,
    WeekFacts,
    build_weekly_prompt,
    last_week_start,
    load_week_facts,
)


def _facts() -> WeekFacts:
    """프롬프트 단정용 사실 한 벌 — DB 를 거치지 않는다."""
    return WeekFacts(
        week_start=date(2026, 9, 7),
        session_count=4,
        occurrence_count=7,
        pattern_count=2,
        top_patterns=[
            TopPattern("article", "article_missing", "the report", 3),
            TopPattern("verb_tense", "tense_past", "worked", 4),
        ],
    )


async def _insert_user(conn: asyncpg.Connection, timezone: str) -> UUID:
    return await conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ('Weekly Test', $1, 'A2') returning id",
        timezone,
    )


async def _new_session(conn: asyncpg.Connection, user_id: UUID) -> UUID:
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        user_id,
    )


@pytest.mark.asyncio
async def test_last_week_start_is_a_monday_one_week_back(db_conn: asyncpg.Connection) -> None:
    """지난 주 월요일이다 — 사용자 타임존으로 구한다.

    ⛔ `current_date` 를 쓰지 않는다(R13-3 · 전역 규약). UTC 자정~09:00 구간에 그 값이 KST 날짜보다
    하루 이르므로, 그 구간에 주가 바뀌면 두 방식이 **다른 월요일**을 낸다.
    ⚠️ 값을 고정하지 않고 **성질**을 잰다: 월요일이고, 사용자 타임존의 「오늘」로부터 7~13일 전이다
    (오늘이 월요일이면 7일, 일요일이면 13일이다).
    """
    user_id = await _insert_user(db_conn, "Asia/Seoul")

    got = await last_week_start(db_conn, user_id)

    assert got.isoweekday() == 1, f"{got} 가 월요일이 아니다"
    today_kst = await db_conn.fetchval("select (now() at time zone 'Asia/Seoul')::date")
    assert 7 <= (today_kst - got).days <= 13


@pytest.mark.asyncio
async def test_the_timezone_can_move_the_week(db_conn: asyncpg.Connection) -> None:
    """타임존이 그 값을 가른다 — 같은 순간에 다른 주를 가리킬 수 있다.

    ⛔ **이 단정이 「타임존을 실제로 읽는가」의 판별력이다.** `now()` 를 그냥 쓰면(타임존을
    무시하면)
    두 사용자가 **언제나 같은 값**을 받아 이 성질이 사라진다.
    ⚠️ 어느 쪽이 앞인지는 이 단정이 도는 시각에 달렸으므로 **차이가 0 또는 7일**임만 잰다 —
    UTC+14 와 UTC-11 은 하루 차이까지 벌어질 수 있고 그 하루가 주 경계를 넘으면 7일이 된다.
    """
    east = await _insert_user(db_conn, "Pacific/Kiritimati")  # UTC+14
    west = await _insert_user(db_conn, "Pacific/Niue")  # UTC-11

    gap = (await last_week_start(db_conn, east)) - (await last_week_start(db_conn, west))

    assert gap.days in (0, 7), f"두 타임존의 주 시작 차이가 {gap.days}일이다"


@pytest.mark.asyncio
async def test_the_job_is_enqueued_when_last_week_has_no_row(db_conn: asyncpg.Connection) -> None:
    """지난 주 행이 없으면 job 이 걸린다 (결정 91)."""
    user_id = await _insert_user(db_conn, "Asia/Seoul")
    session_id = await _new_session(db_conn, user_id)

    job_id = await enqueue_summarize_week(db_conn, session_id)

    assert job_id is not None
    assert (
        await db_conn.fetchval("select job_type from analysis_jobs where id = $1", job_id)
        == JOB_TYPE_SUMMARIZE_WEEK
    )
    # 대상이 세션이다 — 「어떤 주」는 워커가 다시 구한다(설계서 §6).
    assert (
        await db_conn.fetchval("select session_id from analysis_jobs where id = $1", job_id)
        == session_id
    )


@pytest.mark.asyncio
async def test_the_job_is_not_enqueued_when_last_week_already_has_a_row(
    db_conn: asyncpg.Connection,
) -> None:
    """⛔ 결정 91 의 「지난 주 리포트가 없으면」이 이 단정에 걸린다.

    ⚠️ 조건을 **한 문장 안에** 두는 이유: 조회와 삽입을 나누면 그 사이에 다른 세션 종료가 같은 job
    을 넣는다.
    """
    user_id = await _insert_user(db_conn, "Asia/Seoul")
    session_id = await _new_session(db_conn, user_id)
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start, timezone) values ($1, $2, 'Asia/Seoul')",
        user_id,
        await last_week_start(db_conn, user_id),
    )

    assert await enqueue_summarize_week(db_conn, session_id) is None
    assert await db_conn.fetchval("select count(*) from analysis_jobs") == 0


@pytest.mark.asyncio
async def test_a_row_for_another_week_does_not_block_the_job(db_conn: asyncpg.Connection) -> None:
    """⛔ 「지난 주」가 아닌 주의 행은 가드에 걸리지 않는다.

    이 단정이 없으면 `not exists` 가 **주를 보지 않고** 「그 사용자의 행이 하나라도 있으면
    넘긴다」로 쓰여도 통과한다 — 그러면 둘째 주부터 리포트가 영원히 만들어지지 않는다.
    """
    user_id = await _insert_user(db_conn, "Asia/Seoul")
    session_id = await _new_session(db_conn, user_id)
    last_week = await last_week_start(db_conn, user_id)
    # ⚠️ 두 함정이 겹친 자리다: `date - interval` 은 `timestamp` 를 내고, `$2 - 7` 은 Postgres 가
    # `$2` 를 **정수로 추론**하게 만든다. 그래서 `$2::date - 7` 로 타입을 못박는다.
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start, timezone) "
        "values ($1, $2::date - 7, 'Asia/Seoul')",
        user_id,
        last_week,
    )

    assert await enqueue_summarize_week(db_conn, session_id) is not None


@pytest.mark.asyncio
async def test_another_users_row_does_not_block_the_job(db_conn: asyncpg.Connection) -> None:
    """⛔ 남의 리포트가 내 job 을 막지 않는다 — 가드가 `user_id` 를 함께 봐야 한다."""
    mine = await _insert_user(db_conn, "Asia/Seoul")
    other = await _insert_user(db_conn, "Asia/Seoul")
    session_id = await _new_session(db_conn, mine)
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start, timezone) values ($1, $2, 'Asia/Seoul')",
        other,
        await last_week_start(db_conn, other),
    )

    assert await enqueue_summarize_week(db_conn, session_id) is not None


# ─── 사실 모으기 (`TASK-26.3` · 설계서 §3 의 `metrics`) ───
#
# ⚠️ 발화 시각을 **사용자 타임존의 날짜**로 접어서 주에 넣는다 — 그 접기가 하루 밀리면 지난 주와
# 이번 주가 섞인다. 아래 첫 단정이 그 경계를 양쪽에서 찌른다.
async def _pattern(conn: asyncpg.Connection, user_id: UUID, key: str) -> UUID:
    return await conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'verb_tense', $2, 'worked') returning id",
        user_id,
        key,
    )


async def _occurrence(
    conn: asyncpg.Connection, user_id: UUID, pattern_id: UUID, *, day: date, seq: int
) -> None:
    """그 날짜(사용자 타임존 정오)에 발화 하나와 그 발생 하나를 심는다."""
    session_id = await conn.fetchval(
        "insert into learning_sessions (user_id, mode, started_at) "
        "values ($1, 'speaking', ($2::date + time '12:00') at time zone 'Asia/Seoul') returning id",
        user_id,
        day,
    )
    utterance_id = await conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
        "values ($1, 'user', 'Yesterday I work on API.', $2, "
        "($3::date + time '12:00') at time zone 'Asia/Seoul') returning id",
        session_id,
        seq,
        day,
    )
    await conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, 'I work', 'I worked', '과거 시제', 'medium', 0.9)",
        utterance_id,
        pattern_id,
    )


@pytest.mark.asyncio
async def test_week_facts_exclude_days_outside_the_week(db_conn: asyncpg.Connection) -> None:
    """⛔ 경계가 이 단정의 축이다 — 양쪽 하루를 찔러 본다.

    주 밖의 발생이 새면 「그 주에 무엇을 틀렸나」가 거짓이 되고, 그 사실 위에 서는 모델 판단까지
    함께 틀린다.
    """
    user_id = await _insert_user(db_conn, "Asia/Seoul")
    week = await last_week_start(db_conn, user_id)
    pattern_id = await _pattern(db_conn, user_id, "tense_past_simple")

    await _occurrence(db_conn, user_id, pattern_id, day=week - timedelta(days=1), seq=1)
    await _occurrence(db_conn, user_id, pattern_id, day=week, seq=1)
    await _occurrence(db_conn, user_id, pattern_id, day=week + timedelta(days=6), seq=1)
    await _occurrence(db_conn, user_id, pattern_id, day=week + timedelta(days=7), seq=1)

    facts = await load_week_facts(db_conn, user_id, week)

    # 월요일과 일요일은 들어오고 그 앞·뒤 하루는 빠진다.
    assert facts.occurrence_count == 2
    assert facts.pattern_count == 1
    assert facts.session_count == 2


@pytest.mark.asyncio
async def test_week_facts_rank_patterns_by_occurrences_then_key(
    db_conn: asyncpg.Connection,
) -> None:
    """상위 오류가 발생 수 내림차순이고 동수는 `pattern_key` 로 갈린다.

    ⚠️ 동수 가름이 없으면 순서가 실행마다 흔들려 화면이 이유 없이 달라진다 — 일일 요약의 `ranked`
    CTE 가 같은 규약을 쓴다.
    """
    user_id = await _insert_user(db_conn, "Asia/Seoul")
    week = await last_week_start(db_conn, user_id)
    many = await _pattern(db_conn, user_id, "b_article_missing")
    tie_a = await _pattern(db_conn, user_id, "a_tense_past")
    tie_z = await _pattern(db_conn, user_id, "z_preposition")

    for seq, day in enumerate((week, week + timedelta(days=1)), start=1):
        await _occurrence(db_conn, user_id, many, day=day, seq=seq)
    await _occurrence(db_conn, user_id, many, day=week + timedelta(days=2), seq=1)
    await _occurrence(db_conn, user_id, tie_z, day=week + timedelta(days=3), seq=1)
    await _occurrence(db_conn, user_id, tie_a, day=week + timedelta(days=4), seq=1)

    facts = await load_week_facts(db_conn, user_id, week)

    assert [(p.pattern_key, p.occurrences) for p in facts.top_patterns] == [
        ("b_article_missing", 3),
        ("a_tense_past", 1),
        ("z_preposition", 1),
    ]


@pytest.mark.asyncio
async def test_week_facts_are_empty_for_a_quiet_week(db_conn: asyncpg.Connection) -> None:
    """⛔ 「0건」과 「아직 계산 안 됨」은 다르다 — 이 함수는 **0건을 값으로** 준다."""
    user_id = await _insert_user(db_conn, "Asia/Seoul")
    week = await last_week_start(db_conn, user_id)

    facts = await load_week_facts(db_conn, user_id, week)

    assert (facts.occurrence_count, facts.pattern_count, facts.session_count) == (0, 0, 0)
    assert facts.top_patterns == []


@pytest.mark.asyncio
async def test_week_facts_do_not_leak_another_users_errors(db_conn: asyncpg.Connection) -> None:
    """⛔ 남의 오류가 내 리포트에 새지 않는다 — 조회가 `user_id` 를 함께 봐야 한다."""
    mine = await _insert_user(db_conn, "Asia/Seoul")
    other = await _insert_user(db_conn, "Asia/Seoul")
    week = await last_week_start(db_conn, mine)
    theirs = await _pattern(db_conn, other, "tense_past_simple")
    await _occurrence(db_conn, other, theirs, day=week, seq=1)

    facts = await load_week_facts(db_conn, mine, week)

    assert (facts.occurrence_count, facts.session_count) == (0, 0)


# ─── 프롬프트와 파서 (`TASK-26.4` · 설계서 §3 의 `insights`) ───
def test_prompt_requires_korean_and_keeps_quotes_in_english() -> None:
    """문구는 한국어이고 인용은 영어 원문이다 — 결정 89 가 총평에서 정한 규약과 같다."""
    prompt = build_weekly_prompt(facts=_facts(), max_points=3)

    assert "한국어" in prompt
    assert "원문" in prompt


def test_prompt_forbids_scores_in_two_axes() -> None:
    """⛔ **두 축으로 잰다** — 금지 문장이 있는가, 그리고 출력 규격에 그 키가 «없는가».

    ⚠️ `TASK-62` 가 이 자리에서 틀린 축을 쟀다: 「낱말의 부재」로만 재면 프롬프트가 점수를 **금지**
    하는 문장을 넣은 것까지 위반으로 읽힌다. 그래서 재는 것을 갈랐다.
    """
    prompt = build_weekly_prompt(facts=_facts(), max_points=3)

    # ① 금지가 문면에 있다.
    assert "점수" in prompt
    # ② 출력 규격의 키 목록에 점수·등급이 없다 — 규격 절만 떼어 본다.
    spec = prompt.split("[출력]", 1)[1]
    for forbidden in ('"score"', '"grade"', '"level_score"', '"rating"'):
        assert forbidden not in spec, f"출력 규격에 {forbidden} 가 있다"


def test_prompt_carries_the_facts_the_model_must_judge() -> None:
    """사실이 프롬프트에 실린다 — 모델이 판단할 근거다(R11-8).

    ⛔ 이 단정이 없으면 「프롬프트를 만들었지만 사실을 넣지 않은」 구현이 통과하고, 그러면 모델이
    아무 근거 없이 개선 여부를 지어낸다.
    """
    prompt = build_weekly_prompt(facts=_facts(), max_points=3)

    assert "article_missing" in prompt
    assert "3" in prompt


def test_parse_rejects_unknown_keys() -> None:
    """정의되지 않은 키를 거부한다 — 판정이 항목 안으로 들어오는 길을 막는다."""
    with pytest.raises(WeeklyValidationError):
        parse_weekly_insights('{"improving": [], "next_scenarios": [], "score": 80}', max_points=3)


def test_parse_rejects_a_top_level_that_is_not_an_object() -> None:
    """⛔ 「JSON 이 아니다」와 **다른 사유**로 거부한다 (`TASK-226`).

    세 파서가 공용 `loaded_object` 로 접힌 뒤, 이 갈래를 덮는 단정이 하나도 없다는 것이 변이로
    드러났다 — 사유가 원인을 잘못 지목하면 조사하는 사람이 프롬프트를 먼저 의심한다.
    """
    with pytest.raises(WeeklyValidationError, match="최상위"):
        parse_weekly_insights("[1, 2]", max_points=3)


def test_parse_caps_the_lists() -> None:
    """상한을 넘기면 거부한다 — 프롬프트 문면과 같은 수를 본다."""
    with pytest.raises(WeeklyValidationError):
        parse_weekly_insights(
            '{"improving": ["a", "b", "c", "d"], "next_scenarios": []}', max_points=3
        )
