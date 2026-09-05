"""Task 11 — `GET /api/sessions/next-plan` (`docs/PRD.md:189` R11-3, 설계서 §9 Contract).

화면이 "왜 이 연습인지"를 볼 수 있어야 한다는 요구사항의 조회 경로다. **이유 한 문장 +
오늘의 난이도만** 내려준다 — 초점 패턴·질문 목록은 계약에 없다(캡틴 결정 2026-09-04:
"간략하게 표시"). 질문을 미리 보여주면 학습자가 답을 준비해 즉흥 발화 연습이 무의미해진다.

`tests/unit/test_results.py`와 같은 배선을 쓴다(`api_client` — `tests/conftest.py`):
실서버를 띄우지 않고 ASGI 트랜스포트로 앱에 직접 붙는다. `db_conn`이 아니라 `db_pool`을
쓰는 이유도 같다 — 라우터가 여는 커넥션에는 롤백되는 트랜잭션의 쓰기가 보이지 않는다.

⚠️ 이 파일의 지배 규칙: 다섯 테스트가 **서로 다른 것**을 고정한다. 응답 전체를 dict
동일성으로 재므로 키가 빠지거나 늘면 걸린다 —
① 계획이 있을 때: 라우터가 그 행의 이유와 수준을 **DB에서** 옮긴다 (픽스처 기본값과 다른
   값으로 심어 상수 반환을 배제한다).
② 계획이 없을 때: 404 가 아니라 두 값이 `null` 이다 (§9 Contract).
③ 남의 계획만 있을 때: ①②를 둘 다 통과시키는 "사용자로 좁히지 않는 조회"를 여기서 잡는다.
④ 수준을 **지시문에서** 꺼낸다 — ①은 이것을 구분하지 못한다: `seed_plan_for_session`이
   `target_level` 인자 하나로 컬럼과 지시문을 **같은 값으로** 채우므로 어느 쪽을 읽어도
   통과한다. 두 값을 갈라 심는 것이 유일한 판별 수단이다.
⑤ 지시문을 읽을 수 없을 때: 행에 이유가 있어도 화면을 비운다 (`api/results.py`의 계약).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import uuid4

import asyncpg
import httpx
import pytest_asyncio
from conftest import plan_json

from app.api.ws import FIXED_USER_ID

# `asyncio_mode = "auto"`(pyproject.toml)라 `async def test_` 에 마커를 붙이지 않는다.

NEXT_PLAN_PATH = "/api/sessions/next-plan"


@pytest_asyncio.fixture
async def committed_fixed_user(db_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """고정 사용자 1행을 **커밋**해두고 teardown 에서 지운다.

    라우터는 `FIXED_USER_ID`로 조회한다(단일 사용자 로컬 도구 — 인증 계층이 없다). 그래서
    그 사용자로 심어야 API 가 읽는다: `seed_plan_for_session`의 기본 동작인 "새 사용자를
    만든다"로는 이 경로를 재지 못한다.

    teardown 에서 사용자를 지우면 cascade 가 세션 → 계획을 걷어간다(007). 남기면 **이 파일의
    "계획이 없다" 테스트들이 깨진다** — 커밋된 계획 행이 살아남아 그것들이 계획을 찾아낸다.

    ⚠️ **2026-09-06 정정 — 이 절이 지목한 피해자가 틀렸다.** 원래 "`tests/unit/test_schema.py`가
    `count(*) from users == 1`을 잰다"고 적었으나 **그 테스트는 깨지지 않는다**: 이 픽스처가 넣는
    값 `('Learner', 'Asia/Seoul', 기본 current_level='A2')`이 `scripts/migrate.py`의 시드값과
    **완전히 같고**, `migrate.USER_ID`가 `FIXED_USER_ID`와 **같은 UUID**이며, 시드가
    `on conflict (id) do nothing`이다 → 남은 행이 시드된 행과 구별되지 않아 `count`도 필드 단정도
    그대로 통과한다. **teardown 은 여전히 하중을 받는다 — 이유만 다르다.**
    `timezone`을 명시해 넣는 것은 `seed_user`와 같은 규약이다(LOW-14).
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into users (id, display_name, timezone) values ($1, 'Learner', 'Asia/Seoul') "
            "on conflict (id) do nothing",
            FIXED_USER_ID,
        )
    try:
        yield
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", FIXED_USER_ID)


# ① 계획이 있으면 이유와 목표 수준을 그 행에서 옮긴다.
# **픽스처 기본값(`reason` 기본 문구 · `target_level="A2"`)과 다른 값으로 심는다** — 기본값과
# 같은 값을 단정하면 상수를 돌려주는 구현도 통과한다.
async def test_next_plan_returns_reason_and_target_level(
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_fixed_user,
    seed_plan_for_session,
):
    reason = "관사를 계속 빼먹어서 오늘 그것만 봅니다"
    async with db_pool.acquire() as conn:
        await seed_plan_for_session(conn, user_id=FIXED_USER_ID, reason=reason, target_level="B1")

    response = await api_client.get(NEXT_PLAN_PATH)

    assert response.status_code == 200
    # 응답 **전체**를 잰다 — 초점 패턴·질문 목록이 끼어들면 여기서 걸린다.
    assert response.json() == {"reason": reason, "target_level": "B1"}


