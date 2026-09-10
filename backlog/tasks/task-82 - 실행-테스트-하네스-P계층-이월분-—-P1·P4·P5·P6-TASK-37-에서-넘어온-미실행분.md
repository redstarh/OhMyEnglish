---
id: TASK-82
title: '실행: 테스트 하네스 P계층 이월분 — P1·P4·P5·P6 (TASK-37 에서 넘어온 미실행분)'
status: In Progress
assignee: []
created_date: '2026-09-09 23:25'
updated_date: '2026-09-10 00:00'
labels: []
dependencies: []
ordinal: 85000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-37(5차수)이 Done 으로 닫혔으나 P계층 네 시나리오가 앱 경로를 지나간 적이 없다 — 이월분의 소유자가 없어 신설한다. 절차 실측본은 tests/harness/runs/2026-09-10-task78-app-path.md §1·§7 이고 시나리오 정본은 tests/harness/scenarios-P-pronunciation.md 다. TASK-65 가 확정한 사실(세션의 첫 발화가 이후 턴의 ASR 언어를 고정한다)이 P4·P12 의 관측 경로를 바꿨다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 P4(p2k): 강한 억양 픽스처를 세션의 «첫» 발화로 주어 앱 경로에서 관측하고 원자료를 회차 파일에 남긴다 — 다른 발화 뒤에 두면 구조적으로 관측 불가다
- [x] #2 P1(p2a): 정확 발음 기준선을 앱 경로에서 얻는다 — 4차수는 p1 쌍만 돌렸고 p2a·p2k 는 앱 경로 미통과다
- [ ] #3 P5: 한글 전사문의 분석 처리를 관측한다. 워커가 필요하므로 H-AT 를 먼저 읽고 구간을 좁혀 켜고 즉시 되돌린다
- [ ] #4 P6: error_patterns 에 발음 오류 오탐이 생기는지 같은 세션에서 확인한다 — 생기면 frequency 오염이다
- [x] #5 teardown: 시각창으로 잡고 7개 표를 기준선과 대조한다. 보존 세션 6개(210233be·6225ddaf·b2f0d169·76d9ef31·d127dece·e0c5e580) 전건 생존을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 착수 (ohmyenglish-40 · HEAD 67f7608). 인계 4지표를 직접 돌려 전건 대조했고 ohmyenglish-39 가 독립으로 얻은 값과도 일치함 — pytest 884 passed · ruff check exit 0 · format unformatted 0 · ty 통과 · 게이트 밖 ruff 0건 · 프론트 tsc·eslint exit 0. DB 9개 표와 결과 API 상태 6개도 HANDOFF 기록과 일치(보존 세션 6개 전건 생존). 유일한 차이: HANDOFF 지표 2 가 In Progress 3건으로 적었으나 실제 4건임 — TASK-81 이 2026-09-09 23:23 에 In Progress 였는데 그 집계에서 빠졌음(To Do 21 대 20 도 같은 원인). 원장이 정본이라 HANDOFF 쪽 수치가 낡은 것으로 판정함.

신설 근거: TASK-37(5차수)이 Done 으로 닫혔으나 P1·P4·P5·P6 가 판정되지 않아 이월분의 소유자가 없었음. HANDOFF 가 「TASK-37 P계층 이월분」으로 가리켰지만 그 태스크는 이미 닫혀 상태를 올릴 자리가 없었음.

⚠️ HANDOFF 의 「p2a·p2k 는 앱 경로를 지나간 적이 없다」는 정확하지 않음 — runs/2026-09-10-task78-app-path.md §2 가 p2a → 무음 → p2k 를 한 세션에 흘렸음. 정확히는 「P4 의 관측 조건(p2k 를 첫 발화로)이 충족된 적이 없다」임. 그 회차는 p2a 를 첫 발화로 줬으므로 p2k 차례에는 ASR 언어가 이미 영어로 고정됐음.

AC#1·AC#2 를 app-test-agent(p-layer-p4p1)에 위임함 — nova 재기동 · p2k 단독 세션 · p2a 단독 세션 · teardown 대조. AC#3(P5)·AC#4(P6)는 워커가 필요해 위임하지 않았음: H-AT 의 경로 둘(기존 pending job 을 집는다 · flush_ended_sessions 가 job 을 새로 만든다) 때문에 보존 세션이 두 번 파괴됐고, 그 절차는 팀리드가 직접 감독함.

P5 착수 전 전제 — 2026-09-10 이 턴에 DB 에서 직접 읽었음 (읽기만 함):

| 보존 세션 | job_type | status | attempts | available_at <= now() |
|---|---|---|--:|---|
| 210233be | plan_next_session | pending | 0 | true |
| 76d9ef31 | plan_next_session | pending | 0 | true |
| b2f0d169 | plan_next_session | pending | 0 | true |
| d127dece | plan_next_session | pending | 0 | true |
| e0c5e580 | plan_next_session | done | 1 | true |

