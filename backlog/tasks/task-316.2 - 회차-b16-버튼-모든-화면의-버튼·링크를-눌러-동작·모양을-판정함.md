---
id: TASK-316.2
title: '회차 b16-버튼: 모든 화면의 버튼·링크를 눌러 동작·모양을 판정함'
status: Done
assignee: []
created_date: '2026-11-14 05:30'
updated_date: '2026-11-14 06:31'
labels: []
dependencies: []
parent_task_id: TASK-316
ordinal: 383000
---

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 버튼 목록과 동작 판정 표
- [x] #2 결함은 재현 절차와 함께
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
버튼 탭 결과 tests/agent/runs/2026-11-14-b16/buttons/result.md — 동작 97 중 통과 96 · 실패 1(D1). 호출자 대조: D1 을 verify/d1.mjs 로 직접 재현(TASK-319). D2·D4·문서 불일치 → TASK-320. D3(기준 밖 버튼 묶음)은 범위 결정이라 보고서에 사용자 결정으로 올림.
<!-- SECTION:NOTES:END -->
