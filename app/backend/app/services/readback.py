"""낭독 전사문을 클립의 글과 견준다 — 낭독 판정의 계산 (`TASK-207`).

설계: `docs/design/2026-09-18-read-aloud-judgment-design.md` §4.

⛔ **모델을 부르지 않는다.** 「원본대로 읽었는가」는 낱말 일치로 답이 정해지므로 모델 판단이 필요
없고, 순수 함수라 같은 입력에 같은 답이 난다 — 화면 안내가 그 성질에 걸린다.

⚠️ **판정은 「기대한」 낱말마다 난다.** 학습자가 없는 낱말을 «더» 말한 경우(`insert`)는 판정할 기대
낱말이 없어 세지 않는다 — 값역이 셋(맞음·빠짐·다름)이고 넷째 갈래를 넣으려면 값역부터 넓힌다.

⚠️ **알려진 한계 — 되풀이가 심한 글에서는 정렬이 모호하다.** 같은 문장을 서른 번 이어 붙인
270낱말 입력에서 낱말 하나를 빼면 `difflib` 이 «똑같이 긴 다른 정렬»을 골라 99낱말을 빠짐으로
낸다(2026-09-18 직접 관측). 쉐도잉 클립은 한 문장이므로 이 형태가 실제로 오지 않아 받아들였다 —
긴 글을 판정 대상으로 넓히려면 정렬을 문장 단위로 먼저 자르는 것이 선행한다.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from uuid import UUID

import asyncpg

from app.audio_gateway.port import TranscriptEvent, VoiceAdapter
from app.services.recordings import load_recording

MATCH = "match"
MISSING = "missing"
DIFFERENT = "different"


# 한 프레임의 크기. 16kHz·16bit 기준 100ms 다 — 소켓 계층이 브라우저에서 받는 크기와 같은 자리수로
# 두어 어댑터가 다른 리듬을 보지 않게 한다.
_FRAME_BYTES = 3200
# 전사가 오지 않는 어댑터에서 엔드포인트가 영원히 열리지 않게 하는 상한.
_TIMEOUT_S = 30.0
# 오디오 끝에 붙이는 침묵. 16kHz·16bit 기준 2초다.
# ⛔ **이것이 없으면 실물 Nova 가 전사를 «아예» 주지 않는다** (2026-09-18 실측 · `TASK-210`):
# 같은 오디오가 침묵 없이는 빈 문자열이었고 2초를 붙이자 전사가 왔다. VAD 가 침묵으로 발화를 닫는다.
# ⚠️ 파일은 학습자가 「읽기 끝」을 누른 순간 끊기므로 **실사용 입력에 침묵이 없다** — 그래서 이 값이
# 선택이 아니라 필수다.
_TRAILING_SILENCE_BYTES = 16_000 * 2 * 2


async def _send_all(adapter: VoiceAdapter, pcm: bytes, frame_bytes: int) -> None:
    for offset in range(0, len(pcm), frame_bytes):
        await adapter.send_audio(pcm[offset : offset + frame_bytes])


async def _first_user_final(adapter: VoiceAdapter) -> str:
    async for event in adapter.events():
        # ⛔ agent 것을 받지 않는다 — 어댑터가 대화형이라 코치의 전사문과 오디오가 함께 오는데
        #    낭독 판정에 필요한 것은 학습자가 낸 소리뿐이다. 코치 응답은 버린다.
        if isinstance(event, TranscriptEvent) and event.kind == "final" and event.speaker == "user":
            return event.text
    return ""


async def transcribe_readback(
    pcm: bytes,
    *,
    make_adapter: Callable[[], VoiceAdapter],
    frame_bytes: int = _FRAME_BYTES,
    timeout_s: float = _TIMEOUT_S,
    silence_bytes: int = _TRAILING_SILENCE_BYTES,
) -> str:
    """낭독 녹음의 **PCM** 을 어댑터에 흘려 학습자의 final 전사문 하나만 돌려준다.

    얻지 못하면 빈 문자열이다 — 호출자는 그때 판정을 만들지 않는다(설계서 §4).

    ⛔ **경로가 아니라 PCM 을 받는다** (2026-09-18 정정 · `TASK-206` 의 AC 는 「WAV 경로」였다).
    이유: 녹음 접근의 규칙(만료·세션 생존·포인터만 남은 상태)을 `services/recordings.load_recording`
    이 소유하고 그 함수가 **헤더 없는 PCM** 을 돌려준다. 경로를 받으면 호출자가 경로를 다시 조립해
    그 규칙을 건너뛰게 되고, 그것이 이 리포가 *"두 곳에서 각자 계산하면 갈라진다"* 로 금지한 형태다.

    ⛔ **되돌리는 조건의 경계가 이 함수다.** 배치 STT 로 옮기기로 하면(결정 131) 여기만 갈면 되고
    호출자는 그대로 둔다. 그래서 어댑터를 인자로 «만들어» 받는다.

    **실물 Nova 로 확인했다** (2026-09-18 · `TASK-210`):
    ① 프레임을 다 보낸 «뒤» 이벤트를 읽는 순서가 흐름 제어에 걸리지 «않는다» — 실물에서 그 순서로
       전사를 받았다. 이 순서라야 보낸 프레임 수가 결정적이다.
    ② **끝에 침묵을 붙여야 한다**(`_TRAILING_SILENCE_BYTES`) — 침묵 없이 보낸 같은 오디오는
       전사가 빈 문자열이었다.
    ⚠️ **전사기가 낱말을 합치면 판정이 틀린 쪽으로 기운다**: 실물이 `All right` 을 `alright` 로 내서
    두 낱말이 「다름」으로 잡혔다. 낱말 단위 대조의 알려진 한계이고 학습자에게 불리한 방향이다.
    """
    adapter = make_adapter()
    padded = pcm + b"\x00" * silence_bytes
    try:
        return await asyncio.wait_for(_readback_text(adapter, padded, frame_bytes), timeout_s)
    except TimeoutError:
        # 어댑터가 조용한 것은 결함이 아니라 갈래 하나다 — 빈 전사로 알린다.
        return ""
    finally:
        await adapter.close()


async def _readback_text(adapter: VoiceAdapter, pcm: bytes, frame_bytes: int) -> str:
    await adapter.start()
    await _send_all(adapter, pcm, frame_bytes)
    return await _first_user_final(adapter)


@dataclass(frozen=True)
class ReadbackJudgment:
    """낭독 하나에 대한 판정. `words` 가 비면 **전사를 얻지 못했다**는 뜻이다(설계서 §4)."""

    clip_transcript: str
    readback_transcript: str
    words: list[WordVerdict]


_READBACK_ROW_SQL = """
select transcript, readback_transcript
  from utterances
 where id = $1 and session_id = $2 and utterance_type = 'shadowing_recording'
