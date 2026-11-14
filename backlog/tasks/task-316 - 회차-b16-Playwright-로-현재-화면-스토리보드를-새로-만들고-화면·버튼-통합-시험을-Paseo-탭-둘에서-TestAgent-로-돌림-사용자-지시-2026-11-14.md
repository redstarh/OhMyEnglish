---
id: TASK-316
title: >-
  회차 b16: Playwright 로 현재 화면 스토리보드를 새로 만들고 화면·버튼 통합 시험을 Paseo 탭 둘에서 TestAgent 로
  돌림 (사용자 지시 2026-11-14)
status: In Progress
assignee: []
created_date: '2026-11-14 05:30'
labels: []
dependencies: []
ordinal: 381000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시: localhost:3000 을 Playwright 로 현재 구성된 화면의 스토리보드를 확인하고 없으면 만들어 시험함 · 버튼과 화면을 별도 Paseo 탭으로 나눠 실제 시험 · TestAgent 활용 가능 여부 확인. 기존 보드 docs/ux/2026-11-01-user-scenarios 는 e2e86c0 기준이라 TASK-308~315 뒤 화면과 다름(메뉴·Day 줄·Grammar course).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 TestAgent 전용 런처(run.sh)가 Playwright 를 돌릴 수 있는지 확인함
- [ ] #2 두 탭의 회차 결과를 받아 판정을 직접 대조함
- [ ] #3 새 스토리보드를 docs/ux 에 남김
- [ ] #4 회차 뒤 사용자 스택을 복원함
<!-- AC:END -->
