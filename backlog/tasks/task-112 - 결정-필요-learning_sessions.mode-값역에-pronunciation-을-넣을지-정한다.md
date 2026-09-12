---
id: TASK-112
title: '결정 필요: learning_sessions.mode 값역에 pronunciation 을 넣을지 정한다'
status: In Progress
assignee: []
created_date: '2026-09-11 15:43'
updated_date: '2026-09-12 00:25'
labels: []
dependencies: []
ordinal: 117000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST — TASK-10.1 이 발음 전용 모드를 «지시문만» 바꾸는 방식으로 넣었고 세션 행의 mode 는 speaking 으로 남음. 001 의 learning_sessions_mode_check 값역에 그 값이 없기 때문임. ⚠️ 대가: 결과 화면·집계·일일 완료 판정이 이 세션을 말하기 세션으로 셈. ⛔ 모드 리터럴의 소유자는 결정 11 이 TASK-27 로 지목했으므로 이 태스크는 그 결정을 대신하지 않고 «질문을 원장에 세워 두는» 것임. 근거: docs/design/2026-09-12-pronunciation-mode-design.md §5 항목 1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 값역을 늘릴지 정하고 근거를 적는다 — 늘리면 마이그레이션 번호를 착수 턴에 발급한다(결정 27)
- [ ] #2 늘리지 않기로 하면 집계가 이 세션을 어떻게 세는지 문서에 명시한다 — 지금은 조용히 말하기로 섞임
<!-- AC:END -->
