"""Task 1 — config/scaffolding tests.

These tests never touch the database (per controller ruling): they only
exercise `Settings`, the Bedrock SDK import, and the credential-isolation
guarantee (AWS_BEARER_TOKEN_BEDROCK must not leak outside config.py).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app import config as config_module
from app.config import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "app" / "backend"


def _clear_ambient_settings_env(monkeypatch):
    """Real env vars outrank `.env` file values in pydantic-settings — clear
    the ambient Claude Code session's own AWS_BEARER_TOKEN_BEDROCK (and
    friends) so these tests observe only what the `.env` fixture wrote."""
    for key in ("DATABASE_URL", "AWS_REGION", "AWS_BEARER_TOKEN_BEDROCK", "CLAUDE_MODEL_ID"):
        monkeypatch.delenv(key, raising=False)


def test_settings_reads_dotenv(tmp_path, monkeypatch):
    """Settings() with no args reads values from a `.env` in the cwd."""
    _clear_ambient_settings_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://ohmy:ohmy@localhost:5433/ohmyenglish\nAWS_REGION=us-west-2\n"
    )
    monkeypatch.chdir(tmp_path)

    # config.py의 `get_settings`와 같은 사유 — pydantic-settings는 env/.env에서
    # __init__을 런타임에 합성하지만 ty(alpha)는 그것을 모델링하지 못한다.
    settings = Settings()  # ty: ignore[missing-argument]

    assert settings.database_url == "postgresql://ohmy:ohmy@localhost:5433/ohmyenglish"
    assert settings.aws_region == "us-west-2"
    assert settings.claude_model_id == "us.anthropic.claude-opus-5"
    assert settings.aws_bearer_token_bedrock is None


def test_settings_reads_optional_bearer_token(tmp_path, monkeypatch):
    _clear_ambient_settings_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://ohmy:ohmy@localhost:5433/ohmyenglish\n"
        "AWS_REGION=us-west-2\n"
        "AWS_BEARER_TOKEN_BEDROCK=test-bearer-token\n"
    )
    monkeypatch.chdir(tmp_path)

    # config.py의 `get_settings`와 같은 사유 — pydantic-settings는 env/.env에서
    # __init__을 런타임에 합성하지만 ty(alpha)는 그것을 모델링하지 못한다.
    settings = Settings()  # ty: ignore[missing-argument]

    assert settings.aws_bearer_token_bedrock == "test-bearer-token"


def test_bedrock_sdk_is_importable():
    result = subprocess.run(
        [sys.executable, "-c", "import aws_sdk_bedrock_runtime"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def _settings_with_token(token: str | None) -> Settings:
    return Settings(
        database_url="postgresql://fake:fake@localhost/fake",
        aws_region="us-west-2",
        aws_bearer_token_bedrock=token,
    )


def test_bedrock_client_injects_dotenv_bearer_token_when_environ_lacks_it(monkeypatch):
    """I-1: pydantic-settings reads AWS_BEARER_TOKEN_BEDROCK from `.env` into
    `Settings` but never re-exports it to `os.environ`, so boto3 (which
    resolves credentials from the process environment) never sees a token
    that only lives in `.env` — bedrock_client() must inject it once."""
    monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)
    monkeypatch.setattr(config_module, "get_settings", lambda: _settings_with_token("dotenv-only-token"))
    monkeypatch.setattr(config_module.boto3, "client", lambda *args, **kwargs: object())

    config_module.bedrock_client()

    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "dotenv-only-token"


def test_bedrock_client_preserves_existing_environ_bearer_token(monkeypatch):
    """Shell export outranks `.env` — bedrock_client() must not overwrite an
    AWS_BEARER_TOKEN_BEDROCK that is already present in os.environ."""
    monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "shell-export-token")
    monkeypatch.setattr(
        config_module, "get_settings", lambda: _settings_with_token("dotenv-token-should-be-ignored")
    )
    monkeypatch.setattr(config_module.boto3, "client", lambda *args, **kwargs: object())

    config_module.bedrock_client()

    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "shell-export-token"


def test_bearer_token_string_isolated_to_config_module():
    """F5: `grep -r "AWS_BEARER" app/ | grep -v config.py` must be empty."""
    result = subprocess.run(
        ["grep", "-r", "--include=*.py", "AWS_BEARER", "app/"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    offending_lines = [line for line in result.stdout.splitlines() if "config.py" not in line]
    assert offending_lines == [], f"AWS_BEARER referenced outside config.py: {offending_lines}"
