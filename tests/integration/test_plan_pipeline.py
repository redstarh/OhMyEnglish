"""Task 7 — 계획·관찰 노트·수준 갱신을 **한 트랜잭션**에 저장한다 (설계서 §9 Contract).
파일 끝에 Task 8 의 종단 1건이 붙는다 — 저장한 계획을 **다음 세션 시작이 읽는지**.


`db_conn`(롤백되는 단일 트랜잭션)이 아니라 `db_pool` + `ended_session_with_history`를 쓴다.
`process_plan`은 자기 트랜잭션을 여러 개 연다 — 입력 읽기 → **트랜잭션 밖** Claude 호출 →
저장 한 트랜잭션(계획 + 노트 + `users.current_level` + `complete`). 그게 §9 의 요구사항이므로
커밋 경계를 흉내내지 않고 실제로 커밋시켜야 검증이 성립한다.

⚠️ **이 파일의 지배 규칙** (`tests/unit/test_plan.py` 머리말이 소유하는 판별법을 DB 쪽으로
옮긴 것): 이 슬라이스의 지배 실패 모드는 "통과하지만 이유가 틀린 테스트"다(누적 22건).
여기서 특히 조심한 자리 넷 —
① **노트 문구를 `note` 안에서 찾지 않는다.** jsonb 코덱이 없어 asyncpg 가 `str`를 주므로
   `"정답률" in note["note"]`는 **가짜 응답의 문구**를 다시 재는 것이고 코드가 무엇을
   저장했는지는 재지 않는다 — `json.loads`로 파싱해 키별 **왕복**을 잰다.
② **전역 `count(*)`를 쓰지 않는다.** 다른 테스트가 남긴 행이 섞이면 판별력을 잃는다 —
   전부 이 사용자/이 세션으로 좁힌다.
③ **양성만 재지 않는다.** 저장되어야 하는 경우와 **저장되지 않아야** 하는 경우를 함께 잰다
   (거부·부분반영·lease 상실·콜드스타트).
④ **목록은 전 항목을 순회한다.** 질문 3개의 첫 항목만 보면 2·3번째를 떼도 통과한다.
"""

from __future__ import annotations

import json
import logging
from datetime import timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest
from conftest import (
    PlanHistory,
    claim_plan_job,
    end_new_session,
    job_row,
    plan_json,
)

from app.models.plan import SessionInstruction
from app.services.plan import PLAN_NO_FOCUS_CANDIDATES, process_plan
from app.services.plan_input import RECENT_WINDOW_DAYS, load_plan_input
from app.services.sessions import load_prepared_plan

# `asyncio_mode = "auto"`(pyproject.toml)라 `async def test_` 에 마커를 붙이지 않는다.
#
# 이 팩토리가 내는 질문 3개는 `plan_json`이 소유한다 — 여기서 문장을 다시 적지 않고
# 응답에서 뽑아 대조한다(두 곳에 적으면 한쪽이 조용히 낡는다).


def _expected_questions(response: str) -> list[dict[str, str]]:
    """가짜 응답이 실제로 실은 질문 목록. 저장된 jsonb 와 **왕복**을 대조하는 기준이다."""
    questions = json.loads(response)["questions"]
    assert len(questions) == 3, f"기준 응답의 질문 수가 3이 아니다: {len(questions)}"
    return questions


async def _plan_row(pool: asyncpg.Pool, session_id: UUID) -> asyncpg.Record | None:
    async with pool.acquire() as conn:
        return await conn.fetchrow("select * from session_plans where session_id = $1", session_id)


