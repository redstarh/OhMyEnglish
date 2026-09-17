---
id: TASK-164
title: '구현 ③: services/videos.py · models/video.py — 여섯 함수와 DTO'
status: Done
assignee: []
created_date: '2026-09-17 17:16'
updated_date: '2026-09-17 17:31'
labels: []
dependencies:
  - TASK-162
ordinal: 225000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §4 를 이행한다. raw SQL · conn 을 첫 인자로 · 트랜잭션 경계는 호출자 소유. upsert 는 on conflict 로 한 문장에 담고 xmax=0 으로 created 를 준다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 여섯 함수를 만들었다 (list_videos · upsert_video · delete_video · load_video_with_phrases · add_phrase · delete_phrase)
- [x] #2 upsert_video 가 같은 영상을 다시 담을 때 행을 늘리지 않고 제목·채널·metadata_fetched_at 을 갱신하며 created=False 를 준다
- [x] #3 add_phrase 가 level 을 users.current_level 에서 같은 INSERT 안에 읽어 채운다
- [x] #4 add_phrase 가 source_url 을 watch?v= 형태로 정규화해 저장한다
- [x] #5 list_videos 가 문장 수와 metadata_stale(30일)을 함께 준다 — 시각 판정을 프론트에 두지 않는다
- [x] #6 delete_phrase 가 그 영상에 속하지 않는 문장 id 에는 실패한다
- [x] #7 tests/unit/test_videos_service.py 를 쓰고 통과한다 (영상 삭제 시 문장이 남는 것을 못 박는다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 이행 (2026-09-18)

- `app/backend/app/services/videos.py` — DTO 넷과 함수 여섯.
- `tests/unit/test_videos_service.py` — 단정 **10개**. red 를 먼저 확인했음(`ModuleNotFoundError`).

### ⚠️ 설계와 다르게 한 것 하나 — `models/video.py` 를 이 태스크에서 만들지 않았음

설계서 §0 이 `models/video.py` 를 이 자리에 뒀으나 **조회 결과 DTO 는 서비스 안에 두는 선례가
이미 있음** — `services/recordings.py` 의 `ShadowingClip`·`ShadowingTurns` 가 그것임.
⇒ DTO 넷(`VideoSummary`·`VideoPhrase`·`VideoDetail`·`UpsertedVideo`)을 `services/videos.py` 에 뒀음.
⇒ `models/video.py` 는 **요청 몸통 검증 모델**의 자리로 남기고 `TASK-165` 가 만듦. 그것이
「값역·DTO 는 `models/`」 관례와 맞음(요청 검증이 값역이고 조회 결과는 값역이 아님).

### 함수 여섯

| 함수 | 요점 |
|---|---|
| `list_videos` | `left join` 으로 문장 수를 함께 세고 `metadata_stale` 을 **서버가** 계산함 |
| `upsert_video` | `on conflict ... do update` 한 문장. `(xmax = 0)` 이 `created` 를 줌 |
| `delete_video` | `returning id` 로 존재 여부를 알려줌. 문장은 FK 가 남김 |
| `load_video_with_phrases` | 영상 하나 + 문장 전부. 없으면 `None` |
| `add_phrase` | `insert ... select` 로 영상 행과 `level` 을 **같은 문장에서** 읽음 |
| `delete_phrase` | `where id = $2 and youtube_video_id = $1` — 남의 영상 문장을 지우지 못함 |

### ⛔ 이 구현의 핵심 셋

1. **`add_phrase` 가 `insert ... select` 임** — 영상이 없으면 0행이 삽입되어 `None` 이 됨.
   「존재 확인 → 삽입」의 두 왕복이 필요 없고 그 사이에 영상이 지워지는 창도 없음.
   `level` 도 같은 문장에서 읽으므로 사용자가 없으면 NOT NULL 위반으로 실패함 — 조용히 기본값을
   만들지 않음.
2. **`(xmax = 0)`** 이 upsert 에서 삽입과 갱신을 가름. 그 값이 화면 문구를 가름.
3. **구간 상한(90초)을 서비스가 재지 않음** — 스키마 CHECK 둘이 이미 가두고 사용자 문구는 라우터가
   맡음. 세 곳에 흩지 않는 것이 판단임.

### 함정 하나 (내 테스트 쪽이었음)

`($2 || ' days')::interval` 로 일수를 넘겼더니 asyncpg 가 `expected str, got int` 로 거부했음.
⇒ `make_interval(days => $2)` 로 고쳤음. 서비스 SQL 은 처음부터 그 형태였고 **테스트만 틀렸음.**

### 게이트 (이 턴에 직접 돌린 출력)

`pytest` **1324 passed**(앞 차수 1314 + 새 10) · `ruff` 0 · `ruff format` 통과 · `ty` 0.
⚠️ `H-BW`(한글 E501)가 3곳 걸려 줄을 나눴음 — 이 세션에서 세 번째임.
<!-- SECTION:NOTES:END -->
