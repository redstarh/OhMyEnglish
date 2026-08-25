#!/usr/bin/env python3
"""Nova Sonic 양방향 스트림 SigV4 스파이크 — Phase 2 진입 관문.

정본: `docs/ops/iam-setup-nova-sigv4.md` §5 ③, 설계서 §10-1.

**판정 기준 (2026-08-26 실측으로 재정의).** 처음에는 `await_output()`이 값을
돌려주는 것을 성공 조건으로 잡았는데 그것이 틀렸다 — Nova Sonic은 클라이언트가
전체 초기화 시퀀스(sessionStart → promptStart → contentStart …)를 보내기 전까지
아무 이벤트도 내보내지 않는다. 그 프로토콜 구현은 Phase 2의 몫이다.

이 스파이크가 판정하는 것은 **자격증명이 이 연산에 통하는가** 하나다. 인증·인가는
요청 시점에 평가되므로 실패하면 즉시 HTTP 4xx가 온다(실측: 권한 부족 시 1초 안에
403). 따라서:

- 4xx 응답 또는 예외 → **FAIL** (본문에서 원인을 읽어 출력한다)
- 정해진 시간 동안 조용히 스트림이 유지됨 → **PASS** (요청이 수락되었다)

"조용함 = 성공"은 위험한 기준이라 **음성 대조군**을 함께 돌린다 — 존재하지 않는
모델로 같은 호출을 해서 하네스가 실패를 실제로 잡아내는지 먼저 확인한다. 대조군이
조용하면 하네스가 고장 난 것이므로 판정을 내리지 않는다.

**진단 장치 2개** (둘 다 없으면 원인을 알 수 없다):

1. `DiagnosticTransport` — SDK가 4xx 응답 **본문을 버린다**(실측: 403 + 271바이트
   JSON에 정확한 이유가 있는데 `AccessDeniedException('')`만 남는다).
2. asyncio 예외 핸들러 — 자격증명 실패가 내부 태스크에서 터져
   `Task exception was never retrieved`로 삼켜진다 (설계서 §4.2).

실행:

    cd app/backend && .venv/bin/python ../../scripts/spike_nova_bidirectional.py

DB를 쓰지 않는다 — 자격증명과 네트워크만 만진다.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "app" / "backend"

# `app` 패키지는 app/backend 아래에 있다 — cwd에 의존하지 않게 파일 경로에서 계산한다.
sys.path.insert(0, str(BACKEND_DIR))

from app.config import Settings, prepare_bedrock_credentials  # noqa: E402

NOVA_MODEL_ID = "amazon.nova-2-sonic-v1:0"
# 음성 대조군 — 이 계정에 존재하지 않는 모델 ID다(실측: ValidationException).
CONTROL_MODEL_ID = "amazon.nova-sonic-v1:0"

# 스파이크 발명값 — 근거 문서 없음. 인가 실패는 1초 안에 오므로 이보다 훨씬 짧아도
# 되지만, 네트워크 지연을 실패로 오판하지 않을 만큼의 여유를 둔다.
OPEN_TIMEOUT_SECONDS = 20.0
LIVENESS_SECONDS = 10.0
CONTROL_TIMEOUT_SECONDS = 20.0

# 4xx 응답 본문 포착 스위치. 기본 꺼짐 — 켜면 본문을 읽어 정확한 이유를 얻지만,
# 본문을 되돌릴 수 없어 SDK의 예외 타입이 `SmithyError: premature EOF`로 바뀐다.
# 불투명한 `AccessDeniedException('')`를 만났을 때만 켠다:
#     OMY_SPIKE_CAPTURE_BODY=1 .venv/bin/python ../../scripts/spike_nova_bidirectional.py
CAPTURE_ERROR_BODY = os.environ.get("OMY_SPIKE_CAPTURE_BODY") == "1"

SESSION_START_EVENT = {
    "event": {
        "sessionStart": {
            "inferenceConfiguration": {"maxTokens": 256, "topP": 0.9, "temperature": 0.7}
        }
    }
}


class DiagnosticTransport:
    """HTTP 4xx/5xx 응답 **본문**을 붙잡는 트랜스포트 래퍼.

    `SUPPORTS_DUPLEX_STREAMING`이 필요하다 — 없으면 SDK가 양방향 연산에서 이
    트랜스포트를 거부한다.
    """

    SUPPORTS_DUPLEX_STREAMING = True

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self.error_bodies: list[str] = []
        self.saw_error_status = False

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    async def send(self, request: Any, **kwargs: Any) -> Any:
        response = await self._inner.send(request, **kwargs)
        status = getattr(response, "status", None)
        if status is None or status < 400:
            return response

        self.saw_error_status = True
        if not CAPTURE_ERROR_BODY:
            return response

        # 본문은 한 번만 읽을 수 있고 `response.body`는 읽기 전용 property라
        # 되돌려 놓을 수 없다(실측). 따라서 읽는 순간 SDK의 역직렬화가
        # `premature EOF`로 실패해 **진단이 진단을 가린다** — 대조군의
        # ValidationException이 SmithyError로 바뀌어 보였다. 그래서 이 포착은
        # 기본으로 끄고, 불투명한 AccessDenied를 만났을 때만 켠다.
        raw = b"".join([chunk async for chunk in response.body])
        self.error_bodies.append(f"HTTP {status}: {raw.decode('utf-8', 'replace')}")
        return response


def _install_swallowed_exception_reporter(sink: list[BaseException]) -> None:
    """SDK 내부 태스크에서 삼켜지는 예외를 붙잡는다 (설계서 §4.2)."""
    loop = asyncio.get_running_loop()
    previous = loop.get_exception_handler()

    def handler(current_loop: asyncio.AbstractEventLoop, context: dict[str, Any]) -> None:
        exc = context.get("exception")
        if exc is not None:
            sink.append(exc)
        if previous is not None:
            previous(current_loop, context)
        else:
            current_loop.default_exception_handler(context)

    loop.set_exception_handler(handler)


def _report(transport: DiagnosticTransport, swallowed: list[BaseException]) -> None:
    if transport.error_bodies:
        print("\n  서비스가 돌려준 실제 이유 (SDK가 버리는 응답 본문):")
        for body in transport.error_bodies:
            print(f"    {body}")
    elif transport.saw_error_status:
        print(
            "\n  4xx 응답을 받았지만 본문 포착이 꺼져 있다. 정확한 이유를 보려면:\n"
            "    OMY_SPIKE_CAPTURE_BODY=1 .venv/bin/python "
            "../../scripts/spike_nova_bidirectional.py"
        )
    if swallowed:
        print("\n  SDK 내부 태스크에서 삼켜진 예외 (§4.2):")
        for exc in swallowed:
            print(f"    {type(exc).__name__}: {exc}")


async def _quiet_close(stream: Any) -> None:
    """정리 실패가 판정을 덮지 않게 한다.

    `close()`는 내부적으로 `await_output()`을 다시 기다리므로, 이미 취소된
    상태에서는 `CancelledError`(BaseException 계열)가 올라온다 — 잡아야 한다.
    """
    try:
        await asyncio.wait_for(stream.close(), timeout=5.0)
    except (Exception, asyncio.CancelledError):
        pass


async def _open_stream(client: Any, model_id: str, timeout: float) -> Any:
    from aws_sdk_bedrock_runtime.models import (
        InvokeModelWithBidirectionalStreamOperationInput,
    )

    return await asyncio.wait_for(
        client.invoke_model_with_bidirectional_stream(
            InvokeModelWithBidirectionalStreamOperationInput(model_id=model_id)
        ),
        timeout=timeout,
    )


async def _negative_control(client: Any) -> bool:
    """하네스가 실패를 실제로 잡아내는지 확인한다. 잡으면 True."""
    try:
        stream = await _open_stream(client, CONTROL_MODEL_ID, CONTROL_TIMEOUT_SECONDS)
    except Exception as exc:
        print(f"  대조군이 예상대로 거부됨: {type(exc).__name__}: {str(exc)[:80]}")
        return True
    try:
        await asyncio.wait_for(stream.await_output(), timeout=CONTROL_TIMEOUT_SECONDS)
    except TimeoutError:
        return False
    except Exception as exc:
        print(f"  대조군이 예상대로 거부됨: {type(exc).__name__}: {str(exc)[:80]}")
        return True
    finally:
        await _quiet_close(stream)
    return False


def _has_env_sigv4() -> bool:
    return bool(os.environ.get("AWS_ACCESS_KEY_ID")) and bool(
        os.environ.get("AWS_SECRET_ACCESS_KEY")
    )


async def run_spike() -> int:
    swallowed: list[BaseException] = []
    _install_swallowed_exception_reporter(swallowed)
    settings = Settings()  # ty: ignore[missing-argument]

    # 자격증명 해석은 앱과 같은 이음새를 쓴다(F5) — 스파이크는 통과했는데 앱은
    # 실패하는(또는 반대인) 상황을 만들지 않으려면 경로가 하나여야 한다.
    print("[1/5] 자격증명 준비")
    try:
        prepare_bedrock_credentials(settings)
    except RuntimeError as exc:
        print(f"  FAIL: {exc}", file=sys.stderr)
        return 1
    if not _has_env_sigv4():
        print(
            "  FAIL: SigV4 자격증명이 없다 — bearer 폴백 상태다. Nova 양방향은 bearer를\n"
            "        HTTP 403 `This operation does not support API Keys`로 거부한다.\n"
            "        발급 절차: docs/ops/iam-setup-nova-sigv4.md",
            file=sys.stderr,
        )
        return 1
    print("  SigV4 확인 (bearer는 프로세스 환경에서 제거됨)")

    from aws_sdk_bedrock_runtime.client import AsyncBedrockRuntimeClient
    from aws_sdk_bedrock_runtime.config import AsyncBedrockRuntimeConfig
    from aws_sdk_bedrock_runtime.models import (
        BidirectionalInputPayloadPart,
        InvokeModelWithBidirectionalStreamInputChunk,
    )

    print(f"[2/5] 클라이언트 생성 (region={settings.aws_region})")
    # 직접 생성이 금지돼 있다 — `resolve()`가 유일한 경로다.
    try:
        sdk_config = await AsyncBedrockRuntimeConfig.resolve(region=settings.aws_region)
    except Exception as exc:
        print(f"  FAIL: SDK config 해석 실패 — {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    transport = DiagnosticTransport(sdk_config.transport)
    sdk_config.transport = transport
    client = AsyncBedrockRuntimeClient(config=sdk_config)

    print(f"[3/5] 음성 대조군 ({CONTROL_MODEL_ID} — 존재하지 않아야 함)")
    if not await _negative_control(client):
        print(
            "  FAIL: 대조군이 거부되지 않았다 — 하네스가 실패를 못 잡는다.\n"
            "        '조용함 = 성공' 판정을 신뢰할 수 없으므로 판정하지 않는다.",
            file=sys.stderr,
        )
        _report(transport, swallowed)
        return 1
    transport.error_bodies.clear()  # 대조군 소음을 본 판정에서 분리한다
    transport.saw_error_status = False

    print(f"[4/5] 대상 스트림 열기 ({NOVA_MODEL_ID}, 상한 {OPEN_TIMEOUT_SECONDS:.0f}s)")
    try:
        stream = await _open_stream(client, NOVA_MODEL_ID, OPEN_TIMEOUT_SECONDS)
    except Exception as exc:
        print(f"  FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
        _report(transport, swallowed)
        return 1

    print(f"[5/5] sessionStart 전송 + {LIVENESS_SECONDS:.0f}s 유지 확인")
    exit_code = 1
    try:
        await stream.input_stream.send(
            InvokeModelWithBidirectionalStreamInputChunk(
                value=BidirectionalInputPayloadPart(bytes_=json.dumps(SESSION_START_EVENT).encode())
            )
        )
        try:
            await asyncio.wait_for(stream.await_output(), timeout=LIVENESS_SECONDS)
            # 응답이 왔다면 그것도 성공이다 — 인가를 통과했다는 더 강한 증거다.
            print("\nPASS: 서비스가 응답까지 돌려줬다 — SigV4가 이 연산에 통한다.")
            exit_code = 0
        except TimeoutError:
            if transport.saw_error_status:
                print("  FAIL: 4xx 응답을 받았다.", file=sys.stderr)
            else:
                print(
                    f"\nPASS: 요청이 수락되고 스트림이 {LIVENESS_SECONDS:.0f}초간 유지됐다 "
                    "(4xx 없음) — SigV4가 이 연산에 통한다."
                )
                print(
                    "  Nova는 전체 초기화 시퀀스를 받기 전엔 이벤트를 내보내지 않는다 — "
                    "그 구현은 Phase 2다."
                )
                exit_code = 0
    except Exception as exc:
        print(f"  FAIL: {type(exc).__name__}: {exc}", file=sys.stderr)
    finally:
        await _quiet_close(stream)

    if exit_code == 0:
        print("  설계서 §10-1 관문 통과 — Phase 2(Nova 실연동) 착수 조건 충족.")
    _report(transport, swallowed)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run_spike()))
