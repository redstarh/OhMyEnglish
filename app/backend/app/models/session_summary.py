"""세션 총평의 파서와 jsonb 모양 (`TASK-62`).

설계서는 `docs/design/2026-09-13-session-summary-design.md` 다.

⛔ **jsonb 의 모양은 이 모듈이 정본이다** — 쓰는 쪽(`services/session_summary`)과 읽는 쪽
(`services/results`)이 각자 키를 적으면 두 곳이 갈라지고 화면이 조용히 빈다. 키 이름 리터럴이
이 파일에만 있는 것이 그 방어다.

⛔ **점수·등급 키를 두지 않는다.** `R11-8` 이 *"만성 약점 판정의 임계값을 제품이 발명하지 않는다"*
이고 `R13-5` 가 *"만성 여부 · 개선 여부 · 점수는 이 요약의 것이 아님"* 이다. ⚠️ 그 두 요구가 이
총평을 **금지하지는 않는다** — `R11-8` 이 판단 주체로 지목한 것이 **학습 분석 Agent** 이고
`nova-sonic-claude-architecture.md` §4.3 이 이 job 을 그 Agent 로 지정했다. 금지된 것은 제품이 만든
임계값·숫자이고 Agent 가 쓰는 문장은 허용 쪽이다. ⇒ 그래서 **값역을 좁혀 구조가 그 경계를
강제한다** — 문면으로만 막으면 새 키가 조용히 들어온다.

⚠️ **담는 것이 둘인 것은 유도된 것이고 발명이 아니다**(설계서 §2.1). §4.3 의 한 행이 세 항목을
묶어 말하는데 「다음 세션 계획」은 `session_plans` 가, `R11-10` 의 관찰 기록은 `learner_notes` 가
이미 소유한다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, cast

# ⚠️ private 이름을 가져오는 것이 의도다 — 사용자 결정 86 이 이 함수를 **둘로 유지**하고 동일성을
# 테스트로 못박기로 했으므로 판을 늘리지 않는다. 복제하면 파서들의 관대함이 갈라지고 한쪽이 조용히
# 낡는다. ⛔ 공개 API 로 승격하지 않은 이유: `models/plan.py` 가 그 함수의 경계(한 번의
# 재시도까지)를 docstring 으로 소유하고 있고 옮기면 그 근거가 흩어진다.
from app.models.plan import _json_candidates

# 요구가 약점을 *"1~2개"* 로 지정했다(`nova-sonic-claude-architecture.md` §4.3). 잘한 점에도 같은
# 상한을 준다 — 길어지면 총평이 아니라 목록이 되고 화면이 결과 요약을 잃는다.
MAX_POINTS = 2

_WENT_WELL = "went_well"
_WEAK_POINTS = "weak_points"
_POINT = "point"
_QUOTE = "quote"
_ALLOWED_TOP = frozenset({_WENT_WELL, _WEAK_POINTS})
_ALLOWED_POINT = frozenset({_POINT, _QUOTE})

# 「만들었고 담을 것이 없었다」의 값. ⛔ `{}` 와 **다른 뜻**이다 — 그것은 「아직 만들지 않았다」다.
# `R13-7` 이 일일 요약에서 세운 구별(*"분석이 돌고 0건"* ≠ *"학습이 없었다"*)을 같은 모양으로
# 잇는다.
EMPTY_SUMMARY: dict[str, object] = {_WENT_WELL: [], _WEAK_POINTS: []}


class SummaryValidationError(ValueError):
    """모델 출력이 총평의 계약을 지키지 못했다. 실패는 전부 이 하나로 수렴한다."""


@dataclass(frozen=True, slots=True)
class WeakPoint:
    """약점 하나. `quote` 는 **부차**이고 학습자가 말한 영어 원문 그대로다."""

    point: str
    quote: str | None


@dataclass(frozen=True, slots=True)
class SummaryDraft:
    """검증을 통과한 총평 초안. ⛔ 점수·등급 필드가 **없는 것이 계약**이다."""

    went_well: tuple[str, ...]
    weak_points: tuple[WeakPoint, ...]


def _loaded(raw: str) -> dict[str, Any]:
    last_error: json.JSONDecodeError | None = None
    for candidate in _json_candidates(raw):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError as error:
            last_error = error
            continue
        if not isinstance(parsed, dict):
            raise SummaryValidationError(f"JSON 최상위가 객체가 아니다: {type(parsed).__name__}")
        return parsed
    raise SummaryValidationError(f"JSON 으로 읽을 수 없다: {last_error}")


def _reject_unknown(keys: Any, allowed: frozenset[str], where: str) -> None:
    """정의되지 않은 키를 거부한다 — 최상위와 항목 «양쪽»에 같은 방어를 둔다.

    ⛔ 최상위만 막으면 판정이 항목 안으로 들어온다(`{"point": …, "severity": "high"}`).
    """
    unknown = sorted(set(keys) - allowed)
    if unknown:
        raise SummaryValidationError(f"{where} 에 정의되지 않은 키가 있다: {unknown}")


def _sentences(body: dict[str, Any], key: str, *, max_points: int) -> tuple[str, ...]:
    value = body.get(key)
    if not isinstance(value, list):
        raise SummaryValidationError(f"{key} 가 배열이 아니다: {value!r}")
    if len(value) > max_points:
        raise SummaryValidationError(f"{key} 가 {len(value)}개다 — 상한 {max_points}개")
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise SummaryValidationError(f"{key} 에 빈 항목이 있다: {item!r}")
        out.append(item.strip())
    return tuple(out)


def parse_summary(raw: str, *, max_points: int) -> SummaryDraft:
    """모델 출력 문자열 → 검증된 총평 초안. 실패는 전부 `SummaryValidationError` 다.

    거부 순서는 **싼 것부터**다: JSON → 정의되지 않은 키 → 잘한 점 → 약점. 앞에서 걸리면 뒤를
    재지 않으므로 실패 메시지가 **가장 근본적인 사유**를 가리킨다.

    ⛔ **상한·하한은 이 함수의 계약이고 모델 출력에만 걸린다.** 발화 0건 경로는 파서를 지나가지
    않고 `EMPTY_SUMMARY` 를 직접 쓴다(설계서 §4) — 그 둘은 모순이 아니다. 즉 `weak_points` 가 비어
    있을 수 있는 경로는 정확히 하나이고 그것은 모델이 만든 값이 아니다.

    ⚠️ `max_points` 를 인자로 받는다 — 이 모듈이 상수를 갖지만 그것을 **읽는 것은 호출자의 일**이다.
    그러지 않으면 테스트가 상한 경계를 주입할 자리가 없어진다.
    """
    body = _loaded(raw)
    _reject_unknown(body, _ALLOWED_TOP, "최상위")

    went_well = _sentences(body, _WENT_WELL, max_points=max_points)

    raw_points = body.get(_WEAK_POINTS)
    if not isinstance(raw_points, list) or not raw_points:
        raise SummaryValidationError(f"{_WEAK_POINTS} 가 비었다: {raw_points!r}")
    if len(raw_points) > max_points:
        raise SummaryValidationError(
            f"{_WEAK_POINTS} 가 {len(raw_points)}개다 — 상한 {max_points}개"
        )

    points: list[WeakPoint] = []
    for item in raw_points:
        if not isinstance(item, dict):
            raise SummaryValidationError(f"{_WEAK_POINTS} 항목이 객체가 아니다: {item!r}")
        _reject_unknown(item, _ALLOWED_POINT, f"{_WEAK_POINTS} 항목")
        point = item.get(_POINT)
        if not isinstance(point, str) or not point.strip():
            raise SummaryValidationError(f"{_POINT} 가 비었다: {point!r}")
        quote = item.get(_QUOTE)
        if quote is not None and (not isinstance(quote, str) or not quote.strip()):
            raise SummaryValidationError(f"{_QUOTE} 가 비었다: {quote!r}")
        points.append(
            WeakPoint(point=point.strip(), quote=quote.strip() if isinstance(quote, str) else None)
        )

    return SummaryDraft(went_well=went_well, weak_points=tuple(points))


def summary_payload(draft: SummaryDraft) -> dict[str, object]:
    """초안 → `summary` 컬럼에 넣을 dict. ⛔ 키 이름의 정본이 여기 하나다.

    ⚠️ `quote` 가 없으면 **키를 넣지 않는다** — `null` 을 넣으면 읽는 쪽이 「없음」과 「빈 문자열」을
    다시 갈라야 한다.
    """
    return {
        _WENT_WELL: list(draft.went_well),
        _WEAK_POINTS: [
            {_POINT: item.point, **({_QUOTE: item.quote} if item.quote else {})}
            for item in draft.weak_points
        ],
    }


def summary_from_row(value: object) -> dict[str, object] | None:
    """저장된 `summary` 를 화면에 낼 모양으로 돌려준다. 없으면 `None`.

    ⛔ **읽는 쪽에서 재검증하지 않는다** — 저장된 값이 계약을 어겼다고 결과 화면을 죽이면 총평
    하나 때문에 세션 결과 전체를 잃는다. 두 키의 **존재만** 본다.
    ⚠️ `None` 을 돌려주는 것이 `{}`(아직 없음)와 `EMPTY_SUMMARY`(담을 것이 없었음)를 가르는 자리다 —
    그 구별이 값의 모양에 있으므로 호출자가 job 상태를 조회하지 않아도 된다.
    """
    if not isinstance(value, dict):
        return None
    # ⚠️ `isinstance` 만으로 좁히면 `dict[Unknown, Unknown]` 이 되어 **`str` 키를 거부한다**
    # (`H-AV` 가 그 진단을 이름으로 적어 뒀다). 외부 JSON 을 받는 자리는 `cast` 로 좁힌다.
    body = cast(dict[str, Any], value)
    if _WENT_WELL not in body or _WEAK_POINTS not in body:
        return None
    return {_WENT_WELL: body[_WENT_WELL], _WEAK_POINTS: body[_WEAK_POINTS]}
