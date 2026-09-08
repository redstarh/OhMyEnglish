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

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfoNotFoundError

import asyncpg
import pytest

from app.services.recordings import (
    RECORDING_MEDIA_TYPE,
    day_start_for,
    finalize_recording,
    load_recording,
    pending_recording_path,
    purge_expired_recordings,
    recording_dir,
    recording_path,
    recording_url,
    sweep_orphan_recording_files,
)

FRAMES = b"\x00\x01" * 160  # raw LPCM 16kHz·16bit·mono 한 프레임 분량 (헤더 없음)


async def _new_shadowing_session(
    conn: asyncpg.Connection,
    *,
    status: str = "active",
    timezone: str = "Asia/Seoul",
    user_id: UUID | None = None,
) -> UUID:
    """사용자·세션을 직접 insert 한다 — `db_conn` 은 시드를 하지 않는다(`H-I`).

    기본값이 `active`/`Asia/Seoul` 인 것은 **표의 기본값과 같다** — 그래서 만료를 재지 않는
    단정들이 §5.4 의 예외(진행 중 세션은 삭제하지 않는다)에 자동으로 들어간다.

    `user_id` 를 받는 이유 둘: **한 사용자가 세션 여럿을 갖는 상태**를 만들 수 있어야 하고,
    스윕의 사용자 순서(`order by usr.id`)를 **결정론적으로** 만들 수 있어야 한다. 후자가 없으면
    「한 사람의 잘못된 tz 가 나머지를 막지 않는다」를 재는 단정이 uuid 순서에 따라 우연히 통과한다
    (2026-09-08 에 실제로 그랬다).
    """
    if user_id is None:
        user_id = await conn.fetchval(
            "insert into users (display_name, timezone) values ('Recording Test User', $1) "
            "returning id",
            timezone,
        )
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode, status) values ($1, 'shadowing', $2) "
        "returning id",
        user_id,
        status,
    )


async def _new_learner(conn: asyncpg.Connection, *, timezone: str, uuid_prefix: str) -> UUID:
    """id 를 **직접 지정한** 학습자 — 스윕이 사용자를 `order by usr.id` 로 돌기 때문이다.

    ⚠️ id 를 무작위로 두면 「잘못된 tz 를 만난 뒤에도 나머지가 처리된다」가 **순서 운에 따라
    통과한다.** 잘못된 tz 사용자를 앞에 세워야 그 단정에 판별력이 생긴다.
    """
    return await conn.fetchval(
        "insert into users (id, display_name, timezone) values ($1, 'Ordered Learner', $2) "
        "returning id",
        UUID(f"{uuid_prefix}-0000-0000-0000-000000000000"),
        timezone,
    )


async def _new_recording_utterance(
    conn: asyncpg.Connection,
    session_id: UUID,
    *,
    created_at: datetime | None = None,
    sequence_no: int = 1,
) -> UUID:
    """`audio_url` 이 아직 null 인 낭독 발화. 011 의 CHECK 가 이 조합만 허용한다.

    `created_at` 을 받는 이유: 만료 경계가 그 값에 걸리므로 **과거 녹음을 만들 수 있어야** 한다.
    기본값(`None`)이면 표의 `now()` 가 찍는다.
    """
    return await conn.fetchval(
        "insert into utterances "
        "(session_id, speaker, utterance_type, transcript, sequence_no, created_at) "
        "values ($1, 'user', 'shadowing_recording', 'I usually wake up at seven.', $2, "
        "coalesce($3::timestamptz, now())) returning id",
        session_id,
        sequence_no,
        created_at,
    )


