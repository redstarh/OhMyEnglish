"""세션 생성·종료 SQL 단일 소유 (설계서 §5.3, AC G1).

`api/ws.py`(생성)와 `audio_gateway/session.py`(종료)가 각자 들고 있던 두 문장을
여기 모은다 — 둘 다 `learning_sessions` 한 행의 생명주기 양끝일 뿐, 계층이
다르다고 SQL을 갈라 둘 이유가 없다.

* **생성**은 시나리오를 시드된 첫 행에 붙인다 — 첫 슬라이스에는 추천 로직이
  없고(YAGNI), 어떤 질문 세트로 대화했는지 결과가 참조할 수 있도록 연결만
  해둔다. 시드가 없으면 `scenario_id`는 null로 남고(컬럼 nullable) 세션은
  그대로 진행된다. 고정 사용자 id는 이 모듈이 알지 못한다 — 호출자(`api/ws.py`)가
  넘긴다: 단일 사용자 로컬 도구라는 사실은 API 계층의 관심사이고, 이 모듈은
  "누구의 세션인가"를 주입받기만 한다.
* **종료**는 `ended_at`과 `status`를 한 UPDATE로 묻는다 — 두 문장으로 갈라지면
  그 사이에 "끝났지만 active"인 상태가 관측된다. 시각은 DB 시계(timestamptz)로
  찍는다: 앱이 만든 naive datetime이 섞이는 경로를 아예 만들지 않는다.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

import asyncpg

SessionEndStatus = Literal["completed", "failed"]

_CREATE_SESSION_SQL = """
insert into learning_sessions (user_id, scenario_id, mode)
values ($1, (select id from learning_scenarios order by created_at, id limit 1), 'speaking')
returning id
"""

_END_SESSION_SQL = """
update learning_sessions
   set status = $2,
       ended_at = now()
 where id = $1
"""


async def create_session(pool: asyncpg.Pool, user_id: UUID) -> UUID:
    """연결 하나에 대응하는 `active` 세션 행을 만든다."""
    async with pool.acquire() as conn:
        session_id = await conn.fetchval(_CREATE_SESSION_SQL, user_id)
    assert session_id is not None, "insert ... returning produced no row"
    return session_id


async def mark_session_ended(
    pool: asyncpg.Pool, session_id: UUID, status: SessionEndStatus
) -> None:
    """세션 종료를 기록한다 — `ended_at` + `status`를 한 UPDATE로."""
    async with pool.acquire() as conn:
        await conn.execute(_END_SESSION_SQL, session_id, status)
