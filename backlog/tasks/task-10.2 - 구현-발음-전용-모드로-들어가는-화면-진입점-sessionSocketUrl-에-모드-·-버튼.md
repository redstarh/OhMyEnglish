---
id: TASK-10.2
title: '구현: 발음 전용 모드로 들어가는 화면 진입점 (sessionSocketUrl 에 모드 · 버튼)'
status: To Do
assignee: []
created_date: '2026-09-11 15:42'
labels: []
dependencies: []
parent_task_id: TASK-10
ordinal: 115000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST — TASK-10.1 이 지시문과 ?mode=pronunciation 진입 표면까지 만들었고 화면이 없음. TASK-10 노트가 이미 지목한 공백 둘과 같은 자리임: 「어느 화면·어느 버튼이 그 모드로 연결하는가」와 「sessionSocketUrl() 에 모드를 붙이는 URL 조립」. ⛔ 쉐도잉도 같은 공백을 갖고 있으므로 두 모드의 진입을 «같은 문» 으로 두는지가 먼저임 — 그 판정은 TASK-10 의 AC#1 이 소유하고 이 태스크는 그 결정을 구현함. 근거 문서: docs/design/2026-09-12-pronunciation-mode-design.md §5 항목 3.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 TASK-10 AC#1 이 정한 배치대로 진입 버튼을 만들고 sessionSocketUrl 이 모드를 붙이게 한다
- [ ] #2 소리를 고를 수 없는 사용자에게 이 버튼이 무엇을 보이는지 정한다 — 서버는 말하기로 떨어뜨리므로 화면이 침묵하면 사용자가 다른 세션을 받은 것을 모른다
- [ ] #3 브라우저 레그로 실제 진입을 확인한다 — 단위·통합만으로 닫지 않는다
<!-- AC:END -->
