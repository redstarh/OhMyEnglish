---
id: TASK-61.9
title: 음성 명령 「일시 정지」 — status 값역 확장과 재개 계약이 선행함
status: To Do
assignee: []
created_date: '2026-09-15 16:17'
labels: []
dependencies: []
parent_task_id: TASK-61
ordinal: 184000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
PRD §Voice Control 의 남은 명령 셋 가운데 하나다(결정 110 이 넷째 조각을 「추가 학습」으로 좁혔으므로 나머지를 각각 등록했다 — 착수 조건이 서로 달라 묶지 않았다).

⛔ 지금 열 자리가 아닌 이유: learning_sessions.status 값역이 active·completed·failed 셋뿐이고 정지 값이 없다. 그리고 세션이 열려 있는 동안 상태를 바꾸는 경로가 리포에 없다 — UPDATE 경로 여섯이 전부 연결 직후·종료·워커다(TASK-61.8 노트의 조사). 즉 마이그레이션 하나와 재개 계약, 새 UPDATE 경로를 동시에 만들어야 한다. 결정 102 ② 가 첫 조각에서 기각한 이유가 그것이다.

⚠️ 되돌릴 수 있는 부류이므로 확인 절차는 필요하지 않을 것이다(결정 107 ③ 의 기준). 그 판정은 착수 시점에 다시 한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 status 값역 확장 마이그레이션을 발급하고 dev DB 적용 여부를 사용자 판단으로 받는다
- [ ] #2 재개 계약을 정한다 — 누가 어떤 신호로 재개하는가
- [ ] #3 명령을 계약대로 만들고 실물 회차로 영어·한국어 둘을 관측한다
<!-- AC:END -->