async def _note_rows(pool: asyncpg.Pool, user_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return list(
            await conn.fetch(
                "select * from learner_notes where user_id = $1 order by created_at, id", user_id
            )
        )


async def _level(pool: asyncpg.Pool, user_id: UUID) -> str:
    async with pool.acquire() as conn:
        level = await conn.fetchval("select current_level from users where id = $1", user_id)
    assert level is not None, f"사용자 {user_id} 가 사라졌다"
    return level


# AS7 — 계획·노트·수준이 함께 남고 job 이 `done` 으로 수렴한다. 수준은 정확히 한 단계 오른다.
async def test_plan_note_and_level_all_land_and_the_job_is_done(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history: PlanHistory
):
    history = ended_session_with_history
    assert await _level(db_pool, history.user_id) == "A2", "001 의 기본 수준 전제가 깨졌다"
    response = plan_json(
        history.pattern_id,
        level_action="up",
        target_level="B1",
        level_reason="짧은 문장은 안정적이라 한 단계 올립니다.",
        notes=["짧은 문장에서는 관사를 붙이는데 길어지면 빼먹는다", "속도가 붙으면 the 를 흘린다"],
    )
    claude = fake_claude(response)
    job = await claim_plan_job(db_pool, history.session_id)

    await process_plan(db_pool, claude, job)

    # ① 수준은 `level.target_level`이 정본이다 (라벨 `action` 이 아니다).
    assert await _level(db_pool, history.user_id) == "B1"

    # ② 계획 1행 — jsonb 는 파싱해서, uuid[] 는 UUID 그대로 왕복해야 한다.
    plan = await _plan_row(db_pool, history.session_id)
    assert plan is not None, "계획 행이 저장되지 않았다"
    assert plan["source"] == "agent"  # 이 슬라이스는 'agent' 만 쓴다
    assert plan["target_level"] == "B1"
    assert plan["reason"] == json.loads(response)["reason"]
    # `focus_pattern_ids`는 `uuid[]` 컬럼이라 **읽을 때 UUID 로** 돌아온다 — 값이 그대로
    # 실렸는지 잰다. ⚠️ 이 단정은 쓰는 쪽에 `str()`을 씌우는 것을 잡지 **못한다**:
    # 2026-09-05 뮤테이션으로 확인했다(`[str(item.pattern_id) for …]`로 바꿔도 60건 전부
    # 초록). asyncpg 0.31 은 `uuid[]` 파라미터에 문자열도 받아 같은 값을 저장하므로 관측
    # 가능한 차이가 없다 — 계획서 브리프의 "`str()`을 씌우지 마라"는 스타일 지침이고
    # 테스트로 고정할 수 있는 계약이 아니다. 여기서 지키는 계약은 **저장된 값의 동일성**뿐이다.
    assert plan["focus_pattern_ids"] == [history.pattern_id]
    assert all(isinstance(value, UUID) for value in plan["focus_pattern_ids"])
    # ⚠️ 첫 항목만 보지 않는다 — 2·3번째를 떼도 통과하는 단정이 이 슬라이스의 사고였다.
    assert json.loads(plan["questions"]) == _expected_questions(response)
    stored_instruction = json.loads(plan["instruction"])
    assert stored_instruction == json.loads(response)["instruction"]
    # `InstructionFocus`에 `pattern_id`가 없기 때문에 이 jsonb 직렬화가 성립한다
    # (`json.dumps`는 UUID 를 직렬화하지 못한다) — 두 타입을 합치면 여기서 깨진다.
    assert all("pattern_id" not in item for item in stored_instruction["focus"])

    # ③ 관찰 노트 1행 — 문구를 찾지 않고 키별 왕복을 잰다(머리말 ①).
    notes = await _note_rows(db_pool, history.user_id)
    assert len(notes) == 1
    stored_note = json.loads(notes[0]["note"])
    assert stored_note["level_reason"] == "짧은 문장은 안정적이라 한 단계 올립니다."
    assert stored_note["observations"] == json.loads(response)["notes"]
    # 노트가 읽은 근거 범위 — `load_plan_input`이 준 창이 그대로 실려야 한다(§6.3).
    assert notes[0]["window_to"] - notes[0]["window_from"] == timedelta(days=RECENT_WINDOW_DAYS)

    # ④ job 은 `done` 이다 — `complete` 가 같은 트랜잭션 안에서 불렸다.
    async with db_pool.acquire() as conn:
        row = await job_row(conn, job.id)
    assert row["status"] == "done"
    assert row["last_error"] is None


# AS8 — 노트는 덧붙이기만 한다. 세션이 둘이면 노트가 둘이고 **먼저 쓴 행이 남는다.**
# (한 세션에 계획은 하나뿐이므로 — `session_plans.session_id` unique — 두 번째 세션이 필요하다.)
async def test_notes_are_append_only_across_two_sessions(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history: PlanHistory
):
    history = ended_session_with_history
    second_session = await end_new_session(db_pool, history.user_id)

    for session_id, level_reason in (
        (history.session_id, "첫 세션 사유"),
        (second_session, "둘째 세션 사유"),
    ):
        job = await claim_plan_job(db_pool, session_id)
        await process_plan(
            db_pool,
            fake_claude(plan_json(history.pattern_id, level_reason=level_reason)),
            job,
        )

    notes = await _note_rows(db_pool, history.user_id)
    assert len(notes) == 2
    # 먼저 쓴 행이 덮이지 않았다 — 순서까지 그대로다.
    assert [json.loads(row["note"])["level_reason"] for row in notes] == [
        "첫 세션 사유",
        "둘째 세션 사유",
    ]
    # 세션마다 계획 1행씩. 두 번째 세션의 계획이 첫 세션의 것을 덮지 않는다.
    async with db_pool.acquire() as conn:
        plan_sessions = await conn.fetch(
            "select p.session_id from session_plans p "
            "join learning_sessions s on s.id = p.session_id where s.user_id = $1",
            history.user_id,
        )
    assert {row["session_id"] for row in plan_sessions} == {history.session_id, second_session}


# 설계서 §9 Failure — 검증 거부는 계획을 **저장하지 않고** job 에 사유를 남긴다.
async def test_rejected_plan_stores_nothing_and_records_the_reason(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history: PlanHistory
):
    history = ended_session_with_history
    claude = fake_claude(plan_json(history.pattern_id, reason=""))  # 이유 빈값 → 계약 위반
    job = await claim_plan_job(db_pool, history.session_id)

    await process_plan(db_pool, claude, job)

    assert len(claude.prompts) == 1, "거부를 재려면 Claude 가 실제로 불렸어야 한다"
    assert await _plan_row(db_pool, history.session_id) is None
    assert await _note_rows(db_pool, history.user_id) == []
    assert await _level(db_pool, history.user_id) == "A2"
    async with db_pool.acquire() as conn:
        row = await job_row(conn, job.id)
    assert row["last_error"] is not None
    assert "plan contract violated" in row["last_error"]
    # 상한 전이므로 정상 백오프로 재큐된 `pending` 이다 — raise 로 새지 않았다는 증거.
    assert row["status"] == "pending"


# 계획서 Task 7 ① — 지어낸 `pattern_id`는 거부된다. FK 가 없어 조용히 저장되면 실패보다 나쁘다.
async def test_invented_pattern_id_is_rejected_and_nothing_is_stored(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history: PlanHistory
):
    history = ended_session_with_history
    invented = uuid4()
    assert invented != history.pattern_id
    claude = fake_claude(plan_json(invented))
    job = await claim_plan_job(db_pool, history.session_id)

    await process_plan(db_pool, claude, job)

    assert len(claude.prompts) == 1, "이 경로는 콜드스타트가 아니다 — Claude 가 불렸어야 한다"
    assert await _plan_row(db_pool, history.session_id) is None
    assert await _note_rows(db_pool, history.user_id) == []
    async with db_pool.acquire() as conn:
        row = await job_row(conn, job.id)
    # 사유에 그 id 가 들어 있어야 어느 값이 문제였는지 job 이력에서 읽을 수 있다.
    assert str(invented) in row["last_error"]


# 허용 id 집합은 `due_reviews ∪ chronic`이다 — **두 절 모두** 실제로 쓰인다.
#
# ⚠️ 이 테스트가 없던 동안 `process_plan`의 `| {metric.pattern_id for metric in data.chronic}`를
# **통째로 지워도 549건이 전부 통과했다**(2026-09-05 codex 리뷰 지적, 메인이 직접 재현).
# 원인은 두 겹이었다: ① 픽스처가 발생·발화를 안 심어 `data.chronic`이 **0건**이었다(실측
# `due=1 chronic=0`) ② 그래서 chronic 에만 있는 id 로 초점을 고르는 경로가 한 번도 실행되지
# 않았다. 두 목록은 **구조적으로 갈라진다** — `load_due_reviews`는 `next_review_at`으로 거르고
# `load_chronic_metrics`는 거르지 않으므로, "발생은 있지만 아직 예정일이 안 된" 패턴은
# chronic 에만 있다. 그 패턴을 초점으로 고른 계획이 거부되면 정당한 계획을 잃는다.
async def test_focus_from_the_chronic_list_alone_is_accepted(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history: PlanHistory
):
    history = ended_session_with_history
    async with db_pool.acquire() as conn:
        data = await load_plan_input(conn, history.user_id)

    # 선행 확인 — 이 id 가 정말 chronic 에만 있어야 이 테스트가 의미를 갖는다.
    assert history.chronic_pattern_id in {metric.pattern_id for metric in data.chronic}
    assert history.chronic_pattern_id not in {review.pattern_id for review in data.due_reviews}

    claude = fake_claude(plan_json(history.chronic_pattern_id))
    job = await claim_plan_job(db_pool, history.session_id)

    await process_plan(db_pool, claude, job)

    assert len(claude.prompts) == 1, "이 경로는 콜드스타트가 아니다 — Claude 가 불렸어야 한다"
    plan = await _plan_row(db_pool, history.session_id)
    assert plan is not None, "chronic 에만 있는 초점이 거부됐다 — 허용 집합의 chronic 절이 죽었다"
    assert plan["focus_pattern_ids"] == [history.chronic_pattern_id]


# 부분 반영이 없다 — 계획 insert 가 실패하면 노트도 수준 갱신도 남지 않는다(§9 Contract).
#
# 실패를 만드는 방법: 그 세션에 계획 행을 **미리** 넣어 `unique(session_id)`를 건드린다.
# ⚠️ 사용자를 지우는 방법은 쓸 수 없다 — cascade 가 세션까지 지우고, 그러면 `process_plan`이
# "세션 없음" 정상 실패 경로로 빠져 트랜잭션을 열지도 않는다.
# ⚠️ 예외가 **밖으로 새지 않는다**: `analysis.py`의 관례대로 broad `except`가 삼켜
# `report_failure`로 보고한다. 새게 두면 job 이 `running` 에 남아 lease 만료까지 갔다가
# "lease expired without report"라는 **거짓 사유**로 종결된다.
async def test_no_partial_write_when_the_plan_insert_fails(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history: PlanHistory
):
    history = ended_session_with_history
    questions = json.dumps(
        [{"prompt": f"q{i}", "context": f"c{i}"} for i in range(3)], ensure_ascii=False
    )
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into session_plans "
            "(session_id, focus_pattern_ids, questions, target_level, reason, instruction, source) "
            "values ($1, $2, $3, 'A2', '먼저 있던 계획', '{}', 'agent')",
            history.session_id,
            [history.pattern_id],
            questions,
        )
    job = await claim_plan_job(db_pool, history.session_id)
    claude = fake_claude(plan_json(history.pattern_id, level_action="up", target_level="B1"))

    await process_plan(db_pool, claude, job)

    # 노트와 수준 갱신이 같은 트랜잭션에 있었으므로 함께 되돌아간다.
    assert await _note_rows(db_pool, history.user_id) == []
    assert await _level(db_pool, history.user_id) == "A2"
    plan = await _plan_row(db_pool, history.session_id)
    assert plan is not None
    assert plan["reason"] == "먼저 있던 계획", "먼저 있던 계획이 덮였다"
    async with db_pool.acquire() as conn:
        row = await job_row(conn, job.id)
    assert row["last_error"] is not None
    assert "UniqueViolationError" in row["last_error"]


