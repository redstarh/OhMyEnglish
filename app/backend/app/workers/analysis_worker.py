"""분석 워커 — asyncio 단일 루프, 동시성 1 (설계서 §5.4).

FastAPI 기동과 함께 뜨는 하나의 태스크가 `claim_next` → (job 종류로 분기)
`process_analysis`/`process_plan`을 반복한다. **동시성을 1로 고정한 것은 설계
결정이다** — 단일 사용자 로컬 도구라
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
from collections.abc import Collection
from pathlib import Path
from uuid import UUID

import asyncpg

from app.services.analysis import process_analysis
from app.services.jobs import JOB_TYPE_PLAN, ClaimedJob, claim_next
from app.services.plan import process_plan
from app.services.recordings import purge_expired_recordings, sweep_orphan_recording_files
from app.services.sessions import ORPHAN_IDLE_GRACE, reap_orphan_sessions
from app.services.utterances import flush_ended_sessions
from app.workers.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


async def reap_orphans(pool: asyncpg.Pool, *, live_sessions: Collection[UUID]) -> list[UUID]:
    """죽은 프로세스가 남긴 `active` 고아 세션을 `failed`로 닫는다 (I-4 회복 1단).

    **스윕보다 먼저 부른다.** 리퍼가 닫은 세션은 곧바로 `flush_ended_sessions`의 대상이
    되므로 같은 유휴 사이클에서 회복이 끝난다 — 순서가 뒤집히면 회복이 이유 없이 한 주기
    늦어진다. 규칙(무엇이 고아인가·왜 live 가드가 필요한가)은 `services/sessions.py`가
    소유한다. 리퍼도 스윕과 같은 이유로 **큐가 빌 때만** 돈다.
    """
    async with pool.acquire() as conn:
        return await reap_orphan_sessions(conn, live_session_ids=live_sessions)


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


async def sweep_recordings(pool: asyncpg.Pool, root: Path) -> tuple[int, int]:
    """만료된 쉐도잉 녹음을 걷는다 — 유휴 사이클의 **세 번째 회복 항목** (`TASK-45` · §6.1).

    ⛔ **새 job 종류도 새 프로세스도 새 크론도 만들지 않는다.** `analysis_jobs` 에 종류를 더하려면
    `analysis_jobs_target_matches_job_type` CHECK 를 DROP → ADD 해야 하고(그 CHECK 가 job 종류를
    전수 열거한다) 그것이 `data-first` 가 말하는 가장 위험한 형태다. 게다가 그 표에는 `user_id` 가
    없어 **사용자·날짜 단위**인 삭제를 담을 자리가 없다. 그래서 `reap_orphans`·`sweep_lost_runs` 와
    같은 자리에 붙는다.

    **두 다리를 이 순서로 부른다** (§6.2): 1다리가 포인터를 비우고 바이트를 지우고, 2다리가
    포인터 없는 파일을 걷는다. 1다리의 unlink 실패가 2다리의 대상이 되므로 **같은 사이클에서
    회복이 끝난다** — 리퍼를 스윕보다 먼저 부르는 것과 같은 이유다.

    규칙(무엇이 만료인가 · 무엇이 고아인가)은 `services/recordings.py` 가 소유한다. 큐가 빌
    때만 부르는 것도 다른 두 회복과 같다.
    """
    async with pool.acquire() as conn:
        purged = await purge_expired_recordings(conn, root)
        removed = await sweep_orphan_recording_files(conn, root)
    return len(purged), removed


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
    live_sessions: Collection[UUID] = (),
    recording_root: Path | None = None,
) -> None:
    """`stop`이 켜질 때까지 job을 하나씩 처리한다 — `analyze_utterance`는
    `process_analysis`로, `plan_next_session`은 `process_plan`으로 보낸다(Task 3).

    `live_sessions`는 **살아있는 WebSocket이 소유한 세션 id 집합**이다 — 루프는 읽기만
    하고, 채우고 비우는 것은 `api/ws.py`다. 고아 세션 리퍼(I-4)가 진행 중인 세션을 닫지
    않는 근거가 이 집합이므로 **호출자는 반드시 살아있는 집합 객체 자체를 넘긴다**(그 순간의
    복사본을 넘기면 세션이 열려도 리퍼에게는 계속 비어 보인다). 기본값이 빈 튜플인 것은
    리퍼 없이 워커만 돌리는 테스트를 위한 것이다.

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
                # 큐가 비었다 — 먼저 죽은 프로세스가 남긴 고아 세션을 닫고(I-4), 그
                # 다음에 잃어버린 묶음을 걷는다(I-1). 이 순서라서 리퍼가 방금 닫은
                # 세션의 묶음이 같은 사이클에 걷힌다. 걷은 것이 있으면 곧바로 다음
                # claim으로 가서 그 job을 처리한다.
                # 리퍼 고유의 실패가 **I-1 스윕을 막지 않게** 따로 감싼다. 이 두 회복 경로는
                # 독립이고, 직렬로 묶으면 리퍼가 계속 실패하는 동안 잃어버린 묶음이 영구히
                # 걷히지 않는다 — `utterances.flush_ended_sessions`가 말하는 terminal
                # "분석 대상 없음"이 그 결과다. 아래 루프 레벨 `except`는 사이클을 통째로
                # 건너뛰므로 여기서 대신 잡을 수 없다.
                try:
                    reaped = await reap_orphans(pool, live_sessions=live_sessions)
                except Exception:
                    logger.exception("고아 세션 리퍼가 실패했다 — 스윕은 그대로 진행한다 (I-4)")
                    reaped = []
                if reaped:
                    # **WARNING이다 — INFO로 내리지 마라.** 리퍼가 걷었다는 것은 이전
                    # 프로세스가 세션 도중에 죽었다는 뜻이고, 정상 운영에서는 나오지 않는다.
                    # 게다가 문서가 지정한 실행 명령(`docs/ops/local-run.md`:
                    # `.venv/bin/uvicorn app.api.main:app --port 8002`)은 root 로거에 핸들러를
                    # 두지 않아 `logging.lastResort`가 **WARNING 이상만** 흘린다 — INFO면 이
                    # 줄이 실물에서 아예 보이지 않는다(2026-09-03 실측: 같은 실행에서 INFO
                    # "analysis worker started"는 0건, WARNING "텍스트가 아닌 프레임"은 출력됨).
                    logger.warning(
                        "마지막 발화 후 %.0f초 넘게 조용했던 `active` 세션 %d건을 "
                        "failed로 닫았다 (I-4): %s",
                        ORPHAN_IDLE_GRACE.total_seconds(),
                        len(reaped),
                        [str(session_id) for session_id in reaped],
                    )
                # 쉐도잉 녹음 스윕도 **따로 감싼다** — 위 두 회복과 같은 이유다(한 `try` 로
                # 묶으면 이 스윕이 계속 실패하는 동안 다른 회복이 영구히 막힌다).
                # `recording_root` 가 없으면 저장 기능을 배선하지 않은 실행이므로 조용히 건너뛴다.
                if recording_root is not None:
                    try:
                        purged, removed = await sweep_recordings(pool, recording_root)
                    except Exception:
                        logger.exception(
                            "쉐도잉 녹음 스윕이 실패했다 — 다른 회복은 그대로 진행한다 "
                            "(다음 유휴 사이클이 같은 조건을 다시 계산한다)"
                        )
                    else:
                        if purged or removed:
                            # **INFO 다** — 정상 운영에서 매일 나오는 일이고, 실패는 위
                            # `exception`(ERROR)과 서비스의 `WARNING` 으로 보인다(§6.3).
                            logger.info(
                                "쉐도잉 녹음 스윕: 만료 %d건을 접근 불가로 만들고 "
                                "고아 파일 %d건을 지웠다",
                                purged,
                                removed,
                            )
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
            if job.job_type == JOB_TYPE_PLAN:
                await process_plan(pool, claude, job)
            else:
                await process_analysis(pool, claude, job)
        except Exception:
            # 여기까지 오는 것은 큐/DB 자체의 장애다 — `process_analysis`·`process_plan`
            # 둘 다 자기 job의 실패를 큐에 보고하고 예외를 올리지 않는다. 루프를
            # 살려두고 다음 주기에 다시 시도한다.
            logger.exception("analysis worker cycle failed — retrying after the poll interval")
            await _wait(stop, poll_interval)
    logger.info("analysis worker stopped")
