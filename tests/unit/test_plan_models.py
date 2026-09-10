"""계획 출력 계약과 거부 경계 (AS5, 계획서 Task 5).

`app.models.analysis`(Task 5 이전 슬라이스)와 같은 자리를 차지한다 — Claude의 계획 출력은
신뢰할 수 없는 외부 입력이고, 여기서 좁히지 않으면 `session_plans`의 CHECK
(`focus_pattern_ids` 1~2개 · `questions` 3~5개 · `reason` 공백 금지 · `target_level` 값역,
007 마이그레이션)에 부딪혀 저장 트랜잭션 중간에 터진다. AS5는 **저장 전에** 거부해
반쯤 검증된 계획을 쓰지 않는다(설계서 §9 Failure).

DB를 쓰지 않는 순수 단위 테스트다 — `db_conn` 픽스처를 요청하지 않으므로 PostgreSQL 없이도 돈다.
"""

import json
from uuid import UUID, uuid4

import pytest
from conftest import chronic_metric

from app.models.plan import CEFR_LEVELS, PlanValidationError, parse_plan
from app.services.chronic import deepest_recurrence

# Task 7 — `parse_plan`은 이제 **허용된 `pattern_id` 집합**을 함께 받는다. 지어낸 UUID는
# pydantic(`UUID` 타입만 본다)도 DB(`focus_pattern_ids uuid[]`에 FK가 없다)도 통과하므로
# 이 집합이 조용한 데이터 손상을 막는 유일한 장치다(계획서 Task 7 ①).
#
# ⚠️ `_payload`가 id를 **안에서** 만들면(이전 판) 호출자가 그 값을 알 수 없어 허용 집합을
# 만들 수 없다. 그래서 id를 모듈 상수로 올려 두고 `_payload`가 그중 하나를 쓴다. 아래
# 모든 호출이 `_ALLOWED`를 넘기는 이유: 이 파일의 다른 테스트들이 **지어낸 id 때문에**
# 거부되면 "통과하지만 이유가 틀린 테스트"가 된다(길이·값역 규칙을 재려던 것이므로).
_IDS: list[UUID] = [uuid4(), uuid4(), uuid4()]
_ALLOWED: set[UUID] = set(_IDS)

# AC11-2 — `parse_plan`은 **가장 깊은 재발의 `pattern_id`**도 함께 받는다(파일 끝의 절이
# 그 규칙을 소유한다). 아래 기존 호출이 전부 `_IDS[0]`을 넘기는 이유는 `_ALLOWED`와 같다:
# `_payload()`의 초점이 `_IDS[0]` 하나이므로, 다른 값을 넘기면 이 파일의 다른 테스트들이
# **최상위 누락 때문에** 거부되어 "통과하지만 이유가 틀린 테스트"가 된다.
_DEEPEST: UUID = _IDS[0]


