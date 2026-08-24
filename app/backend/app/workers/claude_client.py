"""Claude 포트 + Bedrock 구현 (설계서 §5.4, AC W7 경계).

분석 파이프라인은 `ClaudeClient` **프로토콜**에만 의존한다. 그래서 테스트는
`FakeClaudeClient`로 응답을 고정하고, 실물 경로(`BedrockClaudeClient`)는
자격증명·네트워크 없이도 파이프라인 전체를 검증할 수 있다. 포트의 반환값이
파싱된 객체가 아니라 **원문 문자열**인 것도 같은 이유다 — 출력 검증(W7)은
`models.analysis.parse_analysis` 한 곳에서만 일어나야 하고, 포트 구현마다
검증이 흩어지면 fake와 실물의 엄격함이 갈라진다.

두 가지 경계 주의:

* **boto3는 동기다.** 워커는 asyncio 루프이므로 `invoke_model`을 그대로 await
  없이 호출하면 그 수십 초 동안 이벤트 루프 전체(FastAPI 요청 처리 포함)가
  멈춘다. `asyncio.to_thread`로 스레드에 넘긴다.
* **응답 `content`에는 text 아닌 블록이 섞인다.** Claude Opus 5는 thinking이
  기본 on이라 `content[0]`가 thinking 블록일 수 있다. 첫 블록을 그냥 읽으면
  정상 응답을 "JSON 아님"으로 실패시킨다 — `extract_text`가 text 블록만 모은다.
* **`stop_reason`을 읽는다.** 예산 절단(`max_tokens`)과 거부(`refusal`)는
  "응답이 온전하지 않다"는 서버의 명시적 신고다. 이를 무시하고 잘린 텍스트를
  파서에 넘기면 `last_error`에 "not JSON"만 남아, 예산·프롬프트 문제와 진짜
  파싱 문제를 구분할 수 없다.

자격증명은 `config.bedrock_client()` 팩토리에만 있다(F5) — 이 모듈은 boto3나
토큰을 직접 다루지 않는다. 모델 ID도 `Settings.claude_model_id`가 SoT다.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol

from app.config import Settings, bedrock_client
from app.models.analysis import AnalysisValidationError

# Bedrock InvokeModel의 Anthropic Messages 본문 규격 (모델 버전이 아니라 본문 스키마 버전).
ANTHROPIC_VERSION = "bedrock-2023-05-31"

# 출력 상한. findings JSON 자체는 짧지만 **Claude Opus 5는 thinking이 기본 on이고
# thinking 토큰이 이 예산을 함께 쓴다** — 4096이면 사고가 예산을 먹고 JSON이 중간에
# 잘려 온다(`stop_reason="max_tokens"`). 비스트리밍 요청의 권장 기본값을 쓴다:
# 넉넉하지만 HTTP 타임아웃 아래로 유지되는 값이다.
MAX_TOKENS = 16000

# 응답이 온전하지 않다는 서버 신고. 그대로 파서에 넘기면 원인이 뭉개진다.
STOP_REASON_TRUNCATED = "max_tokens"
STOP_REASON_REFUSAL = "refusal"


class ClaudeClient(Protocol):
    """분석 프롬프트를 넣고 **원문 텍스트**를 받는다 (JSON 파싱은 호출자의 몫)."""

    async def analyze(self, prompt: str) -> str: ...


def build_invoke_body(prompt: str) -> str:
    """Bedrock InvokeModel 본문 (JSON 문자열)."""
    return json.dumps(
        {
            "anthropic_version": ANTHROPIC_VERSION,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
    )


def extract_text(payload: dict[str, Any]) -> str:
    """응답 `content`에서 text 블록만 이어붙인다.

    먼저 `stop_reason`을 본다. 예산 절단과 거부는 **그 사실 자체가 실패 사유**이므로
    `AnalysisValidationError`로 올려 `last_error`에 남긴다(호출자는 이 예외를 다른
    검증 실패와 같은 경로로 처리한다). 잘린 텍스트를 그대로 파서에 넘기면 사유가
    "not JSON"으로 뭉개져, 예산을 올려야 하는 상황인지 프롬프트를 고쳐야 하는
    상황인지 로그만 보고는 알 수 없다.

    정상 종료인데 text 블록이 없는 경우는 빈 문자열을 돌려준다 —
    `parse_analysis`의 단일 거부 경로로 흘려보낸다.
    """
    stop_reason = payload.get("stop_reason")
    if stop_reason == STOP_REASON_TRUNCATED:
        raise AnalysisValidationError(
            f"claude response hit the output budget (stop_reason={STOP_REASON_TRUNCATED}, "
            f"max_tokens={MAX_TOKENS}) — the findings JSON is incomplete"
        )
    if stop_reason == STOP_REASON_REFUSAL:
        details = payload.get("stop_details") or {}
        raise AnalysisValidationError(
            f"claude declined the request (stop_reason={STOP_REASON_REFUSAL}, "
            f"category={details.get('category')})"
        )
    blocks = payload.get("content") or []
    return "".join(block.get("text", "") for block in blocks if block.get("type") == "text")


class BedrockClaudeClient:
    """`bedrock-runtime` InvokeModel로 Claude를 호출하는 실물 구현."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = bedrock_client()

    async def analyze(self, prompt: str) -> str:
        return await asyncio.to_thread(self._invoke, prompt)

    def _invoke(self, prompt: str) -> str:
        response = self._client.invoke_model(
            modelId=self._settings.claude_model_id,
            body=build_invoke_body(prompt),
        )
        return extract_text(json.loads(response["body"].read()))


class FakeClaudeClient:
    """정해진 응답을 순서대로 돌려주고 받은 프롬프트를 기록하는 테스트 대역.

    응답이 떨어지면 조용히 재사용하거나 빈 문자열을 주지 않고 `AssertionError`를
    올린다 — 테스트가 의도한 호출 횟수를 넘겼다는 사실 자체가 버그 신호다.
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []

    async def analyze(self, prompt: str) -> str:
        self.prompts.append(prompt)
        assert self._responses, f"FakeClaudeClient responses exhausted (call #{len(self.prompts)})"
        return self._responses.pop(0)
