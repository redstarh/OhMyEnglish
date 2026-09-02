"""I-4 — `active` 고아 세션 리퍼 (`app.services.sessions.reap_orphan_sessions`).

**왜 필요한가**: 종료 기록 전에 프로세스가 죽으면 `end_session`이 돌지 않아 세션이
`active`로 영구히 남는다. I-1 회복 스윕(`flush_ended_sessions`)은 **정의상 `active`를
건너뛰므로**(진행 중 세션의 자라는 묶음을 걸면 I-1 오탐이 되살아난다) 그 세션의 발화
묶음은 아무도 걷지 않는다. 리퍼가 그 세션을 `failed`로 닫아 스윕 대상으로 만든다.
근거와 캡틴 결정은 `TASKS.md` **I-4**가 소유한다.

⚠️ **경과 시간을 `sleep`으로 만들지 않는다.** `db_conn`은 롤백되는 한 트랜잭션이고
PostgreSQL의 `now()`는 **트랜잭션 시작 시각에 고정**되므로, 테스트 안에서 기다려도
`now()`는 움직이지 않는다 — 유예를 넘기는 상황은 오직 행의 시각을 과거로 밀어서만
만들 수 있다. 벽시계에 의존하지 않으므로 느린 CI에서도 흔들리지 않는다.

⚠️ 이 파일의 `_backdate`는 **테스트가 만든 합성 데이터의 시각을 미는 것**이고,
"표시가 틀렸다고 저장된 `timestamptz`를 변환해 UPDATE한다"(전역 시각 규약 4번의
금지 사항)와는 다른 조작이다. 실제 기록된 순간을 이동시키는 코드는 앱에 없다.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
from conftest import backdate_session as _backdate

from app.services.sessions import ORPHAN_IDLE_GRACE, end_session, reap_orphan_sessions
from app.services.utterances import save_final_transcript

ANSWER = "I usually go to gym after work."
AGENT_REPLY = "That sounds good. How often do you go?"

# 유예를 확실히 넘기는 값과 확실히 못 넘기는 값. 경계 자체(정확히 60초)는 재지 않는다 —
# `now()`가 트랜잭션에 고정되어 있어도 두 UPDATE 사이의 마이크로초 차이가 남기 때문이다.
PAST_THE_GRACE = timedelta(minutes=10)
WITHIN_THE_GRACE = timedelta(seconds=30)


async def _new_session(conn: asyncpg.Connection) -> UUID:
    user_id = await conn.fetchval(
        "insert into users (display_name) values ('Reaper Test User') returning id"
    )
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        user_id,
    )


async def _state(conn: asyncpg.Connection, session_id: UUID) -> tuple[str, datetime | None]:
    row = await conn.fetchrow(
        "select status, ended_at from learning_sessions where id = $1", session_id
    )
    assert row is not None
    return row["status"], row["ended_at"]


# T0 — 유예를 넘겨 조용한 `active` 세션을 `failed`로 닫고 그 id를 돌려준다.
async def test_reaper_closes_an_active_session_silent_past_the_grace(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    await save_final_transcript(db_conn, session_id, ANSWER)
    await _backdate(db_conn, session_id, by=PAST_THE_GRACE)

    assert await reap_orphan_sessions(db_conn) == [session_id]

    status, ended_at = await _state(db_conn, session_id)
    assert status == "failed"
    assert ended_at is not None, "리퍼가 종료 시각을 남기지 않으면 결과 화면이 진행 중처럼 보인다"


# T0 — 유예 안에 말한 세션은 건드리지 않는다. 사용자가 잠깐 뜸을 들인 것과
# 프로세스가 죽은 것을 구분하는 것이 이 함수의 전부다.
async def test_reaper_leaves_a_session_that_spoke_within_the_grace(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    await save_final_transcript(db_conn, session_id, ANSWER)
    await _backdate(db_conn, session_id, by=WITHIN_THE_GRACE)

    assert await reap_orphan_sessions(db_conn) == []
    assert await _state(db_conn, session_id) == ("active", None)


# T0 — **live 가드**: 살아있는 WebSocket이 소유한 세션은 유예를 넘겨도 건드리지 않는다.
# 이것이 없으면 60초 침묵한 진행 중 세션이 닫히고, 그 직후 스윕이 자라는 중인 묶음을
# 걷어 조각 하나가 완전한 문장처럼 분석되는 I-1 오탐이 되살아난다.
# 세션 2개로 재는 이유: 가드가 **행마다** 걸리는지(문장 전체를 무력화하는 것이 아닌지)를 본다.
async def test_reaper_skips_a_session_a_live_connection_still_owns(db_conn: asyncpg.Connection):
    live_id = await _new_session(db_conn)
    orphan_id = await _new_session(db_conn)
    for session_id in (live_id, orphan_id):
        await save_final_transcript(db_conn, session_id, ANSWER)
        await _backdate(db_conn, session_id, by=PAST_THE_GRACE)

    assert await reap_orphan_sessions(db_conn, live_session_ids={live_id}) == [orphan_id]

    assert await _state(db_conn, live_id) == ("active", None)
    assert (await _state(db_conn, orphan_id))[0] == "failed"


# T2 — 발화가 한 건도 없는 세션은 `started_at`으로 잰다. 연결만 열고 아무 말도 못한 채
# 죽은 세션(가장 흔한 고아)이 여기 걸린다.
async def test_reaper_measures_a_session_with_no_utterances_from_its_start(
    db_conn: asyncpg.Connection,
):
    session_id = await _new_session(db_conn)
    await _backdate(db_conn, session_id, by=PAST_THE_GRACE)

    assert await reap_orphan_sessions(db_conn) == [session_id]
    assert (await _state(db_conn, session_id))[0] == "failed"


# T2 — 활동은 **화자를 가리지 않는다.** agent가 방금 말했으면 사용자가 10분 전에 말했어도
# 그 세션은 살아 있다 — 에이전트가 길게 답하는 동안 세션이 닫히면 안 된다.
async def test_reaper_counts_agent_speech_as_activity(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    await save_final_transcript(db_conn, session_id, ANSWER)
    await _backdate(db_conn, session_id, by=PAST_THE_GRACE)
    await save_final_transcript(db_conn, session_id, AGENT_REPLY, speaker="agent")

    assert await reap_orphan_sessions(db_conn) == []
    assert await _state(db_conn, session_id) == ("active", None)


# T3 — 이미 끝난 세션은 다시 닫지 않는다. 다시 닫으면 `ended_at`이 실제 종료 시각에서
# 리퍼가 돈 시각으로 밀려 기록이 손상된다.
async def test_reaper_does_not_reclose_a_session_that_already_ended(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    await save_final_transcript(db_conn, session_id, ANSWER)
    await end_session(db_conn, session_id, "completed")
    _, ended_at_before = await _state(db_conn, session_id)
    await _backdate(db_conn, session_id, by=PAST_THE_GRACE)

    assert await reap_orphan_sessions(db_conn) == []
    assert await _state(db_conn, session_id) == ("completed", ended_at_before)


# T2 — live 집합에 이 프로세스가 모르는 id가 섞여 있어도(빈 집합·낯선 uuid) 판정은 그대로다.
async def test_reaper_ignores_live_ids_that_are_not_active_sessions(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    await _backdate(db_conn, session_id, by=PAST_THE_GRACE)

    assert await reap_orphan_sessions(db_conn, live_session_ids={uuid4(), uuid4()}) == [session_id]


# 발명값이다 — 캡틴 결정(2026-09-03: "1분 이상 답이 없으면 failed로 닫는다").
# 값을 조용히 바꾸면 이 단정이 걸린다.
def test_orphan_idle_grace_is_the_captain_decided_value():
    assert ORPHAN_IDLE_GRACE == timedelta(seconds=60)
