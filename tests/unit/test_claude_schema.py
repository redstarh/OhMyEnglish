"""Task 5 — Claude 출력 경계 검증 + 클라이언트 포트 테스트 (AC W7).

Claude의 응답은 **신뢰할 수 없는 외부 입력**이다. 이 경계에서 거부하지 않으면
`error_patterns.category` / `error_occurrences.severity` CHECK가 트랜잭션
중간에 터져 그 발화의 결과 전체를 잃는다(그리고 실패 이유가 DB 제약 위반으로
뭉개진다). 그래서 스키마는 `extra="forbid"` + Literal + 범위 제약으로 좁히고,
파싱은 `AnalysisValidationError` 하나로 수렴시킨다.

DB를 쓰지 않는 순수 단위 테스트다 — `db_conn` 픽스처를 요청하지 않으므로
PostgreSQL 없이도 돈다. 실제 Bedrock 호출은 하지 않는다(W-live는 별도 태스크):
boto3 클라이언트 팩토리를 스텁으로 대체해 요청 본문과 응답 추출만 검증한다.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID, uuid4

import pytest
from conftest import default_finding

from app.config import Settings
from app.models.analysis import (
    ERROR_CATEGORIES,
    SEVERITIES,
    AnalysisResult,
    AnalysisValidationError,
    ErrorFinding,
    is_valid_new_pattern_key,
    parse_analysis,
)
from app.models.usage import TokenUsage
from app.workers import claude_client as claude_client_module
from app.workers.claude_client import (
    ANTHROPIC_VERSION,
    MAX_TOKENS,
    BedrockClaudeClient,
    FakeClaudeClient,
    extract_text,
    extract_usage,
)


def _raw(*findings: dict[str, Any]) -> str:
    return json.dumps({"findings": list(findings)})


# 코드값은 001 스키마의 CHECK와 반드시 일치해야 한다 — 어긋나면 저장 시점에
# CHECK 위반으로 터진다. 두 곳이 갈라지지 않도록 값 자체를 고정한다.
def test_category_and_severity_codes_match_the_schema_check():
    assert ERROR_CATEGORIES == (
        "verb_tense",
        "article",
        "preposition",
        "word_order",
        "verb_form",
        "business_expression",
        "pronunciation_intonation",
    )
    assert SEVERITIES == ("low", "medium", "high")


# ① 정상 JSON → AnalysisResult
def test_parse_analysis_accepts_valid_json():
    result = parse_analysis(_raw(default_finding()))

    assert isinstance(result, AnalysisResult)
    assert len(result.findings) == 1
    finding = result.findings[0]
    assert isinstance(finding, ErrorFinding)
    assert finding.category == "article"
    assert finding.pattern_key == "article_missing_before_place_noun"
    assert finding.target_form == "go to the gym"
    assert finding.original_span == "go to gym"
    assert finding.correction == "go to the gym"
    assert finding.severity == "medium"
    assert finding.confidence == 0.9


# 오류 0건은 정상 응답이다 — 거부(검증 실패)와 구분되어야 한다.
def test_parse_analysis_accepts_empty_findings():
    result = parse_analysis('{"findings": []}')

    assert result.findings == []


# ② 필수 필드 누락 → 거부
@pytest.mark.parametrize(
    "missing",
    [
        "category",
        "pattern_key",
        "target_form",
        "original_span",
        "correction",
        "explanation",
        "severity",
        "confidence",
    ],
)
def test_parse_analysis_rejects_missing_required_field(missing: str):
    finding = default_finding()
    del finding[missing]

    with pytest.raises(AnalysisValidationError):
        parse_analysis(_raw(finding))


# findings 자체가 없는 응답도 거부한다 (최상위 필수 필드)
def test_parse_analysis_rejects_missing_findings_key():
    with pytest.raises(AnalysisValidationError):
        parse_analysis("{}")


# ③ severity:"critical" → 거부 (001 CHECK에 없는 값)
def test_parse_analysis_rejects_unknown_severity():
    with pytest.raises(AnalysisValidationError):
        parse_analysis(_raw(default_finding(severity="critical")))


# ④ confidence:1.5 → 거부 (numeric(3,2) check between 0 and 1)
#
# ✅ **뮤테이션 KILL 확인 — W7** (`TASK-73`. 2026-09-10 직접 관측).
# `models/analysis.py` 의 `confidence: float = pydantic.Field(ge=0, le=1)` 에서 범위 제약만 떼고
# `confidence: float` 로 두니 **이 테스트가 두 파라미터(`1.5`·`-0.1`)에서 전부 FAIL** 했다.
# ⚠️ 파라미터가 둘인 것이 여기서 값어치를 한다 — 상한만 검사하면 하한 제약(`ge=0`)을 떼는 변이가
# 살아남는다.
@pytest.mark.parametrize("confidence", [1.5, -0.1])
def test_parse_analysis_rejects_out_of_range_confidence(confidence: float):
    with pytest.raises(AnalysisValidationError):
        parse_analysis(_raw(default_finding(confidence=confidence)))


# ④ 경계값 0 / 1은 허용된다 (ge=0, le=1)
@pytest.mark.parametrize("confidence", [0, 1])
def test_parse_analysis_accepts_confidence_boundaries(confidence: float):
    result = parse_analysis(_raw(default_finding(confidence=confidence)))

    assert result.findings[0].confidence == float(confidence)


# ⑤ category:"noun" → 거부 (001 CHECK에 없는 값)
def test_parse_analysis_rejects_unknown_category():
    with pytest.raises(AnalysisValidationError):
        parse_analysis(_raw(default_finding(category="noun")))


# ⑥ 미지 필드 → 거부 (extra="forbid") — finding과 최상위 양쪽
def test_parse_analysis_rejects_unknown_field_in_finding():
    with pytest.raises(AnalysisValidationError):
        parse_analysis(_raw(default_finding(span_start=3)))


def test_parse_analysis_rejects_unknown_top_level_field():
    raw = json.dumps({"findings": [default_finding()], "summary": "nice try"})

    with pytest.raises(AnalysisValidationError):
        parse_analysis(raw)


# 빈 문자열 필드는 거부한다 — pattern_key가 비면 사용자 패턴이 빈 key로 병합된다.
@pytest.mark.parametrize(
    "field", ["pattern_key", "target_form", "original_span", "correction", "explanation"]
)
@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_parse_analysis_rejects_blank_text_field(field: str, value: str):
    with pytest.raises(AnalysisValidationError):
        parse_analysis(_raw(default_finding(**{field: value})))


# Fix round 1 (I-5) — 앞뒤 공백은 경계에서 깎는다. 공백 하나가 붙은 pattern_key가
# 기존 key와 다른 값으로 취급되면 병합이 깨지고(그 발화는 5회 재시도 후 failed),
# original_span에 붙은 공백은 사용자에게 그대로 보인다.
@pytest.mark.parametrize(
    "field", ["pattern_key", "target_form", "original_span", "correction", "explanation"]
)
def test_parse_analysis_strips_surrounding_whitespace(field: str):
    expected = default_finding()[field]

    result = parse_analysis(_raw(default_finding(**{field: f"  {expected}\n"})))

    assert getattr(result.findings[0], field) == expected


# ⑦ 코드펜스로 감싼 JSON → 펜스 제거 후 통과
@pytest.mark.parametrize("fence", ["```json", "```JSON", "```"])
def test_parse_analysis_strips_code_fence(fence: str):
    raw = f"{fence}\n{_raw(default_finding())}\n```"

    result = parse_analysis(raw)

    assert len(result.findings) == 1


# ⑦ 펜스를 제거해도 JSON이 아니면 거부
@pytest.mark.parametrize(
    "raw",
    [
        "여기 분석 결과입니다: 관사가 빠졌습니다.",
        "```json\nnot json at all\n```",
        "",
        "   ",
        "null",
        "[]",
    ],
)
def test_parse_analysis_rejects_non_json_response(raw: str):
    with pytest.raises(AnalysisValidationError):
        parse_analysis(raw)


# 검증 실패는 pydantic ValidationError가 아니라 하나의 도메인 예외로 수렴한다 —
# 호출자(process_analysis)가 fail_or_retry 한 경로로 처리할 수 있어야 한다.
def test_validation_error_is_a_value_error_and_carries_context():
    with pytest.raises(AnalysisValidationError) as excinfo:
        parse_analysis(_raw(default_finding(severity="critical")))

    assert isinstance(excinfo.value, ValueError)
    assert "critical" in str(excinfo.value)


# 신규 pattern_key 형식 규칙: ^{category}_[a-z0-9_]+$ (§5.6 발명 규칙)
@pytest.mark.parametrize(
    ("category", "pattern_key", "valid"),
    [
        ("article", "article_missing_before_place_noun", True),
        ("verb_tense", "verb_tense_past_in_work_update", True),
        ("article", "article_a", True),
        ("article", "missing_article_before_gym", False),  # 접두 없음
        ("article", "article_", False),  # 접미가 비었다
        ("article", "article_Missing_Article", False),  # 대문자
        ("article", "article_missing-article", False),  # 하이픈
        ("article", "article_missing article", False),  # 공백
        ("verb_tense", "verb_tense", False),  # 구분자 없음
        ("preposition", "article_missing_before_noun", False),  # 다른 카테고리 접두
    ],
)
def test_is_valid_new_pattern_key(category: str, pattern_key: str, valid: bool):
    assert is_valid_new_pattern_key(category, pattern_key) is valid


# FakeClaudeClient — 응답을 순서대로 돌려주고 받은 프롬프트를 기록한다
async def test_fake_claude_client_returns_responses_in_order_and_records_prompts():
    claude = FakeClaudeClient(["first", "second"])

    assert await claude.analyze("prompt 1") == "first"
    assert await claude.analyze("prompt 2") == "second"
    assert claude.prompts == ["prompt 1", "prompt 2"]


async def test_fake_claude_client_raises_when_responses_are_exhausted():
    claude = FakeClaudeClient(["only one"])
    await claude.analyze("prompt 1")

    with pytest.raises(AssertionError, match="exhausted"):
        await claude.analyze("prompt 2")


# --- BedrockClaudeClient — 실제 호출 없이 요청 본문과 응답 추출만 검증한다 ---


class _StubBody:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


class _StubBedrockRuntime:
    """`invoke_model` 호출을 기록하는 boto3 `bedrock-runtime` 대역."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[dict[str, Any]] = []

    def invoke_model(self, *, modelId: str, body: str) -> dict[str, Any]:  # noqa: N803
        self.calls.append({"modelId": modelId, "body": json.loads(body)})
        return {"body": _StubBody(self._payload)}


