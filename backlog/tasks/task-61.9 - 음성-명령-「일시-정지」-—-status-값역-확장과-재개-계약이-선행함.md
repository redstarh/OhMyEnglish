---
id: TASK-61.9
title: 음성 명령 「일시 정지」 — status 값역 확장과 재개 계약이 선행함
status: Done
assignee: []
created_date: '2026-09-15 16:17'
updated_date: '2026-09-16 05:00'
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
- [x] #1 status 값역 확장 마이그레이션을 발급하고 dev DB 적용 여부를 사용자 판단으로 받는다
- [x] #2 재개 계약을 정한다 — 누가 어떤 신호로 재개하는가
- [x] #3 명령을 계약대로 만들고 실물 회차로 영어·한국어 둘을 관측한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-16 — 결정 117 로 TASK-61.11 과 한 기능이 됐음(「학습 계속」은 정지된 그 세션을 그대로 이음). 마이그레이션 025 를 발급했고 적용 승인은 결정 115 임.

2026-09-16 — AC#1·#2 를 닫았음. 마이그레이션 **025** 를 발급하고 공유 dev DB 에 적용했음(결정 115 승인) — schema_migrations 22 → 23 · CHECK 에 paused 가 들어갔음 · learning_sessions 17 · session_plans 6 · learning_scenarios 30 은 전후 같음.

AC#2 재개 계약(결정 117): 학습자가 「헤이, 학습 계속」이라 말하면 **그 세션을 그대로 잇는다.** 정지는 «부드러운 정지» 임 — 소켓과 어댑터는 살아 있고(코치가 재개를 들어야 함) 앱이 지키는 계약은 「정지 중 학습 발화를 저장하지 않는다」 하나임. 그 단정이 tests/integration/test_gateway.py 에 셋 있음.

함께 고친 자리 둘: end_session 과 리퍼의 가드가 active 만 보고 있어 정지 중 종료가 영구히 paused 로 남을 자리였음(_LIVE_SESSION_STATUSES 로 묶었음). 지시문 규칙 13 에 pause·resume 을 넣고 「명령의 개수」 서술을 없앴음 — 세면 값역이 늘 때마다 낡음.

2026-09-16 — AC#3 을 닫았음. 정본은 runs/2026-09-16-task61-9-pause-resume 임. 정지 중 미저장 3/3 · 같은 세션 잇기 2/2(영어·한국어 · 새 세션 0건) · 정지 중 종료 3/3 completed · 화면 두 표면을 스크린샷으로 확인했음.
⛔ 회차가 고친 것 하나: 정지 중 미저장 로그가 info 라 보이지 않아(H-Z) warning 으로 올렸음 — 그 크기가 이 기능의 대가라 세지 못하면 안 됨.
⚠️ 부수 관측: 모델이 정지 뒤 첫 학습 발화를 resume 으로 부른 것이 2/3 이고 표지 게이트가 막았음 — 결정 104 의 표지 요구가 오탐을 실제로 막은 첫 관측임.
<!-- SECTION:NOTES:END -->
