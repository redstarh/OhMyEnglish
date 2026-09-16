---
id: TASK-144
title: '정리 회차: 동작을 바꾸지 않고 형태만 고친다 (codebase-cleanup 절차)'
status: In Progress
assignee: []
created_date: '2026-09-16 15:22'
updated_date: '2026-09-16 15:22'
labels: []
dependencies: []
ordinal: 198000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
절차 정본은 ~/.claude/skills/codebase-cleanup/SKILL.md 이고 이 리포 배선은 docs/design/2026-09-16-codebase-cleanup-plan.md 다. 기준선(2026-09-17 착수 시점 직접 측정): HEAD 920dee0 · 테스트 수집 1273 · 통과 1273 · ruff/format/ty 통과 · tsc/eslint exit 0. ⛔ 동작변경=예 는 적용하지 않고 태스크로 갈라낸다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 리뷰 다섯 갈래를 읽기 전용으로 돌리고 발견을 신뢰도 순으로 통합한다
- [ ] #2 적용 묶음을 파일 겹침 0으로 돌린다 — A5(프로토콜 축)는 단독
- [ ] #3 최종 게이트를 리드가 직접 돌려 수집 개수가 기준선 이상임을 보인다
- [ ] #4 동작변경 발견을 태스크로 갈라내고 번호를 보고에 적는다
- [ ] #5 실사용 게이트가 필요한지 판단하고 근거를 보고에 적는다
<!-- AC:END -->
