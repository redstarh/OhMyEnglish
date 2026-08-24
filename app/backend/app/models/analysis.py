"""Claude 분석 출력의 검증 스키마 (설계서 §5.6, AC W7).

Claude의 응답은 **신뢰할 수 없는 외부 입력**이다. 이 경계에서 좁히지 않으면
잘못된 값이 `error_patterns.category` / `error_occurrences.severity` /
`confidence numeric(3,2) check between 0 and 1` CHECK에 부딪혀 결과 저장
트랜잭션 중간에 터진다 — 그 발화의 분석 결과가 통째로 사라지고, 실패 이유는
"DB 제약 위반"으로 뭉개져 무엇이 잘못됐는지 알 수 없게 된다. 그래서:

* `Literal` + `ge/le`로 001 스키마의 CHECK와 **같은 집합**만 통과시킨다.
  코드값이 두 곳에 있으므로 `ERROR_CATEGORIES`는 Literal에서 파생시켜 모듈
  안에서 값이 갈라지는 일을 없앤다 (스키마와의 일치는 단위 테스트가 지킨다).
* `extra="forbid"` — 모르는 필드는 프롬프트 계약이 어긋났다는 신호다. 조용히
  버리면 스키마 변경을 놓친 채 데이터가 반쯤만 저장된다.
* `str_strip_whitespace=True` — 앞뒤 공백은 경계에서 깎는다. `pattern_key`에 붙은
  공백 하나가 "다른 key"로 취급되면 병합(§7 Contract)이 깨지고, `original_span`에
  붙은 공백은 그대로 사용자 화면에 나간다. 공백만으로 이루어진 값은 깎인 뒤
  `min_length=1`에 걸려 거부된다.
* 파싱·검증 실패는 전부 `AnalysisValidationError` **하나로** 수렴시킨다.
  호출자(`services.analysis.process_analysis`)는 이 예외 하나만 잡아
  `fail_or_retry`로 보내면 되고, pydantic 예외 타입에 의존하지 않는다.

`pattern_key`는 여기서 **형식만** 본다(빈 문자열 거부). `^{category}_...`
형식 강제는 **신규 key에만** 적용되는 규칙이라(기존 key 재사용은 형식 무관 허용
— §5.6) 사용자의 기존 key 목록을 아는 저장 단계의 몫이다. 이 모듈은 그 판정에
쓰이는 술어 `is_valid_new_pattern_key`만 제공한다.
"""

from __future__ import annotations

import json
import re
from typing import Literal, get_args

import pydantic

ErrorCategory = Literal[
    "verb_tense",
    "article",
    "preposition",
    "word_order",
    "verb_form",
    "business_expression",
    "pronunciation_intonation",
]
Severity = Literal["low", "medium", "high"]

# Literal에서 파생 — 코드값을 두 번 적지 않는다 (001 CHECK와의 일치는 테스트가 지킨다).
ERROR_CATEGORIES: tuple[ErrorCategory, ...] = get_args(ErrorCategory)
SEVERITIES: tuple[Severity, ...] = get_args(Severity)


class AnalysisValidationError(ValueError):
    """Claude 응답이 계약을 벗어났다 — 이 발화의 분석은 실패로 처리한다."""


class ErrorFinding(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    category: ErrorCategory
    pattern_key: str = pydantic.Field(min_length=1)
    target_form: str = pydantic.Field(min_length=1)
    original_span: str = pydantic.Field(min_length=1)
    correction: str = pydantic.Field(min_length=1)
    explanation: str = pydantic.Field(min_length=1)
    severity: Severity
    confidence: float = pydantic.Field(ge=0, le=1)


class AnalysisResult(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    findings: list[ErrorFinding]


# ```json ... ``` / ``` ... ``` 로 감싼 응답. 언어 태그는 있어도 없어도 된다.
_FENCED = re.compile(r"\A\s*```[^\n`]*\n?(?P<body>.*?)\n?\s*```\s*\Z", re.DOTALL)

_NEW_KEY_SUFFIX = r"[a-z0-9_]+"


def is_valid_new_pattern_key(category: str, pattern_key: str) -> bool:
    """신규 `pattern_key`가 `^{category}_[a-z0-9_]+$` 형식인지 (§5.6 발명 규칙).

    기존 key 재사용에는 적용하지 않는다 — 근거 문서의 예시
    (`past_tense_in_work_update`)는 접두 형식이 아니고, 재사용 우선 규칙이
    있어 실질 충돌이 없다. 이 술어는 "새로 만드는" key에만 쓴다.
    """
    return re.fullmatch(rf"{re.escape(category)}_{_NEW_KEY_SUFFIX}", pattern_key) is not None


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


def parse_analysis(raw: str) -> AnalysisResult:
    """Claude 원문 응답을 검증된 `AnalysisResult`로 바꾼다.

    JSON으로 읽히는 첫 후보에서 스키마 검증까지 끝낸다. 스키마 검증 실패는
    거기서 확정 거부다 — 필드가 틀린 JSON을 "펜스 제거 후 재시도"해도 같은
    결과이고, 그 사이에 다른 후보가 우연히 통과하면 어느 응답을 저장했는지
    알 수 없게 된다.

    빈 `findings`(오류 0건)는 정상 결과다 — 검증 거부와 반드시 구분된다.
    """
    for candidate in _json_candidates(raw):
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        try:
            return AnalysisResult.model_validate(payload)
        except pydantic.ValidationError as exc:
            raise AnalysisValidationError(f"analysis response failed validation: {exc}") from exc
    raise AnalysisValidationError(f"analysis response was not JSON: {raw[:200]!r}")
