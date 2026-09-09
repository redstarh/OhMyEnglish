"""Task 4 — `app.services.utterances` transcript persistence tests (AC W1 전반·W3·W6).

`save_final_transcript` appends the utterance with the next per-session
`sequence_no`. 분석 job 등록은 **저장이 아니라 턴 경계**의 일이다
(`flush_pending_analysis`, I-1) — 저장 시점에는 그 발화가 턴의 마지막 조각인지
알 수 없다. Most tests drive it inside the rolled-back `db_conn` fixture and use
a savepoint (`db_conn.transaction()`) to inject a mid-transaction failure.

⚠️ **되살리지 말 것**: `test_save_is_atomic_even_when_the_caller_opened_no_transaction`
은 2026-09-01 I-1 수정에서 삭제했다. 그것이 지킨 불변식("전사문 insert와 enqueue가
한 단위 = 분석되지 않는 고아 전사문이 남지 않는다")은 enqueue가 이 함수에서 빠지면서
**사라졌다** — 남은 write가 하나뿐이라 단정할 원자성이 없다. 다른 곳으로 옮겨진 것이
아니다. 오히려 `tests/integration/test_gateway.py`의 flush 실패 내성 테스트는 그
**반대**(전사문은 남고 job은 0건)를 허용으로 못 박는다. 그 잔여 위험의 소유자는
`TASKS.md` I-1이다.

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

from app.services.jobs import claim_next, complete
from app.services.sessions import end_session
from app.services.utterances import (
    UtteranceRow,
    flush_ended_sessions,
    flush_pending_analysis,
    save_final_transcript,
)

FIRST_TURN_ANSWER = "I usually go to gym after work."
SECOND_TURN_ANSWER = "I usually go to office by subway."

# 2026-09-01 실물 마이크 1회에서 실제로 쪼개진 발화 (I-1). 이 조각들은 각자
# 분석되면 "주어 없음"·"목적어 없음"을 만들고, 이어붙이면 온전한 문장이 된다.
FRAGMENTS = ("i'm going to", "have a meeting", "with the client.")
AGENT_REPLY = "That sounds important. How are you preparing?"


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


# ① 사용자 learning 발화 → utterances 1행. 턴이 닫히면 analysis_jobs 1행
async def test_user_learning_transcript_is_saved_and_enqueued_when_the_turn_closes(
    db_conn: asyncpg.Connection,
):
    session_id = await _new_session(db_conn)

    row = await save_final_transcript(db_conn, session_id, FIRST_TURN_ANSWER)

    assert isinstance(row, UtteranceRow)
    assert row.session_id == session_id
    assert row.speaker == "user"
    assert row.utterance_type == "learning"
    assert row.transcript == FIRST_TURN_ANSWER
    assert row.sequence_no == 1
    assert row.created_at.tzinfo is not None  # timestamptz — naive 금지
    assert await _counts(db_conn) == (1, 0), "저장만으로는 job이 걸리지 않는다 (I-1)"

    await save_final_transcript(db_conn, session_id, AGENT_REPLY, speaker="agent")
    await flush_pending_analysis(db_conn, session_id)

    assert await _counts(db_conn) == (2, 1)
    job = await db_conn.fetchrow("select job_type, utterance_id, status from analysis_jobs")
    assert job is not None
    assert job["job_type"] == "analyze_utterance"
    assert job["utterance_id"] == row.id
    assert job["status"] == "pending"


# ⛔ **여기 있던 `test_transcript_and_job_roll_back_together_when_the_turn_fails`를 지웠다 —
#    되살리지 마라** (2026-09-09 codex 리뷰 HIGH · `TASK-76`).
#
# 그 테스트는 `async with db_conn.transaction():` 으로 **호출자 트랜잭션**을 열어
# `save_final_transcript` 둘과 `flush_pending_analysis`를 감싸고, 예외를 던져 둘이 함께
# 롤백되는 것을 단정했다. **프로덕션은 그 패턴을 쓰지 않고 금지한다** —
# `audio_gateway/session.py`의 `_save_final`은 트랜잭션을 열지 않고,
# `_flush_analysis`의 docstring이 *"호출자의 트랜잭션 안에서 부르지 않는다 — SQL 오류가 나면 그
# 트랜잭션이 abort되어 뒤따르는 종료 기록까지 함께 실패한다"*를 명시한다. 즉 **프로덕션에 없는
# 호출 패턴에서만 참인 성질을 증명하고 있었다.**
#
# ⛔ **그 성질은 애초에 설계 목표가 아니다.** `save_final_transcript`의 docstring이 그것을 적어
# 뒀다 — *"분석 job은 여기서 걸지 않는다"* · *"I-1에서 enqueue가 빠지며 「두 write의 원자성」이라는
# 원래 목적은 사라졌다"*. 즉 낡은 것은 테스트가 아니라 **AC W1의 문면**이고, 그것은 AC 문서에서
# 고쳤다(`docs/design/2026-08-25-first-slice-acceptance-criteria.md`).
#
# **고치지 않고 지운 이유**: 지금 참인 것은 위 ①(`저장만으로는 job이 걸리지 않는다`)과 아래
# 스윕 묶음(`test_sweep_enqueues_an_unflushed_run_in_an_ended_session` ·
# `test_sweep_covers_sessions_closed_as_failed`)이 **이미 덮는다.** 같은 것을 세 번째로 쓰는 대신
# 거짓 신호를 없앴다 — 통과하는 테스트가 있다는 것이 그 성질이 보장된다는 뜻이 되면 안 된다.


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


# --- I-1 턴 경계 병합 (2026-09-01 캡틴 결정 (가)) ---
#
# 저장 시점에는 그 발화가 턴의 마지막인지 알 수 없다. 조각마다 job을 걸면 조각
# 하나가 완전한 문장처럼 분석되고, 실물 마이크 1회에서 occurrence 13건 중 7건이
# 그렇게 나왔다 — 존재하지 않는 약점 2개가 학습자 프로필에 생겼다.


# T0① — 조각은 저장만 되고 job은 걸리지 않는다 (flush 전)
async def test_consecutive_user_finals_are_saved_without_a_job_until_flush(
    db_conn: asyncpg.Connection,
):
    session_id = await _new_session(db_conn)

    for fragment in FRAGMENTS:
        await save_final_transcript(db_conn, session_id, fragment)

    assert await _counts(db_conn) == (len(FRAGMENTS), 0)


# T0② — agent 발화가 턴을 닫으면 묶음의 **마지막 발화 1건**에만 job이 걸린다
async def test_flush_enqueues_one_job_on_the_last_utterance_of_the_run(
    db_conn: asyncpg.Connection,
):
    session_id = await _new_session(db_conn)
    saved = [await save_final_transcript(db_conn, session_id, text) for text in FRAGMENTS]
    await save_final_transcript(db_conn, session_id, AGENT_REPLY, speaker="agent")

    enqueued = await flush_pending_analysis(db_conn, session_id)

    assert enqueued == [saved[-1].id]
    jobs = await db_conn.fetch("select utterance_id, job_type, status from analysis_jobs")
    assert [(row["utterance_id"], row["job_type"], row["status"]) for row in jobs] == [
        (saved[-1].id, "analyze_utterance", "pending")
    ]


# T0⑤ — agent 발화가 사이에 끼면 묶음이 둘로 갈린다
async def test_agent_speech_between_finals_splits_the_run_in_two(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    first = await save_final_transcript(db_conn, session_id, "i will plan the")
    second = await save_final_transcript(db_conn, session_id, "active plan.")
    await save_final_transcript(db_conn, session_id, AGENT_REPLY, speaker="agent")
    third = await save_final_transcript(db_conn, session_id, "yes, i prepared.")
    fourth = await save_final_transcript(db_conn, session_id, "a report.")

    enqueued = await flush_pending_analysis(db_conn, session_id)

    assert enqueued == [second.id, fourth.id]
    assert first.id not in enqueued
    assert third.id not in enqueued


# 분석 대상이 아닌 발화는 묶음을 닫기만 하고 자신은 job을 받지 않는다 (W6 유지)
async def test_flush_never_enqueues_agent_or_command_speech(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    await save_final_transcript(db_conn, session_id, AGENT_REPLY, speaker="agent")
    await save_final_transcript(db_conn, session_id, "Stop.", utterance_type="voice_command")

    assert await flush_pending_analysis(db_conn, session_id) == []
    assert await _counts(db_conn) == (2, 0)


# flush는 세션 안에서 여러 번 불린다(턴마다 + 종료). 이미 분석이 끝난 묶음을 다시
# 걸면 같은 발화를 Claude로 두 번 보낸다 — `uq_analysis_jobs_pending_utterance`는
# pending/running만 덮으므로 done이 된 job을 막지 못한다.
async def test_flush_does_not_re_enqueue_a_run_whose_analysis_already_finished(
    db_conn: asyncpg.Connection,
):
    session_id = await _new_session(db_conn)
    fragment = await save_final_transcript(db_conn, session_id, FRAGMENTS[0])
    await save_final_transcript(db_conn, session_id, AGENT_REPLY, speaker="agent")
    assert await flush_pending_analysis(db_conn, session_id) == [fragment.id]
    claimed = await claim_next(db_conn)
    assert claimed is not None
    assert await complete(db_conn, claimed.id, claimed.lease_token) is True

    assert await flush_pending_analysis(db_conn, session_id) == []
    assert await db_conn.fetchval("select count(*) from analysis_jobs") == 1


# 다른 세션의 묶음까지 걷어가지 않는다 (경계)
async def test_flush_is_scoped_to_its_session(db_conn: asyncpg.Connection):
    mine = await _new_session(db_conn)
    other = await _new_session(db_conn)
    await save_final_transcript(db_conn, mine, FRAGMENTS[0])
    await save_final_transcript(db_conn, other, SECOND_TURN_ANSWER)

    enqueued = await flush_pending_analysis(db_conn, mine)

    assert len(enqueued) == 1
    owner = await db_conn.fetchval(
        "select u.session_id from utterances u where u.id = $1", enqueued[0]
    )
    assert owner == mine


# --- I-1 회복 스윕 (2026-09-02 캡틴 결정: 워커 스윕 — 끝난 세션만) ---
#
# 종료 경로의 flush가 실패하면(연결 획득 실패·SQL 오류·그 전에 프로세스 사망) 그 묶음을
# 다시 걸어줄 사람이 없다. 그러면 결과 화면이 terminal 상태 "분석 대상 없음"을 띄운다
# (`services/results.py` 규칙 2 → 프론트 TERMINAL_STATUSES). 워커가 유휴일 때 걷어준다.


# T0 — 끝난 세션의 걸리지 않은 묶음을 스윕이 집어낸다
async def test_sweep_enqueues_an_unflushed_run_in_an_ended_session(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    saved = [await save_final_transcript(db_conn, session_id, text) for text in FRAGMENTS]
    assert await _counts(db_conn) == (len(FRAGMENTS), 0)  # flush가 한 번도 안 걸린 상태
    await end_session(db_conn, session_id, "completed")

    assert await flush_ended_sessions(db_conn) == [saved[-1].id]


# T0 — **진행 중 세션은 절대 건드리지 않는다.** 사용자가 아직 말하는 중이면 그 묶음은
# 자라므로, 여기서 걸면 조각 하나가 완전한 문장처럼 분석되는 I-1 결함이 되살아난다.
async def test_sweep_never_touches_an_active_session(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    for fragment in FRAGMENTS:
        await save_final_transcript(db_conn, session_id, fragment)

    assert await flush_ended_sessions(db_conn) == []
    assert await _counts(db_conn) == (len(FRAGMENTS), 0)


# T0 — 턴 경계 flush가 이미 처리한 묶음을 스윕이 다시 걸지 않는다
async def test_sweep_does_not_re_enqueue_what_a_turn_boundary_already_flushed(
    db_conn: asyncpg.Connection,
):
    session_id = await _new_session(db_conn)
    fragment = await save_final_transcript(db_conn, session_id, FRAGMENTS[0])
    await save_final_transcript(db_conn, session_id, AGENT_REPLY, speaker="agent")
    assert await flush_pending_analysis(db_conn, session_id) == [fragment.id]
    await end_session(db_conn, session_id, "completed")

    assert await flush_ended_sessions(db_conn) == []
    # 종류를 명시한다: 세션 종료가 같은 트랜잭션에서 plan_next_session job 을 하나 더
    # 건다(설계서 §3.1). 이 테스트가 보는 것은 분석 job 의 중복 등록이다.
    assert (
        await db_conn.fetchval(
            "select count(*) from analysis_jobs where job_type = 'analyze_utterance'"
        )
        == 1
    )


# T0 — 묶음 경계는 **세션마다** 계산된다. `lead()`에 partition이 없으면 다른 세션의
# 발화가 앞 세션의 묶음을 닫아버려(전역 `sequence_no` 순서로 섞인다) 경계가 틀어진다.
async def test_sweep_computes_run_boundaries_per_session(db_conn: asyncpg.Connection):
    first, second = await _new_session(db_conn), await _new_session(db_conn)
    head = await save_final_transcript(db_conn, first, "i will plan the")
    tail = await save_final_transcript(db_conn, first, "active plan.")
    alone = await save_final_transcript(db_conn, second, "yes, i prepared.")
    for session_id in (first, second):
        await end_session(db_conn, session_id, "completed")

    enqueued = await flush_ended_sessions(db_conn)

    assert set(enqueued) == {tail.id, alone.id}
    assert head.id not in enqueued, "묶음 중간 발화에 job이 걸렸다"


# T0 — `failed`로 닫힌 세션도 끝난 세션이다 (연결 실패 전에 말한 것은 분석 대상이다)
async def test_sweep_covers_sessions_closed_as_failed(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    saved = await save_final_transcript(db_conn, session_id, FRAGMENTS[0])
    await end_session(db_conn, session_id, "failed")

    assert await flush_ended_sessions(db_conn) == [saved.id]


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
                # 경합의 관심사는 전사문 보존이다. 등록은 턴 경계의 일이므로
                # (I-1) 저장만 한 이 시점에 job은 한 건도 없다 — 다른 테스트가
                # 전역 행 수를 단정하므로 커밋된 job이 새면 그쪽이 깨진다.
                assert await winner.fetchval("select count(*) from analysis_jobs") == 0
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


# 존재하지 않는 세션에는 저장하지 않는다 (FK 경계)
async def test_save_rejects_unknown_session(db_conn: asyncpg.Connection):
    with pytest.raises(asyncpg.ForeignKeyViolationError):
        await save_final_transcript(db_conn, uuid4(), FIRST_TURN_ANSWER)
