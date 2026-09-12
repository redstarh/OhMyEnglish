"""기록된 `target_sound` 가 «코치가 말한 소리»와 어긋나는지 판정한다 (결정 82 · `TASK-116.1`).

설계 정본은 `docs/design/2026-09-13-decision82-record-path-verification.md` 이고 여기서 근거를 다시
적지 않는다. 이 파일이 잼: **판정 함수는 순수 함수다** — DB 를 타면 「어느 발화를 창으로 삼는가」가
조용히 바뀌어도 통합 픽스처가 통과한다.

⛔ **문면을 발명하지 않는다.** 아래 문자열은 전부 `TASK-128.3` 회차에서 실제로 관측된 코치 발화다
(`tests/harness/runs/2026-09-12-task128-sound-as-candidate.md` §1 · 원본은
`.harness/evidence/T128A*-frames.json`·`T128B*-frames.json` 의 agent `final`). 실측 문면으로 재면
「내가 만든 입력에서만 도는」 판정을 피한다.

⛔ **이 함수는 「맞다」를 증명하지 않는다 — 「어긋났다」만 증명한다.** 두 실패의 비용이 다르기
때문이다: 놓친 어긋남은 오염 1건이고, 잘못된 배제는 **정상 기록을 복습에서 지우는 것**이다. 그래서
판정할 수 없으면 `None` 이고 호출부는 그것을 배제 사유로 쓰지 않는다.
"""

from __future__ import annotations

from app.services.pronunciation import sound_check_verdict

# `TASK-128.3` ARM-A — 오디오 오류가 /θ/→/s/ 이고 후보도 `th_as_s` 인 팔(코칭 4/4).
_ARM_A_SPEECH = 'I noticed a small pronunciation issue with the "th" sound in "think."'
_ARM_A_SPEECH_VARIANT = (
    "I noticed a small pronunciation point in your sentence. "
    'The word "Sri\'s" had the "th" sound a bit unclear.'
)
# ARM-B — 오디오에 /f/ 가 한 자리도 없는데 후보가 `f_as_p` 였던 판별 팔.
_ARM_B_JUDGEMENT_SPEECH = (
    ' Great job! Your pronunciation of "early" was clear and accurate this time. '
    'The "er" sound blended smoothly, and the word flowed naturally in the sentence.'
)
_ARM_B_INVENTED_SPEECH = (
    "I noticed a small issue with the 'f' sound in 'early'. Let's focus on that. "
    "Try saying just the word 'early' with a clear 'f' sound at the beginning."
)


def test_a_sound_the_coach_did_not_name_is_a_mismatch():
    """⛔ 이 판정이 결정 82 가 막으려는 것이다 — `TASK-128.3` ARM-B 의 B2·B3 이 이 모양이었다.

    코치는 `early` 의 **`er`** 을 코칭했고 tool 에는 **`f_as_p`** 가 실렸다. 그 기록이 복습 시계를
    돌리면 **연습하지 않은 소리**가 전진한다(`review.py` 가 `target_sound` 로 매칭한다).
    """
    assert sound_check_verdict(_ARM_B_JUDGEMENT_SPEECH, "f_as_p") == "mismatched"


def test_the_sound_the_coach_named_is_not_excluded():
    """⚠️ **음성 대조 — 이것이 없으면 「전부 배제」로 고쳐도 위 테스트가 통과한다.**

    ARM-A 는 코칭이 4/4 로 났고 기록도 옳았던 팔이다. ⛔ **그 팔을 배제하면 이 변경이 발음 복습을
    통째로 끄는 것**이 되고, 그것은 결정 82 가 요구한 것이 아니다.
    """
    assert sound_check_verdict(_ARM_A_SPEECH, "th_as_s") == "matched"
    assert sound_check_verdict(_ARM_A_SPEECH_VARIANT, "th_as_s") == "matched"