def _test_settings() -> Settings:
    # ⛔ `_env_file=None` — 이것 없이는 `app/backend/.env`가 이 인스턴스를 먹인다 (TASK-35).
    # 실측(2026-09-08): 그 파일에 `CLAUDE_MODEL_ID=bogus-from-dotenv`를 넣으면 아래
    # `test_bedrock_client_sends_the_messages_api_body_for_the_configured_model`이 **깨졌다.**
    # ⚠️ `.env.example` 첫 줄이 *"Copy this file to app/backend/.env"*이므로 표준 온보딩이
    # 그 창을 연다 — 즉 이것은 가정된 위험이 아니라 관측된 것이다.
    return Settings(
        # `ty`(alpha)는 pydantic-settings가 런타임에 합성하는 `__init__`을 모델링하지
        # 못한다 — 같은 이유의 억제가 이 리포에 이미 있다(`missing-argument`).
        _env_file=None,  # ty: ignore[unknown-argument]
        database_url="postgresql://fake:fake@localhost/fake",
        aws_region="us-west-2",
    )


async def test_bedrock_client_sends_the_messages_api_body_for_the_configured_model(
    monkeypatch: pytest.MonkeyPatch,
):
    stub = _StubBedrockRuntime({"content": [{"type": "text", "text": '{"findings": []}'}]})
    monkeypatch.setattr(claude_client_module, "bedrock_client", lambda: stub)
    # 창이 둘이다 — `_env_file=None`이 `.env`를, 이 한 줄이 **셸 환경변수**를 닫는다 (TASK-35).
    # 아래 리터럴 단정이 재려는 것은 `Settings`의 **선언된 기본값**이고 운영자의 튜닝이 아니다.
    # ⛔ 지우지 마라: 이 줄이 없으면 셸에 `CLAUDE_MODEL_ID`가 있는 개발자에게만 red 가 난다.
    monkeypatch.delenv("CLAUDE_MODEL_ID", raising=False)
    settings = _test_settings()

    raw = await BedrockClaudeClient(settings).analyze("analyze this")

    assert raw == '{"findings": []}'
    assert len(stub.calls) == 1
    call = stub.calls[0]
    # 모델 ID는 Settings가 SoT다 — 모듈에 하드코딩하지 않는다.
    assert call["modelId"] == settings.claude_model_id == "us.anthropic.claude-opus-5"
    assert call["body"] == {
        "anthropic_version": ANTHROPIC_VERSION,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": "analyze this"}],
    }
    assert ANTHROPIC_VERSION == "bedrock-2023-05-31"


