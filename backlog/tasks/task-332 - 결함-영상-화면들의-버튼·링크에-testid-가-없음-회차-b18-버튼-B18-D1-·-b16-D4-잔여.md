---
id: TASK-332
title: '결함: 영상 화면들의 버튼·링크에 testid 가 없음 (회차 b18 버튼 B18-D1 · b16 D4 잔여)'
status: To Do
assignee: []
created_date: '2026-11-14 12:38'
labels: []
dependencies: []
ordinal: 399000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
확인(내가 직접 · 소스): app/videos/page.tsx button 4 · testid 1 · app/videos/[videoId]/page.tsx button 8 · testid 1(돌아가기 링크뿐). 제안 이름: videos-check · videos-delete · videos-title · video-mark-start · video-mark-end · video-mark-cancel · video-span-save.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 영상 두 화면의 실행 버튼·링크에 data-testid
- [ ] #2 tsc·eslint 와 화면 확인
<!-- AC:END -->
