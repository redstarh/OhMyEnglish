---
id: TS-25
title: A7 · 연속 학습일과 학습 히스토리 — history
status: Blocked
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 06:02'
labels: []
dependencies: []
ordinal: 25000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A7. 대상: GET /api/history · 화면 /history. 근거: PRD §15. 실물 외부 호출 없음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 연속 학습일 계산이 사용자 타임존 기준으로 성립함
- [x] #2 화면 /history 가 세션 목록을 사람이 읽을 수 있게 냄
- [ ] #3 기록 0건일 때 화면이 빈 목록 안내를 냄 (H-CA 의 하이드레이션 판정 근거와 같은 문구)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 2026-09-19-b3 (HEAD ced8df0). AC#1·#2 통과. AC#1 은 ended_at 의 UTC 날짜(2026-09-16)와 KST 날짜(2026-09-17)가 갈리는 세션을 직접 심어 가렸음 — 2026-09-17 줄에 들어가고 09-16 은 learned=false 로 남았으며 연속일이 2→3 으로 움직였음. AC#3 은 차단됨 — /api/history 의 days 가 항상 30줄이라 목록이 빌 수 없음(R15-5 가 요구한 것). 전제를 세우려면 회차가 만들지 않은 완료 세션을 지워야 해서 하지 않았음. AC 문면 문제는 결함 TASK-231 (작업 원장) 이 가짐. 상세는 result.md §5-5·§5-6·§6-2.
<!-- SECTION:NOTES:END -->
