---
id: TASK-229
title: 전체 영역 통합테스트 회차 — 계획·수행·종합분석
status: In Progress
assignee: []
created_date: '2026-09-19 05:11'
updated_date: '2026-09-19 05:22'
labels: []
dependencies: []
ordinal: 290000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시(2026-09-19): 지금까지 개발된 모든 영역을 app-test-agent 로 통합테스트함. 테스트 계획의 정본은 테스트 원장(tests/agent/backlog · 접두사 ts)이고 결함은 이 작업 원장으로 옴. ⛔ 테스트 도중에 코드를 고치지 않음 — 결함만 등록하고 회차가 끝난 뒤 종합 분석으로 수정 태스크를 세움.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 테스트 원장에 영역별 시나리오가 전부 등록됨
- [ ] #2 등록된 시나리오 전부가 통과·실패·차단 가운데 하나로 판정됨
- [ ] #3 실패 전부가 이 작업 원장의 결함 태스크로 등록되고 시나리오 ID 와 양방향으로 이어짐
- [ ] #4 회차 결과가 tests/agent/runs 아래 result.md 로 남음
- [ ] #5 종합 분석으로 수정 태스크가 도출되고 심각도가 붙음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
영역 18개로 확정 (TS-19~TS-36). 수행은 5파로 나눔 — ① TS-19·22·30 + TS-27·28(병행) ② TS-23·24·25·26 ③ TS-31·32·35 ④ TS-20·33·36(스텁 WS) ⑤ TS-21·29·34(실물 Nova 1회차로 묶음). 실물 비용을 마지막 한 회차에 몰아 싼 것부터 확인하는 순서임.
<!-- SECTION:NOTES:END -->
