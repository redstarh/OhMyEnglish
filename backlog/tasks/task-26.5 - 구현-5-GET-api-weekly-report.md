---
id: TASK-26.5
title: '구현 5: GET /api/weekly-report'
status: To Do
assignee: []
created_date: '2026-09-13 23:36'
labels: []
dependencies:
  - TASK-26.4
parent_task_id: TASK-26
ordinal: 164000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 5. daily.py 에 붙인다 — 그 라우터의 prefix 가 이미 /api 이고 성격이 같다. 행이 없으면 404 가 아니라 200 에 analyzed=false 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 단정 셋이 통과한다 — 200 의 필드 · 없을 때 빈 모양 · ⛔ jsonb 가 dict 로 나가는지(asyncpg 가 문자열로 준다)
<!-- AC:END -->
