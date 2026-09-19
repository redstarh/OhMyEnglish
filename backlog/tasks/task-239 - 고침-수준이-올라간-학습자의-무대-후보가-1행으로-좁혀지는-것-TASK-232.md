---
id: TASK-239
title: '고침: 수준이 올라간 학습자의 무대 후보가 1행으로 좁혀지는 것 (TASK-232)'
status: In Progress
assignee: []
created_date: '2026-09-19 07:49'
updated_date: '2026-09-19 07:58'
labels: []
dependencies: []
ordinal: 303000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
심각도 HIGH · 앱 결함 · 뿌리 그룹 C(무대 회전). 결함 정본은 TASK-232 임 — 재현 3단계와 경계(1행이 0행보다 나쁨)를 그 태스크가 가짐. 현상: current_level 이 B1 으로 오른 학습자의 무대 후보가 그 수준 1행으로 좁혀져 6회 전부 같은 무대가 나오고 「반복 70 대 신규 30」(결정 73·74)이 깨짐. 시드 30행이 후보에서 사라짐. ⛔ 후보 풀의 수준 조건을 어떻게 넓힐지는 설계 판단이라 설계서(2026-09-12-scenario-rotation-70-30-design.md)를 먼저 읽고 고침.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 수준이 오른 학습자도 창 10회에 신규가 규약 비율만큼 나옴
- [x] #2 후보가 1행인 경계에서 같은 무대가 연속으로 반복되지 않음
- [x] #3 회전 규약을 재는 검사가 추가되고 그 검사가 고치기 전 코드에서 실패함
- [ ] #4 TASK-232 에 고친 커밋과 판정을 적어 이음
<!-- AC:END -->
