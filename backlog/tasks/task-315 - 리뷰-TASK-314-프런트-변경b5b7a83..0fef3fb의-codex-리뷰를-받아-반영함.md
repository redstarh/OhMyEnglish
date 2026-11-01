---
id: TASK-315
title: '리뷰: TASK-314 프런트 변경(b5b7a83..0fef3fb)의 codex 리뷰를 받아 반영함'
status: Done
assignee: []
created_date: '2026-11-01 06:43'
updated_date: '2026-11-01 06:46'
labels: []
dependencies: []
ordinal: 380000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codex 리뷰 결과를 받음
- [x] #2 CRITICAL·HIGH 를 고치거나 근거를 들어 반박함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
codex 리뷰 수신: MEDIUM 1 — 현재 Day 로 연 연습(practiceDay 없음)에서 Day 를 마치면 reloadCourse 뒤 강조 줄이 다음 Day 로 옮고 카드는 마친 Day 를 보여 어긋남. 코드로 확인함(selectedDay = practiceDay ?? current_day). CRITICAL·HIGH 0.

수용·고침: 현재 Day 로 열 때(Start speaking · Grammar course) 연 순간의 current_day 를 practiceDay 에 넣음 · selectedDay 는 practiceDay 만 봄. 회차 b15 start-1400.json · grammar-390.json: 카드 Day 1 = 강조 path-day-1 · 닫으면 강조 없음. Day 를 마치는 경로 자체는 dev DB 를 바꾸므로 실물로 재지 않았음(코드로 확인). tsc 0 · eslint 0 · next build 0 · 하네스 112 passed.
<!-- SECTION:NOTES:END -->
