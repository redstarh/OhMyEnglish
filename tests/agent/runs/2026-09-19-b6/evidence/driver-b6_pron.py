"""B6 회차 전용 — `mode=pronunciation` 한 세션을 태우고 관측을 «내 회차 디렉터리»에 쓴다.

⛔ 대상 소스를 고치지 않는다. `tests/harness/ws_session.py` 의 `run()` 을 그대로 부른다 —
   그 파일의 `main()` 은 관측을 `.harness/evidence/` 에 쓰는데 그 경로는 이 에이전트의 쓰기
   경계 밖이다(§1-1). 그래서 얇은 래퍼만 둔다.

⛔ `pronunciation` 프레임의 «내용» 은 `ws_session.run()` 이 담지 않으므로(type 만 센다)
   판정의 정본은 DB 의 `pronunciation_attempts` 다 — 회차가 회차 전후로 그것을 센다.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

HARNESS = Path("/Users/redstar/MyProject/OhMyEnglish/tests/harness")
sys.path.insert(0, str(HARNESS))

import ws_session as WS  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--mode", default=None)
    ap.add_argument("--wav", required=True)
    ap.add_argument("--silence-ms", type=int, default=12000)
    ap.add_argument("--timeout", type=float, default=90.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = asyncio.run(
        WS.run(
            args.scenario,
            False,
            args.timeout,
            0,
            mode=args.mode,
            wavs=[n.strip() for n in args.wav.split(",")],
            silence_ms=args.silence_ms,
            register_session=False,
        )
    )
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"session_id = {result['session_id']}")
    print(f"elapsed    = {result['elapsed']}s · mode={result['mode']} · wavs={result['wavs']}")
    counts: dict[str, int] = {}
    for f in result["frames"]:
        key = f.get("type") or f.get("_harness") or "?"
        counts[key] = counts.get(key, 0) + 1
    print(f"frame counts = {counts}")
    for f in result["frames"]:
        if f.get("type") in ("partial", "final"):
            print(f"  [{f['t']}] {f['type']} {f.get('speaker')}: {f.get('text')}")
        elif f.get("type") not in ("audio", None):
            print(f"  [{f.get('t')}] {f.get('type')} {json.dumps({k: v for k, v in f.items() if k not in ('t', 'type')}, ensure_ascii=False)}")
    print(f"기록: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
