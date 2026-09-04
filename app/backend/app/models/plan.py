"""Claude 계획 출력의 검증 스키마 (설계서 §9 Failure, AS5·AS7).

`models/analysis.py`와 같은 자리를 차지한다 — Claude의 계획 출력도 **신뢰할 수 없는 외부
입력**이다. 이 경계에서 좁히지 않으면 `session_plans`의 CHECK(007 마이그레이션:
`focus_pattern_ids` 1~2개 · `questions` 3~5개 · `reason` 공백 금지 · `target_level` 값역)에
부딪혀 저장 트랜잭션 중간에 터진다. AS5는 **저장 전에** 거부해 반쯤 검증된 계획을 쓰지
않는다 — 그래서:

* `Literal` + 길이 제약으로 007 CHECK와 **같은 집합**만 통과시킨다. `CEFR_LEVELS`는
  001·007의 CHECK와 같은 값역이다 — 여기서 값을 늘리면 그 두 CHECK도 함께 고쳐야 한다.
* `extra="forbid"` — 모르는 필드는 프롬프트 계약이 어긋났다는 신호다.
* `str_strip_whitespace=True` — 앞뒤 공백은 경계에서 깎는다. 공백만으로 이루어진
  `reason`은 깎인 뒤 `min_length=1`에 걸려 거부된다(`session_plans_reason_not_blank`와
  같은 판정을 pydantic에서도 먼저 한다 — 이중 방어가 중복이 아닌 이유는 아래 참조).
* 파싱·검증 실패는 전부 `PlanValidationError` **하나로** 수렴시킨다. 호출자(워커)는
  이 예외만 잡아 job을 `last_error`와 함께 실패시키고 **계획을 저장하지 않는다.**

**초점 패턴을 나타내는 타입이 둘인 것은 의도된 것이다.** `PlanOutput.focus`는
`FocusPattern`(`pattern_id` 포함) — 그 id가 `session_plans.focus_pattern_ids`에 저장되므로
반드시 있어야 한다. `SessionInstruction.focus`는 `InstructionFocus`(`pattern_id` 없음) —
이 값은 대화 상대의 지시문 문장으로 조립되고, 대화 상대는 UUID를 쓸 일이 없다.

`questions`·`focus` 길이와 `reason` 공백은 pydantic에서도 막고 DB CHECK에서도 막는다.
이중 방어가 중복이 아닌 이유: pydantic은 **읽을 수 있는 오류**를 주고 DB CHECK는
**다른 경로로 들어온 쓰기**까지 막는다(백필 스크립트 등).

**엄격함이 스키마 검증에서 끝나지 않는 자리가 하나 있다** — 목표 수준이 현재 수준에서
두 단계 이상 도약했는지는 출력만으로 판정할 수 없다(`parse_plan`이 `current_level`을
인자로 받는 이유). h-doc이 경고한 "목표 수준을 현재 수준으로 착각"을 구조로 막는다
— AWS 보고 수준 문형으로 예문을 만들면 첫 세션에서 얼어붙는다. 하향도 허용한다:
상향만 되면 잘못 올라간 수준이 영구히 굳는다(설계서 §7).

`_json_candidates`의 관용 범위는 **`models/analysis.py`와 글자 그대로 같다** — 원문,
그리고 전체가 코드펜스인 경우 그 본문뿐이다. 산문 중간의 JSON을 긁어내지 않는다.
계약을 지키지 않은 응답은 실패로 보고하는 편이 낫다.
"""

from __future__ import annotations

import json
import re
from typing import Literal
from uuid import UUID

import pydantic

# 001 users.current_level / learning_scenarios.level, 007 session_plans.target_level
# CHECK와 **같은 값역**이다. 여기서 값을 늘리면 그 CHECK들도 함께 고쳐야 한다
# (두 곳이 SoT를 나눠 갖지 않게).
CEFR_LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class PlanValidationError(ValueError):
    """Claude 계획 출력이 계약을 지키지 않았다.

    `AnalysisValidationError`와 같은 자리를 차지한다 — 워커가 이것을 잡아 job을
    `last_error`와 함께 실패시키고 **계획을 저장하지 않는다**(설계서 §9 Failure).
    """


class FocusPattern(pydantic.BaseModel):
    """`PlanOutput.focus`의 항목 1개.

    `pattern_id`가 `session_plans.focus_pattern_ids`에 저장된다.
    """

    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    pattern_id: UUID
    pattern_key: str = pydantic.Field(min_length=1)
    target_form: str = pydantic.Field(min_length=1)


