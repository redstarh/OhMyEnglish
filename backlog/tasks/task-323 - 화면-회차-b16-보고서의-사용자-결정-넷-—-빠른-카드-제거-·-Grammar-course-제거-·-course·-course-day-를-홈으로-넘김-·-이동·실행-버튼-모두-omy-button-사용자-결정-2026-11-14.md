---
id: TASK-323
title: >-
  화면: 회차 b16 보고서의 사용자 결정 넷 — 빠른 카드 제거 · Grammar course 제거 ·
  /course·/course/<day> 를 홈으로 넘김 · 이동·실행 버튼 모두 omy-button (사용자 결정 2026-11-14)
status: Done
assignee: []
created_date: '2026-11-14 08:56'
updated_date: '2026-11-14 09:04'
labels: []
dependencies: []
ordinal: 390000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
보고서 docs/ux/2026-11-14-ux-flow-review/index.html 의 사용자 결정 4건을 AskUserQuestion 으로 받음: ① 빠른 카드 셋 제거(More practice 와 같은 입구) ② More practice 의 Grammar course 제거(Start speaking 과 같은 일) ③ /course · /course/<day> 는 홈으로 넘기고 그리로 가는 버튼은 홈 Day 줄로 ④ More practice 8개 · View all · Practice a pattern · End lesson · 영상 화면 버튼을 omy-button 기준에 넣음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 빠른 카드와 Grammar course 가 홈에 없음
- [x] #2 /course · /course/<day> 를 열면 홈으로 감 · 그리 가던 버튼이 홈으로 감
- [x] #3 목록의 버튼이 omy-button(36px · 13.6px)
- [x] #4 1400·390 실제 화면으로 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
구현: QuickCards·Grammar course(additionalLearning course 키 포함) 제거 · /course · /course/[day] page 를 redirect('/') 서버 컴포넌트로(CoursePlayer.tsx 는 SentencePractice 의 타입 때문에 남김 → TASK-317 에서 정리) · More practice · View all · Practice a pattern · End lesson · /videos · /videos/[id] 버튼 omy-button. 하네스 p_readback_leg.py 의 quick-shadowing → practice-shadowing. 확인(내가 직접 · verify/t323.mjs · 사용자 스택): quick 0 · grammar 0 · 대상 버튼 1400/390 모두 36px·13.6px · /course→/ · /course/1→/. End lesson 은 세션을 열면 dev DB·Nova 에 닿아 코드로만 확인. tsc 0 · eslint 0 · next build 0 · node --test 4 · 하네스 112.
<!-- SECTION:NOTES:END -->
