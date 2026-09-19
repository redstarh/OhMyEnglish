---
id: TASK-242
title: '고침: 음성 명령으로 연 세션이 started_via 로 갈리지 않는 것 (TASK-234)'
status: To Do
assignee: []
created_date: '2026-09-19 07:49'
labels: []
dependencies: []
ordinal: 306000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
심각도 MEDIUM · 앱 결함 · 뿌리 그룹 B(진입·기록). 결함 정본은 TASK-234 임. 현상: 음성 명령으로 연 세션도 started_via=ui 로 기록돼 화면 진입과 음성 진입을 가릴 수 없음. 영향: 사용자 화면에 바로 보이지는 않으나 「음성으로도 같은 기능을 제어할 수 있음」(PRD UI와 음성 제어)의 실효를 뒤에서 셀 수 없음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 음성 명령으로 연 세션이 화면 진입과 다른 값으로 기록됨
- [ ] #2 값역이 DB 제약과 어긋나지 않음
- [ ] #3 두 진입을 가르는 검사가 추가되고 그 검사가 고치기 전 코드에서 실패함
- [ ] #4 TASK-234 에 고친 커밋과 판정을 적어 이음
<!-- AC:END -->
