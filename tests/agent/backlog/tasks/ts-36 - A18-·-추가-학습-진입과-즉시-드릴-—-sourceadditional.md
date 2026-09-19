---
id: TS-36
title: A18 · 추가 학습 진입과 즉시 드릴 — source=additional
status: Done
assignee: []
created_date: '2026-09-19 05:22'
updated_date: '2026-09-19 12:25'
labels: []
dependencies: []
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A18. 대상: 추가 학습 진입 경로(?source=additional)와 즉시 드릴 진입. 근거: PRD §7 Additional Learning · 설계서 2026-09-12-additional-learning-entry-design.md · 2026-09-08-immediate-drill-entry-design.md. ⛔ 세션 화면을 ?mode=… 쿼리로 열지 않음 — 페이지 로드 즉시 getUserMedia 가 불려 마이크 대체를 심을 틈이 없음(함정 H-CC). 쿼리 없이 / 로 열어 대체본을 먼저 심고 화면의 진입 버튼을 누를 것.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 하루 학습량을 채운 뒤에도 추가 학습을 시작할 수 있음
- [x] #2 추가 학습 종류(자유 대화·질문 다섯 개 더·자주 틀리는 패턴·업무 역할극·쉐도잉) 가운데 최소 셋이 진입됨
- [x] #3 자주 틀리는 패턴에서 즉시 드릴을 만드는 경로가 성립함 (requirements-summary 「이 문법으로 연습 만들어줘」)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-19 배치 B5 — AC#1·#2 확인, AC#3 미확인이라 Blocked. ⚠️ AC#3 은 「관측 차단」이 아니라 「기능 부재로 인한 실패」임 — 원장 상태를 Blocked 로 둔 것은 이 배치의 지시(AC 하나라도 미확인이면 Blocked)를 따른 것임. AC#1 — 회차 시작 시 오늘(KST) 완료 0건이었고 TS-20 의 스텁 세션이 앱 경로로 그것을 채웠음(daily-summary completed_today=true · completed_scenarios=1). 그 상태에서 추가 학습 버튼 다섯이 모두 세션을 열었고 집계가 2→6 으로 늘었음. 화면에 권장량 게이트가 애초에 없음. AC#2 — 다섯이 진입됨(최소 셋 요구): 자유 대화 e7eb8948(speaking) · 약점 패턴 집중 7523a66f(speaking) · 질문 답변 5개 5eb0702e(scenario_intake · generate_scenario job 이 더 걸려 4건) · 발음 집중 072f8489(pronunciation) · 쉐도잉 f2b9d9fb(shadowing). 다섯 모두 learning_source=additional · started_via=ui. 업무 역할극은 disabled 이고 그것은 설계가 정한 빈 칸이라 결함이 아님. 자유 대화와 약점 패턴 집중이 같은 행을 남기는 것도 진입점 설계서 §2 의 의도임. AC#3 미확인 — 결과 화면이 패턴을 보여 주기만 하고 동작이 없음 · pattern_key 가 React key 로만 쓰임 · SessionEntry 에 패턴을 실을 자리가 없음 · practice_current_pattern 이 app/ 안 0건. PRD.md:70 이 글자로 요구하고 TASK-7 이 소유자 없음으로 적어 둔 자리임 ⇒ 결함 TASK-233 등록. ⛔ 브라우저는 쿼리 없이 localhost:3000/ 로 열어 마이크 대체본을 먼저 심었음(H-CC·H-CA). 회차 문서 runs/2026-09-19-b5/result.md §6.

2026-09-19 회차 B8 — AC#3 의 화면 세 자리를 관측했고 넷째를 관측할 수단이 없어 미체크로 두었음. 상태는 Blocked 유지 (HEAD e482afa · 앱 소스 무변경 · 종료 HEAD b96e2be 는 원장 md 3개만 바꿨음).

전제를 먼저 만들었음: 그 절은 dailyPatterns.length > 0 일 때만 렌더되고 값은 GET /api/daily-summary 의 오늘(KST) 행에서 옴. 착수 시 오늘 행이 없었고(최근 행 2026-09-06) ts36_daily_seed.py 로 오늘 행 1건을 심었음. 고른 패턴은 verb_tense_past_simple_for_past_events 이고, 준비된 계획의 초점 둘(pronunciation_an_as_a · article_missing_before_noun)과 «겹치지 않는 것»을 고른 것이 그 선택의 전부임.

