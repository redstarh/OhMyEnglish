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


def test_speech_that_quotes_nothing_gives_no_verdict():
    """코치가 **아무것도** 인용하지 않으면 판정하지 않는다 — `None` 이고 배제 사유가 아니다.

    ⛔ **이 테스트의 앞 판이 뒤집혔다 — 뒤집힌 사실과 근거를 함께
    남긴다**(`rules/session-handoff.md` §4 의 규율 3). 앞 판은 *'…detail in the word "early".'* 도
    **`None`** 이라고 단정했고 그 근거는 「소리를 인용하지 않았다」였다. **사용자 결정 98 이 그것을
    뒤집었다**: 실측에서 일반 세션의 코치는 소리를 이름으로 인용하지 않아 그 규칙 아래에서는 판정이
    **한 건도 붙지 않았고**(일반 세션 3/3 · 브라우저 1/1) 오디오에 없는 소리가 복습 시계를
    전진시켰다. ⇒ 낱말 인용도 대조 재료로 쓴다. 그 자리는 위
    `test_a_quoted_word_alone_can_prove_a_mismatch` 가 가진다.

    ⚠️ 여기 남는 것은 **인용이 0개인 경우**뿐이다 — 그때는 재료가 없어 여전히 판정하지 않는다.
    """
    no_quotes = "I noticed a small pronunciation detail in the word early."

    assert sound_check_verdict(no_quotes, "f_as_p") is None
    assert sound_check_verdict("", "f_as_p") is None


def test_a_missing_key_gives_no_verdict():
    """키가 없으면 대조할 것이 없다. ⛔ 그것을 「어긋남」으로 읽으면 `target_sound` 가 null 인 행이
    전부 배제되는데, 그 행들은 **이미** `review.py` 에서 빠진다(`btrim(null) = x` 가 null 이다)."""
    assert sound_check_verdict(_ARM_A_SPEECH, None) is None
    assert sound_check_verdict(_ARM_A_SPEECH, "   ") is None


# `TASK-116.3` 회차(`runs/2026-09-15-task116-3-verdict-condition`)에서 실측한 **일반 세션** 코치
# 발화. ⛔ 문면을 발명하지 않았다 — 위 ARM 문면과 같은 규율이다. WS 레그
# B2·B4(`runs/2026-09-14-task129-plan-review-key` §1)의 원문 — 낱말만 인용했다.
_GENERAL_SESSION_SPEECH_WORD_ONLY = (
    "I see. Your brother is arriving early tomorrow morning. | "
    'Sorry, I need to hear that word again. Can you say "early" one more time for me?'
)


def test_a_hyphenated_spelling_is_compared_as_a_word():
    """⛔ **결정 98** — `"er-lee."` 처럼 적은 발음 표기도 대조 재료다. **낱말로** 본다.

    ⚠️ **소리 조각으로 쪼개지 않는 이유가 실측에 있다.** 쪼개면 `er` 이 나오는데 그것은 키 `r_as_l`
    «안에» 없어서(`er` ⊄ `r_as_l`) **정상 기록이 배제된다.** 낱말로 두면 키의 소리 조각 `r` 이
    `er-lee` 안에 있으므로 배제하지 않는다 — 아래 둘째 단정이 그 자리를 지킨다.

    ⚠️ 그리고 닫는 따옴표 «앞의» 마침표를 받아야 이 토큰이 잡힌다 — 실측 발화가
    `is "er-lee."` 였고 앞 판의 정규식은 그 모양을 통째로 놓쳤다.
    """
    only_hyphenated = 'Say it like "er-lee."'

    assert sound_check_verdict(only_hyphenated, "f_as_p") == "mismatched"
    assert sound_check_verdict(only_hyphenated, "r_as_l") is None


def test_a_quoted_word_alone_can_prove_a_mismatch():
    """⛔ **결정 98 의 본체** — 낱말만 인용해도 대조 재료로 쓴다.

    실측(WS 레그 3/3): 코치가 `"early"` 만 인용해 토큰이 0개였고 판정이 `None` 이었다. `early` 에는
    키가 지목한 /f/ 가 한 자리도 없으므로 **어긋남을 증명할 수 있다.**
    """
    assert sound_check_verdict(_GENERAL_SESSION_SPEECH_WORD_ONLY, "f_as_p") == "mismatched"


def test_a_quoted_word_does_not_exclude_a_record_that_names_that_word_s_own_sound():
    """⚠️ **결정 98 이 감수한 대가를 여기서 막는다 — 이 단정이 없으면 넓힌 문턱이
    정상 기록을 지운다.**

    코치가 `"early"` 를 인용했고 키가 **`r_as_l`** 이면 그 낱말에 `r` 이 있으므로 어긋남을 증명할 수
    없다 ⇒ **`None`**(배제하지 않는다). ⛔ 여기서 `mismatched` 가 나오면 발음 복습이 통째로 꺼진다.
    """
    assert sound_check_verdict(_GENERAL_SESSION_SPEECH_WORD_ONLY, "r_as_l") is None


