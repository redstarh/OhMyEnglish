---
id: TASK-19
title: '프론트엔드 검증 T2: instrument.js 신설 + 스파이크'
status: To Do
assignee: []
created_date: '2026-09-06 00:13'
updated_date: '2026-09-06 02:34'
labels: []
dependencies:
  - TASK-29
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 T2. 계측 스크립트를 만들고 자기검사를 넣는다. 계측이 조용히 퇴화하면 시끄럽게 죽인다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 반환값이 instrumented가 아니면 즉시 ERROR로 끝낸다
- [ ] #2 후킹 대상 부재를 일부러 만들어 throw하는지 확인
- [ ] #3 createBufferSource를 어느 프로토타입에서 단정해야 하는지 실측 확정
- [ ] #4 계측 없이 클릭했을 때의 대조를 실측한다 — sent가 0이면 FAIL이 아니라 BLOCKED로 보고
<!-- AC:END -->
