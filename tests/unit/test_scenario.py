"""SessionScenario 계약 (설계서 §2.1 TASK-25 AC#1·#3, Batch A).

`models/plan.py`의 `SessionInstruction`과 같은 자리를 차지한다 — 대화 상대에게 조립되어
건네지는 값이라 `services`를 몰라도 된다. **이 배치에서는 아무도 이 타입을 쓰지 않는다**
(소비 배선 — `load_session_scenario`·`factory`·`nova` — 은 다음 배치의 몫). 여기서
못박는 것은 계약뿐이다: `title`·`prompt_template`을 받고, 누락·잘못된 타입·모르는 필드는
거부한다.
"""

from __future__ import annotations

import pydantic
import pytest

from app.models.scenario import SessionScenario


def test_constructs_with_title_and_prompt_template():
    scenario = SessionScenario(
        title="공항 체크인",
        prompt_template="You are an airline check-in agent. Ask for the passport.",
    )

    assert scenario.title == "공항 체크인"
    assert scenario.prompt_template == "You are an airline check-in agent. Ask for the passport."


def test_rejects_missing_title():
    with pytest.raises(pydantic.ValidationError):
        SessionScenario(prompt_template="You are an airline check-in agent.")  # ty: ignore[missing-argument]


def test_rejects_missing_prompt_template():
    with pytest.raises(pydantic.ValidationError):
        SessionScenario(title="공항 체크인")  # ty: ignore[missing-argument]


def test_rejects_wrong_type_for_title():
    with pytest.raises(pydantic.ValidationError):
        SessionScenario(title=123, prompt_template="text")  # ty: ignore[invalid-argument-type]


def test_rejects_wrong_type_for_prompt_template():
    with pytest.raises(pydantic.ValidationError):
        SessionScenario(
            title="공항 체크인",
            prompt_template=123,  # ty: ignore[invalid-argument-type]
        )


def test_rejects_extra_fields():
    """`SessionInstruction`과 같은 `extra="forbid"` 관례 — 모르는 필드는 계약 위반 신호다."""
    with pytest.raises(pydantic.ValidationError):
        SessionScenario(
            title="공항 체크인",
            prompt_template="text",
            bogus="unexpected",  # ty: ignore[unknown-argument]
        )
