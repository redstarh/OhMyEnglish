---
id: TASK-66.5
title: '구현 5: 엔드포인트 GET /api/shadowing/clips/{item_id}/audio'
status: To Do
assignee: []
created_date: '2026-09-13 22:11'
labels: []
dependencies:
  - TASK-66.4
parent_task_id: TASK-66
ordinal: 153000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 5. 세션 경로 밖에 둔다 — 클립은 여러 세션이 공유하는 제품 자산이라 세션 경계를 쓰지 않는다. StaticFiles 를 쓰지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 API 단정 넷이 통과한다 — 200 바이트·Content-Type · 404 셋 · 경로 모양 거부
- [ ] #2 라우터 등록을 지워 red 를 보고 되돌린다
<!-- AC:END -->
