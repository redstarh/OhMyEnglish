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


# ⑧ 010의 새 출력 두 개(`ladder`·`cycle_started_at`)를 **DB 없이** 단정한다
#    (코드 리뷰 LOW-3). 모듈 docstring이 `fold_stages`의 장점으로 "순수 함수라 DB 없이
#    검증된다"를 내세우는데, 새 출력에는 그 장점이 적용되지 않고 있었다 — 두 값이 DB 테스트를
#    거쳐서만 관측됐다.
# ⛔ 여기서 잠그는 것은 **사다리가 연쇄라는 것**이다: 각 단계의 `due_at`은 그 단계를 촉발한
#    시각 + `STAGE_DAYS[stage-1]`이고, 촉발 시각은 1단계에서는 재발 시각이고 그 뒤로는 앞
#    단계를 **접은 정답의 시각**이다. `anchor`(접은 뒤의 값)로 계산하면 1단계의 예정일이
#    미래로 밀려 조용히 틀린다 — 그 오류는 이 단정 없이는 DB 테스트에서만 드러난다.
def test_fold_stages_returns_the_ladder_and_the_cycle_key_without_a_database():
    first = T0 + _days(1)  # 1단계 예정일(T0+1일)에 정확히 맞혔다 → 접힌다

    state = fold_stages(T0, [first], CONTEXT)

    assert state.cycle_started_at == T0  # 사이클 키는 **재발 시각**이다
    assert [(row.stage, row.due_at, row.completed_at) for row in state.ladder] == [
        (1, T0 + _days(1), first),  # 접힌 단계 — 촉발 시각은 재발 시각
        (2, first + _days(3), None),  # 열린 단계 — 촉발 시각은 앞 단계를 접은 정답
    ]
    # 재발이 없으면 사다리도 사이클 키도 비어 있다 — 행을 만들 근거가 없다.
    empty = fold_stages(None, [], CONTEXT)
    assert empty.ladder == ()
    assert empty.cycle_started_at is None


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


async def _occurrence(
    conn: asyncpg.Connection, utterance_id: UUID, pattern_id: UUID, span: str = CONTEXT
) -> None:
    await conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, $3, 'go to the gym', '정관사가 필요합니다.', 'medium', 0.9)",
        utterance_id,
        pattern_id,
        span,
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


