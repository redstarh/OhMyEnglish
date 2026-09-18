---
id: TASK-208
title: '구현 ④: POST /api/shadowing/recordings/{utterance_id}/readback'
status: To Do
assignee: []
created_date: '2026-09-18 05:54'
labels: []
dependencies:
  - TASK-206
  - TASK-207
ordinal: 269000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 131 · 설계서 §4. 요청할 때 계산한다 — job 을 만들지 않는다. readback_transcript 가 이미 있으면 전사를 건너뛴다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 전사가 없으면 만들고 있으면 건너뛰는 것을 테스트로 고정한다
- [ ] #2 응답이 낱말 단위 대조를 실어 준다
- [ ] #3 남의 발화 id 로 부르면 거부한다
<!-- AC:END -->
