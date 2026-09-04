"""계획 프롬프트 조립 (설계서 §4, 계획서 Task 6).

`build_plan_prompt`는 순수 함수다 — `PlanInput`(Task 4)을 받아 Claude에게 보낼 프롬프트
문자열을 만들 뿐 DB에 닿지 않는다. 그래서 `plan_input_factory`(이 태스크가 `tests/conftest.py`에
추가)도 DB 없이 `PlanInput`을 조립한다.

이 프롬프트가 요구하는 출력 키는 Task 5(`app.models.plan.PlanOutput`)의 검증 계약과
**정확히 같아야** 한다 — 하나만 어긋나면 실물 모델 응답이 검증 단계에서 전부 거부된다.

**리뷰 라운드 1 (2026-09-05)에서 고친 것**: Important-2·3 두 테스트는 리뷰어가 항진명제임을
증명했다(문구를 지워도 통과) — 아래 두 테스트는 절 범위를 직접 잘라서 보는 형태로 바꿨다.
M3: `..._asks_for_the_output_contract`는 `"level"`이 `"target_level"`의 부분문자열이자
`"Current level:"`에도 걸려 그 키를 지워도 통과했다 — `"- key:"` 형태로 좁혔다. 그 외에는
Critical-1(pattern_id)·Important-1(제약 3개)·Important-4(최근 창)·Important-5(h-doc 단문
기준)·Important-6(기간을 정수 일수로)·M1(빈 목록 근거)·M2(빈 줄 비대칭) 테스트를 새로 더했다.
"""

from app.services.plan import build_plan_prompt


def test_prompt_lists_every_due_pattern(plan_input_factory):
    data = plan_input_factory(due_keys=["article_missing", "verb_tense_past", "preposition_at"])

    prompt = build_plan_prompt(data)

    # AS1 — 하나라도 빠지면 실패다.
    for key in ("article_missing", "verb_tense_past", "preposition_at"):
        assert key in prompt


def test_prompt_includes_pattern_id_so_the_model_never_invents_one(plan_input_factory):
    data = plan_input_factory(due_keys=["article_missing"], chronic_flagged=["article_missing"])

    prompt = build_plan_prompt(data)

    # Critical-1 — pattern_id가 목록에 없으면 모델이 UUID를 지어낸다. 형식만 맞은 가짜
    # id는 FK 없는 focus_pattern_ids에 조용히 저장돼 복습·초점 조회가 영구히 어긋난다.
    due_id = data.due_reviews[0].pattern_id
    chronic_id = data.chronic[0].pattern_id
    assert str(due_id) in prompt
    assert str(chronic_id) in prompt
    assert "never invent one" in prompt


