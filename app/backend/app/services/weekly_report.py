"""주간 학습 리포트 — 주 경계와 사실·판단의 적재 (`TASK-26`).

설계: `docs/design/2026-09-14-weekly-report-design.md`.

**이 모듈이 주 경계를 소유한다.** `daily_summary.py` 가 「오늘」의 정의를 한 곳에 모은 것과 같은
이유다 — 두 자리에서 각자 계산하면 경계가 갈리고, 갈린 것을 아무 것도 알려 주지 않는다.

⛔ **`current_date` 를 쓰지 않는다.** UTC 자정~09:00(KST) 구간에 그 값이 KST 날짜보다 하루 이르다는
것이 이 리포의 실측이고, R13-3 이 같은 것을 요구한다. 경계의 정본은 **`users.timezone` 컬럼**이다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from uuid import UUID

import asyncpg

# 화면에 실을 상위 오류의 상한. ⚠️ **발명값이다** — PRD 가 개수를 정하지 않았다. 근거는 하나뿐이다:
# 한 주를 되짚는 화면이 목록으로 덮이지 않을 크기. 일일 요약은 20종을 담고(하루라 더 넓다) 주간은
# 「상위」를 보여 주는 것이 요구(`PRD:117`)이므로 더 좁다.
# ⛔ 전체 수는 `occurrence_count`·`pattern_count` 가 따로 들고 있다 — 이 목록을 세면 잘린 만큼
#    어긋난다(일일 요약이 같은 이유로 두 값을 따로 담았다).
TOP_PATTERN_LIMIT = 5

# 사용자 타임존의 「지금」에서 **지난 주 월요일**.
#
# ⚠️ `date_trunc('week', …)` 가 월요일을 주 시작으로 쓰는 것은 Postgres 의 성질이고 발명이 아니다
# (ISO 8601 · 캡틴 결정 4·58 이 요구한 경계와 같다). 023 의
# `weekly_reports_week_starts_on_monday` 가 같은 경계를 **값역으로** 못박으므로, 이 계산이 흔들리면
# 그 CHECK 가 삽입에서 잡는다 — 두 겹이 서로를 지킨다.
_LAST_WEEK_START_SQL = """
select (date_trunc('week', now() at time zone u.timezone) - interval '7 days')::date
  from users u
 where u.id = $1
