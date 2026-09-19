---
id: TASK-243
title: '고침: 회귀 기준선이 공유 DB 의 살아 있는 행에 매여 낡는 것 (TASK-230)'
status: Done
assignee: []
created_date: '2026-09-19 07:49'
updated_date: '2026-09-19 08:12'
labels: []
dependencies: []
ordinal: 307000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
심각도 MEDIUM · 테스트 자산 결함 · 뿌리 그룹 D. 결함 정본은 TASK-230 임. 현상: TS-4 가 세션 uuid 와 상태를 1대1로 적어 두어, 그 세션의 job 이 나중에 바뀌면 기준선이 조용히 낡음. 이 회차가 두 건을 「새로 실패」로 올릴 뻔했고 analysis_jobs 를 직접 조회해서야 데이터 변화임을 갈랐음. ⛔ TASK-230 이 제안 셋을 적어 두었고 ⑴(세션 대응 대신 R2 규칙 번호로 회귀를 봄)이 가장 싸 보임 — 다만 ⑶(보존 픽스처를 워커 스윕 대상에서 뺌)이 뿌리에 더 가까운지 먼저 견줌.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 기준선이 특정 세션 uuid 의 현재 상태에 매이지 않음
- [x] #2 같은 회귀를 다음 회차가 데이터 변화와 혼동하지 않음
- [x] #3 고른 안과 나머지 둘을 버린 근거가 적혀 있음
- [x] #4 TASK-230 에 고친 커밋과 판정을 적어 이음
<!-- AC:END -->
