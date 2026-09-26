"""튜터 발화 번역의 HTTP 표면 (`TASK-275`).

⚠️ **`POST` 인 이유**: 첫 요청이 번역을 «만들어 저장»한다 — 부수 효과가 있는 요청을 `GET` 으로 두면
미리 가져오기·재시도가 돈을 쓴다.
⚠️ 판정은 서비스가 하고 여기서는 HTTP 로 옮기기만 한다(`api/vocab.py` 와 같은 규약).
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request

from app.services.translation import UtteranceNotFoundError, translate_utterance
from app.workers.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["translation"])


@router.post("/{session_id}/utterances/{sequence_no}/translation")
async def post_utterance_translation(
    session_id: UUID, sequence_no: int, request: Request
) -> dict[str, object]:
    """발화 하나의 한국어 번역. `translation` 이 `None` 이면 **번역을 얻지 못했다**는 뜻이다.

    ⛔ 모델 실패를 500 으로 새어 나가게 두지 않는다 — 번역 하나를 못 얻은 것으로 화면이 깨지면
    학습이 멈춘다. 자격증명 없이 띄운 서버는 503 이다(`api/vocab.py` 의 `TASK-197` 판단과 같다).
    """
    claude: ClaudeClient | None = request.app.state.claude
    if claude is None:
        raise HTTPException(status_code=503, detail="번역을 쓸 수 없다")
    try:
        translation = await translate_utterance(
            request.app.state.db_pool, claude, session_id=session_id, sequence_no=sequence_no
        )
    except UtteranceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="발화를 찾을 수 없다") from exc
    except Exception:
        logger.exception("발화 번역이 실패해 빈 번역을 돌려준다 (%s#%s)", session_id, sequence_no)
        return {"translation": None}
    return {"translation": translation}
