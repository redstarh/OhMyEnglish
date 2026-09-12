---
id: TASK-130
title: '설계 결함: 대화 상황의 노출 순서가 created_at 에 얹혀 있다 — seed() 를 트랜잭션으로 감싸면 조용히 무너진다'
status: In Progress
assignee: []
created_date: '2026-09-12 12:18'
updated_date: '2026-09-12 14:12'
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
- [x] #2 고르는 규칙(scenario_rotation._staleness)이 created_at 을 읽는 자리와 Candidate.created_at 필드가 함께 바뀌는지 확인한다 — 「수준 일치 0행이면 가장 이른 행」 기존 계약이 그 필드에 걸려 있다
- [x] #3 DB 의 실제 created_at 이 배열 순서와 같은지 재는 단정을 만든다 — 지금 test_seed_interleaves_business_stages_early 는 상수만 보고 DB 를 보지 않는다
- [x] #4 seed() 를 트랜잭션으로 감쌌을 때 순서가 무너지는 것을 재현해 그 위험이 실재함을 실측으로 남긴다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
⛔ 이 결함의 «두 번째 얼굴» 을 2026-09-12 에 실측했다 (세션 ohmyenglish-f4 · TASK-102 AC#3 작업 중).

시드 배열을 15 → 30행으로 늘리고 upsert 로 dev DB 에 넣었더니 새 15행의 created_at 이 「지금」이라 전부 배열 뒤로 밀렸고, 여행·쇼핑·진료 계열이 40회 세션에서 0회였다. ⇒ 시드 배열을 고쳐도 이미 시드된 DB 에는 순서가 반영되지 않는다. 참조 0인 행을 지우고 다시 넣어야 했다.

즉 이 결함은 두 갈래로 나타난다: ⑴ seed() 를 트랜잭션으로 감싸면 순서가 뭉개진다 ⑵ 이미 시드된 DB 에서 배열을 고쳐도 순서가 갱신되지 않는다. AC#1 의 판단은 그 둘을 함께 봐야 한다 — 명시적 순서 컬럼은 ⑵ 도 함께 닫는다(upsert 의 set 목록에 그 컬럼을 넣으면 되므로).

⚠️ 이 리포에 이미 있는 선례: services/pronunciation.py 가 같은 함정을 문장으로 갖고 정렬을 attempt_seq(명시적 순서 열)로 강제하며 resolved_at 에 clock_timestamp() 를 쓴다(동료 세션 ohmyenglish-19 가 대조해 확인). review.py 도 clock_timestamp() 를 쓴다. ⇒ 「명시 컬럼으로 옮기는 안」의 비용이 그 선례만큼 낮다.

회차 정본: tests/harness/runs/2026-09-12-task4-rotation-app-path.md §3-2.

---

진행 2026-09-12 (세션 ohmyenglish-f4). AC#2·#3·#4 를 닫았음. 회차 정본은 tests/harness/runs/2026-09-12-task4-rotation-app-path.md §3-3 임.

AC#3 — 단정 둘을 tests/unit/test_schema.py 에 세웠음. ⑤-6 test_seeded_created_at_carries_the_array_order(db_pool · 감싸는 트랜잭션 없음)가 DB 의 created_at 순서를 배열 순서와 대조하고 값이 서로 다른지도 잼. ⑤-7 test_wrapping_seed_in_one_transaction_collapses_the_order(db_conn · 트랜잭션 하나)가 30행의 created_at 이 1종으로 뭉개지는 것을 잼. ⛔ 판별력을 무력화로 확인했음 — ⑤-6 의 seed 호출을 conn.transaction() 으로 감싸는 변이를 넣으니 index 3 에서 red 였음(배열은 4번째에 업무 …110, 무너진 순서는 일상 …104). 변이는 되돌렸음.

AC#4 — 위험이 실재함을 계산으로 남겼음. WINDOW=10 안의 계열 구성이 「일상 5 · 업무 3 · 여행 1 · 쇼핑 1」에서 「일상 9 · 업무 1」로 바뀌고, 첫 등장 자리가 업무 4→10 · 여행 5→16 · 쇼핑 8→22 · 진료 14→25 로 밀림. ⇒ §1 의 결함(업무 0회)을 그대로 되살림. 기전은 시드 UUID 가 …101~…109 로 일상에 연속 배정돼 있어 뒷키가 id 로 넘어가면 창이 일상으로 채워지는 것임.

AC#2 — created_at 을 순서 신호로 읽는 자리가 앱 3 · 계약 문서 1 · 테스트 5 이고 전부 함께 바뀜.
- sessions.py 의 _SCENARIO_CANDIDATES_SQL(select s.created_at)과 row → Candidate 매핑(sessions.py:412)
- scenario_rotation.Candidate.created_at 필드와 _staleness 의 자리 ⑶ (last_used_at is None 인 후보에만 걸림)
- scenario_progress.py 의 group by / order by s.created_at, s.id (학습 현황 보고의 정렬)
- tests/harness/scenarios-E-agent-learning.md:169 가 계약을 SQL 문면 그대로 못박음: (select id from learning_scenarios order by created_at, id limit 1)
- 테스트: test_session_creation_falls_back_to_the_earliest_scenario(test_sessions.py:399) · test_earliest_row_contract_survives_the_new_front_slot(test_scenario_rotation.py:80) · test_seed_interleaves_business_stages_early · 새 ⑤-6 · ⑤-7
⇒ 명시 컬럼으로 옮기면 「가장 이른 행」 계약의 문면 자체가 「display_order 가 가장 작은 행」으로 바뀜. 그 문장이 문서·테스트·docstring 셋에 흩어져 있으므로 함께 고쳐야 함.

⚠️ migrate.py 주석 한 줄이 부정확함 — 「순서가 id(랜덤 UUID)로 정해져」라고 적혀 있으나 시드 행의 id 는 고정 상수임. 랜덤인 것은 TASK-5 가 만들 generated 행임. 무너진 순서는 무작위가 아니라 「일상이 앞으로 몰리는 특정 순서」이고 그 차이가 AC#1 판단에 걸림. 문면 정정은 AC#1 결정과 함께 함.

게이트(이 턴 직접 실행 · cwd app/backend): pytest 1 failed · 1077 passed — 유일한 실패는 발음 축 TASK-128.3 이 소유한 바이트 게이트임(내 변경과 무관). ruff check 안 0 · 밖 0 · format 0 · ty 0.
<!-- SECTION:NOTES:END -->
