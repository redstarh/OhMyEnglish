"""어느 대화 상황을 몇 번 했는지 읽는다 (`TASK-102` AC#4 · 「학습 시나리오 완료 현황을 보고」).

**왜 이 모듈이 있는가**: `TASK-4` 가 `learning_sessions.scenario_pick`(016)에 「신규로 골랐는지
반복으로 골랐는지」를 **쓰기 시작했지만 읽는 쪽이 없었다.** 표를 만들고 읽는 쪽이 없는 상태를
만들지 않는다는 이 리포의 규약(012 머리말 · `usage.py` 가 같은 근거로 만들어졌다)이 이 모듈을
요구한다.

⛔ **미학습 상황도 낸다.** 「완료 현황」이므로 0회인 상황이 목록에서 빠지면 **무엇이 남았는지**를
알 수 없다 — `left join` 이 그것 때문이고 `inner join` 으로 바꾸면 이 모듈의 목적이 사라진다.

⛔ **날짜의 정본은 `users.timezone` 컬럼이다**(전역 시각 규약 3항). `current_date` 를 쓰지 않는다 —
UTC 자정~09:00(KST) 구간에서 하루 어긋난다. 사용자가 없으면 **조용히 기본값을 쓰지 않고 실패한다**
(`usage.load_usage_summary` 와 같은 규약).

⚠️ **정렬이 `created_at` 인 것은 의도다** — 그 컬럼이 시드 배열의 삽입 순서이고 배치 규칙이 신규를
고르는 순서다(결정 76). ⇒ 이 목록의 순서가 **다음에 나올 순서**를 함께 보여 준다.
⛔ 제목순으로 정렬하지 않는다. 그러면 그 정보가 사라진다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

import asyncpg

# ⛔ 타임존의 정본은 이 컬럼 하나다. `usage.py`·`recordings.py` 도 같은 한 줄을 쓴다 — 공유
# 헬퍼를 만들지 않은 것은 이 리포의 기존 관행이고, 복제되는 것은 **SQL 한 줄뿐**이다.
_TIMEZONE_SQL = "select timezone from users where id = $1"

# `count(ls.id)` 를 쓰는 이유: `left join` 이라 매칭이 없으면 `ls.*` 가 null 이고 `count(*)` 는
# **1 을 낸다**(행이 하나 나오므로). `count(ls.id)` 만 0 이 된다.
# `filter (where ls.scenario_pick = 'new')` 는 null 을 세지 않는다 — 016 이전 세션에는 그 값이
# 없고 그것을 신규로 세면 「신규였다」를 지어내는 것이 된다.
_PROGRESS_SQL = """
select s.id,
       s.category,
       s.level,
       s.title,
       count(ls.id) as sessions,
       count(ls.id) filter (where ls.scenario_pick = 'new') as new_picks,
       max(ls.started_at at time zone $2)::date as last_studied_on
  from learning_scenarios s
  left join learning_sessions ls
         on ls.scenario_id = s.id
        and ls.user_id = $1
 group by s.id, s.category, s.level, s.title, s.created_at
 order by s.created_at, s.id
"""


@dataclass(frozen=True, slots=True)
class ScenarioProgress:
    """상황 하나의 학습 현황. `sessions` 가 0 이면 아직 안 한 상황이다."""

    scenario_id: UUID
    category: str
    level: str
    title: str
    sessions: int
    new_picks: int
    last_studied_on: date | None


async def load_scenario_progress(conn: asyncpg.Connection, user_id: UUID) -> list[ScenarioProgress]:
    """상황 전체의 학습 현황을 시드 배열 순서로 낸다.

    `sessions` 는 그 상황으로 열린 세션 수이고 `new_picks` 는 그중 **배치 규칙이 신규로 고른**
    횟수다. 둘은 다른 정보다 — 같은 상황이 반복으로 여러 번 나올 수 있다.

    `last_studied_on` 은 **사용자 타임존의 달력 날짜**다. 한 번도 안 했으면 `None`.
    """
    timezone = await conn.fetchval(_TIMEZONE_SQL, user_id)
    if timezone is None:
        raise LookupError(f"user {user_id} not found — no timezone source of truth")

    rows = await conn.fetch(_PROGRESS_SQL, user_id, timezone)
    return [
        ScenarioProgress(
            scenario_id=row["id"],
            category=row["category"],
            level=row["level"],
            title=row["title"],
            sessions=row["sessions"],
            new_picks=row["new_picks"],
            last_studied_on=row["last_studied_on"],
        )
        for row in rows
    ]
