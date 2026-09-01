"""세션 수명주기 (설계서 §5.3, AC G1·G2) — 어댑터 이벤트와 DB·클라이언트 사이의 규칙.

이 모듈이 지키는 계약 넷:

1. **final만 저장한다.** `partial`은 브로드캐스트만 하고 한 행도 남기지 않는다.
   partial은 같은 문장이 자라는 중간 상태라, 저장하면 한 발화가 여러 행으로 쪼개져
   `sequence_no`와 분석 job이 함께 오염된다. 저장은 `save_final_transcript`에
   맡기며 **트랜잭션을 감싸지 않는다** — 그 함수가 자기 트랜잭션을 열어 전사문
   insert(와 `sequence_no` 재시도)를 스스로 원자적으로 만든다(§5.2).
1a. **분석 job은 저장이 아니라 턴 경계에서 건다** (I-1). agent final을 저장한 직후와
   세션 종료 경로에서 `flush_pending_analysis`를 부르는 것이 이 모듈의 일이다 —
   규칙(무엇이 묶음인가)은 `services/utterances.py`가 소유하고 여기는 **언제**만 안다.
   저장 시점에 걸면 이르게 확정된 조각이 완전한 문장처럼 분석되어 오탐이 된다.
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
from typing import Protocol
from uuid import UUID

import asyncpg

from app.audio_gateway.port import (
    InterruptionEvent,
    PronunciationEvent,
    SpeechBoundaryEvent,
    TranscriptEvent,
    VoiceAdapter,
)
from app.services.pronunciation import note_transcript, record_attempt, resolve_dangling
from app.services.sessions import SessionEndStatus, end_session
from app.services.utterances import flush_pending_analysis, save_final_transcript

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


class ClientChannel(Protocol):
    """게이트웨이가 보는 클라이언트. WebSocket이라는 사실은 여기까지 오지 않는다.

    `send_event`는 **끊긴 클라이언트에서도 예외를 올리지 않는다** — 방송은
    세션 진행의 전제가 아니다. `receive_event`는 연결이 끝나면 `None`을 돌려준다.
    """

    async def send_event(self, event: dict[str, object]) -> None: ...

    async def receive_event(self) -> dict[str, object] | None: ...


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

        **종료 기록과 발음 시도 수렴은 한 트랜잭션이다** (설계서 §3.2). 갈라 두면 그 사이
        크래시에서 "세션은 끝났는데 대답 기다림이 영원히 남은" 행이 생기고, 그것이 이후
        학습 계산에 그대로 섞인다.
        """
        await self._await_pending_saves()
        # 대화가 사용자 발화로 끝나는 것이 정상이다 — 뒤따르는 agent final이 없으니
        # 턴 경계 flush가 걸리지 않는다. 여기서 한 번 더 걷지 않으면 마지막 사용자
        # 묶음이 영원히 분석되지 않는다 (I-1). 저장이 다 끝난 뒤에 부른다.
        # **연결 획득까지 `_flush_analysis` 안에서** 한다 — acquire가 pool 소진이나
        # 종료 중 취소로 실패하면 아래 close·종료 기록이 통째로 건너뛰어져 세션이
        # `active` 고아로 남는다(이 docstring이 금지한 상태다).
        await self._flush_analysis()
        try:
            await self._adapter.close()
        except Exception:
            logger.exception("어댑터 close가 실패했다 (세션 %s)", self._session_id)
        finally:
            async with self._pool.acquire() as conn, conn.transaction():
                await end_session(conn, self._session_id, status)
                await resolve_dangling(conn, self._session_id)

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
        """어댑터 이벤트를 방송하거나 저장한다.

        **저장되는 것은 사용자·agent의 final 전사문뿐이다.** 오디오 프레임·발화 경계·
        barge-in 통보는 전부 화면 상태라 방송만 한다 — 포트가 Phase 2에서 확장됐어도
        (`port.SpeechBoundaryEvent`·`InterruptionEvent`) 이 모듈의 저장 규칙과 세션
        수명은 그대로다 (G3).
        """
        async for event in self._adapter.events():
            if isinstance(event, bytes):
                await self._send({"type": "audio", "data": base64.b64encode(event).decode("ascii")})
            elif isinstance(event, SpeechBoundaryEvent):
                await self._send(
                    {
                        "type": "speech_start" if event.speaking else "speech_end",
                        "offset_ms": event.offset_ms,
                    }
                )
            elif isinstance(event, InterruptionEvent):
                await self._send({"type": "interrupted"})
            elif isinstance(event, PronunciationEvent):
                await self._record_pronunciation(event)
            elif event.kind == "partial":
                await self._send({"type": "partial", "text": event.text, "speaker": event.speaker})
            else:
                await self._store_final(event)

    async def _record_pronunciation(self, event: PronunciationEvent) -> None:
        """발음 시도를 저장하고 화면에 알린다 (설계서 §3.2·§5.1 S3·S7).

        생명주기 규칙은 전부 `services/pronunciation.py`가 안다 — 이 메서드는 이벤트를
        그 함수에 넘기고 프레임을 방송할 뿐이다.

        **예외를 세션 밖으로 던지지 않는다**: 발음 기록 실패가 대화를 끊으면 안 된다.
        기록을 잃는 편이 낫다(설계서 §7 Contract).

        **`create_task`로 띄우지 않는다.** 판정은 "같은 세션의 최신 대답 기다림 행"을
        고르므로 두 기록이 겹치면 무관한 시도를 닫는다(코드 리뷰가 연결 2개로 실측).
        이벤트 펌프가 순차로 await하는 지금 형태가 그 경합을 원천 차단한다.
        """
        try:
            async with self._pool.acquire() as conn:
                await record_attempt(
                    conn,
                    self._session_id,
                    target_form=event.target_form,
                    outcome=event.outcome,
                    spoken_form=event.spoken_form,
                    target_sound=event.target_sound,
                )
        except Exception:
            logger.exception("발음 시도 저장에 실패했다 (세션 %s)", self._session_id)
        await self._send(
            {
                "type": "pronunciation",
                "outcome": event.outcome,
                "target_form": event.target_form,
                "target_sound": event.target_sound,
            }
        )

    async def _store_final(self, event: TranscriptEvent) -> None:
        """final을 저장한다 — **취소가 저장을 찢지 못하게** shield로 감싼다.

        드레인 데드라인이 만료돼 펌프가 취소될 때 저장이 진행 중이면, shield가 없으면
        `save_final_transcript`의 트랜잭션 중간에서 취소가 터진다: 전사문이 롤백되어
        그 발화는 흔적 없이 사라진다. 시작한 저장은 끝까지 간다. (분석 job은 이제
        여기서 걸리지 않으므로 같이 잃을 것이 없다 — I-1.)
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
            if event.speaker == "user":
                # 발음 신호가 보이는지 **서비스가** 본다. 무엇을 어떻게 보는지는 이 모듈의
                # 관심사가 아니다 — 감지기가 늘거나 줄어도 여기는 바뀌지 않는다.
                # 실패해도 전사문 저장을 되돌리지 않는다: 신호는 부가 정보다.
                try:
                    await note_transcript(
                        conn,
                        self._session_id,
                        transcript=utterance.transcript,
                        utterance_id=utterance.id,
                    )
                except Exception:
                    logger.exception("발음 신호 기록에 실패했다 (세션 %s)", self._session_id)
            else:
                # agent가 말을 시작했다 = 사용자 턴이 닫혔다. 그 직전까지의 사용자
                # final 묶음을 하나로 묶어 분석 job 1건을 건다 (I-1). 이 모듈은
                # learning 발화만 저장하므로 speaker가 유일한 판별자다.
                await self._flush_analysis(conn)
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

    async def _flush_analysis(self, conn: asyncpg.Connection | None = None) -> None:
        """턴이 닫힌 사용자 발화 묶음에 분석 job을 건다 (I-1).

        **예외를 밖으로 던지지 않는다.** flush 실패가 이벤트 펌프를 죽이면 대화가
        끊기고, 종료 경로에서 터지면 세션이 `active` 고아로 남는다 — 둘 다 분석
        1건을 잃는 것보다 나쁘다. 다음 flush가 같은 묶음을 다시 찾으므로(묶음의
        마지막 발화에 job이 없으면 대상이다) 턴 중간의 실패는 스스로 회복된다.
        종료 시점의 실패만이 그 묶음을 잃는다.

        `conn`이 없으면 **연결도 여기서 얻는다.** 호출자가 acquire를 하면 그 실패가
        이 가드 밖에 남아 종료 경로를 끌고 내려간다(코드 리뷰가 가짜 pool로 실측:
        acquire 1회 실패 → `adapter.close()` 미호출 · 종료 기록 0건). 이미 연결을
        들고 있는 호출처는 그것을 넘겨 재사용한다 — 연결을 쥔 채 또 얻지 않는다.

        **호출자의 트랜잭션 안에서 부르지 않는다** — SQL 오류가 나면 그 트랜잭션이
        abort되어 뒤따르는 종료 기록까지 함께 실패한다. 두 호출처 모두 트랜잭션을
        열지 않은 연결을 쓴다.
        """
        try:
            if conn is not None:
                await flush_pending_analysis(conn, self._session_id)
                return
            async with self._pool.acquire() as own_conn:
                await flush_pending_analysis(own_conn, self._session_id)
        except Exception:
            logger.exception("분석 job flush에 실패했다 (세션 %s)", self._session_id)

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