def _payload(**overrides: object) -> str:
    body: dict[str, object] = {
        "focus": [
            {
                "pattern_id": str(_IDS[0]),
                "pattern_key": "article_missing",
                "target_form": "a/an/the",
            }
        ],
        "questions": [
            {"prompt": "What did you do at work today?", "context": "work update"},
            {"prompt": "Tell me about your morning.", "context": "daily life"},
            {"prompt": "What will you do tomorrow?", "context": "plan"},
        ],
        "target_level": "A2",
        "reason": "관사를 계속 빼먹어서 오늘은 그것만 봅니다.",
        "instruction": {
            "target_level": "A2",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "two short clauses",
            "hint_timing": "offer a starter after one long pause",
            "contexts": ["work update", "daily life", "plan"],
        },
        "level": {"action": "keep", "target_level": "A2", "reason": "정답률이 아직 낮습니다."},
        "notes": ["짧은 문장에서는 관사를 붙이는데 길어지면 빼먹는다"],
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


def test_valid_plan_parses():
    result = parse_plan(
        _payload(), current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
    )

    assert len(result.focus) == 1
    assert len(result.questions) == 3
    assert result.reason.strip() != ""
    assert result.level.action == "keep"


# AS5 ① 추천 이유가 비어 있으면 거부한다 (PRD.md:189 R11-3 — 이유 없는 추천은 검증할 수 없다)
@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_blank_reason_is_rejected(blank: str):
    with pytest.raises(PlanValidationError):
        parse_plan(
            _payload(reason=blank),
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )


# AS5 ② 질문 수가 3~5 밖이면 거부한다 (PRD.md:188 R11-2)
@pytest.mark.parametrize("count", [2, 6])
def test_question_count_outside_three_to_five_is_rejected(count: int):
    questions = [{"prompt": f"q{i}", "context": f"c{i}"} for i in range(count)]
    with pytest.raises(PlanValidationError):
        parse_plan(
            _payload(questions=questions),
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )


# 초점 패턴은 1~2개다 (PRD.md:188 · agent-system-prompt.md:19)
#
# ⚠️ id를 `uuid4()`로 즉석에서 만들지 않고 `_IDS`에서 가져온다 — 지어낸 id는 Task 7이 더한
# 허용 집합 가드에도 걸리므로, 그러면 이 테스트가 **길이 규칙이 아니라 그 가드 때문에** 통과해
# `min_length`/`max_length`를 지워도 초록으로 남는다("통과하지만 이유가 틀린 테스트").
@pytest.mark.parametrize("count", [0, 3])
def test_focus_count_outside_one_to_two_is_rejected(count: int):
    focus = [
        {"pattern_id": str(_IDS[i]), "pattern_key": f"k{i}", "target_form": "f"}
        for i in range(count)
    ]
    with pytest.raises(PlanValidationError):
        parse_plan(
            _payload(focus=focus),
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )


# AS5 ③ CEFR 값역 밖이면 거부한다 (001 의 CHECK 와 같은 값역)
#
# `level`은 오버라이드하지 않는다(기본값 "A2"로 남는다) — pydantic의
# `model_validator(mode="after")`는 **필드 검증이 하나라도 실패하면 실행되지 않는다.**
# 즉 `target_level="Z9"`는 `PlanOutput.target_level: CefrLevel`의 Literal 검증에서
# **단독으로** 거부되고, `target_level != level.target_level` 불일치 검증(after
# validator)까지 갈 일이 없다 — 애초에 confound가 아니다(2026-09-04 리뷰: 이전
# 커밋이 `level`도 "Z9"로 맞춰 confound를 없앤다고 적었는데, 그 진단 자체가 틀렸다.
# `match=`로 pydantic의 Literal 오류 문구를 직접 고정해 이 field-level 검증이
# 실제로 걸리는지 뮤테이션으로 재확인했다 — `target_level`을 `str`로 넓히면 메시지가
# "Input should be ..."에서 불일치 메시지로 바뀌어 이 `match=`가 깨진다).
def test_unknown_level_is_rejected():
    with pytest.raises(PlanValidationError, match="Input should be"):
        parse_plan(
            _payload(target_level="Z9"),
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )


# AS7 — 두 단계 도약은 거부한다. h-doc 이 경고한 "목표 수준을 현재 수준으로 착각"을 구조로 막는다.
def test_two_step_jump_is_rejected():
    payload = _payload(
        target_level="B2",
        level={"action": "up", "target_level": "B2", "reason": "빠르게 좋아졌습니다."},
    )
    with pytest.raises(PlanValidationError):
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# 한 단계 상향은 통과한다
def test_one_step_up_is_accepted():
    payload = _payload(
        target_level="B1",
        level={"action": "up", "target_level": "B1", "reason": "정답률이 꾸준합니다."},
        instruction={
            "target_level": "B1",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "two or three clauses",
            "hint_timing": "wait through one long pause",
            "contexts": ["work update", "daily life", "plan"],
        },
    )
    assert (
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        ).level.target_level
        == "B1"
    )


# 하향도 허용한다 — 상향만 되면 잘못 올라간 수준이 영구히 굳는다 (설계서 §7)
def test_one_step_down_is_accepted():
    payload = _payload(
        target_level="A1",
        level={"action": "down", "target_level": "A1", "reason": "계속 막혔습니다."},
        instruction={
            "target_level": "A1",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "one short clause",
            "hint_timing": "offer a starter early",
            "contexts": ["daily life", "morning", "evening"],
        },
    )
    assert (
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        ).level.action
        == "down"
    )


