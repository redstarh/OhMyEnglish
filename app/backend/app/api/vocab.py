"""낱말 뜻 조회의 HTTP 표면 (`TASK-194` · 캡틴 결정 130).

⛔ **`/api/sessions` 아래에 넣지 않는다** — 낱말 뜻은 세션에 매인 것이 아니고 개인정보도 아니다.
`api/shadowing.py` 가 같은 판단을 적어 두었다: 세션 경로 아래에 두면 **없는 경계를 있는 것처럼**
보이게 하고, 세션마다 같은 질문을 다른 URL 로 부르게 된다.

⚠️ **`POST` 인 이유**: 낱말과 **문맥 문장**을 함께 보내야 한다(`services/vocab.py` 가 근거를 가진다).
문장이 URL 에 들어가면 길이 제한과 인코딩이 따라오고, 로그에 학습자의 문장이 경로로 남는다.
⛔ **그럼에도 서버는 아무것도 저장하지 않는다** — 결정 130 이 저장·캐시를 뺐다.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services.vocab import lookup_word
from app.workers.claude_client import ClaudeClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vocab", tags=["vocab"])


class VocabLookupRequest(BaseModel):
    """조회 요청.

    ⚠️ 길이 상한은 **모델 호출 비용의 상한**이다 — 문장 하나를 넘는 입력을 받지 않는다.
    """

    word: str = Field(min_length=1, max_length=80)
    sentence: str = Field(min_length=1, max_length=600)


class VocabLookupResponse(BaseModel):
    """뜻 한 줄. `meaning` 이 `None` 이면 **모델이 뜻을 주지 않았다**는 뜻이다.

    ⛔ **그것을 404 로 만들지 않는다** — 「없는 자원」이 아니라 「답을 못 얻었다」이고, 화면은 그
    둘에 다르게 반응해야 한다(전자는 조작 실수, 후자는 다시 눌러 볼 일이다).
    """

    meaning: str | None


@router.post("/lookup", response_model=VocabLookupResponse)
async def post_vocab_lookup(payload: VocabLookupRequest, request: Request) -> VocabLookupResponse:
    """낱말 뜻 한 줄을 돌려준다.

    **판정은 서비스가 하고 여기서는 HTTP 로 옮기기만 한다** — 이 리포의 다른 라우터와 같은 규약이다.
    `lookup_word` 의 `ValueError`(빈 낱말)는 400 으로 옮긴다 — 다만 `Field(min_length=1)` 이 먼저
    걸러내므로 그 갈래는 **방어의 둘째 겹**이다.

    ⛔ **모델 호출 실패를 500 으로 새어 나가게 두지 않는다** — 낱말 하나를 못 물은 것으로 화면이
    깨지면 학습이 멈춘다. `meaning=None` 으로 내보내고 화면이 「다시 눌러 보라」고 말한다.
    ⚠️ 그래서 **실패와 「뜻을 모른다」가 화면에서 같게 보인다** — 그 구분이 학습자에게 값을 주지
    않으므로 합쳤다(구분이 필요해지면 사유 코드를 더한다).
    """
    claude: ClaudeClient = request.app.state.claude
    try:
        meaning = await lookup_word(claude, word=payload.word, sentence=payload.sentence)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception:
        # ⛔ **삼키면서 기록을 남기지 않으면 왜 뜻이 안 왔는지 알 수 없다.** `H-Z` 대로 `exception`
        # 으로 찍는다 — 문서가 지정한 실행이 `--log-level warning` 이라 그 아래는 보이지 않는다.
        logger.exception("낱말 뜻 조회가 실패해 빈 뜻을 돌려준다 (낱말=%s)", payload.word)
        return VocabLookupResponse(meaning=None)
    return VocabLookupResponse(meaning=meaning)
