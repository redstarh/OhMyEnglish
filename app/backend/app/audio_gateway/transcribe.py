"""낭독 녹음을 **대화형 어댑터로** 전사한다 — `port.Transcriber` 의 구현 (`TASK-214`).

설계: `docs/design/2026-09-18-read-aloud-judgment-design.md` §4-2 · 결정 131.

⛔ **이 모듈이 있는 이유는 경계다.** 낭독 판정(`services/readback.py`)이 아는 것은 좁은
`Transcriber` 뿐이고, 「대화형 어댑터를 열어 프레임을 흘리고 학습자의 final 을 모은다」는 방법은
여기가 통째로 소유한다. 결정 131 이 약속한 *"배치 STT 로 옮기면 전사 함수 하나만 갈면 된다"* 의
「하나」가 이 모듈이다 — 그때 갈리는 것은 여기이고 판정·라우터·화면은 그대로다.

⛔ **침묵·조용함·프레임 크기·어댑터 수명 넷이 여기 모여 있다.** 넷 다 「전사기를 대화형 어댑터로
만들 때만」 필요한 값이고, 판정 쪽 계약에 실으면 배치 STT 로 갈 때 뜻 없는 인자로 남는다.

⛔ **스텁으로 검증된다** — `tests/unit/test_readback_transcribe.py` 가 프레임 수·닫힘·상한을
고정한다. 실물로만 드러난 성질 둘은 그 파일의 단정이 코드에 못 박아 두었다(아래 실측 참조).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TypeGuard

from app.audio_gateway.port import TranscriptEvent, VoiceAdapter
from app.services.recordings import (
    RECORDING_BYTES_PER_SAMPLE,
    RECORDING_SAMPLE_RATE_HZ,
)

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
    호출자는 그대로 둔다 — 호출자가 보는 것은 `port.Transcriber` 뿐이다. 그래서 어댑터를 인자로
    «만들어» 받는다.

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
