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
from typing import Any

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


# TASK-35 — 기본값을 재는 단정을 **주변 환경에서 격리한다.** 창이 둘이고 기전이 다르다:
#   ① `.env` 파일: `model_config`의 `env_file=".env"`가 **프로세스 cwd 기준**이고 게이트는
#      `app/backend`에서 도므로 `app/backend/.env`로 해석된다 — 그 파일이 실재한다(실측 1.6k).
#      ⛔ `.env.example` 첫 줄이 *"Copy this file to app/backend/.env"*이고 그 파일에 이제
#      `DRILL_*`·`SHADOWING_*`이 들어 있다 → **표준 온보딩이 테스트가 읽는 파일에 그 키를 심는다.**
#   ② 셸 환경변수: 실제 환경변수가 `.env`를 **앞지른다**.
# `_env_file=None`이 ①을 닫는다. ②는 `_no_settings_env`가 닫는다.
def _settings_with_credentials(
    key_id: str | None = "AKIADOTENV",
    secret: str | None = "dotenv-secret",
    session_token: str | None = None,
    bearer: str | None = None,
) -> Settings:
    return Settings(
        # `ty`(alpha)는 pydantic-settings가 런타임에 합성하는 `__init__`을 모델링하지
        # 못한다 — 같은 이유의 억제가 이 리포에 이미 있다(`missing-argument`).
        _env_file=None,  # ty: ignore[unknown-argument]
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


def test_partial_environ_sigv4_does_not_borrow_the_other_half_from_dotenv(monkeypatch):
    """`TASK-80` — 환경에 access key 만 있으면 secret 을 `.env`에서 **빌려 오지 않는다.**

    빌려 오면 두 출처가 섞인 쌍이 만들어지고, `missing_sigv4`가 비어서 **동작 중인 bearer 까지
    지워진다.** 결과는 「잘못된 서명으로 바뀐 인증」이라 학습자가 보는 것은 무응답 타임아웃이다
    (설계서 §4.2 — 이 SDK 는 자격증명 실패를 예외로 내지 않는다).

    ⛔ 결정 41(자격증명 회전 면제)에 걸리지 않는다 — 회전이 아니라 **선택 로직**의 결함이다.
    """
    _clear_ambient_env()
    os.environ["AWS_ACCESS_KEY_ID"] = "AKIASHELLONLY"
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = "working-bearer-token"
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: _settings_with_credentials(bearer="dotenv-bearer"),
    )
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    # 셸이 준 절반은 그대로 두고, 나머지 절반을 다른 출처에서 채우지 않는다.
    assert os.environ["AWS_ACCESS_KEY_ID"] == "AKIASHELLONLY"
    assert "AWS_SECRET_ACCESS_KEY" not in os.environ
    # AC#2 — 동작하던 인증을 깨지 않는 것이 기준이다.
    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "working-bearer-token"


def test_partial_environ_secret_only_does_not_borrow_the_access_key(monkeypatch):
    """반대 방향도 같다 — 한쪽만 검사하면 다른 쪽 순서에서 결함이 살아남는다.

    ⚠️ 두 방향을 함께 재는 이유: 구현이 `AWS_ACCESS_KEY_ID`의 존재만 보고 분기하면 이 케이스가
    조용히 통과한다(`.env` 의 access key 가 주입되고 다시 섞인 쌍이 된다).
    """
    _clear_ambient_env()
    os.environ["AWS_SECRET_ACCESS_KEY"] = "shell-secret-only"
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = "working-bearer-token"
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: _settings_with_credentials(bearer="dotenv-bearer"),
    )
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "shell-secret-only"
    assert "AWS_ACCESS_KEY_ID" not in os.environ
    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "working-bearer-token"


def test_environ_sigv4_pair_does_not_take_a_session_token_from_dotenv(monkeypatch):
    """세션 토큰도 **쌍과 같은 출처**여야 한다 — 임시 자격증명은 셋이 한 세트다.

    셸의 영구 키 쌍에 `.env` 의 임시 세션 토큰이 붙으면 서명이 거부된다. `TASK-80` AC 는 access
    와 secret 만 이름을 들지만 **같은 함수의 같은 기전**이고 AC#2 의 기준(동작하던 인증을 깨지
    않는다)에 그대로 걸린다.
    """
    _clear_ambient_env()
    os.environ["AWS_ACCESS_KEY_ID"] = "AKIASHELL"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "shell-secret"
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: _settings_with_credentials(session_token="dotenv-session-token"),
    )
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    assert os.environ["AWS_ACCESS_KEY_ID"] == "AKIASHELL"
    assert os.environ["AWS_SECRET_ACCESS_KEY"] == "shell-secret"
    assert "AWS_SESSION_TOKEN" not in os.environ


