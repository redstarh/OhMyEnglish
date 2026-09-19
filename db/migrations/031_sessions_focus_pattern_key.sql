-- 031_sessions_focus_pattern_key.sql
-- 학습자가 «고른» 오류 패턴으로 연 세션이 그 사실을 남긴다 — 즉시 드릴 진입의 출처
-- 요구 정본: docs/PRD.md:70 · docs/requirements-summary.md:53-54
--   (「사용자는 자주 틀리는 패턴을 직접 보고, 해당 패턴으로 즉시 학습을 만들 수 있음」)
-- 소유 태스크: TASK-241 · 결함 TASK-233 (통합테스트 회차 TASK-229 가 TS-36 AC#3 에서 찾았다)
--
-- 번호: `ls db/migrations/` 실측 최대가 030 이고 `schema_migrations` 의 마지막 적용도
--       030_analysis_jobs_indexes.sql 이다(이 파일을 쓰는 턴에 직접 조회했다).
-- ⛔ 번호를 미리 예약하지 않는다(결정 27).
--
-- 되돌리기:
--   alter table learning_sessions drop column focus_pattern_key;
-- ⚠️ 되돌리면 「어느 패턴에서 시작한 드릴인가」가 사라진다. 그 값은 학습자의 선택이라
--    재구성할 수 없다 — 되돌리기 전에 집계에 쓰이고 있는지 확인한다.

-- 왜 컬럼 하나인가:
-- ⛔ **`summary` jsonb 에 얹지 않는다.** 그 칸은 세션 종료가 총평으로 덮으므로 진입 시점에 적은
--    값이 사라진다. 진입 기록과 종료 기록은 수명이 다르다.
-- ⛔ **새 표를 만들지 않는다.** 값이 세션 한 행에 1:1 이고 수명도 그 행과 같다
--    (`started_via`·`learning_source`·`scenario_pick` 이 이미 같은 모양이다 — 그 관용을 따른다).
-- ⛔ **FK 를 걸지 않는다.** `error_patterns` 는 재분석으로 행이 바뀌는 표이고(§5.2 replace),
--    패턴 행이 사라져도 「그때 이 패턴으로 연습했다」는 사실은 남아야 한다. FK 를 걸면 그 기록이
--    cascade 로 지워지거나 삭제를 막는다. 그래서 담는 것은 **id 가 아니라 `pattern_key` 문자열**이다.

-- 왜 nullable 인가:
-- 대부분의 세션은 패턴을 고르지 않고 열린다(오늘 학습·쉐도잉·발음 전용 전부). 즉 빈 값이 정상
-- 상태이고 not null 로 만들면 그 상태를 표현할 자리가 없어진다.
-- ⛔ 기본값을 두지 않는다 — 「고르지 않았다」와 「무엇을 골랐다」는 값역이 겹치지 않아야 한다.
alter table learning_sessions
  add column focus_pattern_key text;

-- 빈 문자열을 막는다. 값이 있으면 그것은 실제 패턴 키여야 하고, 빈 문자열은 「고르지 않았다」를
-- null 과 두 가지 방식으로 표현하게 만들어 집계가 갈린다.
-- ⚠️ 새 CHECK 를 **더하는** 것이고 기존 CHECK 를 DROP 하지 않는다.
alter table learning_sessions
  add constraint learning_sessions_focus_pattern_key_not_blank
  check (focus_pattern_key is null or length(btrim(focus_pattern_key)) > 0);
