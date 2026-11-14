---
id: TASK-316.1
title: '회차 b16-화면: 모든 화면·상태를 1400·390 에서 찍어 스토리보드를 만들고 배치를 판정함'
status: Done
assignee: []
created_date: '2026-11-14 05:30'
updated_date: '2026-11-14 06:36'
labels: []
dependencies: []
parent_task_id: TASK-316
ordinal: 382000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 화면·상태별 스크린샷과 판정 표
- [x] #2 스토리보드 HTML
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
화면 탭 결과 screens/result.md — 판정 13 중 통과 11 · 실패 1(영상 390 잘림 → TASK-321) · 차단 1(마이크 거부: 가짜 권한 UI 우회). 논리 결함 Day 상태 불일치 → TASK-322. 흐름 문제 17건. 호출자 대조 verify/screens.mjs 로 두 결함 재현. Nova 세션 4개(상한 2 초과 · 모두 닫힘 · 발화 0).
<!-- SECTION:NOTES:END -->