# Fix round 1 (I-1) — Opus 5는 thinking이 기본 on이고 thinking 토큰이 max_tokens
# 예산을 함께 쓴다. 4096이면 사고가 예산을 먹고 findings JSON이 중간에 잘린다.
def test_max_tokens_leaves_room_for_thinking_plus_the_findings_json():
    assert MAX_TOKENS == 16000


# Claude Opus 5는 thinking이 기본 on이라 content에 text 아닌 블록이 섞여 온다.
# 첫 블록을 그냥 읽으면 빈 문자열을 파서에 넘겨 정상 응답을 실패로 만든다.
def test_extract_text_skips_non_text_content_blocks():
    payload = {
        "content": [
            {"type": "thinking", "thinking": ""},
            {"type": "text", "text": '{"findings":'},
            {"type": "text", "text": " []}"},
        ]
    }

    assert extract_text(payload) == '{"findings": []}'


def test_extract_text_returns_empty_string_when_the_turn_ended_without_text():
    # stop_reason이 정상 종료인데 text가 없는 응답은 parse_analysis의 단일 거부
    # 경로로 내려간다(빈 문자열 → "not JSON").
    assert extract_text({"content": [{"type": "thinking", "thinking": ""}]}) == ""
    assert extract_text({}) == ""
    assert extract_text({"stop_reason": "end_turn", "content": []}) == ""


