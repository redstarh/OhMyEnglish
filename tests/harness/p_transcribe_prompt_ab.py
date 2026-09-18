"""전사 전용 프롬프트의 A/B — 같은 픽스처를 두 프롬프트로 전사한다 (`TASK-217`).

설계: `docs/design/2026-09-18-read-aloud-judgment-design.md` §6.

⛔ **왜 브라우저를 태우지 않는가.** 재는 것은 「프롬프트를 줄였을 때 전사 품질이 유지되는가」이고
그 답은 `transcribe_readback` 한 함수에서 난다 — 브라우저 레그(`p_readback_leg.py`)를 태우면
마이크 대체·hydration·판정 화면이 변수로 끼어들어 **두 팔의 차이가 프롬프트 때문인지** 가릴 수
없다. 같은 PCM 을 같은 함수에 두 번 흘리는 것이 이 질문의 가장 좁은 관측이다.

⛔ **실물 Bedrock 을 부른다 — 비용이 난다.** Nova 양방향 스트림 **두 회차**이고 각 회차가
픽스처 약 15초를 흘린다. ⚠️ **`llm_calls` 에 행이 둘 남는다** — 실제로 쓴 비용이므로 적는 것이
맞다(`services/usage.py` 의 *"이 비용은 복원할 수 없다"*).

⛔ **SigV4 가 필요하다.** 셸에는 bearer 만 있고 SigV4 두 키는 `app/backend/.env` 에만 있다 —
`config.prepare_bedrock_credentials` 가 그 쌍을 환경에 올리고 bearer 를 닫는다. 그 함수가 도는지는
어댑터가 스트림을 열 때 판정되고, 자격증명 실패는 **예외가 아니라 무응답**으로 드러난다.

쓰는 법:

    cd app/backend && env -u AWS_BEARER_TOKEN_BEDROCK ./.venv/bin/python \\
      ../../tests/harness/p_transcribe_prompt_ab.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HARNESS = Path(__file__).resolve().parent
REPO = HARNESS.parent.parent
sys.path.insert(0, str(REPO / "app" / "backend"))

from app.audio_gateway.nova import (  # noqa: E402
    TRANSCRIPTION_ONLY_PROMPT,
    NovaVoiceAdapter,
    build_system_prompt,
)
from app.audio_gateway.transcribe import transcribe_readback  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import close_pool  # noqa: E402
from app.db import pool as get_db_pool  # noqa: E402
from app.models.usage import TokenUsage  # noqa: E402
from app.services.readback import compare_readback  # noqa: E402
from app.services.usage import pool_usage_sink  # noqa: E402

# 시드 클립의 id. ⛔ **글은 복제하지 않고 DB 에서 읽는다**(`_clip_transcript`) — 여기 적어 두면
# `scripts/migrate.py` 의 시드와 갈라지고, 그러면 판정이 조용히 뜻을 잃는다.
CLIP_ID = "00000000-0000-0000-0000-000000000201"
FIXTURE = REPO / "app" / "frontend" / "public" / "harness" / "readback.wav"


@dataclass(frozen=True)
class Arm:
    """한 팔 = 지시문 하나 + 봉투 하나."""

    key: str
    label: str
    instructions: str
    transcribe_only: bool


def _arms() -> list[Arm]:
    settings = get_settings()
    # A 팔은 **`TASK-217` 전의 낭독 경로 그대로**다 — 팩토리가 빈 재료로 코치 지시문을 조립했다.
    baseline = build_system_prompt(
        (),
        None,
        (),
        None,
        scenario_intake=False,
        drill_count=settings.drill_count,
        drill_turns_min=settings.drill_turns_min,
    )
    return [
        Arm("A", "코치 지시문 + tool 스펙 (이전 판)", baseline, False),
        Arm("B", "전사 전용 지시문 · tool 스펙 없음", TRANSCRIPTION_ONLY_PROMPT, True),
    ]


def _load_pcm(path: Path) -> bytes:
    """픽스처를 헤더 없는 PCM 으로 읽는다 — 저장된 녹음과 같은 규격이어야 한다."""
    with wave.open(str(path), "rb") as wav:
        if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (1, 2, 16_000):
            raise SystemExit(
                f"픽스처 규격이 다르다: 채널 {wav.getnchannels()} · "
                f"표본폭 {wav.getsampwidth()} · 표본율 {wav.getframerate()}"
            )
        return wav.readframes(wav.getnframes())


async def _clip_transcript(conn: Any) -> str:
    """견줄 원본을 **DB 에서** 읽는다 — 스크립트에 글을 복제하지 않는다."""
    text = await conn.fetchval(
        "select transcript from shadowing_items where id = $1::uuid", CLIP_ID
    )
    if not text:
        raise SystemExit(f"시드 클립 {CLIP_ID} 가 DB 에 없다 — migrate.py 를 먼저 돌린다")
    return str(text)


async def _run_arm(arm: Arm, pcm: bytes, pool: Any) -> dict[str, Any]:
    """한 팔을 실물로 태우고 전사문과 사용량을 돌려준다."""
    settings = get_settings()
    seen: list[TokenUsage] = []
    record = pool_usage_sink(pool)

    async def sink(usage: TokenUsage, **kwargs: Any) -> None:
        # ⛔ **행도 적고 값도 잡는다** — 행은 실제 비용의 정본이고, 값은 팔을 가려 보고하기 위한
        #    것이다(같은 `purpose='nova'` 로 두 행이 남아 SQL 로는 팔을 못 가른다).
        seen.append(usage)
        await record(usage, **kwargs)

    def make_adapter() -> NovaVoiceAdapter:
        return NovaVoiceAdapter(
            settings,
            instructions=arm.instructions,
            usage_sink=sink,
            transcribe_only=arm.transcribe_only,
        )

    text = await transcribe_readback(pcm, make_adapter=make_adapter)
    usage = seen[-1] if seen else None
    return {
        "arm": arm.key,
        "label": arm.label,
        "instruction_chars": len(arm.instructions),
        "transcript": text,
        "usage": None
        if usage is None
        else {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "input_speech_tokens": usage.input_speech_tokens,
            "input_text_tokens": usage.input_text_tokens,
            "output_speech_tokens": usage.output_speech_tokens,
            "output_text_tokens": usage.output_text_tokens,
        },
    }


def _quality(clip: str, spoken: str) -> dict[str, Any]:
    """전사 품질 = 그 전사로 낸 **낱말 판정**이다 — 전사문 문자열 비교가 아니다.

    ⚠️ 두 팔의 전사문이 낱말 하나 다른 것은 흔하고, 그것이 **판정을 바꾸는지**가 우리가 재는 것이다.
    """
    verdicts = compare_readback(clip, spoken)
    counts: dict[str, int] = {}
    for verdict in verdicts:
        counts[verdict.verdict] = counts.get(verdict.verdict, 0) + 1
    return {"words": len(verdicts), "counts": counts}


async def main_async(args: argparse.Namespace) -> int:
    pcm = _load_pcm(FIXTURE)
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            clip = await _clip_transcript(conn)
        report: dict[str, Any] = {
            "fixture": str(FIXTURE.relative_to(REPO)),
            "pcm_bytes": len(pcm),
            "clip_words": len(clip.split()),
            "arms": [],
        }
        for arm in _arms():
            if args.only and arm.key != args.only:
                continue
            result = await _run_arm(arm, pcm, pool)
            result["quality"] = _quality(clip, result["transcript"])
            report["arms"].append(result)
            # ⚠️ **팔 사이를 띄운다** — 앞 회차의 스트림 정리가 뒤 회차의 연결과 겹치지 않게 한다.
            await asyncio.sleep(1.0)
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return 0
    finally:
        await close_pool()


def main() -> int:
    ap = argparse.ArgumentParser(description="전사 전용 프롬프트 A/B (TASK-217 · 실물 비용 발생)")
    ap.add_argument("--only", choices=("A", "B"), help="한 팔만 태운다")
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
