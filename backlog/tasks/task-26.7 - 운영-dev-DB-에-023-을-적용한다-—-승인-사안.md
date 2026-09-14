---
id: TASK-26.7
title: '운영: dev DB 에 023 을 적용한다 — 승인 사안'
status: Done
assignee: []
created_date: '2026-09-13 23:36'
updated_date: '2026-09-14 06:39'
labels: []
dependencies:
  - TASK-26.6
parent_task_id: TASK-26
ordinal: 166000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
계획서 Task 7. ⛔ 사용자 승인 없이 착수하지 않는다. 011 의 5단계를 따르고 백업에 -T 'harness_*' 를 붙인다(H-BT).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 사용자 승인을 받는다
- [x] #2 적용 전후 조회 출력을 원장에 남긴다 — migrate.py 는 조용한 성공이라 출력만으로 판정하지 않는다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-14 세션 `ohmyenglish-93` — 사용자 승인을 이 세션에서 직접 받아 011 의 5단계로 적용했음.

승인 경위: `AskUserQuestion` 으로 「승인함 — 023 적용과 함께 진행」을 받았음. ⛔ 다른 세션의 승인을 근거로 쓰지 않았음.

① 백업: `/tmp/ohmy-dev-backup-before-023-20260914-153823.sql`(117k · `pg_dump -n public -T 'harness_*'` · exit 0). `H-BT` 대로 `harness_*` 를 제외했고 파이프에 걸지 않아 종료코드가 `pg_dump` 것임.

② 적용 전: `schema_migrations` 20건 · `weekly_reports` 부재(0) · `utterances` 128. ⚠️ 011 머리말의 「`utterances` 114행 유지」는 낡은 값임 — 그 뒤 늘었으므로 대조 기준으로 쓰지 않았음.

③ 적용: `app/backend/.venv/bin/python scripts/migrate.py` · exit 0 · 출력 0줄. 011 이 경고한 조용한 성공이라 출력으로 판정하지 않았음.

④ 적용 후 재조회: `schema_migrations` 21건 · `023_weekly_reports.sql` 이 `2026-09-14 06:38:51+00` 에 적용됨 · `weekly_reports` 생성 확인. 컬럼 여덟 — `id`(uuid) · `user_id`(uuid) · `week_start`(date) · `timezone`(text) · `metrics`(jsonb) · `insights`(jsonb) · `computed_at`(timestamptz) · `created_at`(timestamptz).

다른 표 열여섯의 행 수가 전부 무변경임: `analysis_jobs` 57 · `daily_error_summary` 0 · `error_occurrences` 24 · `error_patterns` 9 · `learner_notes` 7 · `learning_scenarios` 30 · `learning_sessions` 17 · `llm_calls` 4 · `pattern_attempts` 19 · `pronunciation_attempts` 7 · `review_tasks` 15 · `session_plans` 6 · `shadowing_items` 1 · `users` 1 · `utterances` 128 · `weekly_reports` 0(신규).

⚠️ `migrate.py` 의 시딩이 `learning_scenarios`·`shadowing_items` 를 `on conflict do update` 로 덮을 수 있음(그 docstring 이 대가로 명시함). 이번 실행은 두 표의 행 수를 바꾸지 않았음 — 다만 행 수는 열 값의 덮어씀을 배제하지 못하므로 「행 수 무변경」까지만 단정함.

⑤ 어긋남 0건이라 캡틴 상신 조건이 발동하지 않았음.
<!-- SECTION:NOTES:END -->