⛔ H-AT 경로 ①(기존 pending job 을 집는다)이 지금도 실재함 — 보존 세션 4건이 즉시 claim 가능한 job 을 갖고 있음. 워커든 claim_one 이든 부르면 이 넷이 먼저 집힐 수 있음. 따라서 P5 는 available_at 을 미래로 비켜 두고 원래 값을 파일로 뜬 뒤에만 진행함.

⚠️ H-AT 의 서술 하나가 지금 데이터와 어긋남 — 그 함정은 d127dece(no_utterances)를 「job 0건이어서 ①의 방어가 닿지 않은」 사례로 적었으나 지금은 pending job 1건을 가짐. 즉 지금은 ①의 방어가 여섯 전건에 닿음. 그 사고 뒤 복구 과정에서 job 이 생긴 것으로 보이나 확정하지 않았음. P5 를 실제로 돌린 뒤 실측과 함께 pitfalls 를 고칠 예정임.

P5 를 워커 전체로 돌리지 않는 근거: analysis_worker.run_worker 는 루프 안에서 sweep_lost_runs 를 부르고 그것이 flush_ended_sessions 를 부름(analysis_worker.py:54·67) — H-AT 경로 ②가 그 자리임. claim_one(analysis_worker.py:92)과 job 처리만 직접 1회 부르면 그 경로를 구조적으로 지나가지 않음. ⚠️ 단 claim_next 는 호출마다 reaper 를 함께 돌려 lease 만료 + attempts 소진된 running job 을 failed 로 만듦(jobs.py:145 주석) — 지금 보존 세션 job 에 running 이 0건이라 대상이 없으나, P4 세션이 만든 job 이 running 으로 남은 채 재호출하면 걸릴 수 있음.

⛔ 정정 — 위에 적은 「HANDOFF 지표 2 가 낡았다」는 판정을 철회함. HANDOFF 기록(In Progress 3건)이 정확했고 내가 틀렸음.

근거(이 턴에 직접 돌림): date -u 가 2026-09-09 23:30 이고 date 가 2026-09-10 08:30 KST 임. backlog 의 created_date·updated_date 는 UTC 로 적히므로 TASK-81 의 updated_date 2026-09-09 23:23 은 어제가 아니라 KST 08:23 — 즉 HANDOFF 마감 «이후» 임. ohmyenglish-39 가 그 시각에 TASK-81 을 In Progress 로 올렸고 그 세션의 인계 대조 출력이 그 전에 In Progress 3건을 냈음.

이것이 CLAUDE.md 의 DB 시각 규약이 경고하는 바로 그 구간임 — UTC 자정부터 09:00 KST 까지는 UTC 날짜가 KST 날짜보다 하루 이름. 원장 파일의 날짜를 KST 로 읽으면 「어제부터 열려 있었다」로 오독함. ⛔ 마감 기록을 사후 상태로 덮지 않음 — 그 시점에 무엇이 열려 있었는지를 잃음.

P6 기준선 — error_patterns 9행 전문을 이 턴에 직접 읽었음:
article_missing_before_noun 7/occ7 · article_missing_the_before_place_noun 5/occ5 · article_wrong_definite_article 2/occ2 · business_expression_verb_noun_collocation 3/occ3 · preposition_missing_to_after_go 1/occ1 · preposition_time_expression_ago 3/occ3 · pronunciation_an_as_a 2/occ0 · verb_tense_past_simple_for_past_events 2/occ2 · word_order_time_adverb_placement 1/occ1. 전건 next_review_at 이 채워져 있음.

⚠️ pronunciation_an_as_a 만 frequency 2 인데 error_occurrences 가 0행임 — H-AT 가 적은 「발음 패턴은 pronunciation_attempts 에서 세므로 두 writer 의 규약이 다르다」가 데이터로 확인됨. 따라서 P6 오탐 판정은 문법 카테고리 쪽 pattern_key 신설과 frequency 증가로 재고, 발음 카테고리의 frequency 는 occurrence 수로 검산하지 않음.

⚠️ error_patterns 에 target_sound 컬럼이 없음 — 발음 패턴은 pattern_key 로 표현함(스키마 직접 확인). category CHECK 는 pronunciation_intonation 을 허용함.

P4 관측 — 팀리드가 DB 에서 직접 읽음 (2026-09-09 23:34 UTC · 세션 ae0001c8):

전사문이 한글로 나왔음: 「아이티니시프트 리포트 n c o d 더 이절치위드 마이팀」. p2k 를 세션의 첫 발화로 준 조건에서 P4 의 핵심 단정이 재현됐음. TASK-65 가 확정한 기전(첫 발화가 ASR 언어를 고정함)이 앱 경로에서 성립함.

