---
id: TASK-130.1
title: '구현: 노출 순서를 display_order 로 옮긴다 (결정 81)'
status: In Progress
assignee: []
created_date: '2026-09-12 14:26'
updated_date: '2026-09-12 14:46'
labels: []
dependencies: []
parent_task_id: TASK-130
ordinal: 143000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
결정 81 을 실행한다. TASK-130 이 결정을 받는 태스크이고 이 태스크가 그 실행체다. 회차 정본은 tests/harness/runs/2026-09-12-task4-rotation-app-path.md §3-3 이고 결정 원문은 docs/ops/captain-instruction-register.md 결정 81 이다. ⛔ 마이그레이션 번호는 적용 직전 schema_migrations 조회로 발급한다(H-AL) — 이 태스크를 만든 시점의 최대는 018 이다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 정수 컬럼 display_order 를 더하고 시드가 배열 인덱스를 쓴다 — upsert 의 set 목록에 그 컬럼을 넣어 «이미 시드된 DB 에서도 배열 수정이 반영되는 것»을 실측으로 확인한다 (그것이 결정 81 이 기각한 안과 갈리는 지점이다)
- [x] #2 고르는 규칙을 함께 옮긴다 넷: sessions.py 의 _SCENARIO_CANDIDATES_SQL · row→Candidate 매핑 · scenario_rotation.Candidate 필드와 _staleness 의 자리 ⑶ · scenario_progress 의 group by/order by
- [x] #3 「수준 일치 0행이면 가장 이른 행」 계약의 문면을 고친다 — tests/harness/scenarios-E-agent-learning.md:169 의 SQL · test_session_creation_falls_back_to_the_earliest_scenario · test_earliest_row_contract_survives_the_new_front_slot · Candidate docstring
- [x] #4 재는 축을 뒤집는다 — ⑤-6 을 display_order 축으로 다시 세우고 ⑤-7 은 «트랜잭션으로 감싸도 순서가 유지된다»를 재는 단정으로 바꾼다. ⛔ 무력화해서 red 를 본 뒤 초록을 믿는다
- [x] #5 migrate.py 주석의 부정확을 고친다 — 「순서가 id(랜덤 UUID)로 정해져」는 시드 행에 대해 거짓이다(고정 상수다). 무너진 순서가 «일상이 앞으로 몰리는 특정 순서»라는 것으로 고친다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
진행 2026-09-12 (세션 ohmyenglish-f4). AC 5건 전부 닫았음. 회차 정본은 tests/harness/runs/2026-09-12-task4-rotation-app-path.md §3-4 임.

넣은 것: 019_scenario_display_order.sql (display_order int not null default 0) · seed() 가 배열 자리를 1부터 매기고 upsert 의 set 목록에 넣음 · 읽는 자리 넷을 옮김(_SCENARIO_CANDIDATES_SQL 의 select · row→Candidate 매핑 · Candidate 필드와 _staleness 의 자리 ⑶ · scenario_progress 의 group by/order by).

AC#1 두 번째 얼굴을 dev DB 에서 실측했음: 019 적용 뒤 display_order 상위 8 이 배열과 같음(1 0101 · 2 0102 · 3 0103 · 4 0110 · 5 0116 · 6 0104 · 7 0111 · 8 0122) → …0110 을 99 로 일부러 깨뜨림 → migrate.py 재실행 → 4 로 복원됨. 전수는 count 30 · min 1 · max 30 · distinct 30 임.
⚠️ 이 DB 에서는 created_at 순서도 지금 배열과 같음(§3-2 가 참조 0 행을 지우고 다시 넣었음) ⇒ dev DB 만 보고는 두 축을 가를 수 없음. 가르는 것은 위 복원 관측과 두 축을 어긋나게 심는 테스트 셋임.

AC#4 재는 축을 뒤집었음. ⑤-6 은 display_order 축으로 다시 세웠고 ⑤-7 은 「감싸도 유지된다」로 뜻을 뒤집었음 — ⛔ 조건 성립(같은 트랜잭션에서 created_at 이 1종)을 함께 단정해야 「now() 가 안 고정된 판」에서 거짓 초록이 나지 않음. 새 테스트 셋: test_display_order_decides_not_created_at · test_created_at_still_orders_user_made_stages · test_session_creation_honours_display_order_over_created_at · test_rows_follow_the_display_order.

판별력 셋을 무력화로 확인했음: _staleness 자리 ⑶ 을 상수 0 으로 → 새 테스트 1건만 red 이고 나머지 16건 초록(그 축이 이전에 무보호였다는 뜻) · sessions.py 의 display_order 를 0 으로 → 앱 경로 테스트 red · ⑤-6 은 §3-3 에서 이미 red 확인.
⛔ 그 과정에서 한 번 잘못 읽었음 — 두 번째 무력화를 -k "scenario" 로 돌려 9 passed 를 보고 「판별력 없음」으로 판정할 뻔했음. 새 테스트 이름에 scenario 가 없어 선택에서 빠진 것이었고 이름으로 다시 지목하니 red 였음. 필터가 무엇을 배제하는지 먼저 확인함.
⚠️ 019 를 넣고 앱 넷을 옮긴 직후 pytest 가 1080 passed · 0 failed 였는데 그때 기존 단정들은 여전히 옛 축을 재고 있었음 — 전건 초록이 이행을 뜻하지 않은 자리임.

AC#3 계약 문면: tests/harness/scenarios-E-agent-learning.md:169 는 과거 감사 기록이라 문면을 고치지 않고 「이후 두 번 바뀌었음」 주석을 날짜와 함께 덧붙였음(고치면 그 회차의 증거가 훼손됨). 살아 있는 계약 문면은 Candidate docstring · _staleness docstring · 테스트 둘의 단정 문구에서 고쳤음.

AC#5 migrate.py 주석 정정: 「순서가 id(랜덤 UUID)로 정해져」를 「시드 id 는 고정 상수이고 일상 9종에 연속 배정돼 창이 일상으로 채워지는 특정 순서가 된다」로 고쳤음. 랜덤인 것은 사용자 생성 행임.

게이트(이 턴 직접 실행 · cwd app/backend): pytest 1081 passed · 0 failed · ruff check 안 0 · 밖 0 · ruff format 0(204 files) · ty 0.
<!-- SECTION:NOTES:END -->
