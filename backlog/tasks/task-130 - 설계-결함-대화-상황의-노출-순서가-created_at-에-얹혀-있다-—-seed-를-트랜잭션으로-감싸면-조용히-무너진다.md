---
id: TASK-130
title: '설계 결함: 대화 상황의 노출 순서가 created_at 에 얹혀 있다 — seed() 를 트랜잭션으로 감싸면 조용히 무너진다'
status: To Do
assignee: []
created_date: '2026-09-12 12:18'
labels: []
dependencies: []
ordinal: 138000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 76 이 「시드 배열 순서가 노출 순서다」로 정했고 그 순서를 learning_scenarios.created_at 이 담고 있다. 그런데 그 컬럼의 기본값은 now() 이고 PostgreSQL 의 now() 는 트랜잭션 시작 시각에 고정된다 ⇒ seed() 를 한 트랜잭션으로 감싸면 15행의 created_at 이 전부 같아지고 순서가 id(랜덤 UUID)로 정해진다. 지금 scripts/migrate.py 의 main() 은 감싸지 않으므로 동작하지만 그것은 우연한 의존이다.

2026-09-12 에 tests/unit/test_scenario_progress.py 의 순서 테스트가 db_conn(한 트랜잭션)에서 그 현상으로 불안정했고, 그것이 이 결함을 드러냈다. 테스트는 created_at 을 명시로 심어 안정화했으나 제품의 취약점은 남아 있다.

⛔ 게이트가 초록인 채로 무너지는 부류다 — 순서를 재는 단정이 시드 상수(배열)만 보고 DB 의 실제 created_at 을 보지 않는다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 created_at 에 순서를 얹는 것을 그만두고 명시적 순서 컬럼(예: display_order)을 둘지, 지금 구조를 유지하고 「트랜잭션으로 감싸지 마라」를 테스트로 못박을지 사용자 결정을 받는다
- [ ] #2 고르는 규칙(scenario_rotation._staleness)이 created_at 을 읽는 자리와 Candidate.created_at 필드가 함께 바뀌는지 확인한다 — 「수준 일치 0행이면 가장 이른 행」 기존 계약이 그 필드에 걸려 있다
- [ ] #3 DB 의 실제 created_at 이 배열 순서와 같은지 재는 단정을 만든다 — 지금 test_seed_interleaves_business_stages_early 는 상수만 보고 DB 를 보지 않는다
- [ ] #4 seed() 를 트랜잭션으로 감쌌을 때 순서가 무너지는 것을 재현해 그 위험이 실재함을 실측으로 남긴다
<!-- AC:END -->
