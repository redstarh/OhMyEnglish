---
id: TASK-134
title: '결함(확정): llm_calls.purpose 값역이 job 종류를 못 담아 토큰 기록이 조용히 사라진다'
status: To Do
assignee: []
created_date: '2026-09-12 17:07'
labels: []
dependencies: []
ordinal: 147000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-13 세션 ohmyenglish-f4 가 TASK-62 Task 3 을 쓰다 찾았음. 013 의 llm_calls_purpose_check 는 plan·analysis·spike·nova 넷뿐인데 services/scenario_generator.py:248 이 purpose='generate_scenario' 를 넘김 — 값역 밖이라 삽입이 불가능함. ⛔ 그리고 services/usage.py:152 가 asyncpg.PostgresError 를 삼키고 exception 으로만 찍으므로 «호출은 성공하고 기록만 사라짐». 즉 결정 66(TASK-60)이 요구한 토큰 기록이 그 job 에 대해 0건임. dev DB 조회로 확인: 값역은 넷 그대로이고 기록된 purpose 는 nova 1 · spike 3 뿐임. ⚠️ plan·analysis 가 0건인 것은 이 결함의 증거가 아님(그 job 이 dev DB 에서 실물 Claude 로 돈 적이 없을 수 있음) — 확정 근거는 CHECK 정의 하나임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 값역을 늘린다 — generate_scenario·summarize_session 을 담는다. ⛔ drop+add 로 다시 세울 때 기존 값 전부를 pg_get_constraintdef 로 «조회해» 옮긴다(018 의 초안이 review 를 빠뜨린 선례가 있다)
- [ ] #2 기록이 실제로 남는지 재는 단정을 만든다 — 지금 0건이다. ⛔ 「호출했다」가 아니라 «llm_calls 에 행이 생긴다»를 잰다: usage.py 가 오류를 삼키므로 호출만 재면 이 결함이 초록으로 지나간다
- [ ] #3 삼키는 것을 유지할지 정한다 — 기록 실패로 job 을 실패시키지 않는 것이 기존 판단이고 그것은 옳다. ⚠️ 다만 값역 위반은 «설정 오류»라 운영 중 조용히 넘길 것이 아니다: 그 갈래만 따로 로그 수준을 올릴지 검토한다
<!-- AC:END -->
