---
id: TS-36
title: A18 · 추가 학습 진입과 즉시 드릴 — source=additional
status: Blocked
assignee: []
created_date: '2026-09-19 05:22'
updated_date: '2026-09-19 12:09'
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
- [ ] #3 자주 틀리는 패턴에서 즉시 드릴을 만드는 경로가 성립함 (requirements-summary 「이 문법으로 연습 만들어줘」)
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
<!-- SECTION:NOTES:END -->
