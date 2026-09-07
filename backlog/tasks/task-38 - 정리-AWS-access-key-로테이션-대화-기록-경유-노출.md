---
id: TASK-38
title: '정리: AWS access key 로테이션 (대화 기록 경유 노출)'
status: Awaiting Decision
assignee: []
created_date: '2026-09-07 17:50'
updated_date: '2026-09-07 22:27'
labels: []
dependencies: []
ordinal: 41000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md E절에서 이관. 키가 대화 기록을 경유해 노출됐다. 참조: docs/ops/iam-setup-nova-sigv4.md §6.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 키를 로테이션한다
- [ ] #2 docs/ops/iam-setup-nova-sigv4.md §6 절차를 따라 반영을 확인한다
<!-- AC:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:27
---
연관 감사(2026-09-08 팀리드): To Do → Awaiting Decision. 캡틴 결정 21 제약 5 가 이 태스크를 명시적으로 지목한다 — 「TASK-38(AWS access key 로테이션)도 같은 종류의 미결이다. 함께 보라 — 그것 역시 살아 있는 자격증명이고 실행은 캡틴 몫이다.」 실행 주체가 캡틴이므로 To Do 로 두면 브리핑이 「착수 가능」으로 올려 작업세션이 손댈 수 없는 일을 매번 다시 집어 든다. TASK-42(DB 비밀번호 회전)와 한 묶음으로 본다.
---
<!-- COMMENTS:END -->
