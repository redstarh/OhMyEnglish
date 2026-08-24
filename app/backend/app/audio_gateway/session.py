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
4. **연결 실패는 통보된다**(G2). `start()`가 상한 안에 응답하지 않거나 예외로
   실패하면 세션을 `failed`로 닫고 클라이언트에 알린다 — 어느 쪽이든 통보가 없으면
   사용자는 아무 신호 없이 매달리고, 세션은 `active` 고아로 남아 결과 화면이
   "연결 실패"를 표시할 근거를 잃는다.

어떤 어댑터 구현이 붙는지 이 모듈은 모른다 (G3). 주입만 받는다.
"""

from __future__ import annotations

import asyncio
import base64
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

# 설계 발명값 (근거 문서 없음) — 종료 신호 후 어댑터 스트림을 비우는 상한.
# 사용자가 말을 마치고 종료를 누른 순간 마지막 발화의 final은 아직 오는 중이다.
# "직전 발화의 전사문이 도착할 만한 시간이지만 종료 버튼이 먹지 않는다고 느끼기
# 전"으로 정했다. 테스트는 주입으로 줄인다.
DRAIN_TIMEOUT = 1.0

CONNECT_TIMEOUT_REASON = "voice_adapter_connect_timeout"
CONNECT_ERROR_REASON = "voice_adapter_connect_failed"

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
        drain_timeout: float = DRAIN_TIMEOUT,
    ) -> None:
        self._adapter = adapter
        self._pool = pool
        self._session_id = session_id
        self._client = client
        self._connect_timeout = connect_timeout
        self._drain_timeout = drain_timeout
        # shield로 보호한 저장 태스크들. 종료 기록 전에 이들을 기다려 전사문이
        # 세션 종료 뒤에 도착하는 역전을 막는다.
        self._pending_saves: set[asyncio.Task[None]] = set()

    async def run(self) -> None:
        """세션 하나를 끝까지 수행한다. 반환 시점에 세션은 DB에서 닫혀 있다."""
        await self._send({"type": "session_started", "session_id": str(self._session_id)})

        failure_reason = await self._connect()
        if failure_reason is not None:
            await self._close_and_record("failed")
            await self._send({"type": "session_failed", "reason": failure_reason})
            return

        try:
            await self._relay()
        finally:
            # 릴레이가 예외로 끝나도 세션은 닫는다 — `active`로 남은 세션은
            # 종료 시각이 없어 결과 화면에서 영원히 진행 중처럼 보인다.
            await self._close_and_record("completed")
        await self._send({"type": "session_ended", "session_id": str(self._session_id)})

    async def _connect(self) -> str | None:
        """연결을 수립한다. 실패하면 클라이언트에 보낼 reason을, 성공하면 `None`.

        타임아웃과 예외를 **모두** 실패로 취급한다: 무응답만 막으면 권한 거부·
        핸드셰이크 거절(Phase 2 실물 어댑터의 실패 모양)이 그대로 새어나가 세션을
        `active` 고아로 남긴다.
        """
        try:
            await asyncio.wait_for(self._adapter.start(), self._connect_timeout)
        except TimeoutError:
            logger.warning(
                "음성 어댑터 연결이 %.1f초 안에 수립되지 않았다 — 세션 %s를 failed로 닫는다",
                self._connect_timeout,
                self._session_id,
            )
            return CONNECT_TIMEOUT_REASON
        except Exception:
            logger.exception(
                "음성 어댑터 연결이 실패했다 — 세션 %s를 failed로 닫는다", self._session_id
            )
            return CONNECT_ERROR_REASON
        return None

    async def _close_and_record(self, status: SessionEndStatus) -> None:
        """G1: 어댑터를 먼저 닫고, 그 다음에 세션 종료를 기록한다.

        close가 실패해도 기록은 남긴다 — 자원 정리 실패 때문에 세션이 영원히
        `active`로 남는 편이 더 나쁘다. 진행 중인 저장은 그 전에 기다린다.
        """
        await self._await_pending_saves()
        try:
            await self._adapter.close()
        except Exception:
            logger.exception("어댑터 close가 실패했다 (세션 %s)", self._session_id)
        finally:
            await mark_session_ended(self._pool, self._session_id, status)

    async def _await_pending_saves(self) -> None:
        """shield된 저장이 끝나기를 기다린다 — 기다리지 않으면 전사문이 세션 종료
        시각보다 늦게 커밋된다.

        상한은 주입값이 아니라 상수 `DRAIN_TIMEOUT`이다: 저장 하나는 짧은 트랜잭션
        하나라 테스트가 이 값을 줄일 이유가 없고(드레인 데드라인과 달리 대기가
        시나리오의 일부가 아니다), 줄이면 "드레인 마감 직후 저장 중"인 상태를
        재현할 수 없다. 상한을 넘기면 gather 취소가 저장을 끊지만, 그건 저장이
        1초 넘게 걸리는 병리 상황에 대한 마지막 방어선이다.
        """
        if not self._pending_saves:
            return
        saves = asyncio.gather(*self._pending_saves, return_exceptions=True)
        try:
            await asyncio.wait_for(saves, DRAIN_TIMEOUT)
        except TimeoutError:
            logger.warning("전사문 저장이 %.1f초 안에 끝나지 않았다", DRAIN_TIMEOUT)

    async def _relay(self) -> None:
        """어댑터→클라이언트와 클라이언트→어댑터를 동시에 흘리고, **먼저 끝나는
        쪽**에서 세션을 마친다: 어댑터 스트림 소진(대화 종료) 또는 클라이언트의
        `end_session`/연결 종료.

        종료 신호가 먼저 온 경우에는 어댑터 스트림을 즉시 끊지 않고 **데드라인까지
        비운다**: 사용자가 말을 마치고 종료를 누른 순간 마지막 발화의 final은 아직
        오는 중이고, 그것을 버리면 발화 하나가 전사문·분석에서 통째로 사라진다.
        데드라인이 지나면 취소한다 — 어댑터가 스트림을 닫지 않아도 세션은 끝난다.
        """
        events = asyncio.create_task(self._pump_adapter_events(), name="adapter-events")
        client = asyncio.create_task(self._pump_client_messages(), name="client-messages")
        try:
            await asyncio.wait({events, client}, return_when=asyncio.FIRST_COMPLETED)
            if not events.done():
                with contextlib.suppress(TimeoutError, asyncio.CancelledError):
                    await asyncio.wait_for(events, self._drain_timeout)
        finally:
            for task in (events, client):
                if not task.done():
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
        for task in (events, client):
            if not task.cancelled():
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
        """final을 저장한다 — **취소가 저장을 찢지 못하게** shield로 감싼다.

        드레인 데드라인이 만료돼 펌프가 취소될 때 저장이 진행 중이면, shield가 없으면
        `save_final_transcript`의 트랜잭션 중간에서 취소가 터진다: 전사문은 롤백되고
        (분석 job도 함께) 그 발화는 흔적 없이 사라진다. 시작한 저장은 끝까지 간다.
        """
        if not event.text.strip():
            logger.warning("빈 final 전사문을 버렸다 (세션 %s)", self._session_id)
            return
        save = asyncio.create_task(self._save_final(event), name="save-final")
        self._pending_saves.add(save)
        save.add_done_callback(self._pending_saves.discard)
        await asyncio.shield(save)

    async def _save_final(self, event: TranscriptEvent) -> None:
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
            frame = base64.b64decode(data, validate=True)
        except ValueError:
            # `binascii.Error`(base64 알파벳 위반)와 순수 `ValueError`(비ASCII
            # 문자열 — b64decode가 ascii 인코딩에서 먼저 실패한다)를 함께 잡는다.
            # 전자만 잡으면 "한글" 한 프레임이 펌프를 죽여 세션이 끝난다.
            logger.warning("base64로 해석할 수 없는 오디오 프레임을 무시했다")
            return
        await self._adapter.send_audio(frame)

    async def _send(self, event: dict[str, object]) -> None:
        await self._client.send_event(event)