# 계획서 Task 7 ② 콜드스타트 — 후보가 0건이면 Claude 를 **부르지 않고** 큐에 사유를 남긴다.
# `logger.info`가 아니라 job 사유로 남기는 이유: 나중에 "왜 계획이 없었나"를 이력에서 읽는다.
# ⚠️ 폴백을 막지 않는다 — 계획 행 부재 시 세션 시작이 시나리오 뱅크로 떨어지는 것이 §3.3 이다.
async def test_cold_start_skips_the_claude_call(
    db_pool: asyncpg.Pool, fake_claude, committed_session
):
    # 이 사용자에게는 복습 예정 패턴도, 만성 지표도 없다(발화·occurrence 를 만들지 않았다).
    claude = fake_claude()  # 응답 0개 — 부르면 FakeClaudeClient 의 assert 가 터진다
    job = await claim_plan_job(db_pool, committed_session.session_id)

    await process_plan(db_pool, claude, job)

    assert claude.prompts == [], "후보가 0건인데 Claude 를 불렀다"
    assert await _plan_row(db_pool, committed_session.session_id) is None
    assert await _note_rows(db_pool, committed_session.user_id) == []
    async with db_pool.acquire() as conn:
        row = await job_row(conn, job.id)
    assert row["last_error"] == PLAN_NO_FOCUS_CANDIDATES
    assert row["status"] == "pending"


