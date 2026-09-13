---
id: TASK-66.1
title: '구현 1: 마이그레이션 022 — audio_filename 컬럼과 CHECK 둘'
status: To Do
assignee: []
created_date: '2026-09-13 22:11'
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
- [ ] #1 스키마 단정 둘이 통과한다 — 규약 밖 파일명 넷과 source_url 이 있는 행이 거부된다
- [ ] #2 CHECK 를 or true 로 무력화해 red 를 보고 되돌린다 — 변이 적용을 먼저 단정한다
<!-- AC:END -->
