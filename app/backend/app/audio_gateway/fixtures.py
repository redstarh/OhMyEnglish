"""공통 픽스처 데이터 — **단일 소유자** (AC 문서 §공통 픽스처).

스텁 재생, 테스트 픽스처(`tests/conftest.py`), 통합 테스트가 모두 이 모듈을
import한다. 같은 문장을 여러 곳에 적어두면 한쪽만 고쳐졌을 때 "스텁이 재생한
문장"과 "테스트가 기대한 문장"이 조용히 갈라지고, 그때 깨지는 것은 픽스처가 아니라
분석 결과에 대한 단정이다 — 그래서 상수의 소유자를 하나로 못 박는다.

1·2번 응답은 같은 오류 유형(관사 누락)을 서로 다른 문장에 담고 있다. "같은 오류는
하나의 패턴으로 병합"(tests/README.md:9)을 관측할 수 있는 최소 데이터라 이 조합
자체가 계약이다.
"""

from __future__ import annotations

import math
import struct

# (agent 질문, 사용자 응답)
FIXTURE_TURNS: list[tuple[str, str]] = [
    ("What do you usually do after work?", "I usually go to gym after work."),
    ("What do you usually do on weekends?", "I usually go to office by subway."),
    ("What do you need to do tonight?", "I need to finish my homework tonight."),
]

# 스텁이 흘리는 오디오 응답 프레임의 규격 — **스텁 전용 포맷**이다.
# 16kHz·16bit·mono PCM은 스텁이 스스로 정한 값이고, Nova Sonic의 실제 출력 형식은
# Phase 2에서 실측해 확정한다(포트는 `bytes`만 약속하므로 포맷은 계약이 아니다).
_SAMPLE_RATE_HZ = 16_000
_BITS_PER_SAMPLE = 16
_CHANNELS = 1
# 사람이 "소리가 났다"를 귀로 판정할 수 있는 최소 길이 + 음높이. 무음이면 프론트엔드
# 재생 경로가 조용히 망가져도 알 수 없어(볼륨 0, 디코드 실패, 라우팅 오류가 모두
# 같은 결과) 들리는 톤을 발행한다. 440Hz = A4, 진폭은 클리핑을 피해 30%로 둔다.
_FRAME_MILLISECONDS = 200
_TONE_HZ = 440
_TONE_AMPLITUDE = 0.3


def _tone_wav(
    *,
    sample_rate: int = _SAMPLE_RATE_HZ,
    milliseconds: int = _FRAME_MILLISECONDS,
    frequency: int = _TONE_HZ,
) -> bytes:
    """헤더가 유효한 짧은 사인파 톤 WAV. 클라이언트가 실제로 디코딩·재생할 수 있는
    바이트여야 base64 릴레이 경로를 귀로 끝까지 확인할 수 있다."""
    block_align = _CHANNELS * _BITS_PER_SAMPLE // 8
    samples = sample_rate * milliseconds // 1000
    peak = int(_TONE_AMPLITUDE * 32767)
    body = b"".join(
        struct.pack("<h", int(peak * math.sin(2 * math.pi * frequency * index / sample_rate)))
        for index in range(samples)
    )
    fmt_chunk = b"fmt " + struct.pack(
        "<IHHIIHH",
        16,  # fmt 청크 길이 (PCM)
        1,  # PCM
        _CHANNELS,
        sample_rate,
        sample_rate * block_align,  # byte rate
        block_align,
        _BITS_PER_SAMPLE,
    )
    data_chunk = b"data" + struct.pack("<I", len(body)) + body
    riff_size = 4 + len(fmt_chunk) + len(data_chunk)
    return b"RIFF" + struct.pack("<I", riff_size) + b"WAVE" + fmt_chunk + data_chunk


# 고정 오디오 프레임 — 턴마다 같은 바이트를 흘린다. import 시 한 번 계산하고
# 재사용하므로(사전 계산 상수) 턴마다 사인파를 다시 만들지 않으며, 내용이 고정이라
# 클라이언트가 받은 base64를 이 상수와 그대로 비교할 수 있다.
TONE_WAV_FRAME: bytes = _tone_wav()
