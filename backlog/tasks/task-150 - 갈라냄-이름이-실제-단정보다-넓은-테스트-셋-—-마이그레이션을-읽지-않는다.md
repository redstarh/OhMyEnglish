---
id: TASK-150
title: '갈라냄: 이름이 실제 단정보다 넓은 테스트 셋 — 마이그레이션을 읽지 않는다'
status: To Do
assignee: []
created_date: '2026-09-16 15:36'
labels: []
dependencies: []
ordinal: 211000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
R5(도구 낡음) 리뷰 발견. ① test_claude_schema.py::test_category_and_severity_codes_match_the_schema_check 는 이름이 「스키마 CHECK 와 일치」인데 본문은 Python Literal 파생 튜플과 테스트 안 하드코딩을 비교할 뿐 001 마이그레이션을 읽지 않는다 ② test_pronunciation.py::test_outcome_and_signal_value_domains_match_the_migration 도 같은 형태(도크스트링이 정본을 024 라고 명시) ③ test_weekly_report_job.py::test_the_insight_cap_matches_the_prompt 는 본문이 상수 등식 하나뿐이다(다만 build_weekly_prompt 가 max_points 를 필수 인자로 받아 드리프트 배선 자체가 없어 위험은 낮다). ⇒ 단정을 이름이 약속한 것까지 넓히면(마이그레이션 파일이나 DB 의 CHECK 를 읽게) 값역 드리프트를 실제로 잡는다. ⛔ 테스트를 지우지 않는다 — 넓히는 방향만.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 ①②를 마이그레이션 CHECK 를 읽는 단정으로 넓히고 변이로 검출력을 확인한다
<!-- AC:END -->
