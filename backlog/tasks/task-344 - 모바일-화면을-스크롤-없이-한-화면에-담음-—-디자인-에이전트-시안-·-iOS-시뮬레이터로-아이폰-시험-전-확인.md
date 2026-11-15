---
id: TASK-344
title: 모바일 화면을 스크롤 없이 한 화면에 담음 — 디자인 에이전트 시안 · iOS 시뮬레이터로 아이폰 시험 전 확인
status: In Progress
assignee: []
created_date: '2026-11-15 03:06'
updated_date: '2026-11-15 03:55'
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
- [x] #2 디자인 에이전트로 스크롤 없는 모바일 시안을 만들고 사용자 결정을 받음
- [x] #3 시안을 구현하고 게이트(tsc·eslint·next build·node 시험)를 통과함
- [x] #4 시뮬레이터에서 홈·문장 연습이 스크롤 없이 한 화면에 들어감을 스크린샷으로 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-15 실측: iPhone 16 Safari 가시 393×659 · 12 Pro Max 428×745(시뮬레이터 스크린샷). 393×659 Chromium 문서 높이: 홈 대기 1317 · 연습 1318 · KO 1362 · 기록/주간/영상 659(스크롤 없음). 사용자 결정: 홈=연습 카드+진도 한 줄, 나머지는 별도 화면 · 대상 428×745+393×659 · 연습 중 카드가 화면 전체. 브리프 승인: docs/design/2026-11-15-design-system/brief.md

2026-11-15 v0 검토: 사용자 제안대로 GitHub 연결(v0 프로젝트 OhMyEnglish · 기준 브랜치 design/first-vertical-slice · 루트 app/frontend · 채팅 new-chat-44RyJQOdnIo). v0 리뷰: 모바일 시안의 연습 우선 배치에 동의 · 데스크톱은 결함 없어 그대로 둠. v0 코드는 ZIP 으로 받아 적용(GitHub App 권한은 주지 않음). v0 판 결함 넷을 내가 고침: ① page.tsx 한국어 주석 깨짐(U+FFFD) — 그 조각은 받지 않고 Suspense 만 손으로 넣음 ② 슬롯·감싸개가 flex 칸이 아니라 카드가 화면을 못 채움 ③ 결과 칸이 고정 높이라 칸 안 스크롤(51~57 px) ④ /progress 가 넘침(146·256 px) · 44 px 미만 버튼 · 로고가 Mic 로 바뀜. 측정: tests/agent/tools/mobile-fit.mjs 16건 통과(결과 칸 규칙을 끄면 2건 실패 — 판별력 확인). 데스크톱 1400 홈·연습 픽셀 동일(diff bbox None). iOS 시뮬레이터(12 Pro Max · iPhone 16) Safari 에서 홈·연습(/?day=1)·진도 화면이 주소 막대 위에 들어감. 게이트: tsc 0 · eslint 0 · node --test 60 · next build 0.
<!-- SECTION:NOTES:END -->
