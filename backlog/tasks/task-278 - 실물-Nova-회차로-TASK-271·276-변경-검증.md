---
id: TASK-278
title: 실물 Nova 회차로 TASK-271·276 변경 검증
status: Done
assignee: []
created_date: '2026-09-26 13:28'
updated_date: '2026-09-26 13:32'
labels: []
dependencies: []
ordinal: 342000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
격리 DB(TASK-277 직전 백업 복원 — 관사 초점 계획 + an_as_a 후보 = 옛 실패 조건)에서 p_app_path 로 관사가 든 올바른 학습자 문장을 흘림. 상한 Nova 2세션 · Claude 0회
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 격리 스택(DB·백엔드·사본 프런트)을 세우고 dev DB·:8002 를 건드리지 않음
- [x] #2 코치 턴 길이·연속 발화·관사 발음 교정 횟수를 원자료로 셈
- [x] #3 회차 기록을 남기고 teardown 함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 기록 tests/harness/runs/2026-09-26-task278-real-nova.md. 요약: 발음 고리는 후보 있으면 1/2 재발 · 없으면 0/1 → TASK-277 삭제의 근거. 턴 길이 33~203자(수정 전 평균 252). 새 결함(틀린 교정)은 TASK-279. 상한 2→3세션은 비교 팔 r3 때문(기록 §2). 격리 스택은 TASK-279 가 이어 쓰고 정리.
<!-- SECTION:NOTES:END -->
