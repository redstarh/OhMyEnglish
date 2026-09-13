"""합성 클립 오디오를 읽는 길의 계약 (`TASK-66.4`).

설계: `docs/design/2026-09-14-shadowing-clip-audio-design.md` §5.

⚠️ **`db_conn`(롤백 트랜잭션)만 쓴다** — 커밋된 행을 남기지 않는다. HTTP 표면은
`tests/integration/test_clip_audio_api.py` 가 `db_pool` 로 따로 잰다.
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest

from app.services.clip_audio import CLIP_AUDIO_MEDIA_TYPE, clip_audio_path, load_clip_audio


async def _insert_clip(conn: asyncpg.Connection, *, with_audio: bool) -> UUID:
    item_id = await conn.fetchval(
        "insert into shadowing_items (source_title, transcript, clip_start_sec, "
        "clip_end_sec, level) values ('Morning', 'I wake up at seven.', 0, 17.36, 'A2') "
        "returning id"
    )
    if with_audio:
        await conn.execute(
            "update shadowing_items set audio_filename = $2 where id = $1",
            item_id,
            f"{item_id}.wav",
        )
    return item_id


def test_media_type_declares_wav_not_raw_pcm() -> None:
    """⛔ 학습자 낭독의 `audio/L16` 과 **다른 값이어야 한다** (설계서 §6).

    낭독은 헤더가 없어 표본율·채널을 Content-Type 이 말해야 하고 `fetch()` + `VoiceIo` 로만
    재생된다(`RECORDING_MEDIA_TYPE` 의 주석이 그 사실을 실측으로 적어 두었다). 클립은 RIFF
    헤더가 있어 `new Audio()` 가 그대로 디코드한다 — 그 차이가 프런트 설계의 근거이므로 값이
    섞이면 재생 경로가 조용히 틀어진다.
    """
    assert CLIP_AUDIO_MEDIA_TYPE == "audio/wav"


def test_path_is_built_from_the_id_not_from_a_stored_string(tmp_path: Path) -> None:
    """⛔ 경로 조립의 둘째 겹 — DB 문자열을 쓰지 않는다 (설계서 §5).

    022 의 CHECK 가 파일명을 id 로 강제하지만 방어를 겹으로 둔다. **서명이 파일명을 받지 않는 것**이
    그 성질을 타입으로 보장한다 — 인자를 더하는 순간 DB 값이 경로에 닿는 길이 열린다.
    """
    item_id = uuid4()

    assert clip_audio_path(tmp_path, item_id) == tmp_path / f"{item_id}.wav"


@pytest.mark.asyncio
async def test_loads_the_bytes_when_the_pointer_and_the_file_are_both_there(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    item_id = await _insert_clip(db_conn, with_audio=True)
    (tmp_path / f"{item_id}.wav").write_bytes(b"RIFF----WAVEfmt ")

    assert await load_clip_audio(db_conn, tmp_path, item_id) == b"RIFF----WAVEfmt "


@pytest.mark.asyncio
async def test_returns_none_for_the_three_shapes_of_no_audio(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """접근 불가 세 형태가 전부 `None` 이다 — 라우터가 404 로 옮긴다.

    ⚠️ ①(행 없음)과 ②(포인터 null)는 `fetchval` 이 둘 다 `None` 을 주어 **한 갈래로 수렴한다.**
    그래도 둘을 따로 재는 것은 호출자에게 다른 상태이기 때문이다.
    """
    # ① 클립 행이 없다
    assert await load_clip_audio(db_conn, tmp_path, uuid4()) is None

    # ② 포인터가 null 이다 — 오디오를 아직 만들지 않은 클립
    silent_id = await _insert_clip(db_conn, with_audio=False)
    assert await load_clip_audio(db_conn, tmp_path, silent_id) is None

    # ③ 포인터는 있고 파일이 없다 — 배포에서 자산이 빠졌다
    orphan_id = await _insert_clip(db_conn, with_audio=True)
    assert await load_clip_audio(db_conn, tmp_path, orphan_id) is None


@pytest.mark.asyncio
async def test_does_not_expire_product_assets(db_conn: asyncpg.Connection, tmp_path: Path) -> None:
    """⛔ 만료를 재지 않는다 — `load_recording` 과 갈라지는 자리다 (설계서 §5).

    낭독은 학습자의 당일이 지나면 `None` 이 되지만(그쪽 docstring 의 ③) 클립은 제품 자산이라
    시간에 따라 사라지지 않는다. **행이 아무리 오래돼도** 바이트가 나오는 것이 그 성질이다.
    """
    item_id = await _insert_clip(db_conn, with_audio=True)
    (tmp_path / f"{item_id}.wav").write_bytes(b"RIFF")
    await db_conn.execute(
        "update shadowing_items set created_at = now() - interval '400 days' where id = $1",
        item_id,
    )

    assert await load_clip_audio(db_conn, tmp_path, item_id) == b"RIFF"
