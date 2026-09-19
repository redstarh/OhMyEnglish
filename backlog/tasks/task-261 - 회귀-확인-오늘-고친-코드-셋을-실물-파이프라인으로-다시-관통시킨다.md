---
id: TASK-261
title: '회귀 확인: 오늘 고친 코드 셋을 실물 파이프라인으로 다시 관통시킨다'
status: Done
assignee: []
created_date: '2026-09-19 17:22'
updated_date: '2026-09-19 17:22'
labels: []
dependencies: []
ordinal: 325000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
오늘 제품 코드를 세 곳 고쳤음 — 분석 프롬프트 한 줄(TASK-257) · ScenarioNoStage 와 파서 분기(TASK-259) · jobs.fail_terminally 신설(TASK-259). 살아 있는 지시가 「개발 뒤 테스트 필수」이므로 격리 DB 에서 통합 회차를 다시 돌려 단정 전건이 유지되는지 확인함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 w_worker_round 단정 9건이 전건 통과하고 재시도가 0건임
- [x] #2 호출 수와 토큰이 기록됨
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회귀 회차 결과 (2026-09-20 · 이 세션이 직접 돌렸음). 증거는 tests/harness/runs/2026-09-20-task261-regression/ 임. 단정 9/9 통과 · 호출 10건 · 재시도 0건 · job 10건 전건 done · llm_calls 10행이 드라이버 계수기와 같음 · 토큰 22,407 in / 5,666 out. 오늘 고친 셋(분석 프롬프트 · 무대 파서 분기 · 큐 종결 경로)이 실물 파이프라인에서 회귀를 내지 않았음. ⚠️ 이 회차가 「프롬프트 수정이 빈도를 낮췄다」를 뜻하지 않음 — 그 판정은 TASK-258 이 소유하고 표본 크기 때문에 성립하지 않음.
<!-- SECTION:NOTES:END -->
