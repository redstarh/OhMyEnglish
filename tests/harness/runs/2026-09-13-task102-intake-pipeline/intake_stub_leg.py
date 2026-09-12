#!/usr/bin/env python
"""무대 정하기 진입의 **앱 경로** 구간만 켠다 — 스텁 어댑터로 세션을 열고 끝낸다.

`TASK-102.1` AC#1 의 앞 절반이다. 재는 것 셋:

1. `?mode=scenario_intake` 로 붙으면 `session_started` 가 온다(세션이 열린다).
2. 세션 행의 `mode` 가 `scenario_intake` 로 **적힌다** — 종료 경로가 그 값으로 job 을 건다.
3. 종료 뒤 `analysis_jobs` 에 `generate_scenario` 가 걸린다.

⛔ **실물 Nova 를 지나가지 않는다** — 어댑터는 스텁이다. 「다섯을 하나씩 묻는가」는 문면의 유도력
이고 이 스크립트가 재는 것이 아니다(`TASK-102.1` AC#2 가 그 회차를 갖는다).

⛔ **공유 dev DB·`:8002` 를 쓰지 않는다**(`H-BC`). 호출자가 검증 전용 DB 와 포트를 세우고
`--url`·`--dsn` 으로 준다 — 기본값을 두지 않는 이유는 그것을 빠뜨린 실행이 dev DB 에 세션을
남기기 때문이다.

⚠️ **`WORKER_ENABLED=false` 로 띄운 백엔드를 전제한다**(`H-AT`). 워커가 살아 있으면 job 이 이
스크립트가 보기 전에 처리되고, 더 나쁘게는 큐가 빈 뒤 보존 세션에 job 을 새로 만든다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

import asyncpg
from websockets.asyncio.client import connect


async def run(url: str, dsn: str, timeout: float) -> int:
    query = "mode=scenario_intake&source=additional"
    session_id: str | None = None
    frames: list[str] = []

    async with connect(f"{url}?{query}") as socket:
        raw = await asyncio.wait_for(socket.recv(), timeout=timeout)
        first = json.loads(raw)
        frames.append(str(first.get("type")))
        if first.get("type") != "session_started":
            print(f"⛔ 첫 프레임이 session_started 가 아니다: {first!r}", file=sys.stderr)
            return 2
        session_id = str(first["session_id"])
        print(f"session_started: {session_id}")

        await socket.send(json.dumps({"type": "end_session"}))
        # `session_ended` 까지 받는다 — 종료 경로(job 등록)가 그 프레임 «전»에 돈다.
        while True:
            try:
                raw = await asyncio.wait_for(socket.recv(), timeout=timeout)
            except TimeoutError:  # `asyncio.TimeoutError` 는 3.11 부터 이것의 별칭이다
                print(
                    "⛔ session_ended 를 못 받았다 — 종료 경로가 끝났는지 알 수 없다",
                    file=sys.stderr,
                )
                return 3
            event = json.loads(raw)
            frames.append(str(event.get("type")))
            if event.get("type") in ("session_ended", "session_failed"):
                break

    print(f"프레임: {' → '.join(frames)}")

    conn = await asyncpg.connect(dsn=dsn)
    try:
        mode = await conn.fetchval("select mode from learning_sessions where id = $1", session_id)
        jobs = await conn.fetch(
            "select job_type, status from analysis_jobs where session_id = $1 order by job_type",
            session_id,
        )
    finally:
        await conn.close()

    print(f"세션 행의 mode: {mode!r}")
    print(f"job: {[(r['job_type'], r['status']) for r in jobs]}")

    failures = []
    if mode != "scenario_intake":
        failures.append(f"세션 행의 mode 가 {mode!r} 다 — 종료 경로가 job 을 못 건다")
    if not any(r["job_type"] == "generate_scenario" for r in jobs):
        failures.append("generate_scenario job 이 걸리지 않았다")
    for line in failures:
        print(f"⛔ {line}", file=sys.stderr)
    if failures:
        return 4
    print(f"OK — session_id={session_id}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="예: ws://127.0.0.1:8022/ws/session")
    parser.add_argument("--dsn", required=True, help="검증 전용 DB DSN")
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()
    return asyncio.run(run(args.url, args.dsn, args.timeout))


if __name__ == "__main__":
    raise SystemExit(main())