# 계획의 난이도와 수준 판단이 어긋나면 거부한다 — 두 값이 다르면 어느 것이 오늘의 목표인지 모른다.
def test_target_level_must_match_level_decision():
    payload = _payload(
        target_level="A2",
        level={"action": "up", "target_level": "B1", "reason": "좋아졌습니다."},
    )
    with pytest.raises(PlanValidationError):
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# Important 1(리뷰 2026-09-04) — `instruction.target_level`도 같은 값이어야 한다.
# `target_level`·`level.target_level`이 맞아도 여기가 갈라지면, **읽히는 수준은 C2**이고
# (화면과 대화 상대가 둘 다 `instruction.target_level`을 읽는다 — `api/results.py`와
# `audio_gateway/nova.py`) **컬럼에만 A2가 남는다.** 어긋나는 것은 기록이지 표시가 아니다:
# 실제로 쓰인 수준과 다른 기록이 그 행에 영구히 남고 사후 분석이 그것을 믿는다.
# 근거 전문은 `models/plan.py`의 `_target_level_matches_level_and_instruction`이 소유한다.
#
# ⚠️ 앞선 판은 "학습자는 화면에서 A2를 보는데 대화 상대는 C2로 말한다"고 적었다 — 거짓이다.
# 화면도 C2를 본다. 그 서술을 남겨 두면 다음 사람이 "이 실패 모드는 불가능하다"에 도달한 뒤
# 검증자를 지울 이유로 쓴다.
def test_instruction_target_level_must_match():
    payload = _payload(
        target_level="A2",
        level={"action": "keep", "target_level": "A2", "reason": "정답률이 아직 낮습니다."},
        instruction={
            "target_level": "C2",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "two short clauses",
            "hint_timing": "offer a starter after one long pause",
            "contexts": ["work update", "daily life", "plan"],
        },
    )
    with pytest.raises(PlanValidationError):
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# Important 2(리뷰 2026-09-04) — 두 단계 **하향** 도약도 거부한다. 기존 테스트 전부가
# `current_level="A2"`라 `_one_step_or_same`의 대칭(`abs`)이 실제로 재지는지 확인할 방법이
# 없었다(A2 밑으로 두 칸은 존재하지 않는다) — `current_level`을 올려서 확인한다.
def test_two_step_down_jump_is_rejected():
    payload = _payload(
        target_level="A2",
        level={"action": "down", "target_level": "A2", "reason": "많이 어려워했습니다."},
        instruction={
            "target_level": "A2",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "one short clause",
            "hint_timing": "offer a starter early",
            "contexts": ["work update", "daily life", "plan"],
        },
    )
    with pytest.raises(PlanValidationError):
        parse_plan(
            payload, current_level="B2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# 규격 밖 필드가 섞이면 거부한다 (슬라이스 1과 같은 extra="forbid" 규약)
def test_unknown_field_is_rejected():
    with pytest.raises(PlanValidationError):
        parse_plan(
            _payload(surprise="nope"),
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )


# 코드펜스로 감싼 응답은 파싱한다 — 프롬프트가 "펜스 없이"를 요구해도 모델이 종종 붙인다.
def test_code_fenced_json_parses():
    raw = "```json\n" + _payload() + "\n```"
    assert (
        parse_plan(
            raw, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        ).target_level
        == "A2"
    )


# 산문으로 감싼 응답은 **거부한다.** 계약을 지키지 않은 응답은 실패로 보고하는 것이
# 이 리포의 확립된 선택이다 — 산문 중간에서 JSON을 긁어내지 않는다.
def test_prose_wrapped_json_is_rejected():
    raw = "여기 계획입니다:\n" + _payload() + "\n확인해 주세요."
    with pytest.raises(PlanValidationError):
        parse_plan(
            raw, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# Important 3(리뷰 2026-09-04) — 산문이 **코드펜스까지 감싸도** 거부한다. 위
# `test_prose_wrapped_json_is_rejected`의 입력에는 백틱이 전혀 없어 `_FENCED`의
# `\A...\Z` 앵커가 실행조차 되지 않았다 — 그 테스트가 재는 것은 "원문이 그냥 JSON
# 파싱에 실패하면 거부"뿐이었다. 이 테스트는 실제로 펜스가 있는데 그 앞뒤에 산문이
# 붙은 경우를 재현해 앵커가 산문-포함 매칭을 실제로 막는지 확인한다.
def test_prose_wrapped_fenced_json_is_rejected():
    raw = "여기 계획입니다:\n```json\n" + _payload() + "\n```\n확인해 주세요."
    with pytest.raises(PlanValidationError):
        parse_plan(
            raw, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# TASK-100 — 거부 사유가 **「잘림」과 「파서 불일치」를 가를 수 있어야** 한다. 이전 판은 앞 200자만
# 담아서 두 원인을 구별하지 못했다: 실물 실패의 `last_error`가 `'{\n  "focus": [...'`에서 끊겨
# 있었고 그것이 응답이 잘린 것인지 이 슬라이스가 자른 것인지 아무도 알 수 없었다(회차 기록
# `runs/2026-09-11-task98-production-prompt.md` §8). 그래서 **원문 길이 · 디코드 사유 · 끝부분**을
# 사유에 담는다 — 다음 실패가 스스로 원인을 말한다.
def test_undecodable_response_reports_length_and_decode_reason():
    truncated = _payload()[:150]

    with pytest.raises(PlanValidationError) as caught:
        parse_plan(
            truncated,
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )

    message = str(caught.value)
    assert "chars=150" in message, "원문 길이가 없으면 잘림을 판정할 수 없다"
    # 디코드 사유는 파이썬이 이미 갈라 준다 — 잘림은 `Unterminated`·`Expecting`, 뒤에 붙은
    # 산문은 `Extra data`다. 그 문구를 우리가 발명하지 않고 그대로 싣는다.
    assert "json_error=" in message
    assert truncated[-40:] in message, "끝부분이 없으면 어디서 끊겼는지 볼 수 없다"


# TASK-100 — 같은 사유 문구가 **뒤에 산문이 붙은** 경우를 잘림과 다르게 말해야 한다.
def test_trailing_prose_is_reported_as_extra_data():
    with pytest.raises(PlanValidationError) as caught:
        parse_plan(
            _payload() + "\n확인해 주세요.",
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )

    assert "Extra data" in str(caught.value)


# M7(리뷰 2026-09-04) — 하위 모델의 `extra="forbid"`도 실제로 걸리는지 확인한다.
# `test_unknown_field_is_rejected`는 최상위 `PlanOutput`만 재므로 `instruction`·
# `questions` 항목의 `model_config`가 지워져도 잡지 못한다.
def test_instruction_unknown_field_is_rejected():
    payload = _payload(
        instruction={
            "target_level": "A2",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "two short clauses",
            "hint_timing": "offer a starter after one long pause",
            "contexts": ["work update", "daily life", "plan"],
            "surprise": "nope",
        }
    )
    with pytest.raises(PlanValidationError):
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


def test_question_item_unknown_field_is_rejected():
    questions = [
        {"prompt": "q0", "context": "c0", "surprise": "nope"},
        {"prompt": "q1", "context": "c1"},
        {"prompt": "q2", "context": "c2"},
    ]
    with pytest.raises(PlanValidationError):
        parse_plan(
            _payload(questions=questions),
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )


# 미공개 이탈이었던 것을 여기서 등재한다(보고서 참조) — `SessionInstruction.focus`도
# 1~2개다. 문서 근거는 `PlanOutput.focus`와 같다(PRD.md:188 R11-2 · agent-system-prompt.md:19):
# 초점 패턴 자체가 1~2개이고, 지시문은 그 초점을 문장으로 옮긴 것일 뿐 개수가 늘거나
# 줄 이유가 없다. 빼면 `instruction.focus=[]`가 통과해 "초점 없는 세션 지시문"이 관문을
# 지나간다.
@pytest.mark.parametrize("count", [0, 3])
def test_instruction_focus_count_outside_one_to_two_is_rejected(count: int):
    focus = [{"pattern_key": f"k{i}", "target_form": "f"} for i in range(count)]
    payload = _payload(
        instruction={
            "target_level": "A2",
            "focus": focus,
            "sentence_length": "two short clauses",
            "hint_timing": "offer a starter after one long pause",
            "contexts": ["work update", "daily life", "plan"],
        }
    )
    with pytest.raises(PlanValidationError):
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# M5(리뷰 2026-09-04) — 001 `users.current_level` CHECK와 같은 값역인지 값 자체를
# 고정한다. `models/analysis.py`의 `test_category_and_severity_codes_match_the_schema_check`와
# 같은 선례.
def test_cefr_levels_match_the_schema_check():
    assert CEFR_LEVELS == ("A1", "A2", "B1", "B2", "C1", "C2")


# M6(리뷰 2026-09-04) — `contexts`·`notes` 항목 단위 비공백. `models/analysis.py`의
# `SuggestedContext`와 같은 선례(발명이 아니다). 개수 상한은 걸지 않는다(발명하지 않는다).
def test_blank_context_item_is_rejected():
    payload = _payload(
        instruction={
            "target_level": "A2",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "two short clauses",
            "hint_timing": "offer a starter after one long pause",
            "contexts": ["work update", "   "],
        }
    )
    with pytest.raises(PlanValidationError):
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


def test_blank_note_item_is_rejected():
    with pytest.raises(PlanValidationError):
        parse_plan(
            _payload(notes=["   "]),
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )


# M9(리뷰 2026-09-04) — `plan.py`와 `analysis.py`의 `_FENCED`가 "글자 그대로 같다"는
# 두 모듈 docstring의 주장을 지켜 주는 테스트. 한쪽만 고쳐지면 조용히 갈라지는데,
# 이 테스트가 있으면 그 갈라짐이 실패로 드러난다.
def test_fenced_regex_matches_analysis_module():
    from app.models.analysis import _FENCED as analysis_fenced
    from app.models.plan import _FENCED as plan_fenced

    assert plan_fenced.pattern == analysis_fenced.pattern


# 이탈 2(리뷰 2026-09-04) — `current_level` 자체가 값역 밖이면 거부한다. 가드
# (`parse_plan`의 `if current_level not in CEFR_LEVELS`)는 Step 3에서 이미 있었지만
# 전용 테스트가 없어 다음 리팩터가 초록 상태로 지울 위험이 있었다.
def test_unknown_current_level_is_rejected():
    with pytest.raises(PlanValidationError):
        parse_plan(
            _payload(),
            current_level="Z9",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_DEEPEST,
        )


# ── Task 7 — 지어낸 `pattern_id` 거부 가드 ────────────────────────────────────
#
# 계획서 Task 7 ①: 모델이 **형식만 맞는 UUID를 지어내면** pydantic도 통과하고(`UUID`
# 타입만 본다) DB도 통과한다(`focus_pattern_ids uuid[]`에 FK가 **없다**). 그러면 존재하지
# 않는 패턴 id가 조용히 저장되고 초점·복습 조회가 영구히 어긋난다 — 실패보다 나쁘다.
# 허용 집합은 프롬프트에 실린 것과 같아야 한다:
# `{r.pattern_id for r in due_reviews} | {m.pattern_id for m in chronic}`.


def test_focus_pattern_id_outside_the_allowed_set_is_rejected():
    invented = uuid4()
    assert invented not in _ALLOWED  # 헬퍼가 조용히 퇴화하지 않게 전제를 먼저 못 박는다
    payload = _payload(
        focus=[
            {
                "pattern_id": str(invented),
                "pattern_key": "article_missing",
                "target_form": "a/an/the",
            }
        ]
    )

    with pytest.raises(PlanValidationError, match=str(invented)):
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# ⚠️ **첫 항목만 보지 않는다.** 초점은 최대 2개이고, 첫 항목만 검사하는 구현은 두 번째에
# 지어낸 id를 실어도 통과한다 — 그 구멍이 이 슬라이스에서 반복된 실패 모드다.
def test_second_focus_item_is_checked_too():
    invented = uuid4()
    payload = _payload(
        focus=[
            {
                "pattern_id": str(_IDS[0]),
                "pattern_key": "article_missing",
                "target_form": "a/an/the",
            },
            {"pattern_id": str(invented), "pattern_key": "verb_tense_past", "target_form": "went"},
        ]
    )

    with pytest.raises(PlanValidationError, match=str(invented)):
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# 음성 케이스 — 허용 집합 안의 id 2개는 통과한다. 이것이 없으면 "항상 거부한다"는 구현도
# 위 두 테스트를 통과한다.
def test_two_allowed_focus_items_pass():
    payload = _payload(
        focus=[
            {
                "pattern_id": str(_IDS[0]),
                "pattern_key": "article_missing",
                "target_form": "a/an/the",
            },
            {"pattern_id": str(_IDS[1]), "pattern_key": "verb_tense_past", "target_form": "went"},
        ]
    )

    result = parse_plan(
        payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
    )

    assert [item.pattern_id for item in result.focus] == [_IDS[0], _IDS[1]]


# 후보가 0건인 콜드스타트에서는 **무엇을 내도** 거부된다 — `process_plan`이 그때 Claude를
# 부르지 않는 이유가 이것이다(계획서 Task 7 ②). 확실히 거부될 호출에 비용을 쓰지 않는다.
def test_empty_allowed_set_rejects_every_focus():
    with pytest.raises(PlanValidationError):
        parse_plan(
            _payload(), current_level="A2", allowed_pattern_ids=set(), deepest_pattern_id=None
        )


# 스키마 검증이 **먼저** 온다 — 지어낸 id와 규격 위반이 함께 있으면 pydantic 오류가 나야
# 한다. 순서가 뒤집히면 "규격 위반"이 "존재하지 않는 패턴"으로 잘못 보고된다.
def test_schema_violation_is_reported_before_the_pattern_id_guard():
    payload = _payload(
        focus=[{"pattern_id": str(uuid4()), "pattern_key": "", "target_form": "a/an/the"}]
    )

    with pytest.raises(PlanValidationError, match="failed validation"):
        parse_plan(
            payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_DEEPEST
        )


# ── AC11-2 — 가장 깊은 재발이 초점에 포함되어야 한다 ─────────────────────────
#
# 요구사항 AC11-2는 *"가장 깊은 재발이 초점이 되고"*를 요구하는데, 이 파일의 앞부분이
# 강제하던 것은 **개수와 비어 있지 않음**뿐이었다 — 독립 리뷰가 그것을 잡아 판정이
# 완료 → 부분으로 되돌아갔다(`docs/design/2026-09-06-review-outcomes.md` §2).
#
# 규칙의 정본은 그 §2다: **"가장 깊은 재발"은 만성 지표의 최다 `frequency`이고, 동률이면
# `recurring_sessions` → `recurring_days` 순으로 깬다. 초점 1~2개 중 최소 하나가 그 최상위와
# 일치해야 한다.** 순위 계산은 만성 목록을 소유한 `services/chronic.py`가 하고
# (`deepest_recurrence`), `parse_plan`은 그 결과 하나를 받아 **판정만** 한다 —
# `allowed_pattern_ids`와 같은 분업이다.
#
# ⚠️ **만성 목록이 비면 이 규칙을 적용하지 않는다**(`deepest_pattern_id=None`) — 최상위가
# 존재하지 않으므로 강제할 대상이 없고, 콜드스타트에서 계획 생성이 막히면 안 된다.


# ① 최상위가 초점에 **없으면 거부한다.** 이것이 이 절의 이유다.
def test_focus_without_the_deepest_recurrence_is_rejected():
    deepest = _IDS[1]
    assert deepest != _IDS[0], "전제가 퇴화했다 — 두 id 가 같으면 이 테스트는 공허하다"

    with pytest.raises(PlanValidationError) as exc:
        parse_plan(
            _payload(),  # 초점은 `_IDS[0]` 하나뿐이다
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=deepest,
        )

    # 거부 사유가 **무엇이 최상위였고 무엇이 왔는지**를 함께 말해야 한다 — 조용한 실패를
    # 만들지 않는다. 둘 중 하나만 적으면 job 이력만 보고는 어느 쪽이 어긋났는지 모른다.
    assert str(deepest) in str(exc.value)
    assert str(_IDS[0]) in str(exc.value)


# ② 최상위가 초점 **첫 항목**이면 통과한다.
def test_the_deepest_recurrence_as_the_first_focus_item_passes():
    payload = _payload(
        focus=[
            {"pattern_id": str(_IDS[0]), "pattern_key": "article_missing", "target_form": "a/the"},
            {"pattern_id": str(_IDS[1]), "pattern_key": "verb_tense_past", "target_form": "went"},
        ]
    )

    result = parse_plan(
        payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_IDS[0]
    )

    assert [item.pattern_id for item in result.focus] == [_IDS[0], _IDS[1]]


# ③ 최상위가 초점 **둘째 항목**이어도 통과한다.
#
# ⚠️ 이것이 **첫 항목만 검사하는 구현을 잡는다.** 요구사항은 "초점 중 하나가 최상위"이고
# "첫 초점이 최상위"가 아니다 — 첫 항목만 보는 구현은 정당한 계획을 거부한다(그리고 그
# 거부는 실물 모델 응답에서만 드러나 대역 테스트로는 안 보인다).
def test_the_deepest_recurrence_as_the_second_focus_item_passes():
    payload = _payload(
        focus=[
            {"pattern_id": str(_IDS[0]), "pattern_key": "article_missing", "target_form": "a/the"},
            {"pattern_id": str(_IDS[1]), "pattern_key": "verb_tense_past", "target_form": "went"},
        ]
    )

    result = parse_plan(
        payload, current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=_IDS[1]
    )

    assert [item.pattern_id for item in result.focus] == [_IDS[0], _IDS[1]]


# ④ **동률**일 때 `recurring_sessions`로 깬 최상위가 강제된다.
#
# 순위 계산(`deepest_recurrence`)과 강제(`parse_plan`)를 한 테스트에서 이어 붙인다 — 둘을
# 따로만 재면 "순위는 맞지만 그 결과가 강제에 전달되지 않는" 배선 오류가 남는다.
def test_the_tie_broken_top_is_the_one_that_is_enforced():
    loser = chronic_metric(_IDS[0], frequency=3, recurring_sessions=1, recurring_days=9)
    winner = chronic_metric(_IDS[1], frequency=3, recurring_sessions=4, recurring_days=1)
    top = deepest_recurrence([loser, winner])
    assert top is not None
    assert top.pattern_id == _IDS[1], "동률 처리가 바뀌었다 — 아래 단정의 전제가 깨졌다"

    # 동률에서 **진** 쪽만 초점으로 고른 계획은 거부된다.
    with pytest.raises(PlanValidationError, match=str(_IDS[1])):
        parse_plan(
            _payload(),  # 초점은 `_IDS[0]` = loser
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=top.pattern_id,
        )

    # 이긴 쪽을 고른 계획은 통과한다 — 음성 케이스가 없으면 "항상 거부한다"도 위를 통과한다.
    payload = _payload(
        focus=[
            {"pattern_id": str(_IDS[1]), "pattern_key": "verb_tense_past", "target_form": "went"}
        ]
    )
    result = parse_plan(
        payload,
        current_level="A2",
        allowed_pattern_ids=_ALLOWED,
        deepest_pattern_id=top.pattern_id,
    )
    assert [item.pattern_id for item in result.focus] == [_IDS[1]]


# ⑤ **만성 목록이 비면** 이 규칙은 적용되지 않는다 — 강제할 최상위가 없다.
#
# 콜드스타트에서 계획 생성이 막히면 안 된다(§2 경고 1). 복습 예정만 있는 사용자가
# 여기에 해당한다: `DueReview`에는 `frequency`가 없어 깊이 축을 만들 수 없다.
def test_an_empty_chronic_list_does_not_enforce_the_rule():
    assert deepest_recurrence([]) is None, "빈 목록의 계약이 바뀌었다 — 아래 전제가 깨졌다"

    result = parse_plan(
        _payload(), current_level="A2", allowed_pattern_ids=_ALLOWED, deepest_pattern_id=None
    )

    assert [item.pattern_id for item in result.focus] == [_IDS[0]]


# 순서 — 허용 집합 가드가 **먼저** 보고된다. 지어낸 id 는 최상위 누락보다 더 근본적인
# 위반이고(존재하지 않는 패턴이다), 순서가 뒤집히면 job 이력의 사유가 "최상위 누락"으로
# 바뀌어 어느 값이 문제였는지 읽을 수 없게 된다.
def test_the_allowed_set_guard_is_reported_before_the_deepest_guard():
    invented = uuid4()
    assert invented not in _ALLOWED
    payload = _payload(
        focus=[{"pattern_id": str(invented), "pattern_key": "k", "target_form": "f"}]
    )

    with pytest.raises(PlanValidationError, match="was not offered in the prompt"):
        parse_plan(
            payload,
            current_level="A2",
            allowed_pattern_ids=_ALLOWED,
            deepest_pattern_id=_IDS[1],  # 초점에 없다 — 두 가드가 함께 걸리는 입력이다
        )
