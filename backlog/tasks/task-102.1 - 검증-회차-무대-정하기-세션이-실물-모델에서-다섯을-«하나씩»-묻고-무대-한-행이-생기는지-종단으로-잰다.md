---
id: TASK-102.1
title: '검증 회차: 무대 정하기 세션이 실물 모델에서 다섯을 «하나씩» 묻고 무대 한 행이 생기는지 종단으로 잰다'
status: Done
assignee: []
created_date: '2026-09-12 15:04'
updated_date: '2026-09-12 15:54'
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
- [x] #2 실물 Nova 세션 1회로 «다섯을 하나씩 묻는가»를 잰다 — 회차 전에 승인을 받고, 코치가 한 턴에 여러 질문을 묶는지·답을 못 받은 축에서 지어내는지를 전사문으로 센다. ⛔ 1회 관측을 비율로 읽지 않는다
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

AC#2 진행 2026-09-13 — ⛔ 절반만 닫혔으므로 체크하지 않음. 회차 정본은 tests/harness/runs/2026-09-13-task102-intake-pipeline/README.md §4-2 임.

사용자 승인(결정 85)을 받고 실물 Nova 세션 1회를 돌렸음. 격리는 검증 전용 DB ohmyenglish_v102b + :8022 · VOICE_ADAPTER=nova · WORKER_ENABLED=false 이고 teardown 뒤 dev DB 무오염을 확인했음(seed 30 · scenario_intake 세션 0건).

닫힌 것: ⛔ 코치가 한 턴에 여러 질문을 묶지 않았음 — 2 턴 중 0 턴이고 물음표가 각각 0개·1개임. 그리고 그 1개가 질문 1(무대)을 프롬프트 문면 그대로 냈음(`Where do you need English soon? Tell me the place.`). 그것이 이 축의 가장 큰 위험이었음.

닫히지 않은 것 둘: ⑴ 다섯을 끝까지 순서대로 묻는가 — 코치 턴이 둘뿐이었고(픽스처 WAV 가 둘이라 거기서 끝남) 질문 2~5 의 순서·단독성은 관측되지 않았음 ⑵ 답을 못 받은 축을 지어내는가 — 그 상황이 생기지 않았음(학습자가 「모르겠다」를 말한 적이 없음).

⚠️ 관측 조건의 한계 둘: 픽스처가 발음 회차용 문장이라 질문의 답이 아니었고(그래서 첫 코치 턴이 방향을 잡는 데 쓰였음 — 지시문의 결함이 아니라 입력의 성질임) · 코치가 먼저 말하지 않았음(하네스가 곧바로 오디오를 흘리므로 「학습자 오디오 없는 첫 턴」 팔은 지나가지 않았음).

⚠️ 첫 시도가 세션을 하나 더 만들고 죽었음 — ws_session.py 가 harness_sessions 표를 요구하는데 검증 DB 에 없었음(하네스 전용 표이고 마이그레이션에 없음). 오디오 전에 죽었으므로 관측 0이고 Nova 스트림도 열리지 않았음 ⇒ 실물 스트림이 실제로 돈 것은 1회임.

⛔ 남은 둘을 재려면 실물 세션이 한 번 더 필요하고 그것은 다시 승인 사안임 — 승인은 「1회」였고 그 1회를 썼음.

AC#2 완료 2026-09-13 — 사용자가 실물 Nova 1회를 «더» 승인해 2회차를 돌렸음. 회차 정본은 그 회차 §4-3 임.

1회차의 미산 원인이 «입력» 이었으므로 답 픽스처 여섯을 만들었음(tests/harness/gen_si_fixtures.sh · si00~si05 · 목소리·포맷을 gen_pq_fixtures.sh 와 같게 뒀음). ⚠️ si00 은 답이 아니라 여는 인사임 — Nova 가 오디오 전에 말하지 않는 것을 1회차에서 관측했고 그러면 학습자가 먼저 한마디 하는 것이 제품의 실제 경로임. ⛔ 관측을 요구로 바꾸지 않았음. ⚠️ si04 = I don't know. 가 「지어내는가」를 재는 유일한 입력임.

닫힌 것 ①: ⛔ 다섯을 설계서 §3 의 순서 그대로 턴마다 하나씩 물었음 — 5/5 이고 묶은 턴 0건임. ⚠️ 물음표 개수를 질문 개수로 읽지 않음 — 2번 축의 턴은 물음표가 2개인데 축은 하나임(블록 문면이 예시로 담은 A colleague? 임). 즉 단정은 「물음표 1개」가 아니라 「축 하나」여야 함.

닫힌 것 ②: ⛔ 지어내지 않았음. 전사문에 초점(무엇이 가장 어려운가)의 답이 없는데 만들어진 무대에도 그 축이 없음 — 담긴 것은 무대·상대·목표·어조 넷임. ⛔ 판별력의 근거는 「무대에 초점이 없다」 하나임 — 코치가 That is fine. 을 낸 것과 다음으로 넘어간 것은 두 기전을 가리지 못함(코치는 어차피 순서를 밟음).

📌 결정 84(제목은 영어)가 실물에서 확인됐음 — 프롬프트를 고친 뒤 만든 첫 무대의 제목이 영어임(Reporting your project status in the weekly team meeting). §4 의 한국어 제목과 같은 경로·같은 모델이고 바뀐 것은 프롬프트 한 줄임.

⚠️ 재지 못한 것을 적어 둠: 「답을 듣고 다음으로 넘어간다」 — 하네스가 정해진 순서로 오디오를 흘려 학습자 발화와 질문이 한 칸 어긋났음. 코치는 무엇이 오든 순서를 밟았으므로 위 판정은 흔들리지 않지만 응답성 자체는 이 회차의 요구가 아니었음.

⚠️ ws_session.py 를 --no-register 로 불렀음 — 1회차에서 harness_runs·harness_sessions 를 손으로 만든 것은 «불필요했음»(발음 축이 그 플래그를 알려 주고 내가 ws_session.py:189 에서 직접 확인했음).

teardown: 회차마다 :8022 를 죽이고 검증 DB 셋(v102·v102b·v102c)을 drop 했음. dev DB 무오염을 매번 조회로 확인했음(seed 30 · generated 0 · scenario_intake 세션 0건).
<!-- SECTION:NOTES:END -->
