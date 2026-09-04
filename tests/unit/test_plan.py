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

⚠️ **이 파일의 지배 규칙 (재리뷰 라운드 2에서 얻었다 — 어기면 같은 구멍이 다시 난다)**:
**프롬프트 전체나 규격 전체를 대상으로 문구를 찾지 않는다.** 같은 낱말이 다른 절·다른 불릿에
있어서 판별력을 잃는다. 이 슬라이스에서 그 방식이 만든 사고 4건: ① `"Korean" in prompt`가
헤더의 "Korean learner"를 쟀다 ② `"instruction.target_level" in prompt`가 `- instruction:`
불릿에 걸려 **일치 요구 문장을 지워도** 통과했다 ③ `"one or two" in prompt`가 `- instruction:`
쪽에 걸려 `- focus:`의 개수 제약이 **무보호가 됐다**(고침 라운드 1이 만든 회귀) ④ 두 목록에
같은 key를 줘서 `pattern_id`가 동일해져 한쪽만 떼도 통과했다.
→ **절은 `prompt.index(...)` 사이를 잘라서, 불릿은 `_bullet()`으로 잘라서 잰다.**
→ **양성만 재지 않는다** — 표식·placeholder는 붙지 **않아야** 하는 경우도 함께 잰다.
"""

from app.services.plan import build_plan_prompt


def test_prompt_lists_every_due_pattern(plan_input_factory):
    data = plan_input_factory(due_keys=["article_missing", "verb_tense_past", "preposition_at"])

    prompt = build_plan_prompt(data)

    # AS1 — 하나라도 빠지면 실패다.
    for key in ("article_missing", "verb_tense_past", "preposition_at"):
        assert key in prompt
    # `- focus:`는 각 항목에 `target_form`을 요구한다 — 목록이 그것을 싣지 않으면 모델이
    # 지어낸다(pattern_id 와 같은 부류, FK가 없어 검증만으로는 안 걸린다). 무테스트였다.
    assert f'target form "{data.due_reviews[0].target_form}"' in prompt


def test_prompt_includes_pattern_id_so_the_model_never_invents_one(plan_input_factory):
    # ⚠️ 두 목록에 **다른** key를 준다. 같은 key를 주면 픽스처의 `setdefault`가 key당 id를
    # 하나만 배정해 두 id가 동일해지고, 그러면 한쪽 포맷에서만 id를 떼도 이 테스트가 통과한다
    # (재리뷰 라운드 2가 잡았고 내가 직접 재현했다 — `identical? True`).
    data = plan_input_factory(due_keys=["article_missing"], chronic_flagged=["verb_tense_past"])

    prompt = build_plan_prompt(data)

    # Critical-1 — pattern_id가 목록에 없으면 모델이 UUID를 지어낸다. 형식만 맞은 가짜
    # id는 FK 없는 focus_pattern_ids에 조용히 저장돼 복습·초점 조회가 영구히 어긋난다.
    due_id = data.due_reviews[0].pattern_id
    chronic_id = data.chronic[0].pattern_id
    assert due_id != chronic_id  # 픽스처가 두 id를 실제로 갈라 놓았는지 먼저 확인한다
    due_section = prompt[
        prompt.index("Due for review today") : prompt.index("Recent learner utterances")
    ]
    chronic_section = prompt[
        prompt.index("Chronic metrics") : prompt.index("Pronunciation attempts")
    ]
    assert str(due_id) in due_section
    assert str(chronic_id) in chronic_section
    assert "never invent one" in prompt


def test_prompt_restricts_focus_to_the_two_lists_that_carry_pattern_id(plan_input_factory):
    data = plan_input_factory(
        due_keys=["article_missing"],
        chronic_flagged=["verb_tense_past"],
        pronunciation=[("th_as_s", "incorrect", 4)],
        recent=[
            (
                "I go to gym after work.",
                [("preposition_at", "preposition", "to gym", "to the gym", "설명", "medium", 0.9)],
            )
        ],
    )

    prompt = build_plan_prompt(data)

    # 재리뷰 라운드 2의 Critical — 이전 문구는 "Pick from the lists above"였는데 **네 목록 중
    # 둘만 pattern_id를 싣는다**(내가 프로브로 확인: 최근 교정 `False` · 발음 `False`).
    # 최근 교정 목록은 실제 `error_patterns` 행의 `pattern_key`를 부르면서 id는 없으므로
    # 모델이 거기서 초점을 고르면 **여전히 UUID를 지어내야** 하고, FK 없는
    # `focus_pattern_ids uuid[]`에 조용히 저장되는 원래 경로가 그대로 살아난다.
    # 계획서 Task 7이 정한 허용 집합도 `due_reviews ∪ chronic` 둘뿐이라, 다른 목록에서 고른
    # 초점은 그 가드가 어차피 하드 거부한다 — 프롬프트가 그 경계를 먼저 말해야 한다.
    focus_bullet = _bullet(prompt, "focus")
    assert "only two lists that carry pattern_id" in focus_bullet
    assert "a pattern taken from anywhere else is rejected" in focus_bullet

    # ⚠️ 규격이 부르는 이름은 **절 제목을 그대로 인용**해야 한다(재리뷰 라운드 2의 Minor).
    # 이전 판은 "review list"라고 불렀는데 제목은 "Due for review today (…)"였다 — 그 둘을
    # 잇는 것이 모델의 추론이고, 추론이 틀리면 **Critical 경로가 되살아난다**(다른 목록에서
    # 초점을 골라 UUID를 지어낸다). 인용과 실제 제목이 함께 있는지 잰다.
    for bare in ("Due for review today", "Chronic metrics"):
        assert f'"{bare}"' in focus_bullet  # 규격이 제목 문구를 인용한다
        assert f"{bare} (" in prompt  # 그 문구로 시작하는 절 제목이 실재한다

    # 초점 출처가 아닌 두 절은 스스로도 그 사실을 말한다. 제목 **줄 끝까지** 자른다 —
    # 고정 길이 창은 자기순환이었다(`_section_header` docstring).
    assert "context only" in _section_header(prompt, "Recent learner utterances")
    assert "context only" in _section_header(prompt, "Pronunciation attempts")


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
    # 셋의 일치와 CEFR 값역을 프롬프트가 말하지 않으면 Task 5의 검증기가 응답을 거부한다
    # (`PlanOutput._target_level_matches_level_and_instruction`).
    # ⚠️ `"instruction.target_level" in prompt`로는 못 잰다 — 그 이름이 `- instruction:` 절에도
    # 있어서 일치 요구 문장을 통째로 지워도 통과했다(재리뷰 라운드 2, 내가 직접 재현).
    # `level.target_level`은 이 문장에만 나오므로 그것을 잰다.
    assert "must equal level.target_level" in prompt
    assert "all three must match" in prompt
    assert "A1|A2|B1|B2|C1|C2" in prompt


def test_prompt_requires_instruction_focus_count_and_non_empty_fields(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # Important-1 — instruction.focus도 1~2개여야 하고, sentence_length·hint_timing·
    # level.reason은 비어 있으면 안 된다는 것을 프롬프트가 명시해야 한다.
    # ⚠️ 이전 판은 `spec_section.count("must not be empty") >= 2`였다 — **어느 필드에**
    # 붙었는지와 무관한 문구 세기라 두 요구를 한 불릿에 몰아도 통과했다(재리뷰 라운드 2의
    # Minor). 불릿별로 잰다.
    instruction_bullet = _bullet(prompt, "instruction")
    assert "instruction.focus" in instruction_bullet
    assert "one or two items" in instruction_bullet
    assert "must not be empty" in instruction_bullet
    assert "must not be empty" in _bullet(prompt, "level")


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
    # 빈 리스트와 빈 문자열을 갈라 말하는 문장 — 없으면 모델이 "모든 문자열이 비면 안 된다"를
    # **빈 리스트 금지**로 읽을 여지가 있다(재리뷰 라운드 2의 Minor. 이 문장이 무테스트였다).
    assert "Empty lists are allowed where said above; empty strings are not" in spec_section


def _bullet(prompt: str, key: str) -> str:
    """출력 규격에서 `- <key>:` 불릿의 **본문**만 잘라낸다 (`- key:` 표지는 벗긴다).

    규격 전체나 프롬프트 전체를 대상으로 문구를 찾으면 **다른 불릿에 있는 같은 낱말**에
    걸려 판별력을 잃는다 — 재리뷰 라운드 2가 그 방식으로 회귀 1건과 항진 2건을 잡았다.

    불릿은 다음 `\\n- ` **또는 빈 줄**에서 끝난다. ⚠️ 빈 줄을 경계로 넣은 이유: 마지막
    불릿(`notes`)은 `\\n- `를 만나지 않아 규격 끝의 **전역 문장 2개까지 끌고 왔다**
    (실측 — `"must be non-empty" in _bullet(prompt, "notes")` → `True`,
    `"Do not add any key" in _bullet(prompt, "notes")` → `True`). 그것을 불릿 내용으로
    착각하면 엉뚱한 자리를 지킨다.
    """
    spec = prompt[prompt.index("Return one JSON object") :]
    marker = f"- {key}:"
    assert marker in spec, f"출력 규격에 {marker!r} 불릿이 없다"
    body = spec[spec.index(marker) + len(marker) :]
    ends = [i for i in (body.find("\n- "), body.find("\n\n")) if i != -1]
    return body[: min(ends)] if ends else body


def _bullet_lead(prompt: str, key: str) -> str:
    """불릿 본문의 **첫 문장**만. 문구를 그 불릿의 **주어에 묶는다.**

    ⚠️ `_bullet()`만으로는 부족하다 — 창을 좁힐 뿐 문구를 주어에 묶지 않는다. 재리뷰
    라운드 2가 반례를 통과시켰고 **내가 직접 재현했다(22 passed)**: `- focus:`에서 개수
    제약을 지우고 두 칸 들여쓴 연속 줄에 `"Note: instruction.focus below also has one or
    two items."`를 넣으면 `"one or two" in _bullet(prompt, "focus")`가 **참으로 남는다.**
    규격에 이미 불릿 간 상호참조가 있으므로(`instruction.target_level must equal the
    top-level target_level`) 현실적인 편집이다 — 라운드 1이 만든 회귀와 **같은 부류**이고
    창만 한 단계 좁혀졌을 뿐이었다.
    """
    head, _, _ = _bullet(prompt, key).partition(".")
    return head


def _section_header(prompt: str, anchor: str) -> str:
    """절 제목 **한 줄**만. 고정 길이 창(`+120` 같은 것)을 쓰지 않는다.

    ⚠️ 고정 창은 **자기순환**이었다(재리뷰 라운드 2). 최근 창 제목은 지금 **134자**인데
    그것은 여기서 재려는 문구(37자)가 있기 때문이다 — 그 문구를 지우면 제목이 97자로 줄어
    120자 창이 목록 본문으로 **23자 새어들고**, 그 자리에 같은 문구를 넣은 뮤테이션에서
    테스트가 **통과했다.** 단정이 지키려는 문구가 단정의 경계를 지켜 주면 안 된다.
    """
    start = prompt.index(anchor)
    return prompt[start : prompt.index("\n", start)]


def test_prompt_states_the_documented_counts(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # ⚠️ 프롬프트 전체에서 "one or two"를 찾으면 **판별력이 없다** — 고침 라운드 1이
    # `- instruction:` 불릿에 "one or two items"를 더한 뒤로는 `- focus:`의 개수 제약을
    # 지워도 통과했다(재리뷰 라운드 2가 잡은 회귀, 내가 직접 재현).
    # ⚠️ **불릿으로 좁히는 것도 부족했다** — 두 칸 들여쓴 연속 줄에 `instruction.focus`
    # 상호참조를 넣으면 개수 제약을 지워도 통과한다(라운드 2의 반례, 내가 재현: 22 passed).
    # 문구를 불릿의 **주어에 묶는다** → 첫 문장만 본다.
    assert "one or two" in _bullet_lead(prompt, "focus")  # 초점 패턴 (PRD.md:188)
    assert "three to five" in _bullet_lead(prompt, "questions")  # 질문 (PRD.md:188)


def test_prompt_requires_korean_reason(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 출력 규격의 `- reason:` 불릿만 본다 — 헤더의 "Korean learner"에 낚이면 규격에서 그
    # 요구를 지워도 통과하고(리뷰 Important-2), 규격 전체를 보면 그 요구를 **다른 키로
    # 옮겨도** 통과한다(재리뷰 라운드 2의 잔여 지적).
    assert "Korean" in _bullet(prompt, "reason")


def test_prompt_states_the_current_level_and_the_one_step_rule(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 재리뷰 라운드 2의 Important — 둘 다 무테스트였다. `Current level:` 값을
    # `(unavailable)`로 바꿔도, 한 칸 규칙 문장을 지워도 전부 통과했다(내가 직접 재현).
    # `parse_plan`의 `_one_step_or_same`가 두 칸 도약을 **하드 거부**하는데, 모델이
    # 기준선(현재 수준)을 모르면 그 규칙을 지킬 수 없다 — 응답 전체가 죽는다.
    assert "Current level: A2" in prompt  # 픽스처의 current_level
    assert "at most one CEFR step from the current" in _bullet(prompt, "level")


def test_prompt_keeps_pattern_id_out_of_the_instruction_focus(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # `InstructionFocus`도 `extra="forbid"`라서 `instruction.focus[]`에 `pattern_id`가
    # 하나라도 들어오면 **응답 전체가 거부된다**. 최상위 `focus`는 그 id를 요구하므로
    # 모델이 같은 모양으로 복사할 유인이 크다 — 그래서 프롬프트가 명시해야 한다.
    assert "no pattern_id here" in _bullet(prompt, "instruction")


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
    # 절을 나누는 것만으로는 부족하다 — 두 계산 기준이 다르다는 것을 문장으로도 알린다
    # (§4.4 주의 2). 그 문구가 무테스트였다(재리뷰 라운드 2의 Minor).
    assert "do not rank these against the grammar counts" in pronunciation_section


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


def test_prompt_marks_only_the_flagged_chronic_pattern(plan_input_factory):
    data = plan_input_factory(
        chronic_flagged=["article_missing"],
        chronic_unflagged=["verb_tense_past"],
    )

    prompt = build_plan_prompt(data)
    chronic_section = prompt[
        prompt.index("Chronic metrics") : prompt.index("Pronunciation attempts")
    ]
    lines = [line for line in chronic_section.splitlines() if line.startswith("- ")]

    # 재리뷰 라운드 2의 Important — 음성 케이스가 없어서 `metric.pattern_id in
    # chronic_pattern_ids` 조건을 `if True`로 바꿔도 전부 통과했다(내가 직접 재현).
    # 그러면 §6.2의 **유일한 결정론적 신호**가 전 패턴에 붙어 소음이 된다.
    marked = [line for line in lines if "completed all three review stages" in line]
    assert len(lines) == 2
    assert len(marked) == 1
    assert "article_missing" in marked[0]


def test_prompt_renders_chronic_span_and_gap_as_whole_days(plan_input_factory):
    data = plan_input_factory(due_keys=["article_missing"], chronic_flagged=["article_missing"])

    prompt = build_plan_prompt(data)

    # Important-6 — timedelta를 str()로 그대로 새면 "9 days, 0:00:00"처럼 나와 0:00:00이
    # 별개 필드로 읽힐 수 있다. 정수 일수만 낸다.
    assert "span 9 days" in prompt
    assert "longest gap 3 days" in prompt
    assert "0:00:00" not in prompt


def test_prompt_renders_a_missing_max_gap_as_not_applicable(plan_input_factory):
    data = plan_input_factory(chronic_flagged=["article_missing"], chronic_max_gap=None)

    prompt = build_plan_prompt(data)

    # `chronic.py`는 발생이 1건뿐인 패턴에 `max_gap=None`을 낸다. 픽스처가 고정값이라
    # `"n/a"` 분기가 한 번도 실행되지 않았다(재리뷰 라운드 2의 Minor). `None`이 그대로
    # 새면 모델이 "longest gap None"을 읽는다.
    # ⚠️ `"None" not in prompt`로 재지 않는다 — **만성 절로 좁힌다.** 프롬프트에는 학습자
    # 전사문이 그대로 실리므로 `"None of them worked."` 같은 발화에 오경보한다(라운드 2가
    # 실측으로 증명했다). 이 파일 머리말의 지배 규칙("전체를 대상으로 찾지 않는다")도 같다.
    chronic_section = prompt[
        prompt.index("Chronic metrics") : prompt.index("Pronunciation attempts")
    ]
    assert "longest gap n/a" in chronic_section
    assert "None" not in chronic_section


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


_PLACEHOLDERS = (
    "(none due today)",
    "(no learner utterances in this window)",
    "(no chronic metrics yet)",
    "(no pronunciation attempts in this window)",
)


def test_prompt_drops_the_placeholder_once_a_list_has_rows(plan_input_factory):
    data = plan_input_factory(
        due_keys=["article_missing"],
        chronic_flagged=["verb_tense_past"],
        pronunciation=[("th_as_s", "incorrect", 4)],
        recent=[("I go to gym after work.", [])],
    )

    prompt = build_plan_prompt(data)

    # M1의 반쪽 — 빈 목록에 placeholder가 **있는지**는 아래
    # `test_every_section_header_is_followed_directly_by_its_list`가 이미 잰다(그 단정이
    # `f"):\n{ph}" in prompt`라서 존재까지 함의한다). 재리뷰 라운드 2가 지적한 중복을
    # 없애고, 그 테스트가 못 재는 반대 방향만 여기서 잰다: **행이 있으면 사라져야 한다.**
    # 사라지지 않으면 모델이 "없다"와 목록을 동시에 읽는다.
    for placeholder in _PLACEHOLDERS:
        assert placeholder not in prompt


def test_every_section_header_is_followed_directly_by_its_list(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # M2 — 발음 절 상수만 개행으로 끝나서 그 절만 제목과 목록 사이에 빈 줄이 하나 더
    # 있었다. ⚠️ 이것을 `"\n\n\n" not in prompt`로 재면 **항진명제다** — 고침 전 코드에서도
    # 통과한다(2026-09-05 직접 확인). 빈 줄은 `\n\n`이고 절 사이 구분자도 이미 `\n\n`이라
    # 셋이 겹치는 자리가 없다. 실측한 차이는 제목 바로 뒤였다: 발음 `'\n\n'` · 나머지 `'\n'`.
    # 네 절 제목은 모두 `):`로 끝나므로 그 뒤에 목록이 바로 오는지를 잰다.
    for placeholder in _PLACEHOLDERS:
        assert f"):\n{placeholder}" in prompt


def test_prompt_does_not_invent_a_size_limit(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 설계서 §3.4 — 지시문 크기 상한의 구체 수치는 Nova 초기화 실측 후에 정한다.
    for banned in ("at most 500", "maximum 1000", "word limit"):
        assert banned not in prompt.lower()
