---
id: TASK-23
title: '실행: 원격 저장소 연결 + 첫 푸시'
status: Awaiting Decision
assignee: []
created_date: '2026-09-06 00:14'
updated_date: '2026-09-08 22:19'
labels:
  - caps-req
dependencies:
  - TASK-42
ordinal: 23000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 21. 저장소는 실재한다 — redstarh/OhMyEnglish (직접 확인: PUBLIC · 아직 빈 저장소 · 기본 브랜치 없음). 로컬은 미연결이다. ⚠️ PUBLIC이라 첫 푸시는 되돌리기 어려운 외부 공개 행위다 — 커밋 메시지·설계서·원장이 전부 공개되고, 되돌려도 캐시·색인에 남을 수 있다. 공개 여부는 캡틴이 정한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 PUBLIC 그대로 푸시할지 PRIVATE으로 바꾼 뒤 푸시할지 캡틴 확인을 받는다
- [ ] #2 추적 제외가 제대로 걸려 있는지 확인 — .env 및 비밀값이 이력에 없는지 전체 이력을 검사
- [ ] #3 git remote add 후 첫 푸시. remote가 붙으면 backlog의 remote_operations를 true로 되돌린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 — ⛔ 선행 TASK-42 가 Done 이 됐지만 그것이 「풀렸다」를 뜻하지 않음. 상태를 Awaiting Decision 으로 옮긴 이유: 남은 것이 작업이 아니라 캡틴의 선택이고, To Do 로 두면 SessionStart 브리핑이 「착수 가능」으로 올려 다음 세션이 push 할 수 있음.

무엇이 남았나 (캡틴 결정 41): 회전을 하지 않기로 했으므로 DB 비밀번호가 git 이력에 그대로 있음(도입 커밋 7a5bfce). 현재 트리만 깨끗함. 저장소 설정은 PUBLIC 이므로(결정 30) push 하면 이력째 공개됨.

선택지 셋 — 하나를 캡틴이 고르기 전에는 remote 를 붙이지 않음: ① 그때 비밀번호를 회전한다 ② git 이력을 재작성한다(⚠️ 결정 21 이 기각했음 — handoff·원장·설계서·pitfalls·결정 기록에 커밋 해시 인용이 수십 건이고 전부 무효가 됨) ③ 새 초기 커밋으로 스쿼시해 push 한다(이력을 버리는 대가).

⚠️ 백업이 없는 상태가 이어짐 — 로컬 단독임(결정 30 이 적은 그대로).
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:16
---
정리(2026-09-08 팀리드): 선행 TASK-42를 건다. 근거 — TASK-42 노트가 「TASK-23(원격 연결+첫 푸시)은 이것이 닫히기 전까지 착수하지 않는다」고 적고 handoff 착수 전 필수 #3도 같은 금지를 적는데, 원장에는 의존이 0건이어서 SessionStart 브리핑이 매 세션 이 태스크를 「착수 가능」으로 올렸다. 차단은 상태가 아니라 의존이다(task-management.md 원칙 3).
---

created: 2026-09-07 22:56
---
캡틴 결정 30(2026-09-08): 「구현진행시까지 계속 Public 유지해, 나중에 결정할께」. ⛔ **이것은 push 승인이 아니다** — 저장소 설정을 그대로 두라는 뜻이고, TASK-42 가 결정 28 로 미뤄졌으므로 지금 push 하면 평문 비밀번호가 공개된다. 선행 TASK-42 대기 상태를 유지하고 git remote 를 붙이지 않는다. ⚠️ 백업이 없는 상태가 이어진다 — 로컬 단독이다.
---
<!-- COMMENTS:END -->
