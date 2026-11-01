---
id: TASK-311
title: >-
  화면: 모든 화면의 글자 링크 이동(← · → · Back · Home 등)을 홈 버튼과 같은 크기·모양의 버튼으로 바꿈 (사용자 지시
  2026-11-01)
status: Done
assignee: []
created_date: '2026-11-01 05:39'
updated_date: '2026-11-01 05:53'
labels: []
dependencies: []
ordinal: 376000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자 지시: 모든 화면에 있는 <-, ->, Back, Home 등 html link 로만 되어 있는 것을 home 화면의 버튼 크기와 동일한 스타일로 모두 교체함. 전체 화면 통일성은 Home 을 기준으로 삼음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 글자 링크로 된 이동을 모든 화면에서 찾아 목록을 남김
- [x] #2 찾은 이동이 모두 홈과 같은 버튼 모양·크기임
- [x] #3 이동 대상과 data-testid 가 바뀌지 않음
- [x] #4 tsc·eslint·next build 와 화면 스크린샷으로 확인함
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
바꾼 자리: 홈 ← Close · 세션 실패 ← Home · 코스 ← Home·Day 열기 · Day ← Back(2) · 결과 ← Home·History →·실수 연습 · 기록 Weekly report →·← Home · 주간 ← History · 영상 ← Home·← Videos·YouTube. 범위 밖: 사이드바 · 영상 제목 링크 · 홈 Day 경로 카드. 회차 b15 pages-1400.json: 모든 버튼 36px·13.6px. href·data-testid 는 diff 상 짝수(그대로). /course/<day> 화면은 열면 진도를 저장하므로 찍지 않았음.
<!-- SECTION:NOTES:END -->
