---
id: TASK-26.3
title: '구현 3: 사실 모으기 — metrics'
status: To Do
assignee: []
created_date: '2026-09-13 23:35'
labels: []
dependencies:
  - TASK-26.1
parent_task_id: TASK-26
ordinal: 162000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 3. 주 경계를 [week_start, +7) 반열림으로 쓴다. ⛔ between 을 쓰지 않는다 — 끝을 포함해 다음 주 월요일이 들어온다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 단정 넷이 통과한다 — 주 밖 배제 · 상위 정렬과 동수 가름 · 0건 주 · 다른 사용자 배제
- [ ] #2 반열림을 between 으로 바꿔 red 를 보고 되돌린다
<!-- AC:END -->
