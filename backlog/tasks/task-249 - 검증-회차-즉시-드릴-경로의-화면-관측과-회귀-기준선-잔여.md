---
id: TASK-249
title: '검증 회차: 즉시 드릴 경로의 화면 관측과 회귀 기준선 잔여'
status: In Progress
assignee: []
created_date: '2026-09-19 11:41'
updated_date: '2026-09-19 11:42'
labels: []
dependencies: []
ordinal: 313000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
통합테스트 회차(TASK-229)가 다음 회차 몫으로 남긴 둘을 닫음. ⛔ 첫째가 이 태스크의 핵심임 — TASK-241 이 만든 즉시 드릴 경로를 «내가 쓴 코드가 아닌 맥락»에서 관측함(작성자와 검증자를 가르는 규칙). 백엔드 쪽은 검사로 덮었으나 화면 네 자리(SessionEntry.patternKey · entryQuery·entryFromQuery · dashboardEntryHref · 결과 화면 링크)는 tsc·eslint·build 와 코드 검토로만 확인했음. 대상: 테스트 원장의 TS-36 AC#3 과 TS-4 의 남은 AC 둘.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 TS-36 AC#3 이 화면에서 관측돼 그 시나리오가 Done 으로 닫힘
- [ ] #2 TS-4 의 남은 AC 둘(규칙 4 의 성공분 교정 포함 · 규칙 1 대 3 우선순위)이 앱 경로로 관측됨
- [ ] #3 관측 결과가 회차 문서로 남고 실패가 있으면 결함으로 등록됨
<!-- AC:END -->
