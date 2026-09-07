---
id: TASK-46
title: '정리: 원장 논리 모순 9건 — 설계만 Done 되고 구현 태스크가 없던 구조를 고친다'
status: In Progress
assignee: []
created_date: '2026-09-07 22:20'
updated_date: '2026-09-07 22:29'
labels: []
dependencies: []
ordinal: 49000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 지시(2026-09-08): 「이미 진행된 작업·남은 작업·진행중 작업이 서로 배치되거나 논리적으로 모순되는 것이 없는지 확인해 정리하고 시작해. 며칠째 진행하는데 마무리가 안 된다.」 원장 45건을 전수 대조해 모순 9건을 찾아 고친 기록이다. 지배 원인은 하나다 — 설계 태스크가 Done·In Progress 로 쌓이는데 그 설계를 코드로 옮기는 구현 태스크가 원장에 등록되지 않았다(마이그레이션 010·011 이 설계서에만 있고 db/migrations/ 는 009 까지였다). 훅이 잡지 못하고 사람이 소유하는 유일한 누락이다(CLAUDE.md work_continuity ②).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 설계 태스크에 섞인 구현 AC 를 갈라 구현 태스크로 등록한다 (TASK-43·44·45 신설)
- [x] #2 다른 태스크가 「넘겼다」고만 적고 받는 쪽 AC 에 없던 요구를 심는다 (TASK-10)
- [x] #3 handoff·노트가 금지한 태스크가 브리핑에서 「착수 가능」으로 뜨는 것을 의존·상태로 고친다 (TASK-23·13·24·36)
- [x] #4 결정을 받았는데 AC·제목이 「대기」로 남은 것을 고친다 (TASK-42)
- [x] #5 리뷰 없이 Done 된 TASK-7·TASK-12 를 팀리드가 검토해 유지·반려를 판정한다
- [ ] #6 정리 결과를 커밋하고 handoff 의 다음 한 걸음을 갱신한다
- [x] #7 critic 4회차의 새 findings(register 줄번호 인용 3건 어긋남)를 줄번호 제거로 영구히 닫는다
<!-- AC:END -->
