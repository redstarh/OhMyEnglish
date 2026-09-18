"""낭독 판정 엔드포인트 (`TASK-208` · 결정 131).

설계: `docs/design/2026-09-18-read-aloud-judgment-design.md` §4.

⚠️ **재는 것은 라우터와 그 서비스의 몫이다** — 낱말 대조는 `tests/unit/test_readback.py` 가,
전사 계약은 `tests/unit/test_readback_transcribe.py` 가 소유한다. 여기서는 **요청할 때 계산하고
한 번만 계산하는 것**과 **접근 경계가 404 로 나가는 것**을 잰다.

⛔ **경로가 `/api/sessions/...` 아래인 것이 계약이다** — 낭독은 학습자 음성이므로 세션 경계가
개인정보 경계다(`api/shadowing.py` 머리말이 그 판단을 소유한다). 설계서 첫 판이
`/api/shadowing/recordings/...` 로 적었고 그것은 그 규칙과 어긋났다.

`api_client` 는 커밋된 행만 본다(라우터가 자기 커넥션을 연다) — `committed_session` 과 `db_pool` 을
함께 쓰는 이유가 그것이다. 어댑터는 `voice_adapter` 기본값이 `stub` 이라 스텁이 뜬다.
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

from app.audio_gateway.fixtures import FIXTURE_TURNS
from app.config import get_settings
from app.services.recordings import recording_path

FRAMES = b"\x7f\x00" * 320
# 스텁 어댑터가 학습자 발화로 내는 문장들 — 클립의 글을 이것과 같게 두면 판정이 전부 맞음이 된다.
# ⚠️ **셋을 이어 붙인다** — 전사는 조용해질 때까지 «모으므로»(`TASK-210`) 첫 답만이 아니다.
STUB_READBACK = " ".join(answer for _, answer in FIXTURE_TURNS)


@pytest_asyncio.fixture
async def audio_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, test_database: str
) -> AsyncIterator[Path]:
    monkeypatch.setenv("DATABASE_URL", test_database)
    monkeypatch.setenv("SHADOWING_AUDIO_ROOT", str(tmp_path))
    pin_settings_env(monkeypatch, keep=("DATABASE_URL", "SHADOWING_AUDIO_ROOT"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


async def _stored_recording(
    conn: asyncpg.Connection,
    root: Path,
    session_id: UUID,
    *,
    clip_transcript: str = STUB_READBACK,
    utterance_type: str = "shadowing_recording",
    with_pointer: bool = True,
    sequence_no: int = 1,
) -> UUID:
    utterance_id = await conn.fetchval(
        "insert into utterances (session_id, speaker, utterance_type, transcript, sequence_no) "
        "values ($1, 'user', $2, $3, $4) returning id",
        session_id,
        utterance_type,
        clip_transcript,
        sequence_no,
    )
    path = recording_path(root, session_id, utterance_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(FRAMES)
    if with_pointer:
        await conn.execute(
            "update utterances set audio_url = $2 where id = $1",
            utterance_id,
            f"/api/sessions/{session_id}/recordings/{utterance_id}",
        )
    return utterance_id


def _url(session_id: UUID, utterance_id: UUID) -> str:
    return f"/api/sessions/{session_id}/recordings/{utterance_id}/readback"


async def test_처음_부르면_전사를_얻어_저장하고_낱말_판정을_돌려준다(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session, audio_root: Path
) -> None:
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(conn, audio_root, committed_session.session_id)

    response = await api_client.post(_url(committed_session.session_id, utterance_id))

    assert response.status_code == 200
    body = response.json()
    assert body["readbackTranscript"] == STUB_READBACK
    assert body["clipTranscript"] == STUB_READBACK
    assert {word["verdict"] for word in body["words"]} == {"match"}
    assert len(body["words"]) == len(STUB_READBACK.split())
    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select readback_transcript from utterances where id = $1", utterance_id
        )
    assert stored == STUB_READBACK


async def test_이미_전사가_있으면_다시_전사하지_않는다(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session, audio_root: Path
) -> None:
    """⛔ 저장된 값이 스텁의 문장과 «다르게» 두어야 건너뛴 것을 볼 수 있다."""
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(conn, audio_root, committed_session.session_id)
        await conn.execute(
            "update utterances set readback_transcript = $2 where id = $1",
            utterance_id,
            "I usually go to gym",
        )

    response = await api_client.post(_url(committed_session.session_id, utterance_id))

    assert response.status_code == 200
    assert response.json()["readbackTranscript"] == "I usually go to gym"


async def test_다른_세션_아래에서는_판정하지_않는다(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session, audio_root: Path
) -> None:
    """⛔ 세션을 바꿔 넣은 요청이 통과하면 남의 낭독을 판정해 내용이 새어 나간다."""
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(conn, audio_root, committed_session.session_id)

    response = await api_client.post(_url(uuid4(), utterance_id))

    assert response.status_code == 404


async def test_전사가_이미_있어도_다른_세션_아래에서는_새어_나가지_않는다(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session, audio_root: Path
) -> None:
    """⛔ **이 갈래에서는 조회 쿼리의 세션 조건이 «유일한» 가드다.**

    전사가 이미 있으면 `load_recording` 을 아예 부르지 않으므로 그 함수의 세션 필터가 뒤를 받쳐
    주지 못한다. 앞의 「다른 세션」 테스트는 전사가 없는 상태라 `load_recording` 이 대신 막아
    **쿼리의 세션 조건을 지워도 통과했다**(2026-09-18 뮤테이션으로 관측). 그래서 이 테스트가 있다.
    """
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(conn, audio_root, committed_session.session_id)
        await conn.execute(
            "update utterances set readback_transcript = $2 where id = $1",
            utterance_id,
            "I usually go to the gym",
        )

    response = await api_client.post(_url(uuid4(), utterance_id))

    assert response.status_code == 404


async def test_녹음에_접근할_수_없으면_404_다(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session, audio_root: Path
) -> None:
    """포인터가 없으면 파일이 있어도 접근 불가다 — DB 가 접근 가능성의 정본이다."""
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(
            conn, audio_root, committed_session.session_id, with_pointer=False
        )

    response = await api_client.post(_url(committed_session.session_id, utterance_id))

    assert response.status_code == 404


async def test_낭독이_아닌_발화는_두_겹으로_막힌다(
    api_client: httpx.AsyncClient, db_pool: asyncpg.Pool, committed_session, audio_root: Path
) -> None:
    """일반 학습 발화에는 견줄 원본이 없다 — `transcript` 가 클립의 글이 아니라 학습자의 말이다.

    ⛔ **막는 것은 스키마 두 겹이고 서비스의 종류 필터는 그 뒤에 있다.**
    `utterances_audio_only_for_shadowing` 이 낭독이 아닌 발화에 **포인터**를 못 붙이게 하고,
    029 의 `utterances_readback_only_for_shadowing` 이 그런 발화에 **전사문**을 못 넣게 한다
    (둘 다 2026-09-18 실측으로 확인했다).
    ⚠️ **그래서 서비스의 종류 필터는 어떤 테스트로도 관측되지 않는다** — 뮤테이션으로 그 조건을
    지워도 이 테스트가 통과한다(직접 확인했다). 두 CHECK 가 그 경로를 미리 닫아 두기 때문이다.
    **그 필터는 스키마가 나중에 느슨해질 때를 위한 겹으로 남겨 둔다** — 지금 무엇을 막고 있다고
    적지 않는다.
    """
    async with db_pool.acquire() as conn:
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await _stored_recording(
                conn, audio_root, committed_session.session_id, utterance_type="learning"
            )
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(
            conn,
            audio_root,
            committed_session.session_id,
            utterance_type="learning",
            with_pointer=False,
            sequence_no=2,
        )

    response = await api_client.post(_url(committed_session.session_id, utterance_id))

    assert response.status_code == 404
