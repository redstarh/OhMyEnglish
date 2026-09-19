#!/usr/bin/env python3
"""B4 회차 드라이버 2 — TS-31 AC#3. 고아 스윕이 **정지 중** 세션의 `.part` 를 지키는지 잰다.

`TASK-223` 이 고친 자리다. 판정은 파일시스템을 직접 읽어 한다.
⛔ DB 쓰기는 **롤백되는 트랜잭션** 안에서만 하고, 파일은 `/tmp` 아래 내 뿌리에만 만든다.
⚠️ 양성 대조를 함께 둔다 — 끝난 세션의 `.part` 는 **지워져야** 한다. 그것이 지워지지 않으면
   이 계측은 「아무것도 지우지 않는 스윕」과 구별되지 않는다(§7-7).
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg

BACKEND = Path("/Users/redstar/MyProject/OhMyEnglish/app/backend")
sys.path.insert(0, str(BACKEND))

from app.services.recordings import sweep_orphan_recording_files  # noqa: E402
from app.services.sessions import LIVE_SESSION_STATUSES  # noqa: E402

MARK = "b4-part-sweep-driver"
OUT: dict[str, object] = {}


class RollbackNow(Exception):
    pass


def dsn() -> str:
    for line in (BACKEND / ".env").read_text().splitlines():
        if line.startswith("DATABASE_URL="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("DATABASE_URL not found")


async def run(conn: asyncpg.Connection, root: Path) -> None:
    uid = await conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ($1, 'Asia/Seoul', 'B1') returning id",
        MARK,
    )
    sessions: dict[str, UUID] = {}
    for status in ("active", "paused", "completed"):
        sid = await conn.fetchval(
            "insert into learning_sessions (user_id, mode, status, ended_at) "
            "values ($1, 'shadowing', $2, case when $2 = 'completed' then now() end) returning id",
            uid,
            status,
        )
        sessions[status] = sid
        session_dir = root / str(sid)
        session_dir.mkdir(parents=True)
        (session_dir / f"{uuid4()}.pcm.part").write_bytes(b"\x00" * 16)

    # 양성 대조 둘째 — 끝난 세션의 «포인터 없는» 완성 파일도 고아다.
    orphan_pcm = root / str(sessions["completed"]) / f"{uuid4()}.pcm"
    orphan_pcm.write_bytes(b"\x00" * 16)

    before = {
        status: sorted(p.name[-9:] for p in (root / str(sid)).iterdir())
        for status, sid in sessions.items()
    }
    OUT["live_statuses_const"] = list(LIVE_SESSION_STATUSES)
    OUT["before"] = before

    removed = await sweep_orphan_recording_files(conn, root)
    OUT["removed_count"] = removed

    after = {}
    for status, sid in sessions.items():
        session_dir = root / str(sid)
        after[status] = (
            sorted(p.name[-9:] for p in session_dir.iterdir()) if session_dir.is_dir() else "(지워짐)"
        )
    OUT["after"] = after
    OUT["active_part_survived"] = after["active"] == before["active"]
    OUT["paused_part_survived"] = after["paused"] == before["paused"]
    OUT["ended_orphans_removed"] = after["completed"] == "(지워짐)"
    raise RollbackNow


async def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="b4-recordings-")).resolve()
    conn = await asyncpg.connect(dsn())
    try:
        try:
            async with conn.transaction():
                await run(conn, root)
        except RollbackNow:
            pass
        OUT["db_rows_left"] = await conn.fetchval(
            "select count(*) from users where display_name = $1", MARK
        )
    finally:
        await conn.close()
        shutil.rmtree(root, ignore_errors=True)
        OUT["temp_root_removed"] = not root.exists()
    print(json.dumps(OUT, indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    asyncio.run(main())
