---
id: TASK-77
title: '결함: 종단 이벤트 없는 소켓 종료를 성공으로 처리한다 — 결과 화면이 이른 종단 상태에 고정된다'
status: Done
assignee: []
created_date: '2026-09-09 16:26'
updated_date: '2026-09-09 22:29'
labels: []
dependencies: []
ordinal: 80000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 TASK-70 의 codex 리뷰가 HIGH 로 지적하고 팀리드가 코드로 확인했음.

app/frontend/app/page.tsx 의 SessionSocket onClose 가 sessionId 만 있으면 goToResults(sessionId) 로 넘어감. session_ended 를 받았는지 보지 않으므로 session_started 이후 네트워크가 끊긴 경우도 정상 종료와 같게 처리됨.

⛔ 피해는 결과 화면이 이른 종단 상태에 고정되는 것임. 서버가 아직 마지막 전사문 저장·job 등록·세션 종료를 처리 중이면 첫 조회가 no_utterances 를 낼 수 있고, 그것은 TERMINAL_STATUSES 에 있어 폴링이 멈춤. 뒤에 등록된 분석 결과를 영구히 표시하지 않음.

⚠️ TASK-56 이 이것을 만든 것이 아님 — no_utterances 는 그전부터 종단 상태였음. 다만 TASK-56 이 4xx 도 종단으로 만들었으므로 「한 번 멈추면 끝」인 성질이 더 넓어졌음.

⚠️ 같은 리뷰의 다른 지적(어댑터 오류를 completed 로 기록)은 이미 고쳤음(HEAD 참조). 그것을 고치면 이 경로의 일부가 완화됨 — 실제 장애 세션이 failed 로 남아 R2 가 connection_failed 를 내고 그것이 사실에 맞는 종단 상태가 됨. 그러나 「서버가 아직 처리 중인데 먼저 조회한다」는 경합은 남음.

⛔ 해결 방향을 발명하지 않음 — 선택지가 여럿이고 어느 것이 맞는지는 설계가 정함: ① onClose 에서 session_ended 미수신을 실패로 갈라 보여줌(결과 접근을 잃음) ② 결과 화면이 첫 조회의 종단 판정을 유예함(몇 초 또는 1회 재조회) ③ 서버가 종료 기록까지 끝낸 뒤에 소켓을 닫음(순서 보장).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 session_ended 미수신을 성공과 구별한다 — 어느 방향으로 갈랐는지 근거를 남긴다
- [x] #2 이른 종단 상태 고정이 사라지는 것을 관측한다 — 서버 처리 중에 결과 화면을 열어 폴링이 멈추지 않는 것을 직접 본다
- [x] #3 판별력을 게이트로 고정한다 — 결과 화면의 폴링 정지 판정은 순수 함수로 잴 수 있다(TASK-56 이 그 형태를 만들었음)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-10 완료. 캡틴 결정(2026-09-10) 「몇 번 더 보고 정함」대로 고쳤음 — 선택지 셋 중 결과 화면에서 유예를 골랐고, onClose 를 실패로 갈라 결과 접근을 잃는 쪽은 고르지 않았음.

창을 먼저 좁혔음(코드를 직접 읽음): _close_and_record 순서가 저장 대기 → 종료 경로 flush → adapter.close() → end_session 이므로 **종료 기록 전에 flush 가 돎.** 그래서 정상 세션에는 경합이 없음. TASK-70 에서 어댑터 오류를 failed 로 기록하게 고친 것도 이 경로를 좁혔음(R2 가 connection_failed 를 냄). 남은 창은 **종료 경로 flush 가 실패한 경우** 하나임.

AC1 — session_ended 미수신을 성공과 구별함. 단 갈라 놓은 자리가 onClose 가 아니라 **결과 화면의 종단 판정**임. 근거: onClose 는 결과 화면에 더 일찍 도달하게 할 뿐이고, 학습자가 교정을 잃는 실제 원인은 no_utterances 를 첫 판독으로 확정하는 것임. onClose 를 실패로 만들면 그 세션의 교정을 보러 들어갈 수단이 없어짐 — 캡틴이 그 쪽을 고르지 않았음.

AC2 — 이른 종단 고정이 사라지는 것을 직접 관측했음. CDP 로 fetch 를 감싸 세는 계측(TASK-56 이 만든 것과 같음 · 관측창 14s · 주기 2s):
  no_utterances (d127dece) — 호출 5건 · 첫~끝 6.03s · 첫 주기 뒤 2건 → 다시 보고 **멈춤**(무한 아님)
  final (6225ddaf · 음성 대조) — 호출 2건 · 첫 주기 뒤 0건 → 여전히 **즉시 멈춤**
음성 대조가 없으면 「전부 다시 본다」와 구별되지 않으므로 함께 뒀음.

AC3 — 판정을 shouldKeepPolling(status, noUtterancesSeen) 한 곳에 모았음. ⛔ 그 계측이 반증할 수 있음을 무력화로 확인했음: NO_UTTERANCES_RECHECKS 를 0 으로 내리면 호출 2건 · 첫 주기 뒤 0건 이고 FAIL 2건이 남. 되돌린 뒤 PASS 임.

⚠️ NO_UTTERANCES_RECHECKS = 3 은 설계 발명값임 — 스윕이 언제 도는지 보장하는 계약이 없음. 비용은 「진짜로 분석할 것이 없던 세션이 같은 문구를 몇 초 늦게 본다」 하나이고 주석에 그렇게 적었음. ⛔ 무한으로 만들지 않았음 — 상한이 없으면 TASK-56 이 없앤 영구 폴링이 다른 상태로 되살아남.

⚠️ 계측 스크립트를 tests/ 아래에 넣지 않고 /tmp 에 뒀음 — 그 아래 새 .py 는 ty 게이트 대상인데 pytest 가 수집하지 않아 틈이 생김(H-AV). 관측값은 회차 기록이 가짐: tests/harness/runs/2026-09-10-task77-no-utterances-recheck.md.

게이트: 프론트 npx tsc --noEmit exit 0 · npx eslint app lib exit 0. 백엔드 코드 변경 없음.
<!-- SECTION:NOTES:END -->
