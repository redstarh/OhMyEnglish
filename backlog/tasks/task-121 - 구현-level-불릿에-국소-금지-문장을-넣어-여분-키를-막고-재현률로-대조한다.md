---
id: TASK-121
title: '구현: level 불릿에 국소 금지 문장을 넣어 여분 키를 막고 재현률로 대조한다'
status: To Do
assignee: []
created_date: '2026-09-12 00:08'
labels: []
dependencies: []
ordinal: 126000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-119 가 자리를 정했음 — 정본은 runs/2026-09-12-task119-extra-keys.md §3 임. 전역 금지 문장은 이미 있고(plan.py:274) 지켜지지 않았으므로 같은 층에 문장을 더하지 않고 _OUTPUT_SPEC 의 - level: 불릿에 국소 문장을 둠. 기준선은 여분키 2/5(누적 9회 4건 · 생산 경로 1건)임. ⚠️ 이 리포의 선례가 같은 구조임 — _PRONUNCIATION_FOCUS_RULE 다섯째 줄이 전역 요구와의 모순을 그 자리에서 닫았음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 - level: 불릿에 「세 키가 전부이고 번역·주석 키를 붙이지 않는다」를 관측된 이름(reason_en · reason_note)과 함께 적는다. ⛔ 전역 문장을 건드리지 않는다
- [ ] #2 단위 테스트가 그 문장을 «불릿 범위로 좁혀» 지킨다 — 프롬프트 전체를 대상으로 재지 않는다(test_plan.py 머리말의 지배 규칙). 뮤테이션으로 판별력을 확인한다
- [ ] #3 고친 판으로 8회를 돌려 여분키 발생을 센다 — 상한과 해석 규칙을 돌리기 전에 회차 기록에 적는다. ⛔ 0건을 「해결됨」으로 단정하지 않는다(P(0 in 8 | 0.4)=0.017 을 근거로 적는다)
- [ ] #4 ⛔ PlanOutput 의 extra=forbid 를 풀지 않는다 — 지어낸 키가 조용히 저장되는 것을 막는 가드다
<!-- AC:END -->
