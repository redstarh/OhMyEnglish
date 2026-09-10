"""일일 오류 요약 — 그날 무엇을 분석했는지의 스냅샷 (PRD §13).

설계의 정본은 `docs/design/2026-09-11-daily-error-summary-design.md`다. 여기서는 그 문서가 정한
것 가운데 **이 코드를 읽을 때 알아야 하는 것**만 적는다.

**왜 표에 담는가** — `chronic.py`는 같은 종류의 값을 조회 시 계산으로 두었고 그 판단은 지금도
유효하다(설계서 §6.1: 롤업 표를 두면 갱신 시점·신선도 관리만 늘어난다). 이 요약이 갈라지는
이유는 두 자리에서 **조회 시 계산의 결과가 시간이 지나면 달라지기** 때문이다:
`analysis.py`의 `_UPSERT_PATTERN_SQL`이 패턴의 `target_form`을 가장 최근 분석 값으로 갱신하고,
`_DELETE_OCCURRENCES_SQL`이 재분석에서 그 발화의 발생 행을 지우고 다시 넣는다. 즉 나중에 다시
세면 학습자가 그날 실제로 받은 교정과 다른 값이 나온다.

**날짜의 정본은 `users.timezone` 컬럼이다.** `current_date`를 쓰지 않는다 — 서버 세션 타임존의
날짜라 한국 시각 자정부터 오전 9시까지 하루 이른 값을 낸다(전역 시각 규약의 실측 함정).
사용자가 없으면 그 정본이 없으므로 조용히 UTC로 떨어지지 않고 `LookupError`를 올린다.
`load_chronic_metrics`가 같은 판단을 이미 한다.

**집계의 앵커는 발화 시각(`utterances.created_at`)이다.** `error_occurrences.created_at`은 분석
저장 시각이라 새벽에 돌아간 분석이 발화를 다음 날짜로 밀어 넣는다. `chronic.py`·`review.py`가
이미 같은 앵커를 쓴다.

**쓰기는 한 자리뿐이다** — `analysis.py`의 `_replace_occurrences`. 발생 행이 바뀌는 유일한
자리이므로 스냅샷이 원본과 어긋난 채 남는 경로가 없다. 그리고 `+1`로 누적하지 않고 그 날짜를
다시 세므로 재시도가 값을 부풀리지 않는다(`error_patterns.frequency`와 같은 규약).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import asyncpg

# `patterns` 배열의 상한. 단일 사용자 규모에서 하루에 20종을 넘길 일이 없지만 jsonb가 무한히
# 자라는 길을 열어 두지 않는다. 잘려도 두 개수 컬럼은 **전체 수**를 유지한다(설계서 §3.3).
PATTERN_LIMIT = 20

_TIMEZONE_SQL = "select timezone from users where id = $1"

# 그 발화의 날짜 1건을 다시 세어 upsert한다. 한 문장인 이유: 세는 것과 쓰는 것이 갈리면 그
# 사이에 다른 트랜잭션이 발생 행을 바꿀 수 있다.
#
# 발화가 없으면(`anchor`가 0행) 뒤의 `from anchor, totals`가 0행이 되어 **아무 것도 쓰지 않는다** —
# 재분석 도중 발화가 사라진 경우에 이 집계 때문에 저장 트랜잭션을 실패시키지 않는다.
#
# `jsonb_agg`에 `order by`를 **직접** 건다. `ranked`의 `order by`는 상한을 고르기 위한 것이고,
# CTE의 행 순서가 집계에 그대로 전달된다는 보장은 없다.
_UPSERT_SQL = f"""
with anchor as (
      select (u.created_at at time zone $3)::date as summary_date
        from utterances u
       where u.id = $2
),
occ as (
      select eo.id as occurrence_id,
             eo.pattern_id,
             eo.original_span,
             eo.correction,
             eo.explanation,
             u.created_at as utterance_created_at
        from error_occurrences eo
        join utterances u on u.id = eo.utterance_id
        join error_patterns p on p.id = eo.pattern_id
       where p.user_id = $1
         and (u.created_at at time zone $3)::date = (select summary_date from anchor)
),
agg as (
      select pattern_id, count(*) as occurrences
        from occ
       group by pattern_id
),
representative as (
      -- 예시는 그날 **가장 이른** 발화다 — 학습자가 하루를 되짚을 때 처음 틀린 자리가 기준이다.
      -- 같은 트랜잭션에서 들어간 두 발생이 시각까지 같을 수 있으므로 `occurrence_id`로 고정한다.
      select distinct on (pattern_id) pattern_id, original_span, correction, explanation
        from occ
       order by pattern_id, utterance_created_at, occurrence_id
),
ranked as (
      select p.pattern_key,
             p.category,
             p.target_form,
             agg.occurrences,
             rep.original_span,
             rep.correction,
             rep.explanation
        from agg
        join error_patterns p on p.id = agg.pattern_id
        join representative rep on rep.pattern_id = agg.pattern_id
       order by agg.occurrences desc, p.pattern_key
       limit {PATTERN_LIMIT}
),
totals as (
      select (select count(*) from occ) as occurrence_count,
             (select count(*) from agg) as pattern_count
)
insert into daily_error_summary
       (user_id, summary_date, timezone, occurrence_count, pattern_count, patterns, computed_at)
