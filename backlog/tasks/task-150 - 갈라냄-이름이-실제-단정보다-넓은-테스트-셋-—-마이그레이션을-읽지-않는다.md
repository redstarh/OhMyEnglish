---
id: TASK-150
title: '갈라냄: 이름이 실제 단정보다 넓은 테스트 셋 — 마이그레이션을 읽지 않는다'
status: Done
assignee: []
created_date: '2026-09-16 15:36'
updated_date: '2026-09-16 22:45'
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
- [x] #1 ①②를 마이그레이션 CHECK 를 읽는 단정으로 넓히고 변이로 검출력을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 완료 (2026-09-17 · 사용자 결정: 넓히고 DB 규칙과 일치 확인)

새로 만든 단정 넷(tests/unit/test_schema.py): error_patterns_category_check ·
error_occurrences_severity_check · pronunciation_attempts_outcome_check ·
pronunciation_attempts_signal_source_check 를 pg_get_constraintdef 로 읽어 파이썬 값역과 집합 비교함.

⛔ 삽입을 하지 않는 형태로 만들었음 — 이 파일의 기존 주석이 「값역의 값을 전부 삽입해 보면 그 루프가
먼저 CheckViolationError 로 실패해 목록 단정에 도달하지 않는다」는 무력화를 기록해 뒀기 때문임.

검출력 확인: SignalSource 에서 transcript_analysis 를 빼는 변이에서 해당 단정이 FAIL 했고 되돌리면 통과함.

이름도 실제와 맞췄음: test_category_and_severity_codes_are_pinned_to_the_known_values ·
test_outcome_and_signal_value_domains_are_pinned_to_the_known_values. 두 자리에 「DB 대조는 어디가
하는가」를 주석으로 가리켜 뒀음 — 한 방향은 파이썬 변경을, 다른 방향은 DB 변경을 잡음.

게이트: 수집 1274 → 1278 · pytest 1278 passed · ruff exit 0 · format exit 0 · ty exit 0.
<!-- SECTION:NOTES:END -->