화면에서 직접 읽은 것 — 절 제목 h2 '오늘 무엇을 틀렸는지' · 카드 본문 4줄 · 링크 텍스트 '이 패턴으로 연습하기' · href '/?source=additional&pattern=verb_tense_past_simple_for_past_events' · 접근성 스냅샷의 paragraph > link [ref=e3]. 하이드레이션은 main 의 React 내부 키 2개로 판정했고 브라우저는 localhost(127.0.0.1 아님)로 열었음(H-CA).

누른 결과 — 같은 문서 안의 클라이언트 이동이었음(클릭 뒤에도 심어 둔 마이크 대체본이 살아 있었고 __b8.gum=1 로 «불린 것»까지 확인했음). 세션 수 27→28 정확히 1건. 그 행: 3fa98802-… · mode=speaking · learning_source=additional · started_via=ui · focus_pattern_key=verb_tense_past_simple_for_past_events · completed · 발화 6 · job 3.

⛔ AC#3 을 체크하지 않은 이유 — 남은 자리는 「준비된 계획이 있으면 지시문의 초점이 그 패턴으로 바뀜」이고 그것을 앱 경로에서 볼 표면이 없음. 확인한 표면 넷: session_started 이벤트(session_id·pronunciation_focus·shadowing 만 실음) · StubVoiceAdapter.instructions(보관만 함) · GET /api/sessions/next-plan(저장된 계획이고 소켓의 model_copy 사본이 아님) · session_plans 행(워커가 쓰고 워커는 꺼짐). 초점 대체 지점에 로그도 없음. ⇒ 결함 TASK-250 으로 올렸음.
통합 검사 test_ws_pattern_entry_records_the_choice_and_replaces_the_instruction_focus 를 이 회차에 직접 돌려 1 passed 를 봤음. ⛔ 그것으로 이 AC 를 체크하지 않음 — TS-4 노트와 같은 규약이고, 초점 대체는 이 AC 의 부수 조건이 아니라 구성 요소임(TASK-241 노트: '기록만 남고 지시문이 안 바뀌면 코치는 다른 것을 연습시키는데 「경로가 있다」로 보인다').

AC#3 문면의 괄호 인용은 «말로 하는» 요청(경로 A)의 문구이고 이 회차가 관측한 것은 화면 링크(경로 B)임. 두 경로를 가른 것은 구현 쪽 문서임(results/[sessionId]/page.tsx:179-181 · TASK-233 노트). 경로 A 는 코드에 자리가 없음 — start_additional 만 즉시 드릴에 닿고 그 AdditionalTarget 값역 넷에 패턴 키를 실을 자리가 없으며 practice_current_pattern 은 app/ 안 0건임 ⇒ 결함 TASK-251 로 올렸음(판정에 쓰지 않았음).

⚠️ 착수 지시의 전제 하나가 재현되지 않았음 — '주소를 직접 치면 대체본이 죽어 「마이크 권한을 요청하는 중입니다...」에서 멈춤'. orca goto 로 대체본 없이 주소를 직접 열었을 때 getUserMedia 가 원본(native)인 채로 resolve 했고 세션 df9e04d5-… 가 completed·발화 6건으로 끝났음. 두 경로의 결과가 같음. 기전 차이(같은 문서 이동이면 대체본이 살아남음)는 실재하므로 마이크 «내용»을 재는 회차에는 여전히 갈림.

⛔ 내 드라이버가 만든 가짜 결함 하나를 스스로 걸렀음 — orca tab create --url 로 진입 주소를 열면 세션이 2건 생겼고(28→30, 재현 30→32) 「직접 진입이 세션을 두 번 연다」로 올릴 모양이었음. /tmp/omy-frontend.log 가 갈랐음: tab create --url 은 같은 주소를 두 줄 남기고(/history·/results/5c0c614b-… 도 2줄) orca goto 는 1줄이며 세션도 1건임(32→33). ⇒ 드라이버 산물이고 앱 결함이 아님. 앱은 진입 문서 1회 로드당 세션 1건을 열음(진입 GET 다섯과 세션 다섯이 1대1).

증거: tests/agent/runs/2026-09-19-b8/result.md 5~7절 · evidence/TS-36-results-screen-card.json · evidence/TS-36-daily-summary-after-seed.json · evidence/TS-36-frontend-dev-log-entry-loads.txt · evidence/TS-36-daily-seed-restored.txt

2026-09-19 회차 B9 — AC#3 의 남은 넷째 자리를 관측해 체크하고 Done 으로 올렸음 (착수·종료 HEAD 모두 2b537ec · 앱 소스 무변경).

