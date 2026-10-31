---
id: TASK-289
title: '결정: 문법 코스 「내가 말한 문장」 밑줄 위치와 영상 자동 재생'
status: Done
assignee: []
created_date: '2026-10-31 16:26'
updated_date: '2026-10-31 17:59'
labels: []
dependencies: []
ordinal: 354000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
회차 b3·b5 관찰. 밑줄을 원문 낱말에 칠지 학습자 낱말에 칠지(스토리보드 그림과 기존 쉐도잉 방식이 다름) · 저장 위치가 있는 Day 를 열면 seekTo 로 영상이 스스로 재생되는 동작을 둘지.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자 결정을 받아 기록함
- [x] #2 결정대로 구현하고 회차로 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-11-01
- 결정 둘(사용자): 밑줄·취소선은 원문 낱말에 둠(지금 그대로) · 저장 위치가 있는 Day 는 그 자리에 멈춰 둠. 기록은 docs/design/2026-10-26-grammar-course-design.md §7.
- 1차 구현(seekTo+pauseVideo)은 회차 b6 D2 로 실패함 — ▶ 을 눌러도 재생되지 않음. codex 도 seek 가 PLAYING 을 지나 준비 전 「시작」한 연습을 끊을 수 있다고 지적함(MEDIUM, 추론).
- 2차 구현: 시작 위치를 playerVars.start(정수 초)로 주고, 재생 전(UNSTARTED·CUED)에는 위치 반환이 저장된 시작 위치를 돌려줌. seek 가 없어 재생 이벤트도 없음.
- 회차 b7(tests/agent/runs/2026-11-01-b7): 두 자동 재생 정책 모두 스스로 재생 안 함 · ▶ 로 저장 위치부터 재생 · 재생 전 머물다 떠나도 위치 유지 · 준비 전 「시작」 연습 유지 · 회귀 통과 · 콘솔 예외 0. codex 리뷰(이 변경분): 프런트 findings 0.
<!-- SECTION:NOTES:END -->
