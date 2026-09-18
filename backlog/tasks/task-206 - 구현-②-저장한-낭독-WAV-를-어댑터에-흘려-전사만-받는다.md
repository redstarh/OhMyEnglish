---
id: TASK-206
title: '구현 ②: 저장한 낭독 WAV 를 어댑터에 흘려 전사만 받는다'
status: To Do
assignee: []
created_date: '2026-09-18 05:54'
labels: []
dependencies:
  - TASK-205
ordinal: 267000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 §4-2. 코치 응답은 버린다. ⛔ 되돌리는 조건(배치 STT 로 옮김)이 있으므로 이 함수 하나만 갈면 되도록 경계를 좁게 둔다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 WAV 경로를 받아 전사문을 돌려주는 함수 하나로 좁힌다
- [ ] #2 코치 응답을 버리는 것과 그 이유를 코드가 밝힌다
- [ ] #3 전사가 비면 판정을 만들지 않고 그 사실을 돌려준다
<!-- AC:END -->
