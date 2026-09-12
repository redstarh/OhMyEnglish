"""모델이 만든 무대 하나를 검증한다 (`TASK-5` AC#3 · 결정 79).

**결정의 정본은 `docs/ops/captain-instruction-register.md` 의 결정 79 다.** 거부 경계의 목록과
근거는 `docs/design/2026-09-12-scenario-generator-design.md` §5 가 소유한다.

⛔ **`level` 과 `source` 를 여기서 나르지 않는다.** 둘은 **모델이 만들 수 없는 값**이고 호출자가
붙인다 — `models/plan.py` 의 `parse_plan` 이 `current_level`·`allowed_pattern_ids` 를 인자로 받는
것과 같은 원칙이다(그 docstring 이 근거를 갖는다). 모델이 그 키를 **보내더라도 무시한다**:
지어낸 등급이 저장되면 난이도가 튀고, 지어낸 출처는 사용자 생성 행을 시드로 기록한다.

⛔ **값역과 중복 목록도 인자로 받는다.** 이 모듈은 DB 를 모르므로 「무엇이 허용되는가」를 알 수
없다 — 그 분리가 거부 경계를 픽스처 없이 테스트하게 한다(`tests/unit/test_scenario_draft.py`).

⛔ **반쯤 검증된 무대를 내지 않는다.** 실패는 전부 `ScenarioValidationError` 하나로 수렴하고
호출자가 그것을 job 실패로 보고한다(`plan.py` 의 *"반쯤 검증된 계획을 쓰지 않는다"* 와 같은 규약).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

# ⚠️ private 이름을 가져오는 것이 의도다 — 이 로직(원문 → 코드펜스 벗긴 본문 순서로 파싱 시도)을
# 복제하면 두 파서가 서로 다른 관대함을 갖게 되고 한쪽이 조용히 낡는다. `parse_plan` 과 **같은
# 관대함**을 쓰는 것이 이 import 의 목적이다. ⛔ 공개 API 로 승격하지 않은 이유: 그 파일이 그
# 함수의 경계(한 번의 재시도까지만)를 docstring 으로 소유하고 있고, 옮기면 그 근거가 흩어진다.
from app.models.plan import _json_candidates

# 화면 라벨이므로 한 줄이어야 한다. ⚠️ 120 은 발명값이다 — 시드 30행의 최장 제목이 33자이므로
# 그 네 배쯤을 상한으로 두었다. 캡틴 문서에 근거가 있는 수치가 아니다.
_TITLE_MAX = 120


class ScenarioValidationError(ValueError):
    """모델 출력이 무대의 계약을 지키지 못했다. 실패는 전부 이 하나로 수렴한다."""


@dataclass(frozen=True, slots=True)
class ScenarioDraft:
    """검증을 통과한 무대 초안. ⛔ `level`·`source` 가 **없는 것이 계약**이다."""

    category: str
    title: str
    prompt_template: str


def normalize_title(title: str) -> str:
    """중복 판정을 위한 정규화 — 앞뒤 공백을 걷고 내부 공백을 하나로 줄이고 소문자로 만든다.

    ⛔ 공백·대소문자만 다른 제목을 다른 무대로 세면 중복 방어가 공허해진다(설계서 §5).
    호출자가 기존 제목 목록을 만들 때도 **이 함수를 써야** 양쪽 정규화가 갈라지지 않는다.
    """
    return " ".join(title.split()).casefold()


def _loaded(raw: str) -> dict[str, Any]:
    last_error: json.JSONDecodeError | None = None
    for candidate in _json_candidates(raw):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as error:
            last_error = error
            continue
        if not isinstance(parsed, dict):
            raise ScenarioValidationError(f"JSON 최상위가 객체가 아니다: {type(parsed).__name__}")
        return parsed
    raise ScenarioValidationError(f"JSON 으로 읽을 수 없다: {last_error}")


def parse_scenario(
    raw: str,
    *,
    allowed_categories: frozenset[str],
    existing_titles: frozenset[str],
) -> ScenarioDraft:
    """모델 출력 문자열 → 검증된 무대 초안. 실패는 전부 `ScenarioValidationError` 다.

    `existing_titles` 는 **`normalize_title` 로 정규화된** 기존 `generated` 제목의 집합이다.
    ⛔ 시드 제목을 넣지 않는다 — 학습자가 시드와 비슷한 무대를 자기 말로 다시 정의하는 것은
    막을 일이 아니다(설계서 §5).

    거부 순서는 **싼 것부터**다: JSON → 무대(축 1) → 제목 → 지시문 → 중복. 앞에서 걸리면
    뒤를 재지 않으므로 실패 메시지가 **가장 근본적인 사유**를 가리킨다.
    """
    body = _loaded(raw)

    # ⛔ 무대만 필수다(설계서 §5). 다른 넷은 비어도 통과한다 — 다섯을 모두 필수로 하면 학습자가
    # 한 축만 모른다고 답해도 생성이 실패하고 그것은 5회 대화를 버리는 일이다.
    category = body.get("category")
    if not isinstance(category, str) or category not in allowed_categories:
        raise ScenarioValidationError(
            f"category 가 값역 밖이거나 비었다: {category!r} (허용: {sorted(allowed_categories)})"
        )

    title = body.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ScenarioValidationError(f"title 이 비었다: {title!r}")
    title = title.strip()
    if len(title) > _TITLE_MAX:
        raise ScenarioValidationError(f"title 이 {len(title)}자다 — 상한 {_TITLE_MAX}자")

    template = body.get("prompt_template")
    if not isinstance(template, str) or not template.strip():
        raise ScenarioValidationError(f"prompt_template 이 비었다: {template!r}")
    template = template.strip()
    if template.endswith("?"):
        raise ScenarioValidationError(f"prompt_template 이 질문이다 — 무대여야 한다: {template!r}")
    if normalize_title(template) == normalize_title(title):
        raise ScenarioValidationError("title 과 prompt_template 이 같다 — 규칙 6 방어가 공허해진다")

    if normalize_title(title) in existing_titles:
        raise ScenarioValidationError(f"이미 같은 무대가 있다: {title!r}")

    return ScenarioDraft(category=category, title=title, prompt_template=template)
