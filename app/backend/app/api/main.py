"""FastAPI application factory + lifespan (DB pool·분석 워커 기동/정지).

워커를 별도 프로세스가 아니라 API의 lifespan에 붙인다 — 단일 사용자 로컬
도구에서 프로세스를 하나 더 운영할 이유가 없고, job이 테이블에 남으므로
프로세스가 죽어도 재기동 후 이어진다 (설계서 §5.4).

정지 순서가 중요하다: `stop`을 켜고 워커 태스크가 **끝난 뒤에** pool을 닫는다.
반대로 하면 워커가 닫힌 pool에서 커넥션을 얻으려다 터진다. pool 닫기는
`finally`에 두어 워커 종료가 실패해도 커넥션이 남지 않게 한다.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.config import get_settings
from app.db import close_pool, pool
from app.workers.analysis_worker import run_worker
from app.workers.claude_client import BedrockClaudeClient

logger = logging.getLogger(__name__)


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
            if app.state.worker_task is not None:
                await app.state.worker_task
        finally:
            await close_pool()


def create_app() -> FastAPI:
    app = FastAPI(title="OhMyEnglish API", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
