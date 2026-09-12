"""발음 전용 모드가 소리를 «후보로» 내려보내는 규칙 (`TASK-128.2` · 사용자 결정 72).

`_pronunciation_candidates` 는 순수 함수다 — DB 를 타지 않는다. 그래서 여기서 잰다:
DB 를 타면 「어느 출처가 앞인가」가 조용히 바뀌어도 통합 픽스처가 통과할 수 있다.

⛔ **결정 72 가 이 함수의 뜻을 바꿨다.** 이전 판(`_pronunciation_sound_or_none`)은 소리 **하나**를
골라 돌려주고 그것이 프롬프트에서 `- Sound to coach today: "키"` 로 **이름으로** 지목됐다. 그 단수
지목이 되풀이의 구동부였다 — 오디오에 그 소리가 한 자리도 없을 때도 코치가 그 키를 `target_sound`
에 실었고, 강제를 더한 판과 뺀 판이 **모두** 3/3 으로 그랬다
(`runs/2026-09-12-task120-absent-planted-sound.md` · `…task123-118-subtract-key-forcing.md` ARM-B).
⇒ 이제 이 함수는 **후보 목록**을 만든다. 계획의 초점은 «앞에 오는 것»으로만 이긴다.

⛔ **빈 목록은 「말하기로 떨어뜨려라」가 아니다** — 그것이 결정 72 가 뒤집은 자리다. 소리가 없어도
`?mode=pronunciation` 이면 전용 모드로 간다(그 판정은 `_pronunciation_candidates` 가 아니라
`pronunciation_requested` 가 갖는다).
"""

from __future__ import annotations

from app.api.ws import _pronunciation_candidates
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


def test_the_plan_pronunciation_focus_comes_first_and_the_list_survives():
    """계획이 앞인 이유: 복습 예정일을 근거로 «오늘» 다룰 소리를 이미 고른 값이다.

    ⛔ **그러나 목록을 밀어내지 않는다** — 이전 판은 계획의 소리 **하나만** 남기고 목록을 버렸다.
    후보 기제(*"If one of them is off again"*)는 목록이 넓을수록 「실제로 들은 소리」를 그 안에서
    찾을 확률이 높아지므로, 버리면 결정 72 가 노린 값이 줄어든다.
    """
    plan = _instruction(
        (f"{PRONUNCIATION_PATTERN_KEY_PREFIX}th_as_s", "th_as_s"),
        ("article_missing_before_noun", "a/an + 단수 명사"),
    )

    assert _pronunciation_candidates(plan, ["an_as_a", "f_as_p"]) == [
        "th_as_s",
        "an_as_a",
        "f_as_p",
    ]


def test_the_plan_focus_is_not_repeated_when_the_list_already_has_it():
    """⛔ 같은 키가 두 번 실리면 「후보가 둘」이 아니라 **그 키를 강조한 것**으로 읽힌다.

    ⚠️ 이 경로가 예외가 아니라 **평시**다: 계획의 발음 초점은 `error_patterns` 의 due 패턴에서
    오고 놓친 소리 목록도 같은 표에서 온다 — 즉 겹치는 것이 정상이다.
    """
    plan = _instruction((f"{PRONUNCIATION_PATTERN_KEY_PREFIX}f_as_p", "f_as_p"))

    assert _pronunciation_candidates(plan, ["an_as_a", "f_as_p"]) == ["f_as_p", "an_as_a"]


def test_every_pronunciation_focus_of_the_plan_is_a_candidate():
    """초점이 여럿이면 **그 순서대로** 전부 앞에 온다 — 하나만 고르는 것이 이전 판의 규약이었다.

    ⚠️ 초점 둘로 잰다 — `SessionInstruction.focus` 가 **최대 2개**다(직접 확인: 3개는
    `too_long` 으로 거부된다). 문법 초점이 섞이는 경로는 위 첫 테스트가 잰다.
    """
    plan = _instruction(
        (f"{PRONUNCIATION_PATTERN_KEY_PREFIX}th_as_s", "th_as_s"),
        (f"{PRONUNCIATION_PATTERN_KEY_PREFIX}v_as_b", "v_as_b"),
    )

    assert _pronunciation_candidates(plan, []) == ["th_as_s", "v_as_b"]


def test_the_missed_sound_list_is_used_when_the_plan_has_no_pronunciation_focus():
    plan = _instruction(("article_missing_before_noun", "a/an + 단수 명사"))

    assert _pronunciation_candidates(plan, ["an_as_a", "f_as_p"]) == ["an_as_a", "f_as_p"]


def test_no_plan_leaves_the_missed_sound_list_alone():
    assert _pronunciation_candidates(None, ["f_as_p"]) == ["f_as_p"]


def test_neither_source_gives_an_empty_list():
    """⚠️ 이 음성 케이스가 판별력을 만든다 — 없는 소리를 발명하지 않는다.

    ⛔ **빈 목록의 «뜻»이 결정 72 로 바뀌었다.** 이전에는 `None` 이 「말하기로 떨어뜨려라」였고,
    이제는 「후보 없이 전용 모드로 간다」다. 그 판정이 이 함수 밖으로 나갔다는 것이 결정의 내용이고
    `tests/integration/test_ws.py` 가 그 자리를 잰다.
    """
    grammar_only = _instruction(("article_missing_before_noun", "a/an"))

    assert _pronunciation_candidates(None, []) == []
    assert _pronunciation_candidates(grammar_only, []) == []
