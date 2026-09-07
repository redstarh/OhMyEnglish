---
id: TASK-25.2
title: >-
  구현 B: 조립 경로 (원자적) — sessions·ws·factory·nova + 시그니처 테스트 10곳 (§6 항목
  3·4·5·6·12·16)
status: Done
assignee: []
created_date: '2026-09-07 14:21'
updated_date: '2026-09-07 15:41'
labels: []
dependencies:
  - TASK-25.1
parent_task_id: TASK-25
ordinal: 34000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계서 §6 의 3·4·5·6·12·16. 브리프 정본은 .superpowers/sdd/.../batch-B-brief.md. ⛔ 원자적이다 — create_voice_adapter·build_system_prompt 인자가 2개 늘고 그 시그니처를 하드코딩한 테스트가 10곳(spy 2 · 직접호출 8)이라 하나만 고치면 TypeError 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 _PREPARED_PLAN_SQL 에 sp.questions + PreparedPlan.questions + docstring :122 의 '질문 목록은 담지 않는다' 서술을 같은 커밋에서 정정한다
- [x] #2 questions 검증 실패는 warning + None 으로 계획 전체를 포기한다 · load_prepared_plan docstring 에 /next-plan 이 같은 조회를 공유한다는 파급을 적는다
- [x] #3 load_session_scenario 신설 — 세션 부재·scenario_id null·시나리오 행 부재가 전부 None 이고 if 분기를 쓰지 않는다 (TASK-25 AC#3) · DB 오류는 던진다
- [x] #4 drill_turns_expected UPDATE — len(questions[:drill_count]) x drill_turns_min · 계획 없으면 쓰지 않는다(null 유지) · 실패는 로그+진행 · summary 에는 쓰지 않는다
- [x] #5 _load_prepared_plan_or_none 반환을 PreparedPlan | None 으로 올린다 (C-1 의 자리 — 지금은 instruction 만 돌려주고 PreparedPlan 을 버린다)
- [x] #6 지시문 블록 — 순서 SYSTEM_PROMPT→놓친소리→setting→plan · exchanges 낱말(turns 금지) · questions[:drill_count] 만 열거 · in this order 부재 · title 부재
- [x] #7 nova build_system_prompt docstring 축 분석에 설계서 §2.2 축 표 5행을 옮긴다 (그 docstring 이 정본이 된다)
- [x] #8 게이트를 직접 돌려 pytest 기준선 유지/증가 · ruff·format·ty exit 0 · 게이트 밖 6 errors·4 files 기준선 유지를 확인한다
- [x] #9 캡틴 결정 17 — drill_count 기본값을 3→5 로 올리고 근거 주석·.env.example·test_config.py 기본값 단정을 함께 고친다. H-5 tripwire(질문5·drill_count=3 이면 3개만 열거)는 값을 명시 주입해 유지하고, 새 tripwire 1건(기본값에서 질문 5개가 전부 열거된다 = 결정 2 회귀 방어)을 더한다
<!-- AC:END -->
