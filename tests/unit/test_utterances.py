"""Task 4 — `app.services.utterances` transcript persistence tests (AC W1 전반·W3·W6).

`save_final_transcript` must do two writes as one unit: append the utterance
with the next per-session `sequence_no`, and — only for a user's *learning*
speech — register its analysis job in the same transaction. Most tests drive it
inside the rolled-back `db_conn` fixture and use a savepoint
(`db_conn.transaction()`) to inject a mid-transaction failure.

Two tests instead use their own **autocommit** connections against the migrated
test database, because that is the only way to observe what a *caller that did
not open a transaction* commits, and the only way to make two connections race
for the same `sequence_no`. Those tests clean up after themselves (`delete from
users` cascades to sessions → utterances → analysis_jobs) — other tests assert
on global row counts, so committed rows must never survive the test that made
them.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import asyncpg
import pytest

from app.services import utterances as utterances_module
from app.services.jobs import claim_next, complete
from app.services.utterances import (
    UtteranceRow,
    pending_learning_utterances,
    save_final_transcript,
)

FIRST_TURN_ANSWER = "I usually go to gym after work."
SECOND_TURN_ANSWER = "I usually go to office by subway."


async def _new_session(conn: asyncpg.Connection) -> UUID:
    user_id = await conn.fetchval(
        "insert into users (display_name) values ('Transcript Test User') returning id"
    )
    return await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        user_id,
    )


@contextlib.asynccontextmanager
async def _committed_session(conn: asyncpg.Connection) -> AsyncIterator[UUID]:
    """Create a *committed* user + session on an autocommit connection and drop
    them again on exit (cascade), so nothing leaks into other tests."""
    user_id = await conn.fetchval(
        "insert into users (display_name) values ('Autocommit Test User') returning id"
    )
    try:
        yield await conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
            user_id,
        )
    finally:
        await conn.execute("delete from users where id = $1", user_id)


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


# Fix round 2 (I-1) — 원자성이 호출자 계약에만 의존하면 안 된다.
# autocommit 커넥션(= 호출자가 트랜잭션을 열지 않음)으로 호출하고 두 write 사이에
# 실패를 주입하면, 원자성이 함수 안에 없을 때 전사문만 커밋되어 영원히 분석되지 않는
# 고아 발화가 남는다.
async def test_save_is_atomic_even_when_the_caller_opened_no_transaction(
    test_database: str, monkeypatch: pytest.MonkeyPatch
):
    conn = await asyncpg.connect(dsn=test_database)
    try:
        async with _committed_session(conn) as session_id:

            def boom(*args: object, **kwargs: object) -> None:
                raise RuntimeError("injected failure between the two writes")

            monkeypatch.setattr(utterances_module, "enqueue_analyze", boom)

            with pytest.raises(RuntimeError, match="injected"):
                await save_final_transcript(conn, session_id, FIRST_TURN_ANSWER)

            # autocommit이므로 열린 트랜잭션이 없다 — 아래 읽기는 커밋된 상태다.
            saved = await conn.fetchval(
                "select count(*) from utterances where session_id = $1", session_id
            )
            assert saved == 0, "전사문이 커밋되어 job 없는 고아 발화가 남았다"
            # 다른 테스트는 모두 롤백되므로 커밋된 job은 0이어야 한다.
            assert await conn.fetchval("select count(*) from analysis_jobs") == 0
    finally:
        await conn.close()


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


# Fix round 2 (I-3) — 같은 세션에 두 커넥션이 동시에 쓰면 패자가 전사문을 잃어선 안 된다.
# 실제 경합을 만든다: 선착 커넥션이 sequence_no=1을 커밋하지 않은 채 붙들면 후착
# 커넥션의 insert는 unique 인덱스에서 대기하고, 선착이 커밋한 순간 UniqueViolation을
# 받는다. 재시도가 없으면 그 발화는 사라진다.
# READ COMMITTED(Postgres 기본)에 의존한다 — 재시도 문장이 새 스냅샷을 받아 선착의
# 커밋된 행을 보고 sequence_no를 2로 다시 계산한다.
async def test_concurrent_same_session_writes_keep_both_transcripts(test_database: str):
    winner = await asyncpg.connect(dsn=test_database)
    loser = await asyncpg.connect(dsn=test_database)
    try:
        async with _committed_session(winner) as session_id:
            task: asyncio.Task[UtteranceRow] | None = None
            winner_tx = winner.transaction()
            await winner_tx.start()
            committed = False
            try:
                first = await save_final_transcript(winner, session_id, FIRST_TURN_ANSWER)
                assert first.sequence_no == 1

                task = asyncio.create_task(
                    save_final_transcript(loser, session_id, SECOND_TURN_ANSWER)
                )
                await asyncio.sleep(0.1)
                assert not task.done(), "후착 insert가 unique 충돌 대기에 들어가지 않았다"

                await winner_tx.commit()
                committed = True

                second = await task
                assert second.sequence_no == 2

                rows = await winner.fetch(
                    "select sequence_no, transcript from utterances "
                    "where session_id = $1 order by sequence_no",
                    session_id,
                )
                assert [(row["sequence_no"], row["transcript"]) for row in rows] == [
                    (1, FIRST_TURN_ANSWER),
                    (2, SECOND_TURN_ANSWER),
                ]
                # 두 발화 모두 사용자 learning이므로 job도 2건이다.
                assert await winner.fetchval("select count(*) from analysis_jobs") == 2
            finally:
                # 정리는 `_committed_session`의 cascade 삭제보다 먼저 끝나야 한다 —
                # 열린 트랜잭션이 남으면 삭제가 함께 롤백돼 행이 유출된다.
                if task is not None and not task.done():
                    task.cancel()
                    with contextlib.suppress(BaseException):
                        await task
                if not committed:
                    with contextlib.suppress(Exception):
                        await winner_tx.rollback()
    finally:
        await winner.close()
        await loser.close()


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
