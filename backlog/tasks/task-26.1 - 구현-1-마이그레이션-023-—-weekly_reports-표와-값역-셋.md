---
id: TASK-26.1
title: '구현 1: 마이그레이션 023 — weekly_reports 표와 값역 셋'
status: Done
assignee: []
created_date: '2026-09-13 23:35'
updated_date: '2026-09-13 23:40'
labels: []
dependencies: []
parent_task_id: TASK-26
ordinal: 160000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 1. 표 하나 + job_type 값역 + 상호배타 CHECK + llm_calls.purpose 값역을 한 파일에 담는다. ⛔ 값역만 늘리면 job 이 들어가지 않는다(018 의 경고).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 스키마 단정 넷이 통과한다 — 월요일 CHECK · (user_id, week_start) 중복 거부 · job 대상 상호배타 · llm_calls 의 새 purpose
- [x] #2 docs/database-schema.md 를 같은 커밋에서 고친다 — 제안과 달라진 둘(metrics · plan 을 insights 안에)을 적는다
- [x] #3 월요일 CHECK 를 무력화해 red 를 보고 되돌린다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
완료 2026-09-14 (세션 ohmyenglish-f4).

red 를 먼저 봤음 — 표 부재 셋(UndefinedTableError)과 값역 위반 하나(CheckViolationError)로 4 failed.

⚠️ 계획서에 없던 컬럼 하나를 더했음 — timezone(not null · 공백 거부). 근거는 이웃 표에서 읽었음: daily_error_summary 가 「그 날짜를 그은 타임존을 스냅샷으로 함께 남긴다 — users.timezone 이 바뀌면 과거 요약이 어느 경계로 그어졌는지 복원할 수 없다」로 같은 부류의 값을 다루고 있음. 주 경계도 같은 이유로 필요함.

⚠️ 함정 둘을 밟고 고쳤음: ⑴ asyncpg 가 date 파라미터에 문자열을 받지 않음('str' object has no attribute 'toordinal') — date 객체로 줬음 ⑵ test_001_migration_creates_expected_tables 가 표 이름 «집합»을 정확히 비교하므로 weekly_reports 를 그 자리에 넣어야 했음(그 단정의 주석이 「새 표는 반드시 여기 들어와야 한다」로 미리 경고해 뒀음).

판별력: 월요일 CHECK 를 check (true) 로 열어 DID NOT RAISE 를 보고, 되돌린 뒤 __pycache__ 를 지우고 4 passed 를 다시 읽었음(H-BS).

게이트: test_schema.py 53 passed.

문서를 같은 커밋에서 고쳤음 — database-schema.md 에 weekly_reports 절을 넣고, 「아직 SQL 에 없는 테이블」 절을 「없다」로 바꾸고, 다이어그램 머리말의 낡은 서술을 정정했음. ⛔ 제안 컬럼을 미리 적어 두는 관행에 경고를 남겼음 — 이번에 제안(metrics_json·plan)과 실제(metrics·insights)가 갈렸음.
<!-- SECTION:NOTES:END -->
