---
id: TASK-66.8
title: '마감: 선행 검토 §7.4 를 닫고 원장을 갱신한다 (AC#5)'
status: Done
assignee: []
created_date: '2026-09-13 22:11'
updated_date: '2026-09-13 22:58'
labels: []
dependencies:
  - TASK-66.7
parent_task_id: TASK-66
ordinal: 156000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 8. 파일 자리가 정해졌으므로 2026-09-09 선행 검토의 미정 절이 닫힌다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 선행 검토 §7.4 에 닫힘 절을 붙이고 TASK-66 의 AC#1·#2·#4·#5 를 체크한다
- [x] #2 게이트 실측 출력을 노트에 붙인다 — 적었다로 대신하지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

선행 검토 §7.4 에 「닫혔음」 절을 붙였음 — 파일 자리·DB 가 가리키는 것·CHECK 가 강제하는 규약과, 그 절차의 마지막 줄(afconvert 목적지 + check-ignore 확인)을 함께 적었음. ⚠️ §8 의 미결 하나(프론트 재생 경로를 읽지 않았음)도 정정했음 — 그 경로가 0곳이었고 TASK-66.7 이 만들었음.

게이트(이 턴 직접 실행 · 종료코드 확인): pytest 1152 passed exit 0 · ruff check exit 0 · ruff format exit 0(217 files) · ty exit 0 · 프런트 tsc exit 0 · eslint exit 0.
<!-- SECTION:NOTES:END -->
