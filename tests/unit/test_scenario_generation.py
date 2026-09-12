"""`scenario_generator.process_scenario` 와 그 배선 (`TASK-5` · 결정 79·80).

⛔ **재는 것 가운데 둘이 판별력용이다.** 「intake 세션이 job 을 건다」만 재면 **늘 거는 구현**도
통과하고, 「값역에 travel 이 있다」만 재면 `shadowing` 이 새도 통과한다 — 반대 경우를 함께 잰다.

⚠️ 이 파일은 `db_pool`(커밋되는 픽스처)을 쓴다. `create_session`·`end_session` 이 pool 을 받고
job 등록이 세션 종료와 **한 트랜잭션**이어야 하므로 롤백 픽스처로는 그 결합을 잴 수 없다.

⛔⛔ **`db_pool` 은 아무것도 정리하지 않는다 — 손으로 지워야 한다.** 그 픽스처 docstring 이
*"Writes here **commit** — pair it with `committed_session` (or clean up by hand) so nothing
survives the test"* 로 그것을 명시한다. ⚠️ **이 파일의 초안이 「픽스처가 teardown 에서 지운다」고
잘못 적고 정리를 안 했다.** 그 결과 남은 커밋 행이 **다른 테스트 7개를 깨뜨렸다**(롤백 픽스처를
쓰는 테스트가 「시나리오 2행」을 기대하는데 내 커밋 행이 그 수를 늘렸다). ⇒ 아래
`_cleanup_committed_rows` 가 이 모듈이 만든 것만 지운다.

⛔ **다른 테스트가 만든 행을 지우지 않는다.** `delete from learning_scenarios` 를 쓰다가
`learning_sessions_scenario_id_fkey` 위반을 만났다 — 앞 테스트의 세션이 그 무대를 참조하고 있다.
⇒ 각 테스트가 **자기 제목**으로 만들고 자기 것만 센다. 그래서 아래 `_TITLES` 가 테스트마다 다르다.
"""

from __future__ import annotations

import json
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio

from app.services.jobs import JOB_TYPE_GENERATE_SCENARIO, ClaimedJob
from app.services.scenario_generator import process_scenario
from app.services.sessions import SCENARIO_INTAKE_MODE, create_session, end_session

# 이 모듈이 만든 행의 표지. ⛔ 정리가 이 값에 걸리므로 다른 파일과 겹치지 않는 이름이어야 한다.
_MARK = "scenario-gen-test"

# 테스트마다 다른 제목 — 위 ⛔ 가 근거다.
_TITLES = {
    "stored": "Reporting a delay to my manager",
    "empty": "A stage that must never be stored",
    "rejected": "A stage that the parser must refuse",
    "domain": "Asking for help abroad",
    "dup": "Agreeing the next milestone",
}