def test_the_blind_spot_is_named_here_and_not_hidden():
    """⛔ **맹점을 테스트가 «명시»한다 — 이 함수가 못 잡는 것을 기록으로 남긴다.**

    `TASK-128.3` ARM-B 의 B1 에서 코치는 *"the 'f' sound in 'early'"* 라고 말하고 *"like in 'fine'"*
    까지 댔다. **`early` 에는 /f/ 가 한 자리도 없다** — 즉 발화와 기록이 «맞으면서 함께» 틀렸다.
    이 함수는 「기록이 발화를 따르는가」만 재므로 그 경우를 **`matched` 로 판정한다.**

    ⇒ **「발화가 오디오를 따르는가」는 이 축이 아니다**(설계서 §6 이 범위 밖으로 둔다). 그 판정에는
    오디오를 듣는 수단이 필요하다.
    ⛔ 이 단정을 「고쳐야 할 실패」로 읽지 마라 — 고치려면 다른 재료가 필요하고, 그때 이 테스트가
    **무엇이 바뀌었는지** 가리키는 자리가 된다.
    """
    assert sound_check_verdict(_ARM_B_INVENTED_SPEECH, "f_as_p") == "matched"


def test_speech_without_a_quoted_sound_gives_no_verdict():
    """코치가 소리를 인용하지 않으면 **판정하지 않는다** — `None` 이고 배제 사유가 아니다.

    ⚠️ 실측에서 이 모양이 실제로 있었다: ARM-B 의 시범 턴은 *'…detail in the word "early".'* 로
    **소리를 인용하지 않았고** `er` 은 그 다음 판정 턴에 나왔다. ⇒ 창을 시범 턴 하나로 좁히면 이
    함수가 영원히 `None` 을 낸다. 그 창 선택은 호출부의 몫이고 설계서 §4-1 이 갖는다.
    """
    modeling_turn = 'I noticed a small pronunciation detail in the word "early".'

    assert sound_check_verdict(modeling_turn, "f_as_p") is None
    assert sound_check_verdict("", "f_as_p") is None


def test_a_missing_key_gives_no_verdict():
    """키가 없으면 대조할 것이 없다. ⛔ 그것을 「어긋남」으로 읽으면 `target_sound` 가 null 인 행이
    전부 배제되는데, 그 행들은 **이미** `review.py` 에서 빠진다(`btrim(null) = x` 가 null 이다)."""
    assert sound_check_verdict(_ARM_A_SPEECH, None) is None
    assert sound_check_verdict(_ARM_A_SPEECH, "   ") is None


def test_a_letter_that_the_key_connector_contains_lands_on_the_safe_side():
    """⚠️ **알려진 오탐 하나를 «적어 둔다»** — 키에 `_as_` 가 들어가므로 인용된 `a`·`s` 는 어떤 키와
    일치한다. 즉 그 경우 이 함수는 `matched` 를 내고 **아무것도 배제하지 않는다.**

    ⛔ **그 방향이 안전한 쪽이다**(설계서 §4): 이 함수의 계약이 「어긋남만 증명한다」이므로 오탐은
    「막지 못한 오염 1건」이고, 반대 방향 오류(정상 기록을 배제)보다 싸다.
    ⛔ 키의 «모양»을 파싱해 연결어를 떼는 안을 쓰지 않는다 — `X_as_Y` 는 **모델이 지어내는 형태**라
    규약이 아니다(`audio_gateway/nova.py` 의 소리 줄 주석이 그 기각을 소유한다). 다음 키 모양에서
    조용히 깨지는 것보다 오탐을 아는 편이 낫다.
    """
    speech_quoting_s = 'The "s" at the end sounded soft.'

    assert sound_check_verdict(speech_quoting_s, "th_as_s") == "matched"
    # ⛔ 오탐이 «아닌» 자리를 함께 재서 이 단정이 「항상 matched」로 무너지지 않게 한다.
    assert sound_check_verdict('The "er" sound was off.', "th_as_s") == "mismatched"
