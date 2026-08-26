"""발음 시범·재발화의 타입 경계 (설계서 §4.2).

**Nova 출력을 신뢰하지 않는다.** 2026-08-27 스파이크에서 모델이 실제로 스키마를
어겼다 — `outcome` enum 에 없는 `"pending"` 을 냈다(설계서 F4). 그래서 이 모듈이 하는
일은 파싱이 아니라 **강등과 폐기**다:

* 열거값 밖 / 누락 / 타입 불일치 → `unclear` 로 **강등**. 세션을 깨뜨리지 않는다.
* `target_form` 이 비었거나 JSON 이 깨졌으면 → **폐기**(`None`). 시범이 없는
  시범 기록은 의미가 없다.

엄격 검증으로 거부하지 않는 이유는 전례다 — 1차수 I-5 에서 모델 출력에 엄격 검증을
걸었을 때 그 발화가 5회 재시도 끝에 `failed` 가 됐다. 발음 기록은 대화보다 덜 중요하니
기록을 잃는 편이 세션을 끊는 것보다 낫다.

값역은 `db/migrations/003_pronunciation_echo.sql` 의 CHECK 와 같아야 한다 — 어긋나면
앱이 통과시킨 값을 DB 가 거부한다. 테스트가 그 일치를 지킨다.
"""

from __future__ import annotations

import json
import logging
from typing import Literal, get_args

import pydantic

logger = logging.getLogger(__name__)

# `pending` 은 정식 값이다 — Nova 는 재발화 **전에** tool 을 부른다(설계서 F3).
PronunciationOutcome = Literal["pending", "correct", "incorrect", "unclear"]

# 이 행이 무엇 때문에 생겼는지. `agent_reprompt` 는 값역에만 두고 첫 구현에서는 쓰지
# 않는다 — 문구 매칭이라 취약해 5차수 관측 후 판정한다(설계서 §10 미결 2).
SignalSource = Literal["nova_tool", "korean_transcript", "agent_reprompt"]

# Literal 에서 파생 — 코드값을 두 번 적지 않는다 (`models/analysis.py` 와 같은 관례).
PRONUNCIATION_OUTCOMES: tuple[PronunciationOutcome, ...] = get_args(PronunciationOutcome)
SIGNAL_SOURCES: tuple[SignalSource, ...] = get_args(SignalSource)

# 어댑터와 이 모듈이 같은 이름을 써야 한다 — 다르면 tool 이벤트가 조용히 버려진다.
PRONUNCIATION_TOOL_NAME = "report_pronunciation_coaching"

# Nova Sonic 의 `inputSchema.json` 은 **JSON 문자열**이다(객체가 아니다) — 스파이크 F1.
PRONUNCIATION_TOOL_SCHEMA_JSON = json.dumps(
    {
        "type": "object",
        "properties": {
            "target_form": {
                "type": "string",
                "description": "The full sentence you modeled with correct pronunciation.",
            },
            "spoken_form": {
                "type": "string",
                "description": "How the learner actually sounded, if you have heard it yet.",
            },
            "target_sound": {
                "type": "string",
                "description": "Reusable key for the sound that was off, e.g. th_as_s.",
            },
            "outcome": {
                "type": "string",
                "enum": list(PRONUNCIATION_OUTCOMES),
                "description": (
                    "Use pending when you have modeled the sentence but have not yet "
                    "heard the learner repeat it."
                ),
            },
        },
        "required": ["target_form", "outcome"],
    }
)


class PronunciationReport(pydantic.BaseModel):
    """검증을 통과한 발음 보고. 여기까지 오면 신뢰할 수 있다."""

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    target_form: str
    outcome: PronunciationOutcome
    spoken_form: str | None = None
    target_sound: str | None = None


def parse_tool_payload(raw: str) -> PronunciationReport | None:
    """Nova tool 의 `content`(JSON 문자열)를 검증한다. **예외를 던지지 않는다.**"""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("발음 tool 페이로드가 JSON 이 아니다 — 버렸다")
        return None
    if not isinstance(data, dict):
        logger.warning("발음 tool 페이로드가 객체가 아니다 (%s) — 버렸다", type(data).__name__)
        return None

    target_form = data.get("target_form")
    if not isinstance(target_form, str) or not target_form.strip():
        logger.warning("발음 tool 페이로드에 쓸 수 있는 target_form 이 없다 — 버렸다")
        return None

    outcome = data.get("outcome")
    if outcome not in PRONUNCIATION_OUTCOMES:
        logger.warning("발음 outcome %r 을 unclear 로 강등했다", outcome)
        outcome = "unclear"

    def _optional_text(key: str) -> str | None:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    return PronunciationReport(
        target_form=target_form.strip(),
        outcome=outcome,
        spoken_form=_optional_text("spoken_form"),
        target_sound=_optional_text("target_sound"),
    )
