---
id: TASK-170
title: 구간 담기가 HTTP 500 을 냄 — 반올림이 시작·끝을 같은 값으로 뭉개는 구간
status: Done
assignee: []
created_date: '2026-09-17 18:11'
updated_date: '2026-09-17 18:24'
labels: []
dependencies: []
ordinal: 231000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
현상: 두 시각의 차가 0.005초 미만이면 서버가 500 을 내고 사용자는 「구간 끝이 시작보다 뒤여야 해요」 대신 일반 실패 문구(UNAVAILABLE_NOTICE)를 봄.

재현 (3단계):
1. 영상을 담음 — POST /api/videos {url,title,channel_name}
2. 그 영상 id 로 POST /api/videos/<id>/phrases 에 {"transcript":"x","clip_start_sec":5.0,"clip_end_sec":5.001} 을 보냄
3. 응답이 500 Internal Server Error 임 (2/2 재현 · 간헐 아님)

기대: 422 + 「구간 끝이 시작보다 뒤여야 해요」 (설계서 docs/design/2026-09-18-video-learning-design.md §7 의 표)
실제: 500 Internal Server Error. 백엔드 로그에 asyncpg.exceptions.CheckViolationError: violates check constraint "shadowing_items_span_ordered" (Failing row 의 두 값이 5.00, 5.00)

기전: models/video.py PhraseCreateRequest 의 _span_is_ordered_and_bounded 가 **원본 값**으로 clip_end_sec > clip_start_sec 를 판정하고, 반올림은 그 뒤 services/videos.py add_phrase 가 함. 원본은 순서가 맞아도 둘째 자리로 접으면 같은 값이 되어 스키마 CHECK 가 잡음. 그 모듈 docstring 이 스스로 «스키마가 거부하면 사용자는 500 에 가까운 실패를 본다» 고 적어 둔 자리임.

사용자 도달 경로: app/frontend/app/videos/[videoId]/page.tsx 의 markEnd 가 at <= spanStart 만 봄(원본 float). 즉 [구간 시작]·[구간 끝] 을 재생 시각 5ms 미만 간격으로 누르면 프론트가 통과시키고 서버가 500 을 냄. API 를 직접 부르면 자명하게 재현됨. 화면에서의 도달은 좁지만 재생 속도 0.25배에서 넓어짐.

값역 상한(90초)에는 같은 구멍이 없음 — 반올림 이득의 최대가 0.01 이고 검증기가 원본 span <= 90 을 이미 요구하므로 접은 span 이 90 을 넘을 수 없음(실측: 0.004..90.0 · 0.0049..89.999 둘 다 0.00..90.00 로 저장되고 201).

증거: tests/agent/runs/2026-09-18-0303/evidence/TS-12-rounding-collapse.txt
HEAD: 29aeaeb
시나리오: TS-12 (테스트 원장 /Users/redstar/MyProject/OhMyEnglish/tests/agent)

제안: 반올림을 검증 «앞» 으로 옮기거나(모델이 접은 값으로 순서를 판정), 서비스가 접은 뒤 다시 판정해 422 로 번역함. 스키마 CHECK 는 그대로 둠 — 마지막 겹이 그것임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 clip_start_sec=5.0 · clip_end_sec=5.001 로 POST 하면 422 이고 응답 문구가 구간 순서 오류를 가리킨다
- [x] #2 접은 값이 같아지는 다른 조합(0.001..0.004 · 1.001..1.002 · 12.3401..12.3449)도 전부 422 다
- [x] #3 정상 구간(1.234..5.678)은 그대로 201 이고 1.23..5.68 로 저장된다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 고침 (2026-09-18)

### 근본 원인 — 검증이 «저장될 값» 을 보지 않았음

`PhraseCreateRequest` 의 `model_validator` 가 **원본 값**으로 순서를 판정하고 접기는 그 뒤
`services/videos.add_phrase` 가 했음. 원본이 `5.0 < 5.001` 이라 값역을 통과하는데 둘째 자리로 접으면
`5.00 == 5.00` 이 되어 스키마 CHECK 가 잡았고 사용자는 `500` 을 봤음.

### 고친 자리 넷

1. `models/video.py` — 접기를 **값역 층으로 올렸음.** `field_validator` 가 두 값을 먼저 접고
   `model_validator` 가 **접힌 값**으로 순서·상한을 판정함. 정밀도 상수 `CLIP_PRECISION` 이 그 파일로
   올라와 정본이 됨.
2. `services/videos.py` — 자기 `_CLIP_PRECISION` 을 버리고 그 정본을 import 함. 접기는 남겼으나
   ⚠️ **이제 「라우터 없이 불릴 때를 위한 이중 방어」로 위치가 바뀌었음**(주석에 그 사실을 적었음).
3. `api/videos.py` — 상세 응답에 **`clip_precision_sec`** 를 실었음. 화면이 접힌 값으로 비교하려면 그
   값이 필요하고, 화면이 자기 상수를 두면 상한과 같은 부류의 사본이 다시 생김.
4. `app/videos/[videoId]/page.tsx` — `markEnd` 가 **접은 값**으로 비교함. 그러지 않으면 화면이
   통과시킨 요청을 서버가 거부해 사용자가 일반 실패 문구를 봄.

### 실물 확인 — 재기동한 서버(pid 47873)에 직접 호출

| 입력 | 이전 | 지금 |
|---|---|---|
| `5.0 → 5.001` | **500** | **422** `clip_end_sec must be greater than clip_start_sec` |
| `0.001 → 0.004` | 500 | 422 |
| `1.001 → 1.002` | 500 | 422 |
| `12.3401 → 12.3449` | 500 | 422 |
| `1.234 → 5.678` (정상) | 201 | **201** · `1.23`~`5.68` 로 저장 |

⛔ **백엔드 로그의 `CheckViolationError`·`Traceback` 이 0건임** — 예외가 값역에서 막혀 아예 발생하지
않음. 「422 로 바뀜」보다 이것이 더 정확한 증거임.

### 화면에서도 확인했음 (브라우저로 직접)

같은 시각으로 [구간 시작]·[구간 끝] 을 눌러 `role=status` 에
**`"구간 끝이 시작보다 뒤여야 해요."`** 가 나오는 것을 관측했음 — 설계서 §7 이 약속한 문구임
(이전에는 일반 실패 문구를 봤을 자리). 콘솔 error·warn **0건**.

### 게이트 (이 턴에 직접 돌린 출력)

수집 **1343** · `pytest` **1343 passed** · `ruff` 0 · `ruff format` **291 files** · `ty` 0 ·
`tsc` 0 · `eslint` 0 · `next build` 0.

⚠️ 설계서 §1 질문 4 의 답을 **정정했음** — 「서비스가 반올림한다」가 이 결함을 만들었으므로 그 문장을
「값역 층이 접고 검증이 접힌 값을 본다」로 고치고 경위를 남겼음.
<!-- SECTION:NOTES:END -->