# Fix round 1 (I-1) — 절단과 거부는 "JSON 아님"으로 뭉개지면 안 된다. last_error에
# 원인이 남아야 예산·프롬프트 문제와 파싱 문제를 구분할 수 있다.
def test_extract_text_reports_truncation_at_max_tokens():
    payload = {"stop_reason": "max_tokens", "content": [{"type": "text", "text": '{"find'}]}

    with pytest.raises(AnalysisValidationError) as excinfo:
        extract_text(payload)

    assert "max_tokens" in str(excinfo.value)


def test_extract_text_reports_a_refusal_with_its_category():
    payload = {
        "stop_reason": "refusal",
        "stop_details": {"type": "refusal", "category": "cyber"},
        "content": [],
    }

    with pytest.raises(AnalysisValidationError) as excinfo:
        extract_text(payload)

    assert "refusal" in str(excinfo.value)
    assert "cyber" in str(excinfo.value)


def test_extract_text_reports_a_refusal_without_stop_details():
    with pytest.raises(AnalysisValidationError, match="refusal"):
        extract_text({"stop_reason": "refusal", "content": []})


async def test_bedrock_client_surfaces_truncation_as_a_validation_error(
    monkeypatch: pytest.MonkeyPatch,
):
    stub = _StubBedrockRuntime(
        {"stop_reason": "max_tokens", "content": [{"type": "text", "text": '{"findings": [{'}]}
    )
    monkeypatch.setattr(claude_client_module, "bedrock_client", lambda: stub)

    with pytest.raises(AnalysisValidationError, match="max_tokens"):
        await BedrockClaudeClient(_test_settings()).analyze("analyze this")


# ── `TASK-60`(사용자 결정 66) — 호출마다 토큰 사용량을 적는다 ──────────────────────
#
# 이 리포는 Bedrock 호출의 토큰을 **어디에도** 적지 않아 비용을 볼 수단이 없었다. 아래 넷이 그
# 기록의 계약을 잰다: 값을 읽는가 · 없을 때 지어내지 않는가 · 실패한 호출도 적는가 ·
# 귀속을 넘기는가.


def test_extract_usage_reads_both_token_counts():
    payload = {"usage": {"input_tokens": 3690, "output_tokens": 412}, "content": []}

    assert extract_usage(payload) == TokenUsage(input_tokens=3690, output_tokens=412)


