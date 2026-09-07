---
id: TASK-42
title: '결정 대기: DB 비밀번호 평문 노출로 GitHub 공개 push 차단 — 회전/비공개/이력재작성 택1'
status: In Progress
assignee: []
created_date: '2026-09-07 17:51'
updated_date: '2026-09-07 21:52'
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

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-08 캡틴 결정 21 로 방향이 정해졌다 — 「비밀번호 회전 + 문서에서 제거」. 기각한 대안(이력 재작성 · 무기한 비공개)과 제약 5개의 정본은 docs/ops/captain-instruction-register.md 의 결정 21 이다. 팀리드가 확인한 사실: git remote 가 없어 어디에도 push 되지 않았다 · 파일은 추적 중이고 커밋 7a5bfce 가 의도적으로 넣었다. ⛔ 남은 것은 실행이고 두 가지가 캡틴 몫이다: 공유 DB 라 En-Coach 설정을 함께 고쳐야 하는데 작업세션은 남의 리포를 고치지 않는다 · ALTER ROLE 은 공유 자원 변경이라 캡틴 확인 후에 돈다. TASK-23(원격 연결+첫 푸시)은 이것이 닫히기 전까지 착수하지 않는다.
<!-- SECTION:NOTES:END -->
