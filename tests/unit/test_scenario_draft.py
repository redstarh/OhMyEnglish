"""`app.models.scenario_draft` — 모델이 만든 무대를 검증한다 (`TASK-5` AC#3).

⛔ 이 파일은 DB 를 쓰지 않는다. 값역과 중복 목록을 **인자로 받는 것**이 파서의 계약이고
(설계서 §5), 그래서 이 테스트가 픽스처 없이 거부 경계를 전부 잰다.

⛔ **`level` 과 `source` 가 반환에 없다.** 둘은 모델이 만들 수 없는 값이라 호출자가 붙인다 —
`parse_plan` 이 `current_level` 을 인자로 받는 것과 같은 형태다. 그 부재를 이 파일이
`test_draft_does_not_carry_level_or_source` 로 못 박는다.
"""

from __future__ import annotations

import json

import pytest

from app.models.scenario_draft import (
    ScenarioDraft,
    ScenarioNoStage,
    ScenarioValidationError,
    normalize_title,
    parse_scenario,
)

_ALLOWED = frozenset({"daily_life", "business", "travel", "shopping", "health"})


def _raw(**overrides: object) -> str:
    body: dict[str, object] = {
        "category": "business",
        "title": "Reporting a delay to my manager",
        "prompt_template": "You are the learner's manager hearing about a delayed task.",
    }
    body.update(overrides)
    return json.dumps(body)


def test_accepts_a_well_formed_draft() -> None:
    got = parse_scenario(_raw(), allowed_categories=_ALLOWED, existing_titles=frozenset())
    assert got == ScenarioDraft(
        category="business",
        title="Reporting a delay to my manager",
        prompt_template="You are the learner's manager hearing about a delayed task.",
    )


def test_draft_does_not_carry_level_or_source() -> None:
    """⛔ 모델이 만들 수 없는 값을 파서가 나르지 않는다 (AC#3).

    모델이 `level`·`source` 를 **보내더라도** 무시한다 — 지어낸 값이 조용히 저장되면 난이도가
    튀거나 시드 행이 사용자 생성으로 기록된다.
    """
    got = parse_scenario(
        _raw(level="C2", source="seed"),
        allowed_categories=_ALLOWED,
        existing_titles=frozenset(),
    )
    assert not hasattr(got, "level")
    assert not hasattr(got, "source")


def test_rejects_unknown_category() -> None:
    with pytest.raises(ScenarioValidationError, match="category"):
        parse_scenario(
            _raw(category="cooking"), allowed_categories=_ALLOWED, existing_titles=frozenset()
        )


def test_rejects_missing_category() -> None:
    """⛔ 무대(축 1)가 비면 거부한다 — 그것만 필수다(설계서 §5).

    모델이 무대를 못 찾았을 때 값역 중 하나를 고르면 그것은 **지어낸 값**이다. `null` 을
    보내는 길을 열어 두고 파서가 그것을 거부한다.
    """
    with pytest.raises(ScenarioValidationError, match="category"):
        parse_scenario(
            _raw(category=None), allowed_categories=_ALLOWED, existing_titles=frozenset()
        )


# `TASK-259` — 거부는 그대로이고 **종류가 갈린다.** 명시적 `null` 은 프롬프트가 지시한 답이므로
# 재시도가 무의미하고(입력이 같다), 그 구별을 호출자가 읽어 첫 시도에 종결한다.
# ⚠️ 위 테스트가 그대로 통과하는 것이 하위 클래스로 만든 목적이다 — 기존 호출자의 거동이 바뀌지 않음.
def test_an_explicit_null_category_is_the_no_stage_signal() -> None:
    with pytest.raises(ScenarioNoStage):
        parse_scenario(
            _raw(category=None), allowed_categories=_ALLOWED, existing_titles=frozenset()
        )


def test_a_missing_category_key_is_a_plain_contract_violation() -> None:
    """키가 «없는» 것은 프롬프트 위반이다 — 다른 표본이 지킬 수 있으므로 재시도 대상이다.

    ⛔ 그래서 `ScenarioNoStage` 가 아니어야 한다. 두 경우를 한 예외로 묶으면 재시도 판정이
    무너진다(누락에도 종결하거나, `null` 에도 5회 묻는다).
    """
    body = json.loads(_raw())
    del body["category"]

    with pytest.raises(ScenarioValidationError) as caught:
        parse_scenario(json.dumps(body), allowed_categories=_ALLOWED, existing_titles=frozenset())
    assert not isinstance(caught.value, ScenarioNoStage)


def test_rejects_empty_or_overlong_title() -> None:
    for bad in ("", "   ", "x" * 121):
        with pytest.raises(ScenarioValidationError, match="title"):
            parse_scenario(
                _raw(title=bad), allowed_categories=_ALLOWED, existing_titles=frozenset()
            )


def test_rejects_a_question_as_the_stage() -> None:
    """⛔ 무대는 질문이 아니다 — 질문은 계획이 소유한다(캡틴 결정 14).

    시드에 대해 `test_seeded_scenarios_are_stages_not_questions` 가 재는 것과 같은 규칙이다.
    """
    with pytest.raises(ScenarioValidationError, match="prompt_template"):
        parse_scenario(
            _raw(prompt_template="What do you do at work?"),
            allowed_categories=_ALLOWED,
            existing_titles=frozenset(),
        )


def test_rejects_title_equal_to_prompt() -> None:
    same = "You are the learner's manager."
    with pytest.raises(ScenarioValidationError, match="같"):
        parse_scenario(
            _raw(title=same, prompt_template=same),
            allowed_categories=_ALLOWED,
            existing_titles=frozenset(),
        )


def test_rejects_duplicate_title_ignoring_case_and_space() -> None:
    """⛔ 공백·대소문자만 다른 제목을 다른 무대로 세면 중복 방어가 공허해진다(설계서 §5)."""
    existing = frozenset({normalize_title("Reporting a delay to my manager")})
    with pytest.raises(ScenarioValidationError, match="이미"):
        parse_scenario(
            _raw(title="  REPORTING A DELAY TO MY MANAGER  "),
            allowed_categories=_ALLOWED,
            existing_titles=existing,
        )


def test_rejects_non_json() -> None:
    with pytest.raises(ScenarioValidationError):
        parse_scenario(
            "무대를 못 찾았습니다", allowed_categories=_ALLOWED, existing_titles=frozenset()
        )


def test_rejects_a_json_top_level_that_is_not_an_object() -> None:
    """⛔ 「JSON 이 아니다」와 **다른 사유**로 거부한다 (`TASK-226`).

    ⚠️ 이 갈래는 세 파서 모두 단정이 없어서 변이로 드러났다 — 객체가 아닌 최상위를 조용히 빈
    객체로 바꾸는 변이가 전체 1408건을 통과했다. 그 뒤 「필수 섹션 없음」으로 거부되므로 결과는
    같지만 **사유가 원인을 잘못 지목한다.**
    """
    with pytest.raises(ScenarioValidationError, match="최상위"):
        parse_scenario("[1, 2]", allowed_categories=_ALLOWED, existing_titles=frozenset())


def test_accepts_a_fenced_json_block() -> None:
    """⚠️ 프롬프트가 펜스를 금지해도 모델이 붙인다 — `parse_plan` 과 같은 한 번의 재시도."""
    fenced = f"```json\n{_raw()}\n```"
    got = parse_scenario(fenced, allowed_categories=_ALLOWED, existing_titles=frozenset())
    assert got.category == "business"


def test_normalize_title_is_idempotent() -> None:
    once = normalize_title("  Mixed Case  Title ")
    assert normalize_title(once) == once