"""


async def judge_readback(
    conn: asyncpg.Connection,
    root: Path,
    session_id: UUID,
    utterance_id: UUID,
    *,
    make_adapter: Callable[[], VoiceAdapter],
) -> ReadbackJudgment | None:
    """낭독 하나를 클립의 글과 견준다. 접근할 수 없으면 `None` — 호출자가 404 로 옮긴다.

    ⛔ **요청할 때 계산하고 한 번만 계산한다** (결정 131). 전사가 이미 있으면 어댑터를 아예 만들지
    않으므로 두 번째 조회에 비용이 0 이다.
    ⛔ **세션과 발화 종류가 «둘 다» 조회 조건이다.** 세션은 개인정보 경계이고
    (`api/shadowing.py` 머리말) 종류는 「견줄 원본이 있는가」다 — 일반 발화의 `transcript` 는
    클립의 글이 아니라 학습자의 말이라 견주면 뜻이 없는 판정이 나온다.
    ⚠️ 종류 필터는 **둘째 겹**이다 — `utterances_audio_only_for_shadowing` 이 낭독이 아닌 발화에
    포인터 자체를 못 붙이게 한다.
    ⛔ **빈 전사를 저장하지 않는다** — 저장하면 다시 눌러도 영원히 빈 판정이 돌아온다. 저장하지
    않으면 학습자가 다시 눌러 볼 수 있고, 그때 비용은 실패한 회수만큼만 난다.
    """
    row = await conn.fetchrow(_READBACK_ROW_SQL, utterance_id, session_id)
    if row is None:
        return None
    clip_transcript: str = row["transcript"]
    readback: str | None = row["readback_transcript"]
    if readback is None:
        pcm = await load_recording(conn, root, session_id, utterance_id)
        if pcm is None:
            return None
        readback = await transcribe_readback(pcm, make_adapter=make_adapter)
        if not readback:
            return ReadbackJudgment(
                clip_transcript=clip_transcript, readback_transcript="", words=[]
            )
        await conn.execute(
            "update utterances set readback_transcript = $2 where id = $1",
            utterance_id,
            readback,
        )
    return ReadbackJudgment(
        clip_transcript=clip_transcript,
        readback_transcript=readback,
        words=compare_readback(clip_transcript, readback),
    )


# 견줄 때만 쓰는 형태 — 대소문자와 문장부호 차이를 오류로 세지 않기 위해 지운다.
# ⚠️ 홑따옴표도 지운다: `Don't` 와 `dont` 는 같은 낱말을 읽은 것이고 전사기가 어느 쪽으로 낼지
#    우리가 정하지 못한다.
_NOT_WORD = re.compile(r"[^0-9a-z]+")


@dataclass(frozen=True)
class WordVerdict:
    """기대한 낱말 하나에 대한 판정. `word` 는 원본의 «원래 모양»이다(화면이 그것을 보인다)."""

    word: str
    verdict: str


def _words(text: str) -> tuple[list[str], list[str]]:
    """원래 모양과 견줄 형태를 같은 순서로 짝지어 돌려준다.

    부호만 있는 토큰(줄표·홑따옴표 따위)은 견줄 형태가 비므로 버린다 — 판정할 낱말이 아니다.
    """
    originals: list[str] = []
    normalized: list[str] = []
    for token in text.split():
        key = _NOT_WORD.sub("", token.lower())
        if not key:
            continue
        originals.append(token)
        normalized.append(key)
    return originals, normalized


def compare_readback(expected: str, spoken: str) -> list[WordVerdict]:
    """클립의 글 `expected` 를 낭독 전사문 `spoken` 과 견주어 낱말마다 판정한다."""
    originals, want = _words(expected)
    _, got = _words(spoken)
    # 기본값이 「빠짐」이다 — `delete` 갈래와 낭독이 아예 빈 경우가 그대로 여기에 남는다.
    verdicts = [MISSING] * len(want)
    # ⛔ `autojunk=False` 를 명시한다 — 기본값은 b 가 200 항목을 넘으면 «자주 나오는 항목»을
    #    자동으로 버려서 긴 전사문에서 판정이 길이에 따라 달라진다(같은 입력에 같은 답이라는
    #    성질이 깨진다).
    matcher = SequenceMatcher(a=want, b=got, autojunk=False)
    for tag, start, stop, _b_start, _b_stop in matcher.get_opcodes():
        if tag == "equal":
            fill = MATCH
        elif tag == "replace":
            fill = DIFFERENT
        else:
            continue
        for index in range(start, stop):
            verdicts[index] = fill
    return [
        WordVerdict(word=word, verdict=verdict)
        for word, verdict in zip(originals, verdicts, strict=True)
    ]
