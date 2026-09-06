---
id: TASK-22
title: '프론트엔드 검증 T4: 결과 화면 5상태와 교정 카드 관측'
status: To Do
assignee: []
created_date: '2026-09-06 00:14'
updated_date: '2026-09-06 01:35'
labels:
  - caps-req
dependencies:
  - TASK-21
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 T4(C3·C4). 실물 글 모델 1회를 쓰는 유일한 프론트 태스크다(상한 승인됨). 자기순환을 피하려고 결과 API JSON과 화면을 대조한다 — API가 화면의 상류다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 5상태 라벨을 확인
- [ ] #2 교정 카드 구조를 단정한다 — 원문/교정문 접두 2개 + 라벨 없는 셋째 줄이 비어 있지 않음
- [ ] #3 결과 API가 낸 이유 문자열이 화면에 있는지 대조. 빈 문자열이면 FAIL이 아니라 BLOCKED
- [ ] #4 얻은 세션 번호를 보존 목록에 적어 정리 대상에서 제외
<!-- AC:END -->
