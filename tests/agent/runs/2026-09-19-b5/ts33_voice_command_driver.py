#!/usr/bin/env python3
"""TS-33 드라이버 — 음성 명령 여섯을 세션 게이트웨이에 흘려 실제 거동을 관측한다.

⛔ **앱 코드를 고치지 않는다.** 이 파일은 회차 디렉터리에만 있고 `app/**` 를 import 만 한다.

**왜 이 형태인가.** `/ws/session` 으로는 이 시나리오를 관측할 수 없다. 음성 명령은
`SessionCommandEvent` 로만 들어오고 그 이벤트를 만드는 것은 **어댑터**인데
(`audio_gateway/port.SessionCommandEvent` docstring — "어댑터만 만들 수 있다"),
`VOICE_ADAPTER=stub` 의 `StubVoiceAdapter.events()` 는 전사문과 오디오 프레임만 흘린다.
⇒ 이 배치는 실물 Nova 가 금지되어 있으므로, **제어 이벤트를 흘리는 어댑터 대역**을 이 드라이버가
넣고 `SessionRunner` 를 그대로 돌린다. 지나가지 **않는** 구간은 둘이다:
① Nova 의 `toolUse` → `SessionCommandEvent` 번역 ② `/ws/session` 소켓 층.
그 둘은 결과 문서에 「계측하지 못한 것」으로 적는다.

관측 대상(실제 앱 코드):
`SessionRunner._pump_adapter_events` → `_handle_command` → `_decide_command` →
표지 검사(`models/voice_command.is_wake_command`) · 확인 절차 · `_apply_pause`(DB 쓰기) ·
`closes_session` 판정 · `_classify_user_final`(발화 유형) · 종료 경로.
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "app" / "backend"))

from app.audio_gateway.port import AdapterEvent, SessionCommandEvent, TranscriptEvent  # noqa: E402
from app.audio_gateway.session import SessionRunner  # noqa: E402
from app.db import close_pool, pool as get_pool  # noqa: E402
from app.models.user import FIXED_USER_ID  # noqa: E402
from app.services.sessions import create_session  # noqa: E402


class ScriptedAdapter:
    """대본대로 이벤트를 흘리는 어댑터 대역. 실행 보고(`report_command_outcome`)를 기록한다."""

    def __init__(self, script: list[AdapterEvent]) -> None:
        self._script = script
        self.reports: list[dict[str, object]] = []
        self.closed = False
        self.frames = 0

    async def start(self) -> None:
        return None

    async def send_audio(self, frame: bytes) -> None:
        self.frames += 1

    async def events(self) -> AsyncIterator[AdapterEvent]:
        for event in self._script:
            yield event
            # 게이트웨이가 DB 를 오가므로 한 박자 양보한다 — 대본이 앞질러 흐르지 않게 한다.
            await asyncio.sleep(0)

    async def report_command_outcome(
        self, tool_use_id: str, *, executed: bool, reason: str | None = None
    ) -> None:
        self.reports.append({"tool_use_id": tool_use_id, "executed": executed, "reason": reason})

    async def close(self) -> None:
        self.closed = True


class RecordingChannel:
    """클라이언트 대역 — 보낸 프레임을 모두 적고, 클라이언트 쪽은 조용히 매달려 있는다.

    ⛔ `receive_event` 가 곧바로 `None` 을 돌려주면 「연결 종료」로 읽혀 세션이 즉시 닫힌다
    (`_relay` 의 `FIRST_COMPLETED`). 그래서 어댑터 대본이 끝나는 쪽이 세션을 끝내게 매달린다.
    """

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def send_event(self, event: dict[str, object]) -> None:
        self.events.append(dict(event))

    async def receive_event(self) -> dict[str, object] | None:
        await asyncio.Event().wait()
        return None


def user_final(text: str) -> TranscriptEvent:
    return TranscriptEvent(kind="final", text=text, speaker="user")


async def leg(pool, name: str, script: list[AdapterEvent]) -> dict[str, object]:
    """한 다리 = 세션 하나. 세션 id · 프레임 · 보고 · DB 관측을 돌려준다."""
    session_id = await create_session(pool, FIXED_USER_ID, learning_source="additional")
    adapter = ScriptedAdapter(script)
    channel = RecordingChannel()
    runner = SessionRunner(adapter, pool, session_id, client=channel, drain_timeout=2.0)
    await runner.run()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select status, ended_at is not null as closed from learning_sessions where id = $1",
            session_id,
        )
        utterances = await conn.fetch(
            "select sequence_no, speaker, utterance_type, transcript from utterances"
            " where session_id = $1 order by sequence_no",
            session_id,
        )
    return {
        "leg": name,
        "session_id": str(session_id),
        "frames": [e for e in channel.events],
        "reports": adapter.reports,
        "adapter_closed": adapter.closed,
        "session_status": row["status"],
        "session_closed": row["closed"],
        "utterances": [dict(u) for u in utterances],
    }


async def paused_flag(pool, session_id: str) -> str | None:
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "select status from learning_sessions where id = $1", UUID(session_id)
        )


async def main() -> int:
    pool = await get_pool()
    results: list[dict[str, object]] = []
    try:
        # ── 1. next_question — 확인을 타지 않는 명령. 세션을 닫지 않는다.
        results.append(
            await leg(
                pool,
                "next_question",
                [
                    user_final("Hey, next question please."),
                    SessionCommandEvent(
                        command="next_question",
                        stage="requested",
                        heard="next question please",
                        tool_use_id="tu-nq",
                    ),
                    user_final("I usually go to gym after work."),
                ],
            )
        )

        # ── 2. show_report — 확인을 타지 않는 조회 명령.
        results.append(
            await leg(
                pool,
                "show_report",
                [
                    user_final("Hey, show me the weekly report."),
                    SessionCommandEvent(
                        command="show_report",
                        stage="requested",
                        heard="show me the weekly report",
                        tool_use_id="tu-sr",
                    ),
                ],
            )
        )

        # ── 3. pause → resume — DB 상태를 옮기는 한 쌍. 정지 중 발화가 저장되지 않아야 한다.
        pause_leg = await leg(
            pool,
            "pause_resume",
            [
                user_final("Hey, pause the session."),
                SessionCommandEvent(
                    command="pause", stage="requested", heard="pause", tool_use_id="tu-p"
                ),
                user_final("This line is spoken while paused."),
                user_final("Hey, resume the session."),
                SessionCommandEvent(
                    command="resume", stage="requested", heard="resume", tool_use_id="tu-r"
                ),
                user_final("This line is spoken after resuming."),
            ],
        )
        results.append(pause_leg)

        # ── 4. end — 확인을 거쳐야 하고 `confirmed` 에서만 닫힌다.
        results.append(
            await leg(
                pool,
                "end_confirmed",
                [
                    user_final("Hey, end the session."),
                    SessionCommandEvent(
                        command="end", stage="requested", heard="end the session",
                        tool_use_id="tu-e1",
                    ),
                    user_final("Yes, please."),
                    SessionCommandEvent(
                        command="end", stage="confirmed", heard="yes", tool_use_id="tu-e2"
                    ),
                    # ⛔ 이 뒤는 흐르지 않아야 한다 — 닫힌 세션에 발화가 더 붙으면 결함이다.
                    user_final("This must never be stored."),
                ],
            )
        )

        # ── 5. start_additional — 확인을 거쳐 닫고, `target` 을 화면에 넘긴다.
        results.append(
            await leg(
                pool,
                "start_additional_confirmed",
                [
                    user_final("Hey, switch to pronunciation practice."),
                    SessionCommandEvent(
                        command="start_additional",
                        stage="requested",
                        target="pronunciation",
                        heard="switch to pronunciation practice",
                        tool_use_id="tu-a1",
                    ),
                    user_final("Yes."),
                    SessionCommandEvent(
                        command="start_additional",
                        stage="confirmed",
                        target="pronunciation",
                        heard="yes",
                        tool_use_id="tu-a2",
                    ),
                ],
            )
        )

        # ── 6. 경계 ① — 표지가 없는 학습 발화 뒤의 명령은 실행되지 않아야 한다.
        results.append(
            await leg(
                pool,
                "boundary_no_marker",
                [
                    user_final("I want to end the meeting early tomorrow."),
                    SessionCommandEvent(
                        command="end",
                        stage="requested",
                        heard="end the meeting early",
                        tool_use_id="tu-b1",
                    ),
                    user_final("I usually go to office by subway."),
                ],
            )
        )

        # ── 7. 경계 ② — 앱 이름이 문장 가운데 오면 표지가 아니다(포함 검사 금지).
        results.append(
            await leg(
                pool,
                "boundary_marker_mid_sentence",
                [
                    user_final("I told my friend about Oh My English yesterday."),
                    SessionCommandEvent(
                        command="end", stage="requested", heard="oh my english", tool_use_id="tu-b2"
                    ),
                ],
            )
        )

        # ── 8. 경계 ③ — 물린 확인(`cancelled`)은 세션을 닫지 않는다.
        results.append(
            await leg(
                pool,
                "end_cancelled",
                [
                    user_final("Hey, end the session."),
                    SessionCommandEvent(
                        command="end", stage="requested", heard="end", tool_use_id="tu-c1"
                    ),
                    user_final("No, keep going."),
                    SessionCommandEvent(
                        command="end", stage="cancelled", heard="no", tool_use_id="tu-c2"
                    ),
                    user_final("I need to finish my homework tonight."),
                ],
            )
        )
    finally:
        await close_pool()

    out = Path(__file__).resolve().parent / "evidence" / "30-ts33-legs.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1, default=str))
    for leg_result in results:
        frames = [f.get("type") for f in leg_result["frames"]]
        print(f"\n== {leg_result['leg']} == session={leg_result['session_id']}")
        print(f"   status={leg_result['session_status']} closed={leg_result['session_closed']}")
        print(f"   frames={frames}")
        print(f"   reports={leg_result['reports']}")
        for u in leg_result["utterances"]:
            print(f"   utt #{u['sequence_no']} [{u['speaker']}/{u['utterance_type']}] {u['transcript']!r}")
    print(f"\nraw -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
