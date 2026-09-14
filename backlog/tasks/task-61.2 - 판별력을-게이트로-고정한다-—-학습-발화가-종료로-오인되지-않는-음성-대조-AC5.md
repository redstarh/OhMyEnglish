---
id: TASK-61.2
title: 판별력을 게이트로 고정한다 — 학습 발화가 종료로 오인되지 않는 음성 대조 (AC#5)
status: To Do
assignee: []
created_date: '2026-09-14 22:24'
labels: []
dependencies:
  - TASK-61.1
parent_task_id: TASK-61
ordinal: 176000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
AC#5 가 요구하는 판별력이다. 접두어가 없는 학습 발화와 접두어가 있는 명령 발화를 같은 게이트에서 대조해, 무력화하면 실패하는 단정으로 둔다. ⛔ 테스트 코드 작성의 주체는 개발 세션이다 — 통합 테스트 세션은 그 게이트가 실제로 반증력을 갖는지 회차로 확인한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 접두어 없는 학습 발화가 종료를 실행하지 않는 단정이 있다
- [ ] #2 접두어 있는 명령이 종료를 실행하는 단정이 있다 — 반대 방향을 함께 못 박는다
- [ ] #3 단정을 일부러 무력화하면 게이트가 실패하는 것을 확인한다
<!-- AC:END -->