class _StubClaude:
    """고정 응답을 돌려주는 대역. ⛔ 단정을 여기서 하지 않는다 — `process_scenario` 의 broad
    `except` 가 `AssertionError` 를 삼켜 「저장 실패」로 잘못 보고한다(`_PoolProbingClaude` 의
    같은 경고와 같은 이유). 관측만 하고 판정은 테스트 본문에서 한다."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.prompts: list[str] = []
        self.purposes: list[str | None] = []

    async def analyze(self, prompt: str, **kwargs: object) -> str:
        self.prompts.append(prompt)
        purpose = kwargs.get("purpose")
        self.purposes.append(purpose if isinstance(purpose, str) else None)
        return self._response


def _reply(title: str, **overrides: object) -> str:
    body: dict[str, object] = {
        "category": "business",
        "title": title,
        "prompt_template": "You are the learner's manager hearing about a delayed task.",
    }
    body.update(overrides)
    return json.dumps(body)


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_committed_rows(db_pool: asyncpg.Pool):
    """⛔ 이 모듈이 커밋한 행을 지운다 — `db_pool` 은 아무것도 정리하지 않는다.

    순서가 중요하다: **사용자를 먼저** 지워야 세션·발화·job 이 cascade 되고, 그 뒤에야 무대를
    지울 수 있다(세션이 `scenario_id` 로 참조하므로 반대 순서는 FK 위반이다).
    ⚠️ 표지(`_MARK`·`_TITLES`·`seeded `·`a clip `)로 좁혀 **남의 행을 건드리지 않는다.**
    """
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("delete from users where display_name = $1", _MARK)
        await conn.execute(
            "delete from learning_scenarios where title = any($1::text[])",
            list(_TITLES.values()),
        )
        await conn.execute(
            "delete from learning_scenarios where title like 'seeded %' or title like 'a clip %'"
        )


async def _fresh_user(conn: asyncpg.Connection, *, level: str = "A2") -> UUID:
    return await conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ($1, 'Asia/Seoul', $2) returning id",
        _MARK,
        level,
    )


async def _seed_one_stage(conn: asyncpg.Connection, *, category: str = "business") -> UUID:
    """`source='seed'` 행 하나 — 값역이 여기서 나오므로 없으면 프롬프트가 거부된다."""
    return await conn.fetchval(
        "insert into learning_scenarios (category, level, title, prompt_template) "
        "values ($1, 'A2', $2, 'You are someone.') returning id",
        category,
        f"seeded {uuid4().hex[:8]}",
    )


async def _say(conn: asyncpg.Connection, session_id: UUID, speaker: str, text: str, seq: int):
    await conn.execute(
        "insert into utterances (session_id, speaker, transcript, sequence_no) "
        "values ($1, $2, $3, $4)",
        session_id,
        speaker,
        text,
        seq,
    )


_CLAIM_ONE_SQL = """
update analysis_jobs
   set status = 'running',
       locked_by = $3,
       locked_at = now(),
       attempts = attempts + 1
 where id = (
       select id from analysis_jobs
        where job_type = $1 and session_id = $2 and status = 'pending'
        limit 1
       )
returning id, job_type, utterance_id, session_id, attempts
"""


async def _claim_for(conn: asyncpg.Connection, session_id: UUID) -> ClaimedJob:
    """⛔ **그 세션의 job 만** claim 한다 — `claim_next` 를 쓰지 않는다.

    `db_pool` 은 커밋되는 픽스처라 앞 테스트가 남긴 job 이 큐에 그대로 있고, `claim_next` 는
    「다음 실행 가능한 job」을 집으므로 **남의 것을 집는다.** 실제로 그렇게 해서 발화를 넣은
    테스트에서 「전사문이 비었다」가 나왔다 — 다른 세션의 job 을 처리한 것이다.
    ⚠️ 이 헬퍼는 큐 로직을 재지 않는다(그것은 `claim_next` 의 테스트가 잰다). 여기서는
    `process_scenario` 하나만 재려고 대상을 고정한다.
    """
    token = uuid4().hex
    row = await conn.fetchrow(_CLAIM_ONE_SQL, JOB_TYPE_GENERATE_SCENARIO, session_id, token)
    assert row is not None, f"세션 {session_id} 의 무대 생성 job 이 큐에 없다"
    return ClaimedJob(
        id=row["id"],
        job_type=row["job_type"],
        utterance_id=row["utterance_id"],
        session_id=row["session_id"],
        lease_token=token,
        attempts=row["attempts"],
    )


async def _scenario_jobs(conn: asyncpg.Connection, session_id: UUID) -> int:
    return await conn.fetchval(
        "select count(*) from analysis_jobs where job_type = $1 and session_id = $2",
        JOB_TYPE_GENERATE_SCENARIO,
        session_id,
    )


async def _generated_rows(conn: asyncpg.Connection, title: str) -> list[asyncpg.Record]:
    return await conn.fetch(
        "select category, level, title, source from learning_scenarios "
        "where source = 'generated' and title = $1",
        title,
    )


async def _last_error(conn: asyncpg.Connection, job_id: UUID) -> str | None:
    return await conn.fetchval("select last_error from analysis_jobs where id = $1", job_id)


@pytest.mark.asyncio
async def test_intake_session_end_enqueues_the_generate_job(db_pool: asyncpg.Pool):
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
    session_id = await create_session(db_pool, user_id, mode=SCENARIO_INTAKE_MODE)
    async with db_pool.acquire() as conn:
        await end_session(conn, session_id, "completed")
        assert await _scenario_jobs(conn, session_id) == 1


@pytest.mark.asyncio
async def test_a_normal_session_end_does_not_enqueue_it(db_pool: asyncpg.Pool):
    """⛔ 판별력 — 위 테스트만 있으면 «늘 거는» 구현도 통과한다."""
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
    session_id = await create_session(db_pool, user_id)  # 기본 `speaking`
    async with db_pool.acquire() as conn:
        await end_session(conn, session_id, "completed")
        assert await _scenario_jobs(conn, session_id) == 0, (
            "일반 세션에도 무대 생성 job 이 걸렸다 — mode 판정이 걸리지 않았다"
        )


@pytest.mark.asyncio
async def test_stores_one_generated_stage_with_the_users_level(db_pool: asyncpg.Pool):
    """정상 경로. ⛔ `level` 은 `users.current_level` 이고 모델이 준 값이 아니다(AC#3)."""
    title = _TITLES["stored"]
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn, level="B1")
        await _seed_one_stage(conn)
    session_id = await create_session(db_pool, user_id, mode=SCENARIO_INTAKE_MODE)
    async with db_pool.acquire() as conn:
        before = len(await _generated_rows(conn, title))
        await _say(conn, session_id, "agent", "Where do you need English soon?", 1)
        await _say(conn, session_id, "user", "A meeting with my manager next week.", 2)
        await end_session(conn, session_id, "completed")
        job = await _claim_for(conn, session_id)

    assert job.job_type == JOB_TYPE_GENERATE_SCENARIO
    # 모델이 지어낸 `level`·`source` 를 함께 보낸다 — 무시돼야 한다.
    claude = _StubClaude(_reply(title, level="C2", source="seed"))
    await process_scenario(db_pool, claude, job)  # type: ignore[arg-type]

    async with db_pool.acquire() as conn:
        rows = await _generated_rows(conn, title)
    assert len(rows) == before + 1, "무대가 저장되지 않았다"
    assert rows[-1]["level"] == "B1", "모델이 준 level 이 저장됐다 — 호출자가 정해야 한다"
    assert rows[-1]["category"] == "business"
    assert rows[-1]["source"] == "generated"
    assert claude.purposes == ["generate_scenario"], "사용량 귀속이 빠졌다"


