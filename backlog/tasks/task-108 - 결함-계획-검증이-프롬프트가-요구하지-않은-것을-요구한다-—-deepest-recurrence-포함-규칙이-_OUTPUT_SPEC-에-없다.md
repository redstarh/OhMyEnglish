---
id: TASK-108
title: '결함: 계획 검증이 프롬프트가 요구하지 않은 것을 요구한다 — deepest recurrence 포함 규칙이 _OUTPUT_SPEC 에 없다'
status: To Do
assignee: []
created_date: '2026-09-11 11:35'
labels: []
dependencies: []
ordinal: 111000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-11 세션 ohmyenglish-7f 후속이 이 턴에 직접 관측했다. build_plan_prompt 로 조립한 실제 프롬프트(14,030자)에 'deepest' 가 0건인데(grep 직접 확인) parse_plan 은 focus 에 그 패턴이 없으면 계획 전체를 하드 거부한다. 실측 사유: 'focus must include the deepest recurrence 70ad1279-... , but it lists 99fc908f-... , e648ad11-...'. 즉 모델은 요구받지 않은 것을 어겼다고 거부당한다 — plan.py 모듈 docstring 이 이미 '프롬프트와 그 집합이 어긋나면 정당한 응답이 거부된다' 로 같은 부류를 경고했고 이번에는 허용 집합이 아니라 AC11-2 순위 규칙에서 같은 어긋남이 났다. ⚠️ 이것이 session_plans 3행 대 analysis_jobs 57건의 간극을 설명할 후보다 — 다만 그 귀속은 TASK-104 가 소유한다(그 태스크의 pending 14건은 attempts=0 이라 다른 원인이다). 근거 정본: runs/2026-09-11-task86-sound-shaped-questions.md §1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 프롬프트가 deepest recurrence 요구를 말하게 하거나 검증에서 그 요구를 내린다 — 어느 쪽인지 근거와 함께 정한다
- [ ] #2 고친 뒤 같은 재료로 계획 생성을 다시 돌려 parse_plan 이 통과하는 것을 실물로 확인한다
- [ ] #3 ⛔ AC11-2 를 없애지 않는다 — 그 규칙은 캡틴 결정이고 이 태스크가 정하는 것은 그것을 «어디서» 집행하는가다
<!-- AC:END -->
