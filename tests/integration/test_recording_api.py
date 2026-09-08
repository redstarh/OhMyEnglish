"""쉐도잉 녹음 서빙 엔드포인트 (`TASK-45` AC#3 · 설계서 §4.4).

⚠️ **재는 것은 라우터의 몫뿐이다** — 파일 수명과 포인터 순서는 `tests/unit/test_recordings.py`
가 소유한다. 여기서는 그 산출물이 HTTP 로 나가는 형태와 **접근 불가가 404 로 나가는 것**을 잰다.

`api_client` 는 커밋된 행만 본다(라우터가 자기 커넥션을 연다) — 그래서 `committed_session` 과
`db_pool` 을 함께 쓴다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import httpx
import pytest
import pytest_asyncio
from conftest import pin_settings_env

from app.config import get_settings
from app.services.recordings import RECORDING_MEDIA_TYPE, recording_path

FRAMES = b"\x7f\x00" * 320


@pytest_asyncio.fixture
async def audio_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, test_database: str
) -> AsyncIterator[Path]:
    """녹음 뿌리를 tmp 로 옮긴다 — 기본값은 리포루트 `assets/audio` 이므로 격리가 필요하다.

    `get_settings()` 가 `lru_cache` 라서 env 를 심는 것만으로는 안 먹는다(선례:
    `tests/integration/test_ws.py`). `DATABASE_URL` 은 `Settings` 의 필수 필드라 지우면
    `get_settings()` 자체가 죽으므로 `keep` 으로 남긴다.
    """
    monkeypatch.setenv("DATABASE_URL", test_database)
    monkeypatch.setenv("SHADOWING_AUDIO_ROOT", str(tmp_path))
    pin_settings_env(monkeypatch, keep=("DATABASE_URL", "SHADOWING_AUDIO_ROOT"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


async def _stored_recording(
    conn: asyncpg.Connection, root: Path, session_id: UUID, *, sequence_no: int = 1
) -> UUID:
    """접근 가능한 녹음 하나 — 파일과 포인터가 **둘 다** 있는 상태."""
    utterance_id = await conn.fetchval(
        "insert into utterances (session_id, speaker, utterance_type, transcript, sequence_no) "
        "values ($1, 'user', 'shadowing_recording', 'I usually wake up at seven.', $2) "
        "returning id",
        session_id,
        sequence_no,
    )
    path = recording_path(root, session_id, utterance_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(FRAMES)
    await conn.execute(
        "update utterances set audio_url = $2 where id = $1",
        utterance_id,
        f"/api/sessions/{session_id}/recordings/{utterance_id}",
    )
    return utterance_id


async def test_stored_recording_is_served_as_raw_pcm(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session, audio_root: Path
) -> None:
    """바이트를 그대로 내보내고 **표본율·채널을 Content-Type 이 싣는다** (§4.4)."""
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(conn, audio_root, committed_session.session_id)

    response = await api_client.get(
        f"/api/sessions/{committed_session.session_id}/recordings/{utterance_id}"
    )

    assert response.status_code == 200
    assert response.content == FRAMES
    assert response.headers["content-type"] == RECORDING_MEDIA_TYPE


async def test_recording_without_a_pointer_is_404(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session, audio_root: Path
) -> None:
    """포인터가 없으면 파일이 있어도 **접근 불가**다 — DB 가 접근 가능성의 정본이다(§4.5)."""
    async with db_pool.acquire() as conn:
        utterance_id = await conn.fetchval(
            "insert into utterances "
            "(session_id, speaker, utterance_type, transcript, sequence_no) "
            "values ($1, 'user', 'shadowing_recording', 'Then I make a cup of coffee.', 1) "
            "returning id",
            committed_session.session_id,
        )
        path = recording_path(audio_root, committed_session.session_id, utterance_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(FRAMES)

    response = await api_client.get(
        f"/api/sessions/{committed_session.session_id}/recordings/{utterance_id}"
    )

    assert response.status_code == 404


async def test_recording_is_not_served_under_another_session(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session, audio_root: Path
) -> None:
    """⛔ 세션을 바꿔 넣은 요청이 통과하면 남의 녹음이 새어 나간다.

    녹음은 학습자 음성이므로 이 경계가 개인정보 경계다 — URL 두 세그먼트가 **둘 다** 조회
    조건이어야 한다.
    """
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(conn, audio_root, committed_session.session_id)

    response = await api_client.get(f"/api/sessions/{uuid4()}/recordings/{utterance_id}")

    assert response.status_code == 404


async def test_unknown_recording_is_404(
    api_client: httpx.AsyncClient, committed_session, audio_root: Path
) -> None:
    """없는 발화는 500 이 아니라 404 다."""
    response = await api_client.get(
        f"/api/sessions/{committed_session.session_id}/recordings/{uuid4()}"
    )

    assert response.status_code == 404