@pytest.mark.asyncio
async def test_a_session_without_utterances_fails_with_a_readable_reason(db_pool: asyncpg.Pool):
    """전사문이 비면 저장 0행 · 사유에 「재시도해도 같다」가 남는다."""
    title = _TITLES["empty"]
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
        await _seed_one_stage(conn)
    session_id = await create_session(db_pool, user_id, mode=SCENARIO_INTAKE_MODE)
    async with db_pool.acquire() as conn:
        await end_session(conn, session_id, "completed")
        job = await _claim_for(conn, session_id)

    claude = _StubClaude(_reply(title))
    await process_scenario(db_pool, claude, job)  # type: ignore[arg-type]

    async with db_pool.acquire() as conn:
        rows = await _generated_rows(conn, title)
        last_error = await _last_error(conn, job.id)
    assert rows == []
    assert claude.prompts == [], "전사문이 비었는데 Claude 를 불렀다 — 토큰을 헛태운다"
    assert last_error is not None and "재시도해도" in last_error


@pytest.mark.asyncio
async def test_a_rejected_draft_stores_nothing_and_records_the_reason(db_pool: asyncpg.Pool):
    """파서가 거부하면 저장 0행 · `last_error` 에 사유."""
    title = _TITLES["rejected"]
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
        await _seed_one_stage(conn)
    session_id = await create_session(db_pool, user_id, mode=SCENARIO_INTAKE_MODE)
    async with db_pool.acquire() as conn:
        await _say(conn, session_id, "user", "A meeting with my manager.", 1)
        await end_session(conn, session_id, "completed")
        job = await _claim_for(conn, session_id)

    # 무대가 질문이다 — 캡틴 결정 14 가 금지한 형태.
    claude = _StubClaude(_reply(title, prompt_template="What do you do at work?"))
    await process_scenario(db_pool, claude, job)  # type: ignore[arg-type]

    async with db_pool.acquire() as conn:
        rows = await _generated_rows(conn, title)
        last_error = await _last_error(conn, job.id)
    assert rows == []
    assert last_error is not None and "ScenarioValidationError" in last_error


