"""`GET /api/sessions/{id}/results` — 세션 결과 조회 엔드포인트 (설계서 §5.5, R1~R3).

라우터는 판정 로직을 갖지 않는다 — `services.results.get_session_result`가
R2 우선순위를 전부 결정하고, 여기서는 그 결과를 HTTP로 옮기기만 한다:

* 세션이 없으면(`None`) `404`.
* `SessionResult.corrections`가 `None`이면 응답 JSON에 `corrections` 키
  **자체를 넣지 않는다**(생략 — `null`도 아니다). `analyzing`/`connection_failed`/
  `no_utterances`에서 교정을 조용히 노출하지 않기 위한 계약이 API 응답 shape까지
  그대로 이어진다(§5.5 "잠정 노출 금지").
"""

from __future__ import annotations

from uuid import UUID

import asyncpg
from fastapi import APIRouter, HTTPException, Request

from app.services.results import Correction, SessionResult, get_session_result

router = APIRouter(prefix="/api/sessions", tags=["results"])


def _correction_payload(correction: Correction) -> dict[str, object]:
    return {
        "pattern_key": correction.pattern_key,
        "category": correction.category,
        "original_span": correction.original_span,
        "correction": correction.correction,
        "target_form": correction.target_form,
        "occurrences": correction.occurrences,
    }


def _result_payload(result: SessionResult) -> dict[str, object]:
    payload: dict[str, object] = {
        "status": result.status,
        "partial_failure": result.partial_failure,
    }
    if result.corrections is not None:
        payload["corrections"] = [_correction_payload(item) for item in result.corrections]
    return payload


@router.get("/{session_id}/results")
async def get_results(session_id: UUID, request: Request) -> dict[str, object]:
    pool: asyncpg.Pool = request.app.state.db_pool
    async with pool.acquire() as conn:
        result = await get_session_result(conn, session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="session not found")
    return _result_payload(result)
