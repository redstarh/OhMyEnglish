---
id: TASK-42
title: '실행: DB 비밀번호 회전 + 문서에서 제거 (캡틴 결정 21) — GitHub 공개 push 차단 해소'
status: Awaiting Decision
assignee: []
created_date: '2026-09-07 17:51'
updated_date: '2026-09-07 22:56'
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
- [x] #1 세 선택지 중 하나를 캡틴이 확정한다
- [ ] #2 확정된 조치를 실행하고 GitHub 공개 push 차단이 해소됐는지 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-08 캡틴 결정 21 로 방향이 정해졌다 — 「비밀번호 회전 + 문서에서 제거」. 기각한 대안(이력 재작성 · 무기한 비공개)과 제약 5개의 정본은 docs/ops/captain-instruction-register.md 의 결정 21 이다. 팀리드가 확인한 사실: git remote 가 없어 어디에도 push 되지 않았다 · 파일은 추적 중이고 커밋 7a5bfce 가 의도적으로 넣었다. ⛔ 남은 것은 실행이고 두 가지가 캡틴 몫이다: 공유 DB 라 En-Coach 설정을 함께 고쳐야 하는데 작업세션은 남의 리포를 고치지 않는다 · ALTER ROLE 은 공유 자원 변경이라 캡틴 확인 후에 돈다. TASK-23(원격 연결+첫 푸시)은 이것이 닫히기 전까지 착수하지 않는다.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:16
---
정리(2026-09-08 팀리드): AC#1(캡틴이 선택지 확정)을 체크했다 — 노트가 이미 「캡틴 결정 21로 방향이 정해졌다」고 적었는데 AC가 미체크로 남아 원장이 「아직 아무 결정도 없다」고 거짓말했다. 제목의 「결정 대기:」도 낡아서 제거했다. 남은 것은 AC#2(실행) 하나다.
---

created: 2026-09-07 22:56
---
캡틴 결정 28(2026-09-08): 「실행하지마」 — 회전을 실행하지 않는다. ⚠️ 결정 21 이 정한 **방향은 살아 있다**(회전 + 문서 제거가 옳은 조치라는 판정). 바뀐 것은 지금 실행하지 않는다는 것뿐이다. ⛔ 남는 것 둘: 평문 비밀번호가 추적 중 문서에 그대로 있다 · 그 상태에서 push 하면 공개된다. Awaiting Decision 유지 — 작업세션이 착수하지 않는다.
---
<!-- COMMENTS:END -->
