"""LLM 호출의 토큰 사용량 — 순수 타입만 (`TASK-60` · 사용자 결정 66).

이 모듈이 `models`에 있는 이유: **쓰는 쪽과 적는 쪽이 서로를 몰라야 한다.** 값을 만드는 것은
`workers/claude_client`(Bedrock 응답의 `usage`)이고 적는 것은 `services/usage`(DB)다. 둘이 서로를
import 하면 포트 구현이 DB 를 알게 되고, 그러면 자격증명·네트워크 없이 도는 단위 테스트가 DB 를
요구한다(`audio_gateway`가 `app.models`만 아는 것과 같은 경계다).

⛔ **`purpose` 값역을 여기서 열거하지 않는다.** 정본은 013 의 `llm_calls_purpose_check` 이고, 아래
상수는 **이 코드가 실제로 쓰는 값만** 이름 붙인 것이다 — `api/ws.py`가 `SHADOWING_MODE`·
`PRONUNCIATION_MODE`만 두고 값역 전체를 두지 않는 것과 같은 규약이다. 값역 밖 값은
`asyncpg.PostgresError`로 올라간다(조용히 다른 갈래로 바뀌지 않는다).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

# job 경로의 두 갈래. `nova`는 013 의 값역에 자리는 있으나 아직 기록하지 않는다 — 그 클라이언트는
# 양방향 스트리밍이고 응답 모양이 달라서 같은 추출기로 읽히지 않는다(`TASK-60` 노트).
PURPOSE_PLAN = "plan"
PURPOSE_ANALYSIS = "analysis"
# job 밖 호출의 기본값. ⚠️ **기본값을 「분석」으로 두지 않는 이유**: 갈래를 잘못 적은 행은 비용을
# **틀린 축에** 얹고, 그 오류는 조용하다. 이름 없는 호출은 「임시 호출」이라고 말하는 쪽이 정직하다.
PURPOSE_SPIKE = "spike"

PROVIDER_BEDROCK = "bedrock"


@dataclass(frozen=True)
class TokenUsage:
    """한 호출이 쓴 토큰. Bedrock Anthropic 응답의 `usage` 두 값을 그대로 담는다.

    ⛔ **파생값(비용·합계)을 여기서 계산하지 않는다.** 단가는 모델·리전·시점에 따라 바뀌므로
    저장된 토큰 수에서 **읽을 때** 곱한다 — 곱해서 저장하면 단가가 바뀔 때 과거 행이 거짓이 된다.
    """

    input_tokens: int
    output_tokens: int


class UsageSink(Protocol):
    """사용량 1건을 적는 쪽. 실패해도 **호출자를 막지 않는다**(구현이 그 규약을 갖는다).

    ⚠️ `job_id`가 `None`인 것이 정상이다 — job 밖 호출(계획 스파이크·예열)이 이 표의 존재 이유다.
    """

    async def __call__(
        self,
        usage: TokenUsage,
        *,
        model_id: str,
        purpose: str,
        job_id: UUID | None,
    ) -> None: ...
