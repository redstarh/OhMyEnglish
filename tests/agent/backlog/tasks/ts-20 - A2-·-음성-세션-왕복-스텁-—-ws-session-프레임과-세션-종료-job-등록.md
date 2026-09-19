---
id: TS-20
title: A2 · 음성 세션 왕복 (스텁) — /ws/session 프레임과 세션 종료 job 등록
status: To Do
assignee: []
created_date: '2026-09-19 05:18'
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
- [ ] #1 stub 어댑터로 세션이 열려 픽스처 턴이 흐르고 세션이 닫힘
- [ ] #2 그 세션의 발화 전사가 DB 에 남음
- [ ] #3 세션 종료가 job 셋(plan_next_session·summarize_session·summarize_week)을 그 자리에서 등록함 (H-CD)
- [ ] #4 stub_unresponsive 에서 voice_adapter_connect_timeout 사유로 닫힘
- [ ] #5 회차가 만든 세션이 teardown_session.py 로 걷혔음
<!-- AC:END -->
