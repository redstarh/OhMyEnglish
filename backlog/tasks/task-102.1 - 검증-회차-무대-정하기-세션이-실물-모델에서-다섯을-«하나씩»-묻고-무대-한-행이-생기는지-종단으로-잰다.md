---
id: TASK-102.1
title: '검증 회차: 무대 정하기 세션이 실물 모델에서 다섯을 «하나씩» 묻고 무대 한 행이 생기는지 종단으로 잰다'
status: To Do
assignee: []
created_date: '2026-09-12 15:04'
labels: []
dependencies: []
parent_task_id: TASK-102
ordinal: 144000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-5 Task 6 이 배선을 끝냈고 게이트 넷이 초록이지만, 「문면이 실제로 그 행동을 유도하는가」는 재지 않았음. 결정 50 이 그 부류를 스파이크만으로 닫지 않기로 정했음. ⛔ 실물 Nova 세션은 사용자 승인 사안임(결정 38·39 의 선례) — 마이크가 필요하므로 사람이 있어야 함. 조립된 문면은 build_system_prompt(..., scenario_intake=True) 로 출력해 확인했음(질문 다섯이 순서대로 · one at a time · Do not invent).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 먼저 스텁 어댑터로 «파이프라인»만 잰다 — ?mode=scenario_intake 로 열고 종료해 analysis_jobs 에 generate_scenario 가 걸리는지, 워커가 그것을 처리해 source='generated' 행이 생기는지 앱 경로에서 확인한다. ⛔ 이 회차는 사람 없이 돌 수 있으므로 실물 세션보다 먼저 한다
- [ ] #2 실물 Nova 세션 1회로 «다섯을 하나씩 묻는가»를 잰다 — 회차 전에 승인을 받고, 코치가 한 턴에 여러 질문을 묶는지·답을 못 받은 축에서 지어내는지를 전사문으로 센다. ⛔ 1회 관측을 비율로 읽지 않는다
- [ ] #3 생성된 무대가 배치 규칙에 실제로 집히는지 확인한다 — display_order 0 · is_generated True 인 행이 신규 차례에서 시드보다 «먼저» 나오는지(결정 80). ⚠️ 단위 테스트는 그것을 순수 함수로 이미 재므로 여기서는 DB 행으로 잰다
<!-- AC:END -->
