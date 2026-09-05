"""`app.services.sessions` — 세션 생명주기 SQL과 세션 시작이 읽는 준비된 계획.

두 묶음이 있다. 아래 두 ⚠️ 는 첫 묶음(I-4 리퍼)에만 걸린다.

1. **I-4 고아 세션 리퍼** (`reap_orphan_sessions`·`end_session`) — 파일 대부분.
2. **Task 8: 세션 시작** (`load_prepared_plan`·`create_session`) — 파일 끝의 절.
   그 절은 `db_pool`도 쓴다(`create_session`이 pool 을 받는다) — 커밋하므로 픽스처가
   teardown 에서 지운다.

**I-4가 왜 필요한가**: 종료 기록 전에 프로세스가 죽으면 `end_session`이 돌지 않아 세션이
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

import json
import logging
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import pytest
from conftest import backdate_session as _backdate
from conftest import plan_json

from app.models.plan import SessionInstruction
from app.services.sessions import (
    ORPHAN_IDLE_GRACE,
    create_session,
    end_session,
    load_prepared_plan,
    reap_orphan_sessions,
)
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
    # 불변식: `status`가 `active`가 아니면 `ended_at`이 채워져 있다 — `_END_SESSION_SQL`이 둘을
    # 한 UPDATE로 묻는 것과 같은 이유이고, 리퍼도 그 불변식을 지켜야 한다.
    # ⚠️ 결과 화면을 근거로 쓰지 마라 — `results.py`는 `status`만 읽고 `ended_at`은 보지 않는다.
    assert ended_at is not None, "끝난 세션인데 종료 시각이 없는 행을 만들었다"


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


# T0 — **소유자의 종료 기록이 리퍼의 판정을 덮지 못한다** (캡틴 결정 2026-09-03).
# 가드가 없으면 리퍼가 `failed`로 닫은 세션을 나중에 소유자가 `completed`로 덮어써서
# **리퍼가 개입했다는 사실이 DB에서 사라진다**(`ended_at`까지 되돌아간다). 그 경합은 live
# 가드가 깨진 뒤에만 도달하므로, 조용히 수렴시키는 대신 최초 판정을 남기고 경고를 찍는다 —
# 그 경고가 가드 고장의 유일한 신호다.
async def test_end_session_does_not_overwrite_a_reaped_session(
    db_conn: asyncpg.Connection, caplog: pytest.LogCaptureFixture
):
    session_id = await _new_session(db_conn)
    await save_final_transcript(db_conn, session_id, ANSWER)
    await _backdate(db_conn, session_id, by=PAST_THE_GRACE)
    assert await reap_orphan_sessions(db_conn) == [session_id]
    _, reaped_at = await _state(db_conn, session_id)

    with caplog.at_level(logging.INFO):
        await end_session(db_conn, session_id, "completed")

    assert await _state(db_conn, session_id) == ("failed", reaped_at), (
        "소유자의 종료 기록이 리퍼의 판정과 시각을 덮었다"
    )
    assert [record for record in caplog.records if record.levelno >= logging.WARNING], (
        "덮어쓰기를 막았는데 경고가 없다 — 가드 고장이 관측되지 않는다 (H-Z: INFO는 안 보인다)"
    )


# T2 — 정상 흐름은 값이 그대로다: `active` 세션은 소유자가 닫는다. 위 가드가 이것까지
# 막으면 모든 세션이 영원히 `active`로 남는다.
async def test_end_session_closes_an_active_session(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)

    await end_session(db_conn, session_id, "completed")

    status, ended_at = await _state(db_conn, session_id)
    assert status == "completed"
    assert ended_at is not None


# T2 — 유예는 **파라미터**다. `idle_after`가 실제로 SQL의 interval에 묶이는지 본다: 묶이지
# 않으면(기본값만 쓰면) 아래 두 단정 중 하나는 반드시 깨진다. 같은 세션을 두 유예로 재는
# 것이 핵심이다 — 경계가 값에 따라 실제로 움직인다는 뜻이다.
async def test_reaper_honours_a_custom_grace(db_conn: asyncpg.Connection):
    session_id = await _new_session(db_conn)
    await save_final_transcript(db_conn, session_id, ANSWER)
    await _backdate(db_conn, session_id, by=timedelta(minutes=5))

    assert await reap_orphan_sessions(db_conn, idle_after=timedelta(minutes=10)) == []
    assert await reap_orphan_sessions(db_conn, idle_after=timedelta(minutes=1)) == [session_id]


# 발명값이다 — 캡틴 결정(2026-09-03: "1분 이상 답이 없으면 failed로 닫는다").
# 값을 조용히 바꾸면 이 단정이 걸린다.
def test_orphan_idle_grace_is_the_captain_decided_value():
    assert ORPHAN_IDLE_GRACE == timedelta(seconds=60)


# ── Task 8: 세션 시작이 준비된 계획을 읽는다 (없으면 폴백) ────────────────────
#
# 설계서 §3.4 — 시작은 **조회 1회**다. 소비 표시를 하지 않으므로 항상 최신 1행을 읽고,
# 그 계획이 가리키는 세션은 그것을 **만든** 세션이다(계획서 「구현 전 정정」).
# §9 Contract — 계획 부재가 세션 시작 실패로 번역되지 않는다.


# T0 — 최신 1행을 읽는다. 먼저 심은 행이 물리 순서상 앞이라, `order by created_at desc`가
# 없으면 `limit 1`이 **오래된 행**을 돌려준다 — 정렬을 지우면 이 단정이 걸린다.
async def test_load_prepared_plan_returns_the_latest_plan(
    db_conn: asyncpg.Connection, seed_plan_for_session
):
    user_id, older = await seed_plan_for_session(db_conn, reason="오래된 이유", days_ago=3)
    _, newest = await seed_plan_for_session(
        db_conn, user_id=user_id, reason="최신 이유", days_ago=0
    )
    assert older != newest

    prepared = await load_prepared_plan(db_conn, user_id)

    assert prepared is not None
    assert prepared.plan_id == newest
    assert prepared.reason == "최신 이유"


# T0 — 계획은 **그 학습자의 것**이어야 한다. 사용자 조건을 지우면 남의 더 새로운 계획이
# 돌아오고, 다음 세션의 대화 상대가 다른 사람의 초점으로 말한다.
# (단일 사용자 로컬 도구지만 조회는 사용자로 좁힌다 — 그 가드가 실제로 걸려 있는지 잰다.)
async def test_load_prepared_plan_ignores_another_learners_newer_plan(
    db_conn: asyncpg.Connection, seed_plan_for_session
):
    user_id, own = await seed_plan_for_session(db_conn, reason="내 이유", days_ago=2)
    other_user, other_plan = await seed_plan_for_session(db_conn, reason="남의 이유", days_ago=0)
    assert other_user != user_id and other_plan != own

    prepared = await load_prepared_plan(db_conn, user_id)

    assert prepared is not None
    assert prepared.plan_id == own, "다른 학습자의 더 새로운 계획을 골랐다"


# AS4 — 계획이 없으면 `None`이다. 예외를 던지면 세션 시작이 계획 부재로 실패한다.
async def test_load_prepared_plan_returns_none_when_absent(db_conn: asyncpg.Connection, seed_user):
    # `tz`는 이 픽스처의 필수 인자다 (LOW-14 — 타임존을 명시해 넣는다).
    user_id = await seed_user(db_conn, tz="Asia/Seoul")

    assert await load_prepared_plan(db_conn, user_id) is None


# T0 — 저장된 `instruction`은 **구조**로 돌아와야 한다. jsonb 코덱이 없어 asyncpg 는 `str`를
# 주므로(`set_type_codec` 0건) 읽는 쪽이 파싱해 모델로 좁히지 않으면 `str`가 그대로 새어나가
# 지시문 조립(Task 10)이 문자열을 필드처럼 다루게 된다.
async def test_load_prepared_plan_parses_the_stored_instruction(
    db_conn: asyncpg.Connection, seed_plan_for_session
):
    user_id, _ = await seed_plan_for_session(db_conn, target_level="B1")

    prepared = await load_prepared_plan(db_conn, user_id)

    assert prepared is not None
    assert isinstance(prepared.instruction, SessionInstruction)
    # 필드가 하나도 떨어지지 않았는지 **전체 동일성**으로 잰다. `assert prepared.instruction.focus`
    # 같은 단정은 항진명제였다(리뷰 라운드 1의 Minor) — `SessionInstruction.focus`가
    # `min_length=1`이라 `model_validate`를 통과한 인스턴스는 반드시 비어 있지 않다.
    # 기대값은 픽스처가 심은 것과 **같은 소유자**(`plan_json`)에서 만든다: 모양을 여기 다시
    # 적으면 한쪽이 조용히 낡는다. `plan_json`의 `instruction`은 `pattern_id`를 담지 않으므로
    # 인자로 준 uuid 와 무관하게 같은 지시문이 나온다.
    assert prepared.instruction == SessionInstruction.model_validate(
        json.loads(plan_json(uuid4(), target_level="B1"))["instruction"]
    )


# T3 — 읽을 수 없는 지시문은 **계획 없음과 같이** 다룬다. `SessionInstruction`에 필수 필드가
# 하나 늘면 그 전에 저장된 행이 전부 이 경로로 오는데, 예외로 새면 그 순간부터 세션이
# 시작되지 않는다(§9 Contract — 시작은 실패하지 않는다). 경고를 남겨 조용히 지나가지 않게 한다:
# 이 신호가 없으면 계획이 매번 무시되는 것을 아무도 모른다(H-Z — INFO는 보이지 않는다).
async def test_load_prepared_plan_skips_a_plan_whose_instruction_cannot_be_read(
    db_conn: asyncpg.Connection, seed_plan_for_session, caplog: pytest.LogCaptureFixture
):
    user_id, _ = await seed_plan_for_session(db_conn, instruction='"not an instruction object"')

    with caplog.at_level(logging.INFO):
        assert await load_prepared_plan(db_conn, user_id) is None

    assert [record for record in caplog.records if record.levelno >= logging.WARNING], (
        "읽을 수 없는 지시문을 건너뛰었는데 경고가 없다 — 계획이 매번 무시되는 것이 관측되지 않는다"
    )


async def _attached_scenario(pool: asyncpg.Pool, session_id: UUID) -> UUID | None:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "select scenario_id from learning_sessions where id = $1", session_id
        )


# AS4 / §3.3 — 수준이 맞는 시나리오를 고른다.
#
# ⚠️ **일치 행을 시각 양쪽 끝에서 떼어 놓는다** (리뷰 라운드 1의 Important — 앞선 판은
# 일치 행을 가장 최신 행으로 심어서 "수준이 맞는 행"과 "가장 최신 행"이 **같은 한 행**을
# 지목했다. 그래서 수준을 무시하고 `desc`로 고르는 구현이 그대로 통과했고, 메인이 직접
# 재현했다 — 558 passed).
# 뒤집는 것으로는 부족하다: 일치 행을 가장 이르게 두면 이번엔 **이 커밋 이전의 SQL**
# (수준 무시 + 가장 이른 행)이 통과한다. 한 조합으로 두 방향을 막을 수 없다.
# → `A2`를 **가장 이른 행과 가장 최신 행 양쪽에** 두고 일치 행(`B1`)을 가운데 둔다.
#   그러면 `created_at`을 어느 방향으로 정렬하든 수준을 보지 않는 구현은 `A2`를 고른다.
# ⚠️ **이 배치가 막지 못하는 것 2개** — 둘 다 막지 않기로 한 판단이다. 설계서 §3.3
#   (`docs/design/2026-08-25-learning-coach-agent-design.md`)은 "수준에 맞는 행을 골라
#   시작한다"까지만 정하고 **여럿일 때 어느 것인지 정하지 않는다**(직접 읽어 확인). 문서가
#   요구하지 않는 규칙에 단정을 붙이지 않는다. 다만 어디까지 재는지는 정확히 적어 둔다:
#   ① **결정적으로 새는 자리** — 수준 절은 그대로 두고 **그 절 안의 정렬만** `order by s.id`
#      로 바꾸면 전건 초록이다(직접 재현: 558 passed, exit 0). 아래는 일치 행을 **1행만**
#      심으므로 그 절 안의 정렬이 아무 단정도 받지 않는다. 실무에서 도달하는 경로다 —
#      시드가 `A2` 3행이고(`scripts/migrate.py`) `users.current_level` 기본값도 `A2`라
#      (`001:17`) 세 행이 모두 일치해 그 절 안의 정렬이 어느 행인지를 결정한다.
#   ② **확률적으로 새는 자리** — `created_at`을 아예 보지 않고 `s.id`만으로 고르는 구현은
#      3행 중 하나를 무작위로 집는다(직접 5회: red 4 · pass 1). 확률로 지키는 단정을
#      만들지 않는다.
async def test_session_creation_prefers_a_scenario_matching_the_learners_level(
    db_pool: asyncpg.Pool, seed_scenarios_for_level
):
    user_id, (earliest, matching, newest) = await seed_scenarios_for_level(
        level="B1", scenarios=[("A2", 5), ("B1", 3), ("A2", 0)]
    )

    session_id = await create_session(db_pool, user_id)

    scenario_id = await _attached_scenario(db_pool, session_id)
    assert scenario_id == matching, "수준이 맞는 시나리오가 있는데 다른 행이 붙었다"
    # 실패 사유를 읽을 수 있게 두 극단을 따로 짚는다 — 어느 정렬로 새는지 바로 보인다.
    assert scenario_id != earliest, "수준을 무시하고 가장 이른 행을 골랐다"
    assert scenario_id != newest, "수준을 무시하고 가장 최신 행을 골랐다"


# AS4 / §9 Failure — 수준 일치가 0행이어도 시작이 실패하지 않고 **기존 동작(가장 이른 행)**
# 으로 떨어진다. 시드가 `A2` 3행뿐이라 수준이 올라가면 실제로 이 경로로 온다.
#
# ⚠️ `scenario_id is not null`로 재지 않는다 — 그 컬럼은 nullable 이고, 폴백 절을 지운
# 구현에서도 null 이 들어가 **단정이 어느 쪽이든 통과하지 않는다**. 붙은 행을 직접 지목한다.
# ⚠️ 불일치 행을 **2행** 심는다 (리뷰 라운드 1의 Important — 1행만 심으면 어떤 정렬이든
# 그 행을 골라서 "폴백 절이 존재한다"만 재고 **"가장 이른 행"이라는 규칙은 무보호**였다).
# 그 규칙은 이 커밋이 유지한다고 선언한 기존 계약이고
# `tests/harness/scenarios-E-agent-learning.md`가 문서에 못 박은 값이다.
async def test_session_creation_falls_back_to_the_earliest_scenario(
    db_pool: asyncpg.Pool, seed_scenarios_for_level
):
    user_id, (earliest, later) = await seed_scenarios_for_level(
        level="C2", scenarios=[("A2", 3), ("A2", 1)]
    )

    session_id = await create_session(db_pool, user_id)

    scenario_id = await _attached_scenario(db_pool, session_id)
    assert scenario_id == earliest, "수준 일치가 0행일 때 가장 이른 시나리오로 떨어지지 않았다"
    assert scenario_id != later
