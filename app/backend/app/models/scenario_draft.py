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

from dataclasses import dataclass

# ⚠️ JSON 읽기를 복제하지 않고 가져온다 — 복제하면 두 파서의 관대함이 갈라지고 한쪽이 조용히
# 낡는다. `parse_plan` 과 **같은 관대함**을 쓰는 것이 이 import 의 목적이고, 그 경계(한 번의
# 재시도까지만)는 `models/plan.py` 가 docstring 으로 소유한다. ⚠️ 이 파일의 `_loaded` 는 그
# 함수로 접혔다 — 예외 클래스만 다른 3벌이었다(`TASK-226`).
from app.models.plan import loaded_object

# 화면 라벨이므로 한 줄이어야 한다. ⚠️ 120 은 발명값이다 — 시드 30행의 최장 제목이 33자이므로
# 그 네 배쯤을 상한으로 두었다. 캡틴 문서에 근거가 있는 수치가 아니다.
_TITLE_MAX = 120


class ScenarioValidationError(ValueError):
    """모델 출력이 무대의 계약을 지키지 못했다. 실패는 전부 이 하나로 수렴한다."""


class ScenarioNoStage(ScenarioValidationError):
    """모델이 **지시받은 대로** 「무대가 없다」고 답했다 — `category` 가 명시적 `null` 이다.

    ⛔ **이것은 모델의 잘못이 아니라 프롬프트가 요구한 답이다** (`_AXES`: *"축 1(무대)이 전사문에
    없으면 무대를 지어내지 마라 — `category` 를 `null` 로 내라"*). 그러므로 **재시도해도 같은 답이
    온다** — 입력이 같다. 실측(2026-09-20 · `TASK-259`): 무대를 말하지 않은 전사문으로 실물 모델을
    8회 불러 **8회 모두** `null` 이 왔고, 그 8회가 전부 파서에 거부됐다. 그 상태에서 큐가 5회까지
    재시도하므로 **유료 호출 4건이 낭비된다**(그 5회도 직접 셌다).

    ⚠️ **`ScenarioValidationError` 의 하위 클래스인 것이 계약이다** — 기존 호출자의
    `except ScenarioValidationError` 가 그대로 이 경우를 잡으므로, 이 클래스를 몰라도 거동이
    바뀌지 않는다. 구별해 쓰는 곳은 「재시도할지」를 정하는 자리 하나뿐이다
    (`services/scenario_generator.process_scenario`).
    ⛔ **키가 «없는» 경우는 이것이 아니다.** 프롬프트가 키 셋을 정확히 요구하므로 누락은 계약
    위반이고 다른 표본이 지킬 수 있다 — 그쪽은 재시도가 뜻을 갖는다."""


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
    body = loaded_object(raw, error=ScenarioValidationError)

    # ⛔ 무대만 필수다(설계서 §5). 다른 넷은 비어도 통과한다 — 다섯을 모두 필수로 하면 학습자가
    # 한 축만 모른다고 답해도 생성이 실패하고 그것은 5회 대화를 버리는 일이다.
    category = body.get("category")
    # ⛔ **명시적 `null` 을 다른 거부와 «가른다»** (`TASK-259`) — 그것은 프롬프트가 요구한 답이므로
    # 재시도가 무의미하다. 키 자체가 없는 경우는 여기 들어오지 않는다(계약 위반이고 재시도
    # 대상이다).
    if category is None and "category" in body:
        raise ScenarioNoStage(
            "모델이 무대를 정하지 않았다 (category=null) — 전사문에 축 1(무대)이 없다는 뜻이고 "
            "재시도해도 입력이 같으므로 같은 답이 온다"
        )
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
