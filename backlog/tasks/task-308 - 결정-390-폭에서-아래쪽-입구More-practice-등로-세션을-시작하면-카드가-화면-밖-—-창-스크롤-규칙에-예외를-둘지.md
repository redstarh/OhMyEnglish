---
id: TASK-308
title: '결정: 390 폭에서 아래쪽 입구(More practice 등)로 세션을 시작하면 카드가 화면 밖 — 창 스크롤 규칙에 예외를 둘지'
status: Done
assignee: []
created_date: '2026-11-01 04:59'
updated_date: '2026-11-01 05:06'
labels: []
dependencies: []
ordinal: 373000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차 b13 r2 관찰 O1: 390 폭에서 More practice 의 Free talk 를 누르면 scrollY 1379 에서 세션이 맨 위 오늘의 연습 카드(화면 밖)에서 돎. TASK-305 의 사용자 지시 「Start speaking 때 스크롤이 움직이지 않게」를 지킨 결과임. 아래쪽 입구에서 시작할 때만 카드로 스크롤할지 사용자 판단이 필요함. 증거 tests/agent/runs/2026-11-01-b13/evidence/r2-390-freetalk-view.png
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자 결정을 받아 기록함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-01 사용자 결정(AskUserQuestion): 아래쪽 입구로 시작할 때만 카드가 화면 밖이면 카드로 스크롤함. 홈 Start speaking 은 그대로 움직이지 않음. 기록 docs/design/2026-11-01-v0-home-redesign-design.md §3 「아래쪽 입구의 스크롤 예외」. 구현은 후속 태스크.
<!-- SECTION:NOTES:END -->
