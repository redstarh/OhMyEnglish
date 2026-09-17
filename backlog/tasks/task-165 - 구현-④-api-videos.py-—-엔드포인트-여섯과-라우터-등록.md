---
id: TASK-165
title: '구현 ④: api/videos.py — 엔드포인트 여섯과 라우터 등록'
status: To Do
assignee: []
created_date: '2026-09-17 17:16'
updated_date: '2026-09-17 17:17'
labels: []
dependencies:
  - TASK-163
  - TASK-164
ordinal: 226000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §3 을 이행한다. api/shadowing.py 의 계보를 베낀다. 값역은 서버가 소유하고 실패는 422·404 로 낸다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 APIRouter(prefix=/api/videos) 로 엔드포인트 여섯을 만들었다
- [ ] #2 create_app() 에 include_router 를 더했다
- [ ] #3 video_id·item_id 를 UUID 로 받는다 (경로 탈출 방어)
- [ ] #4 값역을 서버가 검사한다 (url 파싱 · 제목 200자 · 문장 1000자 · 구간 90초 · 0<=start<end)
- [ ] #5 구간 초를 서버가 소수 둘째 자리로 반올림한다
- [ ] #6 GET /api/videos/{id} 가 영상과 문장 목록을 함께 준다 (왕복을 하나로)
- [ ] #7 tests/integration/test_videos_api.py 를 쓰고 통과한다 — ⛔ 외부 호출이 0건이다
<!-- AC:END -->
