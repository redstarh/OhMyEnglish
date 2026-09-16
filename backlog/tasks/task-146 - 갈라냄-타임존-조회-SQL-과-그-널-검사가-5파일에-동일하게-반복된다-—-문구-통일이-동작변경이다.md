---
id: TASK-146
title: '갈라냄: 타임존 조회 SQL 과 그 널 검사가 5파일에 동일하게 반복된다 — 문구 통일이 동작변경이다'
status: To Do
assignee: []
created_date: '2026-09-16 15:29'
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
- [ ] #1 문구를 통일할지, 파일별 문구를 유지하며 SQL 만 공유할지 사용자가 고른다
<!-- AC:END -->
