---
id: TASK-23
title: '실행: 원격 저장소 연결 + 첫 푸시'
status: Done
assignee: []
created_date: '2026-09-06 00:14'
updated_date: '2026-09-08 22:37'
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
- [x] #1 PUBLIC 그대로 푸시할지 PRIVATE으로 바꾼 뒤 푸시할지 캡틴 확인을 받는다
- [x] #2 추적 제외가 제대로 걸려 있는지 확인 — .env 및 비밀값이 이력에 없는지 전체 이력을 검사
- [x] #3 git remote add 후 첫 푸시. remote가 붙으면 backlog의 remote_operations를 true로 되돌린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-09 — ⛔ 선행 TASK-42 가 Done 이 됐지만 그것이 「풀렸다」를 뜻하지 않음. 상태를 Awaiting Decision 으로 옮긴 이유: 남은 것이 작업이 아니라 캡틴의 선택이고, To Do 로 두면 SessionStart 브리핑이 「착수 가능」으로 올려 다음 세션이 push 할 수 있음.

무엇이 남았나 (캡틴 결정 41): 회전을 하지 않기로 했으므로 DB 비밀번호가 git 이력에 그대로 있음(도입 커밋 7a5bfce). 현재 트리만 깨끗함. 저장소 설정은 PUBLIC 이므로(결정 30) push 하면 이력째 공개됨.

선택지 셋 — 하나를 캡틴이 고르기 전에는 remote 를 붙이지 않음: ① 그때 비밀번호를 회전한다 ② git 이력을 재작성한다(⚠️ 결정 21 이 기각했음 — handoff·원장·설계서·pitfalls·결정 기록에 커밋 해시 인용이 수십 건이고 전부 무효가 됨) ③ 새 초기 커밋으로 스쿼시해 push 한다(이력을 버리는 대가).

⚠️ 백업이 없는 상태가 이어짐 — 로컬 단독임(결정 30 이 적은 그대로).

2026-09-09 — 캡틴이 푸시를 승인함(「원격저장소는 이미 사전 승인했으니, 푸쉬해서 진행해」). Awaiting Decision → In Progress.

AC#1 — PUBLIC 그대로 푸시로 확정. 결정 30 이 PUBLIC 유지를 정했고 이 승인이 push 를 열었음.

AC#2 — 전체 이력 검사를 돌렸음 (팀리드 직접):
· AWS 키 패턴: git log --all -G'AKIA[0-9A-Z]{16}' → 0건.
· .env 커밋 이력: 없음. .env.example · app/frontend/.env.example 만 추적되고 그 안의 DATABASE_URL 은 postgresql://ohmy:ohmy@... 로 자리표시자임.
· DB 비밀번호: 커밋 3건에 걸쳐 있음 — 7a5bfce(도입) → 44611e7(이관 시 수정) → f53bb51(오늘 제거). 즉 현재 트리는 깨끗하고 이력에는 남아 있음.

⚠️ 노출 크기를 실측했음 — 예상보다 작음: Postgres 의 listen_addresses 가 localhost 이고 127.0.0.1·[::1] 에만 바인딩됨(lsof 확인). 즉 그 비밀번호는 이 머신에 셸 접근이 있는 사람에게만 쓸모가 있음. 공개의 한계 위험이 낮다는 뜻이고, 회전 면제(결정 41)의 대가가 그만큼 작음. ⛔ 다만 0 은 아님 — 값이 공개 색인에 남고 되돌려도 캐시에 남음.

AC#3 — git remote add 완료(https://github.com/redstarh/OhMyEnglish.git). ls-remote 로 저장소가 실재하고 비어 있음을 확인함. ⛔ 첫 푸시는 인증에서 막혔음: gh 토큰 만료(gh auth status 가 invalid) · SSH 키가 GitHub 에 미등록(Permission denied (publickey)) · 키체인에 유효한 HTTPS 자격증명 없음(--dry-run 이 could not read Username). 사용자 인증이 선행이며 그것은 대리 실행 대상이 아님.
⚠️ backlog 의 remoteOperations 는 푸시 성공까지 false 로 둠 — 인증이 안 되는 remote 를 켜면 backlog 명령이 매번 실패함.

2026-09-09 완료 — 캡틴 결정 42. 첫 푸시가 실제로 도착했음.

인증 경위(기록해 둠 — 다음에 같은 자리에서 헛짚지 않게): gh 토큰이 무효라 push 가 could not read Username 으로 막혔음. 원인은 git 이 자격증명을 gh 에 위임하는 설정(credential.helper = !gh auth git-credential)이고, ⛔ 브라우저에서 GitHub 에 로그인하는 것은 CLI 토큰을 갱신하지 않음. gh auth login 의 기기 코드 승인이 끝난 뒤에야 ✓ Logged in · scope repo 가 됐음. 「로그인했다」를 증거로 쓰지 않고 매번 gh auth status + git push --dry-run 으로 확인했음.

AC#3 — git remote add(https://github.com/redstarh/OhMyEnglish.git) 후 첫 푸시 완료. main(e8508e5) 을 먼저 올려 기본 브랜치를 잡고 design/first-vertical-slice(5539c6f · 커밋 441개)를 이어 올렸음 — 순서를 반대로 하면 GitHub 이 작업 브랜치를 기본으로 잡음. 원격 HEAD 가 main 을 가리키는 것을 확인했음. git ls-remote 로 대조: refs/heads/main=e8508e5 · refs/heads/design/first-vertical-slice=5539c6f 로 로컬과 일치. 푸시된 트리에 .env 없음. backlog 의 remoteOperations 를 true 로 되돌리고 그 상태에서 backlog 가 도는 것을 확인했음.

⚠️ 임시 픽스처(app/frontend/public/harness/)는 .git/info/exclude 로 막아 두었으므로 올라가지 않았음 — 확인했음.

⛔ 잔여 위험이 이제 실현됐음: DB 비밀번호가 공개 저장소의 git 이력에 있음(결정 41 이 회전 면제). 되돌려도 캐시·색인에 남음. 크기는 작음 — Postgres 가 localhost 전용 바인딩이라 이 머신 셸 접근자에게만 쓸모가 있음. 그래도 0 은 아님. 없애는 선택지 셋은 결정 42 가 소유함.
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
