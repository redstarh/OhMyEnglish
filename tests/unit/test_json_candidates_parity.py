"""`models/plan.py` 와 `models/analysis.py` 의 `_json_candidates` 가 «같은 관대함»인지 잰다.

⛔ **`plan.py` 가 그 동일성을 문장으로 주장한다** — *"`_json_candidates`의 관용 범위는
**`models/analysis.py`와 글자 그대로 같다**"*. ⚠️ **그런데 그것을 재는 축이 없었다**
(`TASK-132` · 2026-09-12 에 세션 `ohmyenglish-19` 가 `grep _json_candidates tests/` 0건으로
확인했다). ⇒ 누가 한쪽의 관용 범위를 넓히면 그 문장이 **조용히 거짓**이 되고 두 파서가 다른
관대함을 갖는다.

⛔ **소스 문자열을 비교하지 않는다.** 주석이 달라도 동작은 같을 수 있고 그 반대도 가능하다 —
재는 것은 **출력**이다.

⚠️ 이 파일은 그 동일성을 «고정»하지 않는다 — 하나로 합칠지 둘로 둘지는 `TASK-132` AC#1 의
결정이다. 그때까지 **주장이 참인 동안 참임을 지키는 것**이 이 파일의 몫이다.
"""

from __future__ import annotations

from collections.abc import Callable

from app.models.analysis import _json_candidates as analysis_candidates
from app.models.plan import _json_candidates as plan_candidates

# 두 구현이 갈릴 수 있는 자리를 고른 표본이다. ⛔ 「펜스 있음·없음」 둘만으로는 부족하다 —
# 그 둘은 어떤 구현이든 같게 내기 쉽고, 갈리는 곳은 **경계**다(언어 태그·앞뒤 공백·중첩·산문 혼합).
_SAMPLES: tuple[str, ...] = (
    '{"a": 1}',
    '```json\n{"a": 1}\n```',
    '```\n{"a": 1}\n```',
    '   ```json\n{"a": 1}\n```   ',
    '```JSON\n{"a": 1}\n```',
    '앞말 ```json\n{"a": 1}\n``` 뒷말',  # 전체가 펜스가 아니다 — 벗기지 않아야 한다
    '```json\n{"a": 1}\n```\n```json\n{"b": 2}\n```',  # 펜스 둘
    "",
    "   ",
    "not json at all",
    '{"a": "```"}',  # 값 안의 펜스 문자
    "```\n```",
    "```json\n\n```",
)


def _disagreements(
    left: Callable[[str], list[str]], right: Callable[[str], list[str]]
) -> list[str]:
    """두 구현이 다른 결과를 내는 표본을 돌려준다. 빈 목록이면 동일하다."""
    return [sample for sample in _SAMPLES if left(sample) != right(sample)]


def test_the_two_implementations_agree_on_every_sample() -> None:
    """⛔ `plan.py` 의 주장이 참인지 잰다 — 문장이 아니라 출력으로."""
    diff = _disagreements(plan_candidates, analysis_candidates)
    assert diff == [], (
        f"두 `_json_candidates` 가 갈렸다: {diff!r} — `models/plan.py` 의 "
        "「글자 그대로 같다」 문장이 거짓이 됐다(`TASK-132`)"
    )


def test_the_parity_check_can_actually_fail() -> None:
    """⛔ 판별력 — 관대함을 «넓힌» 변종을 넣으면 위 검사가 그것을 잡는다.

    이 단정이 없으면 `test_the_two_implementations_agree_on_every_sample` 이 **늘 참인
    검사**일 수 있다(표본이 둘 다 같게 내는 것만 골랐을 경우). 여기서 일부러 갈라 보고
    차이가 실제로 검출되는 것을 확인한다.
    """

    def wider(raw: str) -> list[str]:
        """산문 중간의 JSON 도 긁는 변종 — 두 구현이 «하지 않기로 한» 것이다."""
        candidates = plan_candidates(raw)
        start, end = raw.find("{"), raw.rfind("}")
        if start != -1 and end > start:
            candidates.append(raw[start : end + 1])
        return candidates

    assert _disagreements(plan_candidates, wider) != [], (
        "관대함을 넓힌 변종을 넣었는데 차이가 안 잡혔다 — 이 표본으로는 아무것도 재지 못한다"
    )


def test_samples_cover_both_branches() -> None:
    """⚠️ 표본이 두 분기(펜스를 벗김·안 벗김)를 모두 지난다 — 한쪽만 지나면 반쪽만 잰다."""
    stripped = [s for s in _SAMPLES if len(plan_candidates(s)) == 2]
    untouched = [s for s in _SAMPLES if len(plan_candidates(s)) == 1]
    assert stripped, "펜스를 벗기는 표본이 없다"
    assert untouched, "펜스를 안 벗기는 표본이 없다"