class PlanQuestion(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    prompt: str = pydantic.Field(min_length=1)
    context: str = pydantic.Field(min_length=1)


class InstructionFocus(pydantic.BaseModel):
    """`SessionInstruction.focus`의 항목 1개 — `pattern_id`가 없다.

    대화 상대의 지시문 문장으로 조립되는 값이라 UUID를 쓸 일이 없다. `FocusPattern`을
    재사용하면 `extra="forbid"` 규약상 `pattern_id`가 필수가 되어 이 자리에 오는 응답이
    거부된다 — 그래서 별도 타입이다.
    """

    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    pattern_key: str = pydantic.Field(min_length=1)
    target_form: str = pydantic.Field(min_length=1)


class SessionInstruction(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_level: CefrLevel
    focus: list[InstructionFocus] = pydantic.Field(min_length=1, max_length=2)
    sentence_length: str = pydantic.Field(min_length=1)
    hint_timing: str = pydantic.Field(min_length=1)
    contexts: list[str]


class LevelDecision(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    action: Literal["keep", "up", "down"]
    target_level: CefrLevel
    reason: str = pydantic.Field(min_length=1)


class PlanOutput(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    # 초점 패턴 1~2개 (PRD.md:188 R11-2 · agent-system-prompt.md:19).
    focus: list[FocusPattern] = pydantic.Field(min_length=1, max_length=2)
    # 질문 3~5개 (PRD.md:188 R11-2).
    questions: list[PlanQuestion] = pydantic.Field(min_length=3, max_length=5)
    target_level: CefrLevel
    # not blank: 이유 없는 추천은 사용자가 판단을 검증할 수 없다(PRD.md:189 R11-3).
    reason: str = pydantic.Field(min_length=1)
    instruction: SessionInstruction
    level: LevelDecision
    notes: list[str]

    @pydantic.model_validator(mode="after")
    def _target_level_matches_level_decision(self) -> PlanOutput:
        """계획의 난이도(`target_level`)와 수준 판단(`level.target_level`)이 어긋나면 거부한다.

        두 값이 다르면 어느 것이 오늘의 목표인지 알 수 없다 — 저장하면 `session_plans`
        1행과 `instruction`이 서로 다른 수준을 가리키는 상태가 영구히 남는다.
        """
        if self.target_level != self.level.target_level:
            raise ValueError(
                f"target_level({self.target_level!r}) != "
                f"level.target_level({self.level.target_level!r})"
            )
        return self


# ```json ... ``` / ``` ... ``` 로 감싼 응답. 언어 태그는 있어도 없어도 된다.
# `models/analysis.py`의 `_FENCED`와 글자 그대로 같은 정규식이다 — 관용의 범위를
# 넓히지 않는다(모듈 docstring).
_FENCED = re.compile(r"\A\s*```[^\n`]*\n?(?P<body>.*?)\n?\s*```\s*\Z", re.DOTALL)


def _json_candidates(raw: str) -> list[str]:
    """원문, 그리고 코드펜스를 벗긴 본문 — 이 순서로 JSON 파싱을 시도한다.

    프롬프트가 "코드펜스 없이 JSON만"을 요구하지만 LLM은 종종 펜스를 붙인다.
    한 번의 펜스 제거 재시도로 흡수하고, 그 이상(산문 중간의 JSON 추출 등)은
    하지 않는다 — 계약을 지키지 않은 응답은 실패로 보고하는 편이 낫다.
    """
    candidates = [raw]
    fenced = _FENCED.match(raw)
    if fenced is not None:
        candidates.append(fenced.group("body"))
    return candidates


def _one_step_or_same(current: str, target: str) -> bool:
    """수준 이동이 한 칸 이내인지. 두 칸 도약을 **구조로** 막는다 (설계서 §7).

    h-doc이 경고한 "목표 수준을 현재 수준으로 착각"이 이 자리에서 일어난다 —
    AWS 보고 수준 문형으로 예문을 만들면 첫 세션에서 얼어붙는다.
    """
    return abs(CEFR_LEVELS.index(target) - CEFR_LEVELS.index(current)) <= 1


def parse_plan(raw: str, *, current_level: str) -> PlanOutput:
    """모델 출력 문자열 → 검증된 계획. 실패는 전부 `PlanValidationError`다.

    `current_level`을 인자로 받는 이유: 두 단계 도약 여부는 **출력만으로는 판정할 수
    없다.** JSON으로 읽히는 첫 후보에서 스키마 검증까지 끝낸다 — 스키마 검증 실패는
    거기서 확정 거부다(`parse_analysis`와 같은 비대칭: JSON 디코드 실패만 다음 후보로
    넘어간다). 필드가 틀린 JSON을 펜스 제거 후 재시도해도 같은 결과이고, 그 사이 다른
    후보가 우연히 통과하면 어느 응답을 저장했는지 알 수 없게 된다.
    """
    if current_level not in CEFR_LEVELS:
        raise PlanValidationError(f"unknown current_level: {current_level!r}")

    for candidate in _json_candidates(raw):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        try:
            result = PlanOutput.model_validate(payload)
        except pydantic.ValidationError as exc:
            raise PlanValidationError(f"plan response failed validation: {exc}") from exc
        if not _one_step_or_same(current_level, result.level.target_level):
            raise PlanValidationError(
                f"level jump from {current_level!r} to {result.level.target_level!r} "
                "skips more than one CEFR step"
            )
        return result
    raise PlanValidationError(f"plan response was not JSON: {raw[:200]!r}")
