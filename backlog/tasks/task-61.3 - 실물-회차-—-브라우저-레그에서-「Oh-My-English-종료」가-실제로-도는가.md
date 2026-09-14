---
id: TASK-61.3
title: '실물 회차 — 브라우저 레그에서 「Oh My English, 종료」가 실제로 도는가'
status: To Do
assignee: []
created_date: '2026-09-14 22:24'
labels: []
dependencies:
  - TASK-61.1
parent_task_id: TASK-61
ordinal: 177000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
구현이 든 뒤 실물 Nova 로 확인한다. 이 태스크의 주체는 통합 테스트 세션이다. ⚠️ TASK-65 가 「파일이 아니라 순서가 ASR 언어를 정한다」를 확정했으므로 한국어 명령의 전사가 어떻게 잡히는지를 이 회차가 관측한다(결정 102 ④의 함정).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 브라우저 레그에서 영어 종료 명령이 확인 절차를 거쳐 세션을 닫는 것을 관측한다
- [ ] #2 한국어 종료 명령의 전사문을 관측하고 인식되는지 판정한다 — 안 되면 결함 후보로 보고한다
- [ ] #3 명령이 아닌 학습 발화로 세션이 닫히지 않는 것을 같은 회차에서 확인한다
- [ ] #4 회차 기록을 tests/harness/runs/ 에 남기고 검증 전용 스택을 정리한다
<!-- AC:END -->
