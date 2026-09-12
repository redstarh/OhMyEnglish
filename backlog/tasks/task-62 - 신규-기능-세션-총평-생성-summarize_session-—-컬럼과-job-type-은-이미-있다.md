---
id: TASK-62
title: '신규 기능: 세션 총평 생성 (summarize_session) — 컬럼과 job type 은 이미 있다'
status: Done
assignee: []
created_date: '2026-09-09 13:11'
updated_date: '2026-09-12 17:28'
labels: []
dependencies: []
ordinal: 65000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
learning_sessions.summary 컬럼과 analysis_jobs.job_type 의 summarize_session 값이 이미 있고 설계서가 「summary(세션 총평)는 summarize_session 과 함께 다음 슬라이스에서 채워진다」고 지정했다. 아직 구현이 없다. ⛔ 요구사항인데 원장에 태스크가 없었다 — 2026-09-09 사용자 질문에서 발견했다.

참고: realtime-meeting 이 같은 부류를 구현했고 그 방식이 배울 만하다 — 세션 종료 시 자동 생성 · 템플릿 지정 가능 · 구획 5개 · ⛔ 재생성 시 원자 교체(부분 실패로 반쯤 덮이지 않게) · 동시 재생성에 409. ⚠️ 우리는 회의록이 아니라 학습 총평이라 형식은 다르지만 「생성·재생성」 구조 문제는 같다. 근거는 docs/design/2026-09-09-realtime-meeting-fit-gap.md 다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 summary 를 무엇으로 채울지 정한다 — 학습 총평의 구획을 요구사항에서 유도하고 발명하지 않는다
- [x] #2 ⛔ summary 컬럼의 소유권을 지킨다 — 설계서 §2.3 이 그 컬럼을 다른 용도로 쓰려던 시도를 H-2 로 기각했다. 그 판단을 뒤집지 않는다
- [x] #3 재생성이 원자적이게 만든다 — 부분 실패로 반쯤 덮이지 않고 동시 요청이 충돌로 드러난다
- [x] #4 TASK-60 과 함께 토큰 사용량을 기록한다 — 총평 생성도 돈이 나가는 호출이다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
착수 2026-09-13 (세션 ohmyenglish-f4) — 사용자 결정 87 로 이 태스크가 다음 기능으로 정해졌음. 기각된 후보는 TASK-26·TASK-61·TASK-88 임.

⛔ 자산을 직접 확인했음 — 새 마이그레이션이 필요하지 않음:
- learning_sessions.summary jsonb not null default '{}' (001_initial_schema.sql:46)
- analysis_jobs.job_type 의 summarize_session (001:138 · 007:71 · 018:51 의 CHECK)
- analysis_jobs_target_matches_job_type 의 그 분기 (001:152 · 007:77 · 018:64)

⚠️ 방금 닫은 generate_scenario job 경로와 같은 모양임(세션 종료 → job → 워커 → 트랜잭션 밖 Claude → 저장 + complete). 그 경로의 규약과 함정은 services/scenario_generator.process_scenario 와 회차 runs/2026-09-13-task102-intake-pipeline/ 이 가짐 — 특히 워커 실행체의 분기를 «종류마다 지목» 하도록 고쳐 둔 것이 이 job 에도 필요함(p5_worker_leg.py 에 summarize_session 분기가 아직 없음).

완료 2026-09-13 (세션 ohmyenglish-f4). 설계서 docs/design/2026-09-13-session-summary-design.md · 계획서 docs/design/2026-09-13-session-summary-plan.md 의 다섯 태스크가 모두 끝났음. 마이그레이션 0건(컬럼·job 종류·CHECK 분기가 이미 있었음).

AC#1(무엇으로 채우나) — 유도했고 발명하지 않았음. nova-sonic-claude-architecture.md §4.3 의 한 행이 세 항목을 묶어 말하는데 소유자가 셋임: 잘한 점·핵심 약점은 이 태스크 · 다음 세션 계획은 session_plans · R11-10 의 관찰 기록은 learner_notes. ⇒ 총평은 둘만 담음. ⛔ 점수·등급은 «값역»으로 막았음(문면이 아니라 구조) — R11-8·R13-5 의 경계임.

AC#2(컬럼 소유권) — H-2 의 판단을 뒤집지 않았음. 별 표를 만들지 않고 learning_sessions.summary 를 그대로 씀.

AC#3(원자 재생성) — 저장이 한 UPDATE 이고 같은 트랜잭션에서 complete 함. 사용자 결정으로 재생성 경로를 만들지 않았으므로 두 번 쓰이는 유일한 경로가 재시도이고 그 트랜잭션이 그것을 닫음.

AC#4(토큰 기록) — purpose='summarize_session' 으로 넘김. ⛔ 그 과정에서 확정 결함을 찾았음: llm_calls_purpose_check 가 넷뿐이라 generate_scenario 의 기록이 «조용히 사라지고» 있었음(usage.py 가 PostgresError 를 삼킴). 마이그레이션 021 로 값역을 늘렸고 TASK-134 로 등록했음 — dev DB 적용은 승인 사안이라 하지 않았음.

사용자 결정 넷: 범위는 결과 화면까지 · 재생성 없음 · 문구는 한국어(인용은 영어 원문) · job 을 따로 둠. 그리고 결정 87 이 이 태스크를 다음 기능으로 정했음.

📌 이웃 job 과 일부러 다른 자리 하나 — 발화 0건 세션은 모델을 부르지 않고 빈 배열 둘을 써서 done 으로 닫음. 연결만 하고 끊은 세션이 흔하므로 report_failure 로 보내면 5회 헛돌고 failed 가 상시 쌓임. {}(아직 없음)와 빈 배열(담을 것이 없었음)의 구별이 값의 «모양» 에 있고 API·화면까지 그 구별이 도달함.

⚠️ 기존 테스트 여섯이 깨졌고 전부 「job 이 셋이 된 것」 때문이었음 — 재던 축을 갈래별로 좁혀 고쳤음(전체 개수를 세던 자리 셋 · claim_next 가 남의 job 을 집던 자리 하나 · 대역이 응답을 순서로만 주던 자리 하나).

게이트(이 턴 직접 실행): pytest 1130 passed · ruff 안 0 · 밖 0 · format 0 · ty 0 · 프런트 tsc exit 0 · eslint exit 0.
<!-- SECTION:NOTES:END -->
