"""복습 스케줄의 소유자 — 재발화 판정 기록과 복습 상태 재계산 (설계서 §4.1·§8.1).

`next_review_at`에 값을 넣는 코드는 이 모듈뿐이다. 세션·워커는 배선만 한다.

**단계를 증분하지 않고 이력에서 다시 접는다.** 이 모듈에서 이것 하나만 기억하면 된다.
`analyze_utterance` job은 재시도되고 결과 저장은 발화 단위 replace라서, `stage + 1`로
전이시키면 재실행마다 단계가 올라가 학습자가 하지 않은 복습이 완주된다. 그래서 상태를
`error_occurrences`와 `pattern_attempts`에서 매번 다시 계산한다 — `frequency`를 `+1`하지
않고 행 수에서 다시 세는 것(`services/analysis.py`)과 같은 규약이고, 같은 이유다.

**그리고 정답 횟수를 세지 않는다 — 예정일을 하나씩 접는다.** §4.1의 "복습을 완주하면 다음
단계로 진행한다"는 그 단계의 예정일이 온 뒤에 다시 맞혔다는 뜻이고, 복습 목록의 판정도
`next_review_at <= clock_timestamp()`다. 단순히 correct를 3번 세면 같은 세션에서 세 번
맞히는 것으로 1·3·7일을 한 번도 경과하지 않고 완주해 간격 반복이 무의미해진다.
`fold_stages`가 그 조건을 담고, **순수 함수**라 DB 없이 검증된다.

시각의 기준은 **발화 시각**이다. `now()`를 기준으로 쓰면 재실행마다 예정일이 밀려 멱등이
깨진다. 간격 연산은 `timedelta`라 타임존과 무관하다 — 달력 날짜를 쓰는 곳은 이 모듈에
없다(만성 지표의 "재발 일수"가 그 경계를 갖고 `services/chronic.py`가 소유한다).

`review_tasks`는 패턴당 **0행 또는 1행**이다. 재계산은 그 패턴의 행을 전부 지운 뒤 현재
상태 1행을 넣는다 — `unique(pattern_id, review_stage)`와 맞물리는 유일한 형태이고, 지운
이력이 손실이 아닌 근거는 완주·재발 여부가 `pattern_attempts`·`error_occurrences`에서
언제든 다시 계산된다는 것이다 (캡틴 결정 2026-09-03).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.models.analysis import PatternAttempt

logger = logging.getLogger(__name__)

# 복습 주기 1·3·7일 3단계. **문서로 확정된 값이다** (설계서 §4.1 "1일 → 3일 → 7일",
# `docs/database-schema.md`) — 발명값이 아니다. 완주까지 최소 11일이 실제로 경과한다.
STAGE_DAYS: tuple[int, ...] = (1, 3, 7)
FINAL_STAGE: int = len(STAGE_DAYS)

# mastery_score는 점수가 아니라 **상태 마커**다 (캡틴 결정 2026-09-03): 3단계를 재발 없이
# 완주했는지만 담는다. 중간값을 만들지 않는 이유는 설계서 §3.2 — 임계값을 발명하지 않는다.
# 재발로 100 → 0이 되어도 정보를 잃지 않는다: 완주 이력은 `pattern_attempts`에 그대로 남아
# "3단계 소진 후 재발"(§6.2의 결정론적 만성 신호)을 언제든 다시 계산할 수 있다.
MASTERED = Decimal("100")
NOT_MASTERED = Decimal("0")

# 슬라이스 1은 무엇도 생성하지 않으므로(§3.2의 경계) 과제 유형은 "다시 말해보기" 하나다.
# 슬라이스 2가 Claude 산출 상황(`suggested_contexts`)으로 이 자리를 넓힌다.
REVIEW_TASK_TYPE = "rephrase"

_DELETE_ATTEMPTS_SQL = """
delete from pattern_attempts where utterance_id = $1 returning pattern_id
"""

# pattern_key → pattern_id 해석을 insert 안에서 한다: 목록에 없는 key는 select가 0행을
# 돌려주어 **행이 생기지 않는다**. 별도 조회 없이 "조용히 버린다"가 성립한다.
_INSERT_ATTEMPT_SQL = """
insert into pattern_attempts (pattern_id, utterance_id, outcome)
select p.id, $2, $3
  from error_patterns p
 where p.user_id = $1 and p.pattern_key = $4
