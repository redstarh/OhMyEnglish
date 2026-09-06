---
id: TASK-20
title: '프론트엔드 검증 T5a: CDP 프레임 주입 스파이크 (3종 + 창 확인)'
status: To Do
assignee: []
created_date: '2026-09-06 00:14'
labels: []
dependencies:
  - TASK-19
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 T5a. 범위가 3종 + 창 확인으로 넓어졌다(지적 M-c·N-3 반영). C2가 partial+final 둘을 요구하므로 그 둘이 되는지 모르면 T3의 전제가 닫히지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 pronunciation 프레임 1건 주입 시 배지가 뜨는지
- [ ] #2 partial 주입 시 접두 단락이 0에서 1로 늘어나는지
- [ ] #3 final 주입 시 두 갈래를 각각 확인 — 첫 final은 새 줄이 되고, 같은 화자 연속 주입은 줄 수가 늘지 않는다
- [ ] #4 주입 창이 실제로 먹는지 확정 — 무응답 대역 모드에서 연결 상한 10초 안에 측정이 끝나는가
<!-- AC:END -->
