---
id: TASK-72
title: '문서 정정: database-schema.md 가 session_plans·learner_notes 를 다루지 않는다'
status: To Do
assignee: []
created_date: '2026-09-09 14:23'
labels: []
dependencies: []
ordinal: 75000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-09 TASK-47 의 6항목 대조 중 기계 대조로 드러났음. 근거는 docs/design/2026-09-09-phase1-completion-audit.md §1 F4 임.

마이그레이션이 만든 표와 docs/database-schema.md 의 ### 절을 대조했음. 문서에 없는 표가 둘임 — session_plans · learner_notes, 둘 다 007_learning_coach_slice2.sql 임. 반대로 문서에만 있는 schema_migrations 는 마이그레이션 러너가 만드는 것이라 공백이 아님.

⛔ 이것을 Phase 1 미충족으로 세지 않았음 — AC F4 의 문면이 「재작성된 001 과」 일치를 요구하고 001 의 8표는 컬럼 단위로 전건 일치함(도입 단계 표기도 문서의 12표 전부에 있음). 007 은 슬라이스 2 라 Phase 1 완료 기준 밖임.

그래도 남기는 이유: F4 의 존재 이유가 「문서-SQL 불일치 재발 방지」(설계서 §6 산출물)임. 표 둘이 문서 밖에 있으면 그 목적이 부분적으로 깨짐.

⚠️ 대조를 기계로 다시 할 수 있음 — 마이그레이션의 create table 목록과 문서의 `### \`표이름\`` 목록을 맞추면 됨. 눈으로 훑지 않음.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 session_plans·learner_notes 를 database-schema.md 에 추가한다 — 컬럼·제약과 도입 단계(007) 를 함께 적는다
- [ ] #2 마이그레이션의 create table 목록과 문서의 절 목록을 기계로 대조해 공백 0건을 확인한다
<!-- AC:END -->
