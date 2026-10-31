"""문법 코스의 진도·따라 하기 기록·이력 (`TASK-286`).

설계: `docs/design/2026-10-26-grammar-course-design.md` §4~§6.

⛔ **콘텐츠는 `models.course.load_course` 가 소유하고 이 모듈은 학습자 상태만 다룬다.** 단원·문장을
표에서 읽지 않으므로 시도 기록의 `sentence_key` 가 어느 Day·단원인지는 콘텐츠로 되짚는다.
⛔ **날짜는 학습자 시간대로 가른다** — `(created_at at time zone $tz)::date`. `current_date` 를 쓰면
UTC 자정~09:00 KST 사이의 시도가 전날 칸에 들어간다.
⛔ **전사는 연결을 잡지 않은 채 한다** — `services/readback.py` 와 같은 규약이다.
전사는 수 초~30초이고
그 안에서 사용량 기록이 풀에서 연결을 또 잡는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.audio_gateway.port import Transcriber
from app.models.course import Course, ProgressUpdate, sentence_key
from app.services.readback import WordVerdict, compare_readback

HEATMAP_DAYS = 16 * 7
RECENT_DATES = 7


@dataclass(frozen=True)
class DayProgress:
    day: int
    position_sec: Decimal
    unit: int
    sentence_index: int
    completed_count: int
    last_completed_at: str | None
    # 완료한 날의 학습자 시간대 달력 날짜(회차 b1 D1).
    # 화면이 UTC 시각을 잘라 날짜를 만들지 않게 한다.
    last_completed_date: date | None
    updated_at: str | None


@dataclass(frozen=True)
class RecentDate:
    local_date: date
    days: list[int]
    first_unit: int
    last_unit: int
    sentences: int
    attempts: int


@dataclass(frozen=True)
class Overview:
    cycle: int
    current_day: int
    progress: dict[int, DayProgress]
    heatmap: list[tuple[date, int]]
    recent: list[RecentDate]


@dataclass(frozen=True)
class AttemptResult:
    transcript: str
    words: list[WordVerdict]
    attempts: int


_PROGRESS_SQL = """
select day, position_sec, unit, sentence_index, completed_count,
       last_completed_at, updated_at,
       (last_completed_at at time zone $2)::date as last_completed_date
  from course_day_progress
 where user_id = $1
"""

_HEATMAP_SQL = """
with days as (
  select generate_series(
           (now() at time zone $2)::date - ($3::int - 1),
           (now() at time zone $2)::date,
           interval '1 day'
         )::date as local_date
)
select d.local_date, count(a.id)::int as attempts
  from days d
  left join course_attempts a
    on a.user_id = $1
   and (a.created_at at time zone $2)::date = d.local_date
 group by d.local_date
 order by d.local_date
"""

_RECENT_SQL = """
select (created_at at time zone $2)::date as local_date,
       array_agg(distinct sentence_key order by sentence_key) as keys,
       count(*)::int as attempts
  from course_attempts
 where user_id = $1
 group by 1
 order by 1 desc
 limit $3
"""

_SENTENCE_COUNTS_SQL = """
select sentence_key, count(*)::int as attempts
  from course_attempts
 where user_id = $1 and sentence_key = any($2::text[])
 group by sentence_key
"""

_SAVE_PROGRESS_SQL = """
insert into course_day_progress as p (user_id, day, position_sec, unit, sentence_index)
values ($1, $2, $3, $4, $5)
on conflict (user_id, day) do update
   set position_sec = excluded.position_sec,
       unit = excluded.unit,
       sentence_index = excluded.sentence_index,
       updated_at = now()
 where p.completed_count <= $6
"""

# 끝낸 Day 는 처음으로 되감고 완료 횟수를 하나 올린다 — 다음 회차가 그 Day 를 처음부터 듣는다.
_COMPLETE_DAY_SQL = """
insert into course_day_progress as p
       (user_id, day, position_sec, unit, sentence_index, completed_count, last_completed_at)
values ($1, $2, 0, $3, 0, 1, now())
on conflict (user_id, day) do update
   set position_sec = 0,
       unit = excluded.unit,
       sentence_index = 0,
       completed_count = p.completed_count + 1,
       last_completed_at = now(),
       updated_at = now()