def test_extract_usage_returns_none_instead_of_inventing_zeros():
    """⛔ `0` 은 「토큰을 쓰지 않았다」는 **주장**이고 그런 호출은 없다 — 적으면 합계가 낮아진다."""
    assert extract_usage({"content": []}) is None
    assert extract_usage({"usage": {}}) is None
    assert extract_usage({"usage": {"input_tokens": 10}}) is None
    # 문자열로 오는 판(스펙 변경·프록시)을 정수로 믿지 않는다.
    assert extract_usage({"usage": {"input_tokens": "10", "output_tokens": "2"}}) is None


async def test_bedrock_client_records_usage_with_the_attribution_it_was_given(
    monkeypatch: pytest.MonkeyPatch,
):
    stub = _StubBedrockRuntime(
        {
            "content": [{"type": "text", "text": '{"findings": []}'}],
            "usage": {"input_tokens": 3690, "output_tokens": 412},
        }
    )
    monkeypatch.setattr(claude_client_module, "bedrock_client", lambda: stub)
    monkeypatch.delenv("CLAUDE_MODEL_ID", raising=False)
    settings = _test_settings()
    recorded: list[tuple[TokenUsage, str, str, UUID | None]] = []

    async def sink(
        usage: TokenUsage, *, model_id: str, purpose: str, job_id: UUID | None
    ) -> None:
        recorded.append((usage, model_id, purpose, job_id))

    job_id = uuid4()
    client = BedrockClaudeClient(settings, usage_sink=sink)

    raw = await client.analyze("analyze this", purpose="plan", job_id=job_id)

    assert raw == '{"findings": []}'
    assert recorded == [
        (TokenUsage(input_tokens=3690, output_tokens=412), settings.claude_model_id, "plan", job_id)
    ]


async def test_the_client_records_a_truncated_call_too_because_it_still_cost_money(
    monkeypatch: pytest.MonkeyPatch,
):
    """⛔ 절단·거부도 **돈이 나간 호출**이다 — 기록을 `extract_text` 뒤에 두면 그 비용이 빠진다.

    ⚠️ 이 음성 케이스가 순서의 판별력을 만든다. 없으면 기록을 예외 뒤로 옮겨도 초록이고, 그러면
    「비용이 왜 늘었는가」를 설명할 수 없다(참고 프로젝트가 예열 호출까지 적은 이유와 같다).
    """
    stub = _StubBedrockRuntime(
        {
            "stop_reason": "max_tokens",
            "content": [{"type": "text", "text": '{"findings": [{'}],
            "usage": {"input_tokens": 3690, "output_tokens": 16000},
        }
    )
    monkeypatch.setattr(claude_client_module, "bedrock_client", lambda: stub)
    recorded: list[TokenUsage] = []

    async def sink(usage: TokenUsage, **_: object) -> None:
        recorded.append(usage)

    with pytest.raises(AnalysisValidationError, match="max_tokens"):
        await BedrockClaudeClient(_test_settings(), usage_sink=sink).analyze("analyze this")

    assert recorded == [TokenUsage(input_tokens=3690, output_tokens=16000)]


async def test_the_client_does_not_call_the_sink_when_the_response_omits_usage(
    monkeypatch: pytest.MonkeyPatch,
):
    stub = _StubBedrockRuntime({"content": [{"type": "text", "text": "{}"}]})
    monkeypatch.setattr(claude_client_module, "bedrock_client", lambda: stub)
    called = False

    async def sink(usage: TokenUsage, **_: object) -> None:
        nonlocal called
        called = True

    await BedrockClaudeClient(_test_settings(), usage_sink=sink).analyze("analyze this")

    assert called is False, "usage 가 없는데 행을 만들면 0 토큰 호출을 발명한다"


# ── 006/슬라이스 1 — suggested_contexts (설계서 §8.2, PRD.md:92) ────────────────


def test_finding_accepts_suggested_contexts_and_strips_each_item():
    padded = ["  퇴근 후 운동 계획 말하기 ", "회의에서 진행 상황 보고"]
    payload = {"findings": [default_finding(suggested_contexts=padded)]}

    result = parse_analysis(json.dumps(payload))

    assert result.findings[0].suggested_contexts == [
        "퇴근 후 운동 계획 말하기",
        "회의에서 진행 상황 보고",
    ]


def test_finding_defaults_suggested_contexts_to_empty_when_absent():
    """필드가 없는 응답은 계약 위반이 아니다 — §8.2가 nullable로 뒀고, 이 기본값이
    기존 픽스처(conftest.default_finding 8필드)와 하네스 시나리오의 무회귀를 지킨다."""
    result = parse_analysis(json.dumps({"findings": [default_finding()]}))

    assert result.findings[0].suggested_contexts == []


