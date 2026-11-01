---
id: TASK-307
title: 홈 문장 연습·세션을 오늘의 연습 카드 안에 스크롤 없이 모두 표시 — 아래 두 섹션을 줄여 공간 확보
status: Done
assignee: []
created_date: '2026-11-01 04:15'
updated_date: '2026-11-01 04:57'
labels: []
dependencies:
  - TASK-305
ordinal: 372000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 2026-11-01(스크린샷 + 정정): 오늘의 연습 카드 높이는 고정함(대기·연습 같은 높이). 지금은 연습 내용이 넘쳐 스크롤이 생기므로, 그 고정 높이를 스크롤이 생기지 않을 만큼 늘림. 늘어난 만큼 공간이 부족하니 아래 두 섹션(Continue your path · 빠른 카드 셋)의 높이를 줄임. 코치 대화는 같은 높이 안에서 대화 목록만 안쪽 스크롤 허용. Start speaking 때 창 스크롤 이동 없음은 유지.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 연습·세션 중 오늘의 연습 카드 안에 안쪽 스크롤이 없고 내용이 모두 보임(1400·390)
- [x] #2 Continue your path · 빠른 카드 셋이 이전보다 낮아짐(실측)
- [x] #3 Start speaking 때 창 스크롤 위치가 바뀌지 않음
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
정정 2026-11-01: 첫 지시를 「내용에 맞게 늘어남」으로 잘못 옮겼음 → 사용자가 「높이를 고정해야 해. 스크롤이 생기지 않을 정도로 늘리라는 말」이라고 정정함. 구현 에이전트에 전달함.

회차 b13 r2·r3: 카드 고정 높이 1400 528px · 390 672px(대기·연습·판정·세션·실패 모두 같음) · home-hero-body 세로·가로 넘침 0 · 창 스크롤 그대로 · 이어 가기 78→58px · 빠른 카드 162→70px · 세션은 대화 목록만 스크롤. r2 D1(HIGH, 390 폭 판정 낱말 줄 줄바꿈 없음) → 낱말 사이 공백으로 고침, r3 에서 565문장 넘침 0. 관찰 O1(390 폭 아래 입구로 시작하면 카드가 화면 밖)은 사용자 결정 대상으로 남김.
<!-- SECTION:NOTES:END -->
