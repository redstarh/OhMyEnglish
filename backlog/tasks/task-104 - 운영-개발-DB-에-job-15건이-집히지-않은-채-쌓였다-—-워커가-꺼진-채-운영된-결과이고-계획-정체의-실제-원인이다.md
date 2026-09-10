---
id: TASK-104
title: '운영: 개발 DB 에 job 15건이 집히지 않은 채 쌓였다 — 워커가 꺼진 채 운영된 결과이고 계획 정체의 실제 원인이다'
status: To Do
assignee: []
created_date: '2026-09-10 23:54'
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
- [ ] #1 pending 15건을 소화할 때 무엇이 바뀌는지(보존 세션 · 기준선 · 호출 비용)를 먼저 적고 그 시점을 고름
- [ ] #2 워커를 켠 회차로 소화하고 session_plans 최신 행이 갱신되는 것을 직접 조회로 확인함
- [ ] #3 하네스 규약(WORKER_ENABLED=false)과 계획 갱신 요구가 충돌하는 지점을 문서 한 곳에 적어 다음 세션이 같은 조사를 반복하지 않게 함
<!-- AC:END -->
