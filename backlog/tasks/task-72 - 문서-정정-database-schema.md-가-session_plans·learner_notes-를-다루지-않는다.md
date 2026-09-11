---
id: TASK-72
title: '문서 정정: database-schema.md 가 session_plans·learner_notes 를 다루지 않는다'
status: Done
assignee: []
created_date: '2026-09-09 14:23'
updated_date: '2026-09-11 15:49'
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
- [x] #1 session_plans·learner_notes 를 database-schema.md 에 추가한다 — 컬럼·제약과 도입 단계(007) 를 함께 적는다
- [x] #2 마이그레이션의 create table 목록과 문서의 절 목록을 기계로 대조해 공백 0건을 확인한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 완료 — 계획서 Task 12 Step 2 임. 표 «셋» 을 더했음(요구는 둘이었음).

AC#1 — session_plans · learner_notes 를 컬럼·제약·도입 단계(007)와 함께 넣었음. session_plans 에는 ⛔ 「session_id 는 이 계획을 «만든» 세션이고 «쓸» 세션이 아니다」를 명시했고, 읽는 쪽이 세션으로 찾지 않고 그 학습자의 최신 1행을 읽는다는 사실과 그 귀결(설계서 §3.4 — 그 앞 세션의 계획이 다시 읽힌다)을 함께 적었음. cardinality 함정(array_length('{}',1) 이 NULL 이라 빈 배열이 통과함 · 2026-09-04 실측)도 그 자리에 남겼음. learner_notes 에는 「덧붙이기만 한다 · 최신 행이 현행 노트」와 window 두 컬럼의 뜻을 적었음.

⛔ AC#2 의 기계 대조가 «새 공백 하나» 를 잡았음 — daily_error_summary(012)가 마이그레이션에 있는데 문서에 없었음. AC#2 가 「공백 0건」을 요구하므로 그 표도 함께 넣었음. 그 절에는 ⚠️ summary_date 가 date 인 것이 전역 시각 규약의 예외가 아니라는 것(달력 날짜이고 그 경계를 그은 타임존을 timezone 에 스냅샷으로 남김)을 적었음.

AC#2 결과 — 마이그레이션의 create table 14종 대 문서 절 목록: 공백 0건. 문서에만 있는 schema_migrations 한쪽 비대칭은 그 절이 이미 이유를 담고 있음(마이그레이션 러너가 만들고 SQL 파일이 아님). ⛔ 판별력을 시험했음 — 방금 넣은 절 이름을 목록에서 빼면 그 대조가 daily_error_summary 를 잡음. 대조 명령: grep -rhoE "create table [a-z_]+" db/migrations/*.sql 과 grep -oE '^### `[a-z_]+`' docs/database-schema.md 를 comm 으로 비교함.

⛔ 삽입 위치를 인용에서 계산했음. 리포 안에서 이 문서를 줄 번호로 인용하는 자리의 «최대값이 377» 이고 표 절이 422 에서 끝나므로 423 앞에 넣었음 — git diff --numstat 이 79 0(순삽입 · 삭제 0)이라 422 이하 줄은 한 글자도 바뀌지 않았음.

⚠️ 그 조사에서 선재 결함이 드러났음 — 인용 39자리 가운데 확인한 셋이 전부 다른 내용을 가리켰음(:120 → 실제 196~197 · :139-140 → 183~184 · :377 → 530). 내 편집과 무관하고 이전 삽입들(011 · 012 · 007)이 민 것임. TASK-113 으로 등록했음.

게이트: 문서만 고쳤음. 한국어 기계 검사 추가분 79행에 의존 명사 붙여쓰기 0건 · 반말 0건이고 「안 되는」은 부정이라 띄어 쓰는 쪽이 맞음.
<!-- SECTION:NOTES:END -->