"""

_INSERT_ATTEMPT_SQL = """
insert into course_attempts (user_id, sentence_key, transcript, words)
values ($1, $2, $3, $4::jsonb)
"""


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _unit_of_key(key: str) -> int:
    return int(key[1:4])


def _left_the_start(item: DayProgress, first_unit: int) -> bool:
    """처음 자리(0초 · 첫 단원 · 첫 문장)를 벗어났는가 — 목록 화면의 「진행 중」 문구와 같은 기준.

    ⛔ 저장 시각으로 가르지 않는다(회차 b4 D5) — 완료 뒤에도 화면의 주기·언마운트 저장이
    처음 자리를 다시 써서 `updated_at` 이 올라간다.
    """
    return item.position_sec > 0 or item.sentence_index > 0 or item.unit != first_unit


async def load_progress(
    conn: asyncpg.Connection, user_id: UUID, *, timezone: str
) -> dict[int, DayProgress]:
    rows = await conn.fetch(_PROGRESS_SQL, user_id, timezone)
    return {
        row["day"]: DayProgress(
            day=row["day"],
            position_sec=row["position_sec"],
            unit=row["unit"],
            sentence_index=row["sentence_index"],
            completed_count=row["completed_count"],
            last_completed_at=_iso(row["last_completed_at"]),
            last_completed_date=row["last_completed_date"],
            updated_at=_iso(row["updated_at"]),
        )
        for row in rows
    }


async def load_overview(
    conn: asyncpg.Connection, course: Course, user_id: UUID, *, timezone: str
) -> Overview:
    """목록 화면의 전부 — Day 진도 · 회차 · 날짜별 히트맵 · 최근 날짜 표."""
    progress = await load_progress(conn, user_id, timezone=timezone)
    counts = [
        progress[item.day].completed_count if item.day in progress else 0 for item in course.days
    ]
    # 회차 = 6편 모두 끝낸 횟수 + 1 (설계서 §4).
    cycle = min(counts) + 1
    # 진행 중인 Day = 이번 회차에서 아직 끝내지 않고 처음 자리를 벗어난 Day 가운데
    # 가장 최근에 손댄 것.
    # 없으면 첫 미완료 Day 다 — 6편을 다 끝낸 직후의 2회차는 Day 1 부터다(TASK-287).
    unfinished = [item for item, done in zip(course.days, counts, strict=True) if done < cycle]
    touched = [
        progress[item.day]
        for item in unfinished
        if item.day in progress and _left_the_start(progress[item.day], item.units[0].unit)
    ]
    current_day = (
        max(touched, key=lambda item: item.updated_at or "").day if touched else unfinished[0].day
    )

    heat_rows = await conn.fetch(_HEATMAP_SQL, user_id, timezone, HEATMAP_DAYS)
    unit_to_day = {unit.unit: day.day for day in course.days for unit in day.units}
    recent: list[RecentDate] = []
    for row in await conn.fetch(_RECENT_SQL, user_id, timezone, RECENT_DATES):
        units = sorted({_unit_of_key(key) for key in row["keys"]})
        recent.append(
            RecentDate(
                local_date=row["local_date"],
                days=sorted({unit_to_day[unit] for unit in units if unit in unit_to_day}),
                first_unit=units[0],
                last_unit=units[-1],
                sentences=len(row["keys"]),
                attempts=row["attempts"],
            )
        )
    return Overview(
        cycle=cycle,
        current_day=current_day,
        progress=progress,
        heatmap=[(row["local_date"], row["attempts"]) for row in heat_rows],
        recent=recent,
    )


async def load_sentence_counts(
    conn: asyncpg.Connection, user_id: UUID, keys: list[str]
) -> dict[str, int]:
    rows = await conn.fetch(_SENTENCE_COUNTS_SQL, user_id, keys)
    return {row["sentence_key"]: row["attempts"] for row in rows}


def day_sentence_keys(course: Course, day: int) -> list[str]:
    found = course.day(day)
    if found is None:
        return []
    return [
        sentence_key(unit.unit, index)
        for unit in found.units
        for index in range(len(unit.sentences))
    ]


async def save_progress(
    conn: asyncpg.Connection, course: Course, user_id: UUID, day: int, update: ProgressUpdate
) -> bool:
    """진도를 저장한다.

    Day 가 없거나 단원이 그 Day 에 속하지 않으면 `False` — 라우터가 404/422 로 옮긴다.
    """
    found = course.day(day)
    if found is None or all(unit.unit != update.unit for unit in found.units):
        return False
    if update.completed:
        await conn.execute(_COMPLETE_DAY_SQL, user_id, day, found.units[0].unit)
    else:
        await conn.execute(
            _SAVE_PROGRESS_SQL,
            user_id,
            day,
            # 실제 영상이 목차의 마지막 단원보다 조금 길 수 있어 거부하지 않고 Day 길이로 자른다.
            min(update.position_sec, Decimal(found.duration_sec)),
            update.unit,
            update.sentence_index,
            update.completed_count,
        )
    return True


async def record_attempt(
    pool: asyncpg.Pool,
    course: Course,
    user_id: UUID,
    key: str,
    pcm: bytes,
    *,
    transcribe: Transcriber,
) -> AttemptResult | None:
    """따라 하기 한 번을 전사해 원문과 견주고 기록한다. 없는 문장이면 `None`.

    ⚠️ 전사가 비어도 기록한다 — 학습자는 따라 했고 「못 알아들었다」는 다시 할 일이다(설계서 §4).
    """
    expected = course.sentence(key)
    if expected is None:
        return None
    transcript = (await transcribe(pcm)).strip()
    words = compare_readback(expected, transcript) if transcript else []
    payload = json.dumps([{"word": item.word, "verdict": item.verdict} for item in words])
    async with pool.acquire() as conn:
        await conn.execute(_INSERT_ATTEMPT_SQL, user_id, key, transcript, payload)
        counts = await load_sentence_counts(conn, user_id, [key])
    return AttemptResult(transcript=transcript, words=words, attempts=counts.get(key, 0))
