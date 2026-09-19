#!/usr/bin/env python3
"""TS-33 AC#3 — 「학습 종료」 버튼의 프레임과 음성 `end` 명령을 **같은 조건에서** 견준다.

⛔ 앱 코드를 고치지 않는다.

**왜 이 형태인가.** `/ws/session` + `VOICE_ADAPTER=stub` 로는 버튼 경로를 가릴 수 없다 — 픽스처
스트림이 45ms 안에 소진되어 종료의 «원인»이 언제나 어댑터 소진이 된다(실측:
`evidence/33-ts33-end-button-leg.txt` 의 order 가 픽스처 세 턴을 전부 담았다). 그래서 이 드라이버는
어댑터를 **천천히** 흘려 두 경로가 각자 종료의 원인이 되게 한다.

- 팔 A(버튼): 클라이언트가 `{"type":"end_session"}` 을 보낸다 (`lib/ws.ts:SessionSocket.endSession`).
- 팔 B(음성): 어댑터가 `SessionCommandEvent(end, confirmed)` 를 흘린다.

견주는 값: 세션 상태 · `ended_at` 유무 · 마지막 프레임 · 어댑터가 닫혔는지.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "app" / "backend"))

from app.audio_gateway.port import AdapterEvent, SessionCommandEvent, TranscriptEvent  # noqa: E402
from app.audio_gateway.session import SessionRunner  # noqa: E402
from app.db import close_pool, pool as get_pool  # noqa: E402
from app.models.user import FIXED_USER_ID  # noqa: E402
from app.services.sessions import create_session  # noqa: E402


class SlowAdapter:
    """대본을 0.4초 간격으로 흘린다 — 클라이언트가 먼저 끝낼 틈을 만든다."""

    def __init__(self, script: list[AdapterEvent], gap: float = 0.4) -> None:
        self._script = script
        self._gap = gap
        self.closed = False
        self.reports: list[dict[str, object]] = []

    async def start(self) -> None:
        return None

    async def send_audio(self, frame: bytes) -> None:
        return None

    async def events(self) -> AsyncIterator[AdapterEvent]:
        for event in self._script:
            yield event
            await asyncio.sleep(self._gap)

    async def report_command_outcome(
        self, tool_use_id: str, *, executed: bool, reason: str | None = None
    ) -> None:
        self.reports.append({"tool_use_id": tool_use_id, "executed": executed, "reason": reason})

    async def close(self) -> None:
        self.closed = True


class ButtonChannel:
    """세션 시작 뒤 한 번 `end_session` 을 보내고 그 뒤로는 조용히 매달리는 클라이언트."""

    def __init__(self, *, send_end_after: float | None) -> None:
        self.events: list[dict[str, object]] = []
        self._send_end_after = send_end_after
        self._sent = False

    async def send_event(self, event: dict[str, object]) -> None:
        self.events.append(dict(event))

    async def receive_event(self) -> dict[str, object] | None:
        if self._send_end_after is not None and not self._sent:
            await asyncio.sleep(self._send_end_after)
            self._sent = True
            return {"type": "end_session"}
        await asyncio.Event().wait()
        return None


def user_final(text: str) -> TranscriptEvent:
    return TranscriptEvent(kind="final", text=text, speaker="user")


async def arm(pool, name: str, script: list[AdapterEvent], *, end_after: float | None):
    session_id = await create_session(pool, FIXED_USER_ID)
    adapter = SlowAdapter(script)
    channel = ButtonChannel(send_end_after=end_after)
    runner = SessionRunner(adapter, pool, session_id, client=channel, drain_timeout=1.0)
    await runner.run()
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
    return {
        "arm": name,
        "session_id": str(session_id),
        "status": row["status"],
        "closed": row["closed"],
        "adapter_closed": adapter.closed,
        "frames": [e.get("type") for e in channel.events],
        "utterances": [dict(u) for u in stored],
    }


async def main() -> int:
    pool = await get_pool()
    results = []
    try:
        # 팔 A — 버튼. 어댑터는 계속 말하는 중인데 클라이언트가 종료를 보낸다.
        results.append(
            await arm(
                pool,
                "A_button_end_session",
                [
                    user_final("I usually go to gym after work."),
                    user_final("I usually go to office by subway."),
                    user_final("I need to finish my homework tonight."),
                ],
                end_after=0.6,
            )
        )
        # 팔 B — 음성. 같은 대본에 표지와 종료 명령을 얹고 클라이언트는 아무것도 보내지 않는다.
        results.append(
            await arm(
                pool,
                "B_voice_end_confirmed",
                [
                    user_final("I usually go to gym after work."),
                    user_final("Hey, end the session."),
                    SessionCommandEvent(
                        command="end", stage="requested", heard="end", tool_use_id="tu-1"
                    ),
                    user_final("Yes."),
                    SessionCommandEvent(
                        command="end", stage="confirmed", heard="yes", tool_use_id="tu-2"
                    ),
                    user_final("I need to finish my homework tonight."),
                ],
                end_after=None,
            )
        )
    finally:
        await close_pool()

    out = Path(__file__).resolve().parent / "evidence" / "34-ts33-end-paths.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str))
    for r in results:
        print(f"\n== {r['arm']} == session={r['session_id']}")
        print(f"   status={r['status']} closed={r['closed']} adapter_closed={r['adapter_closed']}")
        print(f"   frames={r['frames']}")
        for u in r["utterances"]:
            print(f"   utt #{u['sequence_no']} [{u['utterance_type']}] {u['transcript']!r}")
    print(f"\nraw -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
