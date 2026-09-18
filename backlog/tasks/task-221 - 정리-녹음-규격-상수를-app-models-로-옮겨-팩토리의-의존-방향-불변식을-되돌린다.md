---
id: TASK-221
title: '정리: 녹음 규격 상수를 app/models 로 옮겨 팩토리의 의존 방향 불변식을 되돌린다'
status: Done
assignee: []
created_date: '2026-09-18 19:56'
updated_date: '2026-09-18 23:36'
labels: []
dependencies: []
ordinal: 282000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
codex 품질 리뷰의 altitude 지적 3(2026-09-19 · LOW). services/sessions.py 가 「audio_gateway/factory.py·nova.py 가 app.models 만 알고 app.services 가 그 값을 채우는 기존 방향」을 불변식으로 적어 두었는데, TASK-214 가 신설한 audio_gateway/transcribe.py 가 app.services.recordings 에서 RECORDING_SAMPLE_RATE_HZ·RECORDING_BYTES_PER_SAMPLE·RECORDING_CHANNELS 를 가져오고 factory.py 가 transcribe 를 import 하므로 그 불변식이 전이로 깨졌다. 셋은 서비스 거동이 아니라 형식 데이터이므로 app/models 로 옮기고 services/recordings 가 그쪽에서 읽게 한다. ⚠️ audio_gateway/session.py 는 이미 services 를 자유롭게 import 하므로 패키지 전체가 순수했던 적은 없다 — 깨진 것은 factory·nova 로 좁힌 불변식 하나다. 그래서 LOW 이고 별 작업으로 뺐다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 녹음 규격 상수 셋이 app/models 에 있고 services/recordings 가 그쪽에서 읽는다
- [x] #2 audio_gateway/transcribe.py 가 app.services 를 import 하지 않는다
- [x] #3 게이트 여덟이 통과한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 2026-09-19 — 옮김. 구조는 최소로 잡았음

**만든 것**: `app/models/recording.py` 하나(상수 셋 + 머리말). `app/models` 의 관례가 「한 사실을
담는 작은 모듈」이고(`models/session.py` 가 그 전례) 기존 모듈 어디도 오디오 저장 형식의 자리가
아니었음.

**안 한 것 셋** — 구조를 늘리지 않으려고 뺐음:
- `services/recordings` 에서 **재수출하지 않음**(`__all__` 도 두지 않음). 이 파일 밖에서 그 상수를
  쓰는 곳이 `transcribe.py` 하나뿐이고 그쪽이 정본에서 바로 가져가므로 중간 다리가 불필요함.
- `nova.SAMPLE_RATE_HZ` 와 **합치지 않음.** 값이 같아도 뜻이 다르고(Nova 입력 규격 대 낭독 저장
  형식) 그 갈림은 `services/recordings` 가 먼저 정해 둔 것임.
- 프레임·침묵 크기를 호출자가 주입하게 바꾸지 않음 — 정책이 위로 올라감.

**곁들여 고친 것**: `_TRAILING_SILENCE_BYTES` 에도 채널 항이 빠져 있었음(`TASK-220` 이 잡은 것과
같은 누락). 둘을 `_RECORDING_BYTES_PER_SECOND` 하나에서 갈리게 해 그 형태의 누락이 다시 나올
자리를 없앴음.

## 계측 (이 턴에 직접 돌림)

`app.audio_gateway.factory` 를 import 했을 때 함께 올라오는 것:

| | `app.services` 모듈 | `asyncpg` |
|---|---|---|
| `TASK-214` 이전 의존만 | 없음 | 안 올라옴 |
| 고치기 전(= `TASK-214`~`220`) | **다섯** (`services`·`jobs`·`recordings`·`scenario_rotation`·`sessions`) | **올라옴** |
| 고친 뒤 | 없음 | 안 올라옴 |

⇒ 변경 전 상태로 정확히 되돌아왔음.

**단정을 신설했음**: `test_factory_does_not_reach_the_services_layer_even_transitively`.
⛔ `imported_names`(AST) 로는 이 불변식을 못 지킴 — 실제 위반이 **전이**였고 직접 import 는 0건이라
그 단정은 통과했음. 그래서 **별 인터프리터**에서 `sys.modules` 를 읽음(같은 프로세스는 앞선 테스트가
서비스를 이미 올려 둬 답할 수 없음). 판별력 확인: import 를 되돌리자 그 다섯을 이름까지 지목하며 FAIL.

게이트 여덟: `pytest` **1400 passed** · `ruff` 0 · `format` **305 files** · `ty` 0 · `tsc` 0 ·
`eslint` 0 · `next build` 0.
<!-- SECTION:NOTES:END -->
