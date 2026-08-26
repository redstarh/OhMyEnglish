"""발음 tool 페이로드 검증 (설계서 §4.2 — 2026-08-27-pronunciation-echo-design.md).

Nova 출력은 **신뢰할 수 없는 외부 데이터**다. 2026-08-27 스파이크에서 모델이 실제로
스키마를 어겼다 — `outcome` enum 에 없는 `"pending"` 을 냈다(설계서 F4). 그래서 여기서
못박는 것은 파싱이 아니라 **강등과 폐기 규칙**이다.

엄격 검증으로 거부하지 않는 이유는 전례다 — 1차수 I-5 에서 모델 출력에 엄격 검증을
걸었을 때 그 발화가 5회 재시도 끝에 `failed` 가 됐다.

픽스처의 원본은 실제 Nova 응답이다:
`tests/harness/runs/2026-08-27-P-tooluse-spike/P-tooluse-nova-events.json`
"""

from __future__ import annotations

import json

from app.models.pronunciation import (
    PRONUNCIATION_OUTCOMES,
    PRONUNCIATION_TOOL_NAME,
    PRONUNCIATION_TOOL_SCHEMA_JSON,
    SIGNAL_SOURCES,
    parse_tool_payload,
)

# 2026-08-27 스파이크가 실제로 받은 페이로드. 손으로 만든 것이 아니다.
SPIKE_PAYLOAD = (
    '{"target_form":"I think I found three very useful videos.",'
    '"spoken_form":"[awaiting user repetition]","outcome":"pending"}'
)


def test_tool_name_is_stable() -> None:
    """어댑터와 모델이 같은 이름을 써야 한다 — 다르면 tool 이벤트가 조용히 버려진다."""
    assert PRONUNCIATION_TOOL_NAME == "report_pronunciation_coaching"


def test_outcome_and_signal_value_domains_match_the_migration() -> None:
    """003 의 CHECK 와 같은 값역이어야 한다. 어긋나면 앱이 통과시킨 값을 DB가 거부한다."""
    assert PRONUNCIATION_OUTCOMES == ("pending", "correct", "incorrect", "unclear")
    assert SIGNAL_SOURCES == ("nova_tool", "korean_transcript", "agent_reprompt")


def test_tool_schema_is_a_json_string() -> None:
    """Nova Sonic 의 `inputSchema.json` 은 객체가 아니라 **문자열**이다 (스파이크 F1)."""
    assert isinstance(PRONUNCIATION_TOOL_SCHEMA_JSON, str)
    parsed = json.loads(PRONUNCIATION_TOOL_SCHEMA_JSON)
    assert parsed["type"] == "object"
    assert "target_form" in parsed["properties"]
    assert set(parsed["properties"]["outcome"]["enum"]) == set(PRONUNCIATION_OUTCOMES)
    # 모델이 최소한 이 둘은 채워야 한다.
    assert set(parsed["required"]) == {"target_form", "outcome"}


def test_parses_the_real_spike_payload() -> None:
    report = parse_tool_payload(SPIKE_PAYLOAD)
    assert report is not None
    assert report.target_form == "I think I found three very useful videos."
    assert report.outcome == "pending"
    assert report.spoken_form == "[awaiting user repetition]"
    assert report.target_sound is None


def test_unknown_outcome_is_demoted_to_unclear() -> None:
    """열거값 밖이면 강등한다. 세션을 깨뜨리지 않는다."""
    report = parse_tool_payload('{"target_form":"I think.","outcome":"kinda_ok"}')
    assert report is not None
    assert report.outcome == "unclear"


def test_missing_outcome_is_demoted_to_unclear() -> None:
    report = parse_tool_payload('{"target_form":"I think."}')
    assert report is not None
    assert report.outcome == "unclear"


def test_non_string_outcome_is_demoted_to_unclear() -> None:
    """타입이 아예 다른 값도 강등한다 — pydantic 이 터지기 전에 걸러야 한다."""
    report = parse_tool_payload('{"target_form":"I think.","outcome":42}')
    assert report is not None
    assert report.outcome == "unclear"


def test_empty_target_form_is_discarded() -> None:
    """시범이 없는 시범 기록은 의미가 없다."""
    assert parse_tool_payload('{"target_form":"   ","outcome":"correct"}') is None
    assert parse_tool_payload('{"outcome":"correct"}') is None
    assert parse_tool_payload('{"target_form":null,"outcome":"correct"}') is None


def test_broken_json_is_discarded_without_raising() -> None:
    assert parse_tool_payload("not json at all") is None
    assert parse_tool_payload("") is None
    assert parse_tool_payload('{"target_form":') is None


def test_non_object_json_is_discarded() -> None:
    """배열이나 스칼라가 와도 죽지 않는다."""
    assert parse_tool_payload('["target_form"]') is None
    assert parse_tool_payload('"just a string"') is None
    assert parse_tool_payload("17") is None


def test_extra_fields_do_not_break_parsing() -> None:
    """모델이 새 필드를 더해도 우리가 죽지 않아야 한다."""
    report = parse_tool_payload(
        '{"target_form":"I think.","outcome":"correct","confidence":0.9,"nested":{"a":1}}'
    )
    assert report is not None
    assert report.outcome == "correct"


def test_target_sound_is_carried_when_present() -> None:
    report = parse_tool_payload(
        '{"target_form":"I think.","outcome":"incorrect","target_sound":"th_as_s"}'
    )
    assert report is not None
    assert report.target_sound == "th_as_s"


def test_blank_optional_strings_become_none() -> None:
    """공백만 있는 값을 그대로 저장하면 "있는데 비어 있는" 필드가 생긴다."""
    report = parse_tool_payload(
        '{"target_form":"I think.","outcome":"correct","spoken_form":"  ","target_sound":""}'
    )
    assert report is not None
    assert report.spoken_form is None
    assert report.target_sound is None


def test_target_form_is_stripped() -> None:
    report = parse_tool_payload('{"target_form":"  I think.  ","outcome":"correct"}')
    assert report is not None
    assert report.target_form == "I think."


def test_report_is_frozen() -> None:
    """검증을 통과한 뒤에 값이 바뀌면 검증의 의미가 없다."""
    import pydantic
    import pytest

    report = parse_tool_payload(SPIKE_PAYLOAD)
    assert report is not None
    with pytest.raises(pydantic.ValidationError):
        report.outcome = "correct"  # type: ignore[misc]
