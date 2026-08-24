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

자격증명은 `config.bedrock_client()` 팩토리에만 있다(F5) — 이 모듈은 boto3나
토큰을 직접 다루지 않는다. 모델 ID도 `Settings.claude_model_id`가 SoT다.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol

from app.config import Settings, bedrock_client

# Bedrock InvokeModel의 Anthropic Messages 본문 규격 (모델 버전이 아니라 본문 스키마 버전).
ANTHROPIC_VERSION = "bedrock-2023-05-31"

# 한 발화 분석의 출력 상한. 한 문장에서 나올 findings JSON은 이보다 훨씬 짧다.
MAX_TOKENS = 4096


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

    text 블록이 없으면(거부·`max_tokens` 절단 등) 빈 문자열을 돌려준다 —
    여기서 예외를 만들지 않고 `parse_analysis`의 단일 거부 경로로 흘려보내야
    실패 처리(`fail_or_retry`)가 한 곳으로 모인다.
    """
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
