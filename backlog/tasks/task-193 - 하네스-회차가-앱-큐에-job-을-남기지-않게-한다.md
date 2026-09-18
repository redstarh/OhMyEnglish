---
id: TASK-193
title: 하네스 회차가 앱 큐에 job 을 남기지 않게 한다
status: To Do
assignee: []
created_date: '2026-09-18 03:56'
labels: []
dependencies: []
ordinal: 254000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-190 조사에서 드러난 구조 문제. 회차가 돌 때마다 analysis_jobs 에 job 이 쌓이고 teardown 이 걷지 않아 62건이 모였다. H-AC 가 경고한 「하네스가 앱 데이터를 만진다」와 같은 부류이고, 그것을 처리하면 테스트 문장이 error_patterns·복습 과제에 섞인다. ⛔ teardown 이 계산하지 말고 자기가 만든 job 만 표시하거나 걷는 형태여야 한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 회차가 만든 job 을 식별하는 방법을 정한다
- [ ] #2 teardown 이 그것만 처리하고 앱 데이터를 계산하지 않는다
- [ ] #3 회차를 한 번 돌려 큐가 늘지 않는 것을 확인한다
<!-- AC:END -->
