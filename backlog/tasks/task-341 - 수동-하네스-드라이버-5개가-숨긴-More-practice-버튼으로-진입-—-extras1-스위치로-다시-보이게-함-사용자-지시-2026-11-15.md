---
id: TASK-341
title: >-
  수동 하네스 드라이버 5개가 숨긴 More practice 버튼으로 진입 — ?extras=1 스위치로 다시 보이게 함 (사용자 지시
  2026-11-15)
status: Done
assignee: []
created_date: '2026-11-14 16:55'
updated_date: '2026-11-14 16:59'
labels: []
dependencies: []
ordinal: 408000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-338 이 More practice 를 숨겨 c1_session_walkthrough · c2_render_hierarchy · c5_pronunciation_badge · p_app_path · p_readback_leg 가 practice-* 를 못 찾음. 드라이버는 마이크 대체를 심을 틈 때문에 질의 진입 대신 버튼을 누름(H-CC) — 그 이유를 지키고 주소 스위치로 버튼만 다시 보이게 함.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 홈 ?extras=1 이면 More practice · Practice a pattern 이 보이고 없으면 숨김(시험 먼저)
- [x] #2 드라이버 5개가 ?extras=1 로 홈을 엶
- [x] #3 실제 화면 확인
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
시험 먼저(homeExtras.test.mts — 모듈 없음 실패 → 2 통과). homeExtras.extrasFromQuery · useExtrasFromQuery(서버 렌더 숨김). 드라이버 5개 기본 주소 /?extras=1 · p_readback_leg 머리말에 예외 기록. 화면(b24): 질의 없음 practice-* 0 · focus 0 / ?extras=1 7 · 1. 드라이버 자체는 실물 Nova 가 필요해 이번에 돌리지 않음.
<!-- SECTION:NOTES:END -->
