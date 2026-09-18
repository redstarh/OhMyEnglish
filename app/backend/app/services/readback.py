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
from typing import TypeGuard
from uuid import UUID

import asyncpg

from app.audio_gateway.port import TranscriptEvent, VoiceAdapter
from app.services.recordings import (
    RECORDING_BYTES_PER_SAMPLE,
    RECORDING_SAMPLE_RATE_HZ,
    load_recording,
)

MATCH = "match"
MISSING = "missing"
DIFFERENT = "different"


# 한 프레임의 크기 — 저장된 녹음 규격(`services/recordings.py`)에서 끌어낸 100ms 다.
# ⛔ **소켓 계층의 프레임과 같지 않다.** 그쪽은 1024바이트(32ms · `lib/audio.ts` 의
# `FRAME_BYTES`)이고 그 값은 «실시간» 지연을 위한 것이다(`audio_gateway/session.py` 가 근거를
# 가진다). 여기는 이미 끝난 파일을 흘리므로 지연이 아니라 호출 수가 문제이고 100ms 가 그 균형이다.
# ⚠️ 상수를 손으로 적지 않는 이유: 녹음 표본율이 바뀌면 이 값이 조용히 다른 길이가 된다.
_FRAME_BYTES = RECORDING_SAMPLE_RATE_HZ * RECORDING_BYTES_PER_SAMPLE // 10
# 전사가 오지 않는 어댑터에서 엔드포인트가 영원히 열리지 않게 하는 상한.
_TIMEOUT_S = 30.0
# 오디오 끝에 붙이는 침묵. 16kHz·16bit 기준 2초다.
# ⛔ **이것이 없으면 실물 Nova 가 전사를 «아예» 주지 않는다** (2026-09-18 실측 · `TASK-210`):
# 같은 오디오가 침묵 없이는 빈 문자열이었고 2초를 붙이자 전사가 왔다. VAD 가 침묵으로 발화를 닫는다.
# ⚠️ 파일은 학습자가 「읽기 끝」을 누른 순간 끊기므로 **실사용 입력에 침묵이 없다** — 그래서 이 값이
# 선택이 아니라 필수다.
_TRAILING_SILENCE_BYTES = RECORDING_SAMPLE_RATE_HZ * RECORDING_BYTES_PER_SAMPLE * 2
# 마지막 학습자 final 뒤로 이만큼 조용하면 낭독이 끝난 것으로 본다 (`TASK-210`).
# ⚠️ 실물은 끊어 읽는 자리마다 final 을 내므로 문장 사이 숨보다 길어야 한다.
_QUIET_AFTER_FINAL_S = 3.0


async def _send_all(adapter: VoiceAdapter, pcm: bytes, frame_bytes: int) -> None:
    for offset in range(0, len(pcm), frame_bytes):
        await adapter.send_audio(pcm[offset : offset + frame_bytes])


def _is_user_final(event: object) -> TypeGuard[TranscriptEvent]:
    """학습자의 확정 전사문인가.

    ⛔ agent 것을 받지 않는다 — 어댑터가 대화형이라 코치의 전사문과 오디오가 함께 오는데
    낭독 판정에 필요한 것은 학습자가 낸 소리뿐이다. 코치 응답은 버린다.
    """
    return isinstance(event, TranscriptEvent) and event.kind == "final" and event.speaker == "user"


