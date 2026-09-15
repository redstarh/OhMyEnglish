---
id: TASK-61.7
title: PRD Voice Control 의 남은 명령 다섯 — 등록만 하고 착수하지 않음
status: Done
assignee: []
created_date: '2026-09-15 13:07'
updated_date: '2026-09-15 13:31'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 182000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 107 이 둘째 조각을 「주간 리포트 보기」 하나로 좁혔으므로(TASK-61.6 Done) PRD §Voice Control 의 나머지가 등록되지 않은 채 남는 것을 막기 위한 태스크다. 착수 조건은 사용자 판단이다.

남은 다섯과 결정 107 이 적은 비용: 다음 문제(되돌릴 수 있으나 진행도 컬럼이 없어 앱이 할 일이 기록뿐) · 추가 학습(세션을 닫고 다시 여는 계약이 새로 생김) · 모드 변경(세션 중 변경이 결정 35 의 「모드를 러너가 다시 판정하지 않음」과 충돌하고 Nova 지시문은 promptStart 에 한 번만 실림) · 학습 계속(learning_sessions.status 에 되돌아오는 전이가 없어 잇기 개념 자체가 없음) · 일시 정지(status 값역 확장 마이그레이션과 재개 계약을 동시에 요구함).

「학습 시작」은 범위 밖이다(TASK-61 노트 2026-09-14). 「복습 보기」는 화면도 API 도 없어 결정 107 이 빼 두었다 — review_tasks 를 내려주는 경로가 리포에 0건이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 어느 명령을 다음 조각으로 할지 사용자 판단을 받는다 — 결정 107 의 기각 근거를 근거로 다시 제시한다
- [x] #2 정한 명령을 계약대로 만든다 — 표지 요구·확인 필요 여부(requires_confirmation)·기록 유형
- [x] #3 실물 회차로 관측하고 영어·한국어 둘을 함께 본다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 AC 셋 다 닫음. 구현 커밋 abf3210. 회차 tests/harness/runs/2026-09-15-task61-7-next-question — ARM-EN PASS(명령 뒤 코치가 계획의 둘째 질문을 축자로 냈고 드릴 exchange 최소값을 깨고 넘어갔음. 결정 108 ③ 의 문면이 실물 거동을 만들었음) · ARM-KO 는 tool 과 기록은 오지만 코치가 다음 질문을 말하지 않아 기능이 성립하지 않음(결정 106 의 침묵 재현). 화면 무반응은 결정 108 ② 대로임. 공유 dev DB 는 계획 한 행을 읽기만 했고 기준선 그대로임(세션 17 · 계획 6 · 마이그레이션 22).

⛔ 남은 명령의 판단을 바꾸는 발견: 결정 106 의 대가 크기가 「명령을 누가 수행하는가」로 갈림. 화면이 수행하면 한국어에서 성립하고(리포트 보기) 코치가 수행하면 성립하지 않음(다음 문제·종료). 회차 §3 이 그 표를 가짐.
<!-- SECTION:NOTES:END -->
