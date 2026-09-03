#!/usr/bin/env python3
"""006 이전에 쌓인 패턴에 복습 상태를 채운다 (학습 코치 슬라이스 1 백필).

    cd app/backend && .venv/bin/python ../../scripts/backfill_review_state.py

**왜 필요한가.** `services.review.recompute`는 분석이 **그 발화에서 건드린** 패턴에만 돈다
(`services/analysis.py`의 `touched` 집합). 그래서 006을 적용해도 그 전에 쌓인 패턴은 **그
패턴이 다시 발생할 때까지** `next_review_at`을 받지 못하고, `load_due_reviews`가 0행을
돌려준다 — 슬라이스 1의 완료 판정("오늘 복습할 목록이 처음으로 값을 갖는다")이 실물에서
성립하지 않는다. 2026-09-04 dev DB 실측이 그 상태였다: 패턴 7행 · occurrence 17행 ·
예정일 **0건** · `review_tasks` **0행**.

**안전한 이유 3개.**

1. `recompute`는 `error_occurrences`·`pattern_attempts`의 **이력에서만** 계산한다 — 입력이
   바뀌지 않으므로 몇 번 돌려도 같은 결과다(멱등).
2. 쓰는 것은 파생값 3개(`next_review_at`·`mastery_score`·`review_tasks`)뿐이고 셋 다 언제든
   다시 계산된다. 원본 데이터(발화·occurrence·판정)는 건드리지 않는다.
3. 사용자별로 한 트랜잭션이다 — 중간에 죽으면 그 사용자는 통째로 롤백되고, 다시 돌리면 된다.

⚠️ **`migrate.py`에 넣지 않았다.** 그 스크립트는 앱 패키지에 의존하지 않는 것이 계약이라
(`asyncpg`만으로 돌아간다) `app.services.review`를 import할 수 없다. 마이그레이션 적용과
백필은 별개 단계로 두고, 006을 적용한 뒤 이 스크립트를 한 번 돌린다.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from uuid import UUID

import asyncpg
from db_utils import base_dsn

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "app" / "backend"

# `app` 패키지는 app/backend 아래에 있다 — 스크립트 파일 경로에서 계산해 넣는다(cwd 무관).
sys.path.insert(0, str(BACKEND_DIR))

from app.services.review import load_due_reviews, recompute_all  # noqa: E402

_USERS_SQL = "select id, display_name from users order by display_name"


async def _backfill_user(conn: asyncpg.Connection, user_id: UUID, label: str) -> None:
    async with conn.transaction():
        touched = await recompute_all(conn, user_id)
    due = await load_due_reviews(conn, user_id)
    print(f"  {label} ({user_id}): 패턴 {touched}건 재계산 → 오늘 복습할 목록 {len(due)}건")
    for review in due[:5]:
        print(
            f"      · {review.pattern_key} ({review.category}) "
            f"예정 {review.next_review_at.isoformat()}"
        )
    if len(due) > 5:
        print(f"      · … 그리고 {len(due) - 5}건 더")


async def main() -> int:
    conn = await asyncpg.connect(dsn=base_dsn())
    try:
        users = await conn.fetch(_USERS_SQL)
        if not users:
            print("사용자가 없다 — 백필할 것이 없다.")
            return 0
        print(f"[백필] 사용자 {len(users)}명")
        for record in users:
            await _backfill_user(conn, record["id"], record["display_name"])
    finally:
        await conn.close()
    print("\n완료. 이 스크립트는 멱등이므로 다시 돌려도 같은 결과다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
