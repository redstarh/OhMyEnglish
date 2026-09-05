"""스텁 어댑터의 지시문 보관 계약 (설계서 §5.2 · AS6).

스텁은 지시문을 **받아서 보관만** 한다 — 발화는 `app.audio_gateway.fixtures`의
`FIXTURE_TURNS`가 결정한다. 그래서 여기서 못박는 것은 둘이다: 받은 값이 그대로 읽히는가,
그리고 **받았다는 사실이 재생 발화를 바꾸지 않는가.**

두 번째가 이 파일의 핵심이다. 그것을 `type(a) is type(b)`로 재면 항진명제가 된다 —
같은 생성자로 만든 두 객체의 타입은 항상 같으므로, 구현이 지시문에 따라 발화를 바꿔도
통과한다. 그래서 **관측 가능한 동일성**을 잰다: 두 어댑터의 `events()`가 흘리는 시퀀스를
그대로 비교한다.

생성자와 속성은 DB도 세션 러너도 필요 없는 순수 단위 검사라 통합 테스트에 두지 않았다.
"""

from __future__ import annotations

import pytest

from app.audio_gateway.port import AdapterEvent
from app.audio_gateway.stub import StubVoiceAdapter

INSTRUCTIONS = "today: article_missing, A2"


async def _replayed(adapter: StubVoiceAdapter) -> list[AdapterEvent]:
    """어댑터가 흘리는 전체 시퀀스. 전사문과 오디오 프레임을 **한 목록**으로 모은다 —
    포트가 둘을 하나의 시간 순서로 흘리므로 순서까지 비교 대상이다."""
    return [event async for event in adapter.events()]


def test_stub_keeps_the_instructions_it_was_given():
    adapter = StubVoiceAdapter("fixture", instructions=INSTRUCTIONS)

    assert adapter.instructions == INSTRUCTIONS


def test_stub_without_instructions_reports_none():
    # 기본값이 `None`인 것이 계약이다 — 빈 문자열이면 "안 받았다"와 "빈 지시문을 받았다"가
    # 구분되지 않아 AS6("지시문에 값이 들어 있다")을 판정할 수 없다.
    assert StubVoiceAdapter("fixture").instructions is None


def test_instructions_cannot_be_passed_positionally():
    # 키워드 전용으로 두는 이유: 위치로 받으면 기존 `StubVoiceAdapter("fixture")`·
    # `("unresponsive")` 호출 옆에 두 번째 값이 조용히 끼어들 수 있다.
    with pytest.raises(TypeError):
        StubVoiceAdapter("fixture", INSTRUCTIONS)  # ty: ignore[too-many-positional-arguments]


async def test_stub_replays_the_same_utterances_with_or_without_instructions():
    plain = await _replayed(StubVoiceAdapter("fixture"))
    instructed = await _replayed(StubVoiceAdapter("fixture", instructions=INSTRUCTIONS))

    assert instructed == plain


def test_stub_still_rejects_an_unknown_mode():
    # 지시문 인자를 더하면서 모드 검증을 덮어쓰지 않았는지 본다. 검증이 사라지면 오타가
    # 조용히 통과하고, `start()`가 `unresponsive` 분기를 타지 않아 연결 실패 경로(G2)를
    # 만들려던 테스트가 그냥 초록이 된다.
    with pytest.raises(ValueError, match="스텁 모드"):
        StubVoiceAdapter("fixtures")  # ty: ignore[invalid-argument-type]
