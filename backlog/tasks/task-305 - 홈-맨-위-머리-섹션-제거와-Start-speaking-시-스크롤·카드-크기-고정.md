---
id: TASK-305
title: 홈 맨 위 머리 섹션 제거와 Start speaking 시 스크롤·카드 크기 고정
status: Done
assignee: []
created_date: '2026-11-01 03:58'
updated_date: '2026-11-01 04:57'
labels: []
dependencies: []
ordinal: 370000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 2026-11-01(스크린샷): ① 홈 맨 위 섹션(날짜 · Welcome back · 연속 학습일 칩)은 표기하지 않음 ② Start speaking 을 누르면 화면 포커싱이 바뀌며 스크롤이 움직임 — 움직이지 않고, 카드(섹션) 크기 그대로 표시함. 문장 연습·세션은 대기 카드 크기 안에서 보이고 넘치면 카드 안에서만 스크롤함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 홈 머리 섹션(날짜 · 인사 · 연속 학습일)이 없고 다른 배치는 그대로임
- [x] #2 Start speaking·세션 시작 때 창 스크롤 위치가 바뀌지 않음
- [x] #3 연습·세션 중 카드 크기가 대기 카드와 같고 아래 카드가 움직이지 않음(회차)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⛔ 번복(2026-11-01 13:1x 사용자 지시): 「start speaking 을 누르면 실제 연습 화면이 스크롤이 생기지 않게 섹션 내에 내용 모두 표시 · 아래 두 섹션의 세로 길이를 줄여서 맨 위 섹션 크기를 조정」 ⇒ 이 태스크의 「카드 크기 고정 + 안쪽 스크롤」(AC3)은 TASK-307 로 대체됨. 머리 섹션 제거(AC1)와 창 스크롤 이동 제거(AC2)는 유지. 측정 회차 b14 는 의미가 없어져 중간에 멈춤.

마감: AC1(머리 섹션 제거)·AC2(창 스크롤 이동 없음)은 회차 b13 r2 에서 확인(Start·Next·Finish Day 전후 scrollY 그대로). AC3(카드 크기 고정 + 안쪽 스크롤)은 사용자 번복으로 TASK-307 이 대체 — 고정 높이는 유지되고 안쪽 스크롤은 없어졌음.
<!-- SECTION:NOTES:END -->
