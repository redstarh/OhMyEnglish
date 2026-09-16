---
id: TASK-146
title: '갈라냄: 타임존 조회 SQL 과 그 널 검사가 5파일에 동일하게 반복된다 — 문구 통일이 동작변경이다'
status: Done
assignee: []
created_date: '2026-09-16 15:29'
updated_date: '2026-09-16 22:38'
labels: []
dependencies: []
ordinal: 207000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R1(재사용) 리뷰 발견. _TIMEZONE_SQL = 'select timezone from users where id = $1' 와 그 뒤 4행(fetchval → None 이면 LookupError)이 chronic.py · daily_summary.py · scenario_progress.py · usage.py · weekly_report.py 에 바이트 단위로 동일하다. daily_summary._timezone_of 가 이미 그 4행을 감쌌다. ⛔ 합치면 LookupError 문구가 파일마다 다른 것이 통일된다(no timezone source of truth · 주간 사실을 읽을 수 없다 · 주 경계를 구할 수 없다) — 문면 변경이라 정리 회차 밖으로 갈라낸다. ⚠️ 그리고 대상 파일 다섯 중 셋(chronic·scenario_progress·usage)이 이 회차의 어느 묶음에도 없어 파일 겹침 0 규칙과도 충돌한다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 문구를 통일할지, 파일별 문구를 유지하며 SQL 만 공유할지 사용자가 고른다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 완료 (2026-09-17 · 사용자 결정: 합쳐)

신설: services/user_timezone.py — SQL 과 널 검사의 정본. 다섯 자리가 그것을 부름
(chronic · scenario_progress · usage · daily_summary · weekly_report). daily_summary 는 자기 정의를
지우고 재수출만 함(api/daily.py 가 그 이름으로 부름). weekly_report 의 last_week_start 도 사용자
없음 판정을 정본에 맡김.

⚠️ 예외 문면이 하나로 통일됐음 — 사용자가 알고 고른 대가임. 전수 확인: 이제 SQL 1건 · 문면 1건.
⛔ plan_input.py 는 대상 밖 — 그 SQL 은 current_level 까지 함께 읽어 같은 조회가 아님(합치면 왕복이 늘어남).

게이트: pytest 1274 passed · ruff exit 0 · format exit 0 · ty exit 0. 줄 수는 57줄 줄었음.
<!-- SECTION:NOTES:END -->
