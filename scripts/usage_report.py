#!/usr/bin/env python3
"""`llm_calls` 를 읽어 최근 사용량을 출력한다 (`TASK-126`).

    cd app/backend && .venv/bin/python ../../scripts/usage_report.py [--days 7]

**이 스크립트가 존재하는 이유**: 표를 만들고 읽는 쪽이 없는 상태를 만들지 않는다는 이 리포의 규약
(012 머리말 — *"소비자 없이 이 파일만 적용하지 않는다"*). 화면·API 를 붙일지는 아직 정하지 않았고,
그 결정을 기다리는 동안에도 **비용을 볼 수단**은 있어야 한다.

⛔ **금액을 계산하지 않는다** (`TASK-126` AC#4) — 단가는 모델·리전·시점에 따라 바뀌고 그 값을 어디에
둘지가 아직 결정되지 않았다. 여기서 곱하면 그 결정을 코드가 대신 내려 버린다.

⛔ **날짜를 이 스크립트가 만들지 않는다** — `load_usage_summary` 가 `users.timezone` 을 읽어 정한다
(전역 시각 규약 3항). 이 파일은 출력만 한다.

⚠️ `app.backend` 패키지를 import 하므로 그 venv 로 돌린다 — `scripts/migrate.py` 와 달리 독립이
아니다. 그 대가를 받아들인 이유: 집계 SQL 을 두 벌 유지하면 한쪽이 조용히 낡는다.
"""

from __future__ import annotations

import argparse
import asyncio
from uuid import UUID

from app.db import close_pool, pool
from app.services.usage import load_usage_summary

# 단일 사용자 로컬 도구다 — `api/ws.py` 의 `FIXED_USER_ID` 와 같은 값이고 같은 근거다.
# ⚠️ 여기서 쓰는 것은 **날짜 경계**뿐이다(`llm_calls` 에는 `user_id` 가 없다).
FIXED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

_HEADER = f"{'날짜':<12} {'갈래':<9} {'호출':>5} {'입력':>9} {'출력':>9}  분해(speech/text)"


def _split(speech: int | None, text: int | None) -> str:
    """분해가 없으면 `-` 로 낸다 — ⛔ 0 으로 적으면 「분해가 0」과 구분되지 않는다."""
    if speech is None and text is None:
        return "-"
    return f"{speech if speech is not None else '-'}/{text if text is not None else '-'}"


async def main(days: int) -> None:
    conn_pool = await pool()
    async with conn_pool.acquire() as conn:
        rollups = await load_usage_summary(conn, FIXED_USER_ID, days=days)
    await close_pool()

    if not rollups:
        print(f"최근 {days}일에 기록된 LLM 호출이 없다.")
        return

    print(_HEADER)
    print("-" * len(_HEADER))
    for row in rollups:
        print(
            f"{row.day.isoformat():<12} {row.purpose:<9} {row.calls:>5} "
            f"{row.input_tokens:>9,} {row.output_tokens:>9,}  "
            f"입력 {_split(row.input_speech_tokens, row.input_text_tokens)} · "
            f"출력 {_split(row.output_speech_tokens, row.output_text_tokens)}"
        )
    print("-" * len(_HEADER))
    print(
        f"합계: 호출 {sum(row.calls for row in rollups)}건 · "
        f"입력 {sum(row.input_tokens for row in rollups):,} 토큰 · "
        f"출력 {sum(row.output_tokens for row in rollups):,} 토큰"
    )
    print("⛔ 금액은 내지 않는다 — 단가의 자리가 아직 정해지지 않았다(TASK-126 AC#4).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="최근 LLM 사용량 (llm_calls)")
    parser.add_argument("--days", type=int, default=7, help="오늘을 포함한 일수 (기본 7)")
    asyncio.run(main(parser.parse_args().days))
