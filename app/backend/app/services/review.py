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
# `u.created_at > r.at`의 strict `>`는 **관측 가능한 효과가 없다 — 중복 방어다**(2026-09-04
# 실측: `>=`로 바꿔도 전체 스위트가 통과한다). 이유: 재발과 같은 순간의 정답은 `anchor`와
# 시각이 같으므로 `fold_stages`의 간격 조건(`said_at < anchor + STAGE_DAYS[0]`)이 어차피
# 건너뛴다. **실제 방벽은 fold의 간격 조건 하나다** — 여기를 고치기 전에 그쪽을 본다.
# 그래도 `>`를 남기는 이유는 SQL만 읽는 사람에게 "재발 이후"라는 의도를 보이기 위해서다.
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
             -- `r.at is null or`도 관측 불가능하다: relapse가 없으면 `fold_stages`가
             -- `correct_times`를 **읽기 전에** return하므로 이 배열이 무엇이든 결과가 같다.
             -- 남기는 이유는 SQL 단독으로도 의미가 통하게 하는 것이다(`> null`은 0행이 된다).
             and (r.at is null or u.created_at > r.at)),
         '{}'::timestamptz[]
       ) as correct_times
  from relapse r, context ctx
"""

_APPLY_PATTERN_SQL = """
update error_patterns set next_review_at = $2, mastery_score = $3 where id = $1
"""

# 설계서 §4.1의 "오늘 다뤄야 하는 목록". **`clock_timestamp()`를 쓴다** — Postgres `now()`는
# 트랜잭션 시작 시각에 고정되므로 시간 기반 판정이 무력화된다(Phase 1 §5.4 실측).
# `order by`가 가장 밀린 것을 앞에 놓는다: 연체는 무효가 아니라 더 시급한 것이다.
_DUE_REVIEWS_SQL = """
select p.id as pattern_id, p.pattern_key, p.category, p.target_form,
       p.next_review_at, p.mastery_score
  from error_patterns p
 where p.user_id = $1
   and p.next_review_at is not null
   and p.next_review_at <= clock_timestamp()
 order by p.next_review_at
"""

# 백필 대상. 이력에서만 계산하므로 **전체를 훑는 것이 안전하고 멱등이다**.
_ALL_PATTERNS_SQL = "select id from error_patterns where user_id = $1 order by pattern_key"

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

    ⚠️ **전제조건: `attempts`는 canonical `pattern_key`로 중복이 제거돼 있어야 한다.**
    같은 key가 두 번 오면 `unique(pattern_id, utterance_id)` 위반으로 호출자의 트랜잭션이
    통째로 깨진다 — 그 발화의 교정까지 함께 사라진다. 지금 그것을 보장하는 것은
    `services.analysis.resolve_pattern_keys`의 dict 수집 하나다(그 함수를 고칠 때 이 계약을 본다).
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
            # `completed`면 `fold_stages`가 `stage=FINAL_STAGE`를 보장하므로 분기가 필요 없다.
            state.stage,
            state.next_review_at or state.anchor,
            "done" if state.completed else "pending",
        )
    return state


@dataclass(frozen=True, slots=True)
class DueReview:
    """복습 예정일이 지난 패턴 한 건 (설계서 §4.1의 목록 항목)."""

    pattern_id: UUID
    pattern_key: str
    category: str
    target_form: str
    next_review_at: datetime
    mastery_score: float


async def load_due_reviews(conn: asyncpg.Connection, user_id: UUID) -> list[DueReview]:
    """오늘 다뤄야 하는 복습 목록 — 예정일이 지난 것만, **가장 밀린 것부터** (설계서 §4.1).

    **놓치면 안 되는 목록이라 판정을 Claude에 맡기지 않는다**(§3.2의 경계). 소비자는 슬라이스 2의
    계획 생성이고, 이 슬라이스에서 함수를 두는 이유는 두 가지다: ① 슬라이스 1의 완료 판정
    ("복습 목록이 처음으로 값을 갖는다")을 **실제로 증명할 수 있게** 한다 ② `now()` 대신
    `clock_timestamp()`를 써야 한다는 §4.1의 함정을 이 슬라이스 안에서 고정한다 —
    아니면 슬라이스 2가 같은 함정을 다시 밟는다.
    """
    records = await conn.fetch(_DUE_REVIEWS_SQL, user_id)
    return [
        DueReview(
            pattern_id=record["pattern_id"],
            pattern_key=record["pattern_key"],
            category=record["category"],
            target_form=record["target_form"],
            next_review_at=record["next_review_at"],
            mastery_score=float(record["mastery_score"]),
        )
        for record in records
    ]


# 완주 판정에는 **재발 이전** 정답까지 필요하다 — `_HISTORY_SQL`은 마지막 재발 이후만 보므로
# 이 판정에 쓸 수 없다. 그래서 전체 이력을 시각만 뽑아 온다(단일 사용자 규모라 전량이 싸다).
_FULL_HISTORY_SQL = """
select p.id as pattern_id,
       coalesce((
         select array_agg(t.at order by t.at)
           from (
                 select u.created_at as at
                   from error_occurrences eo
                   join utterances u on u.id = eo.utterance_id
                  where eo.pattern_id = p.id
                 union all
                 select u.created_at as at
                   from pattern_attempts pa
                   join utterances u on u.id = pa.utterance_id
                  where pa.pattern_id = p.id and pa.outcome = 'incorrect'
                ) t
       ), '{}'::timestamptz[]) as relapse_times,
       coalesce((
         select array_agg(u.created_at order by u.created_at, pa.id)
           from pattern_attempts pa
           join utterances u on u.id = pa.utterance_id
          where pa.pattern_id = p.id and pa.outcome = 'correct'
       ), '{}'::timestamptz[]) as correct_times
  from error_patterns p
 where p.user_id = $1
 order by p.pattern_key