# lease 를 잃으면 **전부 롤백**하고 `report_failure`를 부르지 않는다 — 그 job 은 이제 우리 것이
# 아니다. 무시하면 노트가 append-only 라 다시 claim 한 워커가 **중복 행**을 남긴다.
async def test_a_lost_lease_rolls_everything_back_without_reporting_failure(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history: PlanHistory
):
    history = ended_session_with_history
    job = await claim_plan_job(db_pool, history.session_id)
    # 다른 워커가 lease 를 가져간 상태를 만든다 — `complete` 는 `locked_by` 로 게이트한다.
    stolen_token = uuid4().hex
    async with db_pool.acquire() as conn:
        updated = await conn.fetchval(
            "update analysis_jobs set locked_by = $2 where id = $1 returning locked_by",
            job.id,
            stolen_token,
        )
    assert updated == stolen_token, "lease 탈취를 만들지 못했다"
    claude = fake_claude(plan_json(history.pattern_id, level_action="up", target_level="B1"))

    await process_plan(db_pool, claude, job)

    assert await _plan_row(db_pool, history.session_id) is None
    assert await _note_rows(db_pool, history.user_id) == []
    assert await _level(db_pool, history.user_id) == "A2"
    async with db_pool.acquire() as conn:
        row = await job_row(conn, job.id)
    # `report_failure`를 부르지 않았다는 증거: 사유가 비어 있고 상태가 그대로 `running` 이다.
    assert row["last_error"] is None
    assert row["status"] == "running"


