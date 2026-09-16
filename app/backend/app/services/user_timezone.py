"""사용자 타임존의 **조회 정본** (`TASK-146` · 사용자 결정 2026-09-17).

⛔ **이 모듈이 있는 이유는 중복이 아니라 「경계의 정본」이다.** 같은 SQL 과 그 뒤의 널 검사가
`chronic`·`daily_summary`·`scenario_progress`·`usage`·`weekly_report` 다섯 파일에 **바이트 단위로
같게** 있었다. 다섯이 각자 들고 있으면 「없는 사용자를 어떻게 대하는가」가 다섯 곳에서 갈릴 수 있고,
그 갈림은 아무것도 알려 주지 않는다.

⚠️ **오류 문면이 하나로 통일됐다 — 그것이 이 합침의 대가이고 사용자가 알고 골랐다.** 이전 문면은
파일마다 달랐다(`no timezone source of truth` · `주간 사실을 읽을 수 없다` · `주 경계를 구할 수
없다`). 문면으로 호출부를 가르던 자리가 있으면 그 자리가 깨진다 — 지금은 없다: 테스트가
`LookupError` 를 부분 매치(`match="timezone"`)로만 잰다(2026-09-17 직접 확인).

⛔ **조용히 UTC 로 떨어지지 않는다.** 타임존의 정본은 `users.timezone` 컬럼이고 그 값이 없으면
「오늘」·「이번 주」의 경계를 구할 수 없다 — 폴백을 두면 날짜가 하루씩 밀린 집계가 조용히 쌓인다.
그래서 `LookupError` 를 올려 호출자가 그 사실을 마주하게 한다.

⚠️ **`plan_input.py` 는 이 모듈을 쓰지 않는다** — 그쪽 SQL 은 `current_level` 까지 함께 읽으므로
같은 조회가 아니다. 억지로 합치면 왕복이 하나 늘어난다.
"""

from __future__ import annotations

from uuid import UUID

import asyncpg

_TIMEZONE_SQL = "select timezone from users where id = $1"


async def timezone_of(conn: asyncpg.Connection, user_id: UUID) -> str:
    """이 사용자의 타임존. 사용자가 없으면 `LookupError`.

    호출자가 이미 타임존을 알고 있으면 **다시 부르지 않고 그 값을 넘긴다** — 한 요청에서 두 조회가
    각자 부르면 같은 왕복이 두 번 나간다(`api/daily.py` 가 그 형태를 고친 자리다).
    """
    timezone = await conn.fetchval(_TIMEZONE_SQL, user_id)
    if timezone is None:
        raise LookupError(f"user {user_id} not found — no timezone source of truth")
    return timezone