def test_a_short_sound_does_not_preempt_word_evidence_for_another_key():
    """⛔ **codex 리뷰 HIGH · `TASK-116.4`** — 한 발화에 소리와 낱말이 함께 인용되면 **짧은 소리가
    낱말 증거를 선점**해 정상 기록이 배제된다.

    실패 시나리오(실측): 발화가 `First practice the "er" sound. Later repeat "fine".` 이고 시도의
    키가 `f_as_p` 일 때 앞 판은 `mismatched` 를 냈다 — `er` 이 그 키 «안에» 없기 때문이다. 그런데
    같은 발화에서 낱말 `fine` 은 키의 소리 `f` 를 담고 있다. ⇒ **증거가 갈리는데 배제로 기울었다.**
    ⚠️ 낱말만 인용된 판(`Later repeat "fine".`)은 이미 `None` 이었으므로, 소리 토큰이 **더 있는 것이
    판정을 나쁘게** 만들었다.

    ⇒ 증거가 갈리면 **배제하지 않는다** — 이 함수의 계약이 「어긋남을 증명할 수 있을 때만」이다.
    """
    split_evidence = 'First practice the "er" sound. Later repeat "fine".'

    assert sound_check_verdict(split_evidence, "f_as_p") is None
    # ⛔ 음성 대조 — 이 단정이 없으면 「낱말이 하나라도 있으면 None」으로 고쳐도 위가 통과한다.
    # `fine` 은 `th_as_s` 의 소리를 담지 않으므로 그 키는 여전히 어긋남이다.
    assert sound_check_verdict(split_evidence, "th_as_s") == "mismatched"


def test_a_possessive_is_not_chopped_into_a_sound_token():
    """⛔ **codex 리뷰 HIGH — 소유격의 아포스트로피를 «닫는 따옴표»로 오인하면
    정상 기록이 배제된다.**

    `"Sri's"` 에서 앞 판은 `Sri` 를 3자 소리 토큰으로 뽑았다. 키가 `s_as_z` 인 **정상 기록**에서
    `sri` ⊄ `s_as_z` 이므로 `mismatched` 가 되고 복습 이력에서 빠진다.
    ⚠️ 이 오추출은 **결정 98 이전에도 있었다**(앞 판 정규식도 1~3자였다) — 리뷰가 그것을 드러냈다.
    ⇒ 낱말 안의 아포스트로피는 **낱말의 일부**로 받는다. 그러면 `sri's` 는 낱말이고 키의 조각 `s` 가
    그 안에 있어 배제하지 않는다.
    """
    possessive_only = 'Please repeat "Sri\'s".'

    assert sound_check_verdict(possessive_only, "s_as_z") is None


def test_a_word_whose_spelling_hides_the_sound_is_a_known_cost():
    """⚠️ **결정 98 이 감수한 대가를 «이름 붙여» 남긴다** (codex 리뷰 HIGH).

    갈래 ②는 **철자**로 대조한다. 영어는 같은 소리를 다른 철자로 적으므로(`laugh`·`enough` 의 /f/ 는
    `gh` · `phone` 의 /f/ 는 `ph`) 그 낱말이 인용되면 키 `f_as_p` 의 조각이 철자에 없어
    **정상 기록이 배제된다.**

    ⛔ **이 단정을 「고쳐야 할 실패」로 읽지 마라.** 고치려면 낱말에서 소리를 얻는 사전·규칙이
    필요하고 **사용자가 그 후보를 기각했다**(결정 98 의 기각 ② — 결정 54·59 가 경계한 추정값이
    된다). ⇒ 남는 선택은 「이 대가를 알고 쓰는 것」이고, 이 테스트가 **그 대가의 크기를 눈에
    보이게** 둔다.
    """
    assert sound_check_verdict('Please repeat "laugh".', "f_as_p") == "mismatched"


