---
id: TASK-162
title: '구현 ①: 027 마이그레이션 — youtube_videos 표와 shadowing_items.youtube_video_id'
status: Done
assignee: []
created_date: '2026-09-17 17:16'
updated_date: '2026-09-17 17:23'
labels: []
dependencies: []
ordinal: 223000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 2026-09-18-video-learning-design.md §2 를 이행한다. 표 하나와 컬럼 하나, CHECK 다섯을 더한다. 기존 컬럼·CHECK 를 바꾸지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 db/migrations/027_*.sql 을 썼다 (머리 주석 블록 포함 · 번호는 그 턴에 최대값을 다시 확인해 받았다)
- [x] #2 youtube_videos 에 CHECK 넷을 걸었다 (11자 형태 · 제목 공백 · 채널 공백 · youtube_id unique)
- [x] #3 shadowing_items 에 youtube_video_id 를 on delete set null 로 더하고 CHECK 하나(영상이면 source_url 필수)를 걸었다
- [x] #4 user_id 컬럼과 thumbnail_url 컬럼을 두지 않았다 (설계서 §2 의 근거)
- [x] #5 dev DB 에 적용하고 information_schema 조회로 확인했다 (current_schema() 를 걸었다)
- [x] #6 tests/unit/test_schema.py 에 pg_get_constraintdef 대조 단정을 더했고 통과한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 이행 (2026-09-18)

파일: `db/migrations/027_youtube_videos.sql`

### 만든 것

- 표 `youtube_videos` — 컬럼 6개(`id`·`youtube_id`·`title`·`channel_name`·`metadata_fetched_at`·
  `created_at`) 전부 NOT NULL. CHECK 넷(11자 형태 · 제목 공백 · 채널 공백 · `youtube_id` unique).
- `shadowing_items.youtube_video_id uuid references youtube_videos(id) on delete set null`.
- 부분 인덱스 `shadowing_items_youtube_video_id_idx` (`where youtube_video_id is not null`) —
  FK 는 자동 인덱스를 만들지 않고 이 컬럼으로 「그 영상의 문장 목록」과 「영상별 문장 수」를 조회함.
- CHECK `shadowing_items_video_requires_source_url`.

### ⛔ 이 마이그레이션이 정책 방어를 **새로 만들지 않은 것**이 핵심임

`youtube_video_id` 가 있으면 `source_url` 이 필수이므로, 기존
`shadowing_items_audio_only_for_synthetic`(`audio_filename is null or source_url is null`)이
**오디오 저장을 자동으로 막음.** 즉 YouTube Developer Policies III.E.1 을 기존 방어가 지킴.
테스트 `test_a_shadowing_item_from_a_video_cannot_carry_audio` 가 그것을 못 박음.

### dev DB 적용 — 직접 조회한 출력

```
 schema_migrations 마지막
 027_youtube_videos.sql   | 2026-09-17 17:21:44.352001+00
 026_dedicated_schema.sql | 2026-09-17 00:37:09.211313+00
```

`information_schema` 조회에 **`current_schema()` 를 걸었음**(`H-BX` — `public` 에 동명 호환 뷰가
있으면 두 스키마 행이 섞이고 뷰는 모든 컬럼을 nullable 로 보고함). 결과: 컬럼 6개 전부
`is_nullable = NO` · `shadowing_items.youtube_video_id` 1행 · CHECK 넷을 `pg_get_constraintdef` 로
확인함.

### 테스트

`tests/unit/test_schema.py` 에 단정 7개를 더했고 그 앞에 **red 를 확인했음**
(7건 다 `relation "youtube_videos" does not exist`).

⚠️ **회귀 1건을 만들고 고쳤음**: `test_001_migration_creates_expected_tables` 가 표 이름 집합을
**정확히** 비교하므로 새 표가 그 집합에 들어와야 함. 그 테스트의 주석이 「새 표는 반드시 여기 들어와야
한다」로 미리 지목해 둔 자리이고 red 로 즉시 드러났음.

⚠️ **함정 하나를 다시 밟았음**: `db_conn` 은 테스트마다 트랜잭션 하나를 열어 두므로 CHECK 위반을
여러 번 내려면 각각을 **중첩 `transaction()`(savepoint)** 으로 감싸야 함. 감싸지 않아
`InFailedSQLTransactionError` 로 2건이 죽었고, 같은 파일의
`test_drill_turns_expected_is_nullable_and_rejects_non_positive` 주석이 그 함정을 이미 적어 뒀음.

### 게이트 (이 턴에 직접 돌린 출력)

`pytest` **1301 passed**(기존 1294 + 새 7) · `ruff` 0 · `ruff format` **273 files** · `ty` 0.
<!-- SECTION:NOTES:END -->