"""


async def last_week_start(conn: asyncpg.Connection, user_id: UUID) -> date:
    """그 사용자의 **지난 주 월요일**. 사용자가 없으면 `LookupError` 를 올린다.

    ⛔ **없는 사용자를 `None` 으로 넘기지 않는다** — 주간 리포트의 대상이 없다는 것은 정상 상태가
    아니고(세션이 사용자에 매여 있다), `None` 을 돌려주면 호출자가 그것을 날짜처럼 쓰다가 뒤에서
    터진다. `load_session_clip` 이 `None` 을 쓰는 것은 그쪽의 부재가 **정상**이기 때문이다.
    """
    week_start = await conn.fetchval(_LAST_WEEK_START_SQL, user_id)
    if week_start is None:
        raise LookupError(f"user {user_id} not found — 주 경계를 구할 수 없다")
    return week_start


@dataclass(frozen=True, slots=True)
class TopPattern:
    """그 주 상위 오류 한 종. **화면이 쓰는 것만** 담는다.

    ⛔ `mastery_score` 를 담지 않는다 — 패턴이 전부 `0.00` 이라 **판별력이 0** 이고(그 실측은
    `chronic.py:deepest_recurrence` 주석이 갖는다), 0 을 실어 보내면 화면이나 모델이 「숙련도가
    낮다」는 없는 신호를 읽는다.
    """

    category: str
    pattern_key: str
    target_form: str
    occurrences: int


@dataclass(frozen=True, slots=True)
class WeekFacts:
    """한 주의 **사실**. R11-8 의 *"조회는 사실을 제공한다"* 가 이 자료구조의 경계다.

    ⛔ **판정을 담지 않는다** — 개선 여부·만성 여부·점수는 모델의 것이고(`insights`), 이 값들은
    그 판단의 **입력**이다. 여기에 판정을 더하면 제품이 임계값을 발명하는 셈이 된다(R11-8 위반).
    ⚠️ `occurrence_count`·`pattern_count` 를 따로 담는 이유: `top_patterns` 가 상한에서 잘리므로
    그것을 세면 전체 수와 어긋난다(일일 요약이 같은 이유로 두 값을 따로 담았다).
    """

    week_start: date
    session_count: int
    occurrence_count: int
    pattern_count: int
    top_patterns: list[TopPattern]


# 그 주의 사실 셋을 한 왕복으로 읽는다.
#
# ⛔ **창을 반열림 `[week_start, week_start + 7)` 으로 쓴다.** `between` 은 끝을 **포함**하므로 다음
# 주 월요일이 함께 들어온다 — 그 하루가 두 리포트에 겹쳐 들어가는 것이 이 계산의 가장 조용한 실패다.
# ⚠️ 발화 시각을 **사용자 타임존의 날짜로 접어** 비교한다(`u.created_at at time zone $3`) — UTC 로
# 비교하면 KST 새벽 발화가 앞 주로 밀린다. 그 타임존은 호출자가 `users.timezone` 에서 읽어 넘긴다.
_WEEK_FACTS_SQL = f"""
with occ as (
      select eo.pattern_id
        from error_occurrences eo
        join utterances u on u.id = eo.utterance_id
        join error_patterns p on p.id = eo.pattern_id
       where p.user_id = $1
         and (u.created_at at time zone $3)::date >= $2
         and (u.created_at at time zone $3)::date < $2 + 7
),
agg as (
      select pattern_id, count(*) as occurrences
        from occ
       group by pattern_id
),
ranked as (
      -- ⚠️ 동수는 `pattern_key` 로 가른다 — 없으면 순서가 실행마다 흔들려 화면이 이유 없이
      -- 달라진다(일일 요약의 `ranked` 가 같은 규약을 쓴다).
      select p.category, p.pattern_key, p.target_form, agg.occurrences
        from agg
        join error_patterns p on p.id = agg.pattern_id
       order by agg.occurrences desc, p.pattern_key
       limit {TOP_PATTERN_LIMIT}
)
select (select count(*)
          from learning_sessions s
         where s.user_id = $1
           and (s.started_at at time zone $3)::date >= $2
           and (s.started_at at time zone $3)::date < $2 + 7) as session_count,
       (select count(*) from occ) as occurrence_count,
       (select count(*) from agg) as pattern_count,
       coalesce((select jsonb_agg(jsonb_build_object(
                          'category', category,
                          'pattern_key', pattern_key,
                          'target_form', target_form,
                          'occurrences', occurrences)
                        order by occurrences desc, pattern_key)
                   from ranked), '[]'::jsonb) as top_patterns
"""

_TIMEZONE_SQL = "select timezone from users where id = $1"


async def load_week_facts(conn: asyncpg.Connection, user_id: UUID, week_start: date) -> WeekFacts:
    """그 주의 사실. 오류가 0건이어도 **값을 준다** — 0 은 정상이고 부재가 아니다.

    ⛔ **`None` 을 돌려주지 않는다.** 「그 주에 아무 일도 없었다」는 리포트가 담을 사실이고, 그것을
    부재로 표현하면 호출자가 「아직 계산 안 됨」과 구별할 수 없다 — 그 구별은 `computed_at` 이
    갖는다.
    """
    timezone = await conn.fetchval(_TIMEZONE_SQL, user_id)
    if timezone is None:
        raise LookupError(f"user {user_id} not found — 주간 사실을 읽을 수 없다")

    row = await conn.fetchrow(_WEEK_FACTS_SQL, user_id, week_start, timezone)
    assert row is not None  # 집계 조회는 항상 1행이다 (모든 열이 스칼라 부질의다)

    # ⚠️ **asyncpg 가 jsonb 를 문자열로 준다** — `TASK-62` 가 이 자리에서 API 가 총평을 한 번도
    # 싣지 못한 결함을 겪었다. 그래서 **모양의 소유자인 이 함수가** 변환을 흡수한다: 호출자마다
    # `json.loads` 를 적으면 한 곳이 반드시 빠뜨린다.
    raw = row["top_patterns"]
    patterns = json.loads(raw) if isinstance(raw, str) else raw
    return WeekFacts(
        week_start=week_start,
        session_count=row["session_count"],
        occurrence_count=row["occurrence_count"],
        pattern_count=row["pattern_count"],
        top_patterns=[TopPattern(**item) for item in patterns],
    )
