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
from uuid import UUID

from app.config import Settings, bedrock_client
from app.models.analysis import AnalysisValidationError
from app.models.usage import PURPOSE_SPIKE, TokenUsage, UsageSink

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
    """분석 프롬프트를 넣고 **원문 텍스트**를 받는다 (JSON 파싱은 호출자의 몫).

    `purpose`·`job_id`는 **사용량 기록의 귀속**에만 쓴다 (`TASK-60` · 결정 66). 기본값이 있어
    기존 호출자를 깨뜨리지 않지만, ⛔ **job 경로의 두 호출자는 반드시 넘긴다** — 넘기지 않으면
    비용이 「임시 호출」로 적혀 갈래별 집계가 조용히 틀린다.
    """

    async def analyze(
        self, prompt: str, *, purpose: str = PURPOSE_SPIKE, job_id: UUID | None = None
    ) -> str: ...


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


def extract_usage(payload: dict[str, Any]) -> TokenUsage | None:
    """응답의 `usage`에서 토큰 둘. 없으면 `None` (`TASK-60` · 결정 66).

    ⛔ **없을 때 0 을 만들지 않는다.** `0` 은 「토큰을 쓰지 않았다」는 **주장**이고, 그런 호출은
    없다 — 그것을 적으면 비용 합계가 조용히 낮아진다. 없으면 그 사실을 남기지 않고(행을 만들지
    않고) 지나가는 쪽이 정직하다.
    """
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
        return None
    return TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens)


class BedrockClaudeClient:
    """`bedrock-runtime` InvokeModel로 Claude를 호출하는 실물 구현.

    `usage_sink`는 **주입한다** (`TASK-60` · 결정 66) — 이 클래스가 DB 를 알면 자격증명·네트워크
    없이 도는 단위 테스트가 DB 를 요구한다. 주지 않으면 기록하지 않는다: 그것이 「기록을 붙일지」를
    **배선하는 쪽**(`api/main.py`·하네스)이 정하게 하는 형태다.
    """

    def __init__(self, settings: Settings, *, usage_sink: UsageSink | None = None) -> None:
        self._settings = settings
        self._client = bedrock_client()
        self._usage_sink = usage_sink

    @property
    def records_usage(self) -> bool:
        """사용량 sink 가 붙어 있는가.

        공개 속성으로 두는 이유: **배선 누락을 잡는 게이트 테스트가 이것을 잰다.** private 속성을
        들여다보는 단정은 리팩터에 깨지고, 그 깨짐이 「배선이 사라졌다」와 구분되지 않는다.
        """
        return self._usage_sink is not None

    async def analyze(
        self, prompt: str, *, purpose: str = PURPOSE_SPIKE, job_id: UUID | None = None
    ) -> str:
        payload = await asyncio.to_thread(self._invoke, prompt)
        # ⛔ **`extract_text`보다 «먼저» 적는다.** 예산 절단·거부는 `extract_text`가 예외로
        # 올리는데 그 호출도 **돈이 나간 호출**이다. 뒤에 적으면 실패한 호출의 비용이 표에서
        # 빠지고, 그러면 「비용이 왜 늘었는가」를 설명할 수 없다(참고 프로젝트가 예열 호출까지
        # 적은 이유와 같다).
        usage = extract_usage(payload)
        if self._usage_sink is not None and usage is not None:
            await self._usage_sink(
                usage,
                model_id=self._settings.claude_model_id,
                purpose=purpose,
                job_id=job_id,
            )
        return extract_text(payload)

    def _invoke(self, prompt: str) -> dict[str, Any]:
        response = self._client.invoke_model(
            modelId=self._settings.claude_model_id,
            body=build_invoke_body(prompt),
        )
        return json.loads(response["body"].read())


class FakeClaudeClient:
    """정해진 응답을 순서대로 돌려주고 받은 프롬프트를 기록하는 테스트 대역.

    응답이 떨어지면 조용히 재사용하거나 빈 문자열을 주지 않고 `AssertionError`를
    올린다 — 테스트가 의도한 호출 횟수를 넘겼다는 사실 자체가 버그 신호다.
    """

    def __init__(self, responses: list[str], *, by_purpose: dict[str, str] | None = None) -> None:
        self._responses = list(responses)
        self.prompts: list[str] = []
        # `TASK-60` — 받은 귀속을 그대로 기록한다. 테스트가 「job 호출자가 갈래를 넘겼는가」를
        # 이 자리에서 잴 수 있어야 한다: 안 넘기면 비용이 「임시 호출」로 적힌다.
        self.attributions: list[tuple[str, UUID | None]] = []
        # `TASK-62` — **갈래별 응답**. 그 갈래로 온 호출은 순서 목록을 «꺼내지 않고» 이것을 받는다.
        #
        # ⛔ **왜 필요한가**: 워커 루프를 돌리는 통합 테스트는 자기가 세운 job 하나만 재는데,
        # 세션 종료가 job 을 **여럿** 걸므로 큐에 그 테스트가 세우지 않은 호출이 섞인다. 순서
        # 목록만 있으면 그 호출이 남의 응답을 꺼내가고 목록이 마르면 `AssertionError` 가 난다 —
        # 2026-09-13 에 총평 job 을 더하면서 통합 테스트 다섯이 그렇게 깨졌다(원인은 라우팅이 아니라
        # **대역의 모양**이었다).
        # ⛔ **자동으로 추측하지 않는다** — 호출자가 준 갈래만 답한다. 대역이 스스로 그럴듯한 응답을
        # 만들기 시작하면 「응답이 준비되지 않은 호출」을 테스트가 못 잡는다.
        self._by_purpose = dict(by_purpose or {})

    async def analyze(
        self, prompt: str, *, purpose: str = PURPOSE_SPIKE, job_id: UUID | None = None
    ) -> str:
        self.prompts.append(prompt)
        self.attributions.append((purpose, job_id))
        if purpose in self._by_purpose:
            return self._by_purpose[purpose]
        assert self._responses, f"FakeClaudeClient responses exhausted (call #{len(self.prompts)})"
        return self._responses.pop(0)

    def prompts_for(self, purpose: str) -> list[str]:
        """그 갈래로 온 프롬프트만 돌려준다.

        ⛔ **`len(self.prompts)` 로 「몇 번 불렸나」를 재지 않는다** — 큐에 다른 종류의 job 이
        섞이면 그 수가 재려던 것과 무관하게 늘어난다. 재려는 것은 대개 **「내 갈래가 한 번
        불렸나」**이므로 그 축을 이 함수가 갖는다.
        """
        return [
            prompt
            for prompt, (called_for, _) in zip(self.prompts, self.attributions, strict=True)
            if called_for == purpose
        ]