agent 발화 전문: 「I see you want to talk about a report. Let's start with a simple sentence about your weekend. What do you want to do this weekend?  Try saying: "I want to make a plan."」 — 재요청(unclear 류)을 하지 않았고 발음 언급도 0건임. 학습자가 알아들을 수 없게 말했는데 agent 가 주제를 넘김.

⛔ 새 발견 — korean_transcript 보조 신호가 앱 경로에서 처음 발동했음. pronunciation_attempts 가 기준선 4에서 5로 늘었고 그 행은 signal_source=korean_transcript · outcome=unclear · target_form=「(전사문이 한국어로 인식되었습니다)」 · spoken_form=위 한글 전사문 · pattern_id NULL · target_sound NULL · attempt_seq 13 임.

⚠️ 이것이 두 문서의 미확인 서술을 닫음: scenarios-P-pronunciation.md §3.2 가 「그 신호가 여태 0행인 이유의 유력한 설명」을 적고 「앱 경로에서 직접 확인한 것은 아님」이라 단서를 달았는데, 이 회차가 앱 경로에서 발동을 확인했음. 그리고 HANDOFF·runs/2026-09-10-task78-app-path.md 의 「pronunciation_attempts 델타 0」은 p2a 를 첫 발화로 준 조건의 값이고 첫 발화 조건을 바꾸면 델타가 1이 됨 — 조건이 다르므로 둘은 모순이 아님.

⚠️ TASK-74(보조 신호에서 복습 시계를 돌릴지) 판정의 직접 재료임 — 보조 신호 행은 pattern_id 와 target_sound 가 둘 다 NULL 이고, 대조로 기존 nova_tool 행은 둘 다 가짐(target_sound=an_as_a). 이 세션에서 error_patterns·error_occurrences 델타가 0임(9 · 24 그대로). 즉 보조 신호는 시도를 기록하지만 복습 시계를 걸 재료를 만들지 못함. ⛔ 표본 1건이라 단서이고 확정이 아님 — 판정은 TASK-74 소유임.

보존 세션 job 무변동 확인 — 5건 전건의 created_at 이 09-06·09-08 그대로이고 새로 만들어진 것 0건임. H-AT 경로 ② 징후 없음(워커를 켜지 않았으므로 예상대로임).

⛔ 정정 2 — 위에 적은 「보존 세션 job 5건」과 「H-AT 경로 ② 징후 없음」의 근거가 불완전했음. 실제 보존 세션 job 은 8건임.

기전: analyze_utterance job 은 session_id 가 NULL 이고 utterance_id 로만 세션에 매임. 내가 쓴 술어 left(j.session_id::text,8) = any(...) 가 NULL 비교로 그 행들을 조용히 버렸음. 이 턴에 직접 센 값 — analyze_utterance 43건 전부 session_id NULL · utterance_id 만 있음. plan_next_session 6건은 그 반대임.

그 결함이 p5_worker_leg.py 의 guard 에도 그대로 들어갔음. 위임 에이전트가 claim 을 돌리기 «전에» 발견해 멈췄음. utterance 경유로 해소하니 claim 가능한 보존 job 이 8건이고, claim_next 가 집을 첫 job(order by available_at limit 1 — jobs.py:203~204 직접 확인)이 210233be(C3a)의 analyze_utterance d3272c2c 였음. guard 가 잡은 plan job 들보다 5ms 이름.

⛔ 그 손상은 verify 로도 안 보였을 것임 — results.py 의 _JOB_COUNTS_SQL 이 status in ('pending','running') 를 함께 non_terminal 로 세므로 pending→running 으로 바뀌어도 세션이 계속 analyzing 임. H-AT 가 말한 「피해가 눈에 안 보인다」의 또 다른 형태임.

⚠️ 앱에는 정답이 이미 있었음 — 그 SQL 자신이 join utterances u on u.id = j.utterance_id 로 세션을 해소함. 내 새 스크립트가 그 관례를 따르지 않은 것이 원인임. 함정 H-AX 로 등록했음.

⚠️ 그리고 이 사고의 정확한 기전은 「틀린 술어가 자기 자신을 통과시킨 것」임 — guard 의 사후 검사도 같은 술어였으므로 「전건 claim 불가」라는 거짓 안심을 출력했음. 보호 대상을 세는 방어는 다른 술어로 교차 검산해야 함.

AC#3·AC#4 는 에이전트가 스크립트를 고친 뒤 진행함. 검증은 내가 함 — 작성과 검증을 같은 눈으로 하지 않기 위해 내가 원저자인 파일의 수정을 에이전트에 맡겼음.
<!-- SECTION:NOTES:END -->
