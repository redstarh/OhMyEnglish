"""`app.models.session_summary` — 총평 파서 (`TASK-62`).

⛔ 이 파일은 DB·모델을 보지 않는다 — 파서가 순수 함수라는 것이 계약이고
`models/scenario_draft.py` 와 같은 규약이다.

⛔ **재는 것의 절반은 «거부»다.** 통과만 재면 「무엇을 넣어도 받는 파서」와 구별되지 않는다.
특히 정의되지 않은 키를 거부하는 단정이 `R11-8`·`R13-5` 의 경계를 **구조로** 지키는 자리다 —
점수·등급이 새 키로 들어오는 것을 문면이 아니라 값역이 막는다(설계서 §2.1).
"""

from __future__ import annotations

import json

import pytest

from app.models.session_summary import (
    EMPTY_SUMMARY,
    MAX_POINTS,
    SummaryValidationError,
    parse_summary,
    summary_from_row,
    summary_payload,
)


def _raw(**overrides: object) -> str:
    body: dict[str, object] = {
        "went_well": ["관사를 붙인 문장이 여러 번 나왔어요."],
        "weak_points": [{"point": "문장이 길어지면 관사를 빼먹어요.", "quote": "I sent report."}],
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


def test_parses_the_two_sections() -> None:
    draft = parse_summary(_raw(), max_points=MAX_POINTS)

    assert draft.went_well == ("관사를 붙인 문장이 여러 번 나왔어요.",)
    assert len(draft.weak_points) == 1
    assert draft.weak_points[0].point == "문장이 길어지면 관사를 빼먹어요."
    assert draft.weak_points[0].quote == "I sent report."


def test_quote_is_optional() -> None:
    """⚠️ `quote` 는 부차다 — 없다고 거부하면 총평 전체를 잃는다."""
    draft = parse_summary(_raw(weak_points=[{"point": "관사를 빼먹어요."}]), max_points=MAX_POINTS)

    assert draft.weak_points[0].quote is None


def test_rejects_a_missing_section() -> None:
    with pytest.raises(SummaryValidationError, match="went_well"):
        parse_summary(json.dumps({"weak_points": [{"point": "x"}]}), max_points=MAX_POINTS)


def test_rejects_more_points_than_the_cap() -> None:
    """⛔ 상한을 넘기면 총평이 아니라 목록이 된다."""
    too_many = [{"point": f"약점 {index}"} for index in range(MAX_POINTS + 1)]
    with pytest.raises(SummaryValidationError, match="상한"):
        parse_summary(_raw(weak_points=too_many), max_points=MAX_POINTS)


def test_rejects_zero_weak_points() -> None:
    """⛔ 0개는 「약점을 못 찾았다」는 판정이고 이 총평의 것이 아니다(설계서 §2.1)."""
    with pytest.raises(SummaryValidationError, match="weak_points"):
        parse_summary(_raw(weak_points=[]), max_points=MAX_POINTS)


def test_rejects_an_undefined_key() -> None:
    """⛔ 점수·등급이 새 키로 들어오는 것을 구조가 막는다(`R11-8`·`R13-5` 의 경계)."""
    with pytest.raises(SummaryValidationError, match="정의되지 않은 키"):
        parse_summary(_raw(score=88), max_points=MAX_POINTS)


def test_rejects_an_undefined_key_inside_a_weak_point() -> None:
    """⛔ 최상위만 막으면 판정이 «항목 안»으로 들어온다 — 같은 방어를 그 자리에도 둔다."""
    with pytest.raises(SummaryValidationError, match="정의되지 않은 키"):
        parse_summary(_raw(weak_points=[{"point": "x", "severity": "high"}]), max_points=MAX_POINTS)


def test_payload_round_trips_through_the_row_reader() -> None:
    """저장한 모양을 읽는 쪽이 그대로 되돌려야 한다 — 두 자리가 갈리면 화면이 빈다."""
    payload = summary_payload(parse_summary(_raw(), max_points=MAX_POINTS))

    assert summary_from_row(payload) == payload


def test_row_reader_separates_never_generated_from_nothing_to_say() -> None:
    """⛔ 이것이 `R13-7` 의 구별을 구조로 갖는 자리다.

    `{}` 는 「아직 만들지 않았다」이고 빈 배열 둘은 「만들었고 담을 것이 없었다」다. 그 둘을 같은
    것으로 읽으면 화면이 「총평이 없는 세션」과 「총평이 빈 세션」을 구별할 수 없다.
    """
    assert summary_from_row({}) is None
    assert summary_from_row(EMPTY_SUMMARY) == EMPTY_SUMMARY
    assert summary_from_row(None) is None
