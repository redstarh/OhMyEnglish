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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.results import router as results_router
from app.api.ws import router as ws_router
from app.config import get_settings
from app.db import close_pool, pool
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

    if settings.worker_enabled:
        app.state.worker_task = asyncio.create_task(
            run_worker(
                app.state.db_pool,
                BedrockClaudeClient(settings),
                stop=app.state.worker_stop,
            )
        )
    else:
        logger.info("WORKER_ENABLED=false — 분석 워커를 기동하지 않는다")

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
    # WebSocket에는 CORS가 적용되지 않는다(브라우저가 preflight를 보내지 않는다) —
    # 이 미들웨어는 결과 조회 같은 HTTP GET만을 위한 것이라 methods를 GET으로 좁힌다.
    app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN], allow_methods=["GET"])
    app.include_router(results_router)
    app.include_router(ws_router)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