async def _user_finals(adapter: VoiceAdapter, quiet_s: float) -> str:
    """학습자의 final 전사문을 **조용해질 때까지 모아** 이어 붙인다.

    ⛔ **첫 final 하나만 받으면 여섯 문장 클립의 판정이 통째로 틀린다**(2026-09-18 실측 ·
    `TASK-210`). 실물 Nova 는 끊어 읽는 자리마다 final 을 내므로 저장된 전사가 **첫 두 문장뿐**
    이었고 학습자가 «읽은» 32낱말이 화면에서 「빠짐」으로 표시됐다.

    ⛔ **조용함은 「마지막 학습자 final 뒤로 흐른 시간」으로 잰다** — 「아무 이벤트도 오지 않음」
    으로 재면 안 된다. 낭독이 끝나면 코치가 말하기 시작해 오디오 이벤트가 계속 오므로 그
    기준으로는 영원히 조용해지지 않는다.
    ⚠️ 첫 final 이 오기 전에는 기다림에 상한을 두지 않는다 — 바깥 `transcribe_readback` 의 상한이
    그 구간을 덮는다(두 곳에서 각자 재면 어느 쪽이 끝냈는지 알 수 없다).
    """
    loop = asyncio.get_running_loop()
    parts: list[str] = []
    deadline = 0.0
    iterator = adapter.events().__aiter__()
    while True:
        timeout = max(0.0, deadline - loop.time()) if parts else None
        try:
            event = await asyncio.wait_for(iterator.__anext__(), timeout)
        except (TimeoutError, StopAsyncIteration):
            break
        if _is_user_final(event):
            parts.append(event.text)
            deadline = loop.time() + quiet_s
    return " ".join(parts).strip()


async def transcribe_readback(
    pcm: bytes,
    *,
    make_adapter: Callable[[], VoiceAdapter],
    frame_bytes: int = _FRAME_BYTES,
    timeout_s: float = _TIMEOUT_S,
    silence_bytes: int = _TRAILING_SILENCE_BYTES,
    quiet_s: float = _QUIET_AFTER_FINAL_S,
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
        return await asyncio.wait_for(
            _readback_text(adapter, padded, frame_bytes, quiet_s), timeout_s
        )
    except TimeoutError:
        # 어댑터가 조용한 것은 결함이 아니라 갈래 하나다 — 빈 전사로 알린다.
        return ""
    finally:
        await adapter.close()


async def _readback_text(
    adapter: VoiceAdapter, pcm: bytes, frame_bytes: int, quiet_s: float
) -> str:
    await adapter.start()
    await _send_all(adapter, pcm, frame_bytes)
    return await _user_finals(adapter, quiet_s)


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
    pool: asyncpg.Pool,
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

    ⛔ **연결이 아니라 풀을 받는다** (`TASK-212`) — 전사는 최대 `_TIMEOUT_S` 초이고 그 안에서
    사용량 기록이 풀에서 연결을 또 잡는다. 연결을 잡은 채 그 구간을 타면 한 판정이 풀의 두 자리를
    30초 넘게 묶는다. 그래서 **읽기 → 반납 → 전사 → 다시 잡아 쓰기**로 나눈다.
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(_READBACK_ROW_SQL, utterance_id, session_id)
        if row is None:
            return None
        clip_transcript: str = row["transcript"]
        readback: str | None = row["readback_transcript"]
        pcm = (
            None
            if readback is not None
            else await load_recording(conn, root, session_id, utterance_id)
        )
    if readback is None:
        if pcm is None:
            return None
        readback = await transcribe_readback(pcm, make_adapter=make_adapter)
        if not readback:
            return ReadbackJudgment(
                clip_transcript=clip_transcript, readback_transcript="", words=[]
            )
        async with pool.acquire() as conn:
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


def _words(text: str) -> list[tuple[str, str]]:
    """`(원래 모양, 견줄 형태)` 짝의 목록.

    부호만 있는 토큰(줄표·홑따옴표 따위)은 견줄 형태가 비므로 버린다 — 판정할 낱말이 아니다.
    ⚠️ **짝으로 돌려주는 것이 계약이다** — 두 리스트를 나란히 돌려주면 길이가 어긋날 자리가 생긴다.
    """
    pairs = ((token, _NOT_WORD.sub("", token.lower())) for token in text.split())
    return [(token, key) for token, key in pairs if key]


def compare_readback(expected: str, spoken: str) -> list[WordVerdict]:
    """클립의 글 `expected` 를 낭독 전사문 `spoken` 과 견주어 낱말마다 판정한다."""
    pairs = _words(expected)
    want = [key for _, key in pairs]
    got = [key for _, key in _words(spoken)]
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
        WordVerdict(word=token, verdict=verdict)
        for (token, _), verdict in zip(pairs, verdicts, strict=True)
    ]
