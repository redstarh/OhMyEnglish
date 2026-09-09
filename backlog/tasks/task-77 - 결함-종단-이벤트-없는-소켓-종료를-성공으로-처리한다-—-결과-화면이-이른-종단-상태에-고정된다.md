---
id: TASK-77
title: '결함: 종단 이벤트 없는 소켓 종료를 성공으로 처리한다 — 결과 화면이 이른 종단 상태에 고정된다'
status: In Progress
assignee: []
created_date: '2026-09-09 16:26'
updated_date: '2026-09-09 22:15'
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
- [ ] #1 session_ended 미수신을 성공과 구별한다 — 어느 방향으로 갈랐는지 근거를 남긴다
- [ ] #2 이른 종단 상태 고정이 사라지는 것을 관측한다 — 서버 처리 중에 결과 화면을 열어 폴링이 멈추지 않는 것을 직접 본다
- [ ] #3 판별력을 게이트로 고정한다 — 결과 화면의 폴링 정지 판정은 순수 함수로 잴 수 있다(TASK-56 이 그 형태를 만들었음)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 착수 — 범위를 좁혔음. codex 의 프레이밍보다 창이 작음.

직접 읽어 확인한 것: audio_gateway/session.py 의 _close_and_record 순서가 ① 진행 중 저장 대기 ② _flush_analysis(종료 경로 flush) ③ adapter.close() ④ end_session + resolve_dangling(한 트랜잭션) 임. 즉 **종료 기록 전에 flush 가 돎.** 그래서 정상 세션에서는 세션이 completed 가 될 때 job 이 이미 걸려 있고, 결과 화면이 no_utterances 를 볼 수 없음.

TASK-70 의 다른 지적을 고친 것도 이 경로를 좁혔음 — 실행 중 어댑터 오류가 이제 failed 로 기록되므로 R2 가 connection_failed(사실에 맞는 종단 상태)를 냄. 클라이언트가 종단 이벤트 없이 닫혀 결과 화면으로 가도 학습자는 「연결 실패」를 봄.

남은 창은 하나임: **종료 경로 flush 가 실패한 경우.** _flush_analysis 는 예외를 삼키므로(그것이 의도임 — 분석 1건보다 세션·전사문이 중요함) 세션이 completed + job 0 으로 남고, 결과 화면이 no_utterances 를 **종단**으로 읽어 폴링을 멈춤. 그 뒤 워커가 유휴일 때 flush_ended_sessions 가 job 을 걸지만 화면은 이미 멈춰 있음. 기존 테스트 test_a_failing_flush_loses_only_the_analysis_not_the_session 이 그 상태를 고정하고 있음.

⛔ 즉 고칠 자리가 onClose 가 아니라 「no_utterances 를 종단으로 읽는 것」일 수 있음. onClose 는 결과 화면에 더 일찍 도달하게 할 뿐임.

⚠️ 어느 쪽으로 고치는지가 학습자가 보는 것을 바꿈 — AC U2(5상태)와 R2 의 뜻에 걸림. 발명하지 않고 캡틴에게 물었음.
<!-- SECTION:NOTES:END -->
