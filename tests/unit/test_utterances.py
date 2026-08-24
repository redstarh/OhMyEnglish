"""Task 4 — `app.services.utterances` transcript persistence tests (AC W1 전반·W3·W6).

`save_final_transcript` must do two writes as one unit: append the utterance
with the next per-session `sequence_no`, and — only for a user's *learning*
speech — register its analysis job in the same transaction. The caller owns the
transaction (`app.db.tx()`), so these tests drive it inside the rolled-back
`db_conn` fixture and use a savepoint (`db_conn.transaction()`) to inject a
mid-transaction failure.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import asyncpg
import pytest

from app.services.jobs import claim_next, complete
from app.services.utterances import (
    UtteranceRow,
    pending_learning_utterances,
    save_final_transcript,
)

FIRST_TURN_ANSWER = "I usually go to gym after work."


async def _new_session(conn: asyncpg.Connection) -> UUID:
    user_id = await conn.fetchval(
        "insert into users (display_name) values ('Transcript Test User') returning id"
    )
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        user_id,
    )


async def _counts(conn: asyncpg.Connection) -> tuple[int, int]:
    utterances = await conn.fetchval("select count(*) from utterances")
    jobs = await conn.fetchval("select count(*) from analysis_jobs")
    return utterances, jobs


# ① 사용자 learning 발화 → utterances 1행 + analysis_jobs 1행
async def test_user_learning_transcript_is_saved_and_enqueued(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)

    row = await save_final_transcript(db_conn, session_id, FIRST_TURN_ANSWER)

    assert isinstance(row, UtteranceRow)
    assert row.session_id == session_id
    assert row.speaker == "user"
    assert row.utterance_type == "learning"
    assert row.transcript == FIRST_TURN_ANSWER
    assert row.sequence_no == 1
    assert row.created_at.tzinfo is not None  # timestamptz — naive 금지

    assert await _counts(db_conn) == (1, 1)
    job = await db_conn.fetchrow("select job_type, utterance_id, status from analysis_jobs")
    assert job is not None
    assert job["job_type"] == "analyze_utterance"
    assert job["utterance_id"] == row.id
    assert job["status"] == "pending"


# ① 같은 트랜잭션 — 중간 실패를 주입하면 발화와 job이 함께 롤백된다
async def test_transcript_and_job_roll_back_together_when_transaction_fails(
    db_conn: asyncpg.Connection,
):
    session_id = await _new_session(db_conn)

    with pytest.raises(RuntimeError, match="injected"):
        async with db_conn.transaction():  # savepoint = 호출자의 트랜잭션 경계
            row = await save_final_transcript(db_conn, session_id, FIRST_TURN_ANSWER)
            assert await _counts(db_conn) == (1, 1)  # 커밋 전에는 보인다
            assert row.sequence_no == 1
            raise RuntimeError("injected failure after enqueue")

    assert await _counts(db_conn) == (0, 0)  # 발화만 남거나 job만 남는 상태는 없다


# ② voice_command 발화는 저장되지만 job은 등록되지 않는다 (W6)
async def test_voice_command_transcript_is_saved_without_job(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)

    row = await save_final_transcript(
        db_conn, session_id, "Start a business roleplay.", utterance_type="voice_command"
    )

    assert row.utterance_type == "voice_command"
    assert await _counts(db_conn) == (1, 0)


# ③ agent 발화는 저장되지만 job은 등록되지 않는다
async def test_agent_transcript_is_saved_without_job(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)

    row = await save_final_transcript(
        db_conn, session_id, "What do you usually do after work?", speaker="agent"
    )

    assert row.speaker == "agent"
    assert row.utterance_type == "learning"  # agent도 learning 발화지만 분석 대상은 아니다
    assert await _counts(db_conn) == (1, 0)


# ④ 같은 (session_id, sequence_no) 강제 재insert → unique 위반 (W3 이중 commit 가드)
async def test_duplicate_session_sequence_no_violates_unique(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    row = await save_final_transcript(db_conn, session_id, FIRST_TURN_ANSWER)

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_conn.execute(
            "insert into utterances (session_id, speaker, transcript, sequence_no) "
            "values ($1, 'user', $2, $3)",
            session_id,
            FIRST_TURN_ANSWER,
            row.sequence_no,
        )


# ⑤ sequence_no는 세션 안에서 1,2,3으로 단조 증가한다
async def test_sequence_no_increases_monotonically_within_session(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)

    rows = [
        await save_final_transcript(db_conn, session_id, "I usually go to gym after work."),
        await save_final_transcript(db_conn, session_id, "I usually go to office by subway."),
        await save_final_transcript(db_conn, session_id, "I need to finish my homework tonight."),
    ]

    assert [row.sequence_no for row in rows] == [1, 2, 3]
    stored = await db_conn.fetch(
        "select sequence_no from utterances where session_id = $1 order by sequence_no", session_id
    )
    assert [record["sequence_no"] for record in stored] == [1, 2, 3]


# ⑤ 보강 — sequence_no는 세션 단위다 (다른 세션은 다시 1부터)
async def test_sequence_no_is_scoped_to_its_session(db_conn: asyncpg.Connection):
    first_session = await _new_session(db_conn)
    second_session = await _new_session(db_conn)

    await save_final_transcript(db_conn, first_session, FIRST_TURN_ANSWER)
    await save_final_transcript(db_conn, first_session, "I need to finish my homework tonight.")
    other = await save_final_transcript(db_conn, second_session, FIRST_TURN_ANSWER)

    assert other.sequence_no == 1


# pending_learning_utterances — 분석 입력은 사용자 learning 발화만이다
async def test_pending_learning_utterances_selects_only_user_learning_speech(
    db_conn: asyncpg.Connection,
):
    session_id = await _new_session(db_conn)
    learning = await save_final_transcript(db_conn, session_id, FIRST_TURN_ANSWER)
    await save_final_transcript(
        db_conn, session_id, "Stop the session.", utterance_type="voice_command"
    )
    await save_final_transcript(db_conn, session_id, "Nice, tell me more.", speaker="agent")

    pending = await pending_learning_utterances(db_conn)

    assert [row.id for row in pending] == [learning.id]
    assert pending[0].transcript == FIRST_TURN_ANSWER


# pending_learning_utterances — 분석이 끝난 발화는 더 이상 대기 목록에 없다
async def test_pending_learning_utterances_excludes_finished_analysis(
    db_conn: asyncpg.Connection,
):
    session_id = await _new_session(db_conn)
    await save_final_transcript(db_conn, session_id, FIRST_TURN_ANSWER)

    claimed = await claim_next(db_conn)
    assert claimed is not None
    assert len(await pending_learning_utterances(db_conn)) == 1  # running도 대기 중이다

    assert await complete(db_conn, claimed.id, claimed.lease_token) is True

    assert await pending_learning_utterances(db_conn) == []


# 존재하지 않는 세션에는 저장하지 않는다 (FK 경계)
async def test_save_rejects_unknown_session(db_conn: asyncpg.Connection):
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await save_final_transcript(db_conn, uuid4(), FIRST_TURN_ANSWER)
