---
id: TASK-302
title: '검증: 모든 화면의 메뉴·버튼 전수 회차 (리디자인 뒤)'
status: Done
assignee: []
created_date: '2026-11-01 02:22'
updated_date: '2026-11-01 03:45'
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
- [x] #1 화면별 메뉴·버튼·링크 목록과 각각의 눌림 결과가 표로 기록됨
- [x] #2 새 결함은 재현 절차와 함께 등록되고 고쳐지거나 미결로 남음
- [x] #3 dev DB 쓰기가 없음을 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 b11: 13화면 × 1400/390 · 225회 클릭 · 메뉴 4 × 13 × 2 어긋남 0 · 진입 mode/source/DB 일치 · 비활성 요소 확인 · 영상 추가·삭제·문장 저장 동작. 새 결함 D1(LOW, 위) · 관찰 O2(약점 진입들이 Free talk 와 같은 진입) · O3(Day 를 열기만 해도 진행 중이 됨). 차단: iframe 재생 판정 · stub 세션이 70ms 라 진행 중 잠금은 data-locked 기록으로만. dev DB 기준선 그대로(19·144·0·0·videos 1). ⚠️ 11:40~11:41 격리 DB 의 recommended 세션 4건은 회차 밖 — 사용자 브라우저가 회차용 백엔드에 붙었던 것으로 봄.

b11 D1(카드 줄어듦)은 5a3ff2d(min-h-72) → b12 D2(390 폭 5px) → bf6b938(대기 높이 실측)으로 고침 · b12r 에서 390/1400 모두 대기 높이 이상 확인. 관찰 O2·O3 은 결함 아님(기록만).
<!-- SECTION:NOTES:END -->
