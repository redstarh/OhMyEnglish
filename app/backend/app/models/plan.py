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

**엄격함이 스키마 검증에서 끝나지 않는 자리가 셋 있다** — ① 두 단계 도약 ② 지어낸
`pattern_id` ③ 초점에 가장 깊은 재발이 없는 것. 셋 다 **출력만으로는 판정할 수 없어서**
`parse_plan`이 인자를 셋 더 받는다(`current_level`·`allowed_pattern_ids`·
`deepest_pattern_id` — 그 함수의 docstring이 각각의 근거를 소유한다). ①은 h-doc이 경고한
"목표 수준을 현재 수준으로 착각"을 구조로 막는다 — AWS 보고 수준 문형으로 예문을 만들면
첫 세션에서 얼어붙는다. 하향도 허용한다: 상향만 되면 잘못 올라간 수준이 영구히 굳는다
(설계서 §7).

`_json_candidates`의 관용 범위는 **`models/analysis.py`와 글자 그대로 같다** — 원문,
그리고 전체가 코드펜스인 경우 그 본문뿐이다. 산문 중간의 JSON을 긁어내지 않는다.
계약을 지키지 않은 응답은 실패로 보고하는 편이 낫다.
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Literal, get_args
from uuid import UUID

import pydantic

# 001 users.current_level / learning_scenarios.level, 007 session_plans.target_level
# CHECK와 **같은 값역**이다. 여기서 값을 늘리면 그 CHECK들도 함께 고쳐야 한다
# (두 곳이 SoT를 나눠 갖지 않게).
CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]

# `models/analysis.py`의 `ERROR_CATEGORIES = get_args(ErrorCategory)`와 같은 선례 —
# 값역을 두 번 손으로 적으면 갈라질 수 있고, 갈라지면 `_one_step_or_same`의
# `CEFR_LEVELS.index(target)`가 Literal-유효 값에도 가드 없는 `ValueError`를 던진다.
CEFR_LEVELS: tuple[str, ...] = get_args(CefrLevel)

