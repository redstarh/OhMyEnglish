"""Task 9 — `/ws/session` 소켓 배선 테스트 (AC G4, 설계서 §5.3).

**실서버를 띄우지 않는다.** starlette의 `TestClient`는 동기라 async DB 픽스처와
같은 테스트 안에서 쓸 수 없고, httpx는 WebSocket을 지원하지 않는다(wsproto 미설치).
그래서 ASGI 프로토콜을 직접 말하는 얇은 클라이언트(`ASGIWebSocket`)로 앱을
in-process 호출한다 — 소켓도 포트도 열지 않으므로 실시간 대기가 없고, 앱이 보낸
프레임을 그대로 관측할 수 있다.

여기서 볼 것은 두 가지뿐이다: 연결이 **고정 사용자의 세션 행**을 만드는가,
그리고 게이트웨이가 만든 이벤트가 **JSON 프레임으로 나가는가**. 세션 규칙 자체는
`tests/integration/test_gateway.py`가 검증한다.

`lifespan`을 직접 열어 pool을 만들고(테스트 DB), 워커는 끈다 — 이 테스트는 큐에
job이 쌓이는 것까지만 보고, 그 뒤(Claude 호출)는 Task 7이 본다.
"""

from __future__ import annotations

import asyncio
import base64
import json
from collections.abc import AsyncIterator, Iterator, MutableMapping, Sequence
from typing import Any
from uuid import UUID, uuid4

import asyncpg
import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from app import db as db_module
from app.api import ws as ws_module
from app.api.main import FRONTEND_ORIGIN, create_app
from app.api.ws import FIXED_USER_ID, WS_SESSION_PATH
from app.audio_gateway.fixtures import FIXTURE_TURNS, TONE_WAV_FRAME
from app.config import Settings, get_settings

RECEIVE_TIMEOUT = 5.0

_SCOPE: dict[str, Any] = {
    "type": "websocket",
    "asgi": {"version": "3.0", "spec_version": "2.3"},
    "http_version": "1.1",
    "scheme": "ws",
    "path": WS_SESSION_PATH,
    "raw_path": WS_SESSION_PATH.encode(),
    "query_string": b"",
    "root_path": "",
    "headers": [(b"host", b"testserver")],
    "client": ("testclient", 50000),
    "server": ("testserver", 80),
    "subprotocols": [],
}


