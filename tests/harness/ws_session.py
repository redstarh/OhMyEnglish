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
import wave
from pathlib import Path

# psql_cli — DATABASE_URL을 따라가는 psql 헬퍼 (:5432 기본, :5433 폴백). 이전에는 이 파일이
# `podman exec`를 하드코딩해 폴백 컨테이너의 사본에 하네스 세션을 등록했다 — 함정 H-T.
from psql_cli import psql
from websockets.asyncio.client import connect

HARNESS = Path(__file__).resolve().parent.parent.parent / ".harness"
RUN_ID = (HARNESS / "run_id.txt").read_text().strip()
URL = "ws://localhost:8002/ws/session"

# `TASK-86` — **앱 경로로 실제 발화를 흘리기 위한 것**(`--wav`). 왜 필요한가: 발음 tool 판정이
# 스파이크(Nova 직결)에서만 났고 결정 50 이 *"스파이크만으로 닫지 않는다"* 를 명시했는데, 앱 레그의
# 유일한 길이던 브라우저가 `H-BD`(CDP 에서 마이크가 열리지 않는다)로 막혀 있다. 그런데 `/ws/session`
# 프로토콜 자체가 base64 오디오 프레임을 받으므로 **마이크·브라우저 없이** 같은 경로를
# 지나갈 수 있다.
#
# ⛔ **프레임 크기와 박자를 스파이크와 같게 둔다** — 32ms·1024B. 다르게 두면 Nova 가 받는 오디오의
# 도착 속도가 달라져 두 팔의 비교가 깨진다(그리고 간격이 55초를 넘기면 세션이 죽는다 — `H-BF`).
SAMPLE_RATE_HZ = 16_000
SAMPLE_SIZE_BITS = 16
CHANNEL_COUNT = 1
FRAME_MS = 32
FRAME_BYTES = SAMPLE_RATE_HZ * (SAMPLE_SIZE_BITS // 8) * CHANNEL_COUNT * FRAME_MS // 1000
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "voice"

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


def read_lpcm(name: str) -> bytes:
    """픽스처 WAV 에서 헤더를 벗겨 raw LPCM 만 돌려준다.

    `spike_nova_protocol.read_lpcm` 과 **같은 검사**를 한다(16kHz/16bit/mono 가 아니면 죽는다) —
    두 도구가 같은 픽스처를 다르게 받아들이면 오디오 차이가 「앱 레그와 스파이크의 차이」로 읽힌다.
    ⛔ 그 파일을 import 하지 않는 이유: 그 모듈은 import 시점에 Bedrock SDK 를 끌어온다.
    """
    path = name if Path(name).is_absolute() else FIXTURES / name
    with wave.open(str(path)) as wav:
        actual = (wav.getframerate(), wav.getsampwidth() * 8, wav.getnchannels())
        if actual != (SAMPLE_RATE_HZ, SAMPLE_SIZE_BITS, CHANNEL_COUNT):
            raise SystemExit(f"{name}이 16kHz/16bit/mono 가 아니다: {actual}")
        return wav.readframes(wav.getnframes())


def slice_frames(names: list[str], silence_ms: int) -> list[bytes]:
    """여러 wav 를 이어 붙이고 사이에 무음을 넣어 프레임 목록으로 자른다.

    ⚠️ **무음이 필요한 이유**: 발화를 붙여 흘리면 Nova 가 한 발화로 듣고 되말하기 요구가 사라진다 —
    스파이크가 `--wav a.wav,b.wav` 에서 같은 처리를 한다(그쪽 주석이 근거를 소유한다).
    """
    gap = b"\x00" * (FRAME_BYTES * (silence_ms // FRAME_MS))
    lpcm = gap.join(read_lpcm(name) for name in names)
    return [lpcm[i : i + FRAME_BYTES] for i in range(0, len(lpcm), FRAME_BYTES)]


async def run(
    scenario: str,
    junk: bool,
    timeout: float,
    send_audio: int,
    *,
    mode: str | None = None,
    wavs: list[str] | None = None,
    silence_ms: int = 640,
    register_session: bool = True,
) -> dict:
    frames: list[dict] = []
    started = time.monotonic()
    session_id = None
    url = URL if mode is None else f"{URL}?mode={mode}"
    audio_frames = slice_frames(wavs, silence_ms) if wavs else []
    async with connect(url, max_size=None) as ws:
        if junk:
            for payload, _label in JUNK_FRAMES:
                await ws.send(payload)
            await ws.send(b"\x00\x01\x02\x03")  # binary frame
        for _ in range(send_audio):
            silence = base64.b64encode(b"\x00" * 320).decode()
            await ws.send(json.dumps({"type": "audio", "data": silence}))
        if audio_frames:
            # ⛔ **보내면서 받지 않는다** — 이 도구는 아래 루프에서 프레임을 읽으므로, 흘리는 동안
            # 서버가 보낸 이벤트는 소켓 버퍼에 쌓이고 그 뒤에 순서대로 읽힌다. 시각(`t`)이 밀리는
            # 대가를 지는 대신 도구가 단순해진다 — 이 회차가 재는 것은 **tool 도착 여부**이고
            # 이벤트 사이 간격이 아니다.
            for frame in audio_frames:
                await ws.send(
                    json.dumps({"type": "audio", "data": base64.b64encode(frame).decode()})
                )
                await asyncio.sleep(FRAME_MS / 1000)
            # 끝에 무음을 붙여 **발화 종료를 알린다** — 없으면 Nova 가 계속 기다린다(`H-BF` 의
            # 55초 상한이 그 대기에 걸린다).
            for _ in range(silence_ms // FRAME_MS):
                blank = base64.b64encode(b"\x00" * FRAME_BYTES).decode()
                await ws.send(json.dumps({"type": "audio", "data": blank}))
                await asyncio.sleep(FRAME_MS / 1000)
        while True:
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                frames.append({"_harness": "timeout"})
                break
            try:
                raw = await asyncio.wait_for(ws.recv(), remaining)
            except TimeoutError:
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
                if register_session:
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
        "audio_sent": send_audio + len(audio_frames),
        "mode": mode,
        "wavs": wavs,
        "frames": frames,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--junk", action="store_true")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--send-audio", type=int, default=0)
    # `TASK-86` — 앱 경로로 실제 발화를 흘린다. `--wav p2m.wav,p2a.wav` 처럼 쉼표로 이어 준다.
    ap.add_argument("--mode", default=None, help="?mode= 로 붙일 값 (pronunciation·shadowing)")
    ap.add_argument("--wav", default=None, help="픽스처 wav 이름들 (쉼표 구분)")
    ap.add_argument("--silence-ms", type=int, default=640)
    ap.add_argument(
        "--no-register",
        action="store_true",
        help="harness_sessions 에 등록하지 않는다 — 검증 전용 DB 에는 그 표가 없다",
    )
    args = ap.parse_args()
    result = asyncio.run(
        run(
            args.scenario,
            args.junk,
            args.timeout,
            args.send_audio,
            mode=args.mode,
            wavs=[name.strip() for name in args.wav.split(",")] if args.wav else None,
            silence_ms=args.silence_ms,
            register_session=not args.no_register,
        )
    )
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
