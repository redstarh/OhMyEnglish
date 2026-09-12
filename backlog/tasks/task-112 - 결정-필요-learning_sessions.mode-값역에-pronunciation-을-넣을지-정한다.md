---
id: TASK-112
title: '결정 필요: learning_sessions.mode 값역에 pronunciation 을 넣을지 정한다'
status: Done
assignee: []
created_date: '2026-09-11 15:43'
updated_date: '2026-09-12 00:42'
labels: []
dependencies: []
ordinal: 117000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
2026-09-12 KST — TASK-10.1 이 발음 전용 모드를 «지시문만» 바꾸는 방식으로 넣었고 세션 행의 mode 는 speaking 으로 남음. 001 의 learning_sessions_mode_check 값역에 그 값이 없기 때문임. ⚠️ 대가: 결과 화면·집계·일일 완료 판정이 이 세션을 말하기 세션으로 셈. ⛔ 모드 리터럴의 소유자는 결정 11 이 TASK-27 로 지목했으므로 이 태스크는 그 결정을 대신하지 않고 «질문을 원장에 세워 두는» 것임. 근거: docs/design/2026-09-12-pronunciation-mode-design.md §5 항목 1.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 값역을 늘릴지 정하고 근거를 적는다 — 늘리면 마이그레이션 번호를 착수 턴에 발급한다(결정 27)
- [x] #2 늘리지 않기로 하면 집계가 이 세션을 어떻게 세는지 문서에 명시한다 — 지금은 조용히 말하기로 섞임
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
2026-09-12 세션 ohmyenglish-f4 — 사용자 결정 67(값역을 늘림)로 닫았음. 결정 정본은 docs/ops/captain-instruction-register.md 「결정 67」임.

AC#1: 마이그레이션 014_pronunciation_session_mode.sql 을 착수 턴에 발급했음(그 순간 schema_migrations 최대가 012 였고 013 은 같은 턴의 TASK-60 것임 · H-AL 대로 직접 조회로 확인). 공유 dev DB 에 적용하고 CHECK 를 직접 조회해 speaking·shadowing·review·pronunciation 넷을 확인했음. ⛔ migrate.py 를 돌리지 않고 psql 로 파일 둘만 적용했음 — 그 스크립트는 시드 upsert 로 learning_scenarios·shadowing_items 의 가변 컬럼을 상수로 덮으므로 공유 DB 에 부수효과가 있음. schema_migrations 행은 같은 트랜잭션에서 직접 넣었음.

AC#2: 「늘리지 않기로 하면」 분기는 발동하지 않았으나 그 취지(집계 해석을 문서에 명시)를 그대로 이행했음 — docs/design/2026-09-12-pronunciation-mode-design.md §5 항목 1 을 갱신해 이전·이후 집계 대조표와 되돌리기 제약을 적었음.

구현: services/sessions.set_session_mode + api/ws.py 가 «오늘의 소리가 정해진 뒤에» 부름. ⛔ 요청만 보고 적지 않음 — 폴백 세션을 발음으로 세는 반대 방향 변종을 만듦. 통합 테스트 2건(양성·음성)이고 뮤테이션(요청만 보고 적기)이 음성 케이스로 잡혔음.

낡은 서술 셋을 함께 고쳤음 — api/ws.py 모듈 docstring · PRONUNCIATION_MODE 상수 주석 · services/sessions.create_session docstring. 그 셋이 전부 「세션 행의 mode 는 바뀌지 않는다」를 말하고 있었음.

게이트: pytest 973 passed(11.46s) · ruff check 0 · 게이트 밖 ruff 0 · ty 0. ⚠️ 게이트 밖 format --check 에 1 file 이 걸리는데 내 파일이 아님(동료 세션의 tests/integration/test_pronunciation_service.py).
<!-- SECTION:NOTES:END -->