# ② 계획 부재는 오류가 아니다. 404 로 만들면 프론트가 그 자리를 비우는 대신 실패로 다뤄야
# 하고, "첫 세션"이 매번 오류로 보인다 (§9 Contract).
async def test_next_plan_returns_nulls_when_no_plan(
    api_client: httpx.AsyncClient, committed_fixed_user
):
    response = await api_client.get(NEXT_PLAN_PATH)

    assert response.status_code == 200
    assert response.json() == {"reason": None, "target_level": None}


# ③ 남의 계획을 화면에 올리지 않는다. 사용자 조건을 지운 조회(예: 최신 1행을 전역에서 고르는
# SQL)는 ①②를 둘 다 통과하므로 이 배치가 유일한 판별 수단이다.
async def test_next_plan_ignores_another_learners_plan(
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_fixed_user,
    seed_plan_for_session,
):
    async with db_pool.acquire() as conn:
        other_user_id, _ = await seed_plan_for_session(
            conn, reason="다른 학습자의 이유", target_level="C1"
        )
    try:
        response = await api_client.get(NEXT_PLAN_PATH)

        assert response.status_code == 200
        assert response.json() == {"reason": None, "target_level": None}
    finally:
        # 이 사용자는 `committed_fixed_user`가 걷어가지 않는다 — 남기면 다음 테스트의
        # 전역 `count(*)` 단정이 깨진다.
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", other_user_id)


# ④ 수준은 **지시문 안의 값**이다 — `session_plans.target_level` 컬럼이 아니다.
#
# ⚠️ 이 조합(컬럼 `B1` ≠ 지시문 `C1`)은 `process_plan` 경로에서 생기지 않는다: `PlanOutput`의
# `_target_level_matches_level_and_instruction`이 세 값의 일치를 저장 전에 강제한다. 그래서
# 이것은 "어느 값이 맞는가"를 다투는 테스트가 아니라 **읽는 지점이 어디인가**를 못 박는
# 테스트다. 지시문 쪽인 이유: 그 값이 대화 상대가 실제로 말하는 수준이고, 지시문을 읽을 수
# 없으면 세션이 그 계획을 아예 쓰지 않는다(⑤ — 그때 화면도 함께 비어야 짝이 맞는다).
# 컬럼으로 옮기는 수정(예: `_PREPARED_PLAN_SQL`에 컬럼을 더해 `prepared.target_level`을 쓰는
# 것)은 ①②③을 전부 통과하고 여기서만 걸린다.
async def test_next_plan_reads_target_level_from_the_instruction_not_the_column(
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_fixed_user,
    seed_plan_for_session,
):
    reason = "컬럼과 지시문의 수준을 갈라 심은 계획"
    # 지시문은 `plan_json`이 소유하는 유효한 모양에서 뽑는다 — 여기서 다시 적으면
    # `SessionInstruction` 계약이 바뀔 때 이 테스트만 낡는다.
    instruction = json.loads(plan_json(uuid4(), target_level="C1"))["instruction"]
    async with db_pool.acquire() as conn:
        await seed_plan_for_session(
            conn,
            user_id=FIXED_USER_ID,
            reason=reason,
            target_level="B1",
            instruction=json.dumps(instruction, ensure_ascii=False),
        )

    response = await api_client.get(NEXT_PLAN_PATH)

    assert response.status_code == 200
    assert response.json() == {"reason": reason, "target_level": "C1"}, (
        "컬럼(B1)을 읽었다 — 화면이 대화 상대가 말하지 않는 수준을 보여준다"
    )


# ⑤ 지시문을 읽을 수 없으면 **이유가 있어도** 화면을 비운다.
#
# `load_prepared_plan`이 그 행을 `None`으로 돌려주므로 세션은 고정 지시문으로 시작한다 —
# 그때 이유만 보여주면 화면은 오늘의 초점을 말하는데 대화 상대는 그 초점을 모른다.
# 그 층의 판정 자체는 `tests/unit/test_sessions.py`가 잰다(경고 로그까지). 여기서 재는 것은
# **API 응답 shape**다: "DB에 이유가 있는데 왜 비나"라는 그럴듯한 수정(부분 표시)이 없으면
# 게이트를 조용히 통과한다. 읽을 수 없는 지시문의 모양도 그 파일과 같은 것을 쓴다.
async def test_next_plan_stays_empty_when_the_instruction_cannot_be_read(
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_fixed_user,
    seed_plan_for_session,
):
    async with db_pool.acquire() as conn:
        await seed_plan_for_session(
            conn,
            user_id=FIXED_USER_ID,
            reason="읽을 수 없는 지시문을 가진 계획의 이유",
            instruction='"not an instruction object"',
        )

    response = await api_client.get(NEXT_PLAN_PATH)

    assert response.status_code == 200
    assert response.json() == {"reason": None, "target_level": None}
