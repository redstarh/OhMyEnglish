"""낭독 판정 엔드포인트 (`TASK-208` · 결정 131).

설계: `docs/design/2026-09-18-read-aloud-judgment-design.md` §4.

⚠️ **재는 것은 라우터와 그 서비스의 몫이다** — 낱말 대조는 `tests/unit/test_readback.py` 가,
전사 계약은 `tests/unit/test_readback_transcribe.py` 가 소유한다. 여기서는 **요청할 때 계산하고
한 번만 계산하는 것**과 **접근 경계가 404 로 나가는 것**을 잰다.

⛔ **경로가 `/api/sessions/...` 아래인 것이 계약이다** — 낭독은 학습자 음성이므로 세션 경계가
개인정보 경계다(`api/shadowing.py` 머리말이 그 판단을 소유한다). 설계서 첫 판이
`/api/shadowing/recordings/...` 로 적었고 그것은 그 규칙과 어긋났다.

`api_client` 는 커밋된 행만 본다(라우터가 자기 커넥션을 연다) — `committed_session` 과 `db_pool` 을
함께 쓰는 이유가 그것이다.

⛔ **설정은 `nova` 를 가리키고 어댑터 «대역»만 스텁이다** (`TASK-213`). 기본값 `stub` 으로는 판정이
503 이므로(픽스처가 학습자 문장을 발명해 영구 저장되는 것을 막는다) 판정 경로를 재는 테스트가
기본 설정에서는 아예 열리지 않는다. 그 503 갈래는 이 파일의 전용 테스트가 잰다.
"""

from __future__ import annotations

import ast
import inspect
from collections.abc import AsyncIterator
from pathlib import Path
from types import ModuleType
from uuid import UUID, uuid4

import asyncpg
import httpx
import pytest
import pytest_asyncio
from conftest import pin_settings_env

from app.api import results as results_module
from app.audio_gateway.fixtures import FIXTURE_TURNS
from app.audio_gateway.port import Transcriber
from app.audio_gateway.stub import StubVoiceAdapter
from app.audio_gateway.transcribe import transcribe_readback
from app.config import get_settings
from app.services.recordings import recording_path

FRAMES = b"\x7f\x00" * 320
# 스텁 어댑터가 학습자 발화로 내는 문장들 — 클립의 글을 이것과 같게 두면 판정이 전부 맞음이 된다.
# ⚠️ **셋을 이어 붙인다** — 전사는 조용해질 때까지 «모으므로»(`TASK-210`) 첫 답만이 아니다.
STUB_READBACK = " ".join(answer for _, answer in FIXTURE_TURNS)


def _stub_transcriber() -> Transcriber:
    """스텁 어댑터를 **실물 구동부로** 흘리는 전사기 (`TASK-214`).

    ⛔ **전사문을 곧바로 돌려주는 대역으로 바꾸지 않는다** — 그러면 프레임 흘리기·침묵·조용함
    판정이 통째로 빠지고 이 파일이 「전사기가 무엇이든 200」만 재게 된다. `TASK-214` 전의 대역은
    `create_voice_adapter` 자리에 걸려 `transcribe_readback` 을 그대로 탔으므로 **그 성질을
    유지하는 것이 회귀 없음의 조건이다.**
    """

    async def transcribe(pcm: bytes) -> str:
        return await transcribe_readback(pcm, make_adapter=StubVoiceAdapter)

    return transcribe


@pytest_asyncio.fixture
async def audio_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, test_database: str
) -> AsyncIterator[Path]:
    monkeypatch.setenv("DATABASE_URL", test_database)
    monkeypatch.setenv("SHADOWING_AUDIO_ROOT", str(tmp_path))
    monkeypatch.setenv("VOICE_ADAPTER", "nova")
    pin_settings_env(monkeypatch, keep=("DATABASE_URL", "SHADOWING_AUDIO_ROOT", "VOICE_ADAPTER"))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def transcriber_band(monkeypatch: pytest.MonkeyPatch) -> None:
    """설정이 `nova` 인 동안 전사기 **대역**만 스텁 어댑터로 바꾼다 (`TASK-213` · `TASK-214`).

    ⛔ **대역 없이 `nova` 를 두면 라우터가 실물 스트림을 연다** — 테스트가 AWS 를 부른다.
    ⚠️ 팩토리의 분기 자체는 `tests/integration/test_gateway.py` 가 잰다. 여기서 재는 것은 라우터다.
    ⚠️ **대역을 «전사기» 자리에 건다** (`TASK-214`) — 라우터가 아는 것이 `Transcriber` 하나뿐이라
    어댑터 자리에 걸 대역이 이 층에 더는 없다. 실물 구동부는 `transcribe_readback` 이 그대로 타므로
    스텁 어댑터를 흘려보내는 경로는 이전과 같다.
    """
    monkeypatch.setattr(
        results_module,
        "create_transcriber",
        lambda *_args, **_kwargs: _stub_transcriber(),
    )


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
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_session,
    audio_root: Path,
    transcriber_band: None,
) -> None:
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(conn, audio_root, committed_session.session_id)

    response = await api_client.post(_url(committed_session.session_id, utterance_id))

    assert response.status_code == 200
    body = response.json()
    assert body["readback_transcript"] == STUB_READBACK
    assert body["clip_transcript"] == STUB_READBACK
    assert {word["verdict"] for word in body["words"]} == {"match"}
    assert len(body["words"]) == len(STUB_READBACK.split())
    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select readback_transcript from utterances where id = $1", utterance_id
        )
    assert stored == STUB_READBACK


