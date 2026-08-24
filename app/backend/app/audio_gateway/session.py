"""세션 수명주기 (설계서 §5.3, AC G1·G2) — 어댑터 이벤트와 DB·클라이언트 사이의 규칙.

이 모듈이 지키는 계약 넷:

1. **final만 저장한다.** `partial`은 브로드캐스트만 하고 한 행도 남기지 않는다.
   partial은 같은 문장이 자라는 중간 상태라, 저장하면 한 발화가 여러 행으로 쪼개져
   `sequence_no`와 분석 job이 함께 오염된다. 저장은 `save_final_transcript`에
   맡기며 **트랜잭션을 감싸지 않는다** — 그 함수가 자기 트랜잭션을 열어 전사문과
   job의 원자성을 스스로 보장한다(§5.2).
2. **빈 final은 저장하지 않는다.** 어댑터가 만들지 않아야 하는 값이지만, 새어
   들어오면 분석 job이 붙은 빈 발화가 남아 워커가 빈 입력으로 Claude를 호출한다.
3. **종료 순서는 `close()` → 종료 기록**(G1). 반대로 하면 "종료됨"으로 기록된 뒤
   소켓이 살아 있는 창이 생기고, 그 사이 도착한 이벤트가 이미 닫힌 세션에 붙는다.
4. **연결에는 상한이 있다**(G2). `start()`가 응답하지 않으면 세션을 `failed`로
   닫고 클라이언트에 통보한다 — 상한이 없으면 사용자는 아무 신호 없이 매달린다.

어떤 어댑터 구현이 붙는지 이 모듈은 모른다 (G3). 주입만 받는다.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import contextlib
import logging
from typing import Literal, Protocol
from uuid import UUID

import asyncpg

from app.audio_gateway.port import TranscriptEvent, VoiceAdapter
from app.services.utterances import save_final_transcript

logger = logging.getLogger(__name__)

# 설계 발명값 (근거 문서 없음) — 음성 어댑터 연결 수립 상한. "느린 네트워크에서
# 한 번의 핸드셰이크는 끝낼 수 있지만, 사용자가 무반응을 장애로 인지하기 전"으로
# 정했다. 테스트는 이 값을 주입으로 줄여 실시간 대기 없이 실패 경로를 관측한다.
CONNECT_TIMEOUT = 10.0

CONNECT_FAILURE_REASON = "voice_adapter_connect_timeout"

SessionEndStatus = Literal["completed", "failed"]

# 종료는 한 UPDATE다 — `ended_at`과 `status`가 서로 다른 문장으로 갈라지면
# 그 사이에 "끝났지만 active"인 상태가 관측된다. 시각은 DB 시계(timestamptz)로
# 찍는다: 앱이 만든 naive datetime이 섞이는 경로를 아예 만들지 않는다.
_END_SESSION_SQL = """
update learning_sessions
   set status = $2,
       ended_at = now()
 where id = $1
