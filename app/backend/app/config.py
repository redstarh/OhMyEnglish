"""Single point of credential acquisition for the OhMyEnglish backend.

`AWS_BEARER_TOKEN_BEDROCK` must never be read, referenced, or re-exported
from any other module (F5). `bedrock_client()` is the one factory that turns
`Settings` into a boto3 Bedrock client — boto3 absorbs the bearer token (or,
after the SigV4 migration described in the design doc, SigV4 credentials)
from the environment on its own. If credential strategy ever changes, this
function is the only place that needs to change.
"""

from __future__ import annotations

from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    aws_region: str
    aws_bearer_token_bedrock: str | None = None
    claude_model_id: str = "us.anthropic.claude-opus-5"
    # 분석 워커 기동 플래그. 기본은 켜짐 — API만 띄우고 큐를 일부러 쌓아두는
    # 시나리오(E2E-S 3단계)에서만 끈다.
    worker_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached Settings singleton."""
    # pydantic-settings synthesizes __init__ from env/.env at runtime; ty
    # (alpha, v0.0.31) does not yet model that and treats the required
    # fields as missing constructor arguments here.
    return Settings()  # ty: ignore[missing-argument]


def bedrock_client():
    """Create a boto3 `bedrock-runtime` client for the configured region.

    Credential acquisition (bearer token today, SigV4 after the design
    doc's migration) is fully delegated to boto3's environment-based
    resolution — this function is the single seam to change if that
    strategy changes.
    """
    settings = get_settings()
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)
