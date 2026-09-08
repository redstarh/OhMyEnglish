"""쉐도잉 낭독 오디오의 파일 수명과 DB 포인터 (`TASK-45` AC#3 · 설계서 §4.3~§4.5).

⛔ **프레임 수신·파일 핸들 수명은 여기 없다.** 설계서 §12 요구 4(*"낭독 턴을 명시적으로 열고
닫는다"*)가 그 경계를 소유하고 그것은 WS 표면이라 `TASK-10` 의 설계 몫이다 — 결정 34 가
「최소한만 만든다」로 제약했다. 이 계층이 재는 것은 **턴이 닫힌 뒤의 두 걸음**(§4.5 의 3·4):
파일을 `<utterance_id>.pcm` 으로 옮기고 **그 다음에** DB 포인터를 쓴다.

⚠️ **그 순서가 이 파일의 핵심 계약이다.** 뒤집으면 「DB 는 접근 가능하다고 말하는데 파일이
없는」 상태가 생기고, 그것은 학습자에게 깨진 재생으로 보인다. 반대 순서로 죽으면 파일만 남고
접근이 불가능해 §6 의 고아 파일 정리가 걷는다 — **DB 가 접근 가능성의 정본이다.**
"""

from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest

from app.services.recordings import (
    RECORDING_MEDIA_TYPE,
    finalize_recording,
    load_recording,
    pending_recording_path,
    recording_path,
    recording_url,
)

FRAMES = b"\x00\x01" * 160  # raw LPCM 16kHz·16bit·mono 한 프레임 분량 (헤더 없음)


async def _new_shadowing_session(conn: asyncpg.Connection) -> UUID:
    """사용자·세션을 직접 insert 한다 — `db_conn` 은 시드를 하지 않는다(`H-I`)."""
    user_id = await conn.fetchval(
        "insert into users (display_name) values ('Recording Test User') returning id"
    )
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'shadowing') returning id",
        user_id,
    )


async def _new_recording_utterance(conn: asyncpg.Connection, session_id: UUID) -> UUID:
    """`audio_url` 이 아직 null 인 낭독 발화. 011 의 CHECK 가 이 조합만 허용한다."""
    return await conn.fetchval(
        "insert into utterances (session_id, speaker, utterance_type, transcript, sequence_no) "
        "values ($1, 'user', 'shadowing_recording', 'I usually wake up at seven.', 1) "
        "returning id",
        session_id,
    )


def test_recording_path_is_derived_from_the_session_and_utterance() -> None:
    """파일 위치가 `(session_id, utterance_id)`에서 결정론적으로 나온다 (§4.4).

    그래서 **뿌리를 옮겨도 저장된 행이 무효가 되지 않는다** — 뿌리는 설정이고 데이터가 아니다.
    """
    session_id = uuid4()
    utterance_id = uuid4()

    path = recording_path(Path("/tmp/audio"), session_id, utterance_id)

    assert path == Path(f"/tmp/audio/{session_id}/{utterance_id}.pcm")


def test_pending_recording_path_is_marked_part_until_the_turn_closes() -> None:
    """턴이 닫히기 전에는 `utterance_id` 를 모른다 (§4.5) — 그래서 이름이 다르다.

    `.part` 접미사가 「이 파일은 아직 완성되지 않았다」를 파일시스템에 적어 둔다. 고아 파일
    정리가 그 표시로 미완성 녹음을 구분한다.
    """
    session_id = uuid4()
    turn_id = uuid4()

    path = pending_recording_path(Path("/tmp/audio"), session_id, turn_id)

    assert path == Path(f"/tmp/audio/{session_id}/{turn_id}.pcm.part")


def test_recording_url_is_an_api_route_not_a_file_path() -> None:
    """⛔ `audio_url` 에 파일 경로를 담지 않는다 (§4.4).

    컬럼 이름과 `database-schema.md` 의 계약(*"접근 불가 처리"*)이 API 경로일 때만 성립한다.
    """
    session_id = uuid4()
    utterance_id = uuid4()

    assert recording_url(session_id, utterance_id) == (
        f"/api/sessions/{session_id}/recordings/{utterance_id}"
    )


