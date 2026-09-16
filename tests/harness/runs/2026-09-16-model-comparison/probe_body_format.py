#!/usr/bin/env python3
"""TASK-141 프로브 — 후보 모델이 «앱이 지금 보내는 본문»을 받는지 먼저 가른다.

⛔ 재는 것은 지금 제품이 보내는 것이다. `app.workers.claude_client.build_invoke_body`
를 그대로 쓴다 — 여기서 본문을 고쳐 쓰면 「바꾸면 무엇이 깨지는가」가 가려진다.

세 갈래를 각각 1회만 부른다:
  A. InvokeModel + Anthropic 본문 (앱의 현재 경로)
  B. Converse (모델 무관 정규화 경로)
  C. InvokeModel + OpenAI 본문 (`max_completion_tokens`)

⚠️ **자격증명이 둘이라 결과가 갈린다.** 앱의 SigV4 IAM 사용자는 `us.anthropic.claude-opus-5`
에만 권한이 있어 후보 셋이 전부 `AccessDeniedException` 이다(1차 실행에서 실측). 그래서 이
프로브는 **측정용 bearer 경로**로 붙는다 — `prepare_bedrock_credentials` 를 부르지 않고
SigV4 키를 환경에서 뺀 뒤 `AWS_BEARER_TOKEN_BEDROCK` 만 남긴다. 권한 차이 자체가 결론의
일부이므로 그 사실을 보고서가 갖는다.

출력은 stdout 과 `probe_body_format.json` 이다. 자격증명 값은 적지 않는다.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/Users/redstar/MyProject/OhMyEnglish/app/backend")

import boto3  # noqa: E402

from app.config import bedrock_boto_config, get_settings  # noqa: E402
from app.workers.claude_client import build_invoke_body  # noqa: E402


def measuring_client(region: str):
    """bearer 토큰만으로 붙는 `bedrock-runtime` 클라이언트.

    ⛔ `app.config.bedrock_client()` 를 쓰지 않는다 — 그것은 SigV4 키를 환경에 심고 bearer 를
    **지운다**(설계서 §4.1 의 단일 경로). 재시도·타임아웃 정책은 앱과 같은 것을 쓴다.
    """
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        os.environ.pop(key, None)
    if not os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        raise SystemExit("AWS_BEARER_TOKEN_BEDROCK 이 셸 환경에 없다 — 측정 경로가 붙지 않는다")
    return boto3.client("bedrock-runtime", region_name=region, config=bedrock_boto_config())


MODELS = [
    "us.anthropic.claude-opus-5",
    "us.anthropic.claude-sonnet-5",
    "us.openai.gpt-5.6-luna",
    "us.openai.gpt-5.6-terra",
]
PROMPT = 'Return one JSON object and nothing else: {"ok": true}'
_OUT = Path(__file__).with_suffix(".json")


def short(exc: Exception) -> str:
    return f"{type(exc).__name__}: {exc}"[:300]


def main() -> None:
    settings = get_settings()
    client = measuring_client(settings.aws_region)
    print(f"region={settings.aws_region} app_model_id={settings.claude_model_id}")
    rows: list[dict[str, object]] = []

    for model in MODELS:
        row: dict[str, object] = {"model": model}

        # A. 앱의 현재 본문 그대로
        try:
            resp = client.invoke_model(modelId=model, body=build_invoke_body(PROMPT))
            payload = json.loads(resp["body"].read())
            row["A_anthropic_body"] = "ok"
            row["A_keys"] = sorted(payload.keys())
        except Exception as exc:  # noqa: BLE001 — 사유 원문이 결론이다
            row["A_anthropic_body"] = short(exc)

        # B. Converse
        try:
            resp = client.converse(
                modelId=model,
                messages=[{"role": "user", "content": [{"text": PROMPT}]}],
                inferenceConfig={"maxTokens": 512},
            )
            row["B_converse"] = "ok"
            row["B_usage"] = resp.get("usage")
            row["B_stop"] = resp.get("stopReason")
        except Exception as exc:  # noqa: BLE001
            row["B_converse"] = short(exc)

        # C. OpenAI 본문 (openai 계열에만 의미가 있다)
        try:
            body = json.dumps(
                {
                    "messages": [{"role": "user", "content": PROMPT}],
                    "max_completion_tokens": 512,
                }
            )
            resp = client.invoke_model(modelId=model, body=body)
            payload = json.loads(resp["body"].read())
            row["C_openai_body"] = "ok"
            row["C_keys"] = sorted(payload.keys())
        except Exception as exc:  # noqa: BLE001
            row["C_openai_body"] = short(exc)

        print(json.dumps(row, ensure_ascii=False, default=str))
        rows.append(row)

    _OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"-> {_OUT}")


if __name__ == "__main__":
    main()
