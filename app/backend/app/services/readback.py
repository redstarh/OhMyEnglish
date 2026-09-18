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
import wave
from collections.abc import Callable
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from app.audio_gateway.port import TranscriptEvent, VoiceAdapter

MATCH = "match"
MISSING = "missing"
DIFFERENT = "different"


# 한 프레임의 크기. 16kHz·16bit 기준 100ms 다 — 소켓 계층이 브라우저에서 받는 크기와 같은 자리수로
# 두어 어댑터가 다른 리듬을 보지 않게 한다.
_FRAME_BYTES = 3200
# 전사가 오지 않는 어댑터에서 엔드포인트가 영원히 열리지 않게 하는 상한.
_TIMEOUT_S = 30.0


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
    path: Path,
    *,
    make_adapter: Callable[[], VoiceAdapter],
    frame_bytes: int = _FRAME_BYTES,
    timeout_s: float = _TIMEOUT_S,
) -> str:
    """저장된 낭독 WAV 를 어댑터에 흘려 **학습자의 final 전사문 하나**만 돌려준다.

    얻지 못하면 빈 문자열이다 — 호출자는 그때 판정을 만들지 않는다(설계서 §4).

    ⛔ **되돌리는 조건의 경계가 이 함수다.** 배치 STT 로 옮기기로 하면(결정 131) 여기만 갈면 되고
    호출자는 그대로 둔다. 그래서 어댑터를 인자로 «만들어» 받는다.

    ⚠️ **실물 Nova 로 확인되지 않은 것 둘** — `TASK-210` 이 그것을 본다:
    ① 프레임을 다 보낸 «뒤» 이벤트를 읽는 순서가 흐름 제어에 걸리지 않는지(스텁에서는 걸리지 않고,
       이 순서라야 보낸 프레임 수가 결정적이다).
    ② 파일이 갑자기 끝나도 Nova 가 final 을 내는지 — VAD 가 침묵으로 판정을 닫으므로 끝에 침묵을
       덧붙여야 할 수 있다. **필요하다는 증거가 나온 뒤에 붙인다**(지금 붙이면 근거 없는 코드다).
    """
    with wave.open(str(path), "rb") as wav:
        pcm = wav.readframes(wav.getnframes())
    adapter = make_adapter()
    try:
        return await asyncio.wait_for(_readback_text(adapter, pcm, frame_bytes), timeout_s)
    except TimeoutError:
        # 어댑터가 조용한 것은 결함이 아니라 갈래 하나다 — 빈 전사로 알린다.
        return ""
    finally:
        await adapter.close()


async def _readback_text(adapter: VoiceAdapter, pcm: bytes, frame_bytes: int) -> str:
    await adapter.start()
    await _send_all(adapter, pcm, frame_bytes)
    return await _first_user_final(adapter)


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
