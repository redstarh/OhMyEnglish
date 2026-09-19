#!/usr/bin/env python3
"""TS-33 AC#3 보조 다리 — 화면 「학습 종료」 버튼이 보내는 프레임을 그대로 보내 종료 경로를 견준다.

⛔ 앱 코드를 고치지 않는다. `tests/harness/ws_session.py` 는 `end_session` 을 보내지 않으므로
이 20줄이 그 한 프레임만 보낸다(`lib/ws.ts:SessionSocket.endSession` 이 보내는 것과 같은 페이로드).

견주는 대상: 음성 `end`(`confirmed`) 다리가 남긴 세션 상태와 이 다리가 남긴 상태.
"""

from __future__ import annotations

import asyncio
import json
import sys

from websockets.asyncio.client import connect

URL = "ws://localhost:8002/ws/session"


async def main() -> int:
    frames: list[dict] = []
    session_id = None
    async with connect(URL, max_size=None) as ws:
        # `session_started` 를 먼저 받아 세션 id 를 잡는다 — 그 뒤에 버튼 프레임을 보낸다.
        first = json.loads(await asyncio.wait_for(ws.recv(), 10))
        frames.append(first)
        session_id = first.get("session_id")
        await ws.send(json.dumps({"type": "end_session"}))
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), 15)
            except (TimeoutError, Exception):
                break
            event = json.loads(raw)
            frames.append({"type": event.get("type"), "reason": event.get("reason")})
            if event.get("type") in ("session_ended", "session_failed"):
                break
    print(f"session_id = {session_id}")
    print("order      = " + " ".join(f.get("type") or "?" for f in frames))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
