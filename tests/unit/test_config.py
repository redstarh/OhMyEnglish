"""Task 1 — config/scaffolding tests.

These tests never touch the database (per controller ruling): they only
exercise `Settings`, the Bedrock SDK import, and the credential-isolation
guarantee (AWS_BEARER_TOKEN_BEDROCK must not leak outside config.py).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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
