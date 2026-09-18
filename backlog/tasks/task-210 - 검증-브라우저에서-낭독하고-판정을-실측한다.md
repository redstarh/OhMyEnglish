---
id: TASK-210
title: '검증: 브라우저에서 낭독하고 판정을 실측한다'
status: To Do
assignee: []
created_date: '2026-09-18 05:54'
labels: []
dependencies:
  - TASK-209
ordinal: 271000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 전체. ⛔ localhost:3000 으로 열고 ?mode= 쿼리를 쓰지 않는다(H-CA·H-CC). ⛔ 회차 뒤 teardown_session.py 로 세션을 걷는다(TASK-193).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 일부러 한 낱말을 빼고 읽어 그 낱말이 빠짐으로 표시되는 것을 본다
- [ ] #2 두 번째 조회가 전사를 다시 하지 않는 것을 확인한다
- [ ] #3 회차 뒤 큐가 늘지 않은 것을 확인한다
<!-- AC:END -->