def test_a_stale_environ_session_token_blocks_borrowing_a_dotenv_pair(monkeypatch):
    """`TASK-80` 재리뷰 HIGH — **반대 방향의 섞임.** 이전 고침이 이 경로를 못 막았다.

    입력: 셸에 `AWS_SESSION_TOKEN`만 잔류하고(이전 SSO 임시 자격증명에서 access·secret 은 지웠지만
    토큰을 안 지운 상태) `.env`에는 **영구 IAM user 키 쌍**이 있다 — 장기 키에는 세션 토큰이 없는
    것이 정상이다(`Settings.aws_session_token` 주석).

    이전 판의 사고 경로: 환경의 access·secret 이 둘 다 없으므로 쌍 주입 분기에 들어가고, `.env`에
    토큰이 없어 주입을 건너뛰므로 **잔류 토큰이 그대로 남는다.** 그러면 영구 키 쌍 + 임시 토큰이라는
    삼중값이 만들어지고, `missing_sigv4`는 그 토큰을 보지 않으므로 SigV4 준비 완료로 판단해
    **동작 중인 bearer 를 지운다.** 결과는 잘못된 서명이고 이 SDK 는 그것을 무응답 타임아웃으로만
    드러낸다(설계서 §4.2).

    ⛔ **이것은 알고 남긴 축소였다.** 이전 판 docstring 이 *"환경에 남아 있는 잔여 토큰은 건드리지
    않는다"*고 스스로 적었고, 그 문장이 가리키는 상태가 정확히 이 결함이다. 「환경이 정본인가」를
    판정하는 키 집합에 세션 토큰을 넣어 닫는다.
    """
    _clear_ambient_env()
    os.environ["AWS_SESSION_TOKEN"] = "stale-leftover-token"
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = "working-bearer-token"
    monkeypatch.setattr(config_module, "get_settings", _settings_with_credentials)
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    # `.env` 의 쌍을 빌려 오지 않는다 — 잔류 토큰이 이미 환경을 「부분 자격증명」으로 만들었다.
    assert "AWS_ACCESS_KEY_ID" not in os.environ
    assert "AWS_SECRET_ACCESS_KEY" not in os.environ
    assert os.environ["AWS_SESSION_TOKEN"] == "stale-leftover-token"
    # AC#2 — 동작하던 인증을 깨지 않는다.
    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "working-bearer-token"


def test_a_stale_environ_session_token_is_not_beaten_by_a_dotenv_token(monkeypatch):
    """같은 게이트의 둘째 방향 — `.env`가 **삼종 전부**를 가져도 잔류 토큰이 있으면
    빌려 오지 않는다.

    이전 판은 토큰을 `setdefault`로 올렸다. 그러면 `.env`의 **정확히 짝이 맞는** 토큰조차 주입되지
    않고 잔류 토큰이 이겨서, *"쌍은 한 출처에서만 온다"*는 그 커밋이 세운 계약을 이 경로에서 스스로
    어긴다(재리뷰가 지목한 두 번째 자리).

    ⚠️ 이 케이스는 위 테스트와 **다른 것을 잡는다**: 위는 「빌려 오지 않는다」이고 이것은 「짝이
    맞아도 빌려 오지 않는다」다. 게이트를 토큰 유무로 두면 둘 다 닫히지만, 토큰 주입만 `setdefault`
    에서 대입으로 바꾸면 위 케이스가 남는다.
    """
    _clear_ambient_env()
    os.environ["AWS_SESSION_TOKEN"] = "stale-leftover-token"
    os.environ["AWS_BEARER_TOKEN_BEDROCK"] = "working-bearer-token"
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: _settings_with_credentials(session_token="dotenv-session-token"),
    )
    _stub_boto3(monkeypatch)

    config_module.bedrock_client()

    assert "AWS_ACCESS_KEY_ID" not in os.environ
    assert os.environ["AWS_SESSION_TOKEN"] == "stale-leftover-token"
    assert os.environ["AWS_BEARER_TOKEN_BEDROCK"] == "working-bearer-token"


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


