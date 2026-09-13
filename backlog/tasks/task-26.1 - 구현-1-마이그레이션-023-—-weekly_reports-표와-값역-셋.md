---
id: TASK-26.1
title: '구현 1: 마이그레이션 023 — weekly_reports 표와 값역 셋'
status: To Do
assignee: []
created_date: '2026-09-13 23:35'
labels: []
dependencies: []
parent_task_id: TASK-26
ordinal: 160000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 1. 표 하나 + job_type 값역 + 상호배타 CHECK + llm_calls.purpose 값역을 한 파일에 담는다. ⛔ 값역만 늘리면 job 이 들어가지 않는다(018 의 경고).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 스키마 단정 넷이 통과한다 — 월요일 CHECK · (user_id, week_start) 중복 거부 · job 대상 상호배타 · llm_calls 의 새 purpose
- [ ] #2 docs/database-schema.md 를 같은 커밋에서 고친다 — 제안과 달라진 둘(metrics · plan 을 insights 안에)을 적는다
- [ ] #3 월요일 CHECK 를 무력화해 red 를 보고 되돌린다
<!-- AC:END -->
