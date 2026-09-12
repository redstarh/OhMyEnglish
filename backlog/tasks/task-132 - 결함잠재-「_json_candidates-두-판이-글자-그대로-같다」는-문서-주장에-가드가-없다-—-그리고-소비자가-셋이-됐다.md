---
id: TASK-132
title: '결함(잠재): 「_json_candidates 두 판이 글자 그대로 같다」는 문서 주장에 가드가 없다 — 그리고 소비자가 셋이 됐다'
status: To Do
assignee: []
created_date: '2026-09-12 13:19'
labels: []
dependencies: []
ordinal: 140000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST · 동료 세션이 «plan.py 의 private _json_candidates 를 import 했다» 고 알려 확인하다 찾았음. 그쪽이 말한 것보다 자리가 하나 더 있었음.

실측한 구조:
- app/backend/app/models/plan.py:179 — 정의 (소비자: 같은 파일 :271, 그리고 models/scenario_draft.py:28 이 import·:59 에서 호출)
- app/backend/app/models/analysis.py:190 — «자기 판을 따로 정의» 함. 독스트링이 바이트 동일임
- plan.py:35 가 문서로 주장함: «_json_candidates 의 관용 범위는 models/analysis.py 와 글자 그대로 같다 — 원문, 그리고 전체가 코드펜스인 경우 그 본문뿐이다»

⛔ 그 동일성을 재는 테스트가 «없음» — grep _json_candidates tests/ 가 0건임. ⇒ 누가 한쪽의 관용 범위를 넓히면(예: 산문 중간 JSON 추출) 그 문서 문장이 조용히 거짓이 되고, 두 파서가 서로 다른 관대함을 갖게 됨. 그것이 정확히 동료 세션이 복제를 피한 이유인데 «이미 복제가 하나 있고 그것이 안 지켜지고 있음».

⚠️ 그리고 패턴이 섞였음: plan.py 판은 둘이 공유하고(plan·scenario_draft) analysis.py 는 자기 것을 씀. 어느 한쪽으로 정하는 것이 이 태스크의 판단임 — ⛔ 지금 상태는 「복제 + 문서로 동일성 주장」과 「private 공유」가 공존함.

이 부류를 이 세션에서 세 번 봤음(TASK-118 소리 줄 · TASK-131 값역 단정 · 이것) — 재는 축이 빠지면 게이트는 그 축에 대해 침묵함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 두 판을 «하나로» 할지 «둘로 두고 동일성을 테스트로 못박을지» 정하고 근거를 적는다. ⛔ 새 공개 API 를 만드는 것이 유일한 답이라고 가정하지 않는다 — plan.py 가 그 함수의 경계를 docstring 으로 소유하고 있어 옮기면 근거가 흩어진다는 것이 동료 세션의 판단이었고 그것도 재료다
- [ ] #2 둘로 두기로 하면 동일성을 재는 테스트를 만든다 — 같은 입력 묶음(원문 · 전체 코드펜스 · 산문 중간 JSON · 펜스 안 펜스)에 두 함수의 «출력이 같은지» 본다. ⛔ 소스 문자열 비교로 하지 않는다(주석이 달라도 동작은 같을 수 있고 그 반대도 가능하다)
- [ ] #3 판별력을 잰다 — 한쪽의 관용 범위를 일부러 넓혀 그 테스트가 빨개지는지 본다. 초록만 보고 닫지 않는다
- [ ] #4 소비자 목록을 그 docstring 에 적는다 — 지금 plan.py 판의 소비자가 둘(plan·scenario_draft)이고 그것이 코드를 읽어도 한눈에 안 보인다
<!-- AC:END -->
