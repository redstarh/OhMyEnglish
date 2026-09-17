---
id: TASK-164
title: '구현 ③: services/videos.py · models/video.py — 여섯 함수와 DTO'
status: To Do
assignee: []
created_date: '2026-09-17 17:16'
updated_date: '2026-09-17 17:17'
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
- [ ] #1 여섯 함수를 만들었다 (list_videos · upsert_video · delete_video · load_video_with_phrases · add_phrase · delete_phrase)
- [ ] #2 upsert_video 가 같은 영상을 다시 담을 때 행을 늘리지 않고 제목·채널·metadata_fetched_at 을 갱신하며 created=False 를 준다
- [ ] #3 add_phrase 가 level 을 users.current_level 에서 같은 INSERT 안에 읽어 채운다
- [ ] #4 add_phrase 가 source_url 을 watch?v= 형태로 정규화해 저장한다
- [ ] #5 list_videos 가 문장 수와 metadata_stale(30일)을 함께 준다 — 시각 판정을 프론트에 두지 않는다
- [ ] #6 delete_phrase 가 그 영상에 속하지 않는 문장 id 에는 실패한다
- [ ] #7 tests/unit/test_videos_service.py 를 쓰고 통과한다 (영상 삭제 시 문장이 남는 것을 못 박는다)
<!-- AC:END -->
