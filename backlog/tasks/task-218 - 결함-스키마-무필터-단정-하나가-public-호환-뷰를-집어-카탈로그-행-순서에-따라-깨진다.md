---
id: TASK-218
title: '결함: 스키마 무필터 단정 하나가 public 호환 뷰를 집어 카탈로그 행 순서에 따라 깨진다'
status: Done
assignee: []
created_date: '2026-09-18 18:43'
updated_date: '2026-09-18 18:46'
labels: []
dependencies: []
ordinal: 279000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASK-41 이 같은 실패 모드를 세 자리에서 고치고 주석까지 남겼는데 test_schema.py:896 의 test_pronunciation_attempts_attempt_seq_is_generated_always 한 자리가 빠졌다. information_schema.columns 를 table_schema 없이 조회해 fetchrow 가 026 의 public 호환 뷰 행을 집으면 is_identity 가 NO 로 와서 단정이 뒤집힌다. 실측 2026-09-19: ohmyenglish_test 에서는 public 행이 먼저 나와 실패하고 ohmyenglish 에서는 ohmyenglish 행이 먼저 나와 통과한다 — 카탈로그 행 순서에 붙어 있어 어느 쪽도 이 단정이 재려는 성질이 아니다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 896행 단정이 table_schema = current_schema() 를 걸고 이웃 세 자리와 같은 형태가 된다
- [x] #2 tests/unit/test_schema.py 의 information_schema 조회 네 자리 전부가 스키마를 건다
- [x] #3 pytest 가 이 단정을 포함해 통과한다
<!-- AC:END -->
