---
id: TS-23
title: A5 · 다음 세션 계획 — next-plan 과 plan_next_session job
status: In Progress
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 06:02'
labels: []
dependencies: []
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A5. 대상: GET /api/sessions/next-plan · job plan_next_session. 근거: PRD §11. 워커는 꺼 둔 채 시드 데이터로 읽기 경로를 잼.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 계획이 없거나 만들기에 실패해도 학습이 그냥 시작됨 (PRD §11 요구)
- [ ] #2 계획이 있으면 초점 패턴 1~2개·질문 3~5개·난이도·추천 이유를 함께 줌
- [x] #3 직전 세션 종료가 plan_next_session job 을 등록함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 2026-09-19-b3 (HEAD ced8df0). AC#1·#3 통과. AC#2 는 미확인 — AC 문면의 「함께 줌」 주체가 엔드포인트인지 계획인지에 따라 판정이 갈림. 결함 TASK-231 (작업 원장) 이 그 결정을 가짐. 저장된 계획 6건은 R11-2 의 네 요소를 전부 가짐(초점 2 · 질문 5 · A2 · reason 74~100자). 상세는 tests/agent/runs/2026-09-19-b3/result.md §5-1·§5-2·§5-3.
<!-- SECTION:NOTES:END -->
