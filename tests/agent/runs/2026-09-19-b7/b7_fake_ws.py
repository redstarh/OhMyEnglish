#!/usr/bin/env python3
"""드라이버 검사용 가짜 `/ws/session` — **판정 수단이 두 결과를 모두 낼 수 있음을 먼저 증명한다.**

왜 필요한가. 실물 Nova 회차는 이 회차에 **2회**만 허용됐다(사용자 사전 승인 범위). 그런데 스텁
어댑터는 세션을 41ms 만에 닫아 `turn_ended` 판정과 둘째 tool 대기 경로를 **한 줄도 지나가지
않는다**(실측 · `evidence/01-stub-dryrun.json`). 그 상태로 실물을 돌리면 「둘째 프레임이 오지
않았다」가 앱의 사실인지 내 미검증 코드의 침묵인지 가릴 수 없다 — 그것이 §7-7 이 경고하는 자리다.

그래서 이 가짜 서버가 **같은 WS 규약으로** 실물의 프레임 지형을 흉내 내고, 두 판을 돌린다.

| 판 | 둘째 `pronunciation` 프레임 | 드라이버가 내야 하는 verdict |
|---|---|---|
| `--emit-second` | 보낸다 | `second_tool_arrived` |
| (기본) | 보내지 않는다 | `second_tool_absent` |

⇒ 두 판이 다른 verdict 를 내면 **그 판정에 판별력이 있다**. 같은 verdict 를 내면 드라이버가
눈먼 것이므로 실물 회차를 돌리지 않는다.

⛔ 이것은 앱을 대신하지 않는다. 앱의 사실은 실물에서만 난다 — 이 파일이 재는 것은 **내 관측
수단**뿐이다.

## 흉내 내는 지형 (B6 의 실측 프레임 순서를 따른다)

첫 발화를 다 받으면: `speech_start` → 사용자 `final` → `speech_end` → **`pronunciation`** →
코치 음성 `audio` 다발 → 코치 `partial` 들 → 코치 `final`(`END_TURN` 이 새는 자리) → 조용해진다.
둘째 발화를 다 받으면: `speech_start` → 사용자 `final` → `speech_end` → (판에 따라)
**둘째 `pronunciation`** → 짧은 `audio` 다발 → 코치 `final`.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import uuid

from websockets.asyncio.server import serve

FRAME_BYTES = 1024
SILENCE_RUN_TO_END_UTTERANCE = 12  # 무음 12프레임(약 384ms)이 이어지면 발화가 끝났다고 본다
VOICE_FRAME = base64.b64encode(b"\x11" * FRAME_BYTES).decode()


async def send(ws, obj: dict) -> None:
    await ws.send(json.dumps(obj))


async def speak(ws, frames: int, gap_s: float = 0.02) -> None:
    """코치의 음성 다발 — `audio` 프레임을 흘린다. 이것이 멈추는 것이 턴 종료의 한 조건이다."""
    for _ in range(frames):
        await send(ws, {"type": "audio", "data": VOICE_FRAME})
        await asyncio.sleep(gap_s)


def is_silence(payload: dict) -> bool:
    if payload.get("type") != "audio":
        return False
    return not any(base64.b64decode(payload["data"]))


async def handler(ws, *, emit_second: bool) -> None:
    session_id = str(uuid.uuid4())
    await send(ws, {"type": "session_started", "session_id": session_id,
                    "pronunciation_focus": {"sound_key": "th_as_t"}})
    utterance_no = 0
    voiced_seen = 0
    silence_run = 0
    seq = 0
    async for raw in ws:
        payload = json.loads(raw)
        if payload.get("type") == "end_session":
            break
        if payload.get("type") != "audio":
            continue
        if is_silence(payload):
            silence_run += 1
        else:
            voiced_seen += 1
            silence_run = 0
            continue
        # 발화 하나가 끝났다 — 유의미한 음성을 받은 뒤에 무음이 이어진 경우만이다.
        if voiced_seen == 0 or silence_run < SILENCE_RUN_TO_END_UTTERANCE:
            continue
        utterance_no += 1
        voiced_seen = 0
        silence_run = 0
        if utterance_no == 1:
            seq += 1
            await send(ws, {"type": "speech_start", "offset_ms": 0})
            await send(ws, {"type": "final", "speaker": "user", "sequence_no": seq,
                            "text": "아이피니시트더리포트엔쉐어드더리절치위드마이팀"})
            await send(ws, {"type": "speech_end", "offset_ms": 3792})
            await send(ws, {"type": "pronunciation", "outcome": "pending",
                            "target_form": "I finished the report and shared the results with my team.",
                            "target_sound": "th_as_t"})
            # 코치의 시범 — 음성이 한참 흐르고 그 뒤에 턴이 닫힌다.
            await speak(ws, 200)
            await send(ws, {"type": "partial", "speaker": "agent",
                            "text": 'The sound to focus on is the "th" sound.'})
            await speak(ws, 60)
            await send(ws, {"type": "partial", "speaker": "agent",
                            "text": "\n\nPlease repeat: I finished the report and shared the results with my team."})
            seq += 1
            await send(ws, {"type": "final", "speaker": "agent", "sequence_no": seq,
                            "text": 'The sound to focus on is the "th" sound.\n\nPlease repeat: I finished the report and shared the results with my team.'})
        elif utterance_no == 2:
            seq += 1
            await send(ws, {"type": "speech_start", "offset_ms": 0})
            await send(ws, {"type": "final", "speaker": "user", "sequence_no": seq,
                            "text": "i finished the report and shared the results with my team"})
            await send(ws, {"type": "speech_end", "offset_ms": 2957})
            if emit_second:
                await send(ws, {"type": "pronunciation", "outcome": "correct",
                                "target_form": "I finished the report and shared the results with my team.",
                                "target_sound": "th_as_t"})
            await speak(ws, 40)
            seq += 1
            await send(ws, {"type": "final", "speaker": "agent", "sequence_no": seq,
                            "text": "That was much better. Great work."})
    await send(ws, {"type": "session_ended"})


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9877)
    ap.add_argument("--emit-second", action="store_true", help="둘째 pronunciation 프레임을 보낸다")
    args = ap.parse_args()

    async def route(ws):
        await handler(ws, emit_second=args.emit_second)

    async with serve(route, "127.0.0.1", args.port, max_size=None):
        print(f"fake ws on ws://127.0.0.1:{args.port}/ws/session  emit_second={args.emit_second}", flush=True)
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