@pytest.mark.asyncio
async def test_finalize_moves_the_file_then_writes_the_pointer(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """§4.5 의 3·4 단계. 두 걸음이 **이 순서로** 끝난 상태를 잰다."""
    session_id = await _new_shadowing_session(db_conn)
    utterance_id = await _new_recording_utterance(db_conn, session_id)
    turn_id = uuid4()
    pending = pending_recording_path(tmp_path, session_id, turn_id)
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_bytes(FRAMES)

    audio_url = await finalize_recording(
        db_conn, tmp_path, session_id=session_id, turn_id=turn_id, utterance_id=utterance_id
    )

    final = recording_path(tmp_path, session_id, utterance_id)
    assert final.read_bytes() == FRAMES
    assert not pending.exists()
    assert audio_url == recording_url(session_id, utterance_id)
    assert (
        await db_conn.fetchval("select audio_url from utterances where id = $1", utterance_id)
        == audio_url
    )


@pytest.mark.asyncio
async def test_finalize_leaves_the_pointer_null_when_the_file_is_missing(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ **순서 계약의 판별력이 여기 걸린다.**

    파일이 없으면 rename 이 실패하고 **그 뒤의 UPDATE 에 도달하지 않는다.** 순서를 뒤집어
    포인터를 먼저 쓰면 이 테스트가 red 가 된다 — 그것이 「DB 는 접근 가능하다는데 파일이 없는」
    상태이고, 학습자에게는 깨진 재생으로 보인다.
    """
    session_id = await _new_shadowing_session(db_conn)
    utterance_id = await _new_recording_utterance(db_conn, session_id)

    with pytest.raises(FileNotFoundError):
        await finalize_recording(
            db_conn, tmp_path, session_id=session_id, turn_id=uuid4(), utterance_id=utterance_id
        )

    assert (
        await db_conn.fetchval("select audio_url from utterances where id = $1", utterance_id)
        is None
    )


@pytest.mark.asyncio
async def test_load_returns_nothing_while_the_pointer_is_null(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """**DB 가 접근 가능성의 정본이다** (§4.5). 파일이 있어도 포인터가 없으면 접근 불가다.

    §4.5 가 「3과 4 사이에서 죽으면 파일만 남고 접근 불가」로 적은 상태가 정확히 이것이다.
    """
    session_id = await _new_shadowing_session(db_conn)
    utterance_id = await _new_recording_utterance(db_conn, session_id)
    final = recording_path(tmp_path, session_id, utterance_id)
    final.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(FRAMES)

    assert await load_recording(db_conn, tmp_path, session_id, utterance_id) is None


@pytest.mark.asyncio
async def test_load_returns_nothing_when_the_pointer_outlives_the_file(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """포인터만 남은 고아는 500 이 아니라 **접근 불가**다.

    삭제 스윕(§6)이 파일과 포인터를 따로 걷기 때문에 그 사이 상태가 실재한다 — 서빙이 그것을
    예외로 터뜨리면 학습자가 서버 오류를 본다.
    """
    session_id = await _new_shadowing_session(db_conn)
    utterance_id = await _new_recording_utterance(db_conn, session_id)
    await db_conn.execute(
        "update utterances set audio_url = $2 where id = $1",
        utterance_id,
        recording_url(session_id, utterance_id),
    )

    assert await load_recording(db_conn, tmp_path, session_id, utterance_id) is None


@pytest.mark.asyncio
async def test_load_does_not_cross_session_boundaries(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ 다른 세션의 `utterance_id` 로 남의 녹음을 읽을 수 없다. 녹음은 학습자 음성이므로 이
    경계가 개인정보 경계다.

    ⚠️ **이 단정이 재는 것은 두 겹의 합이다** — 어느 겹이 막았는지 구분하지 않는다. 겹을 하나씩
    격리하는 것은 아래 `..._even_when_a_file_exists` 가 한다.
    """
    session_id = await _new_shadowing_session(db_conn)
    utterance_id = await _new_recording_utterance(db_conn, session_id)
    turn_id = uuid4()
    pending = pending_recording_path(tmp_path, session_id, turn_id)
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_bytes(FRAMES)
    await finalize_recording(
        db_conn, tmp_path, session_id=session_id, turn_id=turn_id, utterance_id=utterance_id
    )
    other_session_id = await _new_shadowing_session(db_conn)

    assert await load_recording(db_conn, tmp_path, other_session_id, utterance_id) is None
    assert await load_recording(db_conn, tmp_path, session_id, utterance_id) == FRAMES


@pytest.mark.asyncio
async def test_load_is_scoped_to_the_session_even_when_a_file_exists(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ **세션 경계가 두 겹이고 이 단정은 그중 SQL 조건만 격리해 잰다.**

    첫 겹은 **파일 경로**다 — `recording_path` 가 `session_id` 를 포함하므로 남의 세션 id 로는
    파일을 못 찾는다. **그래서 SQL 의 `session_id` 조건을 지워도 위 단정들이 전부 통과한다**
    (2026-09-08 에 직접 무력화해 확인했다: 13 passed). 두 겹 다 값어치 있지만 **한 겹이 조용히
    사라지는 것**을 막으려면 겹마다 단정이 필요하다 — 파일 경로 규칙이 나중에 바뀌면(예: 뿌리
    아래 평면 저장) SQL 조건이 유일한 방어가 된다.

    아래는 파일 경로 방어를 **인공적으로 걷어낸** 상태다: 실제로 한 발화는 한 세션에만 속하므로
    이 배치는 실물에서 생기지 않는다. 그것이 이 테스트의 목적이다 — 남은 겹 하나만 재는 것.
    """
    session_id = await _new_shadowing_session(db_conn)
    utterance_id = await _new_recording_utterance(db_conn, session_id)
    await db_conn.execute(
        "update utterances set audio_url = $2 where id = $1",
        utterance_id,
        recording_url(session_id, utterance_id),
    )
    other_session_id = await _new_shadowing_session(db_conn)
    intruder = recording_path(tmp_path, other_session_id, utterance_id)
    intruder.parent.mkdir(parents=True, exist_ok=True)
    intruder.write_bytes(FRAMES)

    assert await load_recording(db_conn, tmp_path, other_session_id, utterance_id) is None


def test_media_type_declares_the_raw_pcm_parameters() -> None:
    """헤더가 없으므로 **표본율·채널을 Content-Type 이 말해야 한다** (§4.4).

    `lib/audio.ts` 가 실측으로 적어 둔 사실이 그 근거다: 헤더 없는 PCM 은 `new Audio()` 로
    디코드되지 않으므로 프론트가 이 파라미터를 읽어 재생 큐에 넣는다.
    """
    assert RECORDING_MEDIA_TYPE == "audio/L16; rate=16000; channels=1"