def test_prompt_asks_for_the_output_contract(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 출력 계약(Task 5)과 같은 이름을 요구해야 파싱이 성립한다. "- key:" 형태로 찾는다 —
    # "level"만 찾으면 "target_level"의 부분문자열로도 걸리고 "Current level:" 문구에도
    # 걸려, level 키를 규격에서 지워도 통과했다(리뷰 M3).
    for field in ("focus", "questions", "target_level", "reason", "instruction", "level", "notes"):
        assert f"- {field}:" in prompt


def test_prompt_requires_matching_target_level_and_valid_cefr(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # Important-1 — 키 이름이 맞아도 target_level·level.target_level·instruction.target_level
    # 셋의 일치와 CEFR 값역을 프롬프트가 말하지 않으면 Task 5의 검증기가 응답을 거부한다.
    assert "instruction.target_level" in prompt
    assert "A1|A2|B1|B2|C1|C2" in prompt


def test_prompt_requires_instruction_focus_count_and_non_empty_fields(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())
    spec_section = prompt[prompt.index("Return one JSON object") :]

    # Important-1 — instruction.focus도 1~2개여야 하고, sentence_length·hint_timing·
    # level.reason은 비어 있으면 안 된다는 것을 프롬프트가 명시해야 한다.
    assert "instruction.focus" in spec_section
    assert "one or two items" in spec_section
    assert spec_section.count("must not be empty") >= 2


def test_prompt_forbids_extra_keys_and_blank_strings(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())
    spec_section = prompt[prompt.index("Return one JSON object") :]

    # Important-1 확장 (2026-09-05 고침 라운드에서 메인이 필드 단위 대조로 찾았다).
    # `PlanOutput`은 모든 모델이 `extra="forbid"`라서 **모르는 키 하나가 응답 전체를 죽인다** —
    # "Return one JSON object and nothing else"는 JSON 밖의 산문만 막고 키는 막지 않는다.
    # 그리고 출력의 모든 문자열 필드가 `min_length=1`이다(`NonBlankText` 포함) — 열거한
    # 셋(sentence_length·hint_timing·level.reason) 밖에도 questions.prompt·context·
    # contexts 항목·notes 항목이 같은 제약을 받는다.
    assert "Do not add any key that is not listed above" in spec_section
    assert "must be non-empty" in spec_section


def test_prompt_states_the_documented_counts(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    assert "1-2" in prompt or "one or two" in prompt  # 초점 패턴 (PRD.md:188)
    assert "3-5" in prompt or "three to five" in prompt  # 질문 (PRD.md:188)


def test_prompt_requires_korean_reason(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 출력 규격 절만 본다 — 헤더의 "Korean learner"에 낚이면 규격에서 그 요구를 지워도
    # 통과한다(리뷰 Important-2, 리뷰어가 직접 증명했다).
    spec_section = prompt[prompt.index("Return one JSON object") :]
    assert "Korean" in spec_section
    assert "reason" in spec_section


def test_prompt_keeps_pronunciation_separate_from_grammar(plan_input_factory):
    data = plan_input_factory(
        due_keys=["article_missing"],
        pronunciation=[("th_as_s", "incorrect", 4)],
    )

    prompt = build_plan_prompt(data)

    # §4.4 주의 2 — 두 계산 기준을 한 정렬에 섞으면 발음이 부당하게 위/아래로 간다.
    # 절 제목 사이 구간만 잘라서 본다 — 이전 버전(grammar_at != pron_at)은 서로 다른
    # 두 문자열의 index()가 같아질 수 없어 항진이었다(리뷰 Important-3, 한 절에 섞어도
    # 통과했다).
    due_section = prompt[
        prompt.index("Due for review today") : prompt.index("Recent learner utterances")
    ]
    pronunciation_section = prompt[
        prompt.index("Pronunciation attempts") : prompt.index("Current level:")
    ]
    assert "article_missing" in due_section
    assert "th_as_s" not in due_section
    assert "th_as_s" in pronunciation_section
    assert "article_missing" not in pronunciation_section


def test_prompt_never_asks_for_a_pronunciation_score(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory(pronunciation=[("th_as_s", "incorrect", 4)]))

    # requirements-summary.md:120-121 — 점수·등급·유사도 지표는 하지 않는 것이다.
    lowered = prompt.lower()
    for banned in ("pronunciation score", "accent rating", "native-likeness", "how native"):
        assert banned not in lowered


def test_prompt_marks_the_chronic_signal_when_present(plan_input_factory):
    data = plan_input_factory(due_keys=["article_missing"], chronic_flagged=["article_missing"])

    prompt = build_plan_prompt(data)

    # §6.2 — 3단계를 소진한 뒤 재발한 것은 **사실**로 넘기고 만성 판정은 모델이 한다.
    assert "completed all three review stages" in prompt


def test_prompt_renders_chronic_span_and_gap_as_whole_days(plan_input_factory):
    data = plan_input_factory(due_keys=["article_missing"], chronic_flagged=["article_missing"])

    prompt = build_plan_prompt(data)

    # Important-6 — timedelta를 str()로 그대로 새면 "9 days, 0:00:00"처럼 나와 0:00:00이
    # 별개 필드로 읽힐 수 있다. 정수 일수만 낸다.
    assert "span 9 days" in prompt
    assert "longest gap 3 days" in prompt
    assert "0:00:00" not in prompt


def test_prompt_includes_recent_utterances_and_their_corrections(plan_input_factory):
    data = plan_input_factory(
        recent=[
            (
                "I go to gym after work.",
                [
                    (
                        "article_missing",
                        "article",
                        "go to gym",
                        "go to the gym",
                        "설명",
                        "medium",
                        0.9,
                    )
                ],
            )
        ],
    )

    prompt = build_plan_prompt(data)
    recent_section = prompt[
        prompt.index("Recent learner utterances") : prompt.index("Chronic metrics")
    ]

    # Important-4 — 픽스처가 recent=[]를 하드코딩해 이 절의 발화·교정 포맷이 한 번도
    # 실행되지 않았다. 이제 실제로 채워서 잰다.
    assert "I go to gym after work." in recent_section
    assert "article_missing" in recent_section
    assert "go to the gym" in recent_section


def test_prompt_sets_a_short_single_clause_baseline(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # h-doc — 예문·질문·instruction.sentence_length 생성은 단문·단일 절 기준이 발판이고,
    # 확장형은 점진적으로 얹는다(리뷰 Important-5 — 이전 버전은 능력 서술만 있고 생성
    # 지시가 없었다).
    assert "single-clause" in prompt
    assert "gradually" in prompt


def test_prompt_states_empty_lists_explicitly(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # M1 — `audio_gateway/nova.py`의 선례(0건이면 블록을 아예 넣지 않는다)와 다르게,
    # 여기서는 절 제목을 유지하고 빈 목록을 명시한다(plan.py 모듈 주석에 근거를 남겼다).
    for placeholder in (
        "(none due today)",
        "(no learner utterances in this window)",
        "(no chronic metrics yet)",
        "(no pronunciation attempts in this window)",
    ):
        assert placeholder in prompt


def test_every_section_header_is_followed_directly_by_its_list(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # M2 — 발음 절 상수만 개행으로 끝나서 그 절만 제목과 목록 사이에 빈 줄이 하나 더
    # 있었다. ⚠️ 이것을 `"\n\n\n" not in prompt`로 재면 **항진명제다** — 고침 전 코드에서도
    # 통과한다(2026-09-05 직접 확인). 빈 줄은 `\n\n`이고 절 사이 구분자도 이미 `\n\n`이라
    # 셋이 겹치는 자리가 없다. 실측한 차이는 제목 바로 뒤였다: 발음 `'\n\n'` · 나머지 `'\n'`.
    # 네 절 제목은 모두 `):`로 끝나므로 그 뒤에 목록이 바로 오는지를 잰다.
    for placeholder in (
        "(none due today)",
        "(no learner utterances in this window)",
        "(no chronic metrics yet)",
        "(no pronunciation attempts in this window)",
    ):
        assert f"):\n{placeholder}" in prompt


def test_prompt_does_not_invent_a_size_limit(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 설계서 §3.4 — 지시문 크기 상한의 구체 수치는 Nova 초기화 실측 후에 정한다.
    for banned in ("at most 500", "maximum 1000", "word limit"):
        assert banned not in prompt.lower()
