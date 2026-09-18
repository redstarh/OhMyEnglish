---
id: TASK-184
title: '정리·검증: simplify 로 정리하고 게이트 여덟을 돌린다'
status: In Progress
assignee: []
created_date: '2026-09-18 01:40'
updated_date: '2026-09-18 02:03'
labels: []
dependencies:
  - TASK-183
ordinal: 245000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 「주요 개발이 끝나면 simplify 로 정리하면서 진행해」 · 「개발 뒤 테스트 필수」 의 이행이다. 게이트 수치로 브라우저 관측을 대체하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 /simplify 를 돌리고 지적된 것을 처리하거나 남기는 근거를 적는다
- [ ] #2 게이트 여덟이 전부 exit 0 이다 (pytest·ruff·ruff format·ty·tsc·eslint·next build)
<!-- AC:END -->
