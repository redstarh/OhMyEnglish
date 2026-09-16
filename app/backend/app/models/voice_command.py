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

# 받는 명령 넷. `end`(결정 102 ②) · `show_report`(결정 107) · `next_question`(결정 108) ·
# `start_additional`(결정 110). 가운데 둘은 되돌릴 수 있어 확인 절차를 타지 않는다.
#
# ⛔ **명령을 더하면 아래 두 집합을 함께 본다** — 이 Literal 에만 더하면 「확인 없이 돌고 세션도
# 닫지 않는다」가 기본값이 되고, 되돌릴 수 없는 명령이 그렇게 새면 결정 102 ③이 무너진다.
ControlCommand = Literal["end", "show_report", "next_question", "start_additional"]

# 「추가 학습」이 열 수 있는 것 (결정 110 ②). 값역의 근거는 **화면이 실제로 가르는 표면**이다 —
# `frontend/app/page.tsx` 의 `ADDITIONAL_LEARNING` 여섯 가운데 「업무 역할극」은 비활성이고
# (무대를 고르는 화면이 없다) 「자유 대화」·「약점 패턴 집중」은 같은 entry 를 쓴다.
# ⛔ **화면이 가르지 못하는 값을 여기에 두지 않는다** — 두면 모델이 고른 값이 조용히 버려진다.
AdditionalTarget = Literal["conversation", "scenario_intake", "pronunciation", "shadowing"]

# `requested` 는 「명령을 들었고 확인을 묻는다」, `confirmed` 는 「학습자가 확인했다」,
# `cancelled` 는 「학습자가 물렸다」다. ⛔ 앱은 `confirmed` 에서만 세션을 닫는다.
ControlStage = Literal["requested", "confirmed", "cancelled"]

CONTROL_COMMANDS: tuple[ControlCommand, ...] = get_args(ControlCommand)
CONTROL_STAGES: tuple[ControlStage, ...] = get_args(ControlStage)
ADDITIONAL_TARGETS: tuple[AdditionalTarget, ...] = get_args(AdditionalTarget)

# 확인을 거쳐야 하는 명령 (결정 107 ③). PRD:85 가 「학습 종료·녹음 삭제 등 **결과가 큰** 명령」에만
# 확인을 요구하므로 조회는 이 집합에 들지 않는다.
#
# ⛔ **판정을 앱이 갖는다** — 모델의 규율에 맡기면 조회에도 확인을 묻거나(대화가 늘어진다) 종료를
# 확인 없이 부른다(결정 102 ③이 막으려던 것이다). `is_wake_command` 를 앱에 둔 것과 같은 규약이다.
CONFIRMATION_REQUIRED: frozenset[ControlCommand] = frozenset({"end", "start_additional"})

# 세션을 닫는 명령 (결정 110 ④). ⛔ **위 집합과 값이 같아도 합치지 않는다** — 「확인이 필요한가」와
# 「세션을 닫는가」는 다른 물음이고, 한 이름으로 쓰면 둘이 갈리는 순간 조용히 틀린다.
# (예: 녹음 삭제는 확인이 필요하지만 세션을 닫지 않는다.)
CLOSES_SESSION: frozenset[ControlCommand] = frozenset({"end", "start_additional"})

# `target` 을 반드시 받아야 하는 명령. 없으면 무엇을 열지 모르므로 페이로드를 버린다.
TARGET_REQUIRED: frozenset[ControlCommand] = frozenset({"start_additional"})

