"""계획 프롬프트 조립 (설계서 §4, 계획서 Task 6).

`build_plan_prompt`는 순수 함수다 — `PlanInput`(Task 4)을 받아 Claude에게 보낼 프롬프트
문자열을 만들 뿐 DB에 닿지 않는다. 그래서 `plan_input_factory`(이 태스크가 `tests/conftest.py`에
추가)도 DB 없이 `PlanInput`을 조립한다.

이 프롬프트가 요구하는 출력 키는 Task 5(`app.models.plan.PlanOutput`)의 검증 계약과
**정확히 같아야** 한다 — 하나만 어긋나면 실물 모델 응답이 검증 단계에서 전부 거부된다.
"""

from app.services.plan import build_plan_prompt


def test_prompt_lists_every_due_pattern(plan_input_factory):
    data = plan_input_factory(due_keys=["article_missing", "verb_tense_past", "preposition_at"])

    prompt = build_plan_prompt(data)

    # AS1 — 하나라도 빠지면 실패다.
    for key in ("article_missing", "verb_tense_past", "preposition_at"):
        assert key in prompt


def test_prompt_asks_for_the_output_contract(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 출력 계약(Task 5)과 같은 이름을 요구해야 파싱이 성립한다.
    for field in ("focus", "questions", "target_level", "reason", "instruction", "level", "notes"):
        assert field in prompt


def test_prompt_states_the_documented_counts_only(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    assert "1-2" in prompt or "one or two" in prompt  # 초점 패턴 (PRD.md:188)
    assert "3-5" in prompt or "three to five" in prompt  # 질문 (PRD.md:188)


def test_prompt_requires_korean_reason(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    assert "Korean" in prompt
    assert "reason" in prompt


def test_prompt_keeps_pronunciation_separate_from_grammar(plan_input_factory):
    data = plan_input_factory(
        due_keys=["article_missing"],
        pronunciation=[("th_as_s", "incorrect", 4)],
    )

    prompt = build_plan_prompt(data)

    # §4.4 주의 2 — 두 계산 기준을 한 정렬에 섞으면 발음이 부당하게 위/아래로 간다.
    assert "th_as_s" in prompt
    grammar_at = prompt.index("article_missing")
    pron_at = prompt.index("th_as_s")
    assert grammar_at != pron_at  # 서로 다른 절에 있다


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


def test_prompt_does_not_invent_a_size_limit(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 설계서 §3.4 — 지시문 크기 상한의 구체 수치는 Nova 초기화 실측 후에 정한다.
    for banned in ("at most 500", "maximum 1000", "word limit"):
        assert banned not in prompt.lower()
