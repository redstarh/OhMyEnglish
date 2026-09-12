"""`session_summary.process_summary` 와 그 배선 (`TASK-62` · 계획 Task 3).

⛔ **재는 것 가운데 둘이 판별력용이다.** 「세션이 끝나면 job 이 걸린다」만 재면 **특정 모드에만
거는 구현**도 통과하고, 「정상 응답이 저장된다」만 재면 **무엇을 넣어도 저장하는 구현**도 통과한다.
반대 경우를 함께 잰다.

⚠️ 이 파일은 `db_pool`(커밋되는 픽스처)을 쓴다 — `create_session`·`end_session` 이 pool 을 받고
job 등록이 세션 종료와 **한 트랜잭션**이어야 하므로 롤백 픽스처로는 그 결합을 잴 수 없다.

⛔⛔ **`db_pool` 은 아무것도 정리하지 않는다 — 손으로 지운다.** 순서가 중요하다: **사용자를 먼저**
지워야 세션·발화·job 이 cascade 된다. 표지(`_MARK`)로 좁혀 **남의 행을 건드리지 않는다** —
`test_scenario_generation.py` 가 그 정리를 빠뜨려 다른 테스트 7개를 깨뜨린 선례가 있다.
"""

from __future__ import annotations

import json
from typing import cast
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio

from app.models.session_summary import EMPTY_SUMMARY, MAX_POINTS
from app.services.jobs import JOB_TYPE_SUMMARIZE, ClaimedJob
from app.services.session_summary import process_summary
from app.services.sessions import SCENARIO_INTAKE_MODE, create_session, end_session

# 이 모듈이 만든 행의 표지. ⛔ 정리가 이 값에 걸리므로 다른 파일과 겹치지 않는 이름이어야 한다.
_MARK = "summary-job-test"


