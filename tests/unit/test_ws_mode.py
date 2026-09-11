"""발음 전용 모드가 «오늘의 소리»를 고르는 규칙 (`TASK-10.1` · 사용자 결정 64).

`_pronunciation_sound_or_none` 은 순수 함수다 — DB 를 타지 않는다. 그래서 여기서 잰다:
DB 를 타면 「어느 출처가 이기는가」가 조용히 바뀌어도 통합 픽스처가 통과할 수 있다.

⛔ **셋을 함께 잰다**: 계획이 이긴다 · 계획에 발음 초점이 없으면 목록으로 내려간다 ·
**둘 다 없으면 `None`**. 마지막 것이 판별력을 만든다 — 그것 없이는 「항상 목록의 첫 항목」으로
고쳐도 앞의 둘이 통과한다.
"""

from __future__ import annotations

from app.api.ws import _pronunciation_sound_or_none
from app.models.plan import InstructionFocus, SessionInstruction
from app.models.pronunciation import PRONUNCIATION_PATTERN_KEY_PREFIX


def _instruction(*focus: tuple[str, str]) -> SessionInstruction:
    return SessionInstruction(
        target_level="A2",
        focus=[InstructionFocus(pattern_key=key, target_form=form) for key, form in focus],
        sentence_length="short single-clause sentences",
        hint_timing="wait three seconds",
        contexts=["after work"],
    )


def test_the_plan_pronunciation_focus_wins_over_the_missed_sound_list():
    """계획이 먼저인 이유: 그것은 복습 예정일을 근거로 «오늘» 다룰 소리를 이미 고른 값이다."""
    plan = _instruction(
        (f"{PRONUNCIATION_PATTERN_KEY_PREFIX}th_as_s", "th_as_s"),
        ("article_missing_before_noun", "a/an + 단수 명사"),
    )

    assert _pronunciation_sound_or_none(plan, ["an_as_a", "f_as_p"]) == "th_as_s"


def test_the_missed_sound_list_is_used_when_the_plan_has_no_pronunciation_focus():
    plan = _instruction(("article_missing_before_noun", "a/an + 단수 명사"))

    assert _pronunciation_sound_or_none(plan, ["an_as_a", "f_as_p"]) == "an_as_a"


def test_no_plan_falls_back_to_the_missed_sound_list():
    assert _pronunciation_sound_or_none(None, ["f_as_p"]) == "f_as_p"


def test_neither_source_gives_none():
    """⚠️ 이 음성 케이스가 판별력을 만든다.

    `None` 은 「소리 없는 전용 세션」이 아니라 **말하기로 떨어뜨려라**는 신호다 — 소리 없이 그
    지시문을 조립하면 모델에게 있지도 않은 초점을 찾게 시킨다.
    """
    assert _pronunciation_sound_or_none(None, []) is None
    assert (
        _pronunciation_sound_or_none(_instruction(("article_missing_before_noun", "a/an")), [])
        is None
    )
