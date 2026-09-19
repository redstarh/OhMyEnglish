---
id: TASK-241
title: '신설: 자주 틀리는 패턴에서 즉시 드릴을 만드는 경로 (TASK-233)'
status: In Progress
assignee: []
created_date: '2026-09-19 07:49'
updated_date: '2026-09-19 07:58'
labels: []
dependencies: []
ordinal: 305000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
심각도 HIGH · 기능 부재 · 뿌리 그룹 B(진입·기록). 결함 정본은 TASK-233 임. PRD.md:70 이 글자로 요구하고(「사용자는 자주 틀리는 패턴을 직접 보고 해당 패턴으로 즉시 학습을 만들 수 있음」) TASK-7 이 소유자 없음으로 적어 둔 자리임. 관측: 결과 화면이 패턴을 보여 주기만 하고 동작이 없음 · pattern_key 가 React key 로만 쓰임 · SessionEntry 에 패턴을 실을 자리가 없음 · practice_current_pattern 이 app 안 0곳. ⛔ 기능 신설이라 설계가 먼저임 — 진입점 설계서(2026-09-12-additional-learning-entry-design.md)와 즉시 드릴 설계서(2026-09-08-immediate-drill-entry-design.md)를 읽고 기존 진입 경로를 재사용하는 쪽을 먼저 본다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 결과 화면의 패턴에서 그 패턴으로 학습을 시작하는 경로가 있음
- [ ] #2 그 경로로 연 세션이 어떤 패턴에서 왔는지 DB 에 남음
- [ ] #3 기존 추가 학습 진입 경로를 재사용했는지 또는 왜 못 했는지가 적혀 있음
- [ ] #4 TASK-233 에 고친 커밋과 판정을 적어 이음
<!-- AC:END -->