returning pattern_id
"""

# 접기에 필요한 이력만 읽는다. 단계 전이는 파이썬(`fold_stages`)이 한다 — 각 단계의 통과
# 시각이 다음 단계의 기준이 되는 **연쇄**라서 집계 함수로 표현되지 않는다(재귀 CTE 회피).
#
# `greatest`는 NULL 인자를 건너뛴다(Postgres 의미론, 2026-09-03 실측) — 그래서 occurrence만
# 있거나 incorrect만 있는 경우가 분기 없이 처리된다.
# `u.created_at > r.at`의 **strict `>`**: 같은 발화에 오류와 정답이 함께 달린 모순된 판정에서
# 그 정답을 세지 않는다. 그 순간에는 틀린 것으로 남는다.
# `order by`를 지우지 말 것 — `fold_stages`의 전제조건이 오름차순이고, 순서가 흐트러지면
# 단계가 조용히 틀린다(예외도 실패도 없이).
_HISTORY_SQL = """
with relapse as (
      select greatest(
               (select max(u.created_at)
                  from error_occurrences eo
                  join utterances u on u.id = eo.utterance_id
                 where eo.pattern_id = $1),
               (select max(u.created_at)
                  from pattern_attempts pa
                  join utterances u on u.id = pa.utterance_id
                 where pa.pattern_id = $1 and pa.outcome = 'incorrect')
             ) as at
),
context as (
      select coalesce(
               (select eo.original_span
                  from error_occurrences eo
                  join utterances u on u.id = eo.utterance_id
                 where eo.pattern_id = $1
                 order by u.created_at desc, eo.id desc
                 limit 1),
               (select target_form from error_patterns where id = $1)
             ) as scenario_context
)
select r.at as relapse_at,
       ctx.scenario_context,
       coalesce(
         (select array_agg(u.created_at order by u.created_at, pa.id)
            from pattern_attempts pa
            join utterances u on u.id = pa.utterance_id
           where pa.pattern_id = $1
             and pa.outcome = 'correct'
             and (r.at is null or u.created_at > r.at)),
         '{}'::timestamptz[]
       ) as correct_times
  from relapse r, context ctx
