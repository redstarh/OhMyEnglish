---
id: TASK-334
title: '리뷰: TASK-333·332 변경(d8adcef..ba83fec)의 codex 리뷰를 받아 반영함'
status: Done
assignee: []
created_date: '2026-11-14 14:11'
updated_date: '2026-11-14 14:16'
labels: []
dependencies: []
ordinal: 401000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codex 리뷰 결과를 받음
- [x] #2 CRITICAL·HIGH 를 고치거나 근거를 들어 반박함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
codex 리뷰: MEDIUM 3 · CRITICAL·HIGH 0 — 코드로 셋 다 확인 · 셋 다 고침(실패 시험 먼저 4개 실패 → 통과): ① saidNothing — 학습 발화 없는 날은 요약이 있어도 실수 0이면 Nothing said(실수가 잡히면 그 사실) ② restartHref — 다시 열 수 있는 모드(speaking·pronunciation·shadowing·scenario_intake)만 · 그 밖은 홈 ③ source user_requested 를 옮김 · 모르는 출처는 홈. node 전체 · tsc 0 · eslint 0 · next build 0 · pytest 통과.
<!-- SECTION:NOTES:END -->