def _reply(**overrides: object) -> str:
    body: dict[str, object] = {
        "went_well": ["관사를 붙인 문장이 여러 번 나왔어요."],
        "weak_points": [{"point": "문장이 길어지면 관사를 빼먹어요.", "quote": "I sent report."}],
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


class _StubClaude:
    """고정 응답을 돌려주는 대역.

    ⛔ **단정을 여기서 하지 않는다** — `process_summary` 의 broad `except` 가 `AssertionError` 를
    삼켜 「저장 실패」로 잘못 보고한다. 관측만 하고 판정은 테스트 본문에서 한다.
    """

    def __init__(self, response: str) -> None:
        self._response = response
        self.prompts: list[str] = []
        self.purposes: list[str | None] = []

    async def analyze(self, prompt: str, **kwargs: object) -> str:
        self.prompts.append(prompt)
        purpose = kwargs.get("purpose")
        self.purposes.append(purpose if isinstance(purpose, str) else None)
        return self._response


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_committed_rows(db_pool: asyncpg.Pool):
    """이 모듈이 커밋한 행을 지운다 — 사용자를 먼저 지워 나머지를 cascade 시킨다."""
    yield
    async with db_pool.acquire() as conn:
        await conn.execute("delete from users where display_name = $1", _MARK)


async def _fresh_user(conn: asyncpg.Connection, *, level: str = "A2") -> UUID:
    return await conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ($1, 'Asia/Seoul', $2) returning id",
        _MARK,
        level,
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

    `db_pool` 은 커밋되는 픽스처라 앞 테스트가 남긴 job 이 큐에 그대로 있고 `claim_next` 는
    「다음 실행 가능한 job」을 집으므로 **남의 것을 집는다**(그 실패가 선례에서 실제로 났다).
    """
    token = uuid4().hex
    row = await conn.fetchrow(_CLAIM_ONE_SQL, JOB_TYPE_SUMMARIZE, session_id, token)
    assert row is not None, f"세션 {session_id} 의 총평 job 이 큐에 없다"
    return ClaimedJob(
        id=row["id"],
        job_type=row["job_type"],
        utterance_id=row["utterance_id"],
        session_id=row["session_id"],
        lease_token=token,
        attempts=row["attempts"],
    )


async def _summary_jobs(conn: asyncpg.Connection, session_id: UUID) -> int:
    return await conn.fetchval(
        "select count(*) from analysis_jobs where job_type = $1 and session_id = $2",
        JOB_TYPE_SUMMARIZE,
        session_id,
    )


async def _stored(conn: asyncpg.Connection, session_id: UUID) -> dict[str, object]:
    raw = await conn.fetchval("select summary from learning_sessions where id = $1", session_id)
    return json.loads(raw) if isinstance(raw, str) else raw


async def _job_row(conn: asyncpg.Connection, job_id: UUID) -> asyncpg.Record:
    return await conn.fetchrow(
        "select status, attempts, last_error from analysis_jobs where id = $1", job_id
    )


@pytest.mark.asyncio
async def test_a_finished_session_enqueues_the_summary_job(db_pool: asyncpg.Pool):
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
    session_id = await create_session(db_pool, user_id)
    async with db_pool.acquire() as conn:
        await end_session(conn, session_id, "completed")
        assert await _summary_jobs(conn, session_id) == 1


@pytest.mark.asyncio
async def test_it_is_enqueued_for_every_mode_not_only_intake(db_pool: asyncpg.Pool):
    """⛔ 판별력 — 총평은 **모드 조건이 없다**.

    `generate_scenario` 는 `mode='scenario_intake'` 일 때만 걸린다. 그 형태를 베껴 조건을 붙이면
    「말하기 세션에는 총평이 없다」가 되는데 그것은 요구가 아니다(§4.3 은 *"세션 종료 후"* 다).
    ⚠️ 위 테스트만 있으면 **조건을 붙인 구현도 통과한다** — 그 세션이 기본 모드이기 때문이다.
    """
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
    intake_id = await create_session(db_pool, user_id)
    async with db_pool.acquire() as conn:
        await conn.execute(
            "update learning_sessions set mode = $2 where id = $1", intake_id, SCENARIO_INTAKE_MODE
        )
    async with db_pool.acquire() as conn:
        await end_session(conn, intake_id, "completed")
        assert await _summary_jobs(conn, intake_id) == 1, "무대 정하기 세션에도 총평이 걸려야 한다"


@pytest.mark.asyncio
async def test_stores_the_two_sections_and_completes(db_pool: asyncpg.Pool):
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
    session_id = await create_session(db_pool, user_id)
    async with db_pool.acquire() as conn:
        await _say(conn, session_id, "user", "I go to gym yesterday.", 1)
        await _say(conn, session_id, "agent", "Try: I went to the gym yesterday.", 2)
        await end_session(conn, session_id, "completed")

    claude = _StubClaude(_reply())
    async with db_pool.acquire() as conn:
        job = await _claim_for(conn, session_id)
    await process_summary(db_pool, claude, job)  # type: ignore[arg-type]

    async with db_pool.acquire() as conn:
        stored = await _stored(conn, session_id)
        row = await _job_row(conn, job.id)
    assert stored["went_well"] == ["관사를 붙인 문장이 여러 번 나왔어요."]
    # ⚠️ `dict[str, object]` 의 값을 바로 subscript 하면 `ty` 가 막는다(`H-AV` 의 그 진단) —
    # 외부 JSON 을 좁힐 때는 `cast` 를 쓴다.
    points = cast(list[dict[str, str]], stored["weak_points"])
    assert points[0]["quote"] == "I sent report."
    assert row["status"] == "done", f"last_error={row['last_error']}"
    # AC#4 — 총평 생성도 돈이 나가는 호출이다. ⚠️ 그 값은 021 이 값역에 넣은 이름과 같아야 한다.
    assert claude.purposes == ["summarize_session"]


@pytest.mark.asyncio
async def test_a_session_without_utterances_completes_without_calling_the_model(
    db_pool: asyncpg.Pool,
):
    """⛔ 이 갈래가 이웃 job 과 일부러 다른 자리다(설계서 §4).

    연결만 하고 끊은 세션이 흔하므로 `report_failure` 로 보내면 5회 헛돌고 대시보드에 `failed` 가
    상시 쌓인다. ⇒ **모델을 부르지 않고** 빈 배열 둘을 써서 `done` 으로 닫는다 — 그 값이
    「만들었고 담을 것이 없었다」로 읽힌다(`{}` 는 「아직 없음」이다).
    """
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
    session_id = await create_session(db_pool, user_id)
    async with db_pool.acquire() as conn:
        await end_session(conn, session_id, "completed")

    claude = _StubClaude(_reply())
    async with db_pool.acquire() as conn:
        job = await _claim_for(conn, session_id)
    await process_summary(db_pool, claude, job)  # type: ignore[arg-type]

    async with db_pool.acquire() as conn:
        stored = await _stored(conn, session_id)
        row = await _job_row(conn, job.id)
    assert claude.prompts == [], "발화가 0건인데 모델을 불렀다 — 토큰이 헛나간다"
    assert stored == EMPTY_SUMMARY
    assert row["status"] == "done", f"last_error={row['last_error']}"


@pytest.mark.asyncio
async def test_a_rejected_reply_stores_nothing_and_records_the_reason(db_pool: asyncpg.Pool):
    """⛔ 판별력 — 반쯤 검증된 총평을 저장하지 않는다.

    거부는 job 실패이고 학습 기록은 그대로 남는다. ⚠️ `summary` 가 `{}` 로 남는 것이 계약이다 —
    빈 배열을 쓰면 「만들었고 담을 것이 없었다」가 되어 거짓이 된다.
    """
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
    session_id = await create_session(db_pool, user_id)
    async with db_pool.acquire() as conn:
        await _say(conn, session_id, "user", "I go to gym yesterday.", 1)
        await end_session(conn, session_id, "completed")

    claude = _StubClaude(_reply(score=88))
    async with db_pool.acquire() as conn:
        job = await _claim_for(conn, session_id)
    await process_summary(db_pool, claude, job)  # type: ignore[arg-type]

    async with db_pool.acquire() as conn:
        stored = await _stored(conn, session_id)
        row = await _job_row(conn, job.id)
    assert stored == {}, "거부됐는데 무언가 저장됐다"
    assert row["status"] != "done"
    assert row["last_error"] is not None and "정의되지 않은 키" in row["last_error"]


@pytest.mark.asyncio
async def test_the_prompt_carries_the_transcript_and_the_cap(db_pool: asyncpg.Pool):
    """조립된 프롬프트가 **그 세션의** 전사문을 담는지 잰다 — 배선이 끊기면 빈 세션처럼 보인다."""
    async with db_pool.acquire() as conn:
        user_id = await _fresh_user(conn)
    session_id = await create_session(db_pool, user_id)
    async with db_pool.acquire() as conn:
        await _say(conn, session_id, "user", "I need english for my report.", 1)
        await end_session(conn, session_id, "completed")

    claude = _StubClaude(_reply())
    async with db_pool.acquire() as conn:
        job = await _claim_for(conn, session_id)
    await process_summary(db_pool, claude, job)  # type: ignore[arg-type]

    assert len(claude.prompts) == 1
    assert "I need english for my report." in claude.prompts[0]
    assert str(MAX_POINTS) in claude.prompts[0]


@pytest.mark.asyncio
async def test_a_job_without_a_session_target_fails_readably(db_pool: asyncpg.Pool):
    """⛔ `session_id` 가 없는 job 은 대상을 읽을 수 없다 — 조용히 통과시키지 않는다."""
    claude = _StubClaude(_reply())
    job = ClaimedJob(
        id=uuid4(),
        job_type=JOB_TYPE_SUMMARIZE,
        utterance_id=None,
        session_id=None,
        lease_token=uuid4().hex,
        attempts=1,
    )
    await process_summary(db_pool, claude, job)  # type: ignore[arg-type]

    assert claude.prompts == [], "대상이 없는데 모델을 불렀다"
