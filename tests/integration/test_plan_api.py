"""Task 11 — `GET /api/sessions/next-plan` (`docs/PRD.md:189` R11-3, 설계서 §9 Contract).

화면이 "왜 이 연습인지"를 볼 수 있어야 한다는 요구사항의 조회 경로다. **이유 한 문장 +
오늘의 난이도만** 내려준다 — 초점 패턴·질문 목록은 계약에 없다(캡틴 결정 2026-09-04:
"간략하게 표시"). 질문을 미리 보여주면 학습자가 답을 준비해 즉흥 발화 연습이 무의미해진다.

`tests/unit/test_results.py`와 같은 배선을 쓴다(`api_client` — `tests/conftest.py`):
실서버를 띄우지 않고 ASGI 트랜스포트로 앱에 직접 붙는다. `db_conn`이 아니라 `db_pool`을
쓰는 이유도 같다 — 라우터가 여는 커넥션에는 롤백되는 트랜잭션의 쓰기가 보이지 않는다.

⚠️ 이 파일의 지배 규칙: 세 테스트가 **서로 다른 것**을 고정한다. 응답 전체를 dict 동일성으로
재므로 키가 빠지거나 늘면 걸린다 —
① 계획이 있을 때: 라우터가 그 행의 이유와 수준을 **DB에서** 옮긴다 (픽스처 기본값과 다른
   값으로 심어 상수 반환을 배제한다).
② 계획이 없을 때: 404 가 아니라 두 값이 `null` 이다 (§9 Contract).
③ 남의 계획만 있을 때: ①②를 둘 다 통과시키는 "사용자로 좁히지 않는 조회"를 여기서 잡는다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import asyncpg
import httpx
import pytest_asyncio

from app.api.ws import FIXED_USER_ID

# `asyncio_mode = "auto"`(pyproject.toml)라 `async def test_` 에 마커를 붙이지 않는다.

NEXT_PLAN_PATH = "/api/sessions/next-plan"


@pytest_asyncio.fixture
async def committed_fixed_user(db_pool: asyncpg.Pool) -> AsyncIterator[None]:
    """고정 사용자 1행을 **커밋**해두고 teardown 에서 지운다.

    라우터는 `FIXED_USER_ID`로 조회한다(단일 사용자 로컬 도구 — 인증 계층이 없다). 그래서
    그 사용자로 심어야 API 가 읽는다: `seed_plan_for_session`의 기본 동작인 "새 사용자를
    만든다"로는 이 경로를 재지 못한다.

    teardown 에서 사용자를 지우면 cascade 가 세션 → 계획을 걷어간다(007). 남기면 다른
    테스트가 깨진다 — `tests/unit/test_schema.py`가 `count(*) from users == 1`을 잰다.
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