def test_drill_settings_default_to_four_and_five(_no_settings_env):
    """기본값은 요구사항이 명시한 값(드릴마다 4턴 이상)과 **캡틴 결정 17**(드릴 수 상한 5).

    ⚠️ `drill_count` 기본값은 **3에서 5로 올라갔다**. 지시문이 `questions[:drill_count]`만
    열거하므로 3이면 질문 4~5개인 계획의 질문이 대화에 도달하지 않고, 그것이 캡틴 결정 2
    (*"질문 3~5개를 전달한다"*)를 덮었다. 이전 값 3은 캡틴이 정한 값이 아니라 이전 세션의
    유도였다 — 근거 전문은 `app/config.py`의 그 필드 주석이 소유한다.
    """
    settings = _settings_with_credentials()

    assert settings.drill_turns_min == 4
    assert settings.drill_count == 5


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


# ── 기본값 격리 (TASK-35) ────────────────────────────────────────────────────
#
# ⛔ **가장 값있는 단정은 인스턴스가 아니라 클래스를 읽는다.** 우리가 잠그려는 것은
# 「pydantic이 무엇을 적용했나」가 아니라 **「선언된 기본값이 무엇인가」**이고, 그것은
# `Settings.model_fields[…].default`에 있다 — **환경변수도 `.env`도 그 값에 닿을 수 없다.**
# 실측(2026-09-08): `DRILL_COUNT=9 SHADOWING_REPEAT_COUNT=7 SHADOWING_PLAYBACK_RATE=1.75`인
# 프로세스에서 선언값은 `5·1·1.0` 그대로였고 **인스턴스는 `9·7·1.75`로 오염됐다.**
# → 그래서 아래 `test_declared_defaults_…`가 **무력화할 수 없는 tripwire**이고, 인스턴스
#   테스트는 "pydantic이 그 값을 실제로 적용한다"를 따로 본다(그쪽은 격리가 필요하다).
#
# **왜 전역 autouse로 환경을 비우지 않았나**: `database_url`도 `Settings` 필드라서 전역으로
# 지우면 `tests/conftest.py`의 DB 픽스처가 읽는 `DATABASE_URL`까지 사라진다. 격리는 그 값을
# 재는 테스트에만 국소로 건다.

# 이 목록을 손으로 유지하지 않는다 — 필드가 늘면 자동으로 따라온다(AC#3의 구조적 답).
# `case_sensitive: False`(실측 `model_config`)이므로 대소문자 무관하게 지운다.
_SETTINGS_FIELD_NAMES = frozenset(Settings.model_fields)


@pytest.fixture
def _no_settings_env(monkeypatch):
    """`Settings` 필드를 먹일 수 있는 셸 환경변수를 **이 테스트 동안만** 지운다.

    ⛔ `database_url`은 남긴다 — 지우면 DB 픽스처가 죽는다(위 주석). 기본값을 재는 쪽은
    그 값을 인자로 명시하므로 남겨도 단정에 영향이 없다.
    """
    for key in list(os.environ):
        if key.lower() in _SETTINGS_FIELD_NAMES and key.lower() != "database_url":
            monkeypatch.delenv(key, raising=False)


def test_declared_defaults_are_immune_to_the_environment():
    """⛔ **무력화할 수 없는 tripwire** — 클래스의 선언값을 읽으므로 환경이 닿지 않는다.

    이 단정이 깨지는 유일한 경로는 **누가 `config.py`의 기본값을 바꾸는 것**이고, 그것이
    정확히 우리가 알고 싶은 사건이다. 값의 근거는 각 필드 주석이 소유한다 —
    `drill_turns_min=4`(요구사항) · `drill_count=5`(캡틴 결정 17) ·
    쉐도잉 셋(캡틴 결정 6의 값역 + 그 항등원 · 설계서 유도 3).
    """
    declared = {name: field.default for name, field in Settings.model_fields.items()}

    assert declared["drill_turns_min"] == 4
    assert declared["drill_count"] == 5
    assert declared["shadowing_playback_rate"] == 1.0
    assert declared["shadowing_repeat_count"] == 1
    assert declared["shadowing_audio_root"] == Path("../../assets/audio")
    # 모델 ID도 같은 부류다 — `test_claude_schema.py`가 이 값을 리터럴로 단정한다.
    assert declared["claude_model_id"] == "us.anthropic.claude-opus-5"


