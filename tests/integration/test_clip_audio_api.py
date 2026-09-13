"""합성 클립 오디오 서빙 엔드포인트 (`TASK-66.5`).

설계: `docs/design/2026-09-14-shadowing-clip-audio-design.md` §5.

⚠️ **재는 것은 라우터의 몫뿐이다** — 바이트를 고르는 판정은 `tests/unit/test_clip_audio.py` 가
소유한다. 여기서는 그 산출물이 HTTP 로 나가는 형태와 **접근 불가가 404 로 나가는 것**을 잰다.

`api_client` 는 커밋된 행만 본다(라우터가 자기 커넥션을 연다) — 그래서 `db_pool` 로 심고 스스로
지운다. 뿌리 격리는 `test_recording_api.py` 가 세운 방식을 그대로 쓴다(`pin_settings_env` +
`get_settings.cache_clear()`).
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
from app.services.clip_audio import CLIP_AUDIO_MEDIA_TYPE

# RIFF 헤더의 앞머리만 닮은 바이트다 — 라우터는 내용을 해석하지 않으므로 이것으로 충분하다.
WAV_BYTES = b"RIFF----WAVEfmt "


@pytest_asyncio.fixture
async def clip_audio_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, test_database: str
) -> AsyncIterator[Path]:
    """클립 뿌리를 tmp 로 옮긴다 — 기본값은 리포루트 `assets/clips` 라 격리가 필요하다.

    ⚠️ `get_settings()` 가 `lru_cache` 라서 env 를 심는 것만으로는 안 먹는다.
    """
    monkeypatch.setenv("DATABASE_URL", test_database)
    monkeypatch.setenv("SHADOWING_CLIP_AUDIO_ROOT", str(tmp_path))
    pin_settings_env(monkeypatch, keep=("DATABASE_URL", "SHADOWING_CLIP_AUDIO_ROOT"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def committed_clip(db_pool: asyncpg.Pool) -> AsyncIterator[UUID]:
    """커밋된 클립 1행 — 포인터는 있고 파일은 없는 상태로 준다.

    ⛔ **스스로 지운다** — `db_pool` 픽스처는 아무것도 정리하지 않고, 남기면
    `seed_shadowing_clips` 처럼 「자기 행 밖의 클립이 있으면 실패」하는 픽스처를 깨뜨린다.
    """
    async with db_pool.acquire() as conn:
        item_id = await conn.fetchval(
            "insert into shadowing_items (source_title, transcript, clip_start_sec, "
            "clip_end_sec, level) values ('Morning', 'I wake up at seven.', 0, 17.36, 'A2') "
            "returning id"
        )
        await conn.execute(
            "update shadowing_items set audio_filename = $2 where id = $1",
            item_id,
            f"{item_id}.wav",
        )
    yield item_id
    async with db_pool.acquire() as conn:
        await conn.execute("delete from shadowing_items where id = $1", item_id)


async def test_serves_the_clip_bytes_as_wav(
    api_client: httpx.AsyncClient, committed_clip: UUID, clip_audio_root: Path
) -> None:
    """바이트를 그대로 내보내고 Content-Type 이 `audio/wav` 다.

    ⛔ `audio/L16`(낭독의 값)이면 프런트의 `new Audio()` 가 디코드하지 못한다 — 값이 계약이다.
    """
    (clip_audio_root / f"{committed_clip}.wav").write_bytes(WAV_BYTES)

    response = await api_client.get(f"/api/shadowing/clips/{committed_clip}/audio")

    assert response.status_code == 200
    assert response.content == WAV_BYTES
    assert response.headers["content-type"] == CLIP_AUDIO_MEDIA_TYPE


async def test_unknown_clip_is_404(api_client: httpx.AsyncClient, clip_audio_root: Path) -> None:
    response = await api_client.get(f"/api/shadowing/clips/{uuid4()}/audio")

    assert response.status_code == 404


async def test_clip_without_a_file_is_404(
    api_client: httpx.AsyncClient, committed_clip: UUID, clip_audio_root: Path
) -> None:
    """포인터만 있고 파일이 없는 상태 — 배포에서 자산이 빠졌을 때다. **500 이 아니다.**"""
    response = await api_client.get(f"/api/shadowing/clips/{committed_clip}/audio")

    assert response.status_code == 404


async def test_clip_without_a_pointer_is_404(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, clip_audio_root: Path
) -> None:
    """`audio_filename` 이 null 인 클립 — 오디오를 아직 만들지 않은 상태다.

    ⚠️ 파일이 뿌리에 **있어도** 404 여야 한다: DB 가 접근 가능성의 정본이다(낭독 쪽 §4.5 와 같은
    규약). 이 단정이 없으면 「뿌리를 훑어 파일이 있으면 준다」는 구현이 통과한다.
    """
    async with db_pool.acquire() as conn:
        item_id = await conn.fetchval(
            "insert into shadowing_items (source_title, transcript, clip_start_sec, "
            "clip_end_sec, level) values ('Silent', 'I wake up at seven.', 0, 17.36, 'A2') "
            "returning id"
        )
    try:
        (clip_audio_root / f"{item_id}.wav").write_bytes(WAV_BYTES)

        response = await api_client.get(f"/api/shadowing/clips/{item_id}/audio")

        assert response.status_code == 404
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from shadowing_items where id = $1", item_id)


async def test_path_shaped_item_id_never_reaches_the_filesystem(
    api_client: httpx.AsyncClient, clip_audio_root: Path
) -> None:
    """⛔ 경로 이탈의 셋째 겹 — `UUID` 선언이 라우팅에서 막는다.

    `get_recording` 의 docstring 이 *"두 값이 `UUID` 로 선언된 것이 경로 탈출도 함께 막는다"* 로
    같은 성질을 이미 적었다. 422(검증 실패)든 404(경로 불일치)든 **바이트가 나가지 않는 것**이
    이 단정의 축이다.
    """
    response = await api_client.get("/api/shadowing/clips/..%2F..%2Fetc%2Fpasswd/audio")

    assert response.status_code in (404, 422)
    assert response.content != WAV_BYTES
