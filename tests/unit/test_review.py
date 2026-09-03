"""복습 상태 재계산 — 설계서 §4.1 + 계획서 「복습 상태 재계산」 절.

두 층으로 나눠 본다. **앞쪽은 DB 없는 순수 함수**(`fold_stages`)로 예정일 경계를 전부 덮고,
뒤쪽은 `db_conn`(롤백되는 한 트랜잭션)으로 반영 결과를 본다 — `recompute`는 자기 트랜잭션을
열지 않고 호출자의 트랜잭션에서 도는 것이 계약이라 커밋 경계를 흉내낼 필요가 없다.

**발화 시각을 명시해 넣는다.** 단계 전이가 `now()`가 아니라 발화 시각을 기준으로 하는 것이
이 모듈의 멱등성 근거라서, 시각을 테스트가 통제하지 않으면 그 성질을 단정할 수 없다.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
from uuid import UUID

import asyncpg
import pytest

from app.models.analysis import PatternAttempt
from app.services.review import (
    FINAL_STAGE,
    STAGE_DAYS,
    fold_stages,
    load_due_reviews,
    recompute,
    recompute_all,
    store_attempts,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
PATTERN_KEY = "article_missing_before_place_noun"
CONTEXT = "go to gym"
# KST 정오라 어느 타임존으로 읽어도 달력 날짜가 갈리지 않는다 — 이 파일은 간격만 보고
# 달력 날짜는 보지 않는다(그 경계는 test_chronic.py가 소유한다).
T0 = datetime.fromisoformat("2026-09-01T12:00:00+09:00")


def _days(count: int) -> timedelta:
    return timedelta(days=count)


# ── 순수 함수: 예정일 접기 ────────────────────────────────────────────────────


# ① 틀린 적이 없으면 복습할 것이 없다
def test_a_pattern_that_was_never_wrong_has_nothing_to_review():
    state = fold_stages(None, [], CONTEXT)

    assert state.stage == 1
    assert state.completed is False
    assert state.anchor is None
    assert state.next_review_at is None


# ② 틀린 직후는 1일 뒤다
def test_a_relapse_schedules_the_first_stage_one_day_later():
    state = fold_stages(T0, [], CONTEXT)

    assert state.stage == 1
    assert state.anchor == T0
    assert state.next_review_at == T0 + _days(1)


# ③ 예정일에 맞히면 다음 단계로 간다. anchor는 그 정답의 발화 시각이다
def test_a_correct_on_the_due_date_advances_to_the_next_stage():
    said_at = T0 + _days(1)

    state = fold_stages(T0, [said_at], CONTEXT)

    assert state.stage == 2
    assert state.anchor == said_at
    assert state.next_review_at == said_at + _days(3)


# ④ **회귀 방지** — 예정일 **전**의 정답은 단계를 올리지 않는다. 이것이 없으면 같은 세션에서
#    세 번 맞히는 것으로 1·3·7일을 한 번도 경과하지 않고 완주해 간격 반복이 무의미해진다.
def test_a_correct_before_the_due_date_does_not_advance_anything():
    early = [T0 + timedelta(minutes=5), T0 + timedelta(minutes=10), T0 + timedelta(hours=20)]

    state = fold_stages(T0, early, CONTEXT)

    assert state.stage == 1
    assert state.completed is False
    assert state.next_review_at == T0 + _days(1), "예정일이 움직였다 — 간격 조건이 빠졌다"


# ⑤ 완주까지는 1 + 3 + 7 = 11일이 실제로 경과해야 한다
def test_completing_all_three_stages_takes_the_documented_intervals():
    first = T0 + _days(1)
    second = first + _days(3)
    third = second + _days(7)

    state = fold_stages(T0, [first, second, third], CONTEXT)

    assert state.completed is True
    assert state.stage == FINAL_STAGE
    assert state.anchor == third
    assert state.next_review_at is None
    assert third - T0 == _days(sum(STAGE_DAYS)) == _days(11)


# ⑥ 예정일 전 정답이 섞여 있어도 예정일을 넘긴 것만 센다
def test_early_corrects_mixed_with_on_time_ones_are_ignored():
    on_time = T0 + _days(1)
    too_early = on_time + _days(1)  # 2단계 예정일(+3일)보다 이르다
    next_on_time = on_time + _days(3)

    state = fold_stages(T0, [on_time, too_early, next_on_time], CONTEXT)

    assert state.stage == 3
    assert state.anchor == next_on_time
    assert state.next_review_at == next_on_time + _days(7)


# ⑦ 예정일을 **한참** 지나 맞힌 것도 통과다. "너무 늦은 복습"의 상한을 발명하지 않는다
#    (설계서 §3.2 — 임계값을 우리가 정하지 않는다). 늦게 맞히는 것은 더 어려운 조건이라
#    그 정답이 약한 증거일 이유도 없다.
def test_a_very_late_correct_still_counts():
    very_late = T0 + _days(30)

    state = fold_stages(T0, [very_late], CONTEXT)

    assert state.stage == 2
    assert state.next_review_at == very_late + _days(3)


# ── DB 반영 ──────────────────────────────────────────────────────────────────

_SEQ = iter(range(1, 10_000))


async def _seed(conn: asyncpg.Connection) -> tuple[UUID, UUID]:
    """user → session → pattern 한 벌. 발화는 테스트가 시각을 정해 따로 넣는다."""
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'Review Test', 'Asia/Seoul', 'A2')",
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


async def _utterance(conn: asyncpg.Connection, session_id: UUID, at: datetime) -> UUID:
    return await conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
        "values ($1, 'user', 'I go to gym.', $2, $3) returning id",
        session_id,
        next(_SEQ),
        at,
    )


async def _occurrence(conn: asyncpg.Connection, utterance_id: UUID, pattern_id: UUID) -> None:
    await conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, $3, 'go to the gym', '정관사가 필요합니다.', 'medium', 0.9)",
        utterance_id,
        pattern_id,
        CONTEXT,
    )


async def _attempt(
    conn: asyncpg.Connection, utterance_id: UUID, pattern_id: UUID, outcome: str
) -> None:
    await conn.execute(
        "insert into pattern_attempts (pattern_id, utterance_id, outcome) values ($1, $2, $3)",
        pattern_id,
        utterance_id,
        outcome,
    )


async def _review_on_time(
    conn: asyncpg.Connection, session_id: UUID, pattern_id: UUID, at: datetime
) -> datetime:
    """예정일마다 정확히 맞혀 3단계를 완주시킨다. 마지막 정답의 발화 시각을 돌려준다."""
    for days in STAGE_DAYS:
        at = at + _days(days)
        await _attempt(conn, await _utterance(conn, session_id, at), pattern_id, "correct")
    return at


async def _pattern_row(conn: asyncpg.Connection, pattern_id: UUID) -> asyncpg.Record:
    row = await conn.fetchrow(
        "select next_review_at, mastery_score from error_patterns where id = $1", pattern_id
    )
    assert row is not None
    return row


async def _task_rows(conn: asyncpg.Connection, pattern_id: UUID) -> list[asyncpg.Record]:
    return await conn.fetch(
        "select review_stage, status, due_at, scenario_context from review_tasks "
        "where pattern_id = $1 order by review_stage",
        pattern_id,
    )


def _stages(rows: list[asyncpg.Record]) -> list[tuple[int, str]]:
    return [(row["review_stage"], row["status"]) for row in rows]


# ⑧ 처음 틀린 패턴이 복습 목록에 들어간다 — 이 값이 있어야 "오늘 복습할 목록"이 0행을 벗어난다
@pytest.mark.asyncio
async def test_recompute_schedules_a_fresh_error(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)

    state = await recompute(db_conn, pattern_id)

    assert state.next_review_at == T0 + _days(1)
    row = await _pattern_row(db_conn, pattern_id)
    assert row["next_review_at"] == T0 + _days(1)
    assert row["mastery_score"] == 0
    tasks = await _task_rows(db_conn, pattern_id)
    assert _stages(tasks) == [(1, "pending")]
    assert tasks[0]["due_at"] == T0 + _days(1)


# ⑨ 예정일에 맞히면 3일 뒤로 넘어간다 (DB 반영까지)
@pytest.mark.asyncio
async def test_recompute_advances_on_an_on_time_correct(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    due = T0 + _days(1)
    await _attempt(db_conn, await _utterance(db_conn, session_id, due), pattern_id, "correct")

    state = await recompute(db_conn, pattern_id)

    assert state.stage == 2
    assert (await _pattern_row(db_conn, pattern_id))["next_review_at"] == due + _days(3)
    assert _stages(await _task_rows(db_conn, pattern_id)) == [(2, "pending")]


# ⑩ 완주 — 목록에서 빠지고 mastery_score가 그 상태를 기록한다 (§4.1)
@pytest.mark.asyncio
async def test_recompute_marks_a_completed_review(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    await _review_on_time(db_conn, session_id, pattern_id, T0)

    state = await recompute(db_conn, pattern_id)

    assert state.completed is True
    row = await _pattern_row(db_conn, pattern_id)
    assert row["next_review_at"] is None
    assert row["mastery_score"] == 100
    assert _stages(await _task_rows(db_conn, pattern_id)) == [(FINAL_STAGE, "done")]


# ⑪ 재발하면 1단계로 되돌아가고 상위 단계 행이 남지 않는다 (캡틴 결정 2026-09-03)
@pytest.mark.asyncio
async def test_a_relapse_resets_to_stage_one_and_leaves_no_higher_row(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    completed_at = await _review_on_time(db_conn, session_id, pattern_id, T0)
    await recompute(db_conn, pattern_id)  # 완주 상태를 만든다

    relapse_at = completed_at + _days(5)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, relapse_at), pattern_id)
    state = await recompute(db_conn, pattern_id)

    assert state.stage == 1
    assert state.next_review_at == relapse_at + _days(1)
    assert (await _pattern_row(db_conn, pattern_id))["mastery_score"] == 0
    assert _stages(await _task_rows(db_conn, pattern_id)) == [(1, "pending")]


# ⑫ incorrect 판정도 재발이다 — occurrence 없이 attempts에만 적힌 경우에도 되돌린다
@pytest.mark.asyncio
async def test_an_incorrect_retry_counts_as_a_relapse(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    await _attempt(
        db_conn, await _utterance(db_conn, session_id, T0 + _days(1)), pattern_id, "correct"
    )
    fail_at = T0 + _days(2)
    await _attempt(db_conn, await _utterance(db_conn, session_id, fail_at), pattern_id, "incorrect")

    state = await recompute(db_conn, pattern_id)

    assert state.stage == 1
    assert state.next_review_at == fail_at + _days(1)


# ⑬ unclear는 단계를 움직이지 않는다 — 판정 불가를 진전으로도 후퇴로도 세지 않는다
@pytest.mark.asyncio
async def test_an_unclear_retry_moves_nothing(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    await _attempt(
        db_conn, await _utterance(db_conn, session_id, T0 + _days(1)), pattern_id, "unclear"
    )

    state = await recompute(db_conn, pattern_id)

    assert state.stage == 1
    assert state.next_review_at == T0 + _days(1)


# ⑭ **멱등** — 이 모듈의 존재 이유다. job은 재시도된다
@pytest.mark.asyncio
async def test_recompute_is_idempotent(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    await _attempt(
        db_conn, await _utterance(db_conn, session_id, T0 + _days(1)), pattern_id, "correct"
    )

    first = await recompute(db_conn, pattern_id)
    first_tasks = await _task_rows(db_conn, pattern_id)
    second = await recompute(db_conn, pattern_id)
    second_tasks = await _task_rows(db_conn, pattern_id)

    assert first == second
    assert [dict(row) for row in first_tasks] == [dict(row) for row in second_tasks]
    assert len(second_tasks) == 1


# ⑮ 근거가 사라진 패턴은 복습 목록에서도 빠진다 (재분석으로 occurrence가 전부 지워진 경우)
@pytest.mark.asyncio
async def test_a_pattern_without_evidence_leaves_the_due_list(db_conn: asyncpg.Connection):
    _, pattern_id = await _seed(db_conn)

    state = await recompute(db_conn, pattern_id)

    assert state.next_review_at is None
    assert state.anchor is None
    assert await _task_rows(db_conn, pattern_id) == []


# ⑯ scenario_context는 실제 데이터다 — 슬라이스 1은 무엇도 생성하지 않는다(§3.2)
@pytest.mark.asyncio
async def test_scenario_context_comes_from_the_latest_occurrence(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)

    await recompute(db_conn, pattern_id)

    assert (await _task_rows(db_conn, pattern_id))[0]["scenario_context"] == CONTEXT


# ⑰ store_attempts — replace 이고, 재계산 대상 패턴을 돌려준다
@pytest.mark.asyncio
async def test_store_attempts_replaces_and_reports_touched_patterns(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    utterance_id = await _utterance(db_conn, session_id, T0)

    touched = await store_attempts(
        db_conn, utterance_id, USER_ID, [PatternAttempt(pattern_key=PATTERN_KEY, outcome="correct")]
    )
    assert touched == {pattern_id}

    # 재분석: 같은 발화를 다시 저장해도 행이 늘지 않는다 (AS10)
    touched_again = await store_attempts(
        db_conn,
        utterance_id,
        USER_ID,
        [PatternAttempt(pattern_key=PATTERN_KEY, outcome="incorrect")],
    )
    assert touched_again == {pattern_id}
    rows = await db_conn.fetch(
        "select outcome from pattern_attempts where utterance_id = $1", utterance_id
    )
    assert [row["outcome"] for row in rows] == ["incorrect"]


# ⑱ 사라진 패턴을 가리키는 판정은 조용히 버려진다 — 분석 전체를 실패시키지 않는다
@pytest.mark.asyncio
async def test_store_attempts_skips_a_pattern_key_that_no_longer_exists(
    db_conn: asyncpg.Connection,
):
    session_id, _ = await _seed(db_conn)
    utterance_id = await _utterance(db_conn, session_id, T0)

    touched = await store_attempts(
        db_conn,
        utterance_id,
        USER_ID,
        [PatternAttempt(pattern_key="vanished_key", outcome="correct")],
    )

    assert touched == set()
    assert await db_conn.fetchval("select count(*) from pattern_attempts") == 0


# ── 무보호였던 하중 지점 2개 (2026-09-04 코드 리뷰 MEDIUM-4·MEDIUM-5) ─────────────


# ⑲ `_HISTORY_SQL`의 `array_agg(... order by ...)`가 없으면 이 테스트가 깨진다.
#    `fold_stages`의 전제조건은 **오름차순**이고, 그것이 깨지면 예외도 실패도 없이
#    단계만 조용히 틀린다. 삽입 순서를 시각 역순으로 만들어 정렬에 의존시킨다.
@pytest.mark.asyncio
async def test_recompute_orders_the_corrects_by_utterance_time_not_insert_order(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    later = T0 + _days(4)  # 2단계 예정일
    earlier = T0 + _days(1)  # 1단계 예정일
    # **나중 것을 먼저 삽입한다** — 정렬이 없으면 fold가 이 순서를 그대로 본다
    await _attempt(db_conn, await _utterance(db_conn, session_id, later), pattern_id, "correct")
    await _attempt(db_conn, await _utterance(db_conn, session_id, earlier), pattern_id, "correct")

    state = await recompute(db_conn, pattern_id)

    # 오름차순이면 T0+1d가 1단계를, T0+4d가 2단계를 통과해 3단계에 이른다.
    # 삽입 순서대로 보면 T0+4d만 통과하고 T0+1d는 예정일 전이라 버려져 2단계에 멈춘다.
    assert state.stage == 3, "정렬이 빠졌다 — fold가 삽입 순서를 봤다"
    assert state.anchor == later
    assert state.next_review_at == later + _days(7)


# ⑳ 같은 발화에 오류와 정답이 함께 달린 **모순된 판정**에서 단계가 오르지 않는다.
#    실물 모델이 한 발화에 finding과 attempt를 함께 내는 것이 2026-09-04 실물 왕복에서
#    관측됐으므로 가상의 경계가 아니다.
#    ⚠️ 이 동작을 지키는 것은 `_HISTORY_SQL`의 strict `>`가 아니라 **`fold_stages`의 간격
#    조건**이다 — `>`를 `>=`로 바꿔도 이 테스트는 통과한다(2026-09-04 실측). 재발과 같은
#    순간의 정답은 anchor와 시각이 같아 1단계 예정일(+1일) 전이므로 어차피 건너뛴다.
#    그래서 이 테스트는 **결과**를 못 박고, 어느 줄이 그것을 지키는지에 의존하지 않는다.
@pytest.mark.asyncio
async def test_a_correct_on_the_very_utterance_that_relapsed_does_not_advance(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    relapsed = await _utterance(db_conn, session_id, T0)
    await _occurrence(db_conn, relapsed, pattern_id)
    # 같은 발화에 correct 판정도 달린다 (모델이 findings와 attempts에 함께 낸 경우)
    await _attempt(db_conn, relapsed, pattern_id, "correct")

    state = await recompute(db_conn, pattern_id)

    assert state.stage == 1, "재발과 같은 순간의 정답이 단계를 올렸다"
    assert state.next_review_at == T0 + _days(1)


# ── "오늘 복습할 목록" 읽기 + 기존 패턴 백필 (2026-09-04 리뷰 MEDIUM-6 · 계획 검토) ──


# ㉑ §4.1의 목록 쿼리 — 예정일이 지난 것만, 가장 밀린 것부터.
@pytest.mark.asyncio
async def test_due_list_returns_only_patterns_whose_review_is_due(db_conn: asyncpg.Connection):
    _, overdue = await _seed(db_conn)
    later, upcoming, never = [
        await db_conn.fetchval(
            "insert into error_patterns (user_id, category, pattern_key, target_form, "
            " next_review_at) values ($1, 'article', $2, 'x', $3) returning id",
            USER_ID,
            key,
            due,
        )
        for key, due in (
            ("article_older", T0 - _days(9)),
            ("article_future", T0 + _days(9)),
            ("article_none", None),
        )
    ]
    await db_conn.execute(
        "update error_patterns set next_review_at = $2 where id = $1", overdue, T0 - _days(3)
    )

    due_now = await load_due_reviews(db_conn, USER_ID)

    # 가장 밀린 것이 앞이다. 미래·null 은 목록에 없다.
    assert [row.pattern_id for row in due_now] == [later, overdue]
    assert upcoming not in [row.pattern_id for row in due_now]
    assert never not in [row.pattern_id for row in due_now]
    assert due_now[0].pattern_key == "article_older"


# ㉒ **`now()`가 아니라 `clock_timestamp()`** — Postgres `now()`는 트랜잭션 시작 시각에
#    고정되어 시간 기반 판정을 무력화한다(설계서 §4.1이 Phase 1 §5.4 실측을 근거로 못 박았다).
#    이 테스트는 그 차이를 실제로 만든다: 트랜잭션이 시작된 **뒤**의 시각을 예정일로 두고
#    벽시계가 그 시각을 지나도록 기다린다. `now()`로 구현하면 이 행을 아직 미래로 본다.
@pytest.mark.asyncio
async def test_due_list_uses_the_wall_clock_not_the_frozen_transaction_time(
    db_conn: asyncpg.Connection,
):
    _, pattern_id = await _seed(db_conn)
    await db_conn.execute(
        "update error_patterns "
        "   set next_review_at = clock_timestamp() + interval '150 milliseconds' "
        " where id = $1",
        pattern_id,
    )
    await asyncio.sleep(0.4)

    due_now = await load_due_reviews(db_conn, USER_ID)

    assert [row.pattern_id for row in due_now] == [pattern_id], (
        "now()를 썼다 — 트랜잭션 시작 시각에 고정되어 이 예정일을 아직 미래로 본다"
    )


# ㉓ 백필 — 006 **전에** 쌓인 패턴은 그 패턴이 다시 발생할 때까지 예정일을 못 받는다.
#    이것이 없으면 마이그레이션 직후에도 목록이 0행이라 슬라이스 1의 완료 판정이 실물에서
#    성립하지 않는다(2026-09-04 dev DB 실측: 패턴 7행 · occurrence 17행 · 예정일 0건).
@pytest.mark.asyncio
async def test_backfill_schedules_every_pattern_that_already_has_history(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    # 006 이전 상태를 흉내낸다 — 이력은 있는데 예정일이 없다
    await db_conn.execute(
        "update error_patterns set next_review_at = null, mastery_score = 0 where id = $1",
        pattern_id,
    )

    touched = await recompute_all(db_conn, USER_ID)

    assert touched == 1
    assert (await _pattern_row(db_conn, pattern_id))["next_review_at"] == T0 + _days(1)
    assert _stages(await _task_rows(db_conn, pattern_id)) == [(1, "pending")]


# ㉔ 백필은 멱등이다 — 이력에서만 계산하므로 몇 번 돌려도 같다
@pytest.mark.asyncio
async def test_backfill_is_idempotent(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)

    await recompute_all(db_conn, USER_ID)
    first = dict(await _pattern_row(db_conn, pattern_id))
    first_tasks = [dict(row) for row in await _task_rows(db_conn, pattern_id)]
    await recompute_all(db_conn, USER_ID)

    assert dict(await _pattern_row(db_conn, pattern_id)) == first
    assert [dict(row) for row in await _task_rows(db_conn, pattern_id)] == first_tasks


# ㉕ `scenario_context`가 **최신** occurrence의 원문이라는 것(리뷰 L11 — 무보호였다).
#    `_HISTORY_SQL`의 `order by u.created_at desc`를 `asc`로 바꾸면 이 테스트가 깨진다.
@pytest.mark.asyncio
async def test_scenario_context_takes_the_latest_occurrence_not_the_first(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    first = await _utterance(db_conn, session_id, T0)
    latest = await _utterance(db_conn, session_id, T0 + _days(2))
    await db_conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, 'go to gym', 'go to the gym', '이유', 'medium', 0.9)",
        first,
        pattern_id,
    )
    await db_conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, 'go to office', 'go to the office', '이유', 'medium', 0.9)",
        latest,
        pattern_id,
    )

    await recompute(db_conn, pattern_id)

    assert (await _task_rows(db_conn, pattern_id))[0]["scenario_context"] == "go to office"
