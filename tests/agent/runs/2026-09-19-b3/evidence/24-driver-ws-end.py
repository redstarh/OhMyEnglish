#!/usr/bin/env python3
"""B3 회차 드라이버 — /ws/session 에 붙어 곧바로 end_session 을 보내고 프레임을 전부 기록함.

⛔ 관측력 증명을 위해 프레임을 **하나도 버리지 않고** 적음. 종료 프레임을 놓쳐 「0건」을
보고하는 실패(§7-7)를 막으려고, `end_session` 을 보낸 «뒤에» 소켓이 닫힐 때까지 계속 읽음.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time

from websockets.asyncio.client import connect

URL = sys.argv[1] if len(sys.argv) > 1 else "ws://localhost:8002/ws/session"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/b3_ws_frames.jsonl"
TIMEOUT_S = 30.0


async def main() -> int:
    frames: list[dict[str, object]] = []
    started = time.monotonic()
    async with connect(URL, open_timeout=15) as ws:
        # 시작 프레임을 먼저 받아 세션 id 를 얻음 — 종료 뒤 DB 를 그 id 로 조회함.
        await ws.send(json.dumps({"type": "end_session"}))
        while True:
            remaining = TIMEOUT_S - (time.monotonic() - started)
            if remaining <= 0:
                frames.append({"_driver": "timeout"})
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
            except asyncio.TimeoutError:
                frames.append({"_driver": "timeout"})
                break
            except Exception as exc:  # 닫힘도 관측 대상임
                frames.append({"_driver": "closed", "detail": type(exc).__name__})
                break
            try:
                frames.append(json.loads(raw))
            except json.JSONDecodeError:
                frames.append({"_driver": "non-json", "raw": raw[:200]})

    with open(OUT, "w", encoding="utf-8") as fh:
        for frame in frames:
            fh.write(json.dumps(frame, ensure_ascii=False) + "\n")
    types = [f.get("type") or f.get("_driver") for f in frames]
    print(f"frames={len(frames)} types={types}")
    for frame in frames:
        if frame.get("type") in ("session_started", "session_ended", "session_failed"):
            print(json.dumps(frame, ensure_ascii=False)[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