class ASGIWebSocket:
    """ASGI websocket 프로토콜을 직접 말하는 in-process 클라이언트.

    앱을 태스크로 돌리고 두 큐로 프레임을 주고받는다. `receive_event()`는 앱이
    보낸 JSON을 돌려주고, close 프레임을 받으면 `None`을 돌려준다.
    """

    def __init__(self, app: FastAPI) -> None:
        self._app = app
        self._to_app: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._from_app: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self.closed = False

    async def _asgi_send(self, message: MutableMapping[str, Any]) -> None:
        """앱이 클라이언트로 보내는 ASGI `send` 콜러블."""
        await self._from_app.put(dict(message))

    async def __aenter__(self) -> ASGIWebSocket:
        self._task = asyncio.create_task(self._app(dict(_SCOPE), self._to_app.get, self._asgi_send))
        await self._to_app.put({"type": "websocket.connect"})
        accept = await asyncio.wait_for(self._from_app.get(), timeout=RECEIVE_TIMEOUT)
        assert accept["type"] == "websocket.accept", accept
        return self

    async def __aexit__(self, *_exc: object) -> None:
        assert self._task is not None
        if not self.closed:
            await self._to_app.put({"type": "websocket.disconnect", "code": 1000})
        # 앱 태스크가 예외로 끝났다면 여기서 드러난다.
        await asyncio.wait_for(self._task, timeout=RECEIVE_TIMEOUT)

    async def send_event(self, payload: dict[str, Any]) -> None:
        await self._to_app.put({"type": "websocket.receive", "text": json.dumps(payload)})

    async def receive_event(self) -> dict[str, Any] | None:
        message = await asyncio.wait_for(self._from_app.get(), timeout=RECEIVE_TIMEOUT)
        if message["type"] == "websocket.close":
            self.closed = True
            return None
        assert message["type"] == "websocket.send", message
        return json.loads(message["text"])

    async def collect_until(self, event_type: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        while True:
            event = await self.receive_event()
            assert event is not None, f"소켓이 {event_type} 전에 닫혔다: {events}"
            events.append(event)
            if event["type"] == event_type:
                return events


@pytest.fixture
def ws_app(monkeypatch: pytest.MonkeyPatch, test_database: str) -> Iterator[FastAPI]:
    """테스트 DB를 보는 앱. 워커는 끈다 — Bedrock 자격증명도, 실제 호출도 없다.

    `get_settings`(lru_cache)와 `db._pool`은 프로세스 전역이라 둘 다 비운다
    (`tests/integration/test_worker.py`의 `app_settings`와 같은 이유).
    """
    monkeypatch.setenv("DATABASE_URL", test_database)
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("WORKER_ENABLED", "false")
    monkeypatch.setattr(db_module, "_pool", None)
    get_settings.cache_clear()
    yield create_app()
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def seeded_fixed_user(db_pool: asyncpg.Pool) -> AsyncIterator[UUID]:
    """고정 사용자 + 시나리오 1행을 커밋해두고, teardown에서 지운다.

    `/ws/session`은 시드된 고정 사용자로 세션을 만든다(단일 사용자 로컬 도구).
    사용자를 지우면 세션 → 발화 → job이 cascade로 함께 사라지므로 이 테스트의
    커밋된 쓰기가 다음 테스트에 남지 않는다.
    """
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into users (id, display_name) values ($1, 'Learner') "
            "on conflict (id) do nothing",
            FIXED_USER_ID,
        )
        scenario_id = await conn.fetchval(
            "insert into learning_scenarios (category, level, title, prompt_template) "
            "values ('daily_life', 'A2', $1, $1) returning id",
            FIXTURE_TURNS[0][0],
        )
    try:
        yield scenario_id
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", FIXED_USER_ID)
            await conn.execute("delete from learning_scenarios where id = $1", scenario_id)


async def _run_one_session(app: FastAPI) -> tuple[UUID, list[dict[str, Any]]]:
    """소켓 하나를 열어 픽스처 대화가 끝날 때까지 받은 이벤트를 돌려준다."""
    async with app.router.lifespan_context(app), ASGIWebSocket(app) as client:
        started = await client.receive_event()
        assert started is not None and started["type"] == "session_started"
        events = [started, *await client.collect_until("session_ended")]
        assert await client.receive_event() is None, "세션이 끝나면 소켓도 닫혀야 한다"
    return UUID(started["session_id"]), events


# ⑤ WS 연결 → 고정 사용자의 learning_sessions 행 생성
async def test_ws_connection_creates_a_session_for_the_fixed_user(
    ws_app: FastAPI, db_pool: asyncpg.Pool, seeded_fixed_user: UUID
):
    session_id, _ = await _run_one_session(ws_app)

    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            "select user_id, scenario_id, mode, status, started_at, ended_at "
            "from learning_sessions where id = $1",
            session_id,
        )
    assert session is not None, "연결이 세션 행을 만들지 않았다"
    assert session["user_id"] == FIXED_USER_ID
    assert session["scenario_id"] == seeded_fixed_user  # 시드 시나리오 첫 행
    assert session["mode"] == "speaking"
    # 픽스처 스텁은 대화를 완주하므로 세션은 정상 종료로 닫혀 있다 (G1).
    assert session["status"] == "completed"
    assert session["ended_at"] is not None
    assert session["started_at"].tzinfo is not None