# 표지가 없어 **실행하지 않은** 것을 화면에 알리는 명령 (결정 113 ② · `TASK-61.16`).
#
# ⛔ **`next_question` 은 넣지 않는다.** 그 명령은 프레임이 버려져도 코치가 실제로 다음 질문을
# 하므로 화면이 어긋나지 않는다 — 실측이 그것을 갈랐다
# (`tests/harness/runs/2026-09-16-task61-15-accepted-without-execution` §4 의 표).
# 「전부 알린다」로 넓히면 알림이 잡음이 되고, 잡음이 되면 학습자가 그 자리를 보지 않는다.
#
# ⚠️ **이 집합은 「실행 여부」와 무관하다** — 실행하지 않는 것은 표지 검사가 정하고 그것은 바뀌지
# 않았다(결정 104 D5). 이 집합이 정하는 것은 **버린 사실을 말하는가** 하나다.
SURFACED_ON_MARKER_MISS: frozenset[ControlCommand] = frozenset(
    {"end", "start_additional", "show_report"}
)

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
            # ⛔ `required` 에 넣지 않는다 — 다른 명령에는 필요 없고, 필수로 두면 모델이
            # 종료·조회에도 아무 값이나 채운다. 「이 명령에는 필수」는 앱이 검증한다.
            "target": {
                "type": "string",
                "enum": list(ADDITIONAL_TARGETS),
                "description": (
                    "Which extra practice to start. Required when command is "
                    "start_additional, and left out otherwise."
                ),
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
#
# **결정 114 (`TASK-61.17`) — 짧은 표지 넷을 더했다.** 앱 이름 표지가 영어에서 2회 중 1회
# 인식되지 않았고(`runs/2026-09-16-task61-15-accepted-without-execution` §3-①) 그 실패가 명령을
# 조용히 버려 코치의 말과 앱 상태가 갈리는 결함의 트리거였다.
# ⛔ **바꾼 것은 형태 하나다** — 「표지를 앱이 판정한다」와 「맨 앞에 와야 한다」는 그대로다.
# ⚠️ **대가를 알고 받는다**: 「Hello」·「Hey」는 학습자의 가장 흔한 첫마디라 학습 발화가 표지를 얻어
# `voice_command` 로 저장되고 분석에서 빠질 수 있다. 그 크기는 실물 회차가 센다(`TASK-61.17` AC#4).
# ⚠️ 앱 이름 표지를 **떨어뜨리지 않는다** — 이미 만든 픽스처와 이전 회차의 관측이 그것에 걸려 있어
# 지우면 회귀를 회귀로 알아볼 수 없다.
_WAKE_FORMS = (
    "ohmyenglish",
    "오마이잉글리시",
    "오마이잉글리쉬",
    "hey",
    "hello",
    "헤이",
    # ⚠️ **실물 ASR 이 「헤이」를 「해이」로 적었다** — 2026-09-16 회차에서 직접 관측했고
    # (`runs/2026-09-16-task61-16-divergence-surface` 팔 `s5-hey-mode-ko`) 그 때문에 명령이
    # 버려졌다. `잉글리시`·`잉글리쉬` 를 둘 다 받은 것과 같은 이유로 두 표기를 받는다.
    "해이",
    # 「헬로우」는 앞자리 검사가 함께 받는다 — `잉글리시`·`잉글리쉬` 를 둘 다 받은 것과 같은 이유다.
    "헬로",
)


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


def closes_session(command: str) -> bool:
    """이 명령이 세션을 닫는가 (결정 110 ④).

    ⛔ `requires_confirmation` 과 **다른 물음**이다 — 값이 같아도 하나로 합치지 않는다.
    """
    return command in CLOSES_SESSION


class ControlReport(pydantic.BaseModel):
    """검증을 통과한 제어 명령. 여기까지 오면 실행해도 되는 값이다."""

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    command: ControlCommand
    stage: ControlStage
    heard: str | None = None
    # 「추가 학습」이 열 대상 (결정 110 ②). 그 명령에만 실리고 나머지는 `None` 이다.
    target: AdditionalTarget | None = None


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

    target = data.get("target")
    if command in TARGET_REQUIRED:
        # ⛔ **모르는 대상으로 세션을 닫지 않는다.** 이 모듈의 「모르는 값은 버린다」 규약이 가장
        # 강하게 걸리는 자리다 — 잘못 열면 학습자가 원하지 않은 세션이 시작되고 앞 세션은 닫혔다.
        if target not in ADDITIONAL_TARGETS:
            logger.warning("추가 학습 대상 %r 을 알 수 없어 명령을 버렸다", target)
            return None
    elif target is not None:
        # 대상이 필요 없는 명령에 실려 오면 **명령을 버리지 않고 대상만 무시한다** — 명령 자체는
        # 유효하고, 모델이 여분 필드를 붙였다는 이유로 종료·조회를 잃는 것이 더 나쁘다.
        target = None

    heard = data.get("heard")
    return ControlReport(
        command=command,
        stage=stage,
        heard=heard.strip() if isinstance(heard, str) and heard.strip() else None,
        target=target,
    )