"""


async def load_completed_then_relapsed(conn: asyncpg.Connection, user_id: UUID) -> set[UUID]:
    """3단계(1·3·7일)를 완주한 **뒤에** 다시 발생한 패턴들 (설계서 §6.2).

    이것이 설계서가 허용한 **유일한 결정론적 만성 신호**다 — 임계값이 아니라 문서로 확정된
    1·3·7일에서 유도되기 때문이다(§3.2). 판정 자체는 `fold_stages`가 하고 이 함수는
    사이클을 잘라 넘기기만 한다. **복습 단계의 정의를 여기 복제하지 않는다.**

    한 번 완주한 뒤 재발했다면 그 사실은 이후에도 참이므로, 연속한 재발 쌍을 모두 본다.
    마지막 재발 이후의 열린 구간은 세지 않는다 — 아직 "재발이 뒤따랐다"가 성립하지 않는다.
    """
    flagged: set[UUID] = set()
    for record in await conn.fetch(_FULL_HISTORY_SQL, user_id):
        relapses = list(record["relapse_times"])
        corrects = list(record["correct_times"])
        for start, end in zip(relapses, relapses[1:], strict=False):
            within = [at for at in corrects if start < at < end]
            if fold_stages(start, within, "").completed:
                flagged.add(record["pattern_id"])
                break
    return flagged


async def recompute_all(conn: asyncpg.Connection, user_id: UUID) -> int:
    """이 사용자의 **모든** 패턴에 `recompute`를 돌린다. 건드린 패턴 수를 돌려준다.

    **백필용이다.** `recompute`는 분석이 건드린 패턴에만 돌기 때문에, 006 **전에** 쌓인
    패턴은 그 패턴이 다시 발생할 때까지 예정일을 받지 못한다 — 마이그레이션 직후에도
    `load_due_reviews`가 0행이라 슬라이스 1의 완료 판정이 실물에서 성립하지 않는다
    (2026-09-04 dev DB 실측: 패턴 7행·occurrence 17행인데 예정일 0건).

    이력에서만 계산하므로 몇 번 돌려도 같은 결과다(멱등). 호출자의 트랜잭션에서 돈다.
    """
    pattern_ids = [record["id"] for record in await conn.fetch(_ALL_PATTERNS_SQL, user_id)]
    for pattern_id in pattern_ids:
        await recompute(conn, pattern_id)
    return len(pattern_ids)