# I-4 — 고아 세션 리퍼가 **진행 중** 세션을 닫지 않는 근거는 이 집합이다. 세션이 도는
# 동안 등록되어 있어야 하고, 끝나면 빠져야 한다(빠지지 않으면 그 세션은 영구히 리퍼
# 면제 대상이 되어, 정작 고아가 됐을 때 아무도 닫지 않는다).
async def test_a_running_session_is_registered_as_live_and_released_when_it_ends(
    ws_app: FastAPI, seeded_fixed_user: UUID
):
    async with ws_app.router.lifespan_context(ws_app), ASGIWebSocket(ws_app) as client:
        started = await client.receive_event()
        assert started is not None and started["type"] == "session_started"
        session_id = UUID(started["session_id"])
        # 대화가 끝나기 **전에** 관측한다 — 끝난 뒤에 보면 등록 여부를 알 수 없다.
        live_while_running = set(ws_app.state.live_sessions)
        await client.collect_until("session_ended")
        # 소켓이 닫히는 것을 기다린다: 해제는 소켓 close **앞**에서 일어나므로,
        # 여기까지 오면 해제도 끝났다 — 경쟁 없이 다음 단정을 할 수 있다.
        assert await client.receive_event() is None

    assert session_id in live_while_running, "진행 중 세션이 live 집합에 없다"
    assert session_id not in ws_app.state.live_sessions, "끝난 세션이 live 집합에 남았다"


# G4를 소켓 경로로 한 번 더 — 전사문 저장·job 등록이 실사용 경로에서도 일어난다
async def test_ws_session_stores_user_finals_and_enqueues_jobs(
    ws_app: FastAPI, db_pool: asyncpg.Pool, seeded_fixed_user: UUID
):
    session_id, _ = await _run_one_session(ws_app)

    async with db_pool.acquire() as conn:
        transcripts = await conn.fetch(
            "select transcript from utterances where session_id = $1 and speaker = 'user' "
            "order by sequence_no",
            session_id,
        )
        jobs = await conn.fetchval(
            "select count(*) from analysis_jobs j join utterances u on u.id = j.utterance_id "
            "where u.session_id = $1 and j.job_type = 'analyze_utterance'",
            session_id,
        )
    assert [row["transcript"] for row in transcripts] == [answer for _, answer in FIXTURE_TURNS]
    assert jobs == len(FIXTURE_TURNS)


# 프로토콜 — 클라이언트가 받는 프레임의 종류와 모양
async def test_ws_relays_transcripts_and_base64_audio(
    ws_app: FastAPI, db_pool: asyncpg.Pool, seeded_fixed_user: UUID
):
    _, events = await _run_one_session(ws_app)

    types = [event["type"] for event in events]
    assert types[0] == "session_started"
    assert types[-1] == "session_ended"
    assert "partial" in types
    finals = [event for event in events if event["type"] == "final"]
    assert [event["speaker"] for event in finals] == ["agent", "user"] * len(FIXTURE_TURNS)
    assert [event["sequence_no"] for event in finals] == list(range(1, len(FIXTURE_TURNS) * 2 + 1))
    audio = [event for event in events if event["type"] == "audio"]
    assert len(audio) == len(FIXTURE_TURNS)
    assert base64.b64decode(audio[0]["data"]) == TONE_WAV_FRAME


# Fix round 1 (I2) — 어댑터를 아예 만들 수 없어도(설정 오타/구현 부재) 세션을
# `active` 고아로 남기지 않는다. 소켓은 실패를 알리고 닫힌다.
async def test_ws_reports_a_failed_session_when_the_adapter_cannot_be_built(
    ws_app: FastAPI,
    db_pool: asyncpg.Pool,
    seeded_fixed_user: UUID,
    monkeypatch: pytest.MonkeyPatch,
):
    def explode(settings: object) -> None:
        raise ValueError("알 수 없는 voice_adapter 설정: 'nova'")

    monkeypatch.setattr(ws_module, "create_voice_adapter", explode)

    async with ws_app.router.lifespan_context(ws_app), ASGIWebSocket(ws_app) as client:
        failure = await client.receive_event()
        assert failure is not None
        assert failure["type"] == "session_failed"
        assert await client.receive_event() is None, "실패 후 소켓이 닫히지 않았다"

    async with db_pool.acquire() as conn:
        session = await conn.fetchrow(
            "select status, ended_at from learning_sessions where user_id = $1", FIXED_USER_ID
        )
    assert session is not None, "세션 행은 만들어졌어야 한다(그래야 결과 화면이 존재한다)"
    assert session["status"] == "failed", "어댑터를 못 만든 세션이 active 고아로 남았다"
    assert session["ended_at"] is not None


