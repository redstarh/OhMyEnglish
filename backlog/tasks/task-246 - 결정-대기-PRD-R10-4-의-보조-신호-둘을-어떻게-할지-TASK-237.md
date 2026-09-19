---
id: TASK-246
title: '결정 대기: PRD R10-4 의 보조 신호 둘을 어떻게 할지 (TASK-237)'
status: Done
assignee: []
created_date: '2026-09-19 07:50'
updated_date: '2026-09-19 11:21'
labels: []
dependencies: []
ordinal: 310000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
⛔ 제품 요구사항 판단이라 사람이 골라야 함 — 어느 쪽도 코드로 유도되지 않음. 결함 정본은 TASK-237 임. 갈림: PRD R10-4·AC10-3 이 보조 신호 둘(한글 전사 섞임 · 코치의 되물음)을 기록할 것을 지금도 요구하나, 결정 120 과 TASK-24 가 각각 그 writer 를 없앴음. AC 쪽 잘못도 구현 쪽 잘못도 아니고 문서 둘이 갈려 있음. ⚠️ 결정 120 의 근거는 「51세션에서 입력 0건」이었는데 2026-09-19 회차에서 한글 전사가 1건 실제로 발생했음 — 다만 강한 억양 TTS 픽스처를 일부러 썼으므로 실사용 빈도의 근거는 되지 못함. 세 갈래: ⑴ PRD 를 개정해 요구를 걷음 ⑵ writer 를 되살림(결정 120 을 뒤집는 결정 기록이 먼저) ⑶ 기록 대신 다음 세션 계획이 볼 수 있게 다른 수단으로 만듦.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자가 세 갈래 가운데 하나를 골랐음
- [x] #2 고른 근거가 docs/design 에 결정 기록으로 남았음
- [x] #3 고른 갈래대로 PRD 또는 코드가 바뀌었음
<!-- AC:END -->
