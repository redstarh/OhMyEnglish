-- 016_session_scenario_pick.sql
-- `learning_sessions` 에 「이 세션의 상황을 신규로 골랐는지 반복으로 골랐는지」를 더한다.
-- 결정: docs/ops/captain-instruction-register.md 「결정 73」(배치 단위는 대화 상황) ·
--   「결정 74」(신규는 최근 10회 안에 안 나온 상황)
-- 소유 태스크: TASK-4 · 설계서: docs/design/2026-09-12-scenario-rotation-70-30-design.md §5
--
-- 번호: dev DB `schema_migrations` 직접 조회가 `001 · 003~007 · 009~015` 이므로 016 임(`H-AL`).
-- ⛔ `008` 은 주간 리포트(`TASK-26`)용 예약 자리이므로 쓰지 않는다.
--
-- 왜 필요한가: 이 칸이 없으면 「신규를 몇 번 골랐는가」를 셀 수 없고, 그러면 `TASK-4` AC#4 가
-- 요구한 「문구 단정이 아니라 계산 검증」을 할 수단이 없다. 이력에서 매번 재계산하는 대안은
-- 재귀가 되고 창 크기를 바꾸면 과거 판정이 소급해 흔들린다(설계서 §7 대안 2).
--
-- ⚠️ **nullable 이고 소급해 채우지 않는다.** 016 이전 세션의 신규 여부는 그 시점의 창에 달렸고,
-- 지금 창으로 다시 접으면 **실제로 일어난 것과 다른 값**이 된다. 앱은 `null` 을 「신규였다」로
-- 세지 않는다(`services/scenario_rotation.pick_scenario` 가 그것을 명시한다).
-- ⇒ 도입 직후에는 신규가 먼저 3회 연달아 나온다. 그것은 창이 채워지는 과정이고 결함이 아니다.
--
-- ⛔ 값역을 앱과 두 곳에 두지 않는다 — 이 CHECK 가 정본이고 앱은 상수 두 개(`NEW`·`REPEAT`)만
-- 갖는다. 되돌리기는 이 열을 drop 하는 것이고, 값이 있으면 그 값은 사라진다.

alter table learning_sessions
  add column scenario_pick text
  check (scenario_pick in ('new', 'repeat'));
