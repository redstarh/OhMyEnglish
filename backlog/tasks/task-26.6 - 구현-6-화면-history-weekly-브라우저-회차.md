---
id: TASK-26.6
title: '구현 6: 화면 /history/weekly + 브라우저 회차'
status: To Do
assignee: []
created_date: '2026-09-13 23:36'
labels: []
dependencies:
  - TASK-26.5
parent_task_id: TASK-26
ordinal: 165000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 6. 프런트 테스트 인프라가 0이라 브라우저 회차가 검증이다. ⛔ 오디오 주소처럼 상대 경로를 쓰지 않고 API_BASE 를 쓴다(TASK-66.7 회차가 그 결함을 잡았다).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 tsc·eslint 가 exit 0 이다
- [ ] #2 history 화면에 닿는 링크를 둔다 — 화면이 있어도 길이 없으면 소비자 0곳과 같다
- [ ] #3 검증 전용 스택에서 화면을 직접 열어 보고 회차를 기록한다 — ⛔ dev DB 를 쓰지 않는다
<!-- AC:END -->
