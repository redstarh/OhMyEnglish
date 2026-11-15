---
id: TASK-345
title: '리뷰: TASK-344 모바일 한 화면 변경의 codex 리뷰를 받아 반영함'
status: Done
assignee: []
created_date: '2026-11-15 03:56'
updated_date: '2026-11-15 04:03'
labels: []
dependencies: []
ordinal: 412000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
대상 커밋 8a02d84..9a55313 의 app/frontend 변경(globals.css 모바일 블록 · app-shell · HomeDashboard · page.tsx · progress).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 codex 리뷰 결과를 받음
- [x] #2 CRITICAL·HIGH 를 고치거나 근거를 들어 반박함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-15 codex 리뷰(8a02d84..9a55313) 5건 모두 수용·수정. HIGH① 세션 중 모바일 머리의 /progress 링크가 잠금을 우회 → 세션·연습 중 머리·요약 숨김(showMobileChrome). HIGH② 무층 overflow:hidden 이 세션 칸 overflow-y-auto 를 덮음 → 연습 모드에만 적용. MEDIUM③ ?day= 가 초기값만 → 렌더 중 상태 맞춤으로 질의 변화를 따름(실측: Close→로고→Back 에서 Day 2 연습 다시 열림). MEDIUM④ 768~1023 머리 사라짐 → max-md:hidden 으로 폰 폭만(실측 800 머리 보임). MEDIUM⑤ 폰에서 ?extras=1 무력 → data-extras 로 숨김·잠금 해제(실측 More practice 보임 · 문서 1458). ①② 는 실제 세션이 dev DB 에 행을 만들므로 브라우저로 재현하지 않고 코드·CSS 조건으로 확인. 회귀: mobile-fit 16 ALL PASS · 데스크톱 홈·연습 픽셀 동일 · tsc 0 · eslint 0 · node --test 60 · next build 0.
<!-- SECTION:NOTES:END -->
