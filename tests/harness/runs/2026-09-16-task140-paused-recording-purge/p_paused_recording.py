#!/usr/bin/env python3
"""회차 드라이버 — `TASK-140`: 「진행 중」 판정이 `paused` 를 빠뜨리는가.

앱의 함수를 그대로 부른다(재구현하지 않는다) — `load_recording` 과
`purge_expired_recordings` 가 정본이고, 이 스크립트는 상태 셋을 심고 그 둘의 결과를 읽는다.

⛔ **실물 자산 뿌리를 쓰지 않는다.** 뿌리를 인자로 받으므로 `/tmp` 아래를 준다 —
개인정보 삭제를 재는 회차이므로 실제 녹음 자리를 건드리면 되돌릴 수 없다.

    DATABASE_URL=postgresql://ohmy:ohmy@localhost:5432/ohmyenglish_t140 \
      app/backend/.venv/bin/python <이 파일> /tmp/t140-audio
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "app" / "backend"))

import asyncpg  # noqa: E402

from app.services.recordings import (  # noqa: E402
    day_start_for,
    finalize_recording,
    load_recording,
    pending_recording_path,
    purge_expired_recordings,
    recording_path,
)

KST = ZoneInfo("Asia/Seoul")
FRAMES = b"\x00\x01" * 160
# 심는 상태 셋. `paused` 가 물음이고 나머지 둘이 대조다 — `active` 는 살아야 하고
# `completed` 는 지워져야 한다(그것이 §5.4 가 정한 계약이다).
ARMS = ("paused", "active", "completed")


async def _seed(conn: asyncpg.Connection, root: Path, status: str, created_at: datetime):
    user_id = await conn.fetchval(
        "insert into users (display_name, timezone) values ($1, 'Asia/Seoul') returning id",
        f"T140 {status}",
    )
    session_id = await conn.fetchval(
        "insert into learning_sessions (user_id, mode, status) values ($1, 'shadowing', $2) "
        "returning id",
        user_id,
        status,
    )
    utterance_id = await conn.fetchval(
        "insert into utterances "
        "(session_id, speaker, utterance_type, transcript, sequence_no, created_at) "
        "values ($1, 'user', 'shadowing_recording', 'I usually wake up at seven.', 1, $2) "
        "returning id",
        session_id,
        created_at,
    )
    pending = pending_recording_path(root, session_id, uuid4())
    pending.parent.mkdir(parents=True, exist_ok=True)
    pending.write_bytes(FRAMES)
    # 앱의 완성 경로를 그대로 탄다 — 파일을 옮기고 그 뒤에 포인터를 쓴다.
    await finalize_recording(
        conn,
        root,
        session_id=session_id,
        turn_id=UUID(pending.name.removesuffix(".pcm.part")),
        utterance_id=utterance_id,
    )
    return session_id, utterance_id


async def main() -> None:
    root = Path(sys.argv[1]).resolve()
    root.mkdir(parents=True, exist_ok=True)
    conn = await asyncpg.connect(dsn=os.environ["DATABASE_URL"])
    try:
        now = datetime.now(KST)
        boundary = day_start_for("Asia/Seoul", now=now)
        # 학습자의 「오늘」이 시작하기 전에 만든 녹음이어야 만료 판정을 탄다.
        created_at = boundary - timedelta(hours=2)
        print(f"now={now.isoformat()} 경계={boundary.isoformat()} 녹음시각={created_at.isoformat()}")

        seeded = {}
        for status in ARMS:
            seeded[status] = await _seed(conn, root, status, created_at)

        print("\n[1] 스윕 전 — load_recording")
        for status, (session_id, utterance_id) in seeded.items():
            got = await load_recording(conn, root, session_id, utterance_id)
            print(f"  {status:<9} load_recording={'바이트 ' + str(len(got)) if got else 'None'}")

        purged = await purge_expired_recordings(conn, root)
        print(f"\n[2] purge_expired_recordings → {len(purged)}건")

        print("\n[3] 스윕 뒤 — 포인터와 파일")
        for status, (session_id, utterance_id) in seeded.items():
            url = await conn.fetchval("select audio_url from utterances where id = $1", utterance_id)
            path = recording_path(root, session_id, utterance_id)
            print(
                f"  {status:<9} 선택됨={utterance_id in purged!s:<5} "
                f"audio_url={'있음' if url else 'null'} 파일={'있음' if path.is_file() else '없음'}"
            )
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
