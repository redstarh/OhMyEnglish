---
id: TASK-338
title: 홈에서 More practice 전체와 Practice a pattern 을 숨김 — 매일 연습만 남김 (사용자 결정 2026-11-15)
status: Done
assignee: []
created_date: '2026-11-14 16:26'
updated_date: '2026-11-14 16:31'
labels: []
dependencies: []
ordinal: 405000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
사용자: Weak spots · Free talk 메뉴가 없어도 될 것 같아, 일단 매일매일 연습하는 것만 있으면 될 것 같아, 필요하면 나중에 넣자. 범위(AskUserQuestion): More practice 전체를 숨김 · Focus patterns 의 Practice a pattern 도 숨김 · 화면과 코드는 지우지 않고 숨기기만 함(나중에 다시 켬). 홈에 남는 것: Today's practice · Continue your path · Your progress · Focus patterns(목록만).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 More practice 와 Practice a pattern 이 홈에 보이지 않음 · 코드는 남김
- [x] #2 1400·390 실제 화면 확인 · 카드 높이 회귀 없음
- [x] #3 설계서 §3 에 기록
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
구현(내가): HOME_EXTRAS 플래그로 More practice · Practice a pattern 숨김(코드 유지). 확인(b23 hide.mjs · 사용자 스택): 1400·390 practice-* 0 · focus-practice 0 · 남은 섹션 Continue your path · Focus patterns · 카드 513.6 · 가로 넘침 없음. tsc 0 · eslint 0 · next build 0 · pytest 1516. ⚠️ 수동 하네스 드라이버 5개가 practice-* 버튼으로 진입 — 다음 실물 회차 전 진입 방법 변경 필요(설계서 §3 기록).
<!-- SECTION:NOTES:END -->
