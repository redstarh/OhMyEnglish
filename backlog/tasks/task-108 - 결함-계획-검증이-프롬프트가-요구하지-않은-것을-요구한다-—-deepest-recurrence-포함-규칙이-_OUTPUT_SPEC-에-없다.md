---
id: TASK-108
title: '결함: 계획 검증이 프롬프트가 요구하지 않은 것을 요구한다 — deepest recurrence 포함 규칙이 _OUTPUT_SPEC 에 없다'
status: To Do
assignee: []
created_date: '2026-09-11 11:35'
updated_date: '2026-09-11 22:48'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 동료 세션 ohmyenglish-40 이 이 태스크의 전제를 «코드로» 대조하고 참임을 확인했음. 그 문면을 그대로 인용함:

「parse_plan 이 focus 에 deepest_pattern_id 포함을 요구하는데 프롬프트의 만성 절은 사실만 싣고(frequency · recurring_sessions · recurring_days · span · longest gap) 어느 것이 「가장 깊은 재발」인지 지목하지 않음. 즉 모델이 chronic.py 의 순위 규칙을 «추측» 해야 함.」

⇒ 이 태스크의 AC#1(프롬프트가 말하게 하거나 검증에서 내리기)에 셋째 길이 하나 더 있음: **순위를 프롬프트가 «계산해 지목» 하는 것** — deepest_recurrence(data.chronic) 는 process_plan 이 이미 부르고 있으므로 그 값을 만성 목록의 해당 줄에 표시로 붙이면 모델이 추측하지 않음. ⚠️ 다만 그것은 조립 함수가 순수 함수라는 성질과 인자 목록에 걸리므로 착수 시 확인해야 함.

⚠️ 그쪽 TASK-110 이 이 태스크와 TASK-109 «둘 다» 를 선행으로 걸었음 — 내가 같은 재료로 계획 생성을 두 번 돌려 두 번 다 거부됐고 사유가 서로 달랐기 때문임(1회 없는 키 · 2회 이 태스크의 사유). 어느 한쪽만 고쳐도 계획 행이 생기지 않을 수 있음.

2026-09-11 (동료 세션 ohmyenglish-40) — 재현 조건이 «만성 2건 이상» 으로 좁혀졌음. 실측 근거는 확장한 스모크 회차임(커밋 8256219 · scripts/smoke_analysis.py 16/16 PASS).

관측: 스모크의 전용 DB(매 실행 drop/create · 발화 2건 · 패턴 1건)에서 계획 생성이 «통과» 했음 — plan_job status=done attempts=1 이고 session_plans·learner_notes 가 각 1행 생겼음.

⛔ 그 통과가 이 결함을 반증하지 않음. 그 DB 를 직접 조회한 결과 chronic=1 이고 deepest_recurrence 가 그 하나였음 — 즉 이 태스크의 규칙은 «적용된 상태로» 통과했고, 통과한 이유는 후보가 하나라 모델이 틀릴 수 없다는 것임.

⇒ AC#2(같은 재료로 다시 돌려 통과를 확인)를 설계할 때 ⛔ 만성 목록이 2건 이상인 재료를 써야 함 — 1건 재료로는 고치기 «전에도» 통과하므로 판별력이 0임.

⚠️ 위 노트의 마지막 문단을 정정함 — TASK-110 이 이 태스크와 TASK-109 를 선행으로 걸었다가 «지웠음». 지운 근거는 실행이 그 전제를 반증한 것임(계획 행이 실제로 생겼음). Done 이 열린 태스크에 의존하는 것은 그래프 이상이라 남기지 않았음.

2026-09-12 KST 재현성 증거가 하나 더 왔음 — 동료 세션 ohmyenglish-40 이 공유 dev DB 에서 계획 생성 **4회를 돌려 이 결함은 0건** 이었음(커밋 6b14adf · 정본 runs/2026-09-12-task104-plan-drain/).

⇒ 내 관측 1건과 합치면 **재료의 문제가 아니라 비결정성** 으로 읽힘: 같은 공유 DB·같은 재료에서 나는 1회 걸리고 그쪽은 4회 다 통과했음. ⛔ 그러나 **결함이 아닌 것으로 내려가지 않음** — 검증이 프롬프트가 요구하지 않은 것을 요구하는 «어긋남» 은 빈도와 무관하게 그대로임(모델이 순위 규칙을 «추측» 해야 함).

⚠️ AC#2 의 판별력 경고가 더 강해졌음 — 앞 노트가 「만성 1건 재료로는 고치기 전에도 통과한다」를 적었고, 이제 「만성 2건 이상이어도 자주 통과한다」가 더해짐. ⇒ 그 AC 를 잴 때는 **회차 수를 미리 정하고** 통과를 「고쳐졌다」로 읽지 않아야 함.

⚠️ 값어치 있는 부수 사실: 이 결함이 나면 last_error 에 사유가 남으므로(services/plan.py:512) **소급 집계가 가능함** — analysis_jobs 의 last_error 를 훑어 「deepest recurrence」 문면을 세면 과거 발생률을 얻을 수 있음. 그것이 AC#1 의 값싼 경로임.
<!-- SECTION:NOTES:END -->
