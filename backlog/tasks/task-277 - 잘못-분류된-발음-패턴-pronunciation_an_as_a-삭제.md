---
id: TASK-277
title: 잘못 분류된 발음 패턴 pronunciation_an_as_a 삭제
status: Done
assignee: []
created_date: '2026-09-26 09:42'
updated_date: '2026-09-26 09:43'
labels: []
dependencies: []
ordinal: 341000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 결정 2026-09-26(AskUserQuestion: 기록 삭제). 관사 선택 오류가 발음 패턴으로 쌓여 발음 교정 고리를 부름(TASK-276 리뷰 MEDIUM 2)
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 참조 행을 전부 세고 삭제 범위를 확정함
- [x] #2 백업 뒤 삭제하고 남은 참조 0 을 확인함
- [x] #3 결과를 원장에 남기고 커밋함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
범위: error_patterns 1행(99fc908f · 빈도 3) → review_tasks 3행 cascade 삭제 · pronunciation_attempts 3행은 pattern_id 만 null(판정 기록 6행 유지 · R10-7 의 「판정 결과는 남김」) · session_plans 5행의 배열 참조는 FK 없고 SQL 로 읽는 곳 0 이라 그대로 둠(최신 계획 12:01 은 미포함). 백업 ~/Backups/OhMyEnglish/ohmyenglish-before-TASK-277-20260926-1843.dump. 삭제 뒤 패턴 0 · 복습 0 · 연결 0 · load_known_sounds 결과 빈 목록.
<!-- SECTION:NOTES:END -->
