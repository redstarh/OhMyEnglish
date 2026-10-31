---
id: TASK-295
title: '리디자인 T3: 홈 분리(추가 학습 목록 · 세션 덮개 층)'
status: To Do
assignee: []
created_date: '2026-10-31 19:05'
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
- [ ] #1 app/additionalLearning.ts 로 목록과 entryForTarget 이 옮겨지고 고정 key 를 가짐
- [ ] #2 세션이 도는 동안 덮개 층이 사이드바를 가림
- [ ] #3 tsc · eslint 통과
<!-- AC:END -->