# Task 5 리뷰 이월 — `level.action` 이 실제 이동과 어긋나도 **저장을 거부하지 않는다**(라벨이
# 잘못 붙은 것이 계획 전체를 버릴 이유는 아니다). 다만 조용히 삼키지 않는다: 관측이 없으면
# 프롬프트가 라벨을 잘못 유도한다는 신호를 잃는다.
async def test_disagreeing_level_action_label_is_warned_but_stored(
    db_pool: asyncpg.Pool,
    fake_claude,
    ended_session_with_history: PlanHistory,
    caplog: pytest.LogCaptureFixture,
):
    history = ended_session_with_history
    # A2 → B1 은 **상향**인데 라벨은 "down" 이다.
    claude = fake_claude(plan_json(history.pattern_id, level_action="down", target_level="B1"))
    job = await claim_plan_job(db_pool, history.session_id)

    with caplog.at_level(logging.WARNING, logger="app.services.plan"):
        await process_plan(db_pool, claude, job)

    # 저장은 그대로 되고, 수준은 `target_level` 이 정본이다.
    assert await _level(db_pool, history.user_id) == "B1"
    plan = await _plan_row(db_pool, history.session_id)
    assert plan is not None
    assert plan["target_level"] == "B1"
    # 사유는 노트에 그대로 남는다.
    notes = await _note_rows(db_pool, history.user_id)
    assert json.loads(notes[0]["note"])["level_reason"] == "정답률이 아직 낮습니다."
    # 경고 한 줄 — 문구를 그 주어(`level.action`)에 묶어서 찾는다.
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.services.plan" and "level.action" in record.getMessage()
    ]
    assert len(warnings) == 1, f"level.action 경고가 1건이 아니다: {warnings}"
    assert "'down'" in warnings[0]  # 모델이 붙인 라벨
    assert "'up'" in warnings[0]  # 실제 이동
    assert "A2" in warnings[0] and "B1" in warnings[0]


