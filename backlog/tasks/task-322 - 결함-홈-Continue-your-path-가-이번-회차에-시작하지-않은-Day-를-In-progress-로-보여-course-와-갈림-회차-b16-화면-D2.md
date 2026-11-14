---
id: TASK-322
title: >-
  결함: 홈 Continue your path 가 이번 회차에 시작하지 않은 Day 를 In progress 로 보여 /course 와 갈림
  (회차 b16 화면 D2)
status: Done
assignee: []
created_date: '2026-11-14 06:33'
updated_date: '2026-11-14 09:00'
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
- [x] #1 실패 재현을 먼저 남김
- [x] #2 두 화면이 같은 판정 함수를 씀
- [x] #3 같은 응답에서 Day 마다 상태가 같음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
실패 시험 먼저: app/frontend/components/home/dashboardData.test.mts(node --test) — 고치기 전 1 실패(지난 회차 완료 · 시작 위치 Day 가 started) · 3 통과. 고침: dashboardData.dayStarted 하나로 모으고 홈 dayStatus · /course DayRow 가 함께 씀. 고친 뒤 4 통과. 실제 화면(사용자 스택 · verify/screens.mjs): 홈 D1 started · D2~6 new = /course D1 진행 · D2~6 Not started. tsconfig exclude **/*.test.mts(.ts 확장자 가져오기). tsc 0 · eslint 0 · next build 0.
<!-- SECTION:NOTES:END -->
