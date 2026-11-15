---
id: TASK-344
title: 모바일 화면을 스크롤 없이 한 화면에 담음 — 디자인 에이전트 시안 · iOS 시뮬레이터로 아이폰 시험 전 확인
status: In Progress
assignee: []
created_date: '2026-11-15 03:06'
updated_date: '2026-11-15 03:11'
labels: []
dependencies: []
ordinal: 411000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 2026-11-15: 아이폰 접속 확인 뒤 「모바일 창에서 스크롤이 생김」. 디자인 에이전트로 모바일 시안을 다시 잡고 아이폰 시험 전에 시뮬레이터(Xcode)로 먼저 시험함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 iOS 시뮬레이터 Safari 로 지금 홈·문장 연습의 세로 스크롤 크기를 잼
- [ ] #2 디자인 에이전트로 스크롤 없는 모바일 시안을 만들고 사용자 결정을 받음
- [ ] #3 시안을 구현하고 게이트(tsc·eslint·next build·node 시험)를 통과함
- [ ] #4 시뮬레이터에서 홈·문장 연습이 스크롤 없이 한 화면에 들어감을 스크린샷으로 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-15 실측: iPhone 16 Safari 가시 393×659 · 12 Pro Max 428×745(시뮬레이터 스크린샷). 393×659 Chromium 문서 높이: 홈 대기 1317 · 연습 1318 · KO 1362 · 기록/주간/영상 659(스크롤 없음). 사용자 결정: 홈=연습 카드+진도 한 줄, 나머지는 별도 화면 · 대상 428×745+393×659 · 연습 중 카드가 화면 전체. 브리프 승인: docs/design/2026-11-15-design-system/brief.md
<!-- SECTION:NOTES:END -->
