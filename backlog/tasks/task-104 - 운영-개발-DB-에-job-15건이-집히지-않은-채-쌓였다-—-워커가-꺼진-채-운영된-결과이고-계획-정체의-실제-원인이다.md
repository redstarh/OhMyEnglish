---
id: TASK-104
title: '운영: 개발 DB 에 job 15건이 집히지 않은 채 쌓였다 — 워커가 꺼진 채 운영된 결과이고 계획 정체의 실제 원인이다'
status: Done
assignee: []
created_date: '2026-09-10 23:54'
updated_date: '2026-09-11 22:44'
labels: []
dependencies: []
ordinal: 107000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-100 조사가 확정했음. session_plans 최신 행이 2026-09-08 22:58 UTC 에 멈춘 원인은 JSON 파싱 결함이 아니고 «그 job 을 아무도 집지 않은 것»임.

실측 근거 둘 (2026-09-11 · 직접 조회):
1. pending 15건(analyze_utterance 7 · plan_next_session 8) 전부 attempts=0 이고 last_error 가 null 임 — 실패한 흔적이 없음.
2. 떠 있는 백엔드(:8002 · PID 25563 · 2026-09-10 16:27 KST 기동)의 환경이 WORKER_ENABLED=false 임 (ps -Eww 로 직접 확인). VOICE_ADAPTER=nova.

⚠️ 이것은 제품 결함이 아니라 운영 구성의 결과임. tests/harness/browser_leg.md 가 «WORKER_ENABLED=false 는 선택이 아니다» 를 규약으로 못박았고(보존 세션 C3a·C3e 를 지키기 위함) 그 규약과 «계획이 갱신되어야 한다» 가 같은 DB 에서 충돌함.

⚠️ 비용: 소화하면 실물 Claude 호출이 최대 15회 발생함. 그리고 보존 세션의 상태가 바뀔 수 있어 하네스 기준선과 충돌할 수 있음 — 먼저 무엇이 바뀌는지 적고 시점을 고름.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 pending 15건을 소화할 때 무엇이 바뀌는지(보존 세션 · 기준선 · 호출 비용)를 먼저 적고 그 시점을 고름
- [x] #2 워커를 켠 회차로 소화하고 session_plans 최신 행이 갱신되는 것을 직접 조회로 확인함
- [x] #3 하네스 규약(WORKER_ENABLED=false)과 계획 갱신 요구가 충돌하는 지점을 문서 한 곳에 적어 다음 세션이 같은 조사를 반복하지 않게 함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 AC#1 — 소화 «전에» 무엇이 바뀌는지 적었음. 사용자가 「지금 소화함」을 골랐으므로 시점은 지금임.

⛔ 이 태스크의 전제 둘이 낡았음(이 턴에 직접 조회).
1. pending 은 15건이 아니라 «14건» 임 — analyze_utterance 7 · plan_next_session 7. 그 사이 plan job 하나가 소화됐음(plan done 3건).
2. session_plans 최신 행이 2026-09-08 22:58 에 멈춰 있지 않음 — «2026-09-11 00:08:24 UTC · 세션 33447835» 임. 즉 계획 정체가 이미 부분적으로 풀렸음.

소화 대상과 비대상을 갈랐음.

⛔ plan_next_session 7건만 소화하고 analyze_utterance 7건은 «건드리지 않음». 근거: 분석 job 7건 중 3건이 보존 세션 210233be 의 것이고, 소화하면 그 세션의 결과 API status 가 analyzing → final 로 바뀌어 기준선이 깨짐. 기준선 파일(runs/2026-09-10-task82-p5-p6/results-api-baseline.json)을 직접 열어 확인한 것: 그 파일이 고정하는 필드는 status · partial_failure · pronunciation · corrections · drill 다섯이고 «next_plan 은 담지 않음». ⇒ 계획 job 만 소화하면 기준선 drift 가 0 임.

비용: 실물 Claude 7회임(태스크가 적은 「최대 15회」보다 적음 — 계획만 돌리기 때문).

바뀔 표: session_plans(지금 3) · learner_notes(지금 4)만 늘어남. 안 바뀔 표: error_patterns 9 · error_occurrences 24 · review_tasks 15 · pattern_attempts 19 · daily_error_summary 0.

⚠️ 76d9ef31 은 failed 세션이고 발화가 0건인데 계획 job 을 갖고 있음 — 계획 입력이 없어 report_failure 로 끝날 것으로 예상함. 그것은 결함이 아니라 설계된 실패 경로임.

