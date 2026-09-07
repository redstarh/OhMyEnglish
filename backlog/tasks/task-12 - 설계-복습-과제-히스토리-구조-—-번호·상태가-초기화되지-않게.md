---
id: TASK-12
title: '설계: 복습 과제 히스토리 구조 — 번호·상태가 초기화되지 않게'
status: Done
assignee: []
created_date: '2026-09-06 00:13'
updated_date: '2026-09-07 17:54'
labels:
  - caps-req
dependencies: []
ordinal: 12000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
캡틴 노트 항목 19(미결정 5 결정됨). 지금 복습 과제 재계산이 '지우고 다시 넣기'라 과제 번호와 상태가 매번 초기화된다. 읽는 코드가 0곳이라 아직 무해하지만, 화면이 과제 번호로 완료 표시를 하려면 먼저 정해야 한다. 캡틴 결정: 히스토리를 기록하는 구조로 설계한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 현재 재계산이 무엇을 지우고 무엇을 다시 넣는지 코드 심볼로 적는다
- [x] #2 번호 안정성을 어떻게 보장할지 정한다(자연키 대 대리키 중 근거와 함께)
- [x] #3 상태 이력을 어디에 남길지 정한다(같은 표의 이력 컬럼인가 별도 이력 표인가)
- [x] #4 마이그레이션 번호를 지정하고 기존 행 이관 방법을 적는다
<!-- AC:END -->
