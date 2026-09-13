-- 023_weekly_reports.sql
-- 주간 학습 리포트 — 표 하나 + job 종류 하나 + 토큰 기록 값역
-- 설계: docs/design/2026-09-14-weekly-report-design.md §3·§6
-- 계획: docs/design/2026-09-14-weekly-report-plan.md Task 1
-- 캡틴 결정: 4(주 시작은 월요일 · 표로 적재한다 — docs/design/2026-09-06-captain-decisions.md §1) ·
--            58(같은 경계를 대장에 등재) · 91(트리거는 세션 종료 · 범위는 셋 다 + 화면까지) ·
--            27(008 은 영구 결번이므로 쓰지 않는다)
-- 소유 태스크: TASK-26 · TASK-26.1
--
-- 번호: `ls db/migrations/` 실측 최대가 022 이므로 023 이다(2026-09-14 에 쓰는 턴에 조회했다).
-- ⛔ `002`·`008` 은 영구 결번이다 — 018 머리말의 「008 은 주간 리포트용 예약 자리」는 낡았고
--    `TASK-136` 이 그 문장을 고친다.
-- ⛔ 소비자와 같은 커밋 흐름으로 나간다 — 011 이 세운 data-first 규약이다.

create table weekly_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (id) on delete cascade,
  -- 그 주의 **월요일**. 계산은 `date_trunc('week', now() at time zone u.timezone)` 이고 Postgres 가
  -- 월요일을 주 시작으로 쓴다(ISO 8601) — 아래 CHECK 가 그 경계를 값역으로 못박는다.
  -- ⛔ `current_date` 로 구하지 않는다: UTC 자정~09:00(KST) 구간에 그 값이 KST 날짜보다 하루 이르다
  --    (이 리포의 실측 · R13-3 이 같은 것을 요구한다).
  week_start date not null,
  -- ⛔ **그 주 경계를 그은 타임존을 스냅샷으로 함께 남긴다** — `daily_error_summary.timezone` 이
  -- 같은 이유로 그렇게 했다: `users.timezone` 이 나중에 바뀌면 **과거 리포트가 어느 경계로
  -- 그어졌는지 복원할 수 없다.** `week_start` 는 절대 시각이 아니라 **달력 날짜**이므로 전역
  -- 시각 규약의 「이벤트 시각은 timestamptz」에 걸리지 않는다(그 규칙은 절대 시각의 것이다).
  -- ⚠️ `users.timezone` 에는 CHECK 가 없어(001) 무효값이 실재할 수 있고 그 거부는 앱이 한다 —
  -- 이 표는 공백만인 값을 막는다.
  timezone text not null check (length(btrim(timezone)) > 0),
  -- **사실**: 상위 오류 · 발생 수 · 패턴 종 수 · 세션 수. R11-8 의 *"조회는 사실을 제공한다"*.
  metrics jsonb not null default '{}',
  -- **모델 판단**: 개선 패턴 · 다음 주 추천 시나리오. R11-8 의 *"판단은 학습 분석 Agent 가 한다"*.
  -- ⛔ 점수·등급을 담지 않는다 — 프롬프트가 요구하지 않고 출력 규격에 그 키가 없다(R13-5 의 톤
  --    계약 · PRD §15.3 의 비범위). `TASK-62` 가 총평에서 같은 경계를 값역으로 막았다.
  -- ⚠️ 「다음 주 추천」을 별 컬럼으로 두지 않은 이유: 같은 모델 호출의 산출물이라 두 컬럼으로
  --    나누면 원자성이 두 자리로 번진다(설계서 §3).
  insights jsonb not null default '{}',
  -- null = 아직 계산하지 않았다. `daily_error_summary.computed_at` 과 같은 규약이고
  -- 「분석이 돌고 담을 것이 0이었다」와 「아직 안 돌았다」를 구별한다(R13-7 과 같은 축).
  computed_at timestamptz,
  created_at timestamptz not null default now(),
  -- 재계산이 행을 늘리지 않게 한다 — 멱등의 뿌리이고 저장이 이 키로 `on conflict` 한다.
  constraint weekly_reports_user_week_key unique (user_id, week_start),
  -- ⛔ 일요일 시작으로 계산한 코드가 조용히 섞이는 것을 막는다.
  constraint weekly_reports_week_starts_on_monday check (extract(isodow from week_start) = 1)
);

