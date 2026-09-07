---
id: TASK-34
title: 프론트 계약에 기계적 방어를 둔다 — 「결과 화면에 숫자를 렌더하지 않는다」 자동 게이트
status: To Do
assignee: []
created_date: '2026-09-07 16:34'
labels: []
dependencies: []
ordinal: 37000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Batch C 리뷰가 LOW(NOTE) 로 올렸다: app/frontend/app/results/[sessionId]/page.tsx 의 「드릴 두 수를 화면에 렌더하지 않는다」 계약을 지키는 자동 게이트가 없다. tests/harness/c3_results_screen.py 는 directPCount 를 측정만 하고 단정하지 않아 새 <p> 한 줄을 모른다. 캡틴 결정 10(미달의 주어는 학습자가 아니라 대화 모델 — 학습자가 손쓸 수 없는 수를 자기 점수로 읽게 하지 않는다)과 결정 18 이 걸린 계약인데 사람의 주의에만 의존한다. 팀리드가 코드로 '숫자가 DOM 에 닿을 수 없음'을 확인했으나 그것은 지금 코드에 대한 확인이고 회귀 방어가 아니다. 브리프 테스트 목록에 프론트 항목을 넣지 않은 것도 팀리드 쪽 누락이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 결과 화면에 드릴 두 수(exchanges_observed·exchanges_expected)가 렌더되지 않는 것을 기계적으로 단정한다 — 무력화(일부러 숫자를 렌더) 에서 실제로 FAIL 하는 것을 관측해 판별력을 증명한다
- [ ] #2 미달일 때만 문장이 그려지고 달성 세션에는 아무것도 그려지지 않는 것을 함께 단정한다 (달성 문장도 점수판이 된다)
- [ ] #3 c3_results_screen.py 의 directPCount 를 측정에서 단정으로 올릴지, 별도 프론트 테스트로 둘지 정하고 근거를 남긴다 — 하네스는 브라우저 회차 규약(browser_leg.md)의 소유물이라 함부로 고치지 않는다
<!-- AC:END -->
