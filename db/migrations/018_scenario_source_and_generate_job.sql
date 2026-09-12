-- 018_scenario_source_and_generate_job.sql
-- 넷을 한 번에 고친다 — 시나리오 출처 · 생성 job 종류 · 그 job 의 대상 · 진입 모드.
-- 결정: docs/ops/captain-instruction-register.md 「결정 79」(5회 질문은 음성 대화로 하고 생성은
--   세션 뒤 job 이 전사문을 읽어 함) · 「결정 80」(사용자가 만든 상황은 신규 후보 맨 앞)
-- 소유 태스크: TASK-5 · 설계서: docs/design/2026-09-12-scenario-generator-design.md §4
--
-- 번호: dev DB `schema_migrations` 직접 조회가 `001 · 003~007 · 009~017` 이므로 018 임(`H-AL`).
-- ⛔ `008` 은 주간 리포트(`TASK-26`)용 예약 자리이므로 쓰지 않는다.
--
-- ⑴ `learning_scenarios.source` — 시드 행과 사용자가 대화로 만든 행을 가른다.
-- ⛔ **`default 'seed'` 를 두는 이유**: 기존 30행이 전부 시드이므로 **소급 UPDATE 없이 참이 된다.**
-- 값을 고쳐 표시를 맞추는 부류를 이 리포가 금지한다.
-- ⛔ **`user_id` 를 두지 않는다** — 단일 사용자 로컬 도구이고(`api/ws.py` 의 `FIXED_USER_ID`)
-- 지금 두면 항상 같은 값이 들어가는 컬럼이 된다. 다중 사용자가 생기는 턴에 더한다.
--
-- ⑵⑶ `analysis_jobs` — `generate_scenario` 는 **세션 단위** job 이다(전사문 전체를 읽는다).
-- ⛔ **`job_type` 값역만 늘리면 job 을 넣을 수 없다** — `analysis_jobs_target_matches_job_type` 이
-- 종류별 대상 컬럼을 상호배타로 가두므로 분기를 함께 더해야 한다. 007 의 주석이
-- *"값만 늘리면 안 된다"* 로 그 함정을 이미 적었고 이 파일이 그것을 따른다.
--
-- ⑷ `learning_sessions.mode` 에 `scenario_intake` — 진입을 가릴 표지다.
-- ⛔ **`learning_source='additional'` 로는 이 진입을 가릴 수 없다** (2026-09-12 실측 · `nova.py`
-- 소유 갈래가 코드로 반증했다): `app/frontend/app/page.tsx` 의 추가 학습 메뉴 여섯 가운데 **다섯이
-- `additional`** 이고 그중 **셋(자유 대화 · 약점 패턴 집중 · 질문 답변 5개)이 `mode` 를 갖지 않아
-- 서로 구별되지 않는다.** ⇒ 그 값을 조건으로 쓰면 자유 대화 세션에 질문 지시가 샌다.
-- ⚠️ 014 가 `pronunciation` 을 더한 것과 같은 형태이고 결정 67 의 「세션 행이 자기 진입을 적는다」
-- 와 일관된다.
--
-- ⛔⛔ **`drop`+`add` 는 값역을 «대체»한다 — 기존 값을 빠뜨리면 조용히 사라진다.** 아래 목록은
-- 2026-09-12 에 `pg_get_constraintdef` 로 직접 읽은 것이다: `speaking`·`shadowing`·**`review`**·
-- `pronunciation`. ⚠️ 이 파일의 초안이 `review` 를 빠뜨렸고 그 조회가 잡았다 — 그 값을 쓰는 행이
-- 지금 없어 게이트도 침묵할 자리였다. `test_session_mode_domain_includes_scenario_intake` 가
-- 이제 다섯 값을 모두 잰다.
--
-- 되돌리기: `source` 열 drop + 세 CHECK 를 017 상태로 되돌린다. ⚠️ `generated` 행 ·
-- `generate_scenario` job · `scenario_intake` 세션이 남아 있으면 CHECK 복원이 실패하므로 그 행을
-- 먼저 지워야 한다 — 되돌리기가 데이터 삭제를 요구한다.

alter table learning_scenarios
  add column source text not null default 'seed'
  check (source in ('seed', 'generated'));

alter table analysis_jobs
  drop constraint analysis_jobs_job_type_check;

alter table analysis_jobs
  add constraint analysis_jobs_job_type_check
  check (
    job_type in (
      'analyze_utterance',
      'summarize_session',
      'plan_next_session',
      'generate_scenario'
    )
  );

alter table analysis_jobs
  drop constraint analysis_jobs_target_matches_job_type;

alter table analysis_jobs
  add constraint analysis_jobs_target_matches_job_type
  check (
    (job_type = 'analyze_utterance' and utterance_id is not null and session_id is null)
    or (job_type = 'summarize_session' and session_id is not null and utterance_id is null)
    or (job_type = 'plan_next_session' and session_id is not null and utterance_id is null)
    or (job_type = 'generate_scenario' and session_id is not null and utterance_id is null)
  );

alter table learning_sessions
  drop constraint learning_sessions_mode_check;

alter table learning_sessions
  add constraint learning_sessions_mode_check
  check (mode in ('speaking', 'shadowing', 'review', 'pronunciation', 'scenario_intake'));
