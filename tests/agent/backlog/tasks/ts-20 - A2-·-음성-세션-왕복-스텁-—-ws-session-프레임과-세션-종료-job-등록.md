---
id: TS-20
title: A2 · 음성 세션 왕복 (스텁) — /ws/session 프레임과 세션 종료 job 등록
status: Done
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 07:05'
labels: []
dependencies: []
ordinal: 20000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A2. 대상: WebSocket /ws/session · VOICE_ADAPTER=stub 와 stub_unresponsive. 수단: tests/harness/ws_session.py. 실물 외부 호출 없음. ⛔ 회차 뒤 teardown_session.py --session-id 를 돌림.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 stub 어댑터로 세션이 열려 픽스처 턴이 흐르고 세션이 닫힘
- [x] #2 그 세션의 발화 전사가 DB 에 남음
- [x] #3 세션 종료가 job 셋(plan_next_session·summarize_session·summarize_week)을 그 자리에서 등록함 (H-CD)
- [x] #4 stub_unresponsive 에서 voice_adapter_connect_timeout 사유로 닫힘
- [x] #5 회차가 만든 세션이 teardown_session.py 로 걷혔음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-19 배치 B5 — 전건 통과. AC 5건 전부 확인. 세션 54ce134a(stub · 프레임 17개 · utterances 6행 · partial 미저장) · ddf4913d(stub_unresponsive · voice_adapter_connect_timeout at t=10.033s · status=failed). 세션 종료가 워커 없이 plan_next_session·summarize_session·summarize_week 각 1건을 pending 으로 걸었음(analyze_utterance 3건은 저장 시점 등록). 두 세션 모두 teardown_session.py 로 걷었고 DB 전체 수가 회차 전과 같음. 회차 문서 tests/agent/runs/2026-09-19-b5/result.md §6. HEAD 78f7a6c(앱 소스 무변경) · 유료 호출 0건.
<!-- SECTION:NOTES:END -->
