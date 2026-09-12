---
id: TASK-134
title: '결함(확정): llm_calls.purpose 값역이 job 종류를 못 담아 토큰 기록이 조용히 사라진다'
status: Done
assignee: []
created_date: '2026-09-12 17:07'
updated_date: '2026-09-12 17:31'
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
- [x] #1 값역을 늘린다 — generate_scenario·summarize_session 을 담는다. ⛔ drop+add 로 다시 세울 때 기존 값 전부를 pg_get_constraintdef 로 «조회해» 옮긴다(018 의 초안이 review 를 빠뜨린 선례가 있다)
- [x] #2 기록이 실제로 남는지 재는 단정을 만든다 — 지금 0건이다. ⛔ 「호출했다」가 아니라 «llm_calls 에 행이 생긴다»를 잰다: usage.py 가 오류를 삼키므로 호출만 재면 이 결함이 초록으로 지나간다
- [x] #3 삼키는 것을 유지할지 정한다 — 기록 실패로 job 을 실패시키지 않는 것이 기존 판단이고 그것은 옳다. ⚠️ 다만 값역 위반은 «설정 오류»라 운영 중 조용히 넘길 것이 아니다: 그 갈래만 따로 로그 수준을 올릴지 검토한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-13 (세션 ohmyenglish-f4).

AC#1 — 021_llm_calls_purpose_jobs.sql 로 값역에 generate_scenario·summarize_session 을 더했음. ⛔ drop+add 로 다시 세울 때 기존 넷을 pg_get_constraintdef 로 조회해 옮겼음(018 초안이 review 를 빠뜨린 선례). 임시 DB 로 적용을 증명하고 drop 했음 — dev DB 에는 적용하지 않았음(승인 사안 · 최대 019 그대로).

AC#2 — 「행이 생기는가」를 재는 단정을 뒀음(tests/integration/test_usage_service.py). ⛔ 「호출했다」를 재면 이 결함이 초록으로 지나감 — sink 가 PostgresError 를 삼키므로 호출은 늘 성공함. db_pool 을 쓰는 이유는 sink 가 풀에서 자기 연결을 잡기 때문이고, 심은 행은 model_id 표지로 좁혀 손으로 지움.

AC#3 — ⛔ 삼키는 것을 «유지» 하되 말하게 하는 것으로 정했음. 근거: 기록 실패로 job 을 실패시키면 「비용은 나갔고 결과는 잃는다」가 됨. ⚠️ 다만 값역 위반은 설정 오류라 조용히 넘길 것이 아니므로 exception 이 남는 것을 단정으로 지킴 — 그 로그가 없으면 이 부류를 다시 눈으로 찾아야 함. 로그 수준을 더 올리지는 않았음(이미 exception 이고 지정된 실행이 warning 이상을 흘림).

⛔ 판별력을 확인하는 «지렛대»가 DB 가 아니라 마이그레이션 파일이었음 — 테스트 DB 를 손으로 좁혔더니 pytest 가 매 실행 마이그레이션에서 재생성해 변이가 지워졌고 그 결과는 red 도 green 도 아니었음. 021 에서 두 값을 빼고 돌리니 그 단정만 red 였고(삼키는 쪽 단정은 초록으로 남았음 — 그것이 옳음) 되돌린 뒤 12건 초록을 확인했음.

게이트: pytest 1132 passed · ruff 안 0 · 밖 0 · format 0 · ty 0.
<!-- SECTION:NOTES:END -->
