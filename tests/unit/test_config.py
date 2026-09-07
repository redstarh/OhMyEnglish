"""Task 1 — config/scaffolding tests (SigV4 전환판).

DB를 건드리지 않는다 — `Settings`, Bedrock SDK import, 그리고 자격증명 격리
보장(자격증명 문자열이 config.py 밖으로 새지 않는다)만 검증한다.

2026-08-25 SigV4 전환: SigV4(`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`) 계약을
추가했다. 근거는 설계서 §4.1의 "백엔드는 SigV4 단일 경로"이고, Nova 양방향
스트림이 bearer를 HTTP 403 `This operation does not support API Keys`로 거부한다는
실측이다.

**전환기 계약** (캡틴 지시 2026-08-25): SigV4 자격증명이 발급되기 전까지 동작
중인 Claude 분석 경로를 깨뜨리지 않는다. 우선순위는 SigV4 > bearer이고,
SigV4가 준비된 뒤에만 bearer를 제거해 단일 경로를 강제한다. 둘 다 없을 때만
실패한다.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pydantic
import pytest

from app import config as config_module
from app.config import Settings

BACKEND_ROOT = Path(__file__).resolve().parents[2] / "app" / "backend"

# `bedrock_client()`는 os.environ을 직접 바꾼다 — Nova SDK(smithy)가 프로세스
# 환경만 읽으므로 의도된 동작이다. monkeypatch가 추적하지 못하는 그 변경이 다른
# 테스트로 새지 않게, 이 모듈의 모든 테스트에서 관련 키를 스냅샷·복원한다.
_AWS_ENV_KEYS = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "AWS_BEARER_TOKEN_BEDROCK",
    "AWS_REGION",
    "DATABASE_URL",
    "CLAUDE_MODEL_ID",
)


@pytest.fixture(autouse=True)
def _isolate_aws_env():
    saved = {key: os.environ.get(key) for key in _AWS_ENV_KEYS}
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _clear_ambient_env() -> None:
    """실제 환경변수가 `.env` 값을 앞지르므로, Claude Code 세션 자신의 변수를
    지워 테스트가 `.env` 픽스처와 주입 동작만 관찰하게 한다."""
    for key in _AWS_ENV_KEYS:
        os.environ.pop(key, None)


def _stub_boto3(monkeypatch) -> None:
    monkeypatch.setattr(config_module.boto3, "client", lambda *args, **kwargs: object())


def _settings_with_credentials(
    key_id: str | None = "AKIADOTENV",
    secret: str | None = "dotenv-secret",
    session_token: str | None = None,
    bearer: str | None = None,
) -> Settings:
    return Settings(
        database_url="postgresql://fake:fake@localhost/fake",
        aws_region="us-west-2",
        aws_access_key_id=key_id,
        aws_secret_access_key=secret,
        aws_session_token=session_token,
        aws_bearer_token_bedrock=bearer,
    )


def test_settings_reads_dotenv(tmp_path, monkeypatch):
    """Settings()가 인자 없이 cwd의 `.env`를 읽는다. 자격증명은 선택값이다."""
    _clear_ambient_env()
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://ohmy:ohmy@localhost:5433/ohmyenglish\nAWS_REGION=us-west-2\n"
    )
    monkeypatch.chdir(tmp_path)

    # pydantic-settings는 env/.env에서 __init__을 런타임에 합성하지만
    # ty(alpha)는 그것을 모델링하지 못해 필수 인자 누락으로 본다.
    settings = Settings()  # ty: ignore[missing-argument]

    assert settings.database_url == "postgresql://ohmy:ohmy@localhost:5433/ohmyenglish"
    assert settings.aws_region == "us-west-2"
    assert settings.claude_model_id == "us.anthropic.claude-opus-5"
    assert settings.aws_access_key_id is None
    assert settings.aws_secret_access_key is None
    assert settings.aws_session_token is None
    assert settings.aws_bearer_token_bedrock is None


def test_settings_reads_sigv4_credentials(tmp_path, monkeypatch):
    _clear_ambient_env()
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URL=postgresql://ohmy:ohmy@localhost:5433/ohmyenglish\n"
        "AWS_REGION=us-west-2\n"
        "AWS_ACCESS_KEY_ID=AKIATESTVALUE\n"
        "AWS_SECRET_ACCESS_KEY=test-secret-value\n"
    )
    monkeypatch.chdir(tmp_path)

    settings = Settings()  # ty: ignore[missing-argument]

    assert settings.aws_access_key_id == "AKIATESTVALUE"
    assert settings.aws_secret_access_key == "test-secret-value"


def test_bedrock_sdk_is_importable():
    result = subprocess.run(
        [sys.executable, "-c", "import aws_sdk_bedrock_runtime"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_bedrock_client_injects_dotenv_credentials_when_environ_lacks_them(monkeypatch):
    """pydantic-settings는 `.env` 값을 `Settings`에만 담고 os.environ에 재수출하지
    않는다. boto3와 Nova SDK는 프로세스 환경만 보므로 한 번 주입해야 한다."""
    _clear_ambient_env()
    monkeypatch.setattr(config_module, "get_settings", _settings_with_credentials)
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    assert os.environ["AWS_ACCESS_KEY_ID"] == "AKIADOTENV"
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "dotenv-secret"


def test_bedrock_client_preserves_existing_environ_credentials(monkeypatch):
    """셸 export가 `.env`를 앞지른다 — 이미 있는 값을 덮어쓰지 않는다."""
    _clear_ambient_env()
    os.environ["AWS_ACCESS_KEY_ID"] = "AKIASHELL"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "shell-secret"
    monkeypatch.setattr(config_module, "get_settings", _settings_with_credentials)
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    assert os.environ["AWS_ACCESS_KEY_ID"] == "AKIASHELL"
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "shell-secret"


def test_bedrock_client_removes_bearer_once_sigv4_is_available(monkeypatch):
    """SigV4 단일 경로(설계서 §4.1, `docs/ops/iam-setup-nova-sigv4.md`).

    SigV4 자격증명이 **있을 때** bearer가 남아 있으면 boto3가 Bedrock 호출에
    그것을 써서 Claude만 bearer, Nova만 SigV4인 이중 경로가 된다. 개발 셸에
    실제로 export되어 있어(2026-08-25 실측) 그때는 제거가 필수다.
    """
    _clear_ambient_env()
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = "ambient-shell-bearer"
    monkeypatch.setattr(config_module, "get_settings", _settings_with_credentials)
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    assert "AWS_BEARER_TOKEN_BEDROCK" not in os.environ


def test_bedrock_client_keeps_bearer_while_sigv4_is_absent(monkeypatch):
    """전환기 동작 (캡틴 지시 2026-08-25).

    SigV4 자격증명 발급 전까지 **동작 중인 Claude 분석 경로를 깨뜨리지 않는다.**
    SigV4가 없고 bearer가 있으면 bearer를 그대로 두고 성공해야 한다 — 이 조합에서
    자격증명을 요구하며 실패하면 워커가 기동하지 못한다.
    """
    _clear_ambient_env()
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = "working-bearer-token"
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: _settings_with_credentials(key_id=None, secret=None),
    )
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "working-bearer-token"
    assert "AWS_ACCESS_KEY_ID" not in os.environ


def test_bedrock_client_injects_dotenv_bearer_when_sigv4_is_absent(monkeypatch):
    """bearer가 `.env`에만 있어도 boto3가 보게 주입한다 — 커밋 `f33d22a`가 고친
    함정이며, 전환기에도 그 계약이 유지되어야 한다."""
    _clear_ambient_env()
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: _settings_with_credentials(key_id=None, secret=None, bearer="dotenv-bearer"),
    )
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "dotenv-bearer"


def test_bedrock_client_exports_session_token_when_present(monkeypatch):
    """`aws configure export-credentials`로 얻는 임시 자격증명에는 세션 토큰이
    딸려 온다 — 빠뜨리면 SigV4 서명이 거부된다."""
    _clear_ambient_env()
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: _settings_with_credentials(session_token="temporary-session-token"),
    )
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    assert os.environ["AWS_SESSION_TOKEN"] == "temporary-session-token"


def test_bedrock_client_fails_fast_when_no_credentials_of_any_kind(monkeypatch):
    """설계서 §4.2 — 이 SDK는 자격증명 실패를 예외가 아니라 무응답(타임아웃)으로
    드러낸다. 원인을 추적할 수 있게 클라이언트를 만들기 전에 즉시 실패한다.

    SigV4도 bearer도 없을 때만 실패한다 — bearer만 있는 전환기 상태는 정상이다.
    """
    _clear_ambient_env()
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: _settings_with_credentials(key_id=None, secret=None),
    )
    _stub_boto3(monkeypatch)

    with pytest.raises(RuntimeError, match="AWS_ACCESS_KEY_ID"):
        config_module.bedrock_client()


# TASK-6 Batch A — 드릴 턴 수 설정값 (설계서 §3). `drill_count`가 열거·기대값의
# 상한(`min(질문 수, drill_count)`)이고 `drill_turns_min`이 드릴당 exchange 수다.


def test_drill_settings_default_to_four_and_three():
    """기본값은 요구사항이 명시한 값(드릴마다 4턴 이상)과 캡틴 결정 1(드릴 횟수 3)."""
    settings = _settings_with_credentials()

    assert settings.drill_turns_min == 4
    assert settings.drill_count == 3


def test_drill_turns_min_rejects_zero_at_startup():
    """값역 위반은 기동 시점에 거부된다 — 런타임에 조용히 잘리지 않는다(설계서 §3)."""
    with pytest.raises(pydantic.ValidationError):
        Settings(
            database_url="postgresql://fake:fake@localhost/fake",
            aws_region="us-west-2",
            drill_turns_min=0,
        )


def test_drill_count_rejects_zero_at_startup():
    """같은 모양 — `ge=1`이 `drill_count`에도 걸린다(설계서 532줄)."""
    with pytest.raises(pydantic.ValidationError):
        Settings(
            database_url="postgresql://fake:fake@localhost/fake",
            aws_region="us-west-2",
            drill_count=0,
        )


def test_credential_strings_isolated_to_config_module():
    """F5: 자격증명 문자열은 config.py 밖의 `app/` 코드에 등장하지 않는다."""
    for needle in ("AWS_BEARER", "AWS_SECRET_ACCESS_KEY", "AWS_ACCESS_KEY_ID"):
        result = subprocess.run(
            ["grep", "-r", "--include=*.py", needle, "app/"],
            cwd=BACKEND_ROOT,
            capture_output=True,
            text=True,
        )
        offending = [line for line in result.stdout.splitlines() if "config.py" not in line]
        assert offending == [], f"{needle} referenced outside config.py: {offending}"
