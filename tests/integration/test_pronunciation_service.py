"""발음 시도 생명주기와 패턴 연결 (설계서 §3.2·§4.3, 계획 Task 4·7).

Nova는 시범 시점에 `pending`으로 한 번, 재발화를 들은 뒤 판정값으로 한 번 tool을
부른다 — **두 번째가 오지 않을 수도 있다**(설계서 F3, §3.2). 그래서 생명주기를
Gateway가 갖고, 세션 종료 시 남은 `pending`을 `incorrect`로 수렴시킨다(설계서의
`unclear`를 캡틴이 2026-08-28에 뒤집었다). `pending`을 영구히 남기면 미판정 시도가
조용히 쌓여 숙련도 계산을 왜곡한다.

⑭~㉗은 Task 7의 패턴 연결이다 — `incorrect`가 되는 **모든 경로**(판정·종료 수렴)가
`error_patterns`를 만든다. ㉑~㉗은 리뷰(MEDIUM-3·4)가 지적한 경계와 원자성이고, 그중
㉖·㉗은 `db_conn`이 아니라 **`db_pool` + `committed_session`**을 쓴다 — 운영 경로는
savepoint가 아니라 최상위 트랜잭션이라 코드 경로가 다르다. 그 둘은 실제로 커밋하므로
정리를 단정 뒤에 직접 하지 않고 픽스처의 `try/finally`에 맡긴다 — 단정이 깨지는 순간
(= 진짜 회귀가 난 순간) 정리가 건너뛰어지면 세션 스코프 DB가 오염돼 뒤 테스트의
무회귀 신호까지 함께 무너진다.

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
import pytest

from app.services import pronunciation as pronunciation_service
from app.services.pronunciation import (
    link_pattern,
    load_known_sounds,
    record_attempt,
    record_signal,
    resolve_dangling,
)

TARGET = "I think I found three very useful videos."
HEARD = "I sink I found sree very useful videos."
SOUND = "th_as_s"


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


async def _patterns(conn: asyncpg.Connection, session_id: UUID) -> list[asyncpg.Record]:
    """이 세션 사용자의 패턴만 본다.

    ⚠️ `error_patterns` 전체의 절대값을 단정하지 않는다 — 공유 dev DB에서는 다른 갈래가
    남긴 행이 섞여 반드시 깨진다(하네스 함정 H-4). 사용자를 테스트마다 새로 만들므로
    사용자로 좁힌 개수는 결정론적이다.
    """
    return await conn.fetch(
        "select ep.* from error_patterns ep "
        "join learning_sessions s on s.user_id = ep.user_id "
        "where s.id = $1 order by ep.pattern_key",
        session_id,
    )


async def _pattern_id_of(conn: asyncpg.Connection, attempt_id: UUID) -> UUID | None:
    return await conn.fetchval(
        "select pattern_id from pronunciation_attempts where id = $1", attempt_id
    )


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

    closed = await record_attempt(db_conn, session_id, target_form="Second.", outcome="correct")

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
        "select spoken_form, target_sound, utterance_id from pronunciation_attempts where id = $1",
        attempt_id,
    )
    assert row is not None
    assert row["spoken_form"] == "I sink I pound sree very useful bideos."
    assert row["target_sound"] == "th_as_s"
    assert row["utterance_id"] == utterance_id


# ⑥-1 판정의 `target_form`이 그 행의 최종값이 된다 (`TASK-103`).
#
# ⛔ **관측에서 나왔다.** Nova는 규칙 10의 두 호출에 **다른 것**을 싣는다 — 시범 호출의
# `target_form`은 학습자 발화의 **무너진 전사**이고 판정 호출의 것이 **옳은 목표 문장**이다.
# 실물 왕복 6회(`runs/2026-09-11-task97-tool-payload.md` §3)와 이 세션의 REG 팔 4회
# (`runs/2026-09-12-task111-116-selfcontained-key.md` §1)가 같은 모양을 냈다. 아래 두 값은
# **후자에서 직접 옮긴 것**이다.
#
# ⚠️ **이 값이 학습자 화면의 「시범 문장」 자리에 렌더된다**
# (`app/frontend/app/results/[sessionId]/page.tsx`). 즉 고치지 않으면 「이렇게 말하세요」 자리에
# 학습자의 오발음이 뜬다.
#
# ⛔ **규칙 10의 문면으로는 고쳐지지 않는다** — tool 스키마의 필드 설명이 이미
# *"The full sentence you modeled with correct pronunciation."*이고 `TASK-97` 회차가 교차 3쌍으로
# 확인했다. 그래서 저장 쪽을 고친다.
async def test_verdict_target_form_replaces_the_broken_transcript(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    broken = "I think Sri sings are ready for the demo."
    modeled = "I think three things are ready for the demo."
    attempt_id = await record_attempt(db_conn, session_id, target_form=broken, outcome="pending")

    await record_attempt(db_conn, session_id, target_form=modeled, outcome="correct")

    stored = await db_conn.fetchval(
        "select target_form from pronunciation_attempts where id = $1", attempt_id
    )
    assert stored == modeled, (
        "판정이 가져온 옳은 문장이 버려졌다 — 이 값이 화면의 「시범 문장」 자리에 뜬다"
    )


# ⑥-2 그런데 판정이 **빈 값**을 주면 시범 시점의 값을 지우지 않는다.
#
# ⚠️ ⑤의 `coalesce` 계약과 같은 축이다 — *"빈 판정이 기록을 지우지 않는다"*. `target_form`은
# 인자가 `str`(옵셔널이 아님)이라 `coalesce`만으로는 부족하고 **빈 문자열도 걸러야** 한다.
# 이것이 없으면 ⑥-1의 갱신이 「판정이 문장을 안 실어 온 턴」에서 기록을 **비운다.**
async def test_verdict_with_a_blank_target_form_keeps_the_modeled_sentence(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    attempt_id = await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")

    await record_attempt(db_conn, session_id, target_form="   ", outcome="incorrect")

    stored = await db_conn.fetchval(
        "select target_form from pronunciation_attempts where id = $1", attempt_id
    )
    assert stored == TARGET, "빈 판정이 시범 문장을 지웠다"


# ⑥-3 ⛔ **남은 구멍을 «지금 거동으로» 못박는다** — ⑥-1 이 이 경우를 닫지 못한다 (`TASK-103` AC#3).
#
# 관측된 봉투 하나에서는 **두 호출이 모두 `pending`** 이었다(12/12 ·
# `runs/2026-09-11-task97-tool-payload.md`). 그러면 판정 UPDATE 가 아예 돌지 않으므로 ⑥-1 의
# 갱신 경로를 타지 못하고, 열린 행이 **둘** 남는다. 세션 종료의 `resolve_dangling` 이 둘 다
# `incorrect` 로 수렴시키므로 **무너진 전사를 가진 행이 결과 화면에 그대로 뜬다.**
#
# ⚠️ **이 테스트는 「고쳐졌다」가 아니라 「여기까지만 고쳐졌다」를 잰다.** 뒤 태스크가 이 구멍을
# 닫으면 이 단정을 **의도적으로 뒤집어야** 한다 — 그때 이 주석이 그 근거를 준다.
# ⛔ 이 거동을 「정상」으로 읽지 마라.
async def test_two_pendings_leave_the_broken_target_form_on_the_older_row(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    broken = "I think Sri sings are ready for the demo."
    modeled = "I think three things are ready for the demo."
    older = await record_attempt(db_conn, session_id, target_form=broken, outcome="pending")
    await record_attempt(db_conn, session_id, target_form=modeled, outcome="pending")

    await resolve_dangling(db_conn, session_id)

    rows = await db_conn.fetch(
        "select target_form, outcome from pronunciation_attempts "
        "where session_id = $1 order by attempt_seq",
        session_id,
    )
    assert [row["outcome"] for row in rows] == ["incorrect", "incorrect"]
    stale = await db_conn.fetchval(
        "select target_form from pronunciation_attempts where id = $1", older
    )
    assert stale == broken, "구멍이 «닫혔다» — 좋은 일이지만 이 단정과 위 주석을 함께 고쳐야 한다"


# ⑦ 세션 종료 수렴 — 남은 pending 전부가 incorrect가 되고 spoken_form은 비워진다.
#    "대답을 못 한 것은 못 한 것"이고 이후 학습도 그냥 틀림으로 본다(캡틴 결정 2026-08-28).
async def test_resolve_dangling_converges_pending_to_incorrect(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")
    await record_attempt(db_conn, session_id, target_form="Other.", outcome="pending")

    changed = await resolve_dangling(db_conn, session_id)

    assert changed == 2
    rows = await db_conn.fetch(
        "select outcome, resolved_at, spoken_form from pronunciation_attempts "
        "where session_id = $1",
        session_id,
    )
    assert [row["outcome"] for row in rows] == ["incorrect", "incorrect"]
    assert all(row["resolved_at"] is not None for row in rows)
    # 재발화를 실제로 못 들었으므로 "들린 발음"이 남아 있으면 안 된다 — Nova의 placeholder
    # 문구가 남으면 결과 화면이 그것을 학습자 발음으로 보여준다.
    assert all(row["spoken_form"] is None for row in rows)


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
    theirs_attempt = await record_attempt(db_conn, theirs, target_form=TARGET, outcome="pending")

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
    nova_pending = await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")

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


# --- Task 7: 패턴 연결 (R10-6 → R11-9, 설계서 §4.3) ---


# ⑭ incorrect + target_sound → 재사용 가능한 패턴이 생기고 시도가 그것을 가리킨다.
#    **임계값이 없다** — 1회에 만든다(문법 오류와 같은 규약, PRD.md:90).
async def test_incorrect_with_target_sound_creates_a_pattern(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)

    attempt_id = await record_attempt(
        db_conn,
        session_id,
        target_form=TARGET,
        outcome="incorrect",
        spoken_form=HEARD,
        target_sound=SOUND,
    )

    patterns = await _patterns(db_conn, session_id)
    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern["category"] == "pronunciation_intonation"
    assert pattern["pattern_key"] == "pronunciation_th_as_s"
    # 패턴의 target_form은 **일반형**이지 시범 문장이 아니다
    # (`docs/database-schema.md`의 `error_patterns` 절 — ⚠️ 줄 번호로 가리키지 않는다 · `H-H`).
    # 문장은 시도 행이 갖는다 — 여기 넣으면 중복이고, 한 패턴에 시도가 여럿일 때 결과 카드의
    # 두 값이 서로 다른 문장을 가리키는 관측된 결함(1차수 F-2)이 재현된다.
    assert pattern["target_form"] == SOUND
    assert pattern["target_form"] != TARGET
    assert pattern["frequency"] == 1
    assert pattern["last_seen_at"] is not None
    assert await _pattern_id_of(db_conn, attempt_id) == pattern["id"]


# ⑮ 같은 소리가 두 번 → 패턴은 **1개**다. 문장이 달라도 병합된다(001 스키마의
#    unique(user_id, pattern_key) — "같은 오류는 문장이 달라도 한 패턴").
#    frequency는 occurrence가 아니라 **시도 수**다(설계서 §4.3 — 발음은 occurrence를 안 만든다).
async def test_same_target_sound_reuses_one_pattern(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)

    first = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="incorrect", target_sound=SOUND
    )
    second = await record_attempt(
        db_conn,
        session_id,
        target_form="Thanks for the three files.",
        outcome="incorrect",
        target_sound=SOUND,
    )

    assert first != second, "판정된 행은 다시 닫히지 않으므로 시도는 2건이어야 한다"
    patterns = await _patterns(db_conn, session_id)
    assert len(patterns) == 1
    assert patterns[0]["frequency"] == 2
    # **목표 형태가 흔들리지 않는다** — 두 번째 문장이 덮어쓰지 않는다. 흔들리면 학습자가
    # 연습할 것이 분석마다 달라진다(`analysis.py:118` 규칙 3이 문법 경로에 요구하는 것과 같다).
    assert patterns[0]["target_form"] == SOUND
    assert await _pattern_id_of(db_conn, first) == patterns[0]["id"]
    assert await _pattern_id_of(db_conn, second) == patterns[0]["id"]


# ⑯ target_sound가 없으면 키를 만들 재료가 없다 — 시도만 남는다(설계서 §4.2 검증 규칙).
async def test_incorrect_without_target_sound_makes_no_pattern(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)

    attempt_id = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="incorrect", spoken_form=HEARD
    )

    assert await _patterns(db_conn, session_id) == []
    assert await _pattern_id_of(db_conn, attempt_id) is None


# ⑰ correct는 오류가 아니다 — 패턴을 만들면 잘 읽은 것이 약점으로 집계된다.
async def test_correct_makes_no_pattern(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)

    attempt_id = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="correct", target_sound=SOUND
    )

    assert await _patterns(db_conn, session_id) == []
    assert await _pattern_id_of(db_conn, attempt_id) is None


# ⑱ **경로 불문** — 종료 수렴으로 incorrect가 된 행도 패턴을 만든다(설계서 §3.2, 계획 정정).
#    경로별 예외를 두면 "대답 안 함"만 따로 세는 규칙이 생기고 결과·학습 계획으로 번진다.
async def test_resolve_dangling_also_creates_a_pattern(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)
    attempt_id = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="pending", target_sound=SOUND
    )
    assert await _patterns(db_conn, session_id) == [], "pending은 아직 오류가 아니다"

    assert await resolve_dangling(db_conn, session_id) == 1

    patterns = await _patterns(db_conn, session_id)
    assert len(patterns) == 1
    assert patterns[0]["pattern_key"] == "pronunciation_th_as_s"
    assert patterns[0]["frequency"] == 1
    assert await _pattern_id_of(db_conn, attempt_id) == patterns[0]["id"]


# ⑲ 판정 tool이 소리를 다시 안 줘도 시범 시점의 값으로 만든다 — 패턴 재료는 인자가 아니라
#    **저장된 행**에서 읽는다(coalesce 계약 ⑤와 같은 이유: 빈 판정이 기록을 지우지 않는다).
async def test_verdict_uses_the_sound_the_pending_row_already_had(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    pending = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="pending", target_sound=SOUND
    )

    closed = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="incorrect", spoken_form=HEARD
    )

    assert closed == pending
    patterns = await _patterns(db_conn, session_id)
    assert len(patterns) == 1
    assert patterns[0]["pattern_key"] == "pronunciation_th_as_s"


# ⑳ 시도와 패턴은 **한 트랜잭션**이다(설계서 §7 Failure). 호출자는 autocommit
#    (`audio_gateway/session.py:243`의 `pool.acquire()`)이므로 이 함수가 원자성을 보장해야
#    한다 — 안 그러면 패턴 없는 시도나 frequency만 오른 패턴이 남는다.
async def test_attempt_and_pattern_link_are_one_transaction(
    db_conn: asyncpg.Connection, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = await _session(db_conn)

    async def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("패턴 연결이 실패했다")

    monkeypatch.setattr(pronunciation_service, "link_pattern", boom)

    with pytest.raises(RuntimeError):
        await record_attempt(
            db_conn, session_id, target_form=TARGET, outcome="incorrect", target_sound=SOUND
        )

    assert (
        await db_conn.fetchval(
            "select count(*) from pronunciation_attempts where session_id = $1", session_id
        )
        == 0
    ), "패턴 연결이 실패하면 시도 행도 남지 않아야 한다"


# --- Task 7 리뷰(MEDIUM-4)가 지적한 경계값 ---


# ㉑ 빈 문자열·공백만인 target_sound는 **없는 것과 같다**. `record_attempt`는 공개 서비스
#    함수라 Nova 페이로드 검증(`parse_tool_payload`의 strip)을 통과하지 않는 호출자도 있다.
@pytest.mark.parametrize("blank", ["", "   "])
async def test_blank_target_sound_makes_no_pattern(db_conn: asyncpg.Connection, blank: str) -> None:
    session_id = await _session(db_conn)

    attempt_id = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="incorrect", target_sound=blank
    )

    assert await _patterns(db_conn, session_id) == []
    assert await _pattern_id_of(db_conn, attempt_id) is None


# ㉒ 앞뒤 공백은 키를 갈라놓지 않는다 — `pronunciation_ th_as_s `가 되면 같은 소리가 두
#    패턴이 되어 R10-6의 "반복 오류 묶기"가 깨진다.
async def test_target_sound_is_trimmed_into_the_key(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)

    padded = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="incorrect", target_sound=f"  {SOUND} "
    )
    clean = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="incorrect", target_sound=SOUND
    )

    patterns = await _patterns(db_conn, session_id)
    assert len(patterns) == 1, "공백 차이가 패턴을 갈라놓으면 안 된다"
    assert patterns[0]["pattern_key"] == "pronunciation_th_as_s"
    assert patterns[0]["target_form"] == SOUND
    assert await _pattern_id_of(db_conn, padded) == await _pattern_id_of(db_conn, clean)


# ㉓ `unclear`는 오류로 세지 않는다. `correct`(⑰)보다 이쪽이 더 중요하다 — 페이로드 강등
#    (설계서 §4.2)과 한글 전사 신호가 실제로 내는 값이 `unclear`다.
async def test_unclear_makes_no_pattern(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)

    attempt_id = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="unclear", target_sound=SOUND
    )

    assert await _patterns(db_conn, session_id) == []
    assert await _pattern_id_of(db_conn, attempt_id) is None


# ㉔ 같은 시도에 두 번 불러도 값이 변하지 않는다 — frequency를 `+1`이 아니라 행 수에서
#    재계산하는 이유가 이것이다(`analysis.py:220` "+1 금지"와 같은 규약).
async def test_link_pattern_is_idempotent(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)
    attempt_id = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="incorrect", target_sound=SOUND
    )
    first = await _patterns(db_conn, session_id)

    again = await link_pattern(db_conn, attempt_id)

    assert again == first[0]["id"]
    patterns = await _patterns(db_conn, session_id)
    assert len(patterns) == 1
    assert patterns[0]["frequency"] == 1, "두 번 불러도 시도 수는 1이다"
    assert patterns[0]["last_seen_at"] == first[0]["last_seen_at"]


# ㉕ 수렴이 여러 행을 한 번에 처리할 때도 같은 소리는 한 패턴으로 묶이고 시도 수가 맞는다.
async def test_resolve_dangling_merges_two_pendings_of_one_sound(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="pending", target_sound=SOUND
    )
    await record_attempt(
        db_conn, session_id, target_form="Three things.", outcome="pending", target_sound=SOUND
    )

    assert await resolve_dangling(db_conn, session_id) == 2

    patterns = await _patterns(db_conn, session_id)
    assert len(patterns) == 1
    assert patterns[0]["frequency"] == 2
    linked = await db_conn.fetchval(
        "select count(*) from pronunciation_attempts where session_id = $1 and pattern_id = $2",
        session_id,
        patterns[0]["id"],
    )
    assert linked == 2


# ㉖ 운영 경로는 savepoint가 아니라 **최상위 트랜잭션**이다 — `audio_gateway/session.py:243`이
#    `pool.acquire()`(autocommit)로 부른다. ⑳이 덮은 savepoint 경로와 다른 코드 경로라
#    따로 검증한다: 패턴 연결이 실패하면 시도 행이 **커밋되지 않아야** 한다.
async def test_record_attempt_is_atomic_on_an_autocommit_connection(
    db_pool: asyncpg.Pool, committed_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = committed_session.session_id

    async def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("패턴 연결이 실패했다")

    monkeypatch.setattr(pronunciation_service, "link_pattern", boom)

    async with db_pool.acquire() as conn:
        with pytest.raises(RuntimeError):
            await record_attempt(
                conn, session_id, target_form=TARGET, outcome="incorrect", target_sound=SOUND
            )

    async with db_pool.acquire() as check:
        assert (
            await check.fetchval(
                "select count(*) from pronunciation_attempts where session_id = $1", session_id
            )
            == 0
        ), "최상위 트랜잭션이 없으면 시도 행만 커밋돼 패턴 없는 고아가 된다"


# ㉗ 수렴 경로도 최상위 트랜잭션에서 원자적이어야 한다. Task 7 전에는 UPDATE 한 문장이라
#    autocommit에서도 안전했지만, 지금은 `1+3N` 문장이다 — 패턴 연결이 중간에 깨지면
#    `pattern_id`가 null인 `incorrect` 행이 커밋된 채 남는다(리뷰 MEDIUM-3).
async def test_resolve_dangling_is_atomic_on_an_autocommit_connection(
    db_pool: asyncpg.Pool, committed_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    session_id = committed_session.session_id
    async with db_pool.acquire() as setup:
        await record_attempt(
            setup, session_id, target_form=TARGET, outcome="pending", target_sound=SOUND
        )

    async def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("패턴 연결이 실패했다")

    monkeypatch.setattr(pronunciation_service, "link_pattern", boom)

    async with db_pool.acquire() as conn:
        with pytest.raises(RuntimeError):
            await resolve_dangling(conn, session_id)

    async with db_pool.acquire() as check:
        outcome = await check.fetchval(
            "select outcome from pronunciation_attempts where session_id = $1", session_id
        )
        assert outcome == "pending", (
            "수렴만 커밋되면 패턴 없는 incorrect 행이 남는다 — 세션은 이미 끝났으므로 "
            "그 행을 다시 수렴시킬 기회가 없다"
        )


# --- G-3: Nova 지시문에 주입할 기존 소리 조회 (캡틴 결정 B-4) ---


async def _user(conn: asyncpg.Connection) -> UUID:
    user_id = await conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ('Known Sounds Test User', 'Asia/Seoul', 'A2') returning id"
    )
    assert isinstance(user_id, UUID)
    return user_id


async def _seed_pattern(
    conn: asyncpg.Connection, user_id: UUID, *, category: str, pattern_key: str, target_form: str
) -> None:
    await conn.execute(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, $2, $3, $4)",
        user_id,
        category,
        pattern_key,
        target_form,
    )


# 발음 카테고리만 골라온다. **문법 패턴이 섞이면 안 된다** — 문법 쪽 조회
# (`analysis._EXISTING_PATTERNS_SQL`)에 카테고리 필터가 없는 것이 `frequency` 이중 writer
# 문제(B-10/G-8)의 뿌리다. 그 조회를 재사용하지 않고 여기서 필터를 갖는 이유가 이것이다.
async def test_load_known_sounds_returns_only_pronunciation_patterns(
    db_conn: asyncpg.Connection,
) -> None:
    user_id = await _user(db_conn)
    await _seed_pattern(
        db_conn,
        user_id,
        category="pronunciation_intonation",
        pattern_key="pronunciation_th_as_s",
        target_form="th_as_s",
    )
    await _seed_pattern(
        db_conn,
        user_id,
        category="article",
        pattern_key="article_missing_before_noun",
        target_form="go to the + 장소 명사",
    )

    sounds = await load_known_sounds(db_conn, user_id)

    assert sounds == ["th_as_s"]


# 기록이 없으면 빈 목록이다 — 지시문 조립이 이 값으로 블록을 생략한다(dev DB의 현재 상태).
async def test_load_known_sounds_is_empty_without_pronunciation_history(
    db_conn: asyncpg.Connection,
) -> None:
    user_id = await _user(db_conn)

    assert await load_known_sounds(db_conn, user_id) == []
