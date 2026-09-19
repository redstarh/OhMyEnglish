---
id: TS-21
title: A3 · 음성 세션 왕복 (실물 Nova) — 실제 음성 1회차
status: To Do
assignee: []
created_date: '2026-09-19 05:18'
labels: []
dependencies: []
ordinal: 21000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A3. 대상: /ws/session + 실물 nova 어댑터. ⛔ 실물 Bedrock 호출이 필요함(사전 승인 범위 · 회차 1건). ⛔ A11 과 같은 회차로 합쳐 비용을 한 번만 씀. 수단: tests/harness/p_readback_leg.py 머리말의 진입 순서. 픽스처 public/harness/readback.wav 는 끝에 침묵 2초가 있어야 함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 실물 어댑터로 세션 1회가 열려 사용자 음성에 음성 응답이 돌아옴
- [ ] #2 그 발화의 전사가 DB 에 남음
- [ ] #3 회차가 만든 세션이 teardown_session.py 로 걷혔음
- [ ] #4 llm_calls 증가분을 회차 전후로 세어 비용 근거를 남김
<!-- AC:END -->
