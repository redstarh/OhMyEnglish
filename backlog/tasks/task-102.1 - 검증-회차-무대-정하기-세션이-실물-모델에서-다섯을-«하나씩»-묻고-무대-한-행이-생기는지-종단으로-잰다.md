---
id: TASK-102.1
title: '검증 회차: 무대 정하기 세션이 실물 모델에서 다섯을 «하나씩» 묻고 무대 한 행이 생기는지 종단으로 잰다'
status: In Progress
assignee: []
created_date: '2026-09-12 15:04'
updated_date: '2026-09-12 15:23'
labels: []
dependencies: []
parent_task_id: TASK-102
ordinal: 144000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-5 Task 6 이 배선을 끝냈고 게이트 넷이 초록이지만, 「문면이 실제로 그 행동을 유도하는가」는 재지 않았음. 결정 50 이 그 부류를 스파이크만으로 닫지 않기로 정했음. ⛔ 실물 Nova 세션은 사용자 승인 사안임(결정 38·39 의 선례) — 마이크가 필요하므로 사람이 있어야 함. 조립된 문면은 build_system_prompt(..., scenario_intake=True) 로 출력해 확인했음(질문 다섯이 순서대로 · one at a time · Do not invent).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 먼저 스텁 어댑터로 «파이프라인»만 잰다 — ?mode=scenario_intake 로 열고 종료해 analysis_jobs 에 generate_scenario 가 걸리는지, 워커가 그것을 처리해 source='generated' 행이 생기는지 앱 경로에서 확인한다. ⛔ 이 회차는 사람 없이 돌 수 있으므로 실물 세션보다 먼저 한다
- [ ] #2 실물 Nova 세션 1회로 «다섯을 하나씩 묻는가»를 잰다 — 회차 전에 승인을 받고, 코치가 한 턴에 여러 질문을 묶는지·답을 못 받은 축에서 지어내는지를 전사문으로 센다. ⛔ 1회 관측을 비율로 읽지 않는다
- [x] #3 생성된 무대가 배치 규칙에 실제로 집히는지 확인한다 — display_order 0 · is_generated True 인 행이 신규 차례에서 시드보다 «먼저» 나오는지(결정 80). ⚠️ 단위 테스트는 그것을 순수 함수로 이미 재므로 여기서는 DB 행으로 잰다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
진행 2026-09-13 (세션 ohmyenglish-f4). AC#1·AC#3 을 닫았음. 회차 정본은 tests/harness/runs/2026-09-13-task102-intake-pipeline/README.md 임.

⛔ 공유 dev DB·:8002 를 건드리지 않았음(H-BC) — 검증 전용 DB ohmyenglish_v102(소유자 ohmy) + :8022 · VOICE_ADAPTER=stub · WORKER_ENABLED=false. teardown 뒤 dev DB 를 조회해 seed 30 · generated 0 · scenario_intake 세션 0건을 확인했음.

AC#1 앞 절반(앱 경로): 세션 둘 다 session_started → 세션 행 mode='scenario_intake' → 종료 뒤 generate_scenario·plan_next_session 둘 다 pending. 실행체는 그 회차 디렉터리의 intake_stub_leg.py 이고 --url·--dsn 에 기본값을 두지 않았음(빠뜨린 실행이 dev DB 에 남는 것을 막음).

AC#1 뒤 절반(워커): 실물 Claude 로 거부와 성공을 같은 회차에서 쟀음. 거부 팔(스텁 픽스처 전사문) → status=pending · attempts=1 · last_error 가 ScenarioValidationError: category None(허용 목록에 shadowing 이 없는 것도 함께 관측됨) · 생성 0행. 성공 팔(질문 다섯 문답 10줄을 심음) → status=done · attempts=1 · 생성 1행(category=business · level=A2 는 users.current_level 에서 온 값 · source=generated · display_order=0).

⛔ p5_worker_leg.py 에 generate_scenario 분기를 더해야 돌았음. 더하기 전에는 마지막 else 로 떨어져 process_analysis 로 갔고 그 함수는 종류가 다르면 실패로 보고하므로 5회 재시도 뒤 영원히 failed 였음. 분기를 종류마다 지목하도록 바꾸고 모르는 종류는 exit 5 로 거부하게 했음.

AC#3: _pick_scenario_for_user 를 그 DB 에 직접 돌려 pick=new · source=generated 를 얻었음. ⛔ 그 관측 하나로는 근거를 못 가름 — 생성 행의 display_order 가 0 이고 시드가 1..30 이라 「생성이 먼저」와 「자리가 앞」이 같은 답을 냄. 그 행의 display_order 를 99 로 밀어 다시 돌렸더니 여전히 먼저 집혔음 ⇒ 이기는 것은 _staleness 의 맨 앞자리(is_generated)이고 019 의 기본값 0 이 아님. 밀었던 값은 0 으로 되돌렸음.

⚠️ 결함 후보 하나를 TASK-133 으로 등록했음 — 생성된 title 이 한국어이고 시드 30행은 전부 영어임. 프롬프트가 언어에 침묵하고 게이트도 침묵함. 어느 쪽이 정본인지는 제품 판단임.

⛔ AC#2 는 열려 있음 — 실물 Nova 1회가 필요하고 마이크가 있어야 하므로 사용자 승인 사안임(결정 38·39 의 선례).

게이트(이 턴 직접 실행 · 종료코드 확인): pytest 1088 passed(exit 0 · 동료 세션이 독립으로 센 값과 일치) · ruff 안 0 · 밖 0 · format 0(206 files) · ty 0 · 두 실행체 --help exit 0.
<!-- SECTION:NOTES:END -->
