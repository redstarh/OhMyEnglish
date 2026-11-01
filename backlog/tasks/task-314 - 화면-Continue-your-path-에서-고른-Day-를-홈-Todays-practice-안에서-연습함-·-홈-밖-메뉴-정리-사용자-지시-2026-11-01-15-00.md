---
id: TASK-314
title: >-
  화면: Continue your path 에서 고른 Day 를 홈 Today's practice 안에서 연습함 · 홈 밖 메뉴 정리 (사용자
  지시 2026-11-01 15:00)
status: Done
assignee: []
created_date: '2026-11-01 06:03'
updated_date: '2026-11-01 06:43'
labels: []
dependencies: []
ordinal: 379000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시: Home 화면 이외에 Practice·Review·Progress 가 필요한지 모르겠음. Home 에서 실제 학습이 이루어지고, Continue your path 에서 학습 목록을 선택하면 Home 맨 위 Today's Practice 섹션에서 해당 학습이 이루어지면 됨. 현재는 Practice 메뉴로 넘어가고 유튜브 화면과 이전 학습 화면이 나옴. 목록은 첨부(Screenshot 2026-11-01 at 3.00.02 PM)처럼 표시만 하고, 선택하면 Today's Practice 에서 학습함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Continue your path 의 Day 를 고르면 페이지 이동 없이 Today's practice 에서 그 Day 의 문장 연습이 열림(영상 없음)
- [x] #2 메뉴·View all 의 처리를 사용자 결정대로 함
- [x] #3 1400·390 폭 실제 화면으로 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-01 사용자 결정(AskUserQuestion): 사이드바 Practice·Review·Progress 셋 다 숨김 · View all 은 홈 목록을 펼침(Day 전부 · 고르면 Today's practice 에서 연습 · 페이지 이동 없음).

구현·확인(회차 b15 path-*.json): 메뉴 nav-home 하나 · Day 줄 버튼 · View all 6↔2 · Day 2·1 선택 시 주소 / 그대로 · 고른 Day 연습 · 390 카드로 스크롤 · Your progress 에 History·Weekly report 버튼. 커밋 c89c24f. 결정 대기: More practice Grammar course(/course → 옛 Day 화면·유튜브)·Learn with videos 와 빠른 카드 Listen & notice(/videos) 처리.

2026-11-01 사용자 결정(AskUserQuestion): Grammar course 만 홈으로 — Today's practice 에서 현재 Day 연습을 엶. Learn with videos · Listen & notice(/videos)는 그대로 둠.

2026-11-01 사용자 지시로 일시 정지. 미커밋: HomeDashboard.tsx — More practice Grammar course 를 Today's practice(현재 Day)를 여는 버튼으로 바꿈. tsc 0 · eslint 0. 남은 것: 1400·390 실제 화면 확인 · 커밋 · 설계서 §3 기록 · push. 음성 명령은 course 에 target 이 없어 영향 없음(additionalLearning.ts).

재개 후 완료: Grammar course 버튼 확인(회차 b15 grammar-1400/390.json · 주소 / 그대로 · 현재 Day 1 · 390 카드로 스크롤). 설계서 §3 「학습은 홈에서만 · 메뉴는 Home 하나」. tsc 0 · eslint 0 · next build 0 · 하네스 112 passed. dev 진도 위치 불변.
<!-- SECTION:NOTES:END -->
