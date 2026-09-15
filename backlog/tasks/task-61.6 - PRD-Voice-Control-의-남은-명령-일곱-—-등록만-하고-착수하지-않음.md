---
id: TASK-61.6
title: PRD Voice Control 의 남은 명령 일곱 — 등록만 하고 착수하지 않음
status: In Progress
assignee: []
created_date: '2026-09-15 05:05'
updated_date: '2026-09-15 12:52'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 181000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 102 ②가 첫 조각을 「종료 하나」로 좁혔으므로 PRD 가 열거한 나머지가 등록되지 않은 채 남는 것을 막기 위한 태스크다. ⛔ 착수 조건은 사용자 판단이다 — 첫 조각의 결함(TASK-61.5)이 닫히고 표지 인식의 대가(결정 105)를 다시 볼 뒤가 순서상 맞다.

PRD §Voice Control 의 목록 가운데 남은 것: 학습 시작/계속/추가 학습 · 모드 변경 · 다음 문제 · 일시 정지 · 복습·리포트 보기. (반복·천천히·힌트는 대화 규칙 5 로 이미 되고, 종료는 TASK-61.1 이 만들었다.)
⛔ 「학습 시작」은 세션 전에 마이크를 여는 별개 기능이라 이 목록에서도 뺀다(TASK-61 노트 2026-09-14).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 어느 명령을 다음 조각으로 할지 사용자 판단을 받는다 — 되돌릴 수 있는 것과 없는 것을 갈라 제시한다
- [x] #2 정한 명령을 첫 조각과 같은 계약으로 만든다 — 표지·확인·기록 유형
- [ ] #3 실물 회차로 관측하고 영어·한국어 둘을 함께 본다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 AC#1 닫음 (세션 ohmyenglish-65). 후보 여섯을 되돌림 성질로 갈라 제시하고 사용자가 「주간 리포트 보기」를 골랐음 — 정본은 결정 107 (docs/ops/captain-instruction-register.md). 계약 셋: 데이터는 /api/weekly-report · 세션을 유지하고 세션 화면에 패널 · 확인 절차 없음(PRD:85 가 「결과가 큰 명령」에만 확인을 요구함). 「복습」은 화면도 API 도 없어 이 조각에서 빠짐. ⚠️ 제목의 「일곱」은 학습 시작을 포함한 수이고 실제 후보는 여섯임.
<!-- SECTION:NOTES:END -->
