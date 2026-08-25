"""Single point of credential acquisition for the OhMyEnglish backend.

SigV4 자격증명(`AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_SESSION_TOKEN`)은
이 모듈 밖에서 읽거나 재수출하지 않는다(F5). `bedrock_client()`가 `Settings`를
boto3 Bedrock 클라이언트로 바꾸는 유일한 팩토리다 — 자격증명 전략이 또 바뀌면
고칠 곳은 이 함수 하나다.

**목표는 SigV4 단일 경로** (설계서 §4.1, `docs/ops/iam-setup-nova-sigv4.md`).
Nova Sonic 양방향 스트림이 bearer를 HTTP 403 `This operation does not support
API Keys`로 거부하고(실측), SigV4는 Nova 양방향과 Claude invoke 양쪽에 쓸 수
있어 경로를 둘로 유지할 이유가 없다.

**전환기 우선순위 — SigV4 > bearer** (캡틴 지시 2026-08-25). SigV4 자격증명
발급 전까지 동작 중인 Claude 분석 경로를 깨뜨리지 않는다.

| `.env`/환경 상태 | 동작 |
|---|---|
| SigV4 있음 | SigV4 사용 + **bearer 제거** (단일 경로 강제) |
| SigV4 없고 bearer 있음 | bearer 사용 (전환기 — Nova는 아직 불가) |
| 둘 다 없음 | 즉시 실패 (§4.2 — 무응답으로 숨지 않게) |
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache

import boto3
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# boto3는 이 변수가 프로세스 환경에 있으면 Bedrock 호출에 bearer 인증을 쓴다 —
# 즉 SigV4 키가 함께 있어도 bearer가 이긴다. 그래서 SigV4가 준비된 뒤에는
# `prepare_bedrock_credentials()`가 이 변수를 제거한다.
_BEARER_ENV_KEY = "AWS_BEARER_TOKEN_BEDROCK"

# SigV4 서명에 반드시 필요한 키. `AWS_SESSION_TOKEN`은 임시 자격증명일 때만
# 필요하므로 필수 목록에 넣지 않는다.
_SIGV4_ENV_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    aws_region: str
    # SigV4 자격증명. `.env`(gitignore 대상)에 두거나 셸에 export한다 — 후자가 우선.
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    # 임시 자격증명(`aws configure export-credentials`, IAM Identity Center 경유)일
    # 때만 채워진다. 장기 IAM user access key에는 없다.
    aws_session_token: str | None = None
    # 전환기 폴백. SigV4가 채워지면 이 값은 무시되고 프로세스 환경에서도 제거된다.
    aws_bearer_token_bedrock: str | None = None
    claude_model_id: str = "us.anthropic.claude-opus-5"
    # 분석 워커 기동 플래그. 기본은 켜짐 — API만 띄우고 큐를 일부러 쌓아두는
    # 시나리오(E2E-S 3단계)에서만 끈다. 자격증명이 아직 없을 때 백엔드를
    # 기동하려면 이 값을 false로 둔다(워커만 Bedrock 클라이언트를 만든다).
    worker_enabled: bool = True
    # 음성 어댑터 구현 선택 (G3). 첫 슬라이스의 값은 `stub`(픽스처 재생)과
    # `stub_unresponsive`(연결 실패 시나리오 E2E-S 6을 코드 수정 없이 재현) 둘이다.
    # Nova 어댑터가 들어오면 값이 하나 늘고, 분기는 `audio_gateway/factory.py`
    # 한 곳에만 있다.
    voice_adapter: str = "stub"


@lru_cache
def get_settings() -> Settings:
    """Process-wide cached Settings singleton."""
    # pydantic-settings synthesizes __init__ from env/.env at runtime; ty
    # (alpha, v0.0.31) does not yet model that and treats the required
    # fields as missing constructor arguments here.
    return Settings()  # ty: ignore[missing-argument]


def prepare_bedrock_credentials(settings: Settings) -> None:
    """SigV4 자격증명을 프로세스 환경에 올리고 bearer 경로를 닫는다.

    `settings`를 인자로 받는 이유: 호출자가 `get_settings()`(lru_cache)를 아직
    채우고 싶지 않을 수 있다. `scripts/smoke_analysis.py`는 `DATABASE_URL`을
    덮어쓰기 **전에** 자격증명만 검사하는데, 그 시점에 캐시를 채우면 dev DSN이
    프로세스 수명 동안 고정된다.

    pydantic-settings는 `.env` 값을 `Settings`에만 담고 `os.environ`에 재수출하지
    않는다. boto3와 Nova SDK(smithy)는 **프로세스 환경만** 보므로 `.env`에만 있는
    자격증명은 어느 쪽에도 보이지 않는다 — 한 번 주입한다.

    `setdefault`이므로 셸 export가 있으면 그것을 존중한다(no-op).
    """
    for env_key, value in (
        ("AWS_ACCESS_KEY_ID", settings.aws_access_key_id),
        ("AWS_SECRET_ACCESS_KEY", settings.aws_secret_access_key),
        ("AWS_SESSION_TOKEN", settings.aws_session_token),
    ):
        if value:
            os.environ.setdefault(env_key, value)

    missing_sigv4 = [key for key in _SIGV4_ENV_KEYS if not os.environ.get(key)]

    if not missing_sigv4:
        # SigV4가 준비됐다 — 이제 단일 경로를 강제한다. bearer가 남아 있으면
        # boto3가 Bedrock 호출에 그것을 써서 Claude만 bearer, Nova만 SigV4인
        # 이중 경로가 된다(개발 셸에 실제로 export되어 있다).
        os.environ.pop(_BEARER_ENV_KEY, None)
        return

    # 전환기 폴백 — SigV4 발급 전까지 동작 중인 Claude 경로를 깨뜨리지 않는다
    # (캡틴 지시 2026-08-25). bearer는 Claude invoke에만 통하고 Nova 양방향에는
    # HTTP 403이므로, Nova 연동 착수 전에 SigV4로 넘어가야 한다.
    if settings.aws_bearer_token_bedrock:
        # `.env`에만 있는 값은 boto3가 못 본다 — 커밋 f33d22a가 고친 함정이다.
        os.environ.setdefault(_BEARER_ENV_KEY, settings.aws_bearer_token_bedrock)
    if os.environ.get(_BEARER_ENV_KEY):
        logger.warning(
            "SigV4 자격증명이 없어 bearer token으로 Bedrock을 호출한다 (전환기). "
            "Claude invoke는 동작하지만 Nova 양방향 스트림은 HTTP 403이다 — "
            "발급 절차: docs/ops/iam-setup-nova-sigv4.md"
        )
        return

    # 설계서 §4.2: 이 SDK는 자격증명 실패를 예외가 아니라 무응답(타임아웃)으로
    # 드러낸다. 원인 불명의 무한 대기를 만들지 않으려면 여기서 즉시 실패한다.
    raise RuntimeError(
        f"Bedrock 자격증명이 없다 — SigV4({', '.join(missing_sigv4)})도 "
        f"{_BEARER_ENV_KEY}도 없다. `.env`에 넣거나 셸에 export하라 — "
        "절차는 docs/ops/iam-setup-nova-sigv4.md. "
        "자격증명 없이 백엔드만 띄우려면 WORKER_ENABLED=false로 기동하라."
    )


def bedrock_client():
    """Create a boto3 `bedrock-runtime` client for the configured region.

    자격증명 획득은 전부 `prepare_bedrock_credentials`에 있다 — 이 두 함수가
    전략을 바꿀 단 하나의 이음새다.
    """
    settings = get_settings()
    prepare_bedrock_credentials(settings)
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)
