#!/usr/bin/env python3
"""B4 회차 드라이버 5 — TS-35 AC#4. `?mode=scenario_intake` 진입이 성립하는지 실제 소켓으로 잰다.

⚠️ **이 다리만 공유 픽스처 사용자(`FIXED_USER_ID`)를 쓴다** — 소켓이 그 id 를 박아 넣으므로
   격리할 수 없다. 그래서 ⑴ 앞뒤로 그 사용자의 세션 id 집합을 떠서 ⑵ 내가 만든 세션 1행만
   지우고 ⑶ 집합이 원래대로 돌아온 것을 **읽어** 확인한다.
⛔ 워커를 켜지 않는다 — 종료가 거는 job 은 pending 으로 남고, 내 세션을 지울 때 cascade 로 걷힌다.

판정 근거 셋: ⑴ `session_started` 프레임이 온다 ⑵ 세션 행의 `mode` 가 `scenario_intake` 다
⑶ 종료가 그 모드를 읽어 `generate_scenario` job 을 건다(설계서 §5 흐름 3).
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from uuid import UUID

import asyncpg
from websockets.asyncio.client import connect

BACKEND = Path("/Users/redstar/MyProject/OhMyEnglish/app/backend")
sys.path.insert(0, str(BACKEND))

USER = UUID("00000000-0000-0000-0000-000000000001")
URL = "ws://localhost:8002/ws/session?mode=scenario_intake"
LISTEN_SECONDS = 12.0
OUT: dict[str, object] = {}


def dsn() -> str:
    for line in (BACKEND / ".env").read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL not found")


async def session_ids(conn: asyncpg.Connection) -> set[UUID]:
    return {
        r["id"]
        for r in await conn.fetch("select id from learning_sessions where user_id=$1", USER)
    }


async def drive() -> tuple[UUID | None, list[dict[str, object]]]:
    frames: list[dict[str, object]] = []
    session_id: UUID | None = None
    async with connect(URL, max_size=None) as ws:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + LISTEN_SECONDS
        while loop.time() < deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=deadline - loop.time())
            except (TimeoutError, asyncio.TimeoutError):
                break
            event = json.loads(raw)
            frames.append(
                {k: v for k, v in event.items() if k not in {"data", "audio"}}
            )
            if event.get("type") == "session_started":
                session_id = UUID(event["session_id"])
            if len(frames) >= 12:
                break
        await ws.send(json.dumps({"type": "end_session"}))
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=8.0)
            frames.append({k: v for k, v in json.loads(raw).items() if k != "data"})
        except Exception as exc:  # 종료 프레임이 없어도 세션 행으로 판정한다
            frames.append({"recv_after_end": type(exc).__name__})
    return session_id, frames


async def main() -> None:
    conn = await asyncpg.connect(dsn())
    try:
        before = await session_ids(conn)
        OUT["fixture_sessions_before"] = len(before)

        session_id, frames = await drive()
        OUT["frame_types"] = [f.get("type", list(f)[0]) for f in frames]
        OUT["session_started_received"] = any(f.get("type") == "session_started" for f in frames)
        OUT["session_id"] = str(session_id)

        await asyncio.sleep(2.0)  # 종료 경로가 커밋을 끝낼 시간
        row = await conn.fetchrow(
            "select mode, status, scenario_id, drill_turns_expected "
            "from learning_sessions where id=$1",
            session_id,
        )
        OUT["session_row"] = None if row is None else {k: str(v) for k, v in dict(row).items()}
        OUT["mode_recorded_as_intake"] = row is not None and row["mode"] == "scenario_intake"

        jobs_rows = [
            dict(r)
            for r in await conn.fetch(
                "select job_type, status from analysis_jobs where session_id=$1 order by job_type",
                session_id,
            )
        ]
        OUT["jobs_after_end"] = [{k: str(v) for k, v in j.items()} for j in jobs_rows]
        OUT["generate_scenario_job_enqueued"] = any(
            j["job_type"] == "generate_scenario" for j in jobs_rows
        )
        OUT["utterances_recorded"] = await conn.fetchval(
            "select count(*) from utterances where session_id=$1", session_id
        )

        # 되돌리기 — 내가 만든 세션 1행만 지우고 집합이 원래대로인지 읽어 확인한다.
        if session_id is not None:
            await conn.execute("delete from learning_sessions where id=$1", session_id)
        after = await session_ids(conn)
        OUT["fixture_sessions_after_cleanup"] = len(after)
        OUT["session_set_restored"] = after == before
    finally:
        await conn.close()
    print(json.dumps(OUT, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
