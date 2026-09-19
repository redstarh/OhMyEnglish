#!/usr/bin/env python3
"""TS-1 AC#3 레그 2 — `session_ended` 의 **원인**이 클라이언트의 `end_session` 인지 가른다.

⛔ 앱 코드를 고치지 않는다. 이 드라이버는 `SessionRunner` 를 **인프로세스**로 돌린다 —
⚠️ **그래서 실물 `/ws/session` 배선을 지나가지 않는다**(§4-1 이 경고한 우회다). 실물 배선의
프레임 도착은 레그 1(`ts1_real_ws_legs.py`)이 따로 관측했고, 이 레그의 몫은 **인과**뿐이다.

**왜 인프로세스인가.** 서버의 `VOICE_ADAPTER=stub` 은 `FIXTURE_TURNS` 를 **await 없이** 전부
yield 하므로 픽스처가 수십 ms 에 소진된다(레그 1 실측: 12.2ms). 그러면 종료의 원인은 언제나
어댑터 소진이고, 클라이언트가 이길 틈이 없다. 어댑터를 늦추는 수단이 앱 밖에 없어
(어댑터는 `create_voice_adapter(settings, …)` 가 설정만 보고 고른다) 이 팔은 어댑터를 주입한다.
이 방법은 `runs/2026-09-19-b5/ts33_end_paths_compare.py` 가 이미 쓴 것을 그대로 잇는다.

**가름의 근거 — 「대본이 남았는가」.** `_relay` 는 클라이언트가 먼저 끝나면 어댑터 스트림을
`DRAIN_TIMEOUT`(1.0초)까지만 비우고 취소한다(`session.py:378-380`). 그래서 대본 간격을
그 상한보다 **넓게**(2.5초) 두면:

- 클라이언트가 원인이면 → 대본이 **덜 소비된 채** 세션이 닫힌다(yield 수 < 대본 길이).
- 어댑터 소진이 원인이면 → 대본이 **전부** 소비된다.

⇒ 팔 A 에서 대본이 남았다면 종료를 일으킨 것은 어댑터가 아니고, `_relay` 가 깨어날 다른 이유가
`end_session` 하나뿐이므로 인과가 확정된다. 팔 B 는 그 대조군이다(§7-9 의 반증).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections.abc import AsyncIterator
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "app" / "backend"))

from app.audio_gateway.port import AdapterEvent, TranscriptEvent  # noqa: E402
from app.audio_gateway.session import DRAIN_TIMEOUT, SessionRunner  # noqa: E402
from app.db import close_pool  # noqa: E402
from app.db import pool as get_pool  # noqa: E402
from app.models.user import FIXED_USER_ID  # noqa: E402
from app.services.sessions import create_session  # noqa: E402

SCRIPT_GAP_SECONDS = 2.5  # ⛔ `DRAIN_TIMEOUT`(1.0) 보다 넓어야 대본이 남는다 — 이것이 가름의 조건이다
END_AFTER_SECONDS = 0.6  # 대본 1건이 흐른 뒤, 2건째가 오기 전


class SlowAdapter:
    """대본을 넓은 간격으로 흘리고 **몇 건을 실제로 yield 했는지** 노출한다."""

    def __init__(self, script: list[AdapterEvent], gap: float) -> None:
        self._script = script
        self._gap = gap
        self.closed = False
        self.yielded = 0  # ← 가름의 근거. 대본 길이와 견준다

    async def start(self) -> None:
        return None

    async def send_audio(self, frame: bytes) -> None:
        return None

    async def events(self) -> AsyncIterator[AdapterEvent]:
        for event in self._script:
            self.yielded += 1
            yield event
            await asyncio.sleep(self._gap)

    async def report_command_outcome(
        self, tool_use_id: str, *, executed: bool, reason: str | None = None
    ) -> None:
        return None

    async def close(self) -> None:
        self.closed = True


class RecordingChannel:
    """러너가 보낸 프레임을 시각과 함께 적고, 지정 시각에 `end_session` 한 번을 보낸다."""

    def __init__(self, *, send_end_after: float | None) -> None:
        self.events: list[dict[str, object]] = []
        self._send_end_after = send_end_after
        self._sent = False
        self._t0 = time.monotonic()
        self.end_sent_at_ms: float | None = None

    async def send_event(self, event: dict[str, object]) -> None:
        record = {"at_ms": round((time.monotonic() - self._t0) * 1000, 1), **dict(event)}
        self.events.append(record)

    async def receive_event(self) -> dict[str, object] | None:
        if self._send_end_after is not None and not self._sent:
            await asyncio.sleep(self._send_end_after)
            self._sent = True
            self.end_sent_at_ms = round((time.monotonic() - self._t0) * 1000, 1)
            return {"type": "end_session"}
        # 보낼 것이 없으면 영원히 매달린다 — 클라이언트가 종료의 원인이 되지 않게 한다
        await asyncio.Event().wait()
        return None


def user_final(text: str) -> TranscriptEvent:
    return TranscriptEvent(kind="final", text=text, speaker="user")


SCRIPT_TEXTS = [
    "I usually go to gym after work.",
    "I usually go to office by subway.",
    "I need to finish my homework tonight.",
]


async def arm(pool, name: str, *, end_after: float | None) -> dict[str, object]:
    script = [user_final(text) for text in SCRIPT_TEXTS]
    session_id = await create_session(pool, FIXED_USER_ID)
    adapter = SlowAdapter(script, SCRIPT_GAP_SECONDS)
    channel = RecordingChannel(send_end_after=end_after)
    runner = SessionRunner(adapter, pool, session_id, client=channel)
    wall_start = time.monotonic()
    await runner.run()
    elapsed_ms = round((time.monotonic() - wall_start) * 1000, 1)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select status, ended_at is not null as closed from learning_sessions where id = $1",
            session_id,
        )
        stored = await conn.fetch(
            "select sequence_no, utterance_type, transcript from utterances"
            " where session_id = $1 order by sequence_no",
            session_id,
        )

    ended = [e for e in channel.events if e.get("type") == "session_ended"]
    started = [e for e in channel.events if e.get("type") == "session_started"]
    return {
        "arm": name,
        "session_id": str(session_id),
        "end_session_sent_at_ms": channel.end_sent_at_ms,
        "script_length": len(script),
        "script_yielded": adapter.yielded,
        "script_remaining": len(script) - adapter.yielded,
        "adapter_exhausted": adapter.yielded == len(script),
        "adapter_closed": adapter.closed,
        "db_status": row["status"],
        "db_closed": row["closed"],
        "stored_utterances": [dict(u) for u in stored],
        "stored_count": len(stored),
        "frames": channel.events,
        "frame_types": [e.get("type") for e in channel.events],
        "session_ended_present": bool(ended),
        "session_ended_frame": ended[0] if ended else None,
        "session_ended_carries_session_id": bool(ended) and "session_id" in ended[0],
        "session_ended_id_matches": bool(ended)
        and ended[0].get("session_id") == str(session_id)
        and bool(started)
        and started[0].get("session_id") == str(session_id),
        "elapsed_ms": elapsed_ms,
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    pool = await get_pool()
    try:
        arms = [
            await arm(pool, "A_client_end_session", end_after=END_AFTER_SECONDS),
            await arm(pool, "B_adapter_exhaustion", end_after=None),
        ]
    finally:
        await close_pool()

    payload = {
        "drain_timeout_seconds": DRAIN_TIMEOUT,
        "script_gap_seconds": SCRIPT_GAP_SECONDS,
        "end_after_seconds": END_AFTER_SECONDS,
        "arms": arms,
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    for a in arms:
        print(
            f"{a['arm']}: session={a['session_id']} yielded={a['script_yielded']}/{a['script_length']} "
            f"remaining={a['script_remaining']} exhausted={a['adapter_exhausted']} "
            f"stored={a['stored_count']} ended={a['session_ended_present']} "
            f"carries_id={a['session_ended_carries_session_id']} matches={a['session_ended_id_matches']} "
            f"end_sent_at={a['end_session_sent_at_ms']}ms elapsed={a['elapsed_ms']}ms "
            f"frames={a['frame_types']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
