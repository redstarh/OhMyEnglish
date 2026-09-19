"""학습자 낭독 녹음의 **저장 형식** — 두 층이 함께 읽는 사실 (`TASK-221`).

**왜 `models/` 인가**: `services/sessions.py` 가 적어 둔 의존 방향이 *"`audio_gateway/factory.py`·
`nova.py` 가 `app.models` 만 알고 `app.services` 가 그 값을 채운다"* 다. 이 셋은 **거동이 아니라
형식 데이터**이고(DB 도 세션도 모른다) 어댑터 층과 서비스 층이 **둘 다** 읽으므로, 서비스에 두면
그 방향이 뒤집힌다.

⛔ **실제로 뒤집혀 있었고 계측으로 드러났다** (2026-09-19): `TASK-214` 가 신설한
`audio_gateway/transcribe.py` 가 이 값을 `services/recordings` 에서 가져왔고, `factory.py` 가 그
모듈을 import 하므로 **팩토리를 import 하는 것만으로** `app.services` 다섯 모듈과 `asyncpg` 가 함께
올라왔다(이전에는 0개·안 올라옴). 직접 import 는 0건이라 눈으로는 안 보였다 — 전이였다.

⛔ **`audio_gateway/nova.py` 의 `SAMPLE_RATE_HZ` 와 합치지 않는다.** 값이 같아도 뜻이 다르다:
그쪽은 「Nova 입력 규격」이고 이쪽은 「학습자 낭독의 저장 형식」이다. 한 상수로 묶으면 한쪽이 바뀔
때 다른 쪽이 함께 끌려간다 — 이 갈림은 `services/recordings.py` 가 먼저 정해 둔 것이고 옮기면서
뒤집지 않는다.

⚠️ **프론트 `lib/audio.ts` 의 값과도 짝이다** — 그쪽은 소켓으로 흘리는 프레임의 규격이고 언어가
달라 공유할 수단이 없다. 갈라지면 저장된 파일이 재생되지 않는다.
"""

from __future__ import annotations

import io
import wave

RECORDING_SAMPLE_RATE_HZ = 16_000
RECORDING_BYTES_PER_SAMPLE = 2
RECORDING_CHANNELS = 1


def wav_from_pcm(
    pcm: bytes,
    *,
    sample_rate_hz: int = RECORDING_SAMPLE_RATE_HZ,
    bytes_per_sample: int = RECORDING_BYTES_PER_SAMPLE,
    channels: int = RECORDING_CHANNELS,
) -> bytes:
    """raw PCM 에 RIFF 헤더를 얹는다 — **바이트를 새로 만들고 원본은 건드리지 않는다.**

    표준 `wave` 로 쓰는 것이 헤더를 손으로 조립하는 것보다 낫다: 청크 길이·바이트율·정렬을 직접
    계산하면 한 자리만 틀려도 브라우저가 **조용히** 재생을 거부한다.
    ⛔ **손 조립판이 실재했다** (`TASK-226`): `audio_gateway/fixtures.py` 가 `struct.pack` 으로
    44바이트를 직접 쌓고 있었고 출력은 이 함수와 **바이트 단위로 같았다**(6,444바이트). 두 벌로
    두면 규격이 바뀔 때 한쪽만 고쳐지고, 그 결과는 「재생이 안 된다」 하나로만 보인다.

    ⚠️ **규격을 인자로 받는 것이 이 자리의 조건이다.** 저장 녹음은 위 세 상수를 쓰고 스텁 톤은
    자기 규격(16kHz·16bit·mono 이지만 **뜻이 다른** 「스텁 전용 포맷」)을 쓴다 — 기본값으로 묶고
    인자로 열어 두면 두 뜻이 한 함수를 공유하면서도 서로를 끌고 가지 않는다.

    ⚠️ **페이로드를 두 번 복사하는 것을 알고 둔다** (2026-09-18 `/simplify` 가 지적했고 유지로
    판정했음): `writeframes` 가 `BytesIO` 로 한 번, `getvalue()` 가 `bytes` 로 또 한 번 복사한다.
    ⛔ **줄이는 길은 44바이트 헤더를 손으로 조립하는 것뿐이고 그것이 위 단락이 피한 위험이다.**
    `setnframes` 로 헤더만 뽑는 중간 길은 성립하지 않는다 — `wave.close()` 가 `_patchheader()` 로
    data 길이를 실제 쓴 양(0)으로 되돌린다. 재생은 학습자가 버튼을 누를 때 한 번이고, 같은 경로의
    동기 파일 읽기(`services/recordings.load_recording`)가 이미 같은 크기를 의도로 감수한다.

    ⚠️ **프레임이 0인 낭독도 유효한 WAV 로 나간다** — 핸들은 열렸고 프레임이 오지 않은 턴이
    실재하고(`audio_gateway/session.py`), 그때 터뜨리면 학습자가 500 을 본다.
    """
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(bytes_per_sample)
        wav.setframerate(sample_rate_hz)
        wav.writeframes(pcm)
    return buffer.getvalue()