def test_a_whole_sentence_quote_is_still_not_judged():
    """⚠️ **남은 구멍 하나를 적어 둔다** (codex 리뷰 MEDIUM).

    실측 발화에는 문장 전체를 인용한 모양도 있었다(`I hear you say "my brother will …"`). 정규식은
    **공백을 토큰에 넣지 않으므로** 그 인용은 잡히지 않고 판정이 `None` 이다 — 즉 그 모양에서는
    오염이 그대로 통과한다.

    ⛔ 문장을 낱말로 쪼개 넣지 않는 이유는 **확률이 아니라 단조성**이다: `mismatched` 는
    `word_supports_key` 가 **거짓**일 때만 나오고 그 값은
    `any(segment in word …)` 이므로 **인용 범위를 넓히면 참이 되기만 한다.** ⇒ 문장을 낱말 자루로
    넣든 한 덩어리로 넣든 갈래 ②는 `None` 이다 — 이득이 「작다」가 아니라 **구조적으로 0** 이다.

    ⇒ 그래서 이 구멍은 **코치가 소리를 인용하게 만드는 쪽**에서 닫혔다 (`TASK-116.5` · 사용자 결정
    2026-09-17 로 **결정 82 를 이 축에서만 뒤집었다**). `SYSTEM_PROMPT` 규칙 9 가 소리를 따옴표로
    «따로» 인용하라고 요구하고, 그 요구를 `test_nova.py` 의
    `test_system_prompt_makes_the_coach_quote_the_off_sound_on_its_own` 이 잰다.
    ⛔ **이 함수의 거동은 그 결정으로 바뀌지 않았다** — 문장만 인용된 발화는 여전히 `None` 이다.
    바뀐 것은 「그 모양이 «유일한» 증거로 남는 일을 프롬프트가 줄인다」이고, 아래 두 단정이 그
    새 모양을 고정한다.
    ⚠️ **전용 모드 프롬프트에는 아직 그 요구가 없다**(실측 산출물에 바이트로 묶여 있어 실물 회차가
    필요하다) — 그 절반은 열려 있고 별 태스크가 갖는다.
    """
    sentence_quote = 'I hear you say "my brother will arrive early tomorrow morning."'

    assert sound_check_verdict(sentence_quote, "f_as_p") is None


# ⚠️ **아래 두 문면은 관측된 조각 «둘을 합친 것»이고 그 자체로 관측된 발화가 아니다** — 문장 인용은
# `runs/2026-09-15-task81-app-leg` §7 의 실측이고 소리 인용 어법(`The "er" sound …`)은
# `_ARM_B_JUDGEMENT_SPEECH` 의 실측이다. 합친 이유는 **프롬프트가 방금 그 모양을 요구했기 때문**이고
# (규칙 9), 그 모양의 실측은 다음 회차가 만든다. ⛔ 회차가 돌면 이 문면을 실측으로 바꾼다.
#
# ⛔ **두 단정은 red 로 태어나지 않았다** — 검사 코드를 고치지 않았으므로 프롬프트 변경 전에도
# 통과한다(`H-M`). 무엇을 막는가를 적어 둔다: 나중에 누가 `_QUOTED_TOKEN_RE` 에 공백을 넣어 문장을
# 토큰으로 삼으면 **첫 단정이 red 가 된다**(문장이 `words` 로 들어와 `word_supports_key` 가 참이
# 되고 판정이 `None` 으로 떨어진다 — 인용 문장에 `r`·`l` 이 있다). 그 무력화로 판별력을 확인했다.
_SENTENCE_QUOTE_WITH_SOUND = (
    'I hear you say "my brother will arrive early tomorrow morning." The "th" sound was off.'
)


def test_a_quoted_sound_beside_a_sentence_quote_is_judged():
    """규칙 9 가 요구하는 모양 — 문장 인용 **옆에** 소리가 따로 인용되면 판정이 산다."""
    assert sound_check_verdict(_SENTENCE_QUOTE_WITH_SOUND, "r_as_l") == "mismatched"


def test_a_matching_quoted_sound_beside_a_sentence_quote_is_not_excluded():
    """반대 방향 — 소리가 키와 맞으면 `matched` 다. **정상 기록을 배제하지 않는다.**"""
    assert sound_check_verdict(_SENTENCE_QUOTE_WITH_SOUND, "th_as_s") == "matched"


def test_a_letter_that_the_key_connector_contains_lands_on_the_safe_side():
    """⚠️ **알려진 오탐 하나를 «적어 둔다»** — 키에 `_as_` 가 들어가므로 인용된 `a`·`s` 는 어떤 키와
    일치한다. 즉 그 경우 이 함수는 `matched` 를 내고 **아무것도 배제하지 않는다.**

    ⛔ **그 방향이 안전한 쪽이다**(설계서 §4): 이 함수의 계약이 「어긋남만 증명한다」이므로 오탐은
    「막지 못한 오염 1건」이고, 반대 방향 오류(정상 기록을 배제)보다 싸다.

    ⚠️ **이 기각이 «부분» 뒤집혔다 — 경위를 남긴다**(결정 98 · `TASK-116.3`). **소리를 인용한 이
    갈래는 지금도 키를 파싱하지 않는다** — 이 단정이 그것을 지킨다. 뒤집힌 것은 **낱말만 인용된
    갈래**뿐이고, 거기서는 연결어를 떼되 **조각이 둘 미만이면 판정을 포기해** 모양을 계약으로 쓰지
    않는다. 근거는 실측이다: 파싱을 피한 대가가 「오탐 1건」이 아니라 **일반 세션에서 검사가 통째로
    무력해지는 것**이었다.
    """
    speech_quoting_s = 'The "s" at the end sounded soft.'

    assert sound_check_verdict(speech_quoting_s, "th_as_s") == "matched"
    # ⛔ 오탐이 «아닌» 자리를 함께 재서 이 단정이 「항상 matched」로 무너지지 않게 한다.
    assert sound_check_verdict('The "er" sound was off.', "th_as_s") == "mismatched"
