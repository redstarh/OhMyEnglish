"""조회 엔드포인트 — `GET /api/daily-summary` (PRD §13 R13-4 · `TASK-1`).

`results.py`와 같은 규약을 따른다: 라우터는 판정을 갖지 않고 `services.daily_summary`가 정한
것을 HTTP 로 옮기기만 한다. 그래서 이 파일에 날짜 계산도 타임존 조회도 없다 — 그것을 여기서
다시 쓰면 「오늘」의 정의가 둘로 갈라진다.

세 가지가 이 응답 모양의 이유다.

* **요약이 없어도 404 가 아니다.** 그날 학습이 없었던 것은 오류가 아니고 화면은 그 자리를 비우기만
  한다 — `next-plan`이 계획 부재에 `null`을 내리는 것과 같은 판단이다.
* **`analyzed`가 그 둘을 가른다**(R13-7). 「분석이 돌고 오류 0건」과 「그날 학습이 없었다」는 두
  개수만으로는 구별되지 않는다. `results.py`의 `awaiting_analysis`와 같은 모양으로 **항상 싣는다** —
  화면이 키 존재를 갈라 읽지 않게 하는 것이 목적이다.
* **`timezone`을 내려주지 않는다.** `summary_date`가 이미 학습자 타임존의 달력 날짜이고, 화면이
  그 값으로 다시 변환할 일이 없다. 저장은 감사를 위해 그 값을 갖는다(마이그레이션 012).

라우터가 조회 실패를 삼키지 않는다 — `results.py`와 같은 규약이다. 삼키면 화면 결과는 같은데
장애만 조용해진다.
"""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Request

from app.api.ws import FIXED_USER_ID
from app.services.daily_summary import (
    DailyCompletion,
    DailyPattern,
    DailySummary,
    load_daily_completion,
    load_daily_summary,
)

router = APIRouter(prefix="/api", tags=["daily"])


def _pattern_payload(item: DailyPattern) -> dict[str, object]:
    return {
        "pattern_key": item.pattern_key,
        "category": item.category,
        "target_form": item.target_form,
        "occurrences": item.occurrences,
        "example": {
            "original_span": item.example.original_span,
            "correction": item.example.correction,
            "reason": item.example.reason,
        },
    }


def _summary_payload(summary: DailySummary, completion: DailyCompletion) -> dict[str, object]:
    return {
        "summary_date": summary.summary_date.isoformat(),
        # 행이 있으면 그날 분석이 돌았다 — `computed_at`이 그 사실의 정본이다.
        "analyzed": summary.computed_at is not None,
        "occurrence_count": summary.occurrence_count,
        "pattern_count": summary.pattern_count,
        "patterns": [_pattern_payload(item) for item in summary.patterns],
        # `TASK-2` · PRD §14 — 「오늘 학습을 마쳤는지」. 두 키를 **항상** 싣는다(위 `analyzed` 와
        # 같은 규약). 별 엔드포인트로 빼지 않는 이유는 설계서 §4 가 소유한다: 두 판독이 자정을
        # 걸쳐 갈릴 수 있고, 그러면 화면이 「오늘」을 두 날짜로 그린다.
        "completed_today": completion.completed_today,
        "completed_scenarios": completion.completed_scenarios,
    }


@router.get("/daily-summary")
async def get_daily_summary(request: Request) -> dict[str, object]:
    """이 학습자의 오늘(학습자 타임존) 오류 요약. 단일 사용자 로컬 도구라 사용자는 고정이다."""
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        # 한 커넥션에서 둘을 읽는다 — 두 조회가 «같은 오늘»을 봐야 한다.
        summary = await load_daily_summary(conn, FIXED_USER_ID)
        completion = await load_daily_completion(conn, FIXED_USER_ID)
    return _summary_payload(summary, completion)
