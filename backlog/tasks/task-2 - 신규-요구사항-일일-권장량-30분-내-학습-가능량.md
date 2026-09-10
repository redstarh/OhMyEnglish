---
id: TASK-2
title: '신규 요구사항: 일일 권장량 = 30분 내 학습 가능량'
status: To Do
assignee: []
created_date: '2026-09-06 00:11'
updated_date: '2026-09-10 22:33'
labels:
  - caps-req
dependencies: []
ordinal: 2000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 5. 임의의 학습 시나리오는 사전에 생성하고, 이를 기반으로 사용자가 학습을 종료할지, 이어 갈지를 결정.
하나의 학습 시나리오를 마치면 이를 그날 학습을 완료한 것으로 봄 현재 판정 미완료
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 학습 시나리오를 마치면 이를 그날 학습을 완료한 것으로 봄
- [ ] #2 학습 시나리오 하나라도 마치면 일일 학습량을 마친것으로 봄
- [ ] #3 요구사항 상세화 + 설계 반영 + 저장 위치 지정
<!-- AC:END -->

## 착수 전 확인 (TASK-11 조사, 2026-09-06 — 팀리드 직접 확인)

⚠️ **`daily_goal_minutes` 결정이 착지하지 않았다.** `001_initial_schema.sql` 머리말이 그 컬럼을
"앱 상수로 대체했다"고 적었는데 **그 상수가 코드에 없다**(히트 0건). 결정만 기록되고 구현이 0줄이다 —
이 태스크는 "없는 것을 새로 만든다"가 아니라 **"기록된 결정을 착지시킨다"**로 시작한다.

⚠️ **`learning_sessions.learning_source`가 이미 `('recommended','additional','user_requested')`
값역을 갖는데 앱이 쓰지 않는다**(INSERT가 `user_id·scenario_id·mode` 셋뿐). 권장량 초과 후의
추가 학습을 구분할 때 **새 컬럼이 필요 없다** — TASK-10과 이 컬럼을 공유한다.

근거: `docs/design/2026-09-06-gap-investigation.md` §3 항목 14.
