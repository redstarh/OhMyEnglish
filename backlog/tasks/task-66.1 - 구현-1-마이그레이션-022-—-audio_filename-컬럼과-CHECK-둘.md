---
id: TASK-66.1
title: '구현 1: 마이그레이션 022 — audio_filename 컬럼과 CHECK 둘'
status: Done
assignee: []
created_date: '2026-09-13 22:11'
updated_date: '2026-09-13 22:25'
labels: []
dependencies: []
parent_task_id: TASK-66
ordinal: 149000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 1. shadowing_items 에 audio_filename 을 더하고 파일명을 id 로 강제하는 CHECK 와 source_url 이 있는 클립에 오디오를 금지하는 CHECK 를 건다. 정본은 docs/design/2026-09-14-shadowing-clip-audio-plan.md 임.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 스키마 단정 둘이 통과한다 — 규약 밖 파일명 넷과 source_url 이 있는 행이 거부된다
- [x] #2 CHECK 를 or true 로 무력화해 red 를 보고 되돌린다 — 변이 적용을 먼저 단정한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

022 를 썼고 단정 둘이 통과함 — 규약 밖 파일명 넷(다른 확장자·경로 섞임·상위 이탈·남의 이름)과 source_url 이 있는 행이 CheckViolationError 로 거부됨.

red 를 먼저 봤음: UndefinedColumnError 로 2 failed(47 deselected) — -k 필터가 새 테스트를 걸러 0 selected 가 되는 함정을 피했음.

판별력: 파일명 CHECK 를 `or true` 로 무력화해 1 failed 1 passed 를 보고, diff -q 로 원본 동일을 확인한 뒤 2 passed 를 다시 읽었음. 변이 적용 여부는 s2 != s 로 먼저 단정했음.

⛔ dev DB 에 적용하지 않았음 — TASK-66.9 의 승인 사안임. 테스트 DB 는 실행마다 재생성되므로 단정이 이미 그 스키마를 잼.
<!-- SECTION:NOTES:END -->
