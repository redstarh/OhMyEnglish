"""세션이 지금 올라선 무대(scenario)의 타입 경계 (설계서 §2.1, `TASK-25` AC#1·#3).

`app/models/`에 두는 이유: `audio_gateway/factory.py`·`audio_gateway/nova.py`는 `app.models`만
알고 `app.services`가 그 값을 채우는 기존 방향과 같다 — `SessionInstruction`
(`models/plan.py`)이 그 선례다. `services`를 여기서 import하면 의존 방향이 뒤집힌다.

⚠️ **이 배치(TASK-6 Batch A)에서는 아무도 이 타입을 쓰지 않는다.** `load_session_scenario`가
이 타입을 채워 `factory`·`nova`로 넘기는 조립 배선은 다음 배치의 몫이다.
"""

from __future__ import annotations

import pydantic


class SessionScenario(pydantic.BaseModel):
    """`learning_sessions.scenario_id`가 가리키는 무대 1건.

    `SessionInstruction`(`models/plan.py`)과 같은 자리를 차지한다 — 대화 상대에게 조립되어
    건네지는 값이라 `services`를 몰라도 된다.
    """

    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str
    prompt_template: str
