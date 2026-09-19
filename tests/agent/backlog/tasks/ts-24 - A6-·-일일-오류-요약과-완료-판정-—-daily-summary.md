---
id: TS-24
title: A6 · 일일 오류 요약과 완료 판정 — daily-summary
status: Blocked
assignee: []
created_date: '2026-09-19 05:18'
updated_date: '2026-09-19 06:02'
labels: []
dependencies: []
ordinal: 24000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
영역 A6. 대상: GET /api/daily-summary. 근거: PRD §13·§14. ⛔ 날짜 경계는 사용자 타임존으로 갈림 — UTC 자정부터 09시 KST 사이에 current_date 가 하루 이르다는 함정을 반드시 검사에 넣음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 그날의 오류 요약이 사용자 타임존 기준으로 갈림 (UTC 자정~09시 KST 구간을 직접 재현)
- [x] #2 일일 학습 완료 판정이 시나리오 1개 기준으로 성립함 (PRD §14)
- [x] #3 기록이 없는 날의 응답 경계가 오류가 아니라 빈 결과로 나옴
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
회차 2026-09-19-b3 (HEAD ced8df0). AC#2·#3 통과. AC#1 은 차단됨 — 측정 시각(05:44~06:2x UTC)에 current_date 와 KST 날짜가 같아 판별력이 없고, daily_error_summary 의 쓰기 경로는 분석 워커에서만 돌아 유료 호출 없이 지나갈 수 없음. users.timezone 임시 변경 승인을 호출 세션에 요청했으나 회차 끝까지 답이 오지 않았음. ⛔ 「0건 관측」을 결함으로 올리지 않았음. 다만 같은 날짜 경계 요구(R14-3)는 ended_at=2026-09-16 15:10+00 세션을 함정 구간에 심어 통과 확인했음. 상세는 result.md §5-4·§6-1.
<!-- SECTION:NOTES:END -->
