"""만성 약점 지표 — 조회 시 계산 (설계서 §6.1).

**읽기 전용이다.** 롤업 테이블을 두는 안은 설계서 §6.1에서 기각됐다 — 단일 사용자 규모에서
결과가 같고 갱신 시점·신선도 관리만 늘어난다(YAGNI). 그래서 이 모듈에 쓰기 함수가 없다.

두 가지가 이 쿼리의 존재 이유다.

* **지속 기간을 `error_patterns.created_at`으로 계산하지 않는다.** 라이브 DB에서
  `last_seen_at - created_at`이 **음수(-3.8초)** 로 나왔다(§6.1 실측) — 패턴 행의 insert
  시각과 발화 시각이 다른 출처이기 때문이다. 지속 기간은 발화 시각의 min/max로만 낸다.
* **재발 일수는 사용자 타임존의 달력 날짜다.** UTC로 세면 KST 자정 전후의 두 발화가 2일로
  갈린다(함정 H-S, 실측). 타임존의 SoT는 `users.timezone` **컬럼**이고 호스트 시각이나
  세션 기본값이 아니다 — 그래서 이 함수가 그 값을 먼저 읽는다.

**만성 여부를 판정하지 않는다** (§6.2) — 임계값을 발명하지 않고 사실만 돌려준다. 판정은
Claude가 하고, 그 호출은 슬라이스 2의 계획 생성이 소유한다. §6.2의 결정론적 신호
("3단계를 소진한 뒤 재발")도 슬라이스 2의 몫이다 — `pattern_attempts`와
`error_occurrences`에서 언제든 재계산되므로 여기서 미리 만들지 않는다.

⚠️ `deepest_recurrence`는 그 규칙의 예외가 아니다 — **임계값을 두지 않고 순서만 낸다.**
"만성인가"를 정하지 않고 "이미 계산된 지표 중 어느 것이 가장 깊은가"만 답한다. 이 함수가
이 모듈에 있는 이유는 `ChronicMetric`을 소유한 쪽이 그 필드의 우선순위도 소유해야 하기
때문이다 — 깊이 축을 바꾸면 여기 한 곳만 고친다. AC11-2가 그 최상위를 초점에 강제하는
자리는 `models/plan.py`의 `parse_plan`이고, 그 둘을 잇는 배선은 `services/plan.py`다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

import asyncpg

_TIMEZONE_SQL = "select timezone from users where id = $1"

# `lag()`로 인접 발생의 간격을 내고 그 최대값을 취한다 — `frequency=5`가 하루에 몰린 것과
# 3개월에 흩어진 것은 완전히 다르고, 그중 **한동안 사라졌다가 다시 나온 것**이 가장 위험한
# 신호다(§6.1). 발생이 1건이면 `prev_at`이 없어 공백은 null이 된다.
_METRICS_SQL = """
with occurrence as (
      select eo.pattern_id, eo.id as occurrence_id, u.session_id, u.created_at
        from error_occurrences eo
        join utterances u on u.id = eo.utterance_id
        join error_patterns p on p.id = eo.pattern_id
       where p.user_id = $1
),
gap as (
      select pattern_id, max(created_at - prev_at) as max_gap
        from (
               select pattern_id, created_at,
                      lag(created_at) over (
                        partition by pattern_id order by created_at, occurrence_id
                      ) as prev_at
                 from occurrence
             ) windowed
       where prev_at is not null
       group by pattern_id
)
select p.id                                                  as pattern_id,
       p.pattern_key,
       p.category,
       p.frequency,
       p.mastery_score,
       p.next_review_at,
       count(distinct o.session_id)                          as recurring_sessions,
       -- 달력 날짜는 사용자 타임존으로 센다 (함정 H-S). current_date 를 쓰지 않는다.
       count(distinct (o.created_at at time zone $2)::date)  as recurring_days,
       min(o.created_at)                                     as first_seen,
       max(o.created_at)                                     as last_seen,
       max(o.created_at) - min(o.created_at)                  as span,
       g.max_gap
  from error_patterns p
  join occurrence o on o.pattern_id = p.id
  left join gap g on g.pattern_id = p.id
 where p.user_id = $1
 group by p.id, g.max_gap
 order by p.pattern_key
