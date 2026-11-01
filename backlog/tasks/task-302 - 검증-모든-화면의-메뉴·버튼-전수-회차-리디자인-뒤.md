---
id: TASK-302
title: '검증: 모든 화면의 메뉴·버튼 전수 회차 (리디자인 뒤)'
status: To Do
assignee: []
created_date: '2026-11-01 02:22'
labels: []
dependencies:
  - TASK-301
ordinal: 367000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시 2026-11-01 「모든 화면 메뉴에 대한 Test 를 수행했어? 진행 안했으면 Test Agent 로 수행해」. 회차 b9 는 사이드바 활성 표시와 대표 흐름만 봤음. 이번에는 홈·문법 코스(목록·Day)·영상(목록·상세·낱말·문장)·이력·주간·결과 화면과 사이드바·좁은 화면 막대의 모든 메뉴·버튼·링크를 하나씩 눌러 결과를 기록함. TASK-301(카드 안 세션)을 합친 뒤의 화면을 잼. 격리 DB + VOICE_ADAPTER=stub.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 화면별 메뉴·버튼·링크 목록과 각각의 눌림 결과가 표로 기록됨
- [ ] #2 새 결함은 재현 절차와 함께 등록되고 고쳐지거나 미결로 남음
- [ ] #3 dev DB 쓰기가 없음을 확인함
<!-- AC:END -->