"""

_APPLY_PATTERN_SQL = """
update error_patterns set next_review_at = $2, mastery_score = $3 where id = $1
"""

_DELETE_TASKS_SQL = """
delete from review_tasks where pattern_id = $1
"""

_INSERT_TASK_SQL = """
insert into review_tasks (pattern_id, task_type, scenario_context, review_stage, due_at, status)
values ($1, $2, $3, $4, $5, $6)
"""


@dataclass(frozen=True, slots=True)
class ReviewState:
    """패턴 하나의 복습 상태 — 이력에서 계산된 파생물이고 그 자체로는 저장되지 않는다."""

    stage: int
    completed: bool
    next_review_at: datetime | None
    anchor: datetime | None
    scenario_context: str


def fold_stages(
    relapse_at: datetime | None, correct_times: list[datetime], scenario_context: str
) -> ReviewState:
    """마지막 재발 이후의 정답들을 훑어 **예정일을 넘긴 것만** 단계로 센다 (순수 함수).

    `correct_times`는 발화 시각 오름차순이어야 한다 — `_HISTORY_SQL`이 그 순서로 돌려준다.
    예정일 전의 정답은 건너뛴다: 기록(`pattern_attempts`)에는 남고 단계만 올리지 않는다.
    한 세션에서 여러 번 맞히는 것으로 1·3·7일을 건너뛰는 경로를 막는 것이 이 조건이다.
    반대로 예정일을 **한참 지나** 맞힌 것은 그대로 통과시킨다 — "너무 늦은 복습"의 상한을
    발명하지 않는다(§3.2). 늦게 맞히는 쪽이 더 어려운 조건이라 약한 증거일 이유도 없다.

    `relapse_at`이 없으면 틀린 적이 없는 패턴이므로 복습할 것이 없다 — 재분석으로
    occurrence가 전부 지워진 패턴도 이 경로로 목록에서 빠진다.
    """
    if relapse_at is None:
        return ReviewState(
            stage=1,
            completed=False,
            next_review_at=None,
            anchor=None,
            scenario_context=scenario_context,
        )

    anchor = relapse_at
    stage = 1
    for said_at in correct_times:
        if said_at < anchor + timedelta(days=STAGE_DAYS[stage - 1]):
            continue  # 예정일 전 — 간격이 경과하지 않았다
        anchor = said_at
        stage += 1
        if stage > FINAL_STAGE:
            return ReviewState(
                stage=FINAL_STAGE,
                completed=True,
                next_review_at=None,
                anchor=anchor,
                scenario_context=scenario_context,
            )
    return ReviewState(
        stage=stage,
        completed=False,
        next_review_at=anchor + timedelta(days=STAGE_DAYS[stage - 1]),
        anchor=anchor,
        scenario_context=scenario_context,
    )


async def store_attempts(
    conn: asyncpg.Connection,
    utterance_id: UUID,
    user_id: UUID,
    attempts: list[PatternAttempt],
) -> set[UUID]:
    """이 발화의 재시도 판정을 **replace 저장**하고 건드린 패턴 id 집합을 돌려준다.

    지워진 행의 pattern_id도 집합에 넣는다 — 재분석에서 사라진 판정의 패턴을 다시 계산하지
    않으면 그 패턴이 낡은 단계에 남는다(`_DELETE_OCCURRENCES_SQL`이 pattern_id를 돌려받는
    것과 같은 이유).

    호출자의 트랜잭션 안에서 돈다. 자기 트랜잭션을 열지 않는다 — 판정 기록과 그에 따른 단계
    갱신이 갈라지면 절반만 반영된 상태가 남는다(설계서 §9 Dependency).
    """
    removed = await conn.fetch(_DELETE_ATTEMPTS_SQL, utterance_id)
    touched: set[UUID] = {record["pattern_id"] for record in removed}
    for attempt in attempts:
        pattern_id = await conn.fetchval(
            _INSERT_ATTEMPT_SQL, user_id, utterance_id, attempt.outcome, attempt.pattern_key
        )
        if pattern_id is None:
            # `resolve_pattern_keys`의 정규화를 통과했는데도 행이 없다 = 그 사이 패턴이
            # 사라졌다(재분석으로 occurrence가 0이 되어 정리된 경우). 버리고 계속한다.
            logger.warning(
                "attempt for pattern_key %r stored no row — pattern is gone", attempt.pattern_key
            )
            continue
        touched.add(pattern_id)
    return touched


async def recompute(conn: asyncpg.Connection, pattern_id: UUID) -> ReviewState:
    """패턴 하나의 복습 상태를 이력에서 다시 계산해 반영한다 (멱등).

    `error_patterns`(`next_review_at`·`mastery_score`)와 `review_tasks` 0~1행을 함께 맞춘다.
    호출자의 트랜잭션 안에서 돈다.
    """
    record = await conn.fetchrow(_HISTORY_SQL, pattern_id)
    if record is None:  # 방어: 교차 조인이라 항상 1행이지만 계약을 코드로 남긴다
        raise LookupError(f"review history query returned no row for pattern {pattern_id}")

    state = fold_stages(
        record["relapse_at"], list(record["correct_times"] or []), record["scenario_context"]
    )

    await conn.execute(
        _APPLY_PATTERN_SQL,
        pattern_id,
        state.next_review_at,
        MASTERED if state.completed else NOT_MASTERED,
    )
    # 지우고 다시 넣는다 — 한 statement 안의 delete/insert는 서로의 효과를 보지 못해
    # unique(pattern_id, review_stage)에 부딪힌다. 두 문장으로 나누는 것이 그 함정을 피한다.
    await conn.execute(_DELETE_TASKS_SQL, pattern_id)
    if state.anchor is not None:
        await conn.execute(
            _INSERT_TASK_SQL,
            pattern_id,
            REVIEW_TASK_TYPE,
            state.scenario_context,
            FINAL_STAGE if state.completed else state.stage,
            state.next_review_at or state.anchor,
            "done" if state.completed else "pending",
        )
    return state
