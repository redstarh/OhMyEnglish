"""`/ws/session` — 음성 세션 WebSocket (설계서 §5.3).

이 파일은 **얇다**. 세션 규칙은 전부 `audio_gateway.session.SessionRunner`에 있고,
여기서는 두 가지만 한다: 연결이 곧 세션 하나라는 것을 DB 행으로 만들고, 게이트웨이의
이벤트를 JSON 프레임으로 옮긴다.

프로토콜 (JSON 객체):

* 서버→클라이언트: `session_started`(session_id) · `partial` · `final`(speaker,
  sequence_no) · `audio`(base64) · `session_failed`(reason) · `session_ended`
* 클라이언트→서버: `{"type":"audio","data":<base64>}` · `{"type":"end_session"}`

어떤 음성 구현이 붙는지 이 모듈은 모른다 — 팩토리에서 주입받는다 (G3).
"""

from __future__ import annotations

import contextlib
import json
import logging
from uuid import UUID

import asyncpg
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.audio_gateway.factory import create_voice_adapter
from app.audio_gateway.session import SessionRunner
from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter()

WS_SESSION_PATH = "/ws/session"

# 단일 사용자 로컬 도구다(설계서 §2) — 인증 계층이 없어 연결의 주인이 고정이다.
# 값은 시드가 만드는 사용자 id와 같다(`scripts/migrate.py`의 `USER_ID`). 시드
# 스크립트는 앱 패키지를 import하지 않는 독립 ops 스크립트라 상수를 공유하지 못한다.
FIXED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

# 시나리오는 시드된 첫 행에 붙인다 — 첫 슬라이스에는 추천 로직이 없고(YAGNI),
# 어떤 질문 세트로 대화했는지 결과가 참조할 수 있도록 연결만 해둔다. 시드가 없으면
# `scenario_id`는 null로 남고(컬럼 nullable) 세션은 그대로 진행된다.
_CREATE_SESSION_SQL = """
insert into learning_sessions (user_id, scenario_id, mode)
values ($1, (select id from learning_scenarios order by created_at, id limit 1), 'speaking')
returning id
"""


async def create_session(pool: asyncpg.Pool) -> UUID:
    """연결 하나에 대응하는 `active` 세션 행을 만든다."""
    async with pool.acquire() as conn:
        session_id = await conn.fetchval(_CREATE_SESSION_SQL, FIXED_USER_ID)
    assert session_id is not None, "insert ... returning produced no row"
    return session_id


class WebSocketChannel:
    """`session.ClientChannel`을 starlette WebSocket 위에 얹은 어댑터.

    끊긴 소켓에 보내는 것은 **오류가 아니다** — 클라이언트가 먼저 떠난 뒤에도
    게이트웨이는 종료 절차(어댑터 close·세션 기록)를 끝내야 하므로, 방송 실패가
    그 절차를 중단시켜선 안 된다.
    """

    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def send_event(self, event: dict[str, object]) -> None:
        try:
            await self._websocket.send_json(event)
        except (RuntimeError, WebSocketDisconnect):
            # RuntimeError = close 이후의 send, WebSocketDisconnect = 전송 중 끊김.
            logger.debug("이미 닫힌 소켓에 %r을 보내려 했다 — 무시한다", event.get("type"))

    async def receive_event(self) -> dict[str, object] | None:
        """클라이언트 프레임을 JSON 객체로 돌려준다. 연결이 끝나면 `None`.

        해석할 수 없는 프레임(텍스트 아님/JSON 아님/객체 아님)은 빈 dict로 돌려
        러너가 "알 수 없는 메시지"로 무시하게 한다 — 프레임 하나가 깨졌다고 대화를
        끊지 않는다. `None`은 오직 "연결 종료"만 뜻한다.
        """
        try:
            message = await self._websocket.receive()
        except RuntimeError:
            # 이미 disconnect를 받은 뒤의 receive — 연결은 끝났다.
            return None
        if message["type"] == "websocket.disconnect":
            return None
        text = message.get("text")
        if text is None:
            logger.warning("텍스트가 아닌 프레임을 무시했다")
            return {}
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("JSON으로 해석할 수 없는 프레임을 무시했다")
            return {}
        if not isinstance(payload, dict):
            logger.warning("JSON 객체가 아닌 프레임을 무시했다")
            return {}
        return payload


@router.websocket(WS_SESSION_PATH)
async def session_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    channel = WebSocketChannel(websocket)
    pool: asyncpg.Pool = websocket.app.state.db_pool

    try:
        session_id = await create_session(pool)
    except asyncpg.PostgresError:
        # 시드가 없으면(고정 사용자 부재) 여기서 걸린다 — 연결을 조용히 매달아두지
        # 않고 실패를 알린 뒤 닫는다.
        logger.exception("세션 행을 만들 수 없어 연결을 닫는다")
        await channel.send_event({"type": "session_failed", "reason": "session_create_failed"})
        with contextlib.suppress(RuntimeError):
            await websocket.close()
        return

    runner = SessionRunner(create_voice_adapter(get_settings()), pool, session_id, client=channel)
    try:
        await runner.run()
    except Exception:
        # 세션 하나의 사고가 소켓을 close 프레임 없이 끊게 두지 않는다.
        logger.exception("세션 %s가 예외로 끝났다", session_id)
    finally:
        with contextlib.suppress(RuntimeError):
            await websocket.close()