⛔ 방법: run_worker 를 부르지 않음. 그 루프는 큐가 비면 sweep_lost_runs → flush_ended_sessions 를 불러 «보존 세션에 job 을 새로 만들어 처리»하고, 2026-09-09 에 그 경로로 보존 세션 둘이 파괴됐음(H-AT 경로 ②). 대신 tests/harness/p5_worker_leg.py 의 guard(--job-type plan_next_session) → claim → restore 를 세션마다 돎. claim_next 에 종류 필터가 없어 guard 로 내 job 을 전역 최소로 당기는 것이 유일한 선택 방법임.

대상 세션 7개: 210233be · 24597f0f · 76d9ef31 · b2f0d169 · d127dece · d727f79d · f8ebc78b.

2026-09-12 AC#2·#3 완료 — 정본은 tests/harness/runs/2026-09-12-task104-plan-drain/ 임.

AC#2 결과. 계획이 갱신됐음 — session_plans 3 → 6 · learner_notes 4 → 7 · 최신 행이 2026-09-11 00:08 → 2026-09-11 22:40(직접 조회). 실물 Claude 호출 4회임(태스크가 적은 「최대 15회」보다 훨씬 적음).

⛔ 그런데 「소화」가 절반만 가능했음. 계획 job 7건 중 비보존 3건만 처리했고 보존 4건은 하네스가 «거부» 했음 — p5_worker_leg.py 가 「보존 세션이다. 그 job 은 어떤 경우에도 처리하지 않는다(browser_leg.md §9)」로 막음. 규약이 아니라 집행이므로 우회하지 않았음.

세션별: 24597f0f 1회차 거부(없는 키 level.reason_en) → 2회차 성공 · d727f79d 성공 · f8ebc78b 성공 · 210233be·76d9ef31·b2f0d169·d127dece 거부.

보존 세션 기준선 drift 0건 — verify 전후 diff 가 비었음(증거 파일 둘을 회차 디렉터리에 남겼음). 안 바뀐 표: error_patterns 9 · error_occurrences 24 · review_tasks 15 · pattern_attempts 19.

⛔ TASK-109 를 재현했고 성질이 좁혀졌음. 거부 사유가 「level.reason_en 이 없는 키」였는데 동료가 본 것은 level.reason_note 임 — 즉 특정 키 하나의 문제가 아니고 모델이 «없는 키를 만드는» 성향이며 이름이 매번 다름. 그래서 「그 키를 스키마에 더한다」로 닫히지 않음. ⚠️ 그리고 재시도로 회복됐음 — 1회차 거부 뒤 2회차가 통과해 계획 행이 생김. ⇒ 등급을 정할 때 「계획이 안 생긴다」가 아니라 「계획이 늦게 생기고 재시도 예산을 먹는다」로 읽어야 함.

⚠️ TASK-108(deepest 미포함)은 이 회차 4회 호출에서 0건임 — 동료는 같은 공유 DB 에서 봤으므로 재료가 아니라 비결정성의 차이로 보임.

AC#3 — 규약 충돌을 tests/harness/browser_leg.md §9-1 에 넣었음. ⛔ 그 절에 담은 핵심은 「보존 세션의 pending 분석 job 은 잔여물이 아니라 C3a(analyzing) 픽스처를 떠받치는 것」임 — 소화하면 그 픽스처가 사라짐. 그리고 보존 세션 4개가 계획 job 을 영구히 pending 으로 들고 있어 큐에서 사라지지 않는다는 사실과, pending 을 볼 때 보존 세션 몫을 빼고 읽는 SQL 을 함께 넣었음(⚠️ coalesce 를 빼면 H-AX 대로 분석 job 을 통째로 빠뜨림).

⛔ 이 태스크가 «고르지 않은» 것 — 보존 세션 4건의 계획 job 을 어떻게 할지는 사람이 정함. 선택지 셋을 회차 기록 §4 에 적었음: 보존을 끝낸다 / status='failed' 로 큐에서 내린다(DB 쓰기라 승인 필요) / 그대로 두고 집계에서 빼 읽는 규약만 만든다.

⛔ 태스크 전제 둘이 낡아 정정했음(AC#1 노트에 적었음) — pending 은 15 가 아니라 14 였고 session_plans 최신은 2026-09-08 이 아니라 2026-09-11 00:08 이었음.
<!-- SECTION:NOTES:END -->
