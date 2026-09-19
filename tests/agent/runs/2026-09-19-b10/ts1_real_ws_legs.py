#!/usr/bin/env python3
"""TS-1 AC#3 레그 1 — **실물 배선**(`ws://localhost:8002/ws/session`)에서 `session_ended` 를 관측한다.

⛔ 앱 코드를 고치지 않는다. 어댑터는 서버의 `VOICE_ADAPTER=stub` 이 정하므로 이 드라이버가
바꿀 수 없다 — 그것이 아래 두 팔을 나눈 이유다.

**두 팔을 견주는 목적은 「프레임의 도착」과 「종료의 원인」을 갈라 내는 것이다.**

- 팔 `R1_client_end`: 연결 직후 아무것도 읽기 전에 `probe` 와 `end_session` 을 **파이프라인으로**
  밀어 넣는다. 서버의 클라이언트 펌프가 내 메시지를 실제로 읽었는지는 `probe` 의 nonce 가
  백엔드 로그의 `알 수 없는 클라이언트 메시지` 경고로 남는지로 가린다
  (`audio_gateway/session.py:749` · 백엔드가 `--log-level warning` 이라 이 경고는 파일에 남는다).
- 팔 `R2_no_end`: 아무것도 보내지 않고 매달려 있는다. 스텁 픽스처가 스스로 소진되어 세션이 닫힌다.

⚠️ **`R2` 에서도 `session_ended` 가 온다면, 프레임의 존재만으로는 AC#3 의 「`end_session` 후」를
증명하지 못한다** — 그 반증이 이 팔의 값어치다(§7-9). 인과는 레그 2 가 가른다.

기록: 프레임마다 (경과 ms · type · session_id) · 세션 ID · 종료 프레임의 적재 여부.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from pathlib import Path

from websockets.asyncio.client import connect

URL = "ws://localhost:8002/ws/session"


async def run_arm(name: str, *, send_end: bool, timeout: float) -> dict[str, object]:
    nonce = f"ts1-probe-{uuid.uuid4().hex[:12]}"
    frames: list[dict[str, object]] = []
    started_at = time.monotonic()
    sent: list[dict[str, object]] = []

    async with connect(URL, max_size=None) as socket:
        if send_end:
            # ⛔ **읽기 전에 보낸다.** 스텁은 픽스처를 수십 ms 에 소진하므로, 프레임을 하나라도
            # 읽고 나서 보내면 세션은 이미 닫혀 있다(2026-09-09 회차가 그것으로 막혔다).
            await socket.send(json.dumps({"type": nonce}))
            sent.append({"at_ms": round((time.monotonic() - started_at) * 1000, 1), "type": nonce})
            await socket.send(json.dumps({"type": "end_session"}))
            sent.append(
                {"at_ms": round((time.monotonic() - started_at) * 1000, 1), "type": "end_session"}
            )
        deadline = started_at + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                frames.append({"at_ms": None, "type": "__driver_timeout__"})
                break
            try:
                raw = await asyncio.wait_for(socket.recv(), remaining)
            except asyncio.TimeoutError:
                frames.append({"at_ms": None, "type": "__driver_timeout__"})
                break
            except Exception as exc:  # 소켓이 닫혔다 — 정상 종료 경로다
                frames.append(
                    {
                        "at_ms": round((time.monotonic() - started_at) * 1000, 1),
                        "type": "__socket_closed__",
                        "detail": type(exc).__name__,
                    }
                )
                break
            event = json.loads(raw)
            record: dict[str, object] = {
                "at_ms": round((time.monotonic() - started_at) * 1000, 1),
                "type": event.get("type"),
                "keys": sorted(event.keys()),
            }
            if "session_id" in event:
                record["session_id"] = event["session_id"]
            if event.get("type") == "transcript":
                record["speaker"] = event.get("speaker")
                record["kind"] = event.get("kind")
                record["text"] = event.get("text")
            if event.get("type") == "audio":
                record["data_len"] = len(event.get("data") or "")
            frames.append(record)

    started_ids = [f.get("session_id") for f in frames if f.get("type") == "session_started"]
    ended = [f for f in frames if f.get("type") == "session_ended"]
    return {
        "arm": name,
        "nonce": nonce,
        "sent": sent,
        "frame_count": len(frames),
        "frames": frames,
        "session_id_from_started": started_ids[0] if started_ids else None,
        "session_ended_present": bool(ended),
        "session_ended_frame": ended[0] if ended else None,
        "session_ended_carries_session_id": bool(ended) and "session_id" in ended[0],
        "session_ended_id_matches_started": bool(ended)
        and ended[0].get("session_id") == (started_ids[0] if started_ids else None),
        "last_app_frame": next(
            (
                f.get("type")
                for f in reversed(frames)
                if f.get("type") not in {"__socket_closed__", "__driver_timeout__"}
            ),
            None,
        ),
        "total_ms": frames[-1].get("at_ms") if frames else None,
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=float, default=20.0)
    args = parser.parse_args()

    results = [
        await run_arm("R1_client_end", send_end=True, timeout=args.timeout),
        await run_arm("R2_no_end", send_end=False, timeout=args.timeout),
    ]
    payload = {"url": URL, "arms": results}
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for arm in results:
        print(
            f"{arm['arm']}: frames={arm['frame_count']} session={arm['session_id_from_started']} "
            f"ended={arm['session_ended_present']} carries_id={arm['session_ended_carries_session_id']} "
            f"matches={arm['session_ended_id_matches_started']} last={arm['last_app_frame']} "
            f"total_ms={arm['total_ms']} nonce={arm['nonce']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
