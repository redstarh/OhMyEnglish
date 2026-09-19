---
id: TS-35
title: A17 · 시나리오(무대) 생성과 진행 — generate_scenario
status: To Do
assignee: []
created_date: '2026-09-19 05:22'
labels: []
dependencies: []
ordinal: 35000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A17. 대상: job generate_scenario · services/scenario_generator.py·scenario_progress.py·scenario_rotation.py · WS mode=scenario_intake. 근거: 설계서 2026-09-12-scenario-generator-design.md · 2026-09-12-scenario-rotation-70-30-design.md. ⚠️ 자동 테스트는 unit 5파일뿐이고 WS 종단 커버리지는 미확정임. ⛔ 무대 제목의 언어 같은 제품 판단은 판정하지 않고 결함에 적음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 시나리오가 생성돼 세션에 붙음
- [ ] #2 회전 비율 70대 30 규약이 성립함
- [ ] #3 시나리오 진행 상태가 턴을 넘어 이어짐
- [ ] #4 mode=scenario_intake 진입이 성립함
<!-- AC:END -->
