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

RECORDING_SAMPLE_RATE_HZ = 16_000
RECORDING_BYTES_PER_SAMPLE = 2
RECORDING_CHANNELS = 1
