---
id: TASK-41
title: '검토: 우리 표를 public → 전용 스키마로 이관 (En-Coach 비대칭 해소)'
status: To Do
assignee: []
created_date: '2026-09-07 17:51'
labels: []
dependencies: []
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md E절에서 이관. En-Coach는 전용 스키마(en_coach)를 쓰는데 우리 표는 public에 있어 비대칭이다 — 남의 search_path 폴백이 우리 표로 떨어질 수 있다. 우리 SQL이 전부 한정자 없이 쓰여 있어 범위가 커서 미뤄 왔다. 근거: docs/ops/shared-database-naming-rules.md §5.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 전용 스키마 이관의 영향 범위(한정자 없는 SQL 전수)를 조사한다
- [ ] #2 이관 여부와 시점을 캡틴 결정으로 확정한다
<!-- AC:END -->