# 음성 케이스 — 라벨이 맞으면 그 경고가 **나오지 않는다.** 이것이 없으면 "항상 경고한다"는
# 구현도 위 테스트를 통과하고, 경고가 소음이 되어 신호로서의 값을 잃는다.
async def test_matching_level_action_label_produces_no_warning(
    db_pool: asyncpg.Pool,
    fake_claude,
    ended_session_with_history: PlanHistory,
    caplog: pytest.LogCaptureFixture,
):
    history = ended_session_with_history
    claude = fake_claude(plan_json(history.pattern_id, level_action="up", target_level="B1"))
    job = await claim_plan_job(db_pool, history.session_id)

    with caplog.at_level(logging.WARNING, logger="app.services.plan"):
        await process_plan(db_pool, claude, job)

    assert await _level(db_pool, history.user_id) == "B1"  # 정상 경로였음을 먼저 확인한다
    assert [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.services.plan" and "level.action" in record.getMessage()
    ] == []


class _PoolProbingClaude:
    """Claude 호출 **시점**의 풀 상태를 기록한다 — 트랜잭션 밖에서 부르는지 재기 위해.

    ⚠️ 단정을 이 안에서 하지 않는다: `process_plan`의 broad `except Exception` 이
    `AssertionError` 를 삼켜 `report_failure` 로 바꾸므로, 실패가 "저장 실패"로 잘못
    보고되고 테스트는 이유가 틀린 채 초록이 된다. **관측만 하고 판정은 테스트 본문에서.**
    """

    def __init__(self, pool: asyncpg.Pool, response: str) -> None:
        self._pool = pool
        self._response = response
        self.prompts: list[str] = []
        self.pool_state: list[tuple[int, int]] = []

    async def analyze(self, prompt: str) -> str:
        self.prompts.append(prompt)
        self.pool_state.append((self._pool.get_idle_size(), self._pool.get_size()))
        return self._response


# 네트워크 대기 동안 행 잠금을 들고 있으면 다른 job 이 막힌다 — Claude 호출은 트랜잭션 밖이다.
# 연결을 붙들고 있으면 그 순간 유휴 연결이 전체보다 하나 적다.
async def test_claude_is_called_with_no_connection_held(
    db_pool: asyncpg.Pool, ended_session_with_history: PlanHistory
):
    history = ended_session_with_history
    claude = _PoolProbingClaude(
        db_pool, plan_json(history.pattern_id, level_action="up", target_level="B1")
    )
    job = await claim_plan_job(db_pool, history.session_id)

    await process_plan(db_pool, claude, job)

    assert len(claude.prompts) == 1, "Claude 가 불리지 않았다 — 아래 단정이 공허해진다"
    idle, size = claude.pool_state[0]
    assert size > 0
    assert idle == size, f"Claude 호출 중에 연결을 붙들고 있었다 (idle={idle}, size={size})"
    # 정상 경로였음을 확인한다 — 계획이 저장되지 않았다면 위 관측은 다른 흐름의 것이다.
    assert await _plan_row(db_pool, history.session_id) is not None


# Task 8 — **워커가 방금 저장한 계획을 다음 세션 시작이 읽는다.** 종단으로 재는 이유:
# 저장은 `json.dumps(instruction.model_dump())`(문자열)이고 읽기는 `model_validate`인데,
# 픽스처가 심은 jsonb 로만 읽기를 재면 그 왕복이 아니라 **픽스처의 모양**을 재게 된다 —
# 저장 쪽이 모양을 바꿔도 초록으로 남는다.
async def test_the_next_session_start_reads_the_plan_the_worker_saved(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history: PlanHistory
):
    history = ended_session_with_history
    response = plan_json(history.pattern_id, reason="관사를 계속 빼먹어서 오늘은 그것만 봅니다.")
    job = await claim_plan_job(db_pool, history.session_id)

    await process_plan(db_pool, fake_claude(response), job)

    stored = await _plan_row(db_pool, history.session_id)
    assert stored is not None, "저장이 안 됐으면 읽기를 잴 수 없다"
    async with db_pool.acquire() as conn:
        prepared = await load_prepared_plan(conn, history.user_id)

    assert prepared is not None, "직전 세션이 만든 계획을 읽지 못했다"
    assert prepared.plan_id == stored["id"]
    assert prepared.reason == json.loads(response)["reason"]
    # 지시문이 **구조로** 왕복한다 — 문자열이 그대로 새면 Task 10 의 조립이 문자열을
    # 필드처럼 다루게 된다.
    assert prepared.instruction == SessionInstruction.model_validate(
        json.loads(response)["instruction"]
    )