@pytest.mark.asyncio
async def test_the_seed_category_domain_is_what_the_model_sees(db_pool: asyncpg.Pool):
    """⛔ 값역은 「시드에 실재하는 계열」이다 — `shadowing` 은 학습 방식이라 새지 않는다.

    ⚠️ `shadowing` 행을 `source='generated'` 로 심어 둔다. 값역 쿼리가 `source='seed'` 로
    좁히지 않으면 그 계열이 프롬프트에 새고, 그러면 모델이 「쉐도잉 무대」를 만든다.
    """
    title = _TITLES["domain"]
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
        await _seed_one_stage(conn, category="travel")
        await conn.execute(
            "insert into learning_scenarios (category, level, title, prompt_template, source) "
            "values ('shadowing', 'A2', $1, 'You are someone.', 'generated')",
            f"a clip {uuid4().hex[:8]}",
        )
    session_id = await create_session(db_pool, user_id, mode=SCENARIO_INTAKE_MODE)
    async with db_pool.acquire() as conn:
        await _say(conn, session_id, "user", "I travel next month.", 1)
        await end_session(conn, session_id, "completed")
        job = await _claim_for(conn, session_id)

    claude = _StubClaude(_reply(title, category="travel"))
    await process_scenario(db_pool, claude, job)  # type: ignore[arg-type]

    assert len(claude.prompts) == 1
    assert "travel" in claude.prompts[0]
    assert "shadowing" not in claude.prompts[0], (
        "학습 방식 계열이 무대 값역으로 샜다 — 모델이 「쉐도잉 무대」를 만든다"
    )


@pytest.mark.asyncio
async def test_a_duplicate_title_is_rejected(db_pool: asyncpg.Pool):
    """이미 같은 무대가 있으면 거부한다 — 공백·대소문자만 다른 것도 같다."""
    title = _TITLES["dup"]
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
        await _seed_one_stage(conn)
        await conn.execute(
            "insert into learning_scenarios (category, level, title, prompt_template, source) "
            "values ('business', 'A2', $1, 'You are someone.', 'generated')",
            title,
        )
    session_id = await create_session(db_pool, user_id, mode=SCENARIO_INTAKE_MODE)
    async with db_pool.acquire() as conn:
        await _say(conn, session_id, "user", "Same stage again.", 1)
        await end_session(conn, session_id, "completed")
        job = await _claim_for(conn, session_id)

    # 공백·대소문자만 다른 제목 — `normalize_title` 이 같게 본다.
    claude = _StubClaude(_reply(f"  {title.upper()}  "))
    await process_scenario(db_pool, claude, job)  # type: ignore[arg-type]

    async with db_pool.acquire() as conn:
        rows = await _generated_rows(conn, title)
        last_error = await _last_error(conn, job.id)
    assert len(rows) == 1, "중복 무대가 저장됐다"
    assert last_error is not None and "이미" in last_error


@pytest.mark.asyncio
async def test_a_job_without_a_session_target_fails_cleanly(db_pool: asyncpg.Pool):
    """대상이 없는 job 은 사유를 남기고 끝난다 — 예외를 올리지 않는다."""

    # ⚠️ 가짜 클래스를 쓰지 않고 **실제 `ClaimedJob`** 을 만든다 — `ty` 가 그 대체를 거부했고
    # (`Expected ClaimedJob, found _NoTarget`) 그 지적이 맞다. `session_id=None` 이 이 테스트가
    # 재려는 상태이고 그것은 실제 타입으로 표현할 수 있다.
    job = ClaimedJob(
        id=uuid4(),
        job_type=JOB_TYPE_GENERATE_SCENARIO,
        utterance_id=None,
        session_id=None,
        lease_token=uuid4().hex,
        attempts=1,
    )
    claude = _StubClaude(_reply("never used"))
    # ⛔ 예외가 올라오면 워커 루프가 죽는다 — 그것을 재는 것이 이 테스트다.
    await process_scenario(db_pool, claude, job)
    assert claude.prompts == []
