---
id: TASK-324
title: '결함: 390 폭 문장 연습에서 단원 이름이 길면 Auto/Manual 전환 버튼 왼쪽이 잘림 (TASK-317 확인 중 발견)'
status: Done
assignee: []
created_date: '2026-11-14 09:29'
updated_date: '2026-11-14 09:31'
labels: []
dependencies: []
ordinal: 391000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
증거: tests/agent/runs/2026-11-14-b17/evidence/live-result-390.png — Unit 12 · 과거 부정과 질문 didn't · Did you? 에서 Auto 가 「uto」로 보임. 단원 줄은 flex 이고 전환 묶음이 줄어들 수 있어 긴 주제에 밀림.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 고치기 전 측정으로 잘림을 남김
- [x] #2 가장 긴 주제에서도 전환 버튼 전체가 보임(320·390·1400)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
고치기 전(b17/toggle.mjs): 가장 긴 주제(Unit 56)에서 전환 묶음 320 57px · 390 37px 잘림. 고침: 전환 묶음 flexShrink 0 · 단원 이름 minWidth 0. 고친 뒤 320·390·1400 잘림 0. 카드 높이: 390 490 · 1400 434 고정 · 320 은 주제 1~3줄로 554~594(기준 폭 밖).
<!-- SECTION:NOTES:END -->
