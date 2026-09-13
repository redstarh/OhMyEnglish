"""주간 학습 리포트 — 주 경계와 사실·판단의 적재 (`TASK-26`).

설계: `docs/design/2026-09-14-weekly-report-design.md`.

**이 모듈이 주 경계를 소유한다.** `daily_summary.py` 가 「오늘」의 정의를 한 곳에 모은 것과 같은
이유다 — 두 자리에서 각자 계산하면 경계가 갈리고, 갈린 것을 아무 것도 알려 주지 않는다.

⛔ **`current_date` 를 쓰지 않는다.** UTC 자정~09:00(KST) 구간에 그 값이 KST 날짜보다 하루 이르다는
것이 이 리포의 실측이고, R13-3 이 같은 것을 요구한다. 경계의 정본은 **`users.timezone` 컬럼**이다.
"""

from __future__ import annotations

from datetime import date
from uuid import UUID

import asyncpg

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
