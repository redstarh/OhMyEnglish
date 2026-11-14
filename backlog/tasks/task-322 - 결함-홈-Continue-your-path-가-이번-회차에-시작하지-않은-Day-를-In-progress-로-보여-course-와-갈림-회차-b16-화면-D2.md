---
id: TASK-322
title: >-
  결함: 홈 Continue your path 가 이번 회차에 시작하지 않은 Day 를 In progress 로 보여 /course 와 갈림
  (회차 b16 화면 D2)
status: To Do
assignee: []
created_date: '2026-11-14 06:33'
labels: []
dependencies: []
ordinal: 389000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
재현(내가 직접 · 격리 DB cycle 3): 홈 path-day-2~5 data-status=started · /course 는 Day 2~5 Not started. 원인: components/home/dashboardData.ts dayStatus 가 progress 행이 있으면 started(지난 cycle 행 포함) · app/course/page.tsx 는 시작 위치를 벗어나야 진행 중. Your progress 는 0/6 days 라 같은 화면에서도 모순.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 실패 재현을 먼저 남김
- [ ] #2 두 화면이 같은 판정 함수를 씀
- [ ] #3 같은 응답에서 Day 마다 상태가 같음
<!-- AC:END -->
