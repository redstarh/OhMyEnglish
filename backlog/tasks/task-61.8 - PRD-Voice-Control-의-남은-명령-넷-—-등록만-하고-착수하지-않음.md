---
id: TASK-61.8
title: PRD Voice Control 의 남은 명령 넷 — 등록만 하고 착수하지 않음
status: To Do
assignee: []
created_date: '2026-09-15 13:31'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 183000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 108 이 셋째 조각을 「다음 문제」 하나로 좁혔으므로(TASK-61.7 Done) 나머지가 등록되지 않은 채 남는 것을 막기 위한 태스크다. 착수 조건은 사용자 판단이다.

⛔ 후보를 고를 때 쓸 판정 축이 하나 늘었다 — TASK-61.7 회차가 「결정 106 의 침묵이 코치가 수행하는 모든 명령을 막는다」를 관측했다(runs/2026-09-15-task61-7-next-question §3). 화면이 수행하는 명령은 한국어에서 성립하고 코치가 수행하는 명령은 성립하지 않는다.

남은 넷과 수행 주체·비용:
- 추가 학습 — 수행 주체는 앱(세션을 닫고 새로 엶). 한국어 가용. 시작 화면 버튼 여섯이 이미 있으나 종료+재시작 계약이 새로 생기고 확인 절차가 필수다.
- 일시 정지 — 수행 주체는 앱(상태 전이). 한국어 가용. learning_sessions.status 값역 확장 마이그레이션과 재개 계약을 동시에 요구한다.
- 모드 변경 — 세션 중 변경이 결정 35 의 「모드를 러너가 다시 판정하지 않음」과 충돌하고 Nova 지시문은 promptStart 에 한 번만 실린다.
- 학습 계속 — learning_sessions.status 에 되돌아오는 전이가 없어 잇기 개념 자체가 리포에 없다.

「학습 시작」은 범위 밖이고(TASK-61 노트 2026-09-14) 「복습 보기」는 화면도 API 도 없어 결정 107 이 빼 두었다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 어느 명령을 다음 조각으로 할지 사용자 판단을 받는다 — 수행 주체(화면인가 코치인가)를 함께 제시한다
- [ ] #2 정한 명령을 계약대로 만든다 — 표지 요구·확인 필요 여부(requires_confirmation)·기록 유형
- [ ] #3 실물 회차로 관측하고 영어·한국어 둘을 함께 본다
<!-- AC:END -->
