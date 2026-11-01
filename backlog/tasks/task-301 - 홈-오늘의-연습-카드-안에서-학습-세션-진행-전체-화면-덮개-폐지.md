---
id: TASK-301
title: 홈 오늘의 연습 카드 안에서 학습 세션 진행 (전체 화면 덮개 폐지)
status: Done
assignee: []
created_date: '2026-11-01 02:16'
updated_date: '2026-11-01 03:11'
labels: []
dependencies: []
ordinal: 366000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 2026-11-01: Practice Session 화면을 별도로 띄우지 말고 홈의 Start speaking 을 누르면 그 영역(오늘의 연습 카드)에서 바로 연습하게 함. 다른 배치는 바꾸지 않음. 덮개를 없애면 세션 중 사이드바 이동이 연결을 끊으므로, 세션이 도는 동안 사이드바 링크를 막음(권장안). 리디자인 설계서 §3 의 덮개 결정을 뒤집는 것이므로 그 기록을 남김. 회차 b10 이 같은 개발 서버를 쓰는 동안은 별도 작업 트리에서 구현함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Start speaking·빠른 카드·More practice 로 시작한 세션이 오늘의 연습 카드 자리에서 진행되고 다른 카드 배치는 그대로임
- [x] #2 세션 중 사이드바 링크가 막히고 끝나면 풀림
- [x] #3 실패·쉐도잉·주간 리포트 패널·결과 화면 이동이 그대로 동작함(회차)
- [x] #4 설계서 §3 에 뒤집은 결정과 근거를 기록함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 b11(tests/agent/runs/2026-11-01-b11): TASK-301 12항목 통과 — session-panel 이 home-hero 안 · fixed 덮개 0 · 다른 카드 x·폭 그대로(아래로만 밀림) · 연결 중/실패에서 잠긴 요소 16곳 이동 0 · Tab 초점 안 감 · 끝나면 잠금 풀림 · Try again 같은 학습 · ← Home 잠금 해제 · 390 폭 스크롤. 낮음 결함 D1(연결 중·실패에서 카드가 줄어듦) → TASK-304 합치면서 최소 높이로 고침.
<!-- SECTION:NOTES:END -->
