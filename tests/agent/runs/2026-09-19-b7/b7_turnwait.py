#!/usr/bin/env python3
"""B7 회차 전용 드라이버 — **코치의 턴이 끝난 것을 프레임으로 확인한 뒤에** 재발화를 흘린다.

왜 새로 쓰는가. `tests/harness/ws_session.py` 는 머리말에 *"보내면서 받지 않는다"* 를 계약으로
적었고, 그 결과 B6 회차의 모든 프레임이 한 시각(`t=32.728`)으로 뭉쳐 **도착 시각을 잃었다.**
그래서 「재발화가 코치의 시범 도중에 도착했는가」를 그 수단으로는 가릴 수 없었다(`TASK-236`).
⛔ 그 파일은 대상 소스이므로 고치지 않는다 — 이 드라이버가 회차 디렉터리에 따로 산다.

## 이 드라이버가 B6 과 다른 점 넷

1. **보내기와 받기를 동시에 돈다.** 받기 루프가 프레임마다 `t`(연결 뒤 단조 경과)와
   `wall`(UTC)을 **각자** 기록한다. 뭉치지 않는다.
2. **턴 종료를 프레임으로 판정한다** — 시각 간격이 아니다. 판정 조건 둘을 **모두** 만족해야 한다.
   - ⒜ agent `final` 프레임이 왔다. 근거: `audio_gateway/nova.py:1070` 이 `stopReason=END_TURN`
     에서 `_flush_pending_agent_text()` 를 돌리고 그것이 agent final 을 만든다. 즉 **agent final
     프레임 자체가 Nova 의 턴 경계 신호가 WS 로 새어 나온 것**이다.
   - ⒝ `audio` 프레임이 `--quiet-ms` 동안 한 건도 오지 않았다. `audio` 는 코치의 음성이므로
     그것이 멈춘 것이 「코치가 말을 마쳤다」다. (`p_app_path.py` 의 `QUIET_MS` 와 같은 판정이다.)
3. **기다리는 동안 무음을 계속 흘린다.** 실제 마이크가 그렇고, 끊으면 프레임 간격이 55초를
   넘겨 세션이 죽는다(함정 `H-BF`).
4. **둘째 발화 뒤 판정 tool 을 `--second-wait-s` 초 동안 기다린다.** 기다린 시간을 결과에 적는다.

## 관측력 증명 (§7-7)

⛔ 「둘째 `pronunciation` 프레임이 오지 않았다」를 결론으로 쓰기 전에, **같은 수단이 첫
`pronunciation` 프레임을 1건 잡는 것**을 먼저 보여야 한다. 그래서 이 드라이버는 첫 프레임을
**기다리고**(`--first-tool-wait-s`), 그것을 못 잡으면 둘째 발화를 흘리지 않고
`verdict=blocked_no_observability` 로 끝낸다 — 그 경우는 `실패` 가 아니라 `차단됨` 이다.

⚠️ **스텁 어댑터로는 이 측정이 성립하지 않는다**(실측). `audio_gateway/stub.py` 의 `events()` 는
고정 대본을 다 내놓으면 제너레이터가 끝나고 세션이 곧 닫힌다 — 발음 tool 이 없고 턴을 이어 가지
않는다. 그래서 스텁 예비 회차의 값어치는 **드라이버의 기계 부품**(동시 송수신 · 프레임별 시각 ·
닫힘 처리)을 확인하는 것뿐이고, 판정은 실물에서만 난다.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import datetime
import json
import time
import wave
from pathlib import Path

from websockets.asyncio.client import connect

# ⛔ 프레임 크기와 박자를 `ws_session.py` 와 같게 둔다 — 32ms·1024B. 다르게 두면 Nova 가 받는
# 오디오의 도착 속도가 달라져 B6 과 이 회차의 비교가 깨진다.
SAMPLE_RATE_HZ = 16_000
SAMPLE_SIZE_BITS = 16
CHANNEL_COUNT = 1
FRAME_MS = 32
FRAME_BYTES = SAMPLE_RATE_HZ * (SAMPLE_SIZE_BITS // 8) * CHANNEL_COUNT * FRAME_MS // 1000
FIXTURES = Path("/Users/redstar/MyProject/OhMyEnglish/tests/harness/fixtures/voice")

# 코치의 음성으로 세는 프레임. 이것이 멈춘 것이 「말을 마쳤다」의 한쪽 조건이다.
AGENT_VOICE_TYPE = "audio"


def read_lpcm(name: str) -> tuple[bytes, float]:
    """픽스처 WAV 에서 헤더를 벗겨 raw LPCM 과 길이(초)를 돌려준다.

    `ws_session.read_lpcm` 과 **같은 검사**를 한다 — 16kHz/16bit/mono 가 아니면 죽는다. 두 도구가
    같은 픽스처를 다르게 받아들이면 오디오 차이가 「회차 사이의 차이」로 읽힌다.
    """
    path = Path(name) if Path(name).is_absolute() else FIXTURES / name
    with wave.open(str(path)) as wav:
        actual = (wav.getframerate(), wav.getsampwidth() * 8, wav.getnchannels())
        if actual != (SAMPLE_RATE_HZ, SAMPLE_SIZE_BITS, CHANNEL_COUNT):
            raise SystemExit(f"{name} 이 16kHz/16bit/mono 가 아니다: {actual}")
        return wav.readframes(wav.getnframes()), round(wav.getnframes() / wav.getframerate(), 3)


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class Observer:
    """받기 루프가 쓰고 보내기 루프가 읽는 공유 상태.

    ⛔ 프레임마다 도착 시각을 **각자** 기록한다 — B6 의 한계가 정확히 이 자리였다.
    """

    def __init__(self, started: float) -> None:
        self.started = started
        self.frames: list[dict] = []
        self.session_id: str | None = None
        self.phase = "connect"
        self.closed = False
        # 턴 종료 판정에 쓰는 두 값. 프레임이 올 때만 움직인다.
        self.last_agent_voice_t: float | None = None
        self.agent_final_count = 0
        self.pronunciation_frames: list[dict] = []
        # 판정 근거로 적을 「어느 프레임이 조건을 만족시켰는가」
        self.turn_end_evidence: dict | None = None

    def t(self) -> float:
        return round(time.monotonic() - self.started, 3)

    def note(self, **kw) -> None:
        self.frames.append({"i": len(self.frames), "t": self.t(), "wall": utc_now(), "phase": self.phase, **kw})

    def record(self, event: dict) -> dict:
        t = self.t()
        kind = event.get("type")
        rec: dict = {"i": len(self.frames), "t": t, "wall": utc_now(), "phase": self.phase, "type": kind}
        if kind == "session_started":
            self.session_id = event.get("session_id")
            rec["session_id"] = self.session_id
            rec["pronunciation_focus"] = event.get("pronunciation_focus")
        elif kind in ("partial", "final"):
            rec["speaker"] = event.get("speaker")
            rec["text"] = event.get("text")
            if "sequence_no" in event:
                rec["sequence_no"] = event["sequence_no"]
            if kind == "final" and event.get("speaker") == "agent":
                self.agent_final_count += 1
                rec["agent_final_no"] = self.agent_final_count
        elif kind == AGENT_VOICE_TYPE:
            blob = base64.b64decode(event["data"])
            rec["bytes"] = len(blob)
            self.last_agent_voice_t = t
        elif kind == "pronunciation":
            rec["outcome"] = event.get("outcome")
            rec["target_form"] = event.get("target_form")
            rec["target_sound"] = event.get("target_sound")
            self.pronunciation_frames.append(rec)
        elif kind == "session_failed":
            rec["reason"] = event.get("reason")
        elif kind in ("speech_start", "speech_end"):
            rec["offset_ms"] = event.get("offset_ms")
        self.frames.append(rec)
        return rec

    def turn_ended(self, quiet_ms: int) -> bool:
        """코치의 턴이 끝났는가 — **프레임 두 조건으로만** 판정한다.

        ⒜ agent final 이 1건 이상 왔다 (`END_TURN` 이 새어 나온 신호) ·
        ⒝ 코치의 음성 프레임이 `quiet_ms` 동안 오지 않았다.

        ⚠️ 음성이 **한 건도 오지 않은** 경우는 ⒝ 를 만족시키지 않는다 — 그 경우는
        「조용하다」가 아니라 「아직 시작하지 않았다」이고, 그것을 턴 종료로 읽는 것이
        함정 문서가 경고한 `tui-idle` 오판과 같은 실수다.
        """
        if self.agent_final_count < 1 or self.last_agent_voice_t is None:
            return False
        quiet_for = self.t() - self.last_agent_voice_t
        if quiet_for * 1000 < quiet_ms:
            return False
        self.turn_end_evidence = {
            "agent_final_count": self.agent_final_count,
            "last_agent_voice_t": self.last_agent_voice_t,
            "quiet_for_s": round(quiet_for, 3),
            "decided_at_t": self.t(),
            "rule": f"agent final >= 1 AND no '{AGENT_VOICE_TYPE}' frame for >= {quiet_ms}ms",
        }
        return True


async def receiver(ws, obs: Observer) -> None:
    """끝까지 받는다. ⛔ 보내는 동안에도 계속 돈다 — 그것이 이 드라이버의 존재 이유다."""
    while True:
        try:
            raw = await ws.recv()
        except Exception as exc:
            obs.note(_harness=f"closed: {type(exc).__name__}")
            obs.closed = True
            return
        obs.record(json.loads(raw))
        if obs.frames[-1].get("type") in ("session_ended", "session_failed"):
            obs.closed = True
            return


async def send_frame(ws, obs: Observer, payload: str) -> bool:
    """오디오 프레임 하나를 보낸다. **닫혔으면 조용히 False** 를 돌려준다.

    ⛔ 닫힘을 예외로 터뜨리지 않는 이유: 세션이 먼저 닫히는 것은 이 회차가 **관측해야 하는
    결과**이고, 그것을 드라이버의 죽음으로 바꾸면 여태 모은 프레임을 잃는다(실측 — 스텁
    예비 회차에서 `ConnectionClosedOK` 로 통째로 잃었다).
    """
    if obs.closed:
        return False
    try:
        await ws.send(payload)
        return True
    except Exception as exc:
        obs.note(_harness=f"send failed: {type(exc).__name__}")
        obs.closed = True
        return False


def audio_payload(chunk: bytes) -> str:
    return json.dumps({"type": "audio", "data": base64.b64encode(chunk).decode()})


BLANK_PAYLOAD = audio_payload(b"\x00" * FRAME_BYTES)


async def stream_lpcm(ws, obs: Observer, lpcm: bytes) -> int:
    sent = 0
    for i in range(0, len(lpcm), FRAME_BYTES):
        if not await send_frame(ws, obs, audio_payload(lpcm[i : i + FRAME_BYTES])):
            return sent
        sent += 1
        await asyncio.sleep(FRAME_MS / 1000)
    return sent


async def stream_silence(ws, obs: Observer, ms: int) -> int:
    sent = 0
    for _ in range(max(0, ms // FRAME_MS)):
        if not await send_frame(ws, obs, BLANK_PAYLOAD):
            return sent
        sent += 1
        await asyncio.sleep(FRAME_MS / 1000)
    return sent


async def silence_until(ws, obs: Observer, predicate, max_s: float) -> tuple[bool, float, int]:
    """무음을 계속 흘리면서 `predicate()` 가 참이 되기를 기다린다.

    ⛔ 무음을 흘리는 것이 필수다 — 멈추면 프레임 간격이 55초를 넘겨 세션이 죽는다(`H-BF`).
    돌려주는 것: (조건이 참이 됐는가, 기다린 초, 보낸 프레임 수).
    ⚠️ **조건을 먼저 재고 그 다음에 보낸다** — 순서를 뒤집으면 이미 참인 조건에 한 프레임을 더
    흘린다.
    """
    began = time.monotonic()
    sent = 0
    while time.monotonic() - began < max_s:
        if predicate():
            return True, round(time.monotonic() - began, 3), sent
        if obs.closed:
            return predicate(), round(time.monotonic() - began, 3), sent
        if not await send_frame(ws, obs, BLANK_PAYLOAD):
            return predicate(), round(time.monotonic() - began, 3), sent
        sent += 1
        await asyncio.sleep(FRAME_MS / 1000)
    return predicate(), round(time.monotonic() - began, 3), sent


async def close_out(ws, obs: Observer, recv_task, drain_s: float, step) -> None:
    """`end_session` 을 보내고 `session_ended` 까지 받아 낸다."""
    if not obs.closed:
        await send_frame(ws, obs, json.dumps({"type": "end_session"}))
        step("end_session.send")
    try:
        await asyncio.wait_for(asyncio.shield(recv_task), timeout=drain_s)
    except TimeoutError:
        step("drain.timeout", seconds=drain_s)
    except Exception:
        pass


async def run(args) -> dict:
    lpcm1, dur1 = read_lpcm(args.wav_first)
    lpcm2, dur2 = read_lpcm(args.wav_second)
    url = f"{args.url}?mode={args.mode}" if args.mode else args.url
    obs = Observer(time.monotonic())
    log: list[dict] = []

    def step(name: str, **kw) -> None:
        log.append({"step": name, "t": obs.t(), "wall": utc_now(), **kw})
        print(f"[{obs.t():8.3f}] {name} {kw}", flush=True)

    async with connect(url, max_size=None) as ws:
        recv_task = asyncio.create_task(receiver(ws, obs), name="recv")
        try:
            # ── 1단계. 첫 발화(강한 한국어 억양판)를 흘린다.
            obs.phase = "utt1"
            step("utt1.begin", wav=args.wav_first, seconds=dur1)
            n = await stream_lpcm(ws, obs, lpcm1)
            n += await stream_silence(ws, obs, args.end_silence_ms)
            step("utt1.sent", audio_frames=n, closed=obs.closed)
            if obs.closed:
                step("abort", why="첫 발화를 흘리는 중에 세션이 닫혔다")
                await close_out(ws, obs, recv_task, args.drain_s, step)
                return finish(obs, log, "blocked_closed_during_utt1", dur1, dur2, args)

            # ── 2단계. **먼저** 첫 판정 tool 이 오는 것을 확인한다 (관측력 증명 · §7-7).
            obs.phase = "await_first_tool"
            got_first, waited_first, sent_first = await silence_until(
                ws, obs, lambda: len(obs.pronunciation_frames) >= 1, args.first_tool_wait_s
            )
            step("first_tool", arrived=got_first, waited_s=waited_first, silence_frames=sent_first,
                 frame=obs.pronunciation_frames[0] if obs.pronunciation_frames else None)
            if not got_first:
                # ⛔ 관측력을 증명하지 못했다 ⇒ 둘째 발화를 흘리지 않는다. `차단됨` 이다.
                step("abort", why="첫 pronunciation 프레임을 못 잡았다 — 관측력 미증명",
                     closed=obs.closed)
                await close_out(ws, obs, recv_task, args.drain_s, step)
                return finish(obs, log, "blocked_no_observability", dur1, dur2, args)

            # ── 3단계. 코치의 턴이 **끝난 것을 프레임으로 확인**하고 기다린다.
            obs.phase = "await_turn_end"
            turn_over, waited_turn, sent_turn = await silence_until(
                ws, obs, lambda: obs.turn_ended(args.quiet_ms), args.turn_wait_s
            )
            step("turn_end", decided=turn_over, waited_s=waited_turn, silence_frames=sent_turn,
                 evidence=obs.turn_end_evidence, closed=obs.closed)
            if not turn_over:
                step("abort", why="코치의 턴 종료를 프레임으로 확인하지 못했다")
                await close_out(ws, obs, recv_task, args.drain_s, step)
                return finish(obs, log, "blocked_turn_end_unconfirmed", dur1, dur2, args)

            # 턴 밖임을 한 번 더 못 박는다 — 둘째 발화 직전의 프레임 지형을 적어 둔다.
            step("pre_utt2_frame_landscape",
                 last_agent_voice_t=obs.last_agent_voice_t,
                 agent_final_count=obs.agent_final_count,
                 total_frames=len(obs.frames),
                 last_frame=obs.frames[-1] if obs.frames else None)

            # ── 4단계. 둘째 발화(같은 문장의 정확 발음판)를 흘린다 — 코치의 턴 «밖»이다.
            obs.phase = "utt2"
            utt2_begin_t = obs.t()
            step("utt2.begin", wav=args.wav_second, seconds=dur2)
            n2 = await stream_lpcm(ws, obs, lpcm2)
            n2 += await stream_silence(ws, obs, args.end_silence_ms)
            step("utt2.sent", audio_frames=n2, closed=obs.closed)

            # ── 5단계. 둘째 판정 tool 을 충분히 기다린다.
            obs.phase = "await_second_tool"
            got_second, waited_second, sent_second = await silence_until(
                ws, obs, lambda: len(obs.pronunciation_frames) >= 2, args.second_wait_s
            )
            step("second_tool", arrived=got_second, waited_s=waited_second,
                 silence_frames=sent_second, closed=obs.closed,
                 frame=obs.pronunciation_frames[1] if len(obs.pronunciation_frames) >= 2 else None)

            obs.phase = "closing"
            await close_out(ws, obs, recv_task, args.drain_s, step)
            verdict = "second_tool_arrived" if got_second else "second_tool_absent"
            out = finish(obs, log, verdict, dur1, dur2, args)
            out["utt2_begin_t"] = utt2_begin_t
            out["second_tool_waited_s"] = waited_second
            return out
        finally:
            if not recv_task.done():
                recv_task.cancel()


def finish(obs: Observer, log: list[dict], verdict: str, dur1: float, dur2: float, args) -> dict:
    counts: dict[str, int] = {}
    for f in obs.frames:
        key = f.get("type") or f.get("_harness") or "?"
        counts[key] = counts.get(key, 0) + 1
    # 프레임별 시각이 **실제로 갈렸는가** — B6 의 한계를 되풀이하지 않았음을 기계로 보인다.
    distinct_t = len({f["t"] for f in obs.frames})
    return {
        "driver": "b7_turnwait.py",
        "verdict": verdict,
        "session_id": obs.session_id,
        "mode": args.mode,
        "wavs": [args.wav_first, args.wav_second],
        "wav_seconds": [dur1, dur2],
        "elapsed": obs.t(),
        "frame_counts": counts,
        "distinct_arrival_times": distinct_t,
        "total_frames": len(obs.frames),
        "pronunciation_frames": obs.pronunciation_frames,
        "turn_end_evidence": obs.turn_end_evidence,
        "settings": {
            "quiet_ms": args.quiet_ms,
            "first_tool_wait_s": args.first_tool_wait_s,
            "turn_wait_s": args.turn_wait_s,
            "second_wait_s": args.second_wait_s,
            "end_silence_ms": args.end_silence_ms,
        },
        "steps": log,
        "frames": obs.frames,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="ws://localhost:8002/ws/session")
    ap.add_argument("--mode", default="pronunciation")
    ap.add_argument("--wav-first", default="p2k.wav", help="강한 한국어 억양판")
    ap.add_argument("--wav-second", default="p2a.wav", help="같은 문장의 정확 발음판")
    ap.add_argument("--end-silence-ms", type=int, default=1024, help="발화 끝을 알리는 무음")
    ap.add_argument("--quiet-ms", type=int, default=3000, help="코치 음성이 이 시간 없으면 조용함")
    ap.add_argument("--first-tool-wait-s", type=float, default=60.0)
    ap.add_argument("--turn-wait-s", type=float, default=90.0)
    ap.add_argument("--second-wait-s", type=float, default=60.0)
    ap.add_argument("--drain-s", type=float, default=20.0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    result = asyncio.run(run(args))
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== 요약 ===")
    print(f"verdict          = {result['verdict']}")
    print(f"session_id       = {result['session_id']}")
    print(f"elapsed          = {result['elapsed']}s")
    print(f"frames           = {result['frame_counts']}")
    print(f"distinct t 값     = {result['distinct_arrival_times']} / {result['total_frames']} 프레임")
    print(f"turn_end         = {result['turn_end_evidence']}")
    for pf in result["pronunciation_frames"]:
        print(f"  pronunciation @t={pf['t']} phase={pf['phase']} outcome={pf.get('outcome')} sound={pf.get('target_sound')}")
    print("--- 전사문 (도착 순 · 시각 각자) ---")
    for f in result["frames"]:
        if f.get("type") in ("partial", "final"):
            print(f"  [{f['t']:8.3f}] {f['phase']:18s} {f['type']:7s} {f.get('speaker')}: {f.get('text')!r}")
    print(f"기록: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
