---
id: TASK-42
title: '결정 대기: DB 비밀번호 평문 노출로 GitHub 공개 push 차단 — 회전/비공개/이력재작성 택1'
status: Awaiting Decision
assignee: []
created_date: '2026-09-07 17:51'
updated_date: '2026-09-07 17:51'
labels: []
dependencies: []
ordinal: 45000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md H절 이관 중 발견(원 지시 docs/design/2026-08-30-tasks-md-migration-spec.md §비태스크 ③). docs/ops/shared-database-naming-rules.md 에 En-Coach 역할의 평문 비밀번호가 있다(커밋 7a5bfce). 이 때문에 이 리포의 GitHub 공개 push 가 차단돼 있다(DevInfra/TASKS.md Task 10-1). 선택지: (1) 비밀번호 회전 (2) 이 리포만 비공개로 전환 (3) git 이력 재작성. 캡틴 결정이 필요하다 — 작업자가 임의로 정하지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 세 선택지 중 하나를 캡틴이 확정한다
- [ ] #2 확정된 조치를 실행하고 GitHub 공개 push 차단이 해소됐는지 확인한다
<!-- AC:END -->
