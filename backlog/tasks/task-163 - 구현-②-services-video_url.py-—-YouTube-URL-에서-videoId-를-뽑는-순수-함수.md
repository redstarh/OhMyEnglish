---
id: TASK-163
title: '구현 ②: services/video_url.py — YouTube URL 에서 videoId 를 뽑는 순수 함수'
status: To Do
assignee: []
created_date: '2026-09-17 17:16'
labels: []
dependencies: []
ordinal: 224000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §4 의 parse_youtube_id 를 만든다. DB 를 쓰지 않으므로 ① 과 병행할 수 있다. 형태 넷을 다루고 도메인을 확인한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 parse_youtube_id(url) -> str | None 을 만들었다
- [ ] #2 형태 넷(watch?v= · youtu.be/ · shorts/ · embed/)을 다 뽑는다
- [ ] #3 질의 문자열이 붙어도 뽑는다 (&t=42s)
- [ ] #4 11자 형태가 아니면 None 을 준다
- [ ] #5 ⛔ YouTube 도메인이 아니면 None 을 준다 — 아무 URL 에서 조각을 뽑지 않는다
- [ ] #6 tests/unit/test_video_url.py 를 쓰고 통과한다
<!-- AC:END -->
