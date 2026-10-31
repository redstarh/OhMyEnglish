---
id: TASK-296
title: '리디자인 T4: 홈 대시보드(실데이터)'
status: Done
assignee: []
created_date: '2026-10-31 19:05'
updated_date: '2026-10-31 19:27'
labels: []
dependencies:
  - TASK-294
  - TASK-295
ordinal: 361000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
설계: docs/design/2026-11-01-v0-home-redesign-design.md §5.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 모든 칸이 API 값과 맞고 가짜 수치(68 · 312 · 4 / 5 · Alex)가 컴포넌트에 없음
- [x] #2 백엔드를 내려도 Start speaking 이 눌리고 카드별 안내가 나옴
- [x] #3 하이드레이션 경고 0
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
내가 재확인: tsc 0 · lint 0 · build 0 · 가짜 수치 grep 0 · 1400 스크린샷이 v0 배치와 같고 값이 API 와 맞음(연속 1일 · 0/6 days · 1/7 days · 세션 0 · 최장 1 · 패턴 0 · Day 1/2). 백엔드 내림 상태는 코드로만 확인(카드별 실패 · Start 항상 활성) → T6 회차에서 실측. ⚠️ 앞 단계 스크린샷이 /course/1 을 차단 없이 열어 dev DB 에 Day 1 진도 행(전부 0)이 생겼음 → 내가 지워 0행으로 되돌림. 03:35·03:38 의 학습 세션 2건은 사용자 실행으로 보여 그대로 둠.
<!-- SECTION:NOTES:END -->
