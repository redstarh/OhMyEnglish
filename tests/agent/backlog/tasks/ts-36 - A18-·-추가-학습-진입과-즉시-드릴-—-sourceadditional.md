---
id: TS-36
title: A18 · 추가 학습 진입과 즉시 드릴 — source=additional
status: To Do
assignee: []
created_date: '2026-09-19 05:22'
labels: []
dependencies: []
ordinal: 36000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A18. 대상: 추가 학습 진입 경로(?source=additional)와 즉시 드릴 진입. 근거: PRD §7 Additional Learning · 설계서 2026-09-12-additional-learning-entry-design.md · 2026-09-08-immediate-drill-entry-design.md. ⛔ 세션 화면을 ?mode=… 쿼리로 열지 않음 — 페이지 로드 즉시 getUserMedia 가 불려 마이크 대체를 심을 틈이 없음(함정 H-CC). 쿼리 없이 / 로 열어 대체본을 먼저 심고 화면의 진입 버튼을 누를 것.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 하루 학습량을 채운 뒤에도 추가 학습을 시작할 수 있음
- [ ] #2 추가 학습 종류(자유 대화·질문 다섯 개 더·자주 틀리는 패턴·업무 역할극·쉐도잉) 가운데 최소 셋이 진입됨
- [ ] #3 자주 틀리는 패턴에서 즉시 드릴을 만드는 경로가 성립함 (requirements-summary 「이 문법으로 연습 만들어줘」)
<!-- AC:END -->
