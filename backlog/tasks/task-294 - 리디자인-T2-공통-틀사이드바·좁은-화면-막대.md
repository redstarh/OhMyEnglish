---
id: TASK-294
title: '리디자인 T2: 공통 틀(사이드바·좁은 화면 막대)'
status: Done
assignee: []
created_date: '2026-10-31 19:05'
updated_date: '2026-10-31 19:18'
labels: []
dependencies:
  - TASK-293
ordinal: 359000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계: docs/design/2026-11-01-v0-home-redesign-design.md §3. components/app-shell.tsx 를 layout 에 둠.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 넓은 화면 모든 경로에 사이드바가 있고 활성 항목이 대응표와 맞음
- [x] #2 390px 폭에서 위쪽 막대 4개가 보이고 가로 스크롤이 없음
- [x] #3 tsc · eslint 통과
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
내가 재확인: tsc 0 · lint 오류 0 · 홈 DOM 의 nav-* testid · /course 스크린샷에서 Practice 활성. 390px 가로 넘침 없음은 에이전트의 CDP 측정(페이지 폭 390). 각 nav testid 가 사이드바·위쪽 막대 두 번 나옴 — 시험은 보이는 쪽을 골라야 함.
<!-- SECTION:NOTES:END -->
