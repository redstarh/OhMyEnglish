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
from datetime import date
from typing import Protocol
from uuid import UUID

# job 경로의 두 갈래.
PURPOSE_PLAN = "plan"
PURPOSE_ANALYSIS = "analysis"
# 음성 세션 하나가 쓴 토큰(`TASK-124` · 결정 68). ⚠️ **호출이 아니라 «세션» 단위다** — Nova 의
# `usageEvent` 는 세션 동안 여러 번 오고 값이 **누적 총계**이므로 마지막 값만 세션 끝에 적는다.
# 이벤트마다 적으면 같은 토큰이 여러 행에 겹쳐 합계가 부풀어 오른다.
PURPOSE_NOVA = "nova"
# job 밖 호출의 기본값. ⚠️ **기본값을 「분석」으로 두지 않는 이유**: 갈래를 잘못 적은 행은 비용을
# **틀린 축에** 얹고, 그 오류는 조용하다. 이름 없는 호출은 「임시 호출」이라고 말하는 쪽이 정직하다.
PURPOSE_SPIKE = "spike"

PROVIDER_BEDROCK = "bedrock"


@dataclass(frozen=True)
class TokenUsage:
    """한 호출(또는 음성 세션 하나)이 쓴 토큰.

    ⛔ **파생값(비용·합계)을 여기서 계산하지 않는다.** 단가는 모델·리전·시점에 따라 바뀌므로
    저장된 토큰 수에서 **읽을 때** 곱한다 — 곱해서 저장하면 단가가 바뀔 때 과거 행이 거짓이 된다.

    `input_tokens`·`output_tokens`는 **합계**다. 넷의 분해는 `TASK-124`(결정 68)가 더했고
    **Nova 만 채운다** — `usageEvent.details.total` 이 `speechTokens`·`textTokens` 로 나눠 주기
    때문이다. ⚠️ Claude(InvokeModel)는 그 축이 **아예 없으므로** `None` 이고, 그 `None` 이
    「분해 없음」을 뜻한다. ⛔ **0 으로 채우지 않는다** — 0 은 「speech 토큰을 쓰지 않았다」는
    주장이 되고 Claude 호출에는 그런 주장을 할 근거가 없다.
    """

    input_tokens: int
    output_tokens: int
    input_speech_tokens: int | None = None
    input_text_tokens: int | None = None
    output_speech_tokens: int | None = None
    output_text_tokens: int | None = None


@dataclass(frozen=True)
class UsageRollup:
    """하루·한 갈래의 사용량 집계 (`TASK-126`).

    `day`는 **사용자 타임존의 달력 날짜**다 — `users.timezone` 이 그 정본이고 `current_date` 를
    쓰지 않는다(전역 시각 규약 3항: UTC 자정~09:00 KST 구간에서 하루 이른 값이 나온다).

    분해 넷이 `None` 일 수 있는 이유는 `TokenUsage` 와 같다 — 그 갈래의 행이 전부 분해 없이
    적혔다는 뜻이다(SQL `sum()` 은 전부 NULL 이면 NULL 을 낸다). ⛔ **0 으로 바꾸지 않는다**:
    「분해가 없다」와 「분해가 0 이다」는 다른 사실이고, Nova 단가 계산이 그 차이에 걸린다.

    ⛔ **금액을 담지 않는다** — 단가를 어디에 둘지는 아직 결정되지 않았다(`TASK-126` AC#4).
    """

    day: date
    purpose: str
    calls: int
    input_tokens: int
    output_tokens: int
    input_speech_tokens: int | None
    input_text_tokens: int | None
    output_speech_tokens: int | None
    output_text_tokens: int | None


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
