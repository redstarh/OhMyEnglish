"""분석 워커 — asyncio 단일 루프, 동시성 1 (설계서 §5.4).

FastAPI 기동과 함께 뜨는 하나의 태스크가 `claim_next` → `process_analysis`를
반복한다. **동시성을 1로 고정한 것은 설계 결정이다** — 단일 사용자 로컬 도구라
병렬 처리 이유가 없고, `for update skip locked`·lease token 같은 잠금 규칙은
병렬 처리량이 아니라 재기동·이중 기동 방어를 위한 것이다.

루프가 지키는 세 가지:

* **claim은 자기 짧은 트랜잭션에서 한다** (jobs.py 호출 계약). Claude 호출까지
  한 트랜잭션으로 묶으면 그 시간 내내 잠금과 스냅샷을 붙든다.
* **대기는 `stop`을 기다리는 대기다.** `asyncio.sleep(poll_interval)`로 자면
  종료가 최대 한 주기만큼 늦어진다 — 프로세스 종료가 그만큼 매달린다.
* **한 사이클의 실패가 루프를 죽이지 않는다.** 워커가 조용히 사라지면 그
  세션의 job은 lease 만료까지 `running`에 남고, 결과 화면은 "분석 중"에
  고정된다(§5.5). 예외는 로그로 남기고 다음 주기에 다시 시도한다.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from uuid import UUID

import asyncpg

from app.services.analysis import process_analysis
from app.services.jobs import ClaimedJob, claim_next
from app.services.utterances import flush_ended_sessions
from app.workers.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


async def sweep_lost_runs(pool: asyncpg.Pool) -> list[UUID]:
    """끝난 세션에서 job이 없는 사용자 발화 묶음을 걷어 등록한다 (I-1 회복 경로).

    분석 job은 턴 경계와 세션 종료 때 걸린다(`audio_gateway/session.py`). 그 종료 쪽
    flush가 실패하거나 그 전에 프로세스가 죽으면 그 묶음을 다시 걸어줄 사람이 없고,
    결과 화면은 **terminal** 상태 `no_utterances`("분석 대상 없음")에 고정된다. 큐
    수명주기의 소유자가 워커이므로 회복도 여기 둔다.

    **큐가 비었을 때만 부른다** — 분석이 밀리는 동안 이력 전체를 훑을 이유가 없고,
    잃은 묶음이 문제가 되는 시점도 "더 할 일이 없을 때"다. 규칙(무엇이 묶음인가,
    어떤 세션이 끝난 것인가)은 `services/utterances.py`가 소유한다.
    """
    async with pool.acquire() as conn:
        return await flush_ended_sessions(conn)


async def claim_one(pool: asyncpg.Pool) -> ClaimedJob | None:
    """claim 하나를 짧은 자기 트랜잭션에서 커밋한다 (§5.4).

    공개 이름이다 — `tests/integration/test_pipeline.py`와
    `scripts/smoke_analysis.py`가 같은 claim 패턴을 재구현하지 않고 이 함수를
    직접 쓴다.
    """
    async with pool.acquire() as conn, conn.transaction():
        return await claim_next(conn)


async def _wait(stop: asyncio.Event, timeout: float) -> None:
    """`stop`이 켜질 때까지, 늦어도 `timeout`까지 기다린다.

    `asyncio.sleep`이 아니라 `stop.wait()`에 타임아웃을 거는 이유: 빈 큐를 보고
    자는 동안 종료 신호가 와도 즉시 깨어나야 한다. 그렇지 않으면 종료가 poll
    주기만큼 지연된다.
    """
    with contextlib.suppress(TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout)


async def run_worker(
    pool: asyncpg.Pool,
    claude: ClaudeClient,
    *,
    stop: asyncio.Event,
    poll_interval: float = 1.0,
    enabled: bool = True,
) -> None:
    """`stop`이 켜질 때까지 `analyze_utterance` job을 하나씩 처리한다.

    `enabled=False`면 아무것도 claim하지 않고 즉시 돌아온다 — `WORKER_ENABLED`를
    그대로 넘기는 호출자(E2E-S 3단계처럼 워커 없이 API만 띄우는 실행)가 루프를
    조건 분기 없이 배선할 수 있게 하는 안전판이다. `create_app()`의 lifespan은
    한 걸음 더 나아가 꺼진 경우 태스크 자체를 만들지 않는다.

    job을 처리한 뒤에는 기다리지 않고 곧바로 다음 claim으로 간다 — 세션 한 번에
    쌓인 발화들이 poll 주기 간격으로 찔끔찔끔 처리되면 결과 화면이 늦어진다.
    """
    if not enabled:
        logger.info("analysis worker is disabled — not claiming any job")
        return

    logger.info("analysis worker started (poll interval %.2fs, concurrency 1)", poll_interval)
    while not stop.is_set():
        try:
            job = await claim_one(pool)
            if job is None:
                # 큐가 비었다 — 잃어버린 묶음이 있으면 지금 걷는다. 걷은 것이
                # 있으면 곧바로 다음 claim으로 가서 그 job을 처리한다.
                recovered = await sweep_lost_runs(pool)
                if recovered:
                    logger.info(
                        "종료 flush를 놓친 발화 묶음 %d건에 분석 job을 걸었다 (I-1 회복): %s",
                        len(recovered),
                        [str(utterance_id) for utterance_id in recovered],
                    )
                    continue
                await _wait(stop, poll_interval)
                continue
            await process_analysis(pool, claude, job)
        except Exception:
            # 여기까지 오는 것은 큐/DB 자체의 장애다(`process_analysis`는 자기
            # 실패를 큐에 보고한다). 루프를 살려두고 다음 주기에 다시 시도한다.
            logger.exception("analysis worker cycle failed — retrying after the poll interval")
            await _wait(stop, poll_interval)
    logger.info("analysis worker stopped")
