---
id: TASK-319
title: >-
  결함: 문장 연습을 여는 순간 카드가 줄어 1400×900 에서 Start speaking 이 창 스크롤을 0 으로 옮김 (회차 b16 버튼
  D1)
status: Done
assignee: []
created_date: '2026-11-14 06:31'
updated_date: '2026-11-14 08:57'
labels: []
dependencies: []
ordinal: 386000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
재현(내가 직접 · tests/agent/runs/2026-11-14-b16/verify/d1.mjs): 1400×900 scrollY 40 → Start speaking → 0. 원인: 연습 상태 카드는 높이가 없어(TASK-310) HomeCoursePractice 로딩 중 433→335px(390 은 489→126px)로 줄고, 문서 높이 952→창 높이 아래로 내려가 스크롤이 클램프됨. 규칙 위반: TASK-305·308 「Start speaking 은 창을 움직이지 않음」.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 d1.mjs 가 고치기 전 실패함을 기록함
- [x] #2 연습 로딩 중에도 카드가 줄지 않게 고침
- [x] #3 d1.mjs 세 경우 모두 scrollY 유지 · 카드 최소 높이 = 대기 높이
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
고치기 전(내가 직접 · 앱 HEAD a5ac4bf 기준 프런트): 1400x900 docH=952 scrollY 40→0 heroMin=335 · 1400x700 200→200 heroMin=335 · 390x844 120→120 heroMin=126. 고치기는 회차 b16 화면 탭이 끝난 뒤.

고침: 연습 상태 카드에 HERO_MIN_HEIGHT(대기와 같은 최저 높이). 고친 뒤(내가 직접 · d1.mjs · 사용자 스택): 1400x900 40→40 heroMin 434 · 1400x700 200→200 · 390x844 120→120 heroMin 490. tsc 0 · eslint 0.
<!-- SECTION:NOTES:END -->
