---
id: TASK-295
title: '리디자인 T3: 홈 분리(추가 학습 목록 · 세션 덮개 층)'
status: Done
assignee: []
created_date: '2026-10-31 19:05'
updated_date: '2026-10-31 19:18'
labels: []
dependencies:
  - TASK-293
ordinal: 360000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계: docs/design/2026-11-01-v0-home-redesign-design.md §3·§4. 세션 논리는 그대로 두고 대기 상태만 대시보드 자리로 비움.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 app/additionalLearning.ts 로 목록과 entryForTarget 이 옮겨지고 고정 key 를 가짐
- [x] #2 세션이 도는 동안 덮개 층이 사이드바를 가림
- [x] #3 tsc · eslint 통과
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
내가 재확인: tsc 0 · lint 오류 0 · 홈 DOM 에 start-session · practice-<key> 8개 · home-dashboard-slot. 덮개 층이 사이드바를 가림은 에이전트 CDP 측정(마이크 실패 상태 · 백엔드에 연결 안 함). ⚠️ 실제 진행 중 세션(채팅·쉐도잉·주간 리포트 패널)을 덮개 안에서 본 것은 아직 없음 → T6 회차(격리 DB + stub)에서 확인.
<!-- SECTION:NOTES:END -->
