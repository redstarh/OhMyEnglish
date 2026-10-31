---
id: TASK-293
title: '리디자인 T1: Tailwind·shadcn 도입과 밝은 테마 토큰'
status: Done
assignee: []
created_date: '2026-10-31 19:05'
updated_date: '2026-10-31 19:10'
labels: []
dependencies:
  - TASK-292
ordinal: 358000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계: docs/design/2026-11-01-v0-home-redesign-design.md §3·§4. 의존성 · postcss.config.mjs · components.json · lib/utils.ts · components/ui/button.tsx · globals.css 밝은 테마(기존 토큰 이름 유지) · layout.tsx.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 npm run build · tsc · eslint 가 통과함
- [x] #2 globals.css 에 prefers-color-scheme 와 층 밖 리셋 규칙이 없음
- [x] #3 8개 경로가 밝은 배경으로 그려지고 옛 버튼·제목 모양이 남음(스크린샷)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
구현 에이전트 결과를 내가 다시 확인: tsc 0 · lint 오류 0(기존 경고 1) · prefers-color-scheme 0 · /history 스크린샷 밝은 배경. build 통과는 에이전트 보고(exit 0). 결정: 옛 토큰은 hex 유지(하네스가 숫자 색을 읽음) · #4d74e8 은 대비 4.2:1 이라 --brand-bright(장식용)로, 글자용 --brand 는 #3263dc · dark 변형은 .dark 클래스로만 켜지게 함.
<!-- SECTION:NOTES:END -->
