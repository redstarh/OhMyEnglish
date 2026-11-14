"""TASK-317 — transcribe.py 의 「2초 안에 말 시작이 없으면 빈 값」이 실물 Nova 에서 말을 빈 값으로 만들지 않는가.

사용: (app/backend 에서) .venv/bin/python ../../tests/agent/runs/2026-11-14-b17/nova/measure_nova.py
서버를 띄우지 않고 낭독 전사기를 직접 부른다. Nova 호출 2회(말 있음 · 무음).
"""

import asyncio
import json
import time
import wave
from pathlib import Path

from app.audio_gateway.factory import create_transcriber
from app.config import Settings

HERE = Path(__file__).parent


async def main() -> None:
    settings = Settings()
    transcribe = create_transcriber(settings, usage_sink=None)
    with wave.open(str(HERE / "speech.wav")) as w:
        speech = w.readframes(w.getnframes())
    silence = b"\x00" * len(speech)
    out = {}
    for name, pcm in [("speech", speech), ("silence", silence)]:
        t0 = time.monotonic()
        text = await transcribe(pcm)
        out[name] = {"seconds_audio": round(len(pcm) / 32000, 2), "elapsed_s": round(time.monotonic() - t0, 2), "text": text}
        print(name, json.dumps(out[name], ensure_ascii=False))
    (HERE / "result.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


asyncio.run(main())
