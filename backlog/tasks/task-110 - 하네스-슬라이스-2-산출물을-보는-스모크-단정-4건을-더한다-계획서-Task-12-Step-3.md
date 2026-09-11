---
id: TASK-110
title: '하네스: 슬라이스 2 산출물을 보는 스모크 단정 4건을 더한다 (계획서 Task 12 Step 3)'
status: Done
assignee: []
created_date: '2026-09-11 13:24'
updated_date: '2026-09-11 13:38'
labels: []
dependencies: []
ordinal: 113000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-48(계획서 Task 12)을 닫을 때 소유자가 없는 것으로 확인된 항목이다. 계획서 docs/design/2026-09-04-learning-coach-slice2-plan.md 「Task 12: 문서를 정본과 맞춘다」 Step 3 이 정본이고, TASK-48 의 AC 셋(AS11 신설 · AC11-5 미충족 명시 · 정정 항목 대조)에는 이 넷이 들어 있지 않았다. 그래서 TASK-48 을 닫으면 원장에서 사라진다 — 그것을 막기 위해 신설했다. ⚠️ 하네스는 게이트 밖 자산이다(함정 H-AA — 스모크가 이틀간 죽어 있었던 전례가 있다). 손대기 전에 git log -1 -- tests/harness/ 와 최근 앱 변경 날짜를 대조한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 세션 종료 후 계획 job 이 걸리는 것을 스모크가 단정한다
- [x] #2 session_plans 행 1건이 생기는 것을 단정한다
- [x] #3 learner_notes 행 1건이 생기는 것을 단정한다
- [x] #4 다음 세션 시작 시 스텁 지시문에 Today's plan: 이 있는 것을 단정한다
- [x] #5 손대기 전에 하네스가 살아 있는지 확인한 결과를 회차 기록이나 태스크 노트에 적는다 — 죽은 스모크에 단정을 더하면 통과가 무의미하다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-11 완료 — 스모크에 단정 넷을 붙이고 1회 돌려 16/16 PASS 를 얻었음. 정본은 그 실행 출력이고 스크립트는 scripts/smoke_analysis.py 임.

AC#5 먼저 — 손대기 전에 스모크가 살아 있는지 확인했음. 확장 전 그대로 1회 돌려 12/12 PASS · exit 0 을 얻었음(Claude 분석 2호출). ⚠️ 하네스 최근 변경은 2026-09-11(tests/harness/)이고 스모크 자체는 2026-09-08(scripts/)이라 앱보다 뒤처져 있었으므로 이 확인이 필요했음(함정 H-AA).

붙인 단정 넷: ① 세션 종료가 계획 job 을 걸었다 ② session_plans 1행 ③ learner_notes 1행 ④ 다음 세션 스텁 지시문에 Today's plan: 이 있다. 확장 후 16/16 PASS · plan_job status=done attempts=1 임.

⛔ 손으로 job 을 넣지 않았음 — mark_session_ended 를 불러 end_session 이 종료 UPDATE 와 job INSERT 를 한 트랜잭션에서 하게 했음. 손으로 넣으면 등록 경로가 끊겨도 통과함. ④ 도 build_system_prompt 를 직접 부르지 않고 create_voice_adapter 를 그대로 썼음 — 팩토리가 계획을 어댑터에 넘기는 이음매(AS6)를 건너뛰지 않기 위함이고, voice_adapter 만 스텁으로 덮었음(dev .env 는 nova 임).

⛔ 선행으로 걸었던 TASK-108·TASK-109 를 지웠음. 걸었던 근거는 「계획 생성이 거부되므로 ②③④ 가 통과할 수 없다」였는데 실행이 그것을 반증했음 — 이 DB 에서 계획 생성이 성공했음. Done 이 열린 태스크에 의존하는 것은 그래프 이상이라 의존을 남기지 않았음.

⛔ 예측이 틀렸고 그 정정이 이 회차의 값어치임. 나는 「스모크 DB 는 패턴 1건뿐이라 만성 목록이 비고 deepest_pattern_id 가 None 이 되어 TASK-108 의 규칙이 적용되지 않을 것」으로 예측했음. 스모크 DB 를 직접 조회한 결과 chronic=1 이고 deepest_recurrence 가 그 하나였음 — 즉 그 규칙은 «적용된 상태로» 통과했음. 통과한 이유는 후보가 하나라 모델이 틀릴 수 없다는 것임.

⇒ TASK-108 의 재현 조건이 좁혀짐: 만성 목록이 «2건 이상» 이어야 모델이 chronic.py 의 순위 규칙을 추측하게 됨. 이 스모크는 그 조건을 만들지 않으므로 ⛔ 이 넷의 PASS 를 「계획 생성이 건강하다」로 읽으면 안 됨 — 그 경고를 스크립트 주석에 박았음. TASK-109(모델이 없는 키를 붙임)는 비결정적이라 1회 통과가 부재를 뜻하지 않음.

부수로 고친 것 하나: 스모크가 「001 마이그레이션 적용」이라 찍고 docstring 에도 그렇게 적었는데 recreate_database 는 migrations_dir/*.sql 을 전부 적용함. 출력이 거짓을 말하고 있었으므로 교체했음.

게이트: ruff check·format exit 0 · ty All checks passed. 스모크는 게이트 밖 자산이라 pytest 에 걸리지 않음.
<!-- SECTION:NOTES:END -->
