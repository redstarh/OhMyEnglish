---
id: TASK-252
title: '결정 대기: PRD.md:70 의 「이 패턴으로 연습 만들어줘」 음성 경로를 어떻게 할지 (TASK-251)'
status: Done
assignee: []
created_date: '2026-09-19 12:14'
updated_date: '2026-09-19 13:27'
labels: []
dependencies: []
ordinal: 316000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
⛔ 제품 요구사항 판단이라 사람이 골라야 함 — 어느 쪽도 코드로 유도되지 않음. 결함 정본은 TASK-251 임. 갈림: PRD.md:70 은 사용자가 「질문 더 주세요」와 「이 패턴으로 연습 만들어줘」라고 «말해서» 즉시 드릴을 만들 수 있다고 적음. 앞의 것(next_question)은 음성 명령으로 구현돼 있고 뒤의 것은 경로가 없음 — start_additional 만 즉시 드릴에 닿는데 AdditionalTarget 값역 넷(conversation·scenario_intake·pronunciation·shadowing)에 패턴 키를 실을 자리가 없음. TASK-241 이 구현한 것은 «화면 링크»(경로 B)이고 그 소스 주석이 두 경로를 명시로 갈라 두었음. 경로 A 는 TASK-7 이 범위 밖으로 갈라 두고 Done 이 됐고, 그것을 이어받은 TASK-233 도 경로 B 만 구현하고 Done 이 됐음 ⇒ 요구는 살아 있고 소유자가 다시 없음. 두 갈래: ⑴ 경로 A 를 구현함(start_additional 에 패턴 키를 실을 자리를 열어야 하고 실물 Nova 없이는 관측이 안 되는 대가를 함께 받음) ⑵ PRD.md:70 에서 그 인용을 철회해 요구를 닫음(TASK-246 이 R10-4 에 쓴 것과 같은 모양).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자가 두 갈래 가운데 하나를 골랐음
- [x] #2 고른 근거가 docs/design 에 결정 기록으로 남았음
- [x] #3 고른 갈래대로 PRD 또는 코드가 바뀌었음
<!-- AC:END -->
