-- 007_learning_coach_slice2.sql
-- 학습 코치 슬라이스 2 — 판단과 적용
-- 설계: docs/design/2026-08-25-learning-coach-agent-design.md §8.1 · §8.3
-- 계획: docs/design/2026-09-04-learning-coach-slice2-plan.md
-- 요구사항: docs/PRD.md §11 R11-2(계획) · R11-10(관찰 기록)
--
-- 번호가 007인 이유: 006이 슬라이스 1이었고 002는 만들어진 적이 없다(설계서 §8.4 정정).
-- 트랜잭션은 scripts/migrate.py 가 감싼다 — 이 파일에 begin/commit 을 쓰지 않는다.
--
-- 여기 **없는 것**: users.current_level 은 001 이 이미 만들었고 CEFR CHECK 도 거기 있다.
-- pattern_attempts·suggested_contexts 는 006(슬라이스 1)이 만들었다.

-- §8.1: 세션이 만든 계획 1행. session_id 는 **계획을 만든 세션**이다(계획 문서 「구현 전 정정」)
-- — 소비 세션은 생성 시점에 존재하지 않는다. 세션 시작은 직전 세션이 만든 계획을 조회한다.
create table session_plans (
  id uuid primary key default gen_random_uuid(),
  -- unique: 한 세션이 계획을 두 번 만들지 않는다. cascade: 세션이 지워지면 계획도 무의미하다.
  session_id uuid not null unique references learning_sessions (id) on delete cascade,
  -- 초점 패턴 1~2개 (PRD §11 R11-2). uuid[] 로 두는 이유: 순서가 의미를 갖고 행이 2개뿐이라
  -- 별도 연결 표를 만들면 조회가 늘기만 한다(YAGNI).
  focus_pattern_ids uuid[] not null,
  -- 질문 3~5개. 모양은 [{"prompt","context"}, …] — 계획서 Task 1 이 정했다.
  questions jsonb not null,
  -- CEFR 값역은 001 의 users.current_level·learning_scenarios.level 과 **같은 값**을 쓴다.
  target_level text not null check (target_level in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
  -- not null + 공백 금지: 이유 없는 추천은 사용자가 판단을 검증할 수 없다(PRD.md:190 R11-3).
  reason text not null,
  -- 세션 지시문 가변부(§5.2). 구조로 저장하고 문장 조립은 읽는 쪽이 한다.
  instruction jsonb not null,
  -- 계획 품질 관측용. 폴백으로 시작한 세션은 애초에 이 행이 없으므로 'fallback' 은
  -- "계획 생성은 됐지만 뱅크 내용을 썼다"는 뜻이다.
  source text not null check (source in ('agent', 'fallback')),
  created_at timestamptz not null default now(),
  constraint session_plans_focus_len
    check (array_length(focus_pattern_ids, 1) between 1 and 2),
  constraint session_plans_questions_len
    check (jsonb_typeof(questions) = 'array' and jsonb_array_length(questions) between 3 and 5),
  constraint session_plans_reason_not_blank
    check (btrim(reason) <> '')
);

-- §6.3: 덧붙이기만 한다. 갱신·삭제하지 않으므로 updated_at 을 두지 않는다.
create table learner_notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (id) on delete cascade,
  -- 관찰 항목 배열 + 수준 변경 사유. 별도 이력 표를 만들지 않는다(§7).
  note jsonb not null,
  -- 이 노트가 읽은 발화 범위 — 어떤 근거로 쓰인 노트인지 추적한다(§6.3).
  window_from timestamptz not null,
  window_to timestamptz not null,
  created_at timestamptz not null default now(),
  constraint learner_notes_window_ordered check (window_from <= window_to)
);

-- 최신 행이 현행 노트다(§6.3). 조회가 항상 "이 사용자의 가장 최근 1행"이라 이 인덱스를 둔다.
create index idx_learner_notes_latest on learner_notes (user_id, created_at desc);

-- §8.3: job_type 에 계획 생성을 더한다. **값만 늘리면 안 된다** — 대상 컬럼 CHECK 가
-- 2분기 OR 이라 session_id 조합이 거부된다(계획서 「구현 전 정정」). 두 CHECK 를 함께 갈아낸다.
-- partial unique uq_analysis_jobs_pending_session 은 001 이 (job_type, session_id) 로
-- 이미 만들어 뒀다 — **새 인덱스를 만들지 않는다.**
alter table analysis_jobs drop constraint analysis_jobs_job_type_check;
alter table analysis_jobs add constraint analysis_jobs_job_type_check
  check (job_type in ('analyze_utterance', 'summarize_session', 'plan_next_session'));

alter table analysis_jobs drop constraint analysis_jobs_target_matches_job_type;
alter table analysis_jobs add constraint analysis_jobs_target_matches_job_type
  check (
    (job_type = 'analyze_utterance' and utterance_id is not null and session_id is null)
    or (job_type = 'summarize_session' and session_id is not null and utterance_id is null)
    or (job_type = 'plan_next_session' and session_id is not null and utterance_id is null)
  );
