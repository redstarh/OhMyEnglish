"""계획 출력 계약과 거부 경계 (AS5, 계획서 Task 5).

`app.models.analysis`(Task 5 이전 슬라이스)와 같은 자리를 차지한다 — Claude의 계획 출력은
신뢰할 수 없는 외부 입력이고, 여기서 좁히지 않으면 `session_plans`의 CHECK
(`focus_pattern_ids` 1~2개 · `questions` 3~5개 · `reason` 공백 금지 · `target_level` 값역,
007 마이그레이션)에 부딪혀 저장 트랜잭션 중간에 터진다. AS5는 **저장 전에** 거부해
반쯤 검증된 계획을 쓰지 않는다(설계서 §9 Failure).

DB를 쓰지 않는 순수 단위 테스트다 — `db_conn` 픽스처를 요청하지 않으므로 PostgreSQL 없이도 돈다.
"""

import json
from uuid import uuid4

import pytest

from app.models.plan import PlanValidationError, parse_plan


def _payload(**overrides: object) -> str:
    pattern_id = str(uuid4())
    body: dict[str, object] = {
        "focus": [
            {"pattern_id": pattern_id, "pattern_key": "article_missing", "target_form": "a/an/the"}
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
    result = parse_plan(_payload(), current_level="A2")

    assert len(result.focus) == 1
    assert len(result.questions) == 3
    assert result.reason.strip() != ""
    assert result.level.action == "keep"


# AS5 ① 추천 이유가 비어 있으면 거부한다 (PRD.md:189 R11-3 — 이유 없는 추천은 검증할 수 없다)
@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_blank_reason_is_rejected(blank: str):
    with pytest.raises(PlanValidationError):
        parse_plan(_payload(reason=blank), current_level="A2")


# AS5 ② 질문 수가 3~5 밖이면 거부한다 (PRD.md:188 R11-2)
@pytest.mark.parametrize("count", [2, 6])
def test_question_count_outside_three_to_five_is_rejected(count: int):
    questions = [{"prompt": f"q{i}", "context": f"c{i}"} for i in range(count)]
    with pytest.raises(PlanValidationError):
        parse_plan(_payload(questions=questions), current_level="A2")


# 초점 패턴은 1~2개다 (PRD.md:188 · agent-system-prompt.md:19)
@pytest.mark.parametrize("count", [0, 3])
def test_focus_count_outside_one_to_two_is_rejected(count: int):
    focus = [
        {"pattern_id": str(uuid4()), "pattern_key": f"k{i}", "target_form": "f"}
        for i in range(count)
    ]
    with pytest.raises(PlanValidationError):
        parse_plan(_payload(focus=focus), current_level="A2")


# AS5 ③ CEFR 값역 밖이면 거부한다 (001 의 CHECK 와 같은 값역)
#
# `level.target_level`도 함께 "Z9"로 맞춘다 — `target_level`만 바꾸면
# `target_level != level.target_level` 불일치 검증에 걸려서 거부되고, 그 경우
# 이 테스트는 CEFR 값역 검증이 아니라 그 불일치 검증을 재는 것이 된다(두 검증이
# 같은 관측 결과를 내는 confound). 두 필드를 같은 값으로 맞춰야 CEFR 값역 검증만
# 단독으로 걸리는지 확인할 수 있다(뮤테이션 검증: target_level 을 CefrLevel 에서
# str 로 넓히면 이 confound 때문에 그래도 통과해 버린다 — 직접 확인함).
def test_unknown_level_is_rejected():
    with pytest.raises(PlanValidationError):
        parse_plan(
            _payload(
                target_level="Z9",
                level={"action": "keep", "target_level": "Z9", "reason": "정답률이 아직 낮습니다."},
            ),
            current_level="A2",
        )


# AS7 — 두 단계 도약은 거부한다. h-doc 이 경고한 "목표 수준을 현재 수준으로 착각"을 구조로 막는다.
def test_two_step_jump_is_rejected():
    payload = _payload(
        target_level="B2",
        level={"action": "up", "target_level": "B2", "reason": "빠르게 좋아졌습니다."},
    )
    with pytest.raises(PlanValidationError):
        parse_plan(payload, current_level="A2")


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
    assert parse_plan(payload, current_level="A2").level.target_level == "B1"


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
    assert parse_plan(payload, current_level="A2").level.action == "down"


# 계획의 난이도와 수준 판단이 어긋나면 거부한다 — 두 값이 다르면 어느 것이 오늘의 목표인지 모른다.
def test_target_level_must_match_level_decision():
    payload = _payload(
        target_level="A2",
        level={"action": "up", "target_level": "B1", "reason": "좋아졌습니다."},
    )
    with pytest.raises(PlanValidationError):
        parse_plan(payload, current_level="A2")


# 규격 밖 필드가 섞이면 거부한다 (슬라이스 1과 같은 extra="forbid" 규약)
def test_unknown_field_is_rejected():
    with pytest.raises(PlanValidationError):
        parse_plan(_payload(surprise="nope"), current_level="A2")


# 코드펜스로 감싼 응답은 파싱한다 — 프롬프트가 "펜스 없이"를 요구해도 모델이 종종 붙인다.
def test_code_fenced_json_parses():
    raw = "```json\n" + _payload() + "\n```"
    assert parse_plan(raw, current_level="A2").target_level == "A2"


# 산문으로 감싼 응답은 **거부한다.** 계약을 지키지 않은 응답은 실패로 보고하는 것이
# 이 리포의 확립된 선택이다 — 산문 중간에서 JSON을 긁어내지 않는다.
def test_prose_wrapped_json_is_rejected():
    raw = "여기 계획입니다:\n" + _payload() + "\n확인해 주세요."
    with pytest.raises(PlanValidationError):
        parse_plan(raw, current_level="A2")
