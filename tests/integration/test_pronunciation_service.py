"""Task 4 — 발음 시도 생명주기 (설계서 §3.2, 계획 Task 4).

Nova는 시범 시점에 `pending`으로 한 번, 재발화를 들은 뒤 판정값으로 한 번 tool을
부른다 — **두 번째가 오지 않을 수도 있다**(설계서 F3, §3.2). 그래서 생명주기를
Gateway가 갖고, 세션 종료 시 남은 `pending`을 `unclear`로 수렴시킨다. `pending`을
영구히 남기면 미판정 시도가 조용히 쌓여 숙련도 계산을 왜곡한다.

**두 진입점이 나뉘어 있다.** `record_attempt`는 Nova tool 생명주기(pending → 판정)이고
`record_signal`은 보조 신호 1건이다 — 후자는 열린 pending을 닫지 않는다. 함수를 나눈
이유는 호출부에서 무엇이 일어나는지 보이게 하는 것이다: 인자값(`signal_source`)이
생명주기 동작을 바꾸면 `session.py`를 읽는 사람이 호출 이름만으로 알 수 없다.

DB가 필요해서 integration이다. `db_conn`은 마이그레이션만 적용된 테스트 DB를
**롤백되는 트랜잭션 하나**로 감싸 넘긴다 — 시드는 하지 않으므로 사용자·세션을
여기서 직접 만든다(`tests/unit/test_schema.py`와 같은 방식).

⚠️ 한 트랜잭션 안에서는 `now()`가 고정이라 `created_at`으로는 같은 테스트가 만든 두
행의 순서를 가릴 수 없다(`services/utterances.py:151`이 같은 함정을 기록한다).
`test_two_pendings_...`가 그 경로를 지키는 가드이고, 순서 자체는 004가 더한
`attempt_seq`(identity)가 강제한다.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

from app.services.pronunciation import record_attempt, record_signal, resolve_dangling

TARGET = "I think I found three very useful videos."


async def _session(conn: asyncpg.Connection) -> UUID:
    """세션 1개를 만든다. 시나리오는 nullable이라 생략한다."""
    user_id = await conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ('Pronunciation Test User', 'Asia/Seoul', 'A2') returning id"
    )
    session_id = await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        user_id,
    )
    assert isinstance(session_id, UUID)
    return session_id


async def _utterance(conn: asyncpg.Connection, session_id: UUID) -> UUID:
    utterance_id = await conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no) "
        "values ($1, 'user', $2, 1) returning id",
        session_id,
        TARGET,
    )
    assert isinstance(utterance_id, UUID)
    return utterance_id


# ① pending은 열린 행을 만든다 — resolved_at이 없어야 CHECK를 통과한다
async def test_pending_creates_a_row_with_null_resolved_at(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)

    attempt_id = await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")

    row = await db_conn.fetchrow(
        "select outcome, resolved_at, signal_source, target_form "
        "from pronunciation_attempts where id = $1",
        attempt_id,
    )
    assert row is not None
    assert row["outcome"] == "pending"
    assert row["resolved_at"] is None
    assert row["signal_source"] == "nova_tool"
    assert row["target_form"] == TARGET


# ② 두 번째 tool 호출은 **새 행을 만들지 않고** 첫 행을 닫는다
async def test_verdict_updates_the_latest_pending_row(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)
    first = await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")

    second = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="correct", spoken_form="I think..."
    )

    assert second == first, "같은 시도여야 한다 — 행이 두 개가 되면 시도 수가 부풀어 오른다"
    assert await db_conn.fetchval("select count(*) from pronunciation_attempts") == 1
    row = await db_conn.fetchrow(
        "select outcome, spoken_form, resolved_at from pronunciation_attempts where id = $1",
        first,
    )
    assert row is not None
    assert row["outcome"] == "correct"
    assert row["spoken_form"] == "I think..."
    assert row["resolved_at"] is not None


# ③ Nova가 pending을 건너뛰고 판정만 보낼 수도 있다 — 기록을 잃지 않는다
async def test_verdict_without_a_pending_row_inserts_one(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)

    attempt_id = await record_attempt(db_conn, session_id, target_form=TARGET, outcome="incorrect")

    row = await db_conn.fetchrow(
        "select outcome, resolved_at from pronunciation_attempts where id = $1", attempt_id
    )
    assert row is not None
    assert row["outcome"] == "incorrect"
    assert row["resolved_at"] is not None


# ④ 한 세션에 시도가 여러 번 있을 수 있다. 판정은 **가장 최근** pending을 닫는다
async def test_two_pendings_resolve_newest_first(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)
    old = await record_attempt(db_conn, session_id, target_form="First.", outcome="pending")
    new = await record_attempt(db_conn, session_id, target_form="Second.", outcome="pending")

    closed = await record_attempt(
        db_conn, session_id, target_form="Second.", outcome="correct"
    )

    assert closed == new
    assert (
        await db_conn.fetchval("select outcome from pronunciation_attempts where id = $1", old)
        == "pending"
    ), "오래된 시도는 그대로 열려 있어야 한다 — 세션 종료 시 수렴 대상이다"


# ⑤ 판정이 값을 안 주면 pending이 갖고 있던 값을 지우지 않는다 (coalesce 계약)
async def test_verdict_keeps_values_the_pending_row_already_had(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    utterance_id = await _utterance(db_conn, session_id)
    attempt_id = await record_attempt(
        db_conn,
        session_id,
        target_form=TARGET,
        outcome="pending",
        target_sound="th_as_s",
        utterance_id=utterance_id,
    )

    await record_attempt(db_conn, session_id, target_form=TARGET, outcome="incorrect")

    row = await db_conn.fetchrow(
        "select target_sound, utterance_id from pronunciation_attempts where id = $1",
        attempt_id,
    )
    assert row is not None
    assert row["target_sound"] == "th_as_s"
    assert row["utterance_id"] == utterance_id


# ⑥ 판정이 값을 주면 그 값이 실린다 — 발화 연결은 판정 시점에 알 수도 있다
async def test_verdict_attaches_values_when_given(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)
    utterance_id = await _utterance(db_conn, session_id)
    attempt_id = await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")

    await record_attempt(
        db_conn,
        session_id,
        target_form=TARGET,
        outcome="incorrect",
        spoken_form="I sink I pound sree very useful bideos.",
        target_sound="th_as_s",
        utterance_id=utterance_id,
    )

    row = await db_conn.fetchrow(
        "select spoken_form, target_sound, utterance_id "
        "from pronunciation_attempts where id = $1",
        attempt_id,
    )
    assert row is not None
    assert row["spoken_form"] == "I sink I pound sree very useful bideos."
    assert row["target_sound"] == "th_as_s"
    assert row["utterance_id"] == utterance_id


# ⑦ 세션 종료 수렴 — 남은 pending 전부가 unclear가 된다
async def test_resolve_dangling_converges_pending_to_unclear(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")
    await record_attempt(db_conn, session_id, target_form="Other.", outcome="pending")

    changed = await resolve_dangling(db_conn, session_id)

    assert changed == 2
    rows = await db_conn.fetch(
        "select outcome, resolved_at from pronunciation_attempts where session_id = $1",
        session_id,
    )
    assert [row["outcome"] for row in rows] == ["unclear", "unclear"]
    assert all(row["resolved_at"] is not None for row in rows)


# ⑧ 멱등 — 두 번 불러도 두 번째는 0이다 (종료 경로가 두 번 타도 안전해야 한다)
async def test_resolve_dangling_is_idempotent(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)
    await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")

    assert await resolve_dangling(db_conn, session_id) == 1
    assert await resolve_dangling(db_conn, session_id) == 0


# ⑨ 이미 판정된 행은 건드리지 않는다 — correct를 unclear로 덮으면 판정이 사라진다
async def test_resolve_dangling_leaves_resolved_rows_untouched(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")
    settled = await record_attempt(db_conn, session_id, target_form=TARGET, outcome="correct")
    before = await db_conn.fetchval(
        "select resolved_at from pronunciation_attempts where id = $1", settled
    )

    assert await resolve_dangling(db_conn, session_id) == 0

    row = await db_conn.fetchrow(
        "select outcome, resolved_at from pronunciation_attempts where id = $1", settled
    )
    assert row is not None
    assert row["outcome"] == "correct"
    assert row["resolved_at"] == before


# ⑩ 다른 세션의 시도는 건드리지 않는다 — 동시 세션이 서로의 기록을 닫으면 안 된다
async def test_resolve_dangling_does_not_touch_other_sessions(
    db_conn: asyncpg.Connection,
) -> None:
    mine = await _session(db_conn)
    theirs = await _session(db_conn)
    await record_attempt(db_conn, theirs, target_form=TARGET, outcome="pending")

    assert await resolve_dangling(db_conn, mine) == 0

    assert (
        await db_conn.fetchval(
            "select outcome from pronunciation_attempts where session_id = $1", theirs
        )
        == "pending"
    )


# ⑪ 판정도 세션 경계를 넘지 않는다 — 다른 세션의 pending을 닫으면 시도가 섞인다
async def test_verdict_does_not_close_another_sessions_pending(
    db_conn: asyncpg.Connection,
) -> None:
    mine = await _session(db_conn)
    theirs = await _session(db_conn)
    theirs_attempt = await record_attempt(
        db_conn, theirs, target_form=TARGET, outcome="pending"
    )

    mine_attempt = await record_attempt(db_conn, mine, target_form=TARGET, outcome="correct")

    assert mine_attempt != theirs_attempt
    assert (
        await db_conn.fetchval(
            "select outcome from pronunciation_attempts where id = $1", theirs_attempt
        )
        == "pending"
    )


# ⑫ 보조 신호로 만든 행을 구분할 수 있어야 한다 (R10-4)
async def test_signal_source_is_stored(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)

    attempt_id = await record_signal(
        db_conn,
        session_id,
        target_form="(전사문이 한국어로 인식되었습니다)",
        outcome="unclear",
        signal_source="korean_transcript",
    )

    assert (
        await db_conn.fetchval(
            "select signal_source from pronunciation_attempts where id = $1", attempt_id
        )
        == "korean_transcript"
    )


# ⑬ 보조 신호는 열린 pending을 닫지 않고 **자기 행**을 만든다 (설계서 §7 Failure:
#    "tool이 오지 않음 → 보조 신호가 떴다면 unclear 행을 남긴다"). 닫아버리면 그 행의
#    signal_source가 'nova_tool'로 남아 "Nova가 놓쳐서 보조 신호로 잡았다"는 사실이
#    사라진다 — signal_source를 둔 이유(R10-4) 자체가 무의미해진다.
#    Nova의 pending은 세션 종료 수렴이 처리한다.
async def test_assist_signal_does_not_close_a_nova_pending(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)
    nova_pending = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="pending"
    )

    assist = await record_signal(
        db_conn,
        session_id,
        target_form="(전사문이 한국어로 인식되었습니다)",
        outcome="unclear",
        signal_source="korean_transcript",
    )

    assert assist != nova_pending
    rows = {
        row["id"]: row
        for row in await db_conn.fetch(
            "select id, outcome, signal_source from pronunciation_attempts where session_id = $1",
            session_id,
        )
    }
    assert rows[nova_pending]["outcome"] == "pending"
    assert rows[nova_pending]["signal_source"] == "nova_tool"
    assert rows[assist]["signal_source"] == "korean_transcript"


# ⑭ Nova 판정은 **보조 신호 행을 닫지 않는다.** 코드 리뷰 실측 재현:
#    `record_signal(outcome='pending')`로 만든 행을 Nova 판정이 UPDATE해
#    signal_source='korean_transcript'인 행이 Nova의 판정·발화를 실어버렸다.
#    그 행이 바로 ⑬번이 "생기면 안 된다"고 논증한 행이다 — 타입으로 막는 것(record_signal의
#    outcome에서 pending 제외)에 더해 SQL에서도 막는다. 여기서는 타입을 우회해
#    raw INSERT로 그 행을 만들어 **런타임 가드**를 검증한다.
async def test_nova_verdict_does_not_close_an_assist_row(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)
    assist = await db_conn.fetchval(
        "insert into pronunciation_attempts (session_id, target_form, outcome, signal_source) "
        "values ($1, '(전사문이 한국어로 인식되었습니다)', 'pending', 'korean_transcript') "
        "returning id",
        session_id,
    )

    verdict = await record_attempt(
        db_conn,
        session_id,
        target_form="Nova sentence.",
        outcome="correct",
        spoken_form="how the learner said it",
    )

    assert verdict != assist, "Nova 판정이 보조 신호 행을 닫았다 — signal_source의 의미가 사라진다"
    row = await db_conn.fetchrow(
        "select outcome, signal_source, target_form, spoken_form "
        "from pronunciation_attempts where id = $1",
        assist,
    )
    assert row is not None
    assert row["outcome"] == "pending"
    assert row["signal_source"] == "korean_transcript"
    assert row["spoken_form"] is None
    new_row = await db_conn.fetchrow(
        "select outcome, signal_source from pronunciation_attempts where id = $1", verdict
    )
    assert new_row is not None
    assert new_row["outcome"] == "correct"
    assert new_row["signal_source"] == "nova_tool"
