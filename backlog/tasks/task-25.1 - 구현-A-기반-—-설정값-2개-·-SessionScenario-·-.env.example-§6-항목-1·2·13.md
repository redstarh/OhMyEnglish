---
id: TASK-25.1
title: '구현 A: 기반 — 설정값 2개 · SessionScenario · .env.example (§6 항목 1·2·13)'
status: In Progress
assignee: []
created_date: '2026-09-07 14:20'
updated_date: '2026-09-07 14:21'
labels: []
dependencies: []
parent_task_id: TASK-25
ordinal: 33000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 docs/design/2026-09-07-scenario-and-drill-turns-design.md §6 의 1·2·13. 브리프 정본은 .superpowers/sdd/2026-09-07-scenario-and-drill-turns-design/batch-A-brief.md 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 Settings 에 drill_turns_min(기본 4·ge=1)·drill_count(기본 3·ge=1)를 근거 주석과 함께 더한다
- [ ] #2 app/models/scenario.py 신설 — SessionScenario(title, prompt_template) · models 계층에 두는 근거를 docstring 에 적는다
- [ ] #3 루트 .env.example 에 드릴 값 2줄을 근거 주석과 함께 더한다 (값은 Settings 기본값과 같다)
- [ ] #4 drill_turns_min=0 · drill_count=0 이 기동 시점에 거부되는 것을 T0 red→green 으로 관측한다
- [ ] #5 게이트를 app/backend cwd 에서 직접 돌려 668 passed 기준선이 유지/증가하고 ruff·format·ty 가 exit 0 인 것을 확인한다
<!-- AC:END -->
