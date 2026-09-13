---
id: TASK-26.2
title: '구현 2: 주 경계와 조건부 트리거'
status: To Do
assignee: []
created_date: '2026-09-13 23:35'
labels: []
dependencies:
  - TASK-26.1
parent_task_id: TASK-26
ordinal: 161000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 2. services/weekly_report.py 가 주 경계를 한 곳에서 소유하고, enqueue 는 「지난 주 행이 없으면」을 한 문장의 not exists 로 함께 건다(두 왕복으로 하면 중복이 생긴다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 단정 넷이 통과한다 — 지난 주 월요일 · 타임존이 주를 가르는 성질 · 없으면 걸림 · 있으면 안 걸림
- [ ] #2 not exists 절을 지워 red 를 보고 되돌린다
<!-- AC:END -->