@pytest.mark.parametrize("adapter", ["stub", "stub_unresponsive"])
async def test_전사기가_없으면_503_이고_아무것도_저장하지_않는다(
    monkeypatch: pytest.MonkeyPatch,
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_session,
    audio_root: Path,
    adapter: str,
) -> None:
    """⛔ **픽스처 어댑터로는 판정하지 않는다** (`TASK-213`).

    스텁은 학습자 문장을 **발명**하므로 그것이 `readback_transcript` 에 들어가고, 전사가 있으면
    다시 계산하지 않으므로(결정 131) 그 오염이 **영구**다. 개발용 서버가 평소 `stub` 으로 떠 있어
    실제로 밟기 쉬운 경로였다 — 2026-09-18 `/simplify` 의 고도 각도가 잡았다.

    ⚠️ **503 과 「저장되지 않았다」를 «둘 다» 잰다** — 상태 코드만 재면 가드를 전사 «뒤»로 옮겨도
    통과하는데, 그 자리에서는 이미 오염 행이 생긴 뒤다.
    ⚠️ **픽스처 둘을 함께 잰다** — `stub_unresponsive` 는 전사를 내지 않아 오염은 없지만, 「전사기가
    없다」를 「못 알아들었다」로 보이면 학습자가 영원히 다시 누른다(`api/vocab.py` 와 같은 판단).
    """
    monkeypatch.setenv("VOICE_ADAPTER", adapter)
    get_settings.cache_clear()
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(conn, audio_root, committed_session.session_id)

    response = await api_client.post(_url(committed_session.session_id, utterance_id))

    assert response.status_code == 503
    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select readback_transcript from utterances where id = $1", utterance_id
        )
    assert stored is None


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
    assert response.json()["readback_transcript"] == "I usually go to gym"


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


async def test_판정_라우터가_어댑터에_사용량_sink_를_넘긴다(
    monkeypatch: pytest.MonkeyPatch,
    api_client: httpx.AsyncClient,
    db_pool: asyncpg.Pool,
    committed_session,
    audio_root: Path,
) -> None:
    """⛔ **배선 누락을 잡는 자리다** (`TASK-212`).

    `create_voice_adapter` 의 `usage_sink` 기본값이 `None` 이라 호출부에서 그 인자를 떼면
    Nova 토큰 기록이 **조용히** 꺼진다. 소켓 계층에는 그 대역이 있는데(`test_ws.py` 의
    `_capture_factory_args`) 낭독 판정이 **둘째 배선 지점**이 되면서 그 자리가 무보호였다 —
    2026-09-18 `/simplify` 의 고도 각도가 그것을 지적했다.
    ⛔ **대역이 `usage_sink` 에 기본값을 두지 않는다** — 두면 라우터가 넘기지 않아도 조용히
    통과한다.
    ⚠️ **재는 자리가 `create_transcriber` 로 옮겨졌다** (`TASK-214`) — 라우터가 직접 부르는 것이
    그쪽이고, sink 를 어댑터까지 옮기는 책임은 팩토리가 가진다(`test_gateway.py` 가 그것을 잰다).
    """
    seen: dict[str, object] = {}

    def spy(settings: object, *, usage_sink: object) -> Transcriber:
        seen["usage_sink"] = usage_sink
        return _stub_transcriber()

    monkeypatch.setattr(results_module, "create_transcriber", spy)
    async with db_pool.acquire() as conn:
        utterance_id = await _stored_recording(conn, audio_root, committed_session.session_id)

    response = await api_client.post(_url(committed_session.session_id, utterance_id))

    assert response.status_code == 200
    assert seen["usage_sink"] is not None


# ── import 그래프 — HTTP 층은 대화형 어댑터를 모른다 (`TASK-214` · 결정 131) ─────


def _imported_names(module: ModuleType) -> list[str]:
    """관용구는 `tests/integration/test_gateway.py` §④ 와 같다 — 그쪽이 먼저 쓴 형태다.

    ⚠️ **소스 텍스트를 읽는 방식이라 런타임 뮤테이션으로는 재지 못한다** — 판별력을 확인할 때는
    변이를 `import` 문 자체로 준다(그쪽 주석이 그 요령을 가진다).
    """
    tree = ast.parse(inspect.getsource(module))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
            names.extend(alias.name for alias in node.names)
    return names


def test_판정_라우터가_대화형_어댑터를_import_하지_않는다() -> None:
    """⛔ **결정 131 의 경계를 문서가 아니라 검사가 지킨다** (`TASK-214`).

    이 단정이 없으면 다음 사람이 라우터에서 `create_voice_adapter` 를 다시 불러도 아무것도 깨지지
    않고, 그러면 *"배치 STT 로 옮기면 전사 함수 하나만 갈면 된다"* 가 조용히 거짓이 된다 — 고칠
    자리가 구현·서비스·라우터 셋으로 돌아간다.

    ⚠️ **이름을 대소문자 접어 금지한다** — 막고 싶은 것이 `VoiceAdapter`(포트)와
    `create_voice_adapter`(팩토리) 둘이고 표기가 갈린다. 라우터가 받아야 하는 것은 `Transcriber`
    하나이며, 어느 구현이 붙는지는 팩토리가 안다(G3).
    """
    names = [name.lower() for name in _imported_names(results_module)]
    assert all("voice_adapter" not in name for name in names), names
    assert all("voiceadapter" not in name for name in names), names
