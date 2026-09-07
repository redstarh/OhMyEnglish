"""세션이 지금 올라선 무대(scenario)의 타입 경계 (설계서 §2.1, `TASK-25` AC#1·#3).

`app/models/`에 두는 이유: `audio_gateway/factory.py`·`audio_gateway/nova.py`는 `app.models`만
알고 `app.services`가 그 값을 채우는 기존 방향과 같다 — `SessionInstruction`
(`models/plan.py`)이 그 선례다. `services`를 여기서 import하면 의존 방향이 뒤집힌다.

**소비 경로는 하나다** (TASK-25 Batch B에서 배선됐다): `services/sessions.load_session_scenario`가
세션 행에 박힌 `scenario_id`를 읽어 이 타입을 채우고, `api/ws.py`가 `create_voice_adapter`로,
팩토리가 `build_system_prompt`로 넘겨 `Today's setting:` 블록이 된다.

⚠️ **`title`은 그 블록에 실리지 않는다.** 지시문에 가는 것은 `prompt_template` 하나이고 `title`은
**화면용 라벨**이다(규칙 6: *"Never read JSON, lists, or metadata out loud"*). 두 필드를 같은
타입에 두는 이유는 조회가 한 번이기 때문이고, 어느 쪽이 지시문에 실리는지는
`build_system_prompt`의 docstring이 소유한다.
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