# TASK-45 — 쉐도잉 설정값 3종 (설계서 `2026-09-08-shadowing-task-design.md` §7.1·§7.2).
# ⛔ **기본값은 값역의 「항등원」이다** — 캡틴 결정 6은 **값역만** 지정했고 기본값을 말하지
#    않았다(설계서 유도 3). 관측 없이 중간값을 고르면 그 숫자가 코드에 굳는다. `1.0`배·`1`회는
#    "설정이 생기는 것만으로 재생·연습량이 달라지지 않는 상태"라서 발명이 아니다.
# ⚠️ `shadowing_repeat_count`는 **지시문을 바꾸는 값이다**(`drill_count`와 같은 부류) —
#    "통과 문턱만 바꾸는 노브"가 아니라 내리면 실제 연습량이 함께 줄어든다.


def test_shadowing_settings_default_to_the_range_identities(_no_settings_env):
    """기본값이 값역의 항등원이다 — `1.0`배 · `1`회. 설정 도입이 동작을 바꾸지 않는다."""
    settings = _settings_with_credentials()

    assert settings.shadowing_playback_rate == 1.0
    assert settings.shadowing_repeat_count == 1


def test_shadowing_audio_root_defaults_outside_the_backend_tree(_no_settings_env):
    """⚠️ 기본값이 `../../assets/audio`인 것은 편의가 아니라 **추적 회피**다 (설계서 §4.3).

    `.gitignore`의 `assets/audio/`는 슬래시를 포함해 **리포루트에만** 앵커되므로
    `app/backend/assets/audio/`는 **추적 대상이 된다** — 학습자 녹음이 git 에 들어간다.
    이 단정이 무너지면 개인정보가 커밋된다.
    """
    settings = _settings_with_credentials()

    assert settings.shadowing_audio_root == Path("../../assets/audio")
    # 백엔드 트리 **안**을 가리키지 않는다 — 위 근거가 이 성질에 걸려 있다.
    assert not (BACKEND_ROOT / settings.shadowing_audio_root).resolve().is_relative_to(BACKEND_ROOT)


@pytest.mark.parametrize("rate", [0.49, 2.01])
def test_shadowing_playback_rate_rejects_out_of_range_at_startup(rate: float):
    """캡틴 결정 6의 0.5~2.0배가 **계약**이므로 기동 시점에 거부한다 (설계서 §7.2).

    런타임에 조용히 잘리면 학습자가 들은 속도와 설정이 갈라진다.
    """
    with pytest.raises(pydantic.ValidationError):
        Settings(
            database_url="postgresql://fake:fake@localhost/fake",
            aws_region="us-west-2",
            shadowing_playback_rate=rate,
        )


@pytest.mark.parametrize("count", [0, 11])
def test_shadowing_repeat_count_rejects_out_of_range_at_startup(count: int):
    """같은 모양 — 캡틴 결정 6의 1~10회. 경계 **밖** 두 값을 함께 본다."""
    with pytest.raises(pydantic.ValidationError):
        Settings(
            database_url="postgresql://fake:fake@localhost/fake",
            aws_region="us-west-2",
            shadowing_repeat_count=count,
        )


@pytest.mark.parametrize(("rate", "count"), [(0.5, 1), (2.0, 10)])
def test_shadowing_range_endpoints_are_accepted(rate: float, count: int):
    """⛔ 경계값은 **받는다** — 결정 6이 정한 것은 `0.5~2.0`·`1~10`이고 그 끝을 포함한다.

    `gt`/`lt`를 잘못 쓰면 이 테스트만 깨진다(위 거부 테스트는 통과한 채로).
    """
    settings = _settings_with_credentials()
    tuned = settings.model_copy(update={})  # 기본 인스턴스가 유효한 것을 먼저 확인한다
    assert tuned is not None

    accepted = Settings(
        database_url="postgresql://fake:fake@localhost/fake",
        aws_region="us-west-2",
        shadowing_playback_rate=rate,
        shadowing_repeat_count=count,
    )
    assert accepted.shadowing_playback_rate == rate
    assert accepted.shadowing_repeat_count == count


