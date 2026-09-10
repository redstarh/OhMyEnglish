---
id: TASK-98
title: '하네스: 계획이 실린 «제품» 프롬프트로 tool 도착률을 잰다 — 앱과 같은 함수·같은 인자로 조립함'
status: In Progress
assignee: []
created_date: '2026-09-10 21:49'
updated_date: '2026-09-10 22:00'
labels: []
dependencies: []
ordinal: 101000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-86 AC#2 의 재료를 만드는 회차임. 판정은 TASK-86 이 갖고 이 태스크는 측정만 함 (TASK-93·95 와 같은 분리).

⛔ 착수 방법은 세션 ohmyenglish-40 이 TASK-86 노트에 닫아 뒀음 — 설계 결정이 아니라 구현임. 앱과 «같은 함수»(nova.build_system_prompt)를 «같은 인자»로 부르면 산출물이 같음.

인자 출처를 코드로 확정했음 (api/ws.py:286~293 이 제품 경로임):
- known_sounds = await _load_known_sounds_or_empty(pool)
- scenario = await _load_scenario_or_none(pool, session_id)
- prepared = await _load_prepared_plan_or_none(pool) → plan = prepared.instruction · questions = prepared.questions
- drill_count·drill_turns_min = settings 에서

⛔ 손으로 지어낸 계획을 넣지 않음 — 그러면 「제품이 보내는 것」이 아니게 됨. 값의 출처를 회차 기록에 적음.

⚠️ 판별력: 「계획 유무」 축만으로는 안 생김(양쪽 다 0 이 예상됨). 기반 프롬프트 팔이 판별력 기준점이고 같은 픽스처(p2m→p2a)에서 이미 4/4·8/8 로 확보돼 있음 — 시간 효과를 통제하려고 이 회차에서도 함께 교대로 돌림.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 앱의 호출부와 «같은 함수·같은 인자»로 프롬프트를 조립한다 — 인자를 손으로 지어내지 않고 DB 에서 읽으며 값의 출처를 회차 기록에 적는다
- [x] #2 ⛔ 조립기가 인자 넷을 전부 비웠을 때 SYSTEM_PROMPT 와 «글자 그대로» 같은지 먼저 실증한다 — TASK-67 정정이 그것을 주장하고 내 팔 A(AS4)가 그 위에 서 있다
- [x] #3 계획이 실린 팔과 기반 프롬프트 대조군을 교대로 4회씩 돌려 tool 도착률과 target_sound 실림을 센다
- [ ] #4 AS4 팔의 기존 결과(0/8)와 대조해 «계획이 tool 도착을 바꾸는가»를 판정한다 — 표본이 작으면 구별되지 않음으로 적는다
- [x] #5 ⛔ 워커 미기동 · 보존 세션 불가침 · 소스 미수정 · --tool-choice 미사용 · DB SELECT 만
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10(UTC) 부분 완료 — In Progress 유지. AC#4 미충족. 정본은 tests/harness/runs/2026-09-11-task98-production-prompt.md 임.

⛔ 얻은 것 (AC#1·#2): AS4 프롬프트가 SYSTEM_PROMPT 와 글자 그대로 같음을 실증했음 — build_system_prompt((), None, [], None, drill_count=5, drill_turns_min=4) == SYSTEM_PROMPT 가 True 이고 둘 다 2339자임. TASK-67 정정의 함의가 코드로 확인됐고 TASK-93·95 의 0/8 이 근거를 가짐. 그리고 제품 프롬프트를 앱과 같은 함수·같은 인자로 조립했음(4505자) — 인자 출처를 api/ws.py:286~293 으로 확정하고 손으로 지어내지 않았음.

⛔ 잃은 것 (AC#4): 그 프롬프트로 돌린 8회가 해석 불가임. 세션 ohmyenglish-40 이 지적하고 내가 nova.py 를 직접 읽어 확인했음 — :339~340 이 「대체 범위가 소리 줄이 있는 세션으로 한정된다」고 적고 :335~337 이 「규칙 9 는 문법 교정이 없는 턴에서도, 규칙 11 은 있는 턴에서 상호배제로 막는다」고 적음. 즉 소리 줄이 없는 갈래는 규칙 9·11 이 온전히 살아 있고 그 둘이 tool 0 을 이미 예측함. 픽스처가 아니라 분기 자체가 결과를 예측함 — pq* 구간의 순환과 같은 형태이고 이 세션의 네 번째 같은 기전임.

⚠️ 내가 반대로 읽었던 것: 「규칙 9 는 심한 발음(p2m)에서는 코칭을 허용하므로 0 이 예측값이 아니다」. 코드 주석이 반증함 — 규칙 9 가 막는 경로는 문턱이 아니라 Grammar first 이고 문법 교정이 없는 턴에서도 막음.

⛔ 「DB 에 계획이 없어 소리 줄 갈래를 못 잰다」도 틀렸음 — 계획이 낡은 것임. 최신 session_plans 가 2026-09-08 22:58 UTC 이고 발음에 초점 한 자리를 준 커밋이 4563f15(2026-09-09 23:35 UTC)임. 지금 코드로 계획을 재생성하면 그 갈래가 제품 데이터로 성립함 — TASK-81 AC#4 이고 선행 TASK-75 가 Done 이라 의존이 풀렸음.

⛔ 다음 회차가 사용자 결정 앞에 있음: 코칭 기준율 13% 라 P(4회 전부 0)=0.564 · P(≥1회 코칭)≥0.95 에 21회 필요. 계획 재생성은 공유 학습 데이터에 행을 더하고 워커 기동을 요구하며 그 순간부터 이 회차의 제품 프롬프트 4505자가 낡음. 예산과 워커·DB 쓰기가 함께 걸려 사용자 판단을 받음.

하지 않은 것: 워커 미기동 · DB SELECT 만 · 소스 미수정 · --tool-choice 미사용 · 보존 세션 불가침.
<!-- SECTION:NOTES:END -->
