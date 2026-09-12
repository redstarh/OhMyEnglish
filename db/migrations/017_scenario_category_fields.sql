-- 017_scenario_category_fields.sql
-- `learning_scenarios.category` 의 값역에 분야 셋을 더한다 — `travel` · `shopping` · `health`.
-- 결정: docs/ops/captain-instruction-register.md 「결정 77」(2026-09-12 · 사용자가 후보 셋 중
--   「지금 계열을 늘림」을 골랐다. 기각한 둘은 ①분야 칸을 새로 둠 ②기존 둘 안에서 30개를 채움)
-- 소유 태스크: TASK-102 AC#3 (「분야별 학습 시나리오 30개 이상」)
--
-- 번호: dev DB `schema_migrations` 직접 조회가 `001 · 003~007 · 009~016` 이므로 017 임(`H-AL`).
-- ⛔ `008` 은 주간 리포트(`TASK-26`)용 예약 자리이므로 쓰지 않는다.
--
-- 왜 필요한가: 캡틴 요구의 예시 넷 가운데 둘이 기존 값역에 담기지 않았다 — *"여행중 사고를 당한
-- 상황"* · *"쇼핑중 물건을 교환하는 상황"*. 기존 값역은 `daily_life`·`business`·`shadowing` 셋뿐이라
-- 그 둘을 넣으면 CHECK 가 거부한다. ⇒ 30개를 채우기 전에 값역이 먼저 열려야 한다.
--
-- ⛔ **새 컬럼을 만들지 않는다**(결정 77). 축을 「무대 종류」와 「분야」로 가르면 새 컬럼·조회 경로
-- 수정이 따르고 단일 사용자 로컬 도구에 그 비용은 과하다. `category` 는 이미 무대 종류이고
-- 여행·쇼핑·진료도 무대 종류로 읽힌다.
-- ⚠️ **감수한 대가**: `category` 가 두 축을 계속 섞어 담는다 — `shadowing` 은 학습 **방식**이고
-- 나머지는 **무대**다. 「무대별 통계」와 「방식별 통계」를 따로 내야 할 때 이 결정이 되돌려진다.
--
-- ⛔ **값역을 늘리는 것이 「아무 값이나 받는 것」은 아니다.** CHECK 를 지우지 않고 목록만 늘린다 —
-- 오타(`cooking` 같은 값)는 여전히 거부되어야 하고 `test_scenario_category_domain_includes_the_new_fields`
-- 가 그것을 잰다.
--
-- 되돌리기: 이 파일의 CHECK 를 001 의 세 값으로 다시 좁힌다. ⚠️ 그때 새 분야 행이 남아 있으면
-- ALTER 가 실패하므로 **행을 먼저 지워야 한다** — 되돌리기가 데이터 삭제를 요구한다는 뜻이다.

alter table learning_scenarios
  drop constraint learning_scenarios_category_check;

alter table learning_scenarios
  add constraint learning_scenarios_category_check
  check (
    category in ('daily_life', 'business', 'shadowing', 'travel', 'shopping', 'health')
  );
