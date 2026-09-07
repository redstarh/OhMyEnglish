---
id: TASK-39
title: '설정: botocore 재시도 정책 설정 (Phase 2 운영 관찰 대상)'
status: To Do
assignee: []
created_date: '2026-09-07 17:50'
labels: []
dependencies: []
ordinal: 42000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md E절에서 이관. botocore 재시도 미설정 상태라 스로틀 시 중복 과금 위험이 있다. Phase 2 운영 관찰 시점에 설정한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 botocore 재시도 정책(최대 재시도·backoff)을 설정한다
- [ ] #2 스로틀 재현 또는 관찰로 중복 과금이 사라지는지 확인한다
<!-- AC:END -->