select $1,
       anchor.summary_date,
       $3,
       totals.occurrence_count,
       totals.pattern_count,
       coalesce((select jsonb_agg(jsonb_build_object(
                          'pattern_key', pattern_key,
                          'category', category,
                          'target_form', target_form,
                          'occurrences', occurrences,
                          'example', jsonb_build_object(
                                       'original_span', original_span,
                                       'correction', correction,
                                       'reason', explanation))
                        order by occurrences desc, pattern_key)
                   from ranked), '[]'::jsonb),
       now()
  from anchor, totals
on conflict (user_id, summary_date) do update
   set timezone = excluded.timezone,
       occurrence_count = excluded.occurrence_count,
       pattern_count = excluded.pattern_count,
       patterns = excluded.patterns,
       computed_at = excluded.computed_at
"""

_LOAD_SQL = """
select summary_date, timezone, occurrence_count, pattern_count, patterns, computed_at
  from daily_error_summary
 where user_id = $1
   and summary_date = $2
"""


@dataclass(frozen=True, slots=True)
class DailyExample:
    """그날 그 패턴의 발생 1건. 전부를 담으면 이 표가 `error_occurrences`의 사본이 된다."""

    original_span: str
    correction: str
    reason: str


@dataclass(frozen=True, slots=True)
class DailyPattern:
    """패턴 1종의 그날 집계. 판정(만성 여부·개선 여부)은 담지 않는다 — PRD R13-5."""

    pattern_key: str
    category: str
    target_form: str
    occurrences: int
    example: DailyExample


@dataclass(frozen=True, slots=True)
class DailySummary:
    """달력 날짜 1일의 요약.

    `computed_at`이 `None`인 것은 **그날 요약 행이 없다**는 뜻이다 — 「분석이 돌고 오류 0건」과
    「그날 학습이 없었다」를 구별하는 유일한 신호다(PRD R13-7). 두 개수가 0인 것만으로는
    갈리지 않는다.
    """

    summary_date: date
    timezone: str
    occurrence_count: int
    pattern_count: int
    patterns: list[DailyPattern]
    computed_at: datetime | None


async def _timezone_of(conn: asyncpg.Connection, user_id: UUID) -> str:
    timezone = await conn.fetchval(_TIMEZONE_SQL, user_id)
    if timezone is None:
        raise LookupError(f"user {user_id} not found — no timezone source of truth")
    return timezone


def _parse_patterns(raw: str | None) -> list[DailyPattern]:
    if not raw:
        return []
    return [
        DailyPattern(
            pattern_key=item["pattern_key"],
            category=item["category"],
            target_form=item["target_form"],
            occurrences=item["occurrences"],
            example=DailyExample(
                original_span=item["example"]["original_span"],
                correction=item["example"]["correction"],
                reason=item["example"]["reason"],
            ),
        )
        for item in json.loads(raw)
    ]


async def refresh_summary_for_utterance(
    conn: asyncpg.Connection, user_id: UUID, utterance_id: UUID
) -> None:
    """그 발화가 속한 날짜의 요약을 다시 계산해 저장한다.

    갱신 범위는 **그 날짜 1건**이다 — 다른 날짜를 건드리지 않는다. 발화가 이미 사라졌으면
    아무 것도 쓰지 않는다.

    호출자의 트랜잭션 안에서 돈다(`_replace_occurrences`). 여기서 트랜잭션을 열지 않는 이유:
    발생 행의 교체와 이 스냅샷이 갈라져 커밋되면 요약이 원본과 어긋난 채 남는다.
    """
    await conn.execute(_UPSERT_SQL, user_id, utterance_id, await _timezone_of(conn, user_id))


async def load_daily_summary(
    conn: asyncpg.Connection, user_id: UUID, *, now: datetime | None = None
) -> DailySummary:
    """이 학습자의 **오늘**(사용자 타임존) 요약. 행이 없으면 두 개수가 0인 요약을 돌려준다.

    `now`를 인자로 받는 이유는 테스트가 날짜 경계를 지목할 수 있어야 하기 때문이다.
    naive datetime을 거부한다 — 조용히 바인딩되면 서버 오프셋만큼 날짜가 밀린다
    (`services/recordings.py`와 같은 규약).
    """
    resolved_now = now if now is not None else datetime.now(ZoneInfo("UTC"))
    if resolved_now.tzinfo is None:
        raise ValueError("`now` must be timezone-aware (naive datetime is not allowed)")

    timezone = await _timezone_of(conn, user_id)
    today = resolved_now.astimezone(ZoneInfo(timezone)).date()

    record = await conn.fetchrow(_LOAD_SQL, user_id, today)
    if record is None:
        return DailySummary(
            summary_date=today,
            timezone=timezone,
            occurrence_count=0,
            pattern_count=0,
            patterns=[],
            computed_at=None,
        )
    return DailySummary(
        summary_date=record["summary_date"],
        timezone=record["timezone"],
        occurrence_count=record["occurrence_count"],
        pattern_count=record["pattern_count"],
        patterns=_parse_patterns(record["patterns"]),
        computed_at=record["computed_at"],
    )
