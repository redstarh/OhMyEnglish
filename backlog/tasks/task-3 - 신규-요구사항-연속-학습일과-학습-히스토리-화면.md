---
id: TASK-3
title: '신규 요구사항: 연속 학습일과 학습 히스토리 화면'
status: To Do
assignee: []
created_date: '2026-09-06 00:11'
updated_date: '2026-09-06 01:35'
labels:
  - caps-req
dependencies: []
ordinal: 3000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 6. 신규 요구사항이다. 학습 기록 히스토리에 연속 학습일을 기록하고 학습 히스토리 화면에서 볼 수 있게 한다. 지금 히스토리 화면 자체가 없다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 연속 학습일 정의를 못 박는다(무엇을 1일로 세는가·타임존·끊김 판정)
- [ ] #2 학습 히스토리 화면 요구사항 상세화(무엇을 보여주는가)
- [ ] #3 저장 구조와 계산 위치를 설계에 반영(매번 재계산 대 누적 저장 중 선택 근거)
- [ ] #4 일일 경계를 users.timezone으로 구한다(current_date 금지 — 전역 DB 시각 규약)
<!-- AC:END -->
