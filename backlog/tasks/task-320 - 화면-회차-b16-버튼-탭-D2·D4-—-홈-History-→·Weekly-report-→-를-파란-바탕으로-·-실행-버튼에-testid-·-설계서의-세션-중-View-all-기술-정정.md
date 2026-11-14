---
id: TASK-320
title: >-
  화면: 회차 b16 버튼 탭 D2·D4 — 홈 History →·Weekly report → 를 파란 바탕으로 · 실행 버튼에 testid
  · 설계서의 세션 중 View all 기술 정정
status: Done
assignee: []
created_date: '2026-11-14 06:31'
updated_date: '2026-11-14 08:57'
labels: []
dependencies: []
ordinal: 387000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
D2: HomeDashboard ProgressCard 의 두 → 링크가 omy-button 만 씀(다른 화면은 omy-button-primary). D4: End lesson(SessionChat.tsx) · 실패 화면 Try again(page.tsx) · 홈 밖 이동 링크에 data-testid 없음. 문서: 설계서 §3 세션 화면의 번복은 세션 중 View all 잠김이라 적었으나 TASK-314 뒤 제자리 펼침이라 잠기지 않음(펼친 Day 줄은 disabled).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 D2 두 링크가 omy-button-primary
- [x] #2 D4 버튼·링크에 testid
- [x] #3 설계서 정정
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
D2: 홈 home-history·home-weekly 에 omy-button-primary. D4 testid: session-end · session-failed-retry · history-weekly · history-home · weekly-history · results-home · results-history · videos-home · video-back(/course 화면은 TASK-323 에서 홈으로 넘김). 설계서 §3 세션 화면의 번복에 View all 정정. tsc 0 · eslint 0.
<!-- SECTION:NOTES:END -->