# `models/analysis.py`의 `SuggestedContext`와 같은 선례 — 항목 단위 비공백을 건다.
# 개수 상한은 두지 않는다(발명하지 않는다).
NonBlankText = Annotated[str, pydantic.Field(min_length=1)]


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
    contexts: list[NonBlankText]


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
    notes: list[NonBlankText]

    @pydantic.model_validator(mode="after")
    def _target_level_matches_level_and_instruction(self) -> PlanOutput:
        """`target_level` · `level.target_level` · `instruction.target_level` 셋이 다르면 거부한다.

        셋은 같은 개념("오늘의 목표 수준")이다. `target_level`은 `session_plans`의 컬럼이 되고,
        `level.target_level`은 `users.current_level`을 갱신하며, `instruction.target_level`은
        대화 상대가 실제로 조립해 말하는 지시문의 수준이다.

        ⚠️ **화면도 대화 상대도 `instruction.target_level` 하나를 읽는다** — 컬럼이 아니다
        (`api/results.py`의 `next_plan` → `services/sessions.py`의 `PreparedPlan`, 그리고
        `audio_gateway/nova.py`의 `build_system_prompt`). 그래서 "학습자가 보는 수준과 대화
        상대가 말하는 수준이 갈라진다"는 실패 모드는 **일어날 수 없다.** 셋이 갈라졌을 때
        어긋나는 것은 나머지 둘이고, **그 둘이 이 검증의 이유다**:

        1. **컬럼은 "오늘의 목표 수준"의 저장 기록이다.** 읽히는 값과 갈라지면 실제로 쓰인
           수준과 다른 기록이 그 행에 영구히 남는다 — 사후 분석·보고가 그 기록을 믿는다.
           앱은 이 컬럼을 읽지 않는다: `session_plans`를 읽는 SQL은 `_PREPARED_PLAN_SQL`
           하나이고 `sp.id`·`sp.reason`·`sp.instruction`만 고른다 — `target_level`은 그
           select 목록에 없다.
        2. **`level.target_level`은 다음 세션으로 전파된다.** `process_plan`이 그 값으로
           `users.current_level`을 갱신하므로(`services/plan.py` `_UPDATE_LEVEL_SQL`),
           갈라진 값은 다음 계획의 `Current level:` 입력이자 한 단계 가드
           (`_one_step_or_same`)의 입력이 된다 — 실제로 쓰이지 않은 수준으로 수준 이동이
           기록되고 그 오차가 이어진다.
        """
        levels = {self.target_level, self.level.target_level, self.instruction.target_level}
        if len(levels) > 1:
            raise ValueError(
                f"target_level({self.target_level!r}) != "
                f"level.target_level({self.level.target_level!r}) != "
                f"instruction.target_level({self.instruction.target_level!r})"
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


def parse_plan(
    raw: str,
    *,
    current_level: str,
    allowed_pattern_ids: set[UUID],
    deepest_pattern_id: UUID | None,
) -> PlanOutput:
    """모델 출력 문자열 → 검증된 계획. 실패는 전부 `PlanValidationError`다.

    `current_level`을 인자로 받는 이유: 두 단계 도약 여부는 **출력만으로는 판정할 수
    없다.** JSON으로 읽히는 첫 후보에서 스키마 검증까지 끝낸다 — 스키마 검증 실패는
    거기서 확정 거부다(`parse_analysis`와 같은 비대칭: JSON 디코드 실패만 다음 후보로
    넘어간다). 필드가 틀린 JSON을 펜스 제거 후 재시도해도 같은 결과이고, 그 사이 다른
    후보가 우연히 통과하면 어느 응답을 저장했는지 알 수 없게 된다.

    `allowed_pattern_ids`가 같은 이유로 인자다 — **어떤 id 가 실재하는지는 출력만으로
    판정할 수 없다.** 모델이 형식만 맞는 UUID 를 지어내면 `pattern_id: UUID`도 통과하고
    `session_plans.focus_pattern_ids uuid[]`에는 **FK 가 없어** DB 도 통과한다. 그러면
    존재하지 않는 패턴 id 가 조용히 저장되고 초점·복습 조회가 영구히 어긋난다 — **실패보다
    나쁘다**(`InvalidTimezoneError` docstring 의 "틀린 계획보다 실패가 낫다"와 같은 원칙).
    집합을 아는 것은 호출자(`services/plan.py`)이고 그 값은 **프롬프트에 실린 두 목록**과
    같아야 한다: `{r.pattern_id for r in due_reviews} | {m.pattern_id for m in chronic}`.
    비어 있으면 어떤 초점도 통과하지 못한다 — 그래서 호출자가 그 경우 Claude 를 부르지
    않는다(콜드스타트).

    `deepest_pattern_id`도 같은 분업이다 — **초점이 "가장 깊은 재발"인지는 출력만으로 판정할
    수 없다.** 요구사항 AC11-2는 *"가장 깊은 재발이 초점이 되고"*를 요구하는데 이 함수가
    강제하던 것은 개수·비어 있지 않음·값역뿐이었고, 그래서 실물 1건이 우연히 최다 빈도를
    고른 것과 **재현성**을 구분할 수 없었다(판정이 완료 → 부분으로 되돌아간 이유:
    `docs/design/2026-09-06-review-outcomes.md` §2). 순위를 내는 것은 만성 목록을 소유한
    `services/chronic.py`의 `deepest_recurrence`이고, 여기서는 **그 결과와 초점을 비교하는
    판정만** 한다. 규칙 전문은 그 함수의 docstring이 소유한다.

    ⚠️ **`None`은 "만성 목록이 비었다"는 뜻이고 그때 이 규칙을 적용하지 않는다.** 최상위가
    존재하지 않으므로 강제할 대상이 없다 — 콜드스타트에서 계획 생성이 막히면 안 된다.
    `allowed_pattern_ids`가 비는 것과는 다른 상황이다: 복습 예정만 있는 사용자는 허용 집합이
    비지 않지만(`DueReview`에는 `frequency`가 없어) 깊이 축을 만들 수 없다.

    **키워드 인자를 필수로 둔다.** 기본값 `None`("검사 안 함")을 주면 잊은 호출자가 가드
    없이 지나가고, 그 실패는 조용해서 테스트로도 안 드러난다. **`deepest_pattern_id`에
    기본값을 주지 않는 이유가 바로 그것이다** — 이 인자는 `None`이 유효한 값이므로 기본값을
    주면 잊은 호출자와 "만성 목록이 빈 호출자"가 **구분되지 않는다.**
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
        # ⚠️ 초점 **전 항목**을 본다. 첫 항목만 검사하면 두 번째에 지어낸 id 를 실어도
        # 통과하고, 그 값이 그대로 `focus_pattern_ids`에 저장된다.
        invented = [
            item.pattern_id for item in result.focus if item.pattern_id not in allowed_pattern_ids
        ]
        if invented:
            raise PlanValidationError(
                "focus references pattern_id that was not offered in the prompt: "
                + ", ".join(str(pattern_id) for pattern_id in invented)
            )
        # AC11-2 — 초점 **1~2개 중 최소 하나**가 가장 깊은 재발이어야 한다. ⚠️ 첫 항목만
        # 보지 않는다: 요구사항은 "초점이 그것을 포함한다"이고 "첫 초점이 그것이다"가 아니라
        # 둘째 자리에 실은 정당한 계획을 거부하게 된다. 허용 집합 가드보다 **뒤에** 둔다 —
        # 지어낸 id 는 더 근본적인 위반(존재하지 않는 패턴)이라 그쪽 사유가 먼저 보고돼야 한다.
        if deepest_pattern_id is not None and all(
            item.pattern_id != deepest_pattern_id for item in result.focus
        ):
            raise PlanValidationError(
                "focus must include the deepest recurrence "
                f"{deepest_pattern_id}, but it lists "
                + ", ".join(str(item.pattern_id) for item in result.focus)
            )
        if not _one_step_or_same(current_level, result.level.target_level):
            raise PlanValidationError(
                f"level jump from {current_level!r} to {result.level.target_level!r} "
                "skips more than one CEFR step"
            )
        return result
    raise PlanValidationError(f"plan response was not JSON: {raw[:200]!r}")
