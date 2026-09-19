#!/usr/bin/env python3
"""TS-36 AC#3 넷째 자리 — `session_started` 의 `focus_pattern` 을 프로세스 밖에서 읽는다.

무엇을 재는가: 「준비된 계획이 있으면 지시문의 초점이 고른 패턴으로 대체된다」(`PRD.md:70` ·
`api/ws.py` 머리말 「즉시 드릴 진입」 절). 그 대체는 **세션 시작에만** 일어나고 그 뒤 어디에도
남지 않으므로 이 프레임이 유일한 밖의 표면이다(`TASK-250` 노트).

⛔ **팔 하나로는 못 가른다.** 「키가 실렸다」만 보면 **모든 세션에 싣는 구현**도 통과하고, 그것은
「일어나지 않은 대체를 보고한다」는 반대 방향 결함이다. 그래서 팔 셋을 같은 드라이버로 돈다:

* `A` — 실재하는 패턴 + 준비된 계획 ⇒ `focus_pattern` = 그 키
* `B` — 패턴 없이 추가 학습 ⇒ `focus_pattern` **키 자체가 없음**
* `C` — 없는 패턴 키 ⇒ `focus_pattern` **키 없음** · 세션은 열림 · 세션 행의
  `focus_pattern_key` 에는 그 키가 **남음**

팔 A 가 키를 잡는 것이 곧 팔 B·C 의 「없음」 관측에 대한 **관측력 증명**이다(에이전트 규약 §7-7:
관측력을 증명하지 못한 「0건」은 결함이 아니라 차단됨이다).

⚠️ **`focus_pattern` 이 없는 것과 값이 `null` 인 것을 구분해 적는다** — 계약은 「있을 때만 싣는다」
이므로 `null` 로 실리는 것은 계약 위반이다. 그래서 `in` 검사와 값 검사를 따로 기록한다.

⛔ **워커를 켜지 않는다**(`H-CD`) · 스텁 어댑터로만 돈다. 회차가 만든 세션은
`tests/harness/teardown_session.py --session-id <uuid>` 로 걷는다.

쓰는 법:
    ./app/backend/.venv/bin/python tests/agent/runs/2026-09-19-b9/ts36_focus_frame_driver.py \
        --arm A --pattern verb_tense_past_simple_for_past_events
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "tests" / "harness"))

from websockets.asyncio.client import connect  # noqa: E402

URL = "ws://localhost:8002/ws/session"


async def observe(query: dict[str, str], collect_seconds: float) -> dict:
    """소켓 하나를 열어 `session_started` 를 잡고 프레임을 그대로 기록한다.

    ⛔ **`end_session` 을 보내기 «전에» 수집을 끝내지 않는다** — 규약 §7-7 이 이름 붙인 오보의
    기전이 그것이다(수집을 종료 명령 앞에서 끊어 종료 이벤트를 「0건」으로 관측했다). 여기서는
    종료 명령 뒤에도 `session_ended` 까지 계속 읽는다.
    """
    url = f"{URL}?{urlencode(query)}" if query else URL
    frames: list[dict] = []
    started: dict | None = None
    t0 = time.monotonic()
    async with connect(url, max_size=None) as ws:
        # 1) session_started 를 잡을 때까지 읽는다.
        while time.monotonic() - t0 < collect_seconds:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=collect_seconds)
            except TimeoutError:
                break
            frame = json.loads(raw)
            frames.append(frame)
            if frame.get("type") == "session_started":
                started = frame
                break
            if frame.get("type") in {"session_failed", "session_ended"}:
                break
        # 2) 종료 명령을 보내고 그 뒤 프레임도 계속 읽는다.
        if started is not None:
            await ws.send(json.dumps({"type": "end_session"}))
        end_deadline = time.monotonic() + collect_seconds
        while time.monotonic() < end_deadline:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            except (TimeoutError, Exception):  # noqa: BLE001 - 닫힘도 정상 종료다
                break
            with_frame = json.loads(raw)
            frames.append(with_frame)
            if with_frame.get("type") in {"session_ended", "session_failed"}:
                break
    return {"url": url, "frames": frames, "session_started": started}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True)
    parser.add_argument("--pattern", default=None)
    parser.add_argument("--source", default="additional")
    parser.add_argument("--seconds", type=float, default=12.0)
    args = parser.parse_args()

    query: dict[str, str] = {}
    if args.source:
        query["source"] = args.source
    if args.pattern is not None:
        query["pattern"] = args.pattern

    observed = asyncio.run(observe(query, args.seconds))
    started = observed["session_started"]
    # ⛔ 키 «부재» 와 값 `null` 을 갈라 적는다 — 계약은 「있을 때만 싣는다」다.
    report = {
        "arm": args.arm,
        "url": observed["url"],
        "requested_pattern": args.pattern,
        "session_started_seen": started is not None,
        "session_id": (started or {}).get("session_id"),
        "focus_pattern_key_present": (started is not None and "focus_pattern" in started),
        "focus_pattern_value": (started or {}).get("focus_pattern", "<<KEY ABSENT>>"),
        "session_started_keys": sorted(started.keys()) if started else [],
        "session_started_frame": started,
        "frame_types": [f.get("type") for f in observed["frames"]],
    }
    out = HERE / "evidence" / f"TS-36-arm{args.arm}-session-started.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n적은 곳: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
