---
id: TASK-61.8
title: PRD Voice Control 의 남은 명령 넷 — 등록만 하고 착수하지 않음
status: Done
assignee: []
created_date: '2026-09-15 13:31'
updated_date: '2026-09-15 16:17'
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
- [x] #1 어느 명령을 다음 조각으로 할지 사용자 판단을 받는다 — 수행 주체(화면인가 코치인가)를 함께 제시한다
- [x] #2 정한 명령을 계약대로 만든다 — 표지 요구·확인 필요 여부(requires_confirmation)·기록 유형
- [x] #3 실물 회차로 관측하고 영어·한국어 둘을 함께 본다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-15 설명에 적은 판정 축이 낡았음 — 결정 109 가 그것을 해소했음. 「코치가 수행하는 명령은 한국어에서 성립하지 않는다」는 toolResult 미회신이 원인이었고 고쳐졌음(회차 tests/harness/runs/2026-09-15-task61-5-toolresult). ⇒ 남은 넷을 고를 때 그 축은 더 쓰지 않고 비용(마이그레이션·계약 신설·아키텍처 충돌)만 본다.

2026-09-15 조사 결과 하나를 더 남김 (다시 조사하지 않게). learning_sessions 의 UPDATE 경로는 여섯이고 전부 「연결 직후·종료·워커」임 — services/sessions.py:138(shadowing_item_id) · :157(mode · status='active' 조건 · set_session_mode) · :171(status·ended_at) · :183(reap_orphan_sessions) · :331(drill_turns_expected) · services/session_summary.py:58(summary). ⛔ 세션이 열려 있는 동안 상태를 바꾸는 경로는 없음 — 일시 정지와 모드 변경이 새 계약을 요구하는 이유가 이것임.

클라이언트→서버 메시지는 네 종뿐임(audio · end_session · shadowing_turn_start · shadowing_turn_end · session.py:558-576). 그중 화면 버튼이 붙은 것은 end_session 하나임 — 「UI 버튼과 동일한 행동」(PRD:81)의 실제 표면이 그만큼임.

2026-09-16 AC 셋 다 닫고 Done. 구현 커밋 ab99533 · 회차 tests/harness/runs/2026-09-16-task61-8-additional-learning.

두 팔 모두 세션을 갈아 열었음(session_started 2 · 둘째 세션 learning_source=additional). ARM-EN 에서 target 이 mode=shadowing 으로 반영되고 쉐도잉 클립까지 실렸음 — 인자 경로의 판별력은 그 팔이 가짐. ARM-KO 는 ASR 이 「쉐도잉」을 「최도인」으로 들어 모델이 conversation 을 골랐고, 그것은 결함이 아니라 결정 105 가 적은 대가와 같은 부류임.

화면을 직접 열어 확인했음 — 결과 화면을 거치지 않고 쉐도잉 세션이 열렸음(결정 110 ③).

⚠️ 프론트 경합 방어(onClose 의 소켓 동일성 검사)는 거동만 관측했고 무력화로 판별력을 재지 않았음. 남은 명령 셋은 TASK-61.9·61.10·61.11 로 각각 등록했음 — 착수 조건이 서로 달라 묶지 않았음.
<!-- SECTION:NOTES:END -->