-- 뜨거운 조회는 「그 사용자의 최근 주」 하나다(화면이 최신 주를 연다).
create index weekly_reports_user_week_idx on weekly_reports (user_id, week_start desc);

-- job 종류를 늘린다. ⛔ **값역만 늘리면 job 을 넣을 수 없다** — 아래 상호배타 CHECK 가 종류별 대상
-- 컬럼을 가두므로 분기를 함께 더해야 한다(018 주석이 그 함정을 이미 적었다).
alter table analysis_jobs drop constraint analysis_jobs_job_type_check;

alter table analysis_jobs
  add constraint analysis_jobs_job_type_check
  check (job_type in ('analyze_utterance', 'summarize_session', 'plan_next_session',
                      'generate_scenario', 'summarize_week'));

alter table analysis_jobs drop constraint analysis_jobs_target_matches_job_type;

alter table analysis_jobs
  add constraint analysis_jobs_target_matches_job_type
  check ((job_type = 'analyze_utterance' and utterance_id is not null and session_id is null)
      or (job_type = 'summarize_session' and session_id is not null and utterance_id is null)
      or (job_type = 'plan_next_session' and session_id is not null and utterance_id is null)
      or (job_type = 'generate_scenario' and session_id is not null and utterance_id is null)
      -- ⚠️ 대상이 **세션**인 이유: 그 세션의 종료가 트리거다(결정 91). 「어떤 주」는 job 이 들고
      -- 다니지 않고 워커가 세션 시각과 `users.timezone` 으로 다시 구한다 — 공용 큐 표에 종류별
      -- 컬럼을 더하지 않는 것이 그 선택의 값어치다(설계서 §6).
      or (job_type = 'summarize_week' and session_id is not null and utterance_id is null));

-- 토큰 기록의 값역. ⚠️ **`TASK-134` 가 이 자리에서 조용한 소실을 잡았다** — 021 전까지 값역이 넷뿐이라
-- `generate_scenario` 의 기록이 사라지고 있었고 `usage.py` 가 `PostgresError` 를 삼켜 아무도 몰랐다.
-- ⛔ 그래서 새 job 을 낼 때 이 값역을 **같은 마이그레이션에서** 늘린다.
alter table llm_calls drop constraint llm_calls_purpose_check;

alter table llm_calls
  add constraint llm_calls_purpose_check
  check (purpose in ('plan', 'analysis', 'spike', 'nova', 'generate_scenario',
                     'summarize_session', 'summarize_week'));

-- ⛔⛔ **적용 절차 — 011 이 세운 5단계를 그대로 쓴다**
--   ① `pg_dump -n public -T 'harness_*'` 로 백업한다. ⚠️ `-T` 를 빼면 `harness_pattern_baseline`
--      (소유자 `redstar`)에서 권한 거부가 나 백업 전체가 막힌다(`H-BT` · 2026-09-14 실측).
--   ② 표별 행 수를 기록한다. ③ 적용한다(⚠️ `migrate.py` 는 조용한 성공이므로 `schema_migrations`
--      를 조회해 확인한다). ④ 재조회로 대조하고 출력을 태스크 노트에 남긴다.
--   ⑤ 어긋나면 **멈추고 사용자에게 올린다.**
-- 되돌리기: `drop table weekly_reports` + 위 세 값역을 이전 판으로. ⚠️ **값역 축소이므로
-- `summarize_week` 행이 하나라도 있으면 실패한다**(011 이 겪은 형태) — 그 행을 어떻게 할지는 데이터
-- 판단이므로 스크립트가 조용히 정하지 않는다.
