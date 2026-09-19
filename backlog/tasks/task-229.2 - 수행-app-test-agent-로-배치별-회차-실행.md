---
id: TASK-229.2
title: '수행: app-test-agent 로 배치별 회차 실행'
status: In Progress
assignee: []
created_date: '2026-09-19 05:11'
updated_date: '2026-09-19 05:19'
labels: []
dependencies:
  - TASK-229.1
parent_task_id: TASK-229
ordinal: 292000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
배치마다 app-test-agent 를 띄워 시나리오를 실행함. ⛔ 에이전트는 대상 소스를 고치지 않음 — 실패는 결함으로만 등록함. 서버(:8002 백엔드 · :3000 프런트)는 호출 세션이 띄워 두므로 에이전트가 띄우거나 죽이지 않음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 배치 전부가 실행돼 시나리오마다 판정이 남음
- [ ] #2 실패마다 증거 파일이 runs 아래 evidence 에 남음
- [ ] #3 실패마다 작업 원장에 결함 태스크가 등록됨
<!-- AC:END -->