# 추가(T10) — 브라우저에서 결과를 폴링할 수 있어야 한다 (CORS)
async def test_results_endpoint_allows_the_frontend_origin(ws_app: FastAPI):
    async with ws_app.router.lifespan_context(ws_app):
        transport = httpx.ASGITransport(app=ws_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get(
                f"/api/sessions/{uuid4()}/results", headers={"Origin": FRONTEND_ORIGIN}
            )

    # 없는 세션이라 404지만, CORS 헤더는 미들웨어가 응답 상태와 무관하게 붙인다.
    assert response.status_code == 404
    assert response.headers["access-control-allow-origin"] == FRONTEND_ORIGIN


# --- G-3: 조립한 지시문이 어댑터까지 간다 (+ 조회 실패 방어) ---


# 소켓이 세션을 만든 **뒤** 어댑터를 만들기 전에 기존 소리를 읽어 지시문을 조립해 넘긴다.
# 이 순서가 아니면 사용자를 모르는 상태에서 조회하게 된다.
async def test_ws_passes_assembled_instructions_to_the_adapter(
    ws_app: FastAPI,
    db_pool: asyncpg.Pool,
    seeded_fixed_user: UUID,
    monkeypatch: pytest.MonkeyPatch,
):
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into error_patterns (user_id, category, pattern_key, target_form) "
            "values ($1, 'pronunciation_intonation', 'pronunciation_th_as_s', 'th_as_s')",
            FIXED_USER_ID,
        )
    seen: dict[str, object] = {}
    real_factory = ws_module.create_voice_adapter

    def spy(settings: Settings, *, known_sounds: Sequence[str] = ()) -> object:
        seen["known_sounds"] = list(known_sounds)
        return real_factory(settings, known_sounds=known_sounds)

    monkeypatch.setattr(ws_module, "create_voice_adapter", spy)

    try:
        async with ws_app.router.lifespan_context(ws_app), ASGIWebSocket(ws_app) as client:
            await client.receive_event()
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from error_patterns where user_id = $1", FIXED_USER_ID)

    # 소켓은 **데이터**만 넘긴다 — 조립은 팩토리가 한다(G3 이음매). 그래서 여기서 보는 것은
    # 조립된 문구가 아니라 목록이고, 문구 조립은 `test_nova`·`test_gateway`가 못박는다.
    assert seen.get("known_sounds") == ["th_as_s"], (
        "학습자의 기존 소리가 어댑터 생성까지 전달되지 않았다"
    )


# 발음 힌트는 **부가 정보**다. 그 조회가 깨졌다고 대화를 못 열면 손해가 더 크다 —
# 빈 목록으로 넘어가고 세션은 그대로 열린다.
async def test_ws_opens_the_session_even_if_the_known_sounds_lookup_fails(
    ws_app: FastAPI,
    db_pool: asyncpg.Pool,
    seeded_fixed_user: UUID,
    monkeypatch: pytest.MonkeyPatch,
):
    async def explode(conn: object, user_id: object) -> list[str]:
        raise asyncpg.PostgresError("기존 소리 조회가 깨졌다")

    monkeypatch.setattr(ws_module, "load_known_sounds", explode)

    async with ws_app.router.lifespan_context(ws_app), ASGIWebSocket(ws_app) as client:
        first = await client.receive_event()

    assert first is not None
    assert first["type"] != "session_failed", (
        "발음 힌트 조회 실패가 세션을 막았다 — 부가 정보 때문에 대화를 잃는다"
    )

    async with db_pool.acquire() as conn:
        status = await conn.fetchval(
            "select status from learning_sessions where user_id = $1", FIXED_USER_ID
        )
    assert status != "failed"