무엇이 남아 있었나: 「준비된 계획이 있으면 지시문의 초점이 그 패턴으로 바뀜」. B8 이 그것을 볼 표면이 없어 결함 TASK-250 으로 올렸고, 커밋 2b537ec 가 session_started 에 focus_pattern 을 실어 관측 가능해졌음.

⛔ 팔 하나로 판정하지 않았음 — 「키가 실렸다」만 보면 모든 세션에 싣는 구현도 통과하고 그것은 「일어나지 않은 대체를 보고한다」는 반대 방향 결함임. 부재를 뜻으로 읽는 대조 팔 둘을 두었음. 키 부재와 값 null 도 갈라 기록했음(계약이 「있을 때만 싣는다」이므로 null 은 위반임).

프레임에서 실제로 읽은 값 —
- 팔 A(드라이버 · ?source=additional&pattern=verb_tense_past_simple_for_past_events): session_started 키가 focus_pattern·session_id·type 셋이고 focus_pattern = verb_tense_past_simple_for_past_events. 세션 a331a4e5-…
- 팔 A′(실제 화면 클릭): 결과 화면의 link 「이 패턴으로 연습하기」[ref=e3] 를 눌렀고, 프런트가 연 소켓 주소를 직접 읽었음 — ws://localhost:8002/ws/session?source=additional&pattern=verb_tense_past_simple_for_past_events. 그 소켓 첫 프레임에 focus_pattern 이 같은 키로 실렸음. 세션 5cf40a76-… · 세션 수 30→31 정확히 1건. WebSocket 을 감싸 기록만 했고 프레임을 삼키거나 바꾸지 않았음.
- 팔 B(패턴 없이 추가 학습): 키가 session_id·type 둘뿐 — focus_pattern 키 자체가 없음. 세션 행 focus_pattern_key = NULL. 세션 1bd11c50-…
- 팔 C(없는 키 존재하지않는키_b9): focus_pattern 키 없음 · 세션은 그대로 열림(completed · 발화 6) · 세션 행 focus_pattern_key 에 그 키가 남음. 세션 1e755344-… ⇒ 「기록은 남기지만 대체는 보고하지 않는다」가 성립함.

재현: 팔 C 를 다른 없는 키(없는키_두번째_b9)로 한 번 더 돌려 같은 결과를 봤음(세션 731770c9-…). 간헐 아님. 팔 A 는 진입 수단이 다른 둘에서 같은 값을 냈음.
관측력 증명(§7-7): 팔 B·C 의 「없음」을 기대값으로 읽는 근거는 같은 드라이버가 팔 A 에서 그 키를 실제로 잡았다는 것임.

⚠️ 전제 하나를 착수 지시와 다르게 확인했음 — 대체가 성립할 조건은 error_patterns 이고 daily_error_summary 가 아님(load_focus_pattern 의 SQL · services/sessions.py:302-307). 그 표에 그 키가 있어 팔 A 가 성립했음. daily_error_summary 시드는 화면 카드를 띄우는 조건일 뿐임.

⛔ 관측하지 않은 갈래 하나: 「계획이 없으면 키만 세션 행에 남음」(AS4 규약). 재려면 최신 session_plans 행을 없애야 하고 그것은 회차가 만들지 않은 기존 행의 삭제라 허용 범위 밖임. AC#3 의 구성 요소가 아니라 계획 부재 시의 퇴화 동작이므로 판정에 쓰지 않았음.

⚠️ AC#3 문면의 괄호 인용(「이 문법으로 연습 만들어줘」)은 «말로 하는» 요청(경로 A)이고 이 회차가 관측한 것은 화면 링크(경로 B)임 — B8 과 같은 갈림이고 경로 A 는 여전히 코드에 자리가 없어 TASK-251 로 열려 있음. 이 배치의 지시가 판정 범위를 팔 셋으로 정했고 그 셋이 다 성립해 체크했음.
⛔ 고친 쪽이 판별력 근거로 든 인프로세스 통합 검사는 이 판정에 쓰지 않았음(TS-4 노트와 같은 규약).

새로 등록한 결함 0건. 정리: 회차가 만든 세션 5건 전부 teardown(session_deleted 1 · 잔존 0 · analysis_jobs 잔존 0) · 세션 수 27→32→27 · daily 시드 되돌림 확인(오늘 행 없음 = 기준선) · Orca 탭 닫음 · 워커 안 켰음 · 유료 호출 0건.
증거: tests/agent/runs/2026-09-19-b9/result.md 4·5절 · evidence/TS-36-arm{A,A-browser,B,C,C-repeat}-session-started.json · evidence/TS-36-session-rows-three-arms.txt · evidence/99-cleanup-verified.txt
<!-- SECTION:NOTES:END -->
