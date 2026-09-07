-- 009_drill_turns.sql
-- 드릴 exchange 관측 — 세션이 기대한 exchange 수를 남긴다
-- 설계: docs/design/2026-09-07-scenario-and-drill-turns-design.md §2.3 (정본)
-- 캡틴 결정: docs/design/2026-09-06-captain-decisions.md — 결정 10(기록하고 드러낸다) · 결정 16(이 컬럼)
-- 요구사항: 드릴마다 4턴 이상 (TASK-6)
--
-- 번호: 008은 **주간 리포트(TASK-26)에 예약**돼 있다(captain-decisions.md §3 유도 1) —
-- 그래서 이 파일이 009다(캡틴 결정 16).
--
-- ⛔ **정정(4판) — 이 파일의 이전 근거 서술이 인과를 뒤집어 적었다.** "예약 번호를 앞질러 쓰면
-- 순서가 갈라진다"고 적었으나 **사실은 반대다**: 갈라짐을 만드는 쪽이 009다. 직접 확인한 것 —
-- `schema_migrations`에 `…007, 009`가 있고 **008은 비어 있다**(psql 직접 조회) · `scripts/migrate.py:100`
-- 이 `sorted(glob("*.sql"))` 순으로 돌면서 `:102`가 **이미 적용된 파일을 건너뛴다.**
-- → 나중에 `008_*.sql`이 들어오면 **이 DB는 009 뒤에 008을 적용**하고 **새 DB는 008을 먼저** 적용한다.
--    적용 순서가 실제로 갈라진다.
-- **그래도 번호는 009로 둔다**: 결정 16이 정한 값이고, 이 파일은 **이미 적용됐다** — 지금 renumber하면
--    `schema_migrations`의 filename과 어긋나 새 파일로 오인돼 **두 번 적용된다**(같은 컬럼 add로 실패).
-- ⚠️ **008을 만드는 사람이 알아야 할 것**: 이 갈라짐이 무해한 이유는 **008과 009가 서로 독립**일
--    때뿐이다(009는 `learning_sessions`에 컬럼 1개 add). 008이 `learning_sessions`를 건드리거나
--    이 컬럼에 의존하면 **먼저 그 순서 문제를 해결**해야 한다.
--
-- **왜 컬럼인가 — `learning_sessions.summary` jsonb를 쓰지 않은 이유가 셋이다.**
-- ① `docs/database-schema.md`가 그 컬럼을 **`summarize_session`(세션 총평)의 것으로 이미
--    지정**했고 007이 `analysis_jobs.job_type` CHECK에 그 job을 열어 뒀다 — 「미사용 컬럼」이
--    아니라 **이름 붙은 다음 소비자가 있는** 컬럼이다(코드 grep이 0건이어도 그렇다).
-- ② 총평 구현자가 `set summary = $2`를 쓰는 것은 컬럼 이름과 문서를 따르는 **정상 행동**이고,
--    그때 지워지는 값은 설계가 스스로 「복원 불가」라고 적은 값이다. docstring은 그 함수를
--    읽을 이유가 없는 사람을 구속하지 못한다. **스키마는 구속한다.**
-- ③ CHECK 없는 jsonb는 모양을 강제하지 못한다.
--
-- 여기 **없는 것**: 실제 exchange 수. 그것은 저장하지 않고 조회 시점에 `utterances`에서
-- 「**코치 발화 바로 뒤에 온 사용자 발화**」로 센다(설계서 §2.3) — 두 곳에 세면 갈라지고,
-- 세션이 예외로 끝나도 도출값은 남는다.
-- ⛔ **정정(4판)**: 이 주석은 「사용자→코치 전이」라고 적혀 있었고 그것이 3판의 방향이다.
--    §2.2가 모델에게 준 문구는 exchange를 **코치→학습자**로 정의하므로 방향이 반대였고,
--    세션이 학습자 발화로 끝나면(정상 종료 모양) **완전 순응 세션도 1만큼 미달로 세어졌다.**

-- nullable이 계약이다: null = **계획 없이 시작한 세션 = 관측 대상 아님.**
-- ⛔ 0을 허용하지 않는다 — 0은 「기대가 0이었다」로 읽혀 **「기대가 없었다」와 구분되지 않고**,
--    그 구분이 결과 응답의 `drill` 키 유무를 정한다. 값역에서 막아 둔다.
-- 기존 행은 전부 null이 된다(기대값을 사후에 복원할 수 없다 — 계획 조회가 「사용자 최신 1건」이라
--    그 세션이 어느 계획을 썼는지 알 길이 없다). 그것이 정상이고 백필하지 않는다.
alter table learning_sessions
  add column drill_turns_expected integer;

alter table learning_sessions
  add constraint learning_sessions_drill_turns_expected_positive
  check (drill_turns_expected is null or drill_turns_expected > 0);
