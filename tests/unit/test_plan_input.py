"""계획 입력 3계층을 한 자료구조로 모은다 (설계서 §4, 계획서 Task 4).

`load_plan_input`은 **읽기 전용**이다 — 복습 목록(review.py)·만성 지표(chronic.py)·최근 14일
발화·발음 시도를 한 곳에 모아 Claude 프롬프트로 넘길 재료를 만든다. 무엇이 약점인지·무엇을
연습할지는 여기서 판단하지 않는다(§3.2의 경계) — 그래서 이 파일에는 점수식 단정이 없다.

`load_completed_then_relapsed`(review.py)는 §6.2의 유일한 결정론적 만성 신호를 검증한다 —
3단계(1·3·7일)를 완주한 **뒤에** 다시 발생했는지를 본다.
"""

from datetime import timedelta

import asyncpg
import pytest

from app.services.plan_input import InvalidTimezoneError, load_plan_input
from app.services.review import load_completed_then_relapsed


# AS1 — 복습일이 지난 패턴이 여럿이면 **전부** 입력에 들어온다. 하나라도 빠지면 실패다.
@pytest.mark.asyncio
async def test_all_due_patterns_reach_the_input(db_conn: asyncpg.Connection, seed_due_patterns):
    user_id = await seed_due_patterns(db_conn, count=3)

    result = await load_plan_input(db_conn, user_id)

    assert len(result.due_reviews) == 3
    assert len({review.pattern_id for review in result.due_reviews}) == 3


# §4.2 — 최근 창은 14일이고 학습 발화만 본다(명령 발화는 학습 이력이 아니다).
@pytest.mark.asyncio
async def test_recent_window_is_14_days_and_learning_only(
    db_conn: asyncpg.Connection, seed_utterance_at
):
    user_id = await seed_utterance_at(db_conn, days_ago=1, transcript="inside", kind="learning")
    await seed_utterance_at(db_conn, days_ago=1, transcript="a command", kind="voice_command")
    await seed_utterance_at(db_conn, days_ago=20, transcript="too old", kind="learning")

    result = await load_plan_input(db_conn, user_id)

    transcripts = [item.transcript for item in result.recent]
    assert transcripts == ["inside"]
    assert result.window_to - result.window_from == timedelta(days=14)


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


# LOW-14 — 타임존 값이 무효면 **조용히 UTC 로 떨어지지 않고** 읽을 수 있는 오류를 낸다.
@pytest.mark.asyncio
async def test_invalid_timezone_raises_readable_error(db_conn: asyncpg.Connection, seed_user):
    user_id = await seed_user(db_conn, tz="Not/AZone")

    with pytest.raises(InvalidTimezoneError) as excinfo:
        await load_plan_input(db_conn, user_id)

    assert "Not/AZone" in str(excinfo.value)
