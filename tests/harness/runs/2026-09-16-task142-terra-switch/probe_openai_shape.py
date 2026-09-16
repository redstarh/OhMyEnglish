#!/usr/bin/env python3
"""`TASK-142` — openai 계열 InvokeModel 응답의 **실제 모양**을 잰다. 추정하지 않는다.

무엇이 필요한가: 텍스트가 어느 키에 있는가 · 종료 사유의 키와 값 · usage 의 키 이름.
⛔ 자격증명 값을 출력하지 않는다. bearer 경로로만 붙는다(앱의 SigV4 IAM 사용자는 권한이 없다).

    app/backend/.venv/bin/python <이 파일>
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, "/Users/redstar/MyProject/OhMyEnglish/app/backend")

import boto3  # noqa: E402

from app.config import bedrock_boto_config, get_settings  # noqa: E402

MODEL = "us.openai.gpt-5.6-terra"
PROMPT = 'Reply with exactly this JSON and nothing else: {"ok": true}'


def _bearer_from_env_file() -> str:
    """`.env` 의 bearer 토큰. 셸에 없을 때만 읽고 **값을 찍지 않는다.**"""
    env_path = Path("/Users/redstar/MyProject/OhMyEnglish/app/backend/.env")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("AWS_BEARER_TOKEN_BEDROCK="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("AWS_BEARER_TOKEN_BEDROCK 을 찾지 못했다")


def main() -> None:
    settings = get_settings()
    for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        os.environ.pop(key, None)
    os.environ.setdefault("AWS_BEARER_TOKEN_BEDROCK", _bearer_from_env_file())
    client = boto3.client(
        "bedrock-runtime", region_name=settings.aws_region, config=bedrock_boto_config()
    )
    body = json.dumps(
        {"messages": [{"role": "user", "content": PROMPT}], "max_completion_tokens": 64}
    )
    payload = json.loads(client.invoke_model(modelId=MODEL, body=body)["body"].read())

    # 모양만 남긴다 — 본문 텍스트는 짧으므로 그대로 실어 파서 분기의 근거로 쓴다.
    shape = {
        "top_keys": sorted(payload.keys()),
        "choice_keys": sorted(payload["choices"][0].keys()) if payload.get("choices") else None,
        "message_keys": sorted(payload["choices"][0]["message"].keys())
        if payload.get("choices")
        else None,
        "finish_reason": payload["choices"][0].get("finish_reason")
        if payload.get("choices")
        else None,
        "text": payload["choices"][0]["message"].get("content") if payload.get("choices") else None,
        "usage": payload.get("usage"),
    }
    out = Path(__file__).with_name("openai_shape.json")
    out.write_text(json.dumps(shape, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(shape, ensure_ascii=False, indent=2))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
