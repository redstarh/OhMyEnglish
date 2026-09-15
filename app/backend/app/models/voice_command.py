"""음성 명령 제어 tool 의 이름·스키마·검증 (`TASK-61.1` · 결정 102).

이름과 스키마의 소유자는 이 모듈 하나다 — 어댑터가 문자열을 다시 적으면 보내는 이름과 파서가
기다리는 이름이 갈라져 tool 이벤트가 조용히 버려진다(`models/pronunciation.py` 와 같은 규약).

⛔ **발음 tool 과 규약이 하나 다르다.** 발음은 모르는 `outcome` 을 `unclear` 로 강등하지만 이쪽은
모르는 값을 **버린다.** 종료는 되돌릴 수 없으므로 모호한 페이로드로 세션을 닫는 것이 명령 하나를
잃는 것보다 나쁘다 — 결정 102 ③이 확인 절차를 둔 판단과 같은 방향이다.
"""

from __future__ import annotations

import json
import logging
from typing import Literal, get_args

import pydantic

logger = logging.getLogger(__name__)

# 어댑터와 이 모듈이 같은 이름을 써야 한다.
CONTROL_TOOL_NAME = "request_session_control"

# 받는 명령 셋. `end` 는 첫 조각(결정 102 ②) · `show_report` 는 둘째(결정 107) · `next_question`
# 은 셋째(결정 108)다. 뒤 둘은 되돌릴 수 있는 부류라 확인 절차를 타지 않는다.
#
# ⛔ **명령을 더하면 `CONFIRMATION_REQUIRED` 를 함께 본다** — 이 Literal 에만 더하면 확인 없이
# 도는 것이 기본값이 되고, 되돌릴 수 없는 명령이 그렇게 새면 결정 102 ③이 무너진다.
ControlCommand = Literal["end", "show_report", "next_question"]

# `requested` 는 「명령을 들었고 확인을 묻는다」, `confirmed` 는 「학습자가 확인했다」,
# `cancelled` 는 「학습자가 물렸다」다. ⛔ 앱은 `confirmed` 에서만 세션을 닫는다.
ControlStage = Literal["requested", "confirmed", "cancelled"]

CONTROL_COMMANDS: tuple[ControlCommand, ...] = get_args(ControlCommand)
CONTROL_STAGES: tuple[ControlStage, ...] = get_args(ControlStage)

# 확인을 거쳐야 하는 명령 (결정 107 ③). PRD:85 가 「학습 종료·녹음 삭제 등 **결과가 큰** 명령」에만
# 확인을 요구하므로 조회는 이 집합에 들지 않는다.
#
# ⛔ **판정을 앱이 갖는다** — 모델의 규율에 맡기면 조회에도 확인을 묻거나(대화가 늘어진다) 종료를
# 확인 없이 부른다(결정 102 ③이 막으려던 것이다). `is_wake_command` 를 앱에 둔 것과 같은 규약이다.
CONFIRMATION_REQUIRED: frozenset[ControlCommand] = frozenset({"end"})

# Nova Sonic 의 `inputSchema.json` 은 JSON **문자열**이다 (객체가 아니다 — 스파이크 F1).
CONTROL_TOOL_SCHEMA_JSON = json.dumps(
    {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "enum": list(CONTROL_COMMANDS),
                "description": "Which session control the learner asked for.",
            },
            "stage": {
                "type": "string",
                "enum": list(CONTROL_STAGES),
                "description": (
                    "Use requested right after you hear the command, before you ask the "
                    "learner to confirm. Use confirmed only after the learner has said yes, "
                    "and cancelled if they said no."
                ),
            },
            "heard": {
                "type": "string",
                "description": "What the learner said, as you heard it.",
            },
        },
        "required": ["command", "stage"],
    }
)


# 명령임을 표시하는 접두어 (결정 102 ①). 표지를 **앱이 판정한다** — 모델의 규율에 맡기면
# 학습 발화가 명령으로 저장되는 것을 막을 수 없다.
#
# ⛔ **공백과 문장부호를 지운 뒤 비교한다.** ASR 이 `Oh, my English,` · `오마이 잉글리시` 처럼
# 띄어쓰기와 쉼표를 제 맘대로 적으므로 그대로 비교하면 대개 어긋난다.
# ⚠️ 한글 표기가 「잉글리시」·「잉글리쉬」로 갈려 둘 다 받는다 — 실물 ASR 이 어느 쪽으로 적는지는
# `TASK-61.3` 회차가 관측한다.
_WAKE_FORMS = ("ohmyenglish", "오마이잉글리시", "오마이잉글리쉬")


def _squeeze(text: str) -> str:
    """비교용으로 낮춰 쓰고 **글자·숫자만** 남긴다 (공백·문장부호를 지운다)."""
    return "".join(ch for ch in text.lower() if ch.isalnum())


def is_wake_command(text: str) -> bool:
    """이 발화가 명령 표지로 시작하는가 (결정 102 ①).

    ⛔ **포함 검사를 하지 않는다** — 학습자가 문장 가운데서 앱 이름을 말할 수 있고, 그때 그 발화는
    학습 발화다. 표지는 **맨 앞**에 와야 한다.
    """
    squeezed = _squeeze(text)
    return any(squeezed.startswith(form) for form in _WAKE_FORMS)


def requires_confirmation(command: str) -> bool:
    """이 명령이 확인을 거쳐야 하는가 (결정 107 ③).

    모르는 명령은 `parse_control_payload` 가 이미 버리므로 여기까지 오지 않는다 — 그래도
    `in` 검사로 두어 **모르는 값이 확인 없이 통과하는 쪽으로 기울지 않게** 한다.
    """
    return command in CONFIRMATION_REQUIRED


class ControlReport(pydantic.BaseModel):
    """검증을 통과한 제어 명령. 여기까지 오면 실행해도 되는 값이다."""

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    command: ControlCommand
    stage: ControlStage
    heard: str | None = None


def parse_control_payload(raw: str) -> ControlReport | None:
    """제어 tool 의 `content`(JSON 문자열)를 검증한다. **예외를 던지지 않는다.**"""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("제어 tool 페이로드가 JSON 이 아니다 — 버렸다")
        return None
    if not isinstance(data, dict):
        logger.warning("제어 tool 페이로드가 객체가 아니다 (%s) — 버렸다", type(data).__name__)
        return None

    command = data.get("command")
    if command not in CONTROL_COMMANDS:
        logger.warning("모르는 음성 명령 %r 을 실행하지 않고 버렸다", command)
        return None

    stage = data.get("stage")
    if stage not in CONTROL_STAGES:
        logger.warning("모르는 확인 단계 %r 이라 명령을 실행하지 않고 버렸다", stage)
        return None

    heard = data.get("heard")
    return ControlReport(
        command=command,
        stage=stage,
        heard=heard.strip() if isinstance(heard, str) and heard.strip() else None,
    )
