---
id: TASK-335
title: '홈 This week: N / 7 days 가 학습 발화 없는 날도 셈 — 연속 학습일과 같은 기준으로 (사용자 지시 2026-11-15)'
status: Done
assignee: []
created_date: '2026-11-14 16:22'
updated_date: '2026-11-14 16:30'
labels: []
dependencies: []
ordinal: 402000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차 b18 이후 남은 관찰 1. 연속 학습일·기록 Nothing said 는 학습 발화(utterance_type=learning)가 있는 세션만 셈(TASK-333). 홈 This week 만 다른 기준이라 같은 화면에서 어긋남.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 실패 시험 먼저
- [x] #2 This week 가 학습 발화 있는 날만 셈
- [x] #3 실제 화면 확인
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
구현(opus 에이전트) · 내가 직접 재실행: tsc 0 · eslint 0 · next build 0 · node 55/55. 실패 시험 먼저(learned 2 ≠ 1). learnedInLastWeek 가 learned && spoken !== false 만 셈. 실데이터 This week 0/7(11-14 는 학습 발화 없음) · 가짜 기록 1/7.
<!-- SECTION:NOTES:END -->
