---
id: TASK-162
title: '구현 ①: 027 마이그레이션 — youtube_videos 표와 shadowing_items.youtube_video_id'
status: In Progress
assignee: []
created_date: '2026-09-17 17:16'
updated_date: '2026-09-17 17:18'
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
- [ ] #1 db/migrations/027_*.sql 을 썼다 (머리 주석 블록 포함 · 번호는 그 턴에 최대값을 다시 확인해 받았다)
- [ ] #2 youtube_videos 에 CHECK 넷을 걸었다 (11자 형태 · 제목 공백 · 채널 공백 · youtube_id unique)
- [ ] #3 shadowing_items 에 youtube_video_id 를 on delete set null 로 더하고 CHECK 하나(영상이면 source_url 필수)를 걸었다
- [ ] #4 user_id 컬럼과 thumbnail_url 컬럼을 두지 않았다 (설계서 §2 의 근거)
- [ ] #5 dev DB 에 적용하고 information_schema 조회로 확인했다 (current_schema() 를 걸었다)
- [ ] #6 tests/unit/test_schema.py 에 pg_get_constraintdef 대조 단정을 더했고 통과한다
<!-- AC:END -->
