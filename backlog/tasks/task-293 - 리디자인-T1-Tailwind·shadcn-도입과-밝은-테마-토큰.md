---
id: TASK-293
title: '리디자인 T1: Tailwind·shadcn 도입과 밝은 테마 토큰'
status: To Do
assignee: []
created_date: '2026-10-31 19:05'
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
- [ ] #1 npm run build · tsc · eslint 가 통과함
- [ ] #2 globals.css 에 prefers-color-scheme 와 층 밖 리셋 규칙이 없음
- [ ] #3 8개 경로가 밝은 배경으로 그려지고 옛 버튼·제목 모양이 남음(스크린샷)
<!-- AC:END -->
