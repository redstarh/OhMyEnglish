---
id: TASK-28
title: 원장 마이그레이션 마감 — TASKS.md 분류를 Backlog로 옮긴다
status: To Do
assignee: []
created_date: '2026-09-06 01:37'
updated_date: '2026-09-06 02:25'
labels:
  - caps-req
dependencies: []
ordinal: 28000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
문서 정리 점검(2026-09-06)에서 발견. docs/design/2026-08-30-tasks-md-migration-spec.md 가 '분류는 캡틴이 확정했고 실행만 남았다'고 적은 미실행 작업 지시인데 태스크로 등록돼 있지 않았다 — 보관 후보로 훑다가 잡았다. 2026-09-06에 캡틴 회신 후속을 Backlog에 새로 등록했지만 그것은 이 지시의 실행이 아니다. ⚠️ 이 문서는 폐기 대상이 아니다 — 인용 0곳이지만 대체 문서가 없고 실행이 남았다(보관 판정 기준 3개 중 1번 미충족).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 TASKS.md 의 각 절이 태스크인지 영구 지식인지 분류한다 — 지시 문서의 분류 결정을 따른다
- [ ] #2 태스크인 것만 Backlog로 옮기고 나머지는 docs/design 또는 docs/ops/pitfalls.md 로 보낸다
- [ ] #3 TASKS.md 를 지우지 않는다 — 다른 문서가 절 제목으로 인용한다. 옮긴 뒤 남는 것이 무엇인지 적는다
- [ ] #4 완료 후 지시 문서를 보관소로 보낸다(그때는 보관 기준 3개가 충족된다)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
handoff 줄 수 정리는 2026-09-06에 선행 처리했다 — 475줄 → 137줄(72% 감소). 이전 판은 handoff/backup/2026-09-06/HANDOFF-full-475lines.md 가 소유한다(지우지 않고 옮겼다). 이 태스크의 남은 범위는 TASKS.md 분류를 Backlog 로 옮기는 것이다 — handoff 는 이미 정리됐다.
<!-- SECTION:NOTES:END -->