# ── `TASK-39` — 재시도·타임아웃 정책을 «불변식»으로 잰다 ─────────────────────────────
#
# 미설정이면 botocore 기본값이 쓰이고 실측으로 그것은 legacy 재시도(전송 5회)다. 정책이 조용히
# 사라지는 것을 막는 자리가 여기다. 수치의 근거는 `runs/2026-09-12-task39-retry-policy.md` 다.


def _boto_option(config: object, name: str) -> Any:
    """botocore `Config` 의 옵션 하나를 읽는다.

    ⛔ **억제를 한 자리로 모으는 함수다.** botocore 는 옵션을 `__init__`에서 **동적으로** 심으므로
    `ty` 가 `config.read_timeout` 같은 속성을 보지 못한다(alpha 단계의 한계이고 이 리포에 같은
    부류의 억제가 이미 있다 — `pydantic-settings` 의 합성 `__init__`). 줄마다 `ty: ignore` 를
    붙이면 무엇을 왜 억제했는지 흩어지므로 이 함수 하나로 모은다.
    """
    return getattr(config, name)


# 실측 최대 소요 시간(계획 크기 프롬프트 14,538자 · 입력 6,174 토큰 · 2026-09-12): 30.27초.
# ⛔ 이 상수를 낮추지 마라 — 낮추면 아래 여유 단정이 무력해진다.
_MEASURED_MAX_CALL_SECONDS = 30.27


def test_bedrock_config_caps_the_number_of_billed_sends():
    """⛔ 전송 수 상한이 명시돼 있어야 한다 — 미설정이면 legacy 기본이 **전송 5회**다.

    ⛔ **`max_attempts` 키를 쓰지 않는다**: 무응답 서버로 직접 센 값이 `max_attempts=1`→2회 ·
    `2`→3회 · `3`→4회로 **1 어긋난다.** `total_max_attempts=N`은 정확히 N회다. 그 어긋남은 비용을
    실제보다 적게 세게 만들므로 키 이름 자체를 단정한다.
    """
    retries = _boto_option(config_module.bedrock_boto_config(), "retries")

    assert retries == {"mode": "standard", "total_max_attempts": 2}
    assert "max_attempts" not in retries, "뜻이 1 어긋나는 키다 — total_max_attempts 를 쓴다"


def test_the_read_timeout_keeps_a_margin_over_the_measured_call_duration():
    """⛔ 읽기 상한이 실측 소요 시간에 가까우면 **정상 호출이 다시 보내진다**(=중복 과금).

    ⚠️ 여유를 3배로 두는 것은 표본 2에서 분포를 주장하지 않기 위해서다 — 관측값보다 넉넉하다는
    것만 단정한다. 연결 상한은 별개다: 연결 수립이 느린 것은 재시도로 풀 문제이므로 짧게 둔다.
    """
    config = config_module.bedrock_boto_config()

    read_timeout = _boto_option(config, "read_timeout")
    assert read_timeout >= 3 * _MEASURED_MAX_CALL_SECONDS
    assert _boto_option(config, "connect_timeout") <= read_timeout / 4


def test_bedrock_client_actually_receives_that_config(monkeypatch):
    """⛔ **배선 누락을 잡는 단정이다** — 정책을 만들어 두고 넘기지 않으면 기본값이 조용히 쓰인다.

    ⚠️ 값이 있는지만 보지 않고 **팩토리가 받은 객체가 그 정책인지**까지 본다.
    """
    _clear_ambient_env()
    monkeypatch.setattr(config_module, "get_settings", _settings_with_credentials)
    captured: dict[str, object] = {}

    def capture_client(*args: object, **kwargs: object) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(config_module.boto3, "client", capture_client)

    config_module.bedrock_client()

    passed = captured.get("config")
    assert passed is not None, "config= 를 넘기지 않았다 — botocore 기본값이 쓰인다"
    expected = config_module.bedrock_boto_config()
    assert _boto_option(passed, "retries") == _boto_option(expected, "retries")
    assert _boto_option(passed, "read_timeout") == _boto_option(expected, "read_timeout")


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
