---
id: TASK-23
title: '실행: 원격 저장소 연결 + 첫 푸시'
status: Awaiting Decision
assignee: []
created_date: '2026-09-06 00:14'
updated_date: '2026-09-06 00:14'
labels: []
dependencies: []
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
