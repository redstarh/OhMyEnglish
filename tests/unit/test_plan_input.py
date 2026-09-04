"""계획 입력 3계층을 한 자료구조로 모은다 (설계서 §4, 계획서 Task 4).

`load_plan_input`은 **읽기 전용**이다 — 복습 목록(review.py)·만성 지표(chronic.py)·최근 14일
발화·발음 시도를 한 곳에 모아 Claude 프롬프트로 넘길 재료를 만든다. 무엇이 약점인지·무엇을
연습할지는 여기서 판단하지 않는다(§3.2의 경계) — 그래서 이 파일에는 점수식 단정이 없다.

`load_completed_then_relapsed`(review.py)는 §6.2의 유일한 결정론적 만성 신호를 검증한다 —
3단계(1·3·7일)를 완주한 **뒤에** 다시 발생했는지를 본다.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg
import pytest

from app.services.plan_input import InvalidTimezoneError, _load_recent, load_plan_input
from app.services.review import load_completed_then_relapsed


# AS1 — 복습일이 지난 패턴이 여럿이면 **전부** 입력에 들어온다. 하나라도 빠지면 실패다.
@pytest.mark.asyncio
async def test_all_due_patterns_reach_the_input(db_conn: asyncpg.Connection, seed_due_patterns):
    user_id = await seed_due_patterns(db_conn, count=3)

    result = await load_plan_input(db_conn, user_id)

    assert len(result.due_reviews) == 3
    assert len({review.pattern_id for review in result.due_reviews}) == 3


# §4.2 — 최근 창은 14일이고 **학습자의 학습 발화만** 본다(명령 발화는 학습 이력이 아니고,
# 코치 발화는 학습자가 말한 것이 아니다 — 리뷰 Important-1). 코치 발화도 `utterance_type=
# 'learning'`으로 저장되므로(`utterances.py` 기본값) 종류만 거르면 코치 발화가 섞여
# 들어온다(2026-09-04 dev DB 실측: 14일 창 92행 중 54행이 코치 발화).
@pytest.mark.asyncio
async def test_recent_window_is_14_days_and_learning_only(
    db_conn: asyncpg.Connection, seed_utterance_at
):
    user_id = await seed_utterance_at(db_conn, days_ago=1, transcript="inside", kind="learning")
    await seed_utterance_at(db_conn, days_ago=1, transcript="a command", kind="voice_command")
    await seed_utterance_at(db_conn, days_ago=20, transcript="too old", kind="learning")
    await seed_utterance_at(
        db_conn, days_ago=1, transcript="coach reply", kind="learning", speaker="agent"
    )

    result = await load_plan_input(db_conn, user_id)

    transcripts = [item.transcript for item in result.recent]
    assert transcripts == ["inside"]
    assert result.window_to - result.window_from == timedelta(days=14)


# 리뷰 M4 — 14일 창의 하한은 포함이다(`>=`, `>`가 아니다). 벽시계로 부르면 이 테스트를 쓰는
# 시각과 `load_plan_input` 내부의 `clock_timestamp()` 호출 사이에 실제로 시간이 흘러 정확히
# 경계에 걸리는 데이터를 만들 수 없다(둘 다 "지금"을 기준으로 움직이는 목표라 항상 어긋난다).
# 그래서 `window_from`을 테스트가 직접 정해 `_load_recent`를 그 값으로 부른다 — SQL의 경계
# 조건 자체를 겨눈다.
@pytest.mark.asyncio
async def test_recent_window_lower_bound_is_inclusive(db_conn: asyncpg.Connection):
    user_id = await db_conn.fetchval(
        "insert into users (display_name) values ('Plan Input Boundary Test') returning id"
    )
    session_id = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        user_id,
    )
    boundary = datetime.now(UTC) - timedelta(days=14)
    await db_conn.execute(
        "insert into utterances "
        "(session_id, speaker, utterance_type, transcript, sequence_no, created_at) "
        "values ($1, 'user', 'learning', 'on the edge', 1, $2)",
        session_id,
        boundary,
    )

    included = await _load_recent(db_conn, user_id, boundary, datetime.now(UTC))

    assert [item.transcript for item in included] == ["on the edge"]


# §4.4 주의 1 — pending 은 미판정이라 계획 근거로 쓰지 않는다.
@pytest.mark.asyncio
async def test_pronunciation_pending_is_excluded(db_conn: asyncpg.Connection, seed_pronunciation):
    user_id = await seed_pronunciation(
        db_conn, [("th_as_s", "incorrect"), ("th_as_s", "pending"), ("f_as_p", "correct")]
    )

    result = await load_plan_input(db_conn, user_id)

    outcomes = {(tally.target_sound, tally.outcome) for tally in result.pronunciation}
    assert ("th_as_s", "pending") not in outcomes
    assert ("th_as_s", "incorrect") in outcomes
    assert ("f_as_p", "correct") in outcomes


# 리뷰 M3 — `target_sound`가 없는 시도(003이 nullable로 둔 경우)는 "어느 소리인지 모르는
# 시도"라 초점 패턴 후보가 될 수 없다. 제외하지 않으면 `PronunciationTally.target_sound`에
# `None`이 실려 그대로 Claude 프롬프트로 간다.
@pytest.mark.asyncio
async def test_pronunciation_without_a_target_sound_is_excluded(
    db_conn: asyncpg.Connection, seed_pronunciation
):
    user_id = await seed_pronunciation(db_conn, [("th_as_s", "incorrect"), (None, "incorrect")])

    result = await load_plan_input(db_conn, user_id)

    assert [tally.target_sound for tally in result.pronunciation] == ["th_as_s"]


# §6.2 — 3단계를 완주한 뒤 다시 발생한 패턴은 그 사실 자체로 만성이다.
#   틀림(day0) → day1·day4·day11 정답(완주) → day20 다시 틀림  ⇒ 신호 ON
@pytest.mark.asyncio
async def test_completed_then_relapsed_is_detected(db_conn: asyncpg.Connection, seed_cycle):
    user_id, pattern_id = await seed_cycle(
        db_conn,
        relapses=[0, 20],
        corrects=[1, 4, 11],
    )

    flagged = await load_completed_then_relapsed(db_conn, user_id)

    assert pattern_id in flagged


# 완주하지 못한 채 재발한 패턴은 신호가 켜지지 않는다 — 임계값을 발명하지 않는다.
@pytest.mark.asyncio
async def test_relapse_without_completion_is_not_flagged(db_conn: asyncpg.Connection, seed_cycle):
    user_id, pattern_id = await seed_cycle(
        db_conn,
        relapses=[0, 20],
        corrects=[1, 4],  # 2단계까지만 — 7일 단계를 통과하지 못했다
    )

    flagged = await load_completed_then_relapsed(db_conn, user_id)

    assert pattern_id not in flagged


# 리뷰 Important-2 — 완주 판정은 **재발 이전** 정답만 본다(`start < at < end`). 이 창을 지우면
# `fold_stages`가 다음 재발보다 한참 뒤의 정답까지 이어 접어 완주로 오판한다. 기존 두 테스트는
# 정답이 전부 첫 재발 구간(0~20일) 안에 있어 이 창의 유무와 무관하게 같은 결과가 나온다 —
# 이 테스트는 정답을 **전부 두 번째 재발(20일) 뒤**에 둬 그 창이 실제로 막는 오판을 겨눈다.
@pytest.mark.asyncio
async def test_corrects_after_the_next_relapse_do_not_count_as_completion(
    db_conn: asyncpg.Connection, seed_cycle
):
    user_id, pattern_id = await seed_cycle(
        db_conn,
        relapses=[0, 20],
        corrects=[25, 30, 40],  # 전부 두 번째 재발 뒤 — 첫 재발 구간(0~20일)은 비어 있다
    )

    flagged = await load_completed_then_relapsed(db_conn, user_id)

    assert pattern_id not in flagged


# 리뷰 M5 — 사용자가 없으면 조용히 빈 결과를 돌려주지 않고 실패한다(`chronic.py`의 같은
# 경로를 재는 `test_missing_user_raises_instead_of_defaulting_the_timezone`과 같은 이유).
@pytest.mark.asyncio
async def test_missing_user_raises_instead_of_silently_returning_nothing(
    db_conn: asyncpg.Connection,
):
    with pytest.raises(LookupError):
        await load_plan_input(db_conn, UUID("00000000-0000-0000-0000-0000000000ff"))


# LOW-14 — 타임존 값이 무효면 **조용히 UTC 로 떨어지지 않고** 읽을 수 있는 오류를 낸다.
@pytest.mark.asyncio
async def test_invalid_timezone_raises_readable_error(db_conn: asyncpg.Connection, seed_user):
    user_id = await seed_user(db_conn, tz="Not/AZone")

    with pytest.raises(InvalidTimezoneError) as excinfo:
        await load_plan_input(db_conn, user_id)

    assert "Not/AZone" in str(excinfo.value)


# 리뷰 M2 — 검증이 `at time zone`(chronic.py가 실제로 쓰는 연산자)보다 엄격하면 **동작하는
# 설정을 여기서만 거부**한다. `pg_timezone_names`는 대소문자를 가리지만(2026-09-04 실측:
# `asia/seoul`은 `false`) `at time zone 'asia/seoul'`은 정상 동작한다 — `users.timezone`에
# CHECK가 없어 소문자 값이 실제로 들어올 수 있다.
@pytest.mark.asyncio
async def test_lowercase_timezone_is_accepted(db_conn: asyncpg.Connection, seed_user):
    user_id = await seed_user(db_conn, tz="asia/seoul")

    result = await load_plan_input(db_conn, user_id)

    assert result.timezone == "asia/seoul"
