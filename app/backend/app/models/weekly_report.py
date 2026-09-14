"""주간 리포트 판단(`insights`)의 파서와 jsonb 모양 (`TASK-26`).

설계: `docs/design/2026-09-14-weekly-report-design.md` §3.

⛔ **모델에게 점수·등급을 묻지 않는다.** 파서가 그 키를 버리는 것만으로는 부족하다 — 프롬프트가
요구하지 않아야 하고 출력 규격에 그 키가 **없어야** 한다. 이 파일은 그 둘째 겹(정의되지 않은 키를
거부한다)을 맡고, 첫째 겹은 `services/weekly_report.py` 의 출력 규격이 맡는다.
근거: R13-5 의 톤 계약 · PRD §15.3 의 비범위 · R11-8 — 판단은 모델의 것이지만 **점수는 요구가
아니다**.

⚠️ **`_json_candidates` 를 private 로 가져오는 것이 의도다** — 사용자 결정 86 이 그 함수를 **둘로
유지**하고 동일성을 테스트로 못박기로 했으므로 판을 늘리지 않는다. `models/session_summary.py` 가
같은 이유로 같은 import 를 쓴다(그 파일의 주석이 근거를 갖는다).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.models.plan import _json_candidates

# 항목 상한. ⚠️ **발명값이다** — PRD 가 개수를 정하지 않았다. 근거: 한 주를 되짚는 화면이 목록으로
# 덮이지 않을 크기이고, 총평이 같은 이유로 상한을 뒀다(`MAX_POINTS`).
MAX_INSIGHT_POINTS = 3

# 「만들었고 담을 것이 없었다」의 값. ⛔ `{}` 와 **다른 뜻**이다 — 그것은 「아직 만들지 않았다」다.
# 그 구별을 값의 **모양**에 두는 것이 총평이 세운 규약이고, 화면·API 까지 그 구별이 도달한다.
EMPTY_INSIGHTS: dict[str, object] = {"improving": [], "next_scenarios": []}


class WeeklyValidationError(ValueError):
    """모델 응답이 규격을 벗어났다. ⛔ 반쯤 검증된 판단을 저장하지 않는다."""


@dataclass(frozen=True, slots=True)
class WeeklyInsights:
    """모델이 내린 판단 둘. **사실은 담지 않는다** — 그것은 `WeekFacts` 의 것이다.

    ⛔ 점수·등급·달성률을 담을 자리가 **구조에 없다** — 값역이 계약이라는 이 리포의 방식이다.
    """

    improving: tuple[str, ...]
    next_scenarios: tuple[str, ...]


_ALLOWED_KEYS = frozenset({"improving", "next_scenarios"})


def _loaded(raw: str) -> dict[str, Any]:
    last_error: json.JSONDecodeError | None = None
    for candidate in _json_candidates(raw):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as error:
            last_error = error
            continue
        if not isinstance(parsed, dict):
            raise WeeklyValidationError(f"JSON 최상위가 객체가 아니다: {type(parsed).__name__}")
        return parsed
    raise WeeklyValidationError(f"JSON 으로 읽을 수 없다: {last_error}")


def _sentences(body: dict[str, Any], key: str, *, max_points: int) -> tuple[str, ...]:
    """문장 배열 하나를 읽는다. 없으면 빈 배열이고, 규격을 벗어나면 거부한다.

    ⚠️ **빈 배열을 허용한다** — 그 주에 개선이 없었거나 추천할 무대가 없는 것은 정상이고, 모델이
    없는 것을 지어내는 것보다 낫다(프롬프트가 그렇게 요구한다).
    """
    value = body.get(key, [])
    if not isinstance(value, list):
        raise WeeklyValidationError(f"{key} 가 배열이 아니다: {type(value).__name__}")
    if len(value) > max_points:
        raise WeeklyValidationError(f"{key} 가 상한 {max_points} 를 넘었다: {len(value)}")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise WeeklyValidationError(f"{key} 에 빈 문장이나 문자열이 아닌 항목이 있다")
    return tuple(item.strip() for item in value)


def parse_weekly_insights(raw: str, *, max_points: int) -> WeeklyInsights:
    """모델 응답을 판단 둘로 읽는다.

    ⛔ **정의되지 않은 키를 거부한다** — 그것이 점수·등급이 들어오는 길이고, 값역이 계약이라는
    규약을 파서가 지키는 자리다. 최상위만 막으면 충분한 이유: 두 값이 **문장 배열**이라 항목 안에
    키가 없다(총평은 항목이 객체라 양쪽을 막아야 했다).
    """
    body = _loaded(raw)
    unknown = sorted(set(body) - _ALLOWED_KEYS)
    if unknown:
        raise WeeklyValidationError(f"정의되지 않은 키가 있다: {unknown}")
    return WeeklyInsights(
        improving=_sentences(body, "improving", max_points=max_points),
        next_scenarios=_sentences(body, "next_scenarios", max_points=max_points),
    )


def insights_payload(insights: WeeklyInsights) -> dict[str, object]:
    """`weekly_reports.insights` 에 넣을 모양. 키 집합이 `EMPTY_INSIGHTS` 와 같아야 한다.

    ⚠️ 그 동일성이 계약이다 — 화면이 두 경로(모델이 만든 것 · 담을 것이 없었던 것)를 같은 모양으로
    읽는다.
    """
    return {
        "improving": list(insights.improving),
        "next_scenarios": list(insights.next_scenarios),
    }


__all__ = [
    "EMPTY_INSIGHTS",
    "MAX_INSIGHT_POINTS",
    "WeeklyInsights",
    "WeeklyValidationError",
    "insights_payload",
    "parse_weekly_insights",
]
