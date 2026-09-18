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
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

HARNESS = Path(__file__).resolve().parent
REPO = HARNESS.parent.parent
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(REPO / "app" / "backend"))

from ws_session import read_lpcm  # noqa: E402

from app.audio_gateway.factory import create_voice_adapter, transcriber_available  # noqa: E402
from app.audio_gateway.port import VoiceAdapter  # noqa: E402
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
    """한 팔 = `transcribe_only` 값 하나.

    ⛔ **지시문을 담지 않는다** — 담으면 이 파일이 팩토리의 조립을 다시 구현하게 되고, A 팔이
    「`TASK-217` 전의 낭독 경로 그대로」라는 주장이 **아무것도 강제하지 않는 주석**이 된다.
    조립이 바뀌면 A 팔은 조용히 기준선이 아니게 되면서도 수치는 계속 보고한다.
    """

    key: str
    label: str
    transcribe_only: bool


ARMS = (
    Arm("A", "코치 지시문 + tool 스펙 (이전 판)", False),
    Arm("B", "전사 전용 지시문 · tool 스펙 없음", True),
)


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

    # ⛔ **어댑터를 직접 조립하지 않고 «팩토리» 를 부른다.** 그래야 A 팔이 제품의 낭독 경로와 같은
    #    지시문을 받는 것이 강제된다 — 손으로 조립하면 팩토리가 바뀌어도 이 파일은 조용히 옛 형태를
    #    계속 쓰고, 그러면 「두 팔이 프롬프트만 다르다」는 A/B 의 전제가 무너진다.
    # ⚠️ **대가**: 팩토리는 `settings.voice_adapter` 를 따르므로 설정이 스텁이면 스텁이 나온다.
    #    실물 비용을 태우는 드라이버이므로 위 `main_async` 가 착수 전에 그것을 거절한다.
    adapters: list[VoiceAdapter] = []

    def make_adapter() -> VoiceAdapter:
        adapter = create_voice_adapter(
            settings,
            questions=(),
            scenario=None,
            transcribe_only=arm.transcribe_only,
            usage_sink=sink,
        )
        adapters.append(adapter)
        return adapter

    text = await transcribe_readback(pcm, make_adapter=make_adapter)
    usage = seen[-1] if seen else None
    # 지시문 길이는 **어댑터가 실제로 받은 값**에서 읽는다 — 우리가 계산한 값을 적으면 팩토리가
    # 무엇을 실었는지가 아니라 우리 믿음을 보고하게 된다.
    instructions = getattr(adapters[-1], "instructions", "") if adapters else ""
    return {
        "arm": arm.key,
        "label": arm.label,
        "instruction_chars": len(instructions),
        "transcript": text,
        # `TokenUsage` 는 frozen dataclass 이므로 필드를 손으로 옮기지 않는다 — 옮기면 새 필드가
        # 이 보고에서 조용히 빠진다.
        "usage": None if usage is None else asdict(usage),
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
    # ⛔ **스텁 설정으로는 돌지 않는다.** 아래가 팩토리를 부르므로 설정이 스텁이면 스텁 어댑터가
    #    나오고, 그러면 **픽스처가 발명한 문장**이 전사문으로 보고돼 A/B 가 통째로 거짓이 된다.
    if not transcriber_available(get_settings()):
        raise SystemExit(
            f"VOICE_ADAPTER 가 {get_settings().voice_adapter!r} 다 — "
            "실물 A/B 는 nova 에서만 뜻이 있다"
        )
    # 픽스처 읽기는 하네스의 기존 헬퍼를 쓴다 — 같은 규격 검사를 세 번째로 복제하면 두 도구가 같은
    # 파일을 다르게 받아들일 여지가 생긴다(`ws_session.read_lpcm` 의 머리말이 그 근거를 가진다).
    pcm = read_lpcm(str(FIXTURE))
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
        arms = [arm for arm in ARMS if not args.only or arm.key == args.only]
        for index, arm in enumerate(arms):
            if index:
                # ⚠️ **팔 «사이» 만 띄운다** — 앞 회차의 스트림 정리가 뒤 회차의 연결과 겹치지 않게
                #    한다. 마지막 뒤에 두면 아무것도 기다리지 않는 1초를 버린다.
                await asyncio.sleep(1.0)
            result = await _run_arm(arm, pcm, pool)
            result["quality"] = _quality(clip, result["transcript"])
            report["arms"].append(result)
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