# ⚠️ 이 절의 규칙: **부가 필드의 규격 위반은 그 항목만 버린다.** 응답 전체를 거부하면
# 저가치 필드 하나가 그 발화의 **교정 전체**를 태운다 — `suggested_contexts`가 없어도
# 학습자는 교정을 받아야 한다. `findings`의 엄격함은 그대로다(아래 마지막 테스트가 지킨다).
def test_finding_drops_a_blank_suggested_context_instead_of_rejecting():
    payload = {"findings": [default_finding(suggested_contexts=["집에서 말하기", "   "])]}

    result = parse_analysis(json.dumps(payload))

    assert result.findings[0].suggested_contexts == ["집에서 말하기"]


def test_finding_drops_suggested_contexts_that_are_not_a_list():
    """모델이 문자열 하나로 답해도 그 발화의 교정을 잃지 않는다."""
    payload = {"findings": [default_finding(suggested_contexts="집에서 말하기")]}

    result = parse_analysis(json.dumps(payload))

    assert result.findings[0].suggested_contexts == []
    assert result.findings[0].correction == "go to the gym"


# ── 슬라이스 1 — attempts (재발화 정답 여부, 설계서 §8.1·§11 미결 2) ─────────────

RETRIED_KEY = "article_missing_before_place_noun"


def test_result_parses_attempts_with_their_outcome():
    payload = {"findings": [], "attempts": [{"pattern_key": RETRIED_KEY, "outcome": "correct"}]}

    result = parse_analysis(json.dumps(payload))

    assert result.attempts[0].pattern_key == RETRIED_KEY
    assert result.attempts[0].outcome == "correct"


def test_result_defaults_attempts_to_empty_when_absent():
    """대부분의 발화에는 재시도가 없다 — 기본값이 없으면 기존 픽스처가 전부 깨진다."""
    assert parse_analysis(json.dumps({"findings": []})).attempts == []


# 값역 밖 `outcome`이 006 CHECK에 닿으면 저장 트랜잭션 중간에 터진다 — 그래서 경계에서
# 막아야 한다. 단 **막는 방법이 "그 항목만 버리기"** 여야 한다: 응답 전체를 거부하면
# 그 발화의 교정까지 함께 사라져 막으려던 손실이 그대로 일어난다(실측 확인).
@pytest.mark.parametrize(
    ("label", "attempt"),
    [
        ("값역 밖 outcome", {"pattern_key": RETRIED_KEY, "outcome": "pending"}),
        ("여분 필드", {"pattern_key": RETRIED_KEY, "outcome": "correct", "confidence": 0.8}),
        ("빈 pattern_key", {"pattern_key": "   ", "outcome": "correct"}),
        ("outcome 누락", {"pattern_key": RETRIED_KEY}),
        ("항목이 객체가 아님", "correct"),
    ],
)
def test_result_drops_a_malformed_attempt_and_keeps_the_findings(label: str, attempt: object):
    payload = {"findings": [default_finding()], "attempts": [attempt]}

    result = parse_analysis(json.dumps(payload))

    assert result.attempts == [], label
    assert len(result.findings) == 1, f"{label}: 교정이 사라졌다"


def test_a_valid_attempt_survives_next_to_a_malformed_one():
    """항목 단위로 버린다 — 성한 판정을 함께 잃지 않는다."""
    payload = {
        "findings": [],
        "attempts": [
            {"pattern_key": "bogus", "outcome": "wat"},
            {"pattern_key": RETRIED_KEY, "outcome": "correct"},
        ],
    }

    result = parse_analysis(json.dumps(payload))

    assert [(a.pattern_key, a.outcome) for a in result.attempts] == [(RETRIED_KEY, "correct")]


def test_findings_stay_strict_while_the_side_fields_are_lenient():
    """비대칭의 반쪽 — `findings`의 규격 위반은 여전히 응답 전체를 거부한다.
    규격 밖 신규 key를 그냥 저장하면 병합되지 않는 쌍둥이 패턴이 영구히 남기 때문이다."""
    with pytest.raises(AnalysisValidationError):
        parse_analysis(json.dumps({"findings": [default_finding(severity="critical")]}))
