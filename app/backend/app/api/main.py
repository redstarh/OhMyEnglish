"""FastAPI application factory + lifespan (DB pool·분석 워커 기동/정지).

워커를 별도 프로세스가 아니라 API의 lifespan에 붙인다 — 단일 사용자 로컬
도구에서 프로세스를 하나 더 운영할 이유가 없고, job이 테이블에 남으므로
프로세스가 죽어도 재기동 후 이어진다 (설계서 §5.4).

정지 순서가 중요하다: `stop`을 켜고 워커 태스크가 **끝난 뒤에** pool을 닫는다.
반대로 하면 워커가 닫힌 pool에서 커넥션을 얻으려다 터진다. pool 닫기는
`finally`에 두어 워커 종료가 실패해도 커넥션이 남지 않게 한다.

종료 대기에는 상한이 있다(`WORKER_SHUTDOWN_TIMEOUT`). 워커가 Claude 호출
한복판이면 `stop`을 확인할 지점에 도달하지 못하므로, 상한 없이 기다리면 프로세스가
응답 없이 매달린다 — Ctrl+C도 먹지 않는 것처럼 보인다.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.daily import router as daily_router
from app.api.results import router as results_router
from app.api.shadowing import router as shadowing_router
from app.api.videos import router as videos_router
from app.api.vocab import router as vocab_router
from app.api.ws import router as ws_router
from app.config import get_settings
from app.db import close_pool, pool
from app.services.usage import pool_usage_sink
from app.workers.analysis_worker import run_worker
from app.workers.claude_client import BedrockClaudeClient

logger = logging.getLogger(__name__)

# 설계 발명값 (근거 문서 없음) — 워커 종료 대기 상한. "정상적인 한 사이클(Claude 1회
# 호출)은 끝낼 수 있지만 사람이 종료를 기다려줄 수 있는 시간"으로 정했다. 상한을
# 넘기면 취소하며, 취소된 job은 `running`으로 남아 lease 만료 후 회수된다(§5.4) —
# 그래서 취소가 데이터를 잃지 않는다.
WORKER_SHUTDOWN_TIMEOUT = 15.0

# Next.js 개발 서버의 origin. 브라우저는 다른 origin의 fetch 응답을 CORS 헤더 없이
# 스크립트에 넘기지 않으므로, 이 헤더가 없으면 결과 폴링(`GET /api/sessions/...`)이
# 프론트엔드에서 통째로 막힌다. 단일 사용자 로컬 도구라 origin은 이 하나로 충분하고,
# 와일드카드를 쓰지 않는 이유도 그것이다 — 허용 범위를 넓힐 이유가 없다.
FRONTEND_ORIGIN = "http://localhost:3000"


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    app.state.db_pool = await pool()
    app.state.worker_stop = asyncio.Event()
    # 꺼진 경우 태스크를 아예 만들지 않는다 — None이 "워커 없음"의 표현이다.
    app.state.worker_task = None

    # ⛔ **`worker_enabled` 분기 «밖»에서 만든다** (`TASK-194` · 결정 130) — 낱말 뜻 조회가 HTTP
    # 요청 경로에서 이 클라이언트를 쓰므로 `WORKER_ENABLED=false` 로 띄운 서버에서도 있어야 한다.
    # ⚠️ **요청마다 만들지 않는 이유**: `__init__` 이 boto3 `bedrock-runtime` 클라이언트를 만든다.
    # ⛔ **`usage_sink` 를 빼면 토큰 기록이 조용히 꺼진다** (`TASK-60` · 결정 66) — 클라이언트의
    # 기본값이 `None`(기록 없음)인 것은 자격증명·DB 없이 도는 단위 테스트를 위한 것이고,
    # **실물 배선은 여기 하나뿐이다.** 아래 `recording_root` 와 같은 부류의 위험이고 같은 방식으로
    # 게이트 테스트가 못 박는다(`test_claude_client_is_wired_even_when_the_worker_is_off`).
    # ⛔ **자격증명이 없으면 `None` 으로 두고 기동을 막지 않는다** (`TASK-197` 회귀 수정).
    # 그 길은 발명이 아니라 **제품이 스스로 안내하는 것**이다 — `config.py` 의 `RuntimeError` 문구가
    # *"자격증명 없이 백엔드만 띄우려면 WORKER_ENABLED=false로 기동하라"* 고 말한다.
    # ⚠️ 첫 판이 그 안내를 깼고 실측으로 확정했다(`.env` 를 치우고 `AWS_*` 를 모두 지운 셸에서 재현).
    # ⛔ **워커를 켠 경우에는 그대로 터뜨린다** — 그 `RuntimeError` 의 근거가 「이 SDK 는 자격증명
    # 실패를 무응답으로 드러낸다」이고, 삼키면 워커가 원인 불명의 무한 대기에 걸린다.
    # ⚠️ **두 갈래에서 각자 만드는 것이 판단이다** — 한 번 만들고 `None` 검사를 워커 분기에 두면
    # 「워커를 켰는데 클라이언트가 없다」는 닿을 수 없는 상태를 타입이 계속 물어본다. 갈래를 나누면
    # 워커 쪽은 `None` 일 수 없음이 **구조로** 보장된다.
    if settings.worker_enabled:
        # 워커가 돌 것이므로 자격증명이 없으면 **그대로 터뜨린다**(기존 동작).
        claude = BedrockClaudeClient(settings, usage_sink=pool_usage_sink(app.state.db_pool))
        app.state.claude = claude
        app.state.worker_task = asyncio.create_task(
            run_worker(
                app.state.db_pool,
                # 워커와 요청 경로가 **같은 객체를 쓴다** — 둘을 따로 만들면 boto3 클라이언트가
                # 둘이 되고 배선을 고칠 자리도 둘이 된다.
                claude,
                stop=app.state.worker_stop,
                # 집합 **객체 자체**를 넘긴다 — 복사본을 넘기면 세션이 열려도 리퍼에게는
                # 계속 비어 보여 진행 중 세션을 닫는다 (I-4).
                live_sessions=app.state.live_sessions,
                # ⛔ **이 인자를 빼면 쉐도잉 녹음 삭제가 조용히 꺼진다** (`TASK-45` · §6.1).
                # 워커의 기본값이 `None`(스윕 없음)인 것은 녹음 없이 워커만 돌리는 테스트를
                # 위한 것이고, 실물 배선은 여기 하나뿐이다 —
                # `test_lifespan_hands_the_recording_root_to_the_worker` 가 그것을 못 박는다.
                recording_root=settings.shadowing_audio_root,
            )
        )
    else:
        logger.info("WORKER_ENABLED=false — 분석 워커를 기동하지 않는다")
        # ⛔ **이 값은 `config.py` 가 「자격증명 없이 띄우는 길」로 안내하는 것이다** — 그 안내를
        # 지키려면 여기서만 실패를 삼킨다. 낱말 조회 경로는 `None` 을 받아 503 으로 답한다.
        try:
            app.state.claude = BedrockClaudeClient(
                settings, usage_sink=pool_usage_sink(app.state.db_pool)
            )
        except RuntimeError:
            logger.warning(
                "Bedrock 자격증명이 없어 낱말 뜻 조회를 끈 채 기동한다 — 그 경로는 503 으로 답한다"
            )
            app.state.claude = None

    try:
        yield
    finally:
        app.state.worker_stop.set()
        try:
            task = app.state.worker_task
            if task is not None:
                try:
                    await asyncio.wait_for(task, timeout=WORKER_SHUTDOWN_TIMEOUT)
                except TimeoutError:
                    logger.warning(
                        "분석 워커가 %.0f초 안에 멈추지 않아 취소한다 — 진행 중이던 "
                        "job은 lease 만료 후 회수된다",
                        WORKER_SHUTDOWN_TIMEOUT,
                    )
                    # `wait_for`가 이미 취소를 시작했다 — 멱등하게 한 번 더 요청하고
                    # 취소가 끝나는 것만 확인한다.
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
        finally:
            await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="OhMyEnglish API", lifespan=lifespan)
    # 살아있는 WebSocket이 소유한 세션 id들 — `api/ws.py`가 채우고 비우며, 분석 워커의
    # 고아 세션 리퍼가 읽는다(I-4). **lifespan이 아니라 여기서 만드는 이유**: 닫을 자원이
    # 아니라 앱과 수명이 같은 상태이고, lifespan을 열지 않고 라우터만 쓰는 호출자에게도
    # 있어야 한다 — 없으면 첫 연결이 AttributeError로 죽는다.
    app.state.live_sessions = set[UUID]()
    # WebSocket에는 CORS가 적용되지 않는다(브라우저가 preflight를 보내지 않는다) —
    # 이 미들웨어는 HTTP 라우터만을 위한 것이다.
    # ⚠️ **`GET` 만 허용했던 이전 판을 `TASK-165` 가 넓혔다.** 그때는 HTTP 표면이 조회뿐이라 맞는
    # 값이었으나 영상 학습이 첫 쓰기 REST(`/api/videos`)를 들여왔다.
    # ⛔ **이 한 줄을 빼먹으면 테스트는 전부 통과하고 브라우저에서만 담기·지우기가 막힌다** —
    # `api_client` 는 ASGI 로 직접 붙어 preflight 를 거치지 않는다. 그래서
    # `tests/integration/test_videos_api.py` 가 preflight 를 **직접 보내** 이 값을 잰다.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[FRONTEND_ORIGIN],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )
    app.include_router(results_router)
    app.include_router(daily_router)
    # 클립 오디오는 세션에 매이지 않은 제품 자산이라 `/api/shadowing` 을 따로 쓴다(`TASK-66`).
    app.include_router(shadowing_router)
    # 담아 둔 영상과 그 영상에서 담은 문장 (`TASK-165` · 결정 125·126).
    app.include_router(videos_router)
    app.include_router(vocab_router)
    app.include_router(ws_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