"""


class ClientChannel(Protocol):
    """게이트웨이가 보는 클라이언트. WebSocket이라는 사실은 여기까지 오지 않는다.

    `send_event`는 **끊긴 클라이언트에서도 예외를 올리지 않는다** — 방송은
    세션 진행의 전제가 아니다. `receive_event`는 연결이 끝나면 `None`을 돌려준다.
    """

    async def send_event(self, event: dict[str, object]) -> None: ...

    async def receive_event(self) -> dict[str, object] | None: ...


async def mark_session_ended(
    pool: asyncpg.Pool, session_id: UUID, status: SessionEndStatus
) -> None:
    """세션 종료를 기록한다 — `ended_at` + `status`를 한 UPDATE로."""
    async with pool.acquire() as conn:
        await conn.execute(_END_SESSION_SQL, session_id, status)


class SessionRunner:
    """어댑터 이벤트를 소비해 저장·방송하고, 클라이언트 오디오를 어댑터로 릴레이한다."""

    def __init__(
        self,
        adapter: VoiceAdapter,
        pool: asyncpg.Pool,
        session_id: UUID,
        *,
        client: ClientChannel,
        connect_timeout: float = CONNECT_TIMEOUT,
    ) -> None:
        self._adapter = adapter
        self._pool = pool
        self._session_id = session_id
        self._client = client
        self._connect_timeout = connect_timeout

    async def run(self) -> None:
        """세션 하나를 끝까지 수행한다. 반환 시점에 세션은 DB에서 닫혀 있다."""
        await self._send({"type": "session_started", "session_id": str(self._session_id)})

        if not await self._connect():
            await self._close_and_record("failed")
            await self._send({"type": "session_failed", "reason": CONNECT_FAILURE_REASON})
            return

        try:
            await self._relay()
        finally:
            # 릴레이가 예외로 끝나도 세션은 닫는다 — `active`로 남은 세션은
            # 종료 시각이 없어 결과 화면에서 영원히 진행 중처럼 보인다.
            await self._close_and_record("completed")
        await self._send({"type": "session_ended", "session_id": str(self._session_id)})

    async def _connect(self) -> bool:
        try:
            await asyncio.wait_for(self._adapter.start(), self._connect_timeout)
        except TimeoutError:
            logger.warning(
                "음성 어댑터 연결이 %.1f초 안에 수립되지 않았다 — 세션 %s를 failed로 닫는다",
                self._connect_timeout,
                self._session_id,
            )
            return False
        return True

    async def _close_and_record(self, status: SessionEndStatus) -> None:
        """G1: 어댑터를 먼저 닫고, 그 다음에 세션 종료를 기록한다.

        close가 실패해도 기록은 남긴다 — 자원 정리 실패 때문에 세션이 영원히
        `active`로 남는 편이 더 나쁘다.
        """
        try:
            await self._adapter.close()
        except Exception:
            logger.exception("어댑터 close가 실패했다 (세션 %s)", self._session_id)
        finally:
            await mark_session_ended(self._pool, self._session_id, status)

    async def _relay(self) -> None:
        """어댑터→클라이언트와 클라이언트→어댑터를 동시에 흘리고, **먼저 끝나는
        쪽**에서 세션을 마친다: 어댑터 스트림 소진(대화 종료) 또는 클라이언트의
        `end_session`/연결 종료. 남은 쪽은 취소한다 — 취소하지 않으면 상대가
        영원히 오지 않을 메시지를 기다린다.
        """
        pumps = {
            asyncio.create_task(self._pump_adapter_events(), name="adapter-events"),
            asyncio.create_task(self._pump_client_messages(), name="client-messages"),
        }
        done, pending = await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        for task in done:
            task.result()  # 펌프에서 터진 예외를 삼키지 않는다

    async def _pump_adapter_events(self) -> None:
        async for event in self._adapter.events():
            if isinstance(event, bytes):
                await self._send({"type": "audio", "data": base64.b64encode(event).decode("ascii")})
            elif event.kind == "partial":
                await self._send({"type": "partial", "text": event.text, "speaker": event.speaker})
            else:
                await self._store_final(event)

    async def _store_final(self, event: TranscriptEvent) -> None:
        if not event.text.strip():
            logger.warning("빈 final 전사문을 버렸다 (세션 %s)", self._session_id)
            return
        async with self._pool.acquire() as conn:
            utterance = await save_final_transcript(
                conn, self._session_id, event.text, speaker=event.speaker
            )
        # 방송하는 `sequence_no`는 DB가 부여한 값이다 — 어댑터가 보낸 번호가 아니라
        # 실제로 저장된 순번이라야 클라이언트가 결과 조회와 대조할 수 있다.
        await self._send(
            {
                "type": "final",
                "text": utterance.transcript,
                "speaker": utterance.speaker,
                "sequence_no": utterance.sequence_no,
            }
        )

    async def _pump_client_messages(self) -> None:
        while True:
            message = await self._client.receive_event()
            if message is None:
                logger.info("클라이언트 연결이 끊겼다 — 세션 %s를 닫는다", self._session_id)
                return
            message_type = message.get("type")
            if message_type == "end_session":
                return
            if message_type == "audio":
                await self._forward_audio(message.get("data"))
                continue
            logger.warning("알 수 없는 클라이언트 메시지를 무시했다: %r", message_type)

    async def _forward_audio(self, data: object) -> None:
        """base64 오디오 프레임을 어댑터로 넘긴다. 깨진 프레임은 세션을 죽이지
        않는다 — 마이크 한 조각을 잃는 것이 대화를 끊는 것보다 낫다."""
        if not isinstance(data, str):
            logger.warning("audio 메시지에 base64 data가 없다 — 무시한다")
            return
        try:
            # binascii.Error는 ValueError의 하위 타입이다.
            frame = base64.b64decode(data, validate=True)
        except binascii.Error:
            logger.warning("base64로 해석할 수 없는 오디오 프레임을 무시했다")
            return
        await self._adapter.send_audio(frame)

    async def _send(self, event: dict[str, object]) -> None:
        await self._client.send_event(event)
