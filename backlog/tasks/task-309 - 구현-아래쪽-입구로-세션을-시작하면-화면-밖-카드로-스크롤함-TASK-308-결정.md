---
id: TASK-309
title: '구현: 아래쪽 입구로 세션을 시작하면 화면 밖 카드로 스크롤함 (TASK-308 결정)'
status: Done
assignee: []
created_date: '2026-11-01 05:06'
updated_date: '2026-11-01 05:57'
labels: []
dependencies: []
ordinal: 374000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 docs/design/2026-11-01-v0-home-redesign-design.md §3 「아래쪽 입구의 스크롤 예외」. 홈 Start speaking 은 창을 움직이지 않음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 아래쪽 입구로 시작하고 카드가 화면 밖이면 카드로 스크롤함
- [x] #2 Start speaking 과 카드가 이미 보이는 경우는 창이 움직이지 않음
- [x] #3 390·1400 폭 실제 화면으로 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
구현 HomeDashboard.tsx revealHero — 아래쪽 입구(startSession)만 부르고, 카드가 다 보이면 움직이지 않음. 회차 b15 reveal-*.json(마이크 권한 거부로 세션이 소켓 전에 실패 → dev DB·Nova 영향 없음): 390 Free talk scrollY 887→156(카드 top 0) · 390 Start speaking scrollY 120→120 · 1400 카드가 보임 → 0→0. tsc 0 · eslint 0.
<!-- SECTION:NOTES:END -->
