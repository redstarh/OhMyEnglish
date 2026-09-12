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
from pathlib import Path

import boto3
from botocore.config import Config as BotocoreConfig
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# boto3는 이 변수가 프로세스 환경에 있으면 Bedrock 호출에 bearer 인증을 쓴다 —
# 즉 SigV4 키가 함께 있어도 bearer가 이긴다. 그래서 SigV4가 준비된 뒤에는
# `prepare_bedrock_credentials()`가 이 변수를 제거한다.
_BEARER_ENV_KEY = "AWS_BEARER_TOKEN_BEDROCK"

# SigV4 서명에 반드시 필요한 키. `AWS_SESSION_TOKEN`은 임시 자격증명일 때만
# 필요하므로 필수 목록에 넣지 않는다.
_SIGV4_ENV_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY")

# **「환경이 자격증명의 정본인가」를 판정하는 키 집합.**
# `_SIGV4_ENV_KEYS`와 **다르고, 달라야 한다** —
# 그쪽은 「서명에 필수인 키」이고 이쪽은 「환경에 있으면 다른 출처를 섞는 키」다. 세션 토큰은 서명에
# 항상 필요하지는 않지만, 환경에 잔류한 채 `.env`의 영구 키 쌍이 올라오면 **영구 쌍 + 임시 토큰**
# 이라는 섞인 삼중값을 만든다(`TASK-80` 재리뷰 HIGH — 직접 재현했다).
# ⛔ 두 상수를 합치지 마라: `_SIGV4_ENV_KEYS`에 토큰을 넣으면 `missing_sigv4`가 장기 IAM user 키
# 쌍을 **불완전으로 판정**해 SigV4 경로가 통째로 죽는다(장기 키에는 토큰이 없다).
_SIGV4_SOURCE_KEYS = (*_SIGV4_ENV_KEYS, "AWS_SESSION_TOKEN")


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
    # Nova 2 Sonic 어댑터 설정. 모델 ID는 스파이크가 실측으로 확인한 값이고
    # (`amazon.nova-sonic-v1:0`은 이 계정에 없다), voiceId는 실음성 왕복(N-1)에서 쓴 값이다.
    # `nova_endpointing_sensitivity`(HIGH/MEDIUM/LOW)가 barge-in 민감도를 정한다 —
    # 코드 수정 없이 환경변수로 바꿔 발화 종료 감지 시점을 튜닝할 수 있어야 한다(N13).
    nova_model_id: str = "amazon.nova-2-sonic-v1:0"
    nova_voice_id: str = "matthew"
    nova_endpointing_sensitivity: str = "MEDIUM"
    # 드릴당 exchange 수의 하한. 요구사항이 명시한 값(드릴마다 4턴 이상) — `drill_count`가
    # 열거·기대값의 상한(`min(질문 수, drill_count)`)이고 이 값이 턴 수다(설계서 §3).
    # 상한은 두지 않는다(발명하지 않는다) — `ge=1`이 기동 시점에 값역 위반을 거부한다.
    drill_turns_min: int = Field(default=4, ge=1)
    # 드릴 수의 상한(`min(질문 수, drill_count)`). 캡틴 결정 1 — "드릴 횟수는 설정값
    # (config·env)에 따로 두고 읽는다"(설계서 §3).
    #
    # **기본값은 5다 — 캡틴 결정 17.** 지시문은 `questions[:drill_count]`만 열거하므로
    # (`audio_gateway/nova.build_system_prompt`) 기본이 3이면 **질문 4~5개인 계획의 질문이
    # 대화에 도달하지 않는다.** 그것은 **캡틴 결정 2**(*"계획이 만든 질문 3~5개를 대화 상대에게
    # 전달한다"*)와 **결정 9**(*"계획 = 목표(초점 패턴과 질문 3~5개)"*)를 덮는다.
    # ⚠️ 이전 기본값 `3`은 캡틴이 정한 값이 아니라 **이전 세션의 유도**였다 — 그래서 이 값은
    # 결정을 뒤집는 것이 아니라 유도가 덮고 있던 결정 2를 **복원한다.**
    # **왜 5인가**: `session_plans.questions`의 CHECK가 `3 ≤ len ≤ 5`(`007:42-43`)이므로 5면
    # 절단이 원리적으로 일어나지 않는다. 상한은 여전히 발명하지 않는다(`ge=1`만 둔다).
    # ⚠️ **H-5는 그대로 닫혀 있다** — 운영자가 이 값을 낮추면 **열거와 기대값이 함께** 줄어드므로
    # 설정값이 여전히 대화를 바꾼다. 「통과 문턱만 바꾸는 노브」로 되돌아가지 않는다.
    drill_count: int = Field(default=5, ge=1)

    # ── 쉐도잉 (`TASK-45` · 설계서 `2026-09-08-shadowing-task-design.md` §7.1) ──
    #
    # **새 설정 체계를 만들지 않고 이 클래스에 더한다.** 값역은 **캡틴 결정 6**이 지정했고
    # (재생 0.5~2배 · 반복 1~10회) `ge`/`le`가 그것을 **기동 시점에** 거부한다 — pydantic이
    # `Settings()` 구성에서 `ValidationError`를 던지고 `get_settings()`가 `@lru_cache`라
    # 첫 호출(=앱 기동)에서 터진다. 런타임에 조용히 잘리지 않는 것이 계약이다(§7.2).
    #
    # ⛔ **기본값은 값역의 「항등원」이다 — 발명이 아니라 그 반대다** (설계서 유도 3).
    # 캡틴은 **값역만** 정했고 기본값을 말하지 않았다. 관측 없이 중간값(예: 3회)을 고르면
    # 그 숫자가 코드에 굳고, 나중에 "누가 3을 정했나"에 답할 사람이 없어진다. 값역의 최소는
    # **"설정이 생기는 것만으로 동작이 달라지지 않는 상태"**라서 결정을 선점하지 않는다.
    shadowing_playback_rate: float = Field(default=1.0, ge=0.5, le=2.0)
    # ⚠️ **이것은 지시문을 바꾸는 값이다** — `drill_count`와 같은 부류이고 「통과 문턱만 바꾸는
    # 노브」가 아니다. 코치 지시문이 "각 문장을 N회 따라 말하게 한다"로 이 값을 실으므로
    # **내리면 실제 연습량이 함께 줄어든다.** 그것이 의도가 아니면 내리지 마라.
    shadowing_repeat_count: int = Field(default=1, ge=1, le=10)
    # 학습자 녹음 뿌리. 백엔드 cwd(`app/backend`) 기준 **상대경로**다 — `.env`와 같은 해석.
    # ⛔ **기본값이 `../../`인 것은 편의가 아니라 추적 회피다** (설계서 §4.3 실측):
    # `.gitignore`의 `assets/audio/`는 슬래시를 포함해 **리포루트에만** 앵커되므로
    # `app/backend/assets/audio/`는 **추적 대상이 된다** → 학습자 녹음이 git 에 들어간다.
    # 이 값을 백엔드 트리 안으로 옮기면 개인정보가 커밋된다.
    shadowing_audio_root: Path = Path("../../assets/audio")


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

    셸 export가 있으면 그것을 존중한다.

    ⛔ **키를 하나씩 `setdefault`하지 않는다** (`TASK-80` — 재리뷰 P2). 그러면 환경에 access key
    만 남아 있을 때 `.env`의 secret 이 그 자리를 채워 **두 출처가 섞인 쌍**이 만들어진다. 그러면
    `missing_sigv4`가 비어서 이 함수가 SigV4 준비 완료로 판단하고 **동작 중인 bearer 까지
    지운다** — 결과는 잘못된 서명으로 바뀐 인증이고, 이 SDK 는 자격증명 실패를 예외가 아니라
    **무응답 타임아웃**으로 드러내므로(설계서 §4.2) 원인을 추적하기 어렵다.
    ⛔ 결정 41(자격증명 회전 면제)에 걸리지 않는다 — 회전이 아니라 **선택 로직**의 결함이다.

    그래서 **쌍을 한 출처에서만** 가져온다: 환경에 SigV4 절반이라도 있으면 환경이 정본이고
    `.env`에서 아무것도 빌려 오지 않는다. 환경에 하나도 없을 때만 `.env`의 **완전한 쌍**을
    올린다 — 한쪽만 있는 `.env`도 쌍이 아니므로 올리지 않는다.

    ⚠️ **세션 토큰도 쌍과 같은 출처여야 한다.** 임시 자격증명은 셋이 한 세트라, 한쪽의 영구 키
    쌍에 다른 쪽의 임시 토큰이 붙으면 서명이 거부된다. `TASK-80`의 AC 는 access·secret 만 이름을
    들지만 같은 함수의 같은 기전이고 「동작하던 인증을 깨지 않는다」는 그 기준에 그대로 걸린다.

    ⛔ **그래서 판정 키 집합이 `_SIGV4_SOURCE_KEYS`다** (재리뷰 HIGH 로 고친 자리). 첫 판은 access·
    secret 만 보고 「환경이 정본인가」를 판정했는데, 환경에 **토큰만 잔류**한 상태(이전 SSO 세션의
    찌꺼기)에서 `.env`의 영구 키 쌍을 올려 **영구 쌍 + 임시 토큰**을 만들고 bearer 까지 지웠다.
    ⚠️ 그 결함은 **알고 남긴 축소였다** — 첫 판이 *"환경에 남아 있는 잔여 토큰은 건드리지 않는다"*고
    스스로 적었고 그 문장이 가리키는 상태가 정확히 그것이다. 지금은 잔류 토큰이 환경을 「부분
    자격증명」으로 만들어 아무것도 빌려 오지 않는다.
    """
    if not any(os.environ.get(key) for key in _SIGV4_SOURCE_KEYS):
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            # 이 분기는 세 키가 환경에 **하나도** 없음을 보장하므로 `setdefault`가 아니라 대입이다 —
            # `setdefault`는 「환경이 이길 수 있다」를 시사해 위 게이트의 뜻을 흐린다.
            os.environ["AWS_ACCESS_KEY_ID"] = settings.aws_access_key_id
            os.environ["AWS_SECRET_ACCESS_KEY"] = settings.aws_secret_access_key
            if settings.aws_session_token:
                os.environ["AWS_SESSION_TOKEN"] = settings.aws_session_token

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


# `TASK-39` — 재시도·타임아웃을 **명시**한다. 미설정이면 botocore 1.43.78 의 기본값이 쓰이는데
# 실측으로 그것은 `connect_timeout 60` · `read_timeout 60` · legacy 재시도(**전송 5회**)다.
# 정본은 `runs/2026-09-12-task39-retry-policy.md` 다.
#
# ⛔ **`max_attempts` 를 쓰지 않는다 — 실제 전송 수와 «1» 어긋난다.** 무응답 서버로 직접 센 값:
# `max_attempts=1`→전송 2회 · `2`→3회 · `3`→4회. 반면 `total_max_attempts=N`→정확히 N회다.
# 즉 `max_attempts` 는 「재시도 수」처럼 동작하고, 그 어긋남은 **비용을 두 배로 적게 세게** 만든다.
_BEDROCK_TOTAL_MAX_ATTEMPTS = 2
# ⛔ **재시도를 0(=1회)으로 만들지 않는다** — 스로틀·일시 오류에서 계획 job 이 그대로 실패하면
# 그 세션의 계획이 안 생긴다. ⚠️ 이 값은 job 재시도(`services/jobs.MAX_ATTEMPTS=5`)와 **곱해진다**:
# 최대 청구 횟수가 legacy 기본에서는 5×5=25 였고 이 설정에서는 2×5=10 이다. 그 곱을 줄이는 것이
# 이 태스크의 실질 목표다.
#
# `standard` 모드를 고른 이유: 스로틀(`ThrottlingException`)을 지수 백오프+jitter 로 재시도하고
# 재시도 예산(quota)을 갖는다. legacy 는 재시도 대상이 좁고 예산이 없다.
_BEDROCK_RETRY_MODE = "standard"
# 연결 수립은 빠르다 — 여기서 오래 기다릴 이유가 없다.
_BEDROCK_CONNECT_TIMEOUT = 10
# ⚠️ **읽기 상한은 「짧게」가 아니라 「넉넉히」가 맞다.** 실측(2026-09-12, 계획 크기 프롬프트
# 14,538자 · 입력 6,174 토큰): 한 호출이 **30.27초 · 18.25초**였다. 기본 60초는 그 최대의 2배뿐이고,
# 넘으면 botocore 가 **같은 호출을 다시 보낸다** — 그것이 중복 과금의 기전이다. 그래서 4배로 둔다.
# ⛔ **대가를 적는다**: 인터프리터 종료 시 `asyncio.to_thread` 의 워커 스레드가 진행 중 호출을
# 최대 이 시간만큼 붙잡을 수 있다. lifespan 의 대기는 `WORKER_SHUTDOWN_TIMEOUT=15` 가 끊는다.
_BEDROCK_READ_TIMEOUT = 120


def bedrock_boto_config() -> BotocoreConfig:
    """Bedrock 호출의 재시도·타임아웃 정책 (`TASK-39`).

    함수로 빼는 이유: **불변식 테스트가 자격증명 없이 이 값을 잴 수 있어야 한다.**
    `bedrock_client()`는 `prepare_bedrock_credentials`를 지나므로 단위 테스트에서 부를 수 없다.
    """
    return BotocoreConfig(
        connect_timeout=_BEDROCK_CONNECT_TIMEOUT,
        read_timeout=_BEDROCK_READ_TIMEOUT,
        retries={"mode": _BEDROCK_RETRY_MODE, "total_max_attempts": _BEDROCK_TOTAL_MAX_ATTEMPTS},
    )


def bedrock_client():
    """Create a boto3 `bedrock-runtime` client for the configured region.

    자격증명 획득은 전부 `prepare_bedrock_credentials`에 있다 — 이 두 함수가
    전략을 바꿀 단 하나의 이음새다. 재시도·타임아웃은 `bedrock_boto_config`가 갖는다.
    """
    settings = get_settings()
    prepare_bedrock_credentials(settings)
    return boto3.client(
        "bedrock-runtime", region_name=settings.aws_region, config=bedrock_boto_config()
    )