"""


@dataclass(frozen=True, slots=True)
class ChronicMetric:
    """패턴 하나의 만성 지표 — 전부 사실이고, 판정은 들어 있지 않다(§6.2)."""

    pattern_id: UUID
    pattern_key: str
    category: str
    frequency: int
    mastery_score: float
    next_review_at: datetime | None
    recurring_sessions: int
    recurring_days: int
    first_seen: datetime
    last_seen: datetime
    span: timedelta
    max_gap: timedelta | None


def _depth(metric: ChronicMetric) -> tuple[int, int, int]:
    """깊이 축 — 빈도, 그다음 연속 세션 수, 그다음 연속 일수. 큰 쪽이 더 깊다."""
    return (metric.frequency, metric.recurring_sessions, metric.recurring_days)


def deepest_recurrence(chronic: list[ChronicMetric]) -> ChronicMetric | None:
    """AC11-2의 **"가장 깊은 재발"** 1건. 만성 목록이 비면 `None`.

    규칙의 정본은 `docs/design/2026-09-06-review-outcomes.md` §2다 — 여기서 발명한 것이
    아니고, 그 §2가 개발 DB 실측으로 정했다:

    * **`frequency`가 축이다.** `mastery_score`는 패턴 7개가 **전부 `0.00`**이라 어떤 순위도
      만들지 못한다(판별력 0). `frequency`는 `7·3·3·2·2·1·1`로 갈린다.
    * **동률은 `recurring_sessions` → `recurring_days`로 깬다.** 같은 빈도라도 여러 세션·여러
      날에 걸쳐 나온 쪽이 더 뿌리 깊게 재발한다.
    * **복습 예정(`DueReview`)은 섞지 않는다** — 그것은 **시간** 축이고 깊이 축이 아니다.
      이 함수가 `ChronicMetric`만 받는 것이 그 경계다(`DueReview`에는 `frequency`가 아예 없다).

    `None`을 돌려주는 경우가 **콜드스타트**다: 최상위가 존재하지 않으므로 강제할 대상이 없고,
    그때 계획 생성을 막으면 첫 세션부터 계획이 못 만들어진다. 그래서 이 값을 받는
    `parse_plan`은 `None`을 "이 규칙을 적용하지 않는다"로 읽는다.

    ⚠️ **남는 약점 하나**: 세 축이 **전부** 같은 두 패턴은 이 함수로 구분되지 않는다. 그때는
    `load_chronic_metrics`의 `order by p.pattern_key`가 정한 순서에서 앞선 것이 이긴다(`max`는
    첫 최대값을 돌려준다) — 결정론적이긴 하지만, 같은 깊이의 다른 패턴을 초점으로 고른 계획이
    거부될 수 있다. §2가 정한 동률 규칙은 두 축까지이므로 그 이상을 발명하지 않았다.
    """
    return max(chronic, key=_depth, default=None)


async def load_chronic_metrics(conn: asyncpg.Connection, user_id: UUID) -> list[ChronicMetric]:
    """이 학습자의 패턴별 만성 지표. 발생이 0건인 패턴은 포함되지 않는다.

    타임존을 `users.timezone`에서 **읽어서** 쿼리에 넘긴다. 사용자가 없으면 그 SoT가 없으므로
    조용히 UTC로 떨어지지 않고 `LookupError`를 올린다 — 조용한 폴백은 재발 일수를 하루씩
    어긋나게 만들고, 그 오차는 복습 주기와 일일 계획으로 번진다(H-S).
    """
    timezone = await conn.fetchval(_TIMEZONE_SQL, user_id)
    if timezone is None:
        raise LookupError(f"user {user_id} not found — no timezone source of truth")

    records = await conn.fetch(_METRICS_SQL, user_id, timezone)
    return [
        ChronicMetric(
            pattern_id=record["pattern_id"],
            pattern_key=record["pattern_key"],
            category=record["category"],
            frequency=record["frequency"],
            mastery_score=float(record["mastery_score"]),
            next_review_at=record["next_review_at"],
            recurring_sessions=record["recurring_sessions"],
            recurring_days=record["recurring_days"],
            first_seen=record["first_seen"],
            last_seen=record["last_seen"],
            span=record["span"],
            max_gap=record["max_gap"],
        )
        for record in records
    ]
