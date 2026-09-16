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

import httpx

from app.config import (
    BEDROCK_CONNECT_TIMEOUT,
    BEDROCK_READ_TIMEOUT,
    Settings,
    bedrock_client,
)
from app.models.analysis import AnalysisValidationError
from app.models.usage import PURPOSE_PLAN, PURPOSE_SPIKE, TokenUsage, UsageSink

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

# 같은 사실의 openai 계열 이름 (`TASK-142` · 실측 `openai_shape.json`). 정상 종료는 `stop` 이다.
# ⛔ 두 값역을 한 상수로 합치지 않는다 — 계열마다 규격이 따로 바뀌므로 합치면 한쪽 변경이
# 다른 쪽 판정을 조용히 옮긴다.
OPENAI_FINISH_TRUNCATED = "length"


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
    """Bedrock InvokeModel 본문 (JSON 문자열) — **Anthropic 규격**."""
    return json.dumps(
        {
            "anthropic_version": ANTHROPIC_VERSION,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
    )


def build_openai_invoke_body(prompt: str) -> str:
    """같은 InvokeModel 의 **OpenAI 규격** 본문 (`TASK-142` · 결정 121).

    ⛔ **`anthropic_version` 을 싣지 않는다** — openai 계열이 그 키를 `unknown_parameter` 로
    **거부한다**(실측: `runs/2026-09-16-model-comparison` §3 의 표에서 luna·terra 둘 다 거부).
    출력 상한의 키 이름도 `max_completion_tokens` 로 다르다.

    ⚠️ **Converse 로 옮기지 않은 것이 판단이다.** 네 모델이 모두 받는 모양은 Converse 하나지만
    같은 회차가 Opus 5 를 두 경로로 재서 **Converse 가 5.2초 느린 것**을 관측했다(18.4초 → 23.6초).
    지금 바꾸는 것은 job 하나이므로 계열별 분기가 더 좁은 변경이다.
    """
    return json.dumps(
        {
            "messages": [{"role": "user", "content": prompt}],
            "max_completion_tokens": MAX_TOKENS,
        }
    )


def is_openai_model(model_id: str) -> bool:
    """이 모델 ID 가 openai 계열인가 — **규격 분기의 유일한 판정자**.

    ⛔ 값역을 열거하지 않는다(`us.openai.gpt-5.6-terra`·`…-luna`·`…-sol`·다음 판). 계열이
    이름에 박혀 있고 그것이 Bedrock 의 모델 ID 규약이다 — 열거하면 모델이 늘 때마다 조용히 틀린다.
    """
    return "openai." in model_id


def body_for(model_id: str, prompt: str) -> str:
    """이 모델이 받는 본문. 계열 판정은 `is_openai_model` 하나가 한다."""
    if is_openai_model(model_id):
        return build_openai_invoke_body(prompt)
    return build_invoke_body(prompt)


def _http_post(url: str, *, headers: dict[str, str], content: bytes, timeout: Any) -> Any:
    """이음새 하나 — 테스트가 이 이름을 바꿔 끼운다(네트워크를 타지 않기 위해)."""
    return httpx.post(url, headers=headers, content=content, timeout=timeout)


def invoke_openai_model(model_id: str, body: str, *, region: str, token: str | None) -> Any:
    """openai 계열을 **bearer 키**로 부른다 (`TASK-142` · 사용자 지시 2026-09-16).

    ⛔ **왜 boto3 가 아닌가 — 실측 둘.** ① 앱 IAM 사용자에게 그 추론 프로필 권한이 없다
    (`AccessDenied`. 같은 클라이언트로 Opus 5 는 통과한다). ② 그 키를 boto3 로 쓸 수 없었다:
    클라이언트 생성 시점에 환경변수를 올리고 지우면 **호출 시점**에 `NoCredentialsError` 이고
    (토큰은 호출 시점에 읽힌다), 토큰 provider 를 클라이언트에 직접 꽂아도 환경의 SigV4 가 이겨
    `AccessDenied` 가 났다. ⇒ 이 경로만 HTTPS 직접 호출이다.

    ⛔ **환경변수를 만지지 않는다.** bearer 를 프로세스 환경에 올리면 boto3 의 Bedrock 호출 전부가
    그것을 쓰고 **Nova 양방향이 403 으로 죽는다** — `config.prepare_bedrock_credentials` 가 SigV4 가
    준비되면 그 값을 지우는 이유가 그것이다. 토큰은 인자로만 흐른다.

    ⚠️ 타임아웃은 boto 경로와 같은 수를 쓴다(`config` 의 두 상수) — 두 경로가 다른 시간에 죽으면
    실패의 모양이 갈려 원인을 가리기 어렵다. 재시도는 job 큐가 갖는다(`services/jobs.MAX_ATTEMPTS`).
    """
    if not token:
        raise RuntimeError(
            "openai 계열 모델을 부를 bearer 키가 없다 — Bedrock API 키를 셸에 export 하거나 "
            "app/backend/.env 에 넣어라(키의 «이름»은 app/config.py 가 소유한다 — F5). "
            "SigV4 로는 이 추론 프로필을 부를 수 없다."
        )
    response = _http_post(
        f"https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        content=body.encode("utf-8"),
        timeout=httpx.Timeout(BEDROCK_READ_TIMEOUT, connect=BEDROCK_CONNECT_TIMEOUT),
    )
    response.raise_for_status()
    return response.json()


def model_for_purpose(settings: Settings, purpose: str) -> str:
    """이 목적이 쓸 모델 (`TASK-142` · 결정 121).

    ⛔ **학습 추천(plan)만 다른 모델을 쓴다.** 사용자 결정 121 의 범위가 「학습 추천」이고
    `claude_model_id` 하나가 job 다섯을 덮으므로, 목적으로 가르지 않으면 문법 분석과 총평까지
    함께 옮겨 간다. ⚠️ 목적이 늘 때 이 함수가 유일하게 고칠 자리다 — 호출부는 목적만 넘긴다.
    """
    return settings.plan_model_id if purpose == PURPOSE_PLAN else settings.claude_model_id


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
    if "choices" in payload:
        return _extract_openai_text(payload)
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


def _extract_openai_text(payload: dict[str, Any]) -> str:
    """openai 계열 응답에서 텍스트 (`TASK-142`).

    실측 모양(`runs/2026-09-16-task142-terra-switch/openai_shape.json`): 텍스트는
    `choices[0].message.content` · 종료 사유는 `choices[0].finish_reason`(정상은 `stop`) ·
    거부는 같은 message 의 `refusal` 이다.

    ⛔ **절단과 거부를 Anthropic 갈래와 «같은 예외»로 올린다** — 호출자가 두 계열을 가르지 않아야
    한다. `length` 를 그냥 넘기면 잘린 JSON 이 파서로 내려가 사유가 「JSON 아님」으로 뭉개진다.
    """
    choices = payload.get("choices") or []
    if not choices:
        return ""
    choice = choices[0]
    message = choice.get("message") or {}
    if choice.get("finish_reason") == OPENAI_FINISH_TRUNCATED:
        raise AnalysisValidationError(
            f"openai response hit the output budget (finish_reason={OPENAI_FINISH_TRUNCATED}, "
            f"max_completion_tokens={MAX_TOKENS}) — the JSON is incomplete"
        )
    refusal = message.get("refusal")
    if refusal:
        raise AnalysisValidationError(f"openai model declined the request (refusal={refusal!r})")
    content = message.get("content")
    return content if isinstance(content, str) else ""


def extract_usage(payload: dict[str, Any]) -> TokenUsage | None:
    """응답의 `usage`에서 토큰 둘. 없으면 `None` (`TASK-60` · 결정 66).

    ⛔ **없을 때 0 을 만들지 않는다.** `0` 은 「토큰을 쓰지 않았다」는 **주장**이고, 그런 호출은
    없다 — 그것을 적으면 비용 합계가 조용히 낮아진다. 없으면 그 사실을 남기지 않고(행을 만들지
    않고) 지나가는 쪽이 정직하다.
    """
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None
    # ⚠️ **계열마다 키 이름이 다르다** (`TASK-142` · 실측): Anthropic 은 `input_tokens`·
    # `output_tokens`, openai 는 `prompt_tokens`·`completion_tokens` 다. ⛔ 이 갈림을 빼면
    # `llm_calls` 가 조용히 비고, 그러면 비용의 큰 쪽을 세지 못한다(`TASK-124` 가 같은 부류다).
    input_tokens = usage.get("input_tokens", usage.get("prompt_tokens"))
    output_tokens = usage.get("output_tokens", usage.get("completion_tokens"))
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
        # ⛔ **모델을 목적으로 고른다** (`TASK-142` · 결정 121) — 그 판정은 `model_for_purpose`
        # 하나가 갖고, 아래 usage 기록도 **같은 값**을 적어야 한다(다르게 적으면 비용이 엉뚱한
        # 모델에 귀속된다).
        model_id = model_for_purpose(self._settings, purpose)
        payload = await asyncio.to_thread(self._invoke, prompt, model_id)
        # ⛔ **`extract_text`보다 «먼저» 적는다.** 예산 절단·거부는 `extract_text`가 예외로
        # 올리는데 그 호출도 **돈이 나간 호출**이다. 뒤에 적으면 실패한 호출의 비용이 표에서
        # 빠지고, 그러면 「비용이 왜 늘었는가」를 설명할 수 없다(참고 프로젝트가 예열 호출까지
        # 적은 이유와 같다).
        usage = extract_usage(payload)
        if self._usage_sink is not None and usage is not None:
            await self._usage_sink(
                usage,
                model_id=model_id,
                purpose=purpose,
                job_id=job_id,
            )
        return extract_text(payload)

    def _invoke(self, prompt: str, model_id: str) -> dict[str, Any]:
        body = body_for(model_id, prompt)
        if is_openai_model(model_id):
            # ⛔ **자격증명 경로가 계열마다 다르다** (`TASK-142`) — openai 계열은 bearer 키로만
            # 부를 수 있다(그 함수의 docstring 이 실측 근거를 갖는다). 토큰은 `Settings` 에서
            # 오고 **프로세스 환경을 거치지 않는다** — 환경에 올리면 Nova 가 403 으로 죽는다.
            return invoke_openai_model(
                model_id,
                body,
                region=self._settings.aws_region,
                token=self._settings.aws_bearer_token_bedrock,
            )
        response = self._client.invoke_model(modelId=model_id, body=body)
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
