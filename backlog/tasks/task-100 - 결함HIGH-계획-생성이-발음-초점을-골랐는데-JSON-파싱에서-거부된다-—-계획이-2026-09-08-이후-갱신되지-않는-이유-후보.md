---
id: TASK-100
title: '결함(HIGH): 계획 생성이 발음 초점을 골랐는데 JSON 파싱에서 거부된다 — 계획이 2026-09-08 이후 갱신되지 않는 이유 후보'
status: To Do
assignee: []
created_date: '2026-09-10 22:16'
labels: []
dependencies: []
ordinal: 103000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-98 회차가 찾았음. 정본은 tests/harness/runs/2026-09-11-task98-production-prompt.md §8 임.

재현: cd app/backend && .venv/bin/python ../../tests/harness/p5_worker_leg.py claim --expect-session <plan_next_session job 이 있는 세션> (⛔ guard 와 앞선 job 밀기가 선행됨 — 그 절차는 회차 기록 §8 이 가짐)

실제 관측 (last_error 앞 200자 · 원문):
plan output rejected: plan response was not JSON: '{\n  "focus": [\n    {\n      "pattern_id": "99fc908f-e25c-4c19-86ed-a4720cf8eb2b",\n      "pattern_key": "pronunciation_an_as_a",\n      "target_form": "an_as_a"\n    },\n    {\n      "pattern_id": "70ad1279'

⛔ 두 가지가 동시에 드러났음.
1. 좋은 것 — 모델이 pronunciation_an_as_a 를 focus «첫 자리»에 골랐음. 즉 4563f15(발음이 복습 예정일에 걸리면 계획 초점 한 자리를 얻게 함 · TASK-81)가 «작동»함. 그 갈래가 성립함.
2. ⛔ 나쁜 것 — 그 응답이 models/plan.py:285 에서 「plan response was not JSON」으로 거부됨. 즉 모델이 옳은 내용을 냈는데 저장되지 않음. job 은 status=pending attempts=1 로 남고 재시도 백오프가 걸림.

⚠️ 원인 미확정. 후보 둘: ⑴ 응답이 잘렸음(에러가 앞 200자만 담아 원문 길이를 모름. 70ad1279 에서 끊긴 것으로 보임) ⑵ 파서가 찾는 JSON 후보 형태와 응답 형태가 어긋남(그 raise 가 for 루프 «밖»이라 후보를 모두 시도한 뒤임). ⛔ 어느 것도 배제하지 못했음.

⚠️ 왜 HIGH 인가: session_plans 의 최신 행이 2026-09-08 22:58 UTC 이고 그 뒤 plan_next_session job 이 pending 으로 8건 쌓여 있음. 이 결함이 그 정체의 원인이면 «계획이 갱신되지 않는 상태»가 이어짐 — 즉 발음이 초점을 얻는 기능(TASK-81)이 제품에서 한 번도 발휘되지 못함.

⛔ 이 회차가 고치지 않았음. DB 는 전건 복원했음(analysis_jobs drift 0).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 응답이 잘린 것인지 파서 불일치인지 가른다 — 원문 전체를 로그로 남기게 하고 길이를 잰다
- [ ] #2 이 결함이 session_plans 정체(2026-09-08 이후 갱신 0)의 원인인지 확인한다 — pending 8건이 같은 사유로 실패하는지 본다
- [ ] #3 고친 뒤 계획이 실제로 저장되고 그 계획으로 조립한 프롬프트에 소리 줄이 붙는지 확인한다 (grep -c "Sound to coach today" >= 1)
- [ ] #4 ⛔ TASK-98 AC#4(21회 회차)가 이 결함에 막혀 있다 — 이것이 닫히기 전에 21회를 쓰지 않는다
<!-- AC:END -->