# ⚠️ **`id`·`created_at`을 함께 select한다** — 010 설계의 핵심이 "재계산이 이 둘을 보존한다"이고,
# 그것을 보는 테스트가 없으면 upsert가 delete+insert로 되돌아가도 아무 테스트가 실패하지 않는다
# (설계서 `2026-09-08-review-task-history-design.md` §1.3 · §6).
# `order by`에 `cycle_started_at`을 **먼저** 둔다: 사이클이 둘 이상이면 `review_stage`만으로는
# 순서가 정해지지 않아 단정이 조용히 흔들린다.
async def _task_rows(conn: asyncpg.Connection, pattern_id: UUID) -> list[asyncpg.Record]:
    return await conn.fetch(
        "select id, created_at, cycle_started_at, review_stage, status, due_at, "
        "completed_at, scenario_context from review_tasks "
        "where pattern_id = $1 order by cycle_started_at, review_stage",
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
    # 010부터 접힌 1단계 행이 함께 남는다 — 그것이 히스토리다(이전 판은 `[(2,"pending")]`이었다).
    assert _stages(await _task_rows(db_conn, pattern_id)) == [(1, "done"), (2, "pending")]


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
    # ⚠️ `done`의 뜻이 010에서 「사이클 완주」→「**단계** 완주」로 바뀌었다
    # → 완주 사이클은 세 행이다.
    tasks = await _task_rows(db_conn, pattern_id)
    assert _stages(tasks) == [(1, "done"), (2, "done"), (FINAL_STAGE, "done")]
    # 완주한 3단계 행도 자기 실제 예정일을 갖는다 — 이전 판의 `next_review_at or anchor` 폴백이
    # 사라진 자리다. 2단계를 접은 시각 + 7일이고, 그 시각이 곧 3단계의 완주 시각 기준이 됐다.
    assert all(row["completed_at"] is not None for row in tasks)
    assert tasks[FINAL_STAGE - 1]["due_at"] == tasks[1]["completed_at"] + _days(7)


# ⑪ 재발하면 1단계로 되돌아가고 **완주한 사이클은 이력으로 남는다** (010 · TASK-43)
# ⛔ **이 단정은 뒤집혔다.** 이전 판은 `test_..._leaves_no_higher_row`였고 캡틴 결정 2026-09-03의
#    "재발 시 상위 단계 행은 삭제한다"를 박고 있었다. 그 결정의 근거(파생값은 언제든 다시
#    계산된다)는 지금도 참이지만 `id`·`created_at`·접힌 단계에는 닿지 않는다 — 지우면 히스토리
#    화면이 "1·2·3단계를 했고 그 뒤 재발했다"를 그릴 근거가 사라진다(설계서 §3.1).
#    되돌리려면 그 설계서를 먼저 뒤집어라.
@pytest.mark.asyncio
async def test_a_relapse_opens_a_new_cycle_and_keeps_the_completed_one(
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
    assert state.cycle_started_at == relapse_at
    assert (await _pattern_row(db_conn, pattern_id))["mastery_score"] == 0
    tasks = await _task_rows(db_conn, pattern_id)
    # 완주한 옛 사이클 세 행 + 새 사이클의 열린 1단계.
    assert _stages(tasks) == [(1, "done"), (2, "done"), (3, "done"), (1, "pending")]
    # 두 사이클이 **다른 `cycle_started_at`으로** 갈라져 있다 — 옛 1단계와 새 1단계가 같은
    # 자연키를 다투지 않는 것이 010의 유일키가 하는 일이다.
    assert {row["cycle_started_at"] for row in tasks} == {T0, relapse_at}
    assert tasks[-1]["cycle_started_at"] == relapse_at


# ⑪-2 재발이 **끊은** 사이클의 열린 단계는 `abandoned`가 된다 (010 · 설계서 §4 Failure)
# 이것이 히스토리 화면이 "1단계는 했고 2단계에서 끊겼다"를 그릴 근거다. 이전 판에서는 그 행이
# 삭제되어 존재하지 않았고, 그래서 "어디서 끊겼는가"가 복원 불가능했다.
@pytest.mark.asyncio
async def test_a_relapse_abandons_the_open_stage_of_the_interrupted_cycle(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    folded_at = T0 + _days(1)
    await _attempt(db_conn, await _utterance(db_conn, session_id, folded_at), pattern_id, "correct")
    await recompute(db_conn, pattern_id)  # 1단계 done · 2단계 pending 인 상태를 만든다
    rows_before = await _task_rows(db_conn, pattern_id)
    # `dict(row)`로 **복사**해 둔다 — 아래 재계산 뒤에 같은 행을 다시 읽어 대조하기 때문이다.
    before = {row["review_stage"]: dict(row) for row in rows_before}
    assert _stages(rows_before) == [(1, "done"), (2, "pending")]

    # 2단계 예정일(접은 시각 + 3일) **전에** 재발한다 → 그 사이클은 완주하지 못하고 끊긴다.
    relapse_at = folded_at + _days(2)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, relapse_at), pattern_id)
    await recompute(db_conn, pattern_id)

    tasks = await _task_rows(db_conn, pattern_id)
    assert _stages(tasks) == [(1, "done"), (2, "abandoned"), (1, "pending")]
    # ⚠️ **끊긴 사이클의 행이 그 자리에 그대로 있다** — `id`·`created_at`이 바뀌지 않았다.
    # 이 단정이 무너지면 미래에 그 행에 붙을 학습자 이력이 갈 곳을 잃는다.
    for stage in (1, 2):
        row = next(r for r in tasks if r["cycle_started_at"] == T0 and r["review_stage"] == stage)
        assert row["id"] == before[stage]["id"]
        assert row["created_at"] == before[stage]["created_at"]
    # 접힌 1단계는 완주 시각을 유지하고, 중단된 2단계는 완주 시각이 없다.
    assert next(r for r in tasks if r["review_stage"] == 1)["completed_at"] == folded_at
    assert next(r for r in tasks if r["status"] == "abandoned")["completed_at"] is None


# ⑪-3 근거가 이력에서 사라지면 행을 **은퇴시키고 지우지 않는다** (010 · 설계서 §4 Failure)
# ⛔ 지우지 않는 이유는 성능이 아니다: `TASK-3`이 학습자 이력을 이 행에 FK로 붙이면 삭제가
#    cascade로 그 이력을 날린다. `superseded`는 화면에서 감춰지므로 사용자에게는 사라진 것과 같다.
@pytest.mark.asyncio
async def test_a_pattern_whose_basis_vanished_retires_its_rows_instead_of_deleting_them(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    utterance_id = await _utterance(db_conn, session_id, T0)
    await _occurrence(db_conn, utterance_id, pattern_id)
    await recompute(db_conn, pattern_id)
    before = dict((await _task_rows(db_conn, pattern_id))[0])
    assert before["status"] == "pending"

    # 재분석이 그 판정을 지웠다 — 이 패턴에는 재발이 하나도 남지 않는다.
    await db_conn.execute("delete from error_occurrences where pattern_id = $1", pattern_id)
    state = await recompute(db_conn, pattern_id)

    assert state.cycle_started_at is None
    assert state.ladder == ()
    assert (await _pattern_row(db_conn, pattern_id))["next_review_at"] is None
    tasks = await _task_rows(db_conn, pattern_id)
    assert _stages(tasks) == [(1, "superseded")]
    assert tasks[0]["id"] == before["id"]  # 지워지지 않았다 — 같은 행이다
    assert tasks[0]["created_at"] == before["created_at"]


# ⑪-3b 재분석이 **최신 재발을 지워 사이클 시작이 뒤로 움직이면** 옛 사이클 행이 은퇴한다
# (010 · 설계서 §4 Failure · 코드 리뷰 MEDIUM-3)
# ⚠️ **`_SUPERSEDE_TASKS_SQL`의 조건은 두 갈래인데 그중 하나만 테스트가 잠그고 있었다.**
#    ② `cycle_started_at = $2 ∧ review_stage > $3`(사다리가 짧아졌다)는 ⑪-3·재분석 테스트가 덮지만,
#    ① `cycle_started_at > $2`(사이클 시작이 **뒤로** 움직였다)는 무보호였다 — 그 갈래를 지워도
#    전 테스트가 통과했다. 설계서 §7 약점 1이 지목한 바로 그 경로라 특히 값비싸다.
# ⛔ 이 테스트가 잠그는 것: 옛 사이클 행이 **지워지지 않고** `superseded`로 남는다. 지우면
#    `TASK-3`이 붙일 학습자 이력이 cascade로 날아간다(⑪-3과 같은 이유).
@pytest.mark.asyncio
async def test_reanalysis_that_drops_the_latest_relapse_retires_the_newer_cycle(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    # 재발 둘 — T0 과 그보다 **뒤**인 T0+10일. 두 번째가 현재 사이클을 연다.
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    later = T0 + _days(10)
    later_utterance = await _utterance(db_conn, session_id, later)
    await _occurrence(db_conn, later_utterance, pattern_id)
    state = await recompute(db_conn, pattern_id)
    assert state.cycle_started_at == later  # 최신 재발이 사이클을 연다
    newer = [r for r in await _task_rows(db_conn, pattern_id) if r["cycle_started_at"] == later]
    assert [(r["review_stage"], r["status"]) for r in newer] == [(1, "pending")]
    newer_id, newer_created = newer[0]["id"], newer[0]["created_at"]

    # 재분석이 **최신** 판정만 지웠다 → 사이클 시작이 T0 로 되돌아간다(뒤로 움직인다).
    await db_conn.execute("delete from error_occurrences where utterance_id = $1", later_utterance)
    state = await recompute(db_conn, pattern_id)

    assert state.cycle_started_at == T0
    tasks = await _task_rows(db_conn, pattern_id)
    # T0 사이클이 열려 있고, 뒤 사이클 행은 **은퇴했지만 그 자리에 그대로 있다.**
    assert _stages(tasks) == [(1, "pending"), (1, "superseded")]
    retired = next(r for r in tasks if r["cycle_started_at"] == later)
    assert retired["id"] == newer_id  # 지워지지 않았다 — 같은 행이다
    assert retired["created_at"] == newer_created


# ⑪-4 `scenario_context`는 **접힌 단계에서 동결되고 열린 단계에서만 갱신된다** (010 · 설계서 §7-3)
# 그러지 않으면 1단계 행의 연습 문구가 나중 오류의 원문으로 덮여 "그때 무엇으로 연습했는가"가
# 틀어진다. ⛔ 완화일 뿐 해결이 아니다 — **열린 행의 문맥은 여전히 바뀐다**
# (그 약점은 설계서가 소유).
@pytest.mark.asyncio
async def test_scenario_context_is_frozen_on_a_folded_stage_but_updated_on_the_open_one(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    # ⚠️ **사이클 시각을 `incorrect` 판정으로 고정한다.** 그래야 뒤에 occurrence를 하나 더 넣어
    # 문맥만 바꿀 수 있다 — `relapse_at`은 `greatest(최신 occurrence, 최신 incorrect)`이므로
    # 새 occurrence를 그 `incorrect`보다 **앞에** 두면 사이클 키가 움직이지 않는다.
    # ⛔ 두 occurrence를 **같은 시각**에 두어 이것을 만들려 하지 마라: `_HISTORY_SQL`의 tie-break가
    #    `eo.id desc`이고 그 컬럼은 `gen_random_uuid()`라 어느 쪽이 「최신」인지 **비결정적**이다
    #    (이 테스트를 그렇게 쓰다가 단독 실행에서 실패했다 — 파일 전체 실행에서는 통과했다).
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    relapse_at = T0 + _days(2)
    await _attempt(
        db_conn, await _utterance(db_conn, session_id, relapse_at), pattern_id, "incorrect"
    )
    folded_at = relapse_at + _days(1)
    await _attempt(db_conn, await _utterance(db_conn, session_id, folded_at), pattern_id, "correct")
    await recompute(db_conn, pattern_id)
    assert _stages(await _task_rows(db_conn, pattern_id)) == [(1, "done"), (2, "pending")]
    assert [row["scenario_context"] for row in await _task_rows(db_conn, pattern_id)] == [
        CONTEXT,
        CONTEXT,
    ]

    # 새 occurrence를 `relapse_at` **앞에** 넣는다 → 사이클 키는 그대로이고 문맥만 바뀐다.
    later_span = "go to office"
    await _occurrence(
        db_conn, await _utterance(db_conn, session_id, T0 + _days(1)), pattern_id, later_span
    )
    await recompute(db_conn, pattern_id)

    tasks = await _task_rows(db_conn, pattern_id)
    assert {row["cycle_started_at"] for row in tasks} == {relapse_at}, "사이클이 갈라졌다"
    assert _stages(tasks) == [(1, "done"), (2, "pending")]
    assert tasks[0]["scenario_context"] == CONTEXT, "접힌 단계의 연습 문구가 덮였다"
    assert tasks[1]["scenario_context"] == later_span


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
    # `_task_rows`가 `id`·`created_at`을 select하므로 이 비교가 010의 핵심을 직접 잠근다:
    # upsert를 delete+insert로 되돌리면 두 컬럼이 새로 발급돼 여기서 실패한다.
    assert [dict(row) for row in first_tasks] == [dict(row) for row in second_tasks]
    # 접힌 1단계 + 열린 2단계 = 2행 (이전 판은 1행이었다 — 010이 이력을 남기기 때문에 바뀐다).
    assert _stages(second_tasks) == [(1, "done"), (2, "pending")]


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