async def _stored(
    conn: asyncpg.Connection, root: Path, session_id: UUID, utterance_id: UUID
) -> None:
    """파일과 포인터가 **둘 다** 있는 상태로 만든다 — 접근 가능한 녹음."""
    path = recording_path(root, session_id, utterance_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(FRAMES)
    await conn.execute(
        "update utterances set audio_url = $2 where id = $1",
        utterance_id,
        recording_url(session_id, utterance_id),
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


# ── 「당일이 지났다」의 경계 (AC#4 · 설계서 §5.2·§5.3) ──────────────────────────────
#
# ⛔ **`current_date` 를 쓰지 않는다.** 설계 세션이 공유 DB 에서 직접 관측한 값이 그 근거다:
# `current_date` = 2026-09-07 인데 `(now() at time zone 'Asia/Seoul')` = 2026-09-08 이었다
# (`SHOW TimeZone` = UTC). 그 값으로 판정하면 **학습자가 아직 비교하지 못한 녹음이 하루 일찍
# 사라지고 되돌릴 수 없다.** 타임존의 정본은 `users.timezone` 컬럼이다.
#
# 아래 기대값은 계산한 것이 아니라 **경계의 정의**다: 학습자의 현재 달력 날짜가 시작한 절대 시각.


def test_day_start_rejects_a_naive_now() -> None:
    """앱 경계에서 naive datetime 을 거부한다 — `jobs.py` 의 `_require_aware` 와 같은 방어다.

    조용히 바인딩되면 서버 오프셋만큼 시각이 밀리고, 그 밀림이 **되돌릴 수 없는 삭제**의 경계를
    움직인다.
    """
    with pytest.raises(ValueError):
        day_start_for("Asia/Seoul", now=datetime(2026, 9, 8, 2, 45))


def test_day_start_uses_the_learner_timezone_not_the_server_date() -> None:
    """설계서 §5.1 이 관측한 그 순간을 그대로 잰다.

    `2026-09-07 17:45:58+00` 은 서버 날짜로 9월 7일이지만 학습자(KST)에게는 **9월 8일**이다.
    경계는 KST 9월 8일 00:00 = UTC 9월 7일 15:00 이어야 한다 — `current_date`(9월 7일)를 썼다면
    경계가 하루 앞서 학습자의 오늘 녹음까지 삭제 대상이 됐다.
    """
    now = datetime(2026, 9, 7, 17, 45, 58, tzinfo=UTC)

    assert day_start_for("Asia/Seoul", now=now) == datetime(2026, 9, 7, 15, 0, tzinfo=UTC)


def test_day_start_moves_forward_the_moment_local_midnight_passes() -> None:
    """자정 직전·직후가 서로 다른 날을 가리킨다 — 되돌릴 수 없는 판정이라 경계값을 잰다."""
    just_before = datetime(2026, 9, 7, 14, 59, 59, tzinfo=UTC)  # KST 9/7 23:59:59
    just_after = datetime(2026, 9, 7, 15, 0, 0, tzinfo=UTC)  # KST 9/8 00:00:00

    assert day_start_for("Asia/Seoul", now=just_before) == datetime(2026, 9, 6, 15, 0, tzinfo=UTC)
    assert day_start_for("Asia/Seoul", now=just_after) == datetime(2026, 9, 7, 15, 0, tzinfo=UTC)


def test_day_start_handles_a_dst_zone_without_inventing_a_local_midnight() -> None:
    """⛔ `replace(hour=0, …)` 를 쓰지 않는 이유가 이 단정이다 (§5.2 의 주석).

    DST 가 있는 지역에서는 **존재하지 않는 지역 자정**이 만들어질 수 있다. 날짜와 tzinfo 로 다시
    조립하면 `zoneinfo` 가 fold 규칙으로 푼다. 미국 동부 DST 종료일(2026-11-01) 하루를 잰다 —
    그날 자정은 EDT(UTC-4)이므로 경계가 `2026-11-01 04:00Z` 다.
    """
    now = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)

    assert day_start_for("America/New_York", now=now) == datetime(2026, 11, 1, 4, 0, tzinfo=UTC)


def test_day_start_rejects_an_unknown_timezone() -> None:
    """⛔ `users.timezone` 에는 CHECK 가 없다(설계 세션이 조회로 확인했다).

    그래서 잘못된 값이 실재할 수 있고, **그것이 한 사람만 막아야 한다** — 집합 UPDATE 안에서
    터지면 한 사람의 값이 모든 사람의 삭제를 막는다(§5.2 의 이유 1). 여기서 예외 종류를 못
    박아 두면 스윕이 그 사용자만 건너뛸 수 있다.
    """
    with pytest.raises(ZoneInfoNotFoundError):
        day_start_for("Not/AZone", now=datetime(2026, 9, 8, tzinfo=UTC))


# ── 조회 시점 차단 (AC#4 · 설계서 §6.4) ────────────────────────────────────────────
#
# ⛔ **워커에 개인정보를 걸지 않는다.** `WORKER_ENABLED=false` 로 며칠을 돌리면 스윕이 한 번도
# 돌지 않는다 — 그동안 접근이 열려 있으면 「당일이 지나면 삭제」가 **워커 기동 여부에 걸린
# 약속**이 된다. 그래서 조회가 같은 경계 함수를 다시 계산해 스스로 닫는다.
#
# ⚠️ 스윕과 조회가 **같은 함수 하나**(`day_start_for`)를 부르는 것이 계약이다 — 두 곳에서 각자
# 계산하면 갈라진다(`009_drill_turns.sql` 이 "두 곳에 세면 갈라진다"로 적어 둔 규칙과 같다).

NOON_KST = datetime(2026, 9, 8, 3, 0, tzinfo=UTC)  # KST 9/8 12:00


@pytest.mark.asyncio
async def test_load_refuses_a_recording_from_a_past_learner_day(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """당일이 지난 녹음은 스윕이 돌기 전에도 접근 불가다."""
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(
        db_conn, session_id, created_at=datetime(2026, 9, 7, 3, 0, tzinfo=UTC)
    )
    await _stored(db_conn, tmp_path, session_id, utterance_id)

    assert await load_recording(db_conn, tmp_path, session_id, utterance_id, now=NOON_KST) is None


@pytest.mark.asyncio
async def test_load_still_serves_a_past_day_recording_while_the_session_runs(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ **§5.4 의 예외.** 자정을 넘기며 진행되는 세션의 녹음은 대상이 아니다.

    23:58 에 만든 녹음을 00:01 에 막으면 **학습자가 지금 비교하려는 것이 사라진다.** 캡틴 결정의
    문구가 *"비교된 오디오는 당일이 지나면 삭제한다"* 이므로 아직 비교 중인 것은 대상이 아니다.
    """
    session_id = await _new_shadowing_session(db_conn, status="active")
    utterance_id = await _new_recording_utterance(
        db_conn, session_id, created_at=datetime(2026, 9, 7, 14, 58, tzinfo=UTC)
    )
    await _stored(db_conn, tmp_path, session_id, utterance_id)

    assert await load_recording(db_conn, tmp_path, session_id, utterance_id, now=NOON_KST) == FRAMES


@pytest.mark.asyncio
async def test_load_serves_a_recording_made_today_in_the_learner_timezone(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """학습자의 오늘 녹음은 세션이 끝났어도 접근 가능하다 — 당일이 지나지 않았다."""
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(
        db_conn,
        session_id,
        created_at=datetime(2026, 9, 7, 16, 0, tzinfo=UTC),  # KST 9/8 01:00
    )
    await _stored(db_conn, tmp_path, session_id, utterance_id)

    assert await load_recording(db_conn, tmp_path, session_id, utterance_id, now=NOON_KST) == FRAMES


@pytest.mark.asyncio
async def test_the_learner_timezone_decides_the_boundary_not_the_server(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ **`current_date` 를 쓰면 이 두 사용자가 같은 판정을 받는다 — 그것이 틀렸다.**

    `2026-09-07 16:00Z` 는 KST 학습자에게 **오늘**(9/8 01:00)이고 UTC 학습자에게는
    **어제**(9/7 16:00)다. 같은 녹음 시각·같은 서버 날짜인데 판정이 갈려야 한다.
    """
    kst_session = await _new_shadowing_session(db_conn, status="completed", timezone="Asia/Seoul")
    utc_session = await _new_shadowing_session(db_conn, status="completed", timezone="UTC")
    made_at = datetime(2026, 9, 7, 16, 0, tzinfo=UTC)
    kst_utterance = await _new_recording_utterance(db_conn, kst_session, created_at=made_at)
    utc_utterance = await _new_recording_utterance(db_conn, utc_session, created_at=made_at)
    await _stored(db_conn, tmp_path, kst_session, kst_utterance)
    await _stored(db_conn, tmp_path, utc_session, utc_utterance)

    assert (
        await load_recording(db_conn, tmp_path, kst_session, kst_utterance, now=NOON_KST) == FRAMES
    )
    assert await load_recording(db_conn, tmp_path, utc_session, utc_utterance, now=NOON_KST) is None


@pytest.mark.asyncio
async def test_load_closes_when_the_learner_timezone_is_unusable(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ 경계를 계산할 수 없으면 **닫는 쪽으로 넘어진다.**

    `users.timezone` 에는 CHECK 가 없으므로 잘못된 값이 실재할 수 있다. 그때 바이트를 내주면
    「당일이 지나면 삭제」가 **잘못된 설정값 하나로 무력화된다** — 녹음은 학습자 음성이므로
    판정 불가는 거부여야 한다. 삭제 스윕의 처리(그 사용자만 건너뛴다)와 방향이 반대인 것은
    의도다: 스윕은 열어 두고 넘어가면 되지만 조회는 그럴 수 없다.
    """
    session_id = await _new_shadowing_session(db_conn, status="completed", timezone="Not/AZone")
    utterance_id = await _new_recording_utterance(db_conn, session_id)
    await _stored(db_conn, tmp_path, session_id, utterance_id)

    assert await load_recording(db_conn, tmp_path, session_id, utterance_id, now=NOON_KST) is None


# ── 당일 경과 삭제 — 1다리 (AC#4 · 설계서 §6.2) ──────────────────────────────────
#
# **순서가 (a) 포인터 → (b) 파일인 것이 계약이다.** `database-schema.md` 가 요구하는 것은
# 「즉시 접근 불가」이므로 실패 시 **닫히는 쪽**으로 넘어져야 한다. 뒤집으면(파일 먼저) 크래시 후
# DB 는 "있다"고 하고 파일은 없어 **학습자에게 깨진 재생**이 남는다.


async def _pointer_and_file(
    conn: asyncpg.Connection, root: Path, session_id: UUID, utterance_id: UUID
) -> tuple[str | None, bool]:
    """(포인터, 파일 존재) — 두 다리의 상태를 한 번에 본다."""
    audio_url = await conn.fetchval("select audio_url from utterances where id = $1", utterance_id)
    return audio_url, recording_path(root, session_id, utterance_id).is_file()


@pytest.mark.asyncio
async def test_purge_clears_the_pointer_and_deletes_the_bytes(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """만료된 녹음은 접근 불가가 되고 바이트가 사라진다 — 두 다리가 모두 걸린다."""
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(
        db_conn, session_id, created_at=datetime(2026, 9, 6, 3, 0, tzinfo=UTC)
    )
    await _stored(db_conn, tmp_path, session_id, utterance_id)

    purged = await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST)

    assert purged == [utterance_id]
    assert await _pointer_and_file(db_conn, tmp_path, session_id, utterance_id) == (None, False)


@pytest.mark.asyncio
async def test_purge_spares_a_running_session(db_conn: asyncpg.Connection, tmp_path: Path) -> None:
    """⛔ §5.4 — 진행 중 세션의 녹음은 대상이 아니다. 학습자가 지금 비교하는 중이다."""
    session_id = await _new_shadowing_session(db_conn, status="active")
    utterance_id = await _new_recording_utterance(
        db_conn, session_id, created_at=datetime(2026, 9, 6, 3, 0, tzinfo=UTC)
    )
    await _stored(db_conn, tmp_path, session_id, utterance_id)

    assert await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST) == []
    audio_url, exists = await _pointer_and_file(db_conn, tmp_path, session_id, utterance_id)
    assert audio_url is not None
    assert exists


@pytest.mark.asyncio
async def test_purge_spares_the_running_session_of_a_learner_who_also_has_a_finished_one(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ **§5.4 의 예외를 사용자 단위가 아니라 세션 단위로 적용한다.**

    스윕은 사용자 목록을 먼저 뽑고 사용자마다 대상을 고른다. 사용자 목록 쪽에도 같은
    `status <> 'active'` 조건이 있어서 **끝난 세션이 하나도 없는 학습자**는 애초에 목록에 뜨지
    않는다 — 그래서 대상 조회 쪽 조건을 지워도 위 단정이 통과한다(2026-09-08 에 직접 확인했다:
    32 passed). 실제 위험은 **한 학습자가 두 세션을 다 가진 지금 이 배치**다: 끝난 세션이 그를
    목록에 올리고, 대상 조회에 조건이 없으면 **진행 중 세션의 녹음까지 함께 지워진다.**
    """
    learner = await _new_learner(db_conn, timezone="Asia/Seoul", uuid_prefix="00000003")
    finished = await _new_shadowing_session(db_conn, status="completed", user_id=learner)
    running = await _new_shadowing_session(db_conn, status="active", user_id=learner)
    long_ago = datetime(2026, 9, 6, 3, 0, tzinfo=UTC)
    finished_utterance = await _new_recording_utterance(db_conn, finished, created_at=long_ago)
    running_utterance = await _new_recording_utterance(db_conn, running, created_at=long_ago)
    await _stored(db_conn, tmp_path, finished, finished_utterance)
    await _stored(db_conn, tmp_path, running, running_utterance)

    assert await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST) == [finished_utterance]
    running_pointer, running_file = await _pointer_and_file(
        db_conn, tmp_path, running, running_utterance
    )
    assert running_pointer is not None
    assert running_file


@pytest.mark.asyncio
async def test_purge_spares_a_recording_made_on_the_learner_today(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """당일이 지나지 않은 녹음은 남는다 — 경계가 **학습자의** 날짜다."""
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(
        db_conn,
        session_id,
        created_at=datetime(2026, 9, 7, 16, 0, tzinfo=UTC),  # KST 9/8 01:00
    )
    await _stored(db_conn, tmp_path, session_id, utterance_id)

    assert await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST) == []


@pytest.mark.asyncio
async def test_one_broken_timezone_does_not_block_everyone_else(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ **이것이 경계를 Python 에서 구하는 첫째 이유다** (§5.2).

    `users.timezone` 에는 CHECK 가 없어 잘못된 값이 실재할 수 있다. 집합 UPDATE 안에서
    `AT TIME ZONE` 이 그 값을 만나면 **한 사람의 잘못된 값이 모든 사람의 삭제를 막는다** —
    설계 세션이 직접 확인했다(`select now() at time zone 'Not/AZone'` → `ERROR`). 사용자별로
    Python 이 계산하면 그 사람만 건너뛰고 나머지는 낫는다.

    ⚠️ **잘못된 tz 사용자를 id 순서에서 앞에 세운다** — 스윕이 `order by usr.id` 로 돌기 때문이다.
    무작위 id 로 두면 정상 사용자가 먼저 처리되어 `continue` 를 `break` 로 바꿔도 통과한다
    (2026-09-08 에 직접 확인했다: 32 passed).
    """
    broken_user = await _new_learner(db_conn, timezone="Not/AZone", uuid_prefix="00000001")
    healthy_user = await _new_learner(db_conn, timezone="Asia/Seoul", uuid_prefix="00000002")
    broken = await _new_shadowing_session(db_conn, status="completed", user_id=broken_user)
    healthy = await _new_shadowing_session(db_conn, status="completed", user_id=healthy_user)
    long_ago = datetime(2026, 9, 6, 3, 0, tzinfo=UTC)
    broken_utterance = await _new_recording_utterance(db_conn, broken, created_at=long_ago)
    healthy_utterance = await _new_recording_utterance(db_conn, healthy, created_at=long_ago)
    await _stored(db_conn, tmp_path, broken, broken_utterance)
    await _stored(db_conn, tmp_path, healthy, healthy_utterance)

    purged = await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST)

    assert purged == [healthy_utterance]
    # 건너뛴 사용자의 녹음은 **그대로 남는다** — 값을 고치면 다음 사이클에 낫는다(§6.3).
    broken_pointer, broken_file = await _pointer_and_file(
        db_conn, tmp_path, broken, broken_utterance
    )
    assert broken_pointer is not None
    assert broken_file


@pytest.mark.asyncio
async def test_purge_clears_the_pointer_even_when_the_file_is_already_gone(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ **(b) 의 실패가 (a) 를 되돌리지 않는다** (§6.2).

    파일이 이미 없는 것은 흔한 상태다(2다리가 먼저 걷었거나 사람이 지웠다). 그때 예외로 터지면
    **접근 불가 확정이 미뤄지고** 그 사이 만료된 녹음이 계속 서빙된다 — 순서 계약이 지키려던
    것을 스스로 깨는 셈이다.
    """
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(
        db_conn, session_id, created_at=datetime(2026, 9, 6, 3, 0, tzinfo=UTC)
    )
    await _stored(db_conn, tmp_path, session_id, utterance_id)
    recording_path(tmp_path, session_id, utterance_id).unlink()

    assert await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST) == [utterance_id]
    assert (
        await db_conn.fetchval("select audio_url from utterances where id = $1", utterance_id)
        is None
    )


@pytest.mark.asyncio
async def test_purge_keeps_going_when_the_bytes_cannot_be_removed(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ **(b) 의 진짜 실패도 (a) 를 되돌리지 않는다** (§6.3).

    파일 자리에 디렉터리를 두어 `unlink` 가 `OSError` 를 내게 한다 — 권한·EBUSY 를 흉내내는 가장
    값싼 방법이다. 예외가 올라가면 **접근 불가 확정이 미뤄지고** 그 사이 만료된 녹음이 계속
    서빙된다. 남은 바이트는 고아 파일 정리 2다리가 소유한다.
    """
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(
        db_conn, session_id, created_at=datetime(2026, 9, 6, 3, 0, tzinfo=UTC)
    )
    await _stored(db_conn, tmp_path, session_id, utterance_id)
    path = recording_path(tmp_path, session_id, utterance_id)
    path.unlink()
    path.mkdir()

    assert await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST) == [utterance_id]
    assert (
        await db_conn.fetchval("select audio_url from utterances where id = $1", utterance_id)
        is None
    )
    assert path.is_dir()


@pytest.mark.asyncio
async def test_purging_twice_is_a_no_op(db_conn: asyncpg.Connection, tmp_path: Path) -> None:
    """멱등이다 — **그래서 attempts 카운터도 백오프도 두지 않는다** (§6.3).

    같은 조건을 다시 계산하므로 영구 실패해도 데이터가 어긋나지 않는다. `analysis_jobs` 의
    lease·attempts 는 **Claude 호출 중복 과금**을 막는 장치인데 여기에는 그 비용이 없다.
    """
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(
        db_conn, session_id, created_at=datetime(2026, 9, 6, 3, 0, tzinfo=UTC)
    )
    await _stored(db_conn, tmp_path, session_id, utterance_id)

    assert await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST) == [utterance_id]
    assert await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST) == []


@pytest.mark.asyncio
async def test_purge_stops_at_the_cycle_limit_and_resumes_next_time(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """사이클당 상한이 루프를 굶기지 않는다 (§6.2). 남은 것은 다음 사이클이 이어간다."""
    session_id = await _new_shadowing_session(db_conn, status="completed")
    long_ago = datetime(2026, 9, 6, 3, 0, tzinfo=UTC)
    for sequence_no in (1, 2, 3):
        utterance_id = await _new_recording_utterance(
            db_conn, session_id, created_at=long_ago, sequence_no=sequence_no
        )
        await _stored(db_conn, tmp_path, session_id, utterance_id)

    first = await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST, limit=2)
    second = await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST, limit=2)

    assert len(first) == 2
    assert len(second) == 1
    assert await purge_expired_recordings(db_conn, tmp_path, now=NOON_KST, limit=2) == []


# ── 고아 파일 정리 — 2다리 (AC#5 · 설계서 §6.2) ──────────────────────────────────
#
# ⛔ **이 다리는 선택이 아니라 필수다.** 1다리의 (b) 실패는 1다리로 재시도되지 않는다 — 조건이
# `audio_url is not null` 이라 (a) 가 이미 선 행은 **다시 선택되지 않는다.** 그래서 파일 쪽에서
# 걷는 다리가 없으면 바이트가 영구히 남는다.
#
# **이 다리가 잡는 것 셋**: ① 1다리의 unlink 실패 ② §4.5 의 중단된 쓰기(`.part`)
# ③ **FK cascade 로 사라진 포인터** — `utterances` 는 `learning_sessions` 에
# `on delete cascade` 이므로 세션을 지우면 포인터는 사라지고 파일은 남는다.


@pytest.mark.asyncio
async def test_orphan_sweep_keeps_files_that_still_have_a_pointer(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """살아있는 녹음을 지우지 않는다 — 이 다리가 가장 먼저 만족해야 하는 성질이다."""
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(db_conn, session_id)
    await _stored(db_conn, tmp_path, session_id, utterance_id)

    assert await sweep_orphan_recording_files(db_conn, tmp_path) == 0
    assert recording_path(tmp_path, session_id, utterance_id).is_file()


@pytest.mark.asyncio
async def test_orphan_sweep_removes_a_file_whose_pointer_is_gone(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """포인터가 없는 바이트를 걷는다 — 1다리의 (b) 실패가 여기서 낫는다."""
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(db_conn, session_id)
    await _stored(db_conn, tmp_path, session_id, utterance_id)
    await db_conn.execute("update utterances set audio_url = null where id = $1", utterance_id)

    assert await sweep_orphan_recording_files(db_conn, tmp_path) == 1
    assert not recording_path(tmp_path, session_id, utterance_id).exists()


@pytest.mark.asyncio
async def test_orphan_sweep_removes_an_interrupted_write(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """`.part` 는 언제나 고아다 (§4.5 의 2·3 사이에서 죽은 흔적)."""
    session_id = await _new_shadowing_session(db_conn, status="completed")
    pending = pending_recording_path(tmp_path, session_id, uuid4())
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_bytes(FRAMES)

    assert await sweep_orphan_recording_files(db_conn, tmp_path) == 1
    assert not pending.exists()


@pytest.mark.asyncio
async def test_orphan_sweep_does_not_touch_a_running_session(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ 진행 중 세션 디렉터리는 건드리지 않는다 — **지금 쓰는 중인 `.part` 가 있다.**

    §4.5 의 1단계가 그 파일에 프레임을 흘리고 있으므로, 여기서 지우면 학습자가 방금 낭독한
    것이 사라진다. §5.4 가 삭제에서 진행 중 세션을 뺀 것과 같은 판단이다.
    """
    session_id = await _new_shadowing_session(db_conn, status="active")
    pending = pending_recording_path(tmp_path, session_id, uuid4())
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_bytes(FRAMES)

    assert await sweep_orphan_recording_files(db_conn, tmp_path) == 0
    assert pending.is_file()


@pytest.mark.asyncio
async def test_orphan_sweep_removes_files_of_a_session_deleted_by_cascade(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """⛔ **2다리 없이는 영구 누출인 경로다** (§6.2 의 ③).

    `utterances` 는 `learning_sessions` 에 `on delete cascade` 이므로 **세션을 지우면 DB
    포인터는 사라지고 파일은 남는다.** 1다리는 포인터로 대상을 고르므로 이것을 영원히 못 본다.
    """
    session_id = await _new_shadowing_session(db_conn, status="completed")
    utterance_id = await _new_recording_utterance(db_conn, session_id)
    await _stored(db_conn, tmp_path, session_id, utterance_id)
    await db_conn.execute("delete from learning_sessions where id = $1", session_id)

    assert await sweep_orphan_recording_files(db_conn, tmp_path) == 1
    assert not recording_dir(tmp_path, session_id).exists()


@pytest.mark.asyncio
async def test_orphan_sweep_leaves_an_unrecognized_file_and_warns(
    db_conn: asyncpg.Connection, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """⛔ **이름 규칙에 맞지 않는 파일은 지우지 않고 경고한다.**

    설계서 §6.2 는 *"그 집합에 없는 파일"* 을 지우라고 적었지만, 알 수 없는 파일을 조용히 지우면
    **되돌릴 수 없다.** 남기고 경고하면 누출이 **보이는 상태**로 남아 사람이 판단할 수 있다 —
    이 절충은 내가 정한 것이고 뒤집으려면 이 단정을 뒤집으면 된다.
    """
    session_id = await _new_shadowing_session(db_conn, status="completed")
    stray = recording_dir(tmp_path, session_id) / "notes.txt"
    stray.parent.mkdir(parents=True, exist_ok=True)
    stray.write_text("사람이 둔 파일")

    with caplog.at_level("WARNING"):
        assert await sweep_orphan_recording_files(db_conn, tmp_path) == 0

    assert stray.is_file()
    assert "notes.txt" in caplog.text


@pytest.mark.asyncio
async def test_orphan_sweep_tolerates_a_missing_root(
    db_conn: asyncpg.Connection, tmp_path: Path
) -> None:
    """뿌리가 없다는 것은 **저장한 적이 없다는 뜻이라 오류가 아니다** (§6.3)."""
    assert await sweep_orphan_recording_files(db_conn, tmp_path / "not-created-yet") == 0


def test_media_type_declares_the_raw_pcm_parameters() -> None:
    """헤더가 없으므로 **표본율·채널을 Content-Type 이 말해야 한다** (§4.4).

    `lib/audio.ts` 가 실측으로 적어 둔 사실이 그 근거다: 헤더 없는 PCM 은 `new Audio()` 로
    디코드되지 않으므로 프론트가 이 파라미터를 읽어 재생 큐에 넣는다.
    """
    assert RECORDING_MEDIA_TYPE == "audio/L16; rate=16000; channels=1"
