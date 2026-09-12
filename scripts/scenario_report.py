#!/usr/bin/env python3
"""대화 상황의 학습 현황을 출력한다 (`TASK-102` AC#4 · 「학습 시나리오 완료 현황을 보고」).

    cd app/backend && .venv/bin/python ../../scripts/scenario_report.py [--only-unstudied]

**이 스크립트가 존재하는 이유**: `TASK-4` 가 `learning_sessions.scenario_pick`(016)에 쓰기
시작했는데 읽는 쪽이 없었다. 표를 만들고 읽는 쪽이 없는 상태를 만들지 않는다는 이 리포의
규약이고(`usage_report.py` 가 같은 근거로 만들어졌다), 화면·API 는 아직 정해지지 않았다.

⚠️ **줄 순서가 「다음에 나올 순서」다** — 집계가 `learning_scenarios.created_at` 으로 정렬하고 그
컬럼이 시드 배열의 삽입 순서이며 배치 규칙이 신규를 그 순서로 집는다(결정 76). ⛔ 여기서 다시
정렬하지 않는다.

⛔ **날짜를 이 스크립트가 만들지 않는다** — `load_scenario_progress` 가 `users.timezone` 을 읽어
정한다(전역 시각 규약 3항). 이 파일은 출력만 한다.

⚠️ `app` 패키지를 import 하므로 그 venv 로 돌린다 — `scripts/migrate.py` 와 달리 독립이 아니다.
그 대가를 받아들인 이유: 집계 SQL 을 두 벌 유지하면 한쪽이 조용히 낡는다.
"""

from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from app.db import close_pool, pool
from app.services.scenario_progress import ScenarioProgress, load_scenario_progress

# 단일 사용자 로컬 도구다 — `api/ws.py` 의 `FIXED_USER_ID` 와 같은 값이고 같은 근거다.
FIXED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

_HEADER = f"{'#':>3} {'계열':<11} {'횟수':>4} {'신규':>4} {'마지막 학습':<12} 제목"


def _row(index: int, item: ScenarioProgress) -> str:
    # ⛔ 미학습을 `0`·`-` 로 뭉개지 않는다 — 「한 번도 안 함」과 「했는데 날짜를 모름」은 다르다.
    last = item.last_studied_on.isoformat() if item.last_studied_on else "안 함"
    return (
        f"{index:>3} {item.category:<11} {item.sessions:>4} {item.new_picks:>4} "
        f"{last:<12} {item.title}"
    )


def _summary(items: list[ScenarioProgress]) -> str:
    studied = [item for item in items if item.sessions > 0]
    unstudied = [item for item in items if item.sessions == 0]
    line = f"상황 {len(items)}개 중 {len(studied)}개 학습함 · {len(unstudied)}개 남음"
    if unstudied:
        # 배열 순서가 노출 순서이므로 남은 것의 첫 줄이 **다음에 나올 신규 후보**다.
        line += f"\n다음에 나올 신규 후보: {unstudied[0].title}"
    return line


async def main(*, only_unstudied: bool) -> None:
    conn_pool = await pool()
    async with conn_pool.acquire() as conn:
        items = await load_scenario_progress(conn, FIXED_USER_ID)
    await close_pool()

    if not items:
        print("상황이 0행이다 — 시드가 적용되지 않았다 (scripts/migrate.py 의 SEED_SCENARIOS)")
        return

    shown = [item for item in items if item.sessions == 0] if only_unstudied else items
    print(_HEADER)
    print("-" * len(_HEADER))
    for index, item in enumerate(items, start=1):
        if item in shown:
            print(_row(index, item))
    print()
    print(_summary(items))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="대화 상황 학습 현황")
    parser.add_argument(
        "--only-unstudied",
        action="store_true",
        help="아직 안 한 상황만 낸다 (번호는 전체 순서를 유지한다)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    asyncio.run(main(only_unstudied=args.only_unstudied))
