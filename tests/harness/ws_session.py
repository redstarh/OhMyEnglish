#!/usr/bin/env python3
"""하네스 WS 클라이언트 — /ws/session 한 세션을 끝까지 관측하고 프레임을 기록한다.

사용:
    .venv/bin/python ../../.harness/ws_session.py --scenario A1
    .venv/bin/python ../../.harness/ws_session.py --scenario A2 --junk
    .venv/bin/python ../../.harness/ws_session.py --scenario B5 --timeout 15
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import time
from pathlib import Path

# psql_cli — DATABASE_URL을 따라가는 psql 헬퍼 (:5432 기본, :5433 폴백). 이전에는 이 파일이
# `podman exec`를 하드코딩해 폴백 컨테이너의 사본에 하네스 세션을 등록했다 — 함정 H-T.
from psql_cli import psql
from websockets.asyncio.client import connect

HARNESS = Path(__file__).resolve().parent.parent.parent / ".harness"
RUN_ID = (HARNESS / "run_id.txt").read_text().strip()
URL = "ws://localhost:8002/ws/session"

JUNK_FRAMES = [
    ('{"type":"audio","data":"한글"}', "non-ascii base64"),
    ('{"type":"audio","data":"!!!!"}', "invalid base64 alphabet"),
    ('{"type":"무엇"}', "unknown type"),
    ("not-json-at-all", "unparseable text"),
]


def register(session_id: str, scenario: str) -> None:
    psql(
        "insert into harness_sessions (run_id, session_id, scenario) "
        f"values ('{RUN_ID}', '{session_id}', '{scenario}') on conflict do nothing"
    )


async def run(scenario: str, junk: bool, timeout: float, send_audio: int) -> dict:
    frames: list[dict] = []
    started = time.monotonic()
    session_id = None
    async with connect(URL, max_size=None) as ws:
        if junk:
            for payload, _label in JUNK_FRAMES:
                await ws.send(payload)
            await ws.send(b"\x00\x01\x02\x03")  # binary frame
        for _ in range(send_audio):
            await ws.send(json.dumps({"type": "audio", "data": base64.b64encode(b"\x00" * 320).decode()}))
        while True:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                frames.append({"_harness": "timeout"})
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), remaining)
            except (asyncio.TimeoutError, TimeoutError):
                frames.append({"_harness": "timeout"})
                break
            except Exception as exc:  # 소켓 종료
                frames.append({"_harness": f"closed: {type(exc).__name__}"})
                break
            event = json.loads(raw)
            elapsed = round(time.monotonic() - started, 3)
            record = {"t": elapsed, "type": event.get("type")}
            if event.get("type") == "session_started":
                session_id = event["session_id"]
                register(session_id, scenario)
                record["session_id"] = session_id
            elif event.get("type") in ("partial", "final"):
                record["speaker"] = event.get("speaker")
                record["text"] = event.get("text")
                if "sequence_no" in event:
                    record["sequence_no"] = event["sequence_no"]
            elif event.get("type") == "audio":
                blob = base64.b64decode(event["data"])
                record["bytes"] = len(blob)
                record["header"] = blob[:4].decode("latin-1") + blob[8:12].decode("latin-1")
            elif event.get("type") == "session_failed":
                record["reason"] = event.get("reason")
            frames.append(record)
            if event.get("type") in ("session_ended", "session_failed"):
                break
    return {
        "scenario": scenario,
        "session_id": session_id,
        "elapsed": round(time.monotonic() - started, 3),
        "junk_sent": len(JUNK_FRAMES) + 1 if junk else 0,
        "audio_sent": send_audio,
        "frames": frames,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--junk", action="store_true")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--send-audio", type=int, default=0)
    args = ap.parse_args()
    result = asyncio.run(run(args.scenario, args.junk, args.timeout, args.send_audio))
    out = HARNESS / "evidence" / f"{args.scenario}-frames.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    order = [f.get("type") or f.get("_harness") for f in result["frames"]]
    print(f"session_id = {result['session_id']}")
    print(f"elapsed    = {result['elapsed']}s")
    print(f"frames     = {len(result['frames'])}")
    print("order      = " + " ".join(order))
    for f in result["frames"]:
        if f.get("type") == "final":
            print(f"  final #{f.get('sequence_no')} [{f['speaker']}] {f['text']!r}")
        elif f.get("type") == "partial":
            print(f"  partial  [{f['speaker']}] {f['text']!r}")
        elif f.get("type") == "audio":
            print(f"  audio    {f['bytes']}B header={f['header']!r}")
        elif f.get("type") == "session_failed":
            print(f"  FAILED   reason={f['reason']!r} at t={f['t']}s")
    print(f"raw -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
