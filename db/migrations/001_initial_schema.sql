-- 001_initial_schema.sql
-- 첫 수직 슬라이스 확정 스키마 (설계서 §6, §6.1a — docs/design/2026-08-24-first-vertical-slice-design.md)
-- 아직 어떤 DB에도 적용된 적이 없는 001을 직접 재작성한다(002를 쌓지 않음).
--
-- 이번 재작성에 넣지 않는 것 (§6.4): shadowing_items(002), weekly_reports(002),
-- users.daily_goal_minutes(단일 사용자라 앱 상수로 대체).

create extension if not exists pgcrypto;

-- CEFR 레벨은 users.current_level / learning_scenarios.level에서 공유한다 (D3).
-- Postgres에는 재사용 가능한 도메인 CHECK가 없어 두 테이블에 동일한 CHECK를 각각 건다.

create table users (
  id uuid primary key default gen_random_uuid(),
  display_name text not null,
  timezone text not null default 'Asia/Seoul',
  current_level text not null default 'A2'
    check (current_level in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
  goal text,
  created_at timestamptz not null default now()
);

create table learning_scenarios (
  id uuid primary key default gen_random_uuid(),
  category text not null check (category in ('daily_life', 'business', 'shadowing')),
  level text not null check (level in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
  title text not null,
  prompt_template text not null,
  created_at timestamptz not null default now()
);

create table learning_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (id) on delete cascade,
  scenario_id uuid references learning_scenarios (id),
  mode text not null check (mode in ('speaking', 'shadowing', 'review')),
  learning_source text not null default 'recommended'
    check (learning_source in ('recommended', 'additional', 'user_requested')),
  started_via text not null default 'ui'
    check (started_via in ('ui', 'voice_command', 'schedule')),
  -- F2-ii: Nova 연결 실패로 닫힌 세션(§7 Failure)을 정상 종료와 구분한다.
  status text not null default 'active'
    check (status in ('active', 'completed', 'failed')),
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  summary jsonb not null default '{}'::jsonb
);

create table utterances (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references learning_sessions (id) on delete cascade,
  speaker text not null check (speaker in ('user', 'agent')),
  utterance_type text not null default 'learning'
    check (utterance_type in ('learning', 'voice_command', 'command_confirmation')),
  transcript text not null,
  audio_url text,
  sequence_no integer not null,
  created_at timestamptz not null default now(),
  -- Gateway 자체의 이중 commit을 막는 무결성 가드다. sequence_no는 서버가
  -- 세션 내 단조 증가로 부여하므로 재수신 중복 제거 장치가 아니다 (§7 Boundary).
  unique (session_id, sequence_no)
);

create table error_patterns (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (id) on delete cascade,
  -- D1: 코드값 확정 — PRD.md:89 한국어 표시명과의 매핑은 database-schema.md에 문서화.
  -- pronunciation_intonation은 텍스트 전사문만 받는 이번 워커가 산출할 수 없어
  -- CHECK에는 두되 첫 슬라이스에선 미사용이다.
  category text not null check (
    category in (
      'verb_tense',
      'article',
      'preposition',
      'word_order',
      'verb_form',
      'business_expression',
      'pronunciation_intonation'
    )
  ),
  pattern_key text not null,
  target_form text not null,
  frequency integer not null default 0,
  mastery_score numeric(5, 2) not null default 0 check (mastery_score between 0 and 100),
  -- B3: 사용자가 스스로 체감한 난이도. 미입력을 허용한다(null 허용).
  self_difficulty smallint check (self_difficulty between 1 and 5),
  last_seen_at timestamptz,
  next_review_at timestamptz,
  created_at timestamptz not null default now(),
  -- 같은 오류는 문장이 달라도 한 패턴으로 병합된다 (§7 Contract, tests/README.md:9).
  unique (user_id, pattern_key)
);

create table error_occurrences (
  id uuid primary key default gen_random_uuid(),
  utterance_id uuid not null references utterances (id) on delete cascade,
  pattern_id uuid not null references error_patterns (id) on delete cascade,
  original_span text not null,
  correction text not null,
  severity text not null check (severity in ('low', 'medium', 'high')),
  confidence numeric(3, 2) not null check (confidence between 0 and 1),
  created_at timestamptz not null default now()
  -- F2-i: 발화 단위 replace로 멱등 처리한다(§5.2) — unique(utterance_id, pattern_id)는
  -- 한 발화의 복수 occurrence(같은 패턴이 한 문장에 두 곳)를 잃어 철회했다.
);

-- E1: 세션 결과 조회(§5.5)와 패턴별 최신 발생 조회를 위한 인덱스.
create index idx_error_occurrences_pattern_created on error_occurrences (pattern_id, created_at desc);
create index idx_error_occurrences_utterance on error_occurrences (utterance_id);

create table review_tasks (
  id uuid primary key default gen_random_uuid(),
  -- F3: user_id를 제거하고 소유자를 pattern_id로 유도한다(단일 사용자 범위의
  -- 불일치 가능성 원천 제거).
  pattern_id uuid not null references error_patterns (id) on delete cascade,
  task_type text not null check (task_type in ('rephrase', 'role_play', 'shadowing')),
  scenario_context text not null,
  -- B1: 복습 단계는 패턴이 아니라 과제에 둔다. 1·3·7일 3단계로 확정한다(C1).
  review_stage smallint not null check (review_stage between 1 and 3),
  due_at timestamptz not null,
  status text not null default 'pending' check (status in ('pending', 'done', 'skipped')),
  created_at timestamptz not null default now(),
  -- F1: 복습 과제 중복 생성을 차단한다 (tests/README.md:12).
  unique (pattern_id, review_stage)
);

create index idx_review_tasks_due on review_tasks (status, due_at);
create index idx_error_patterns_review on error_patterns (user_id, next_review_at);

-- F2 / §6.1a: 비동기 분석 큐. 컬럼은 구현자 선택 여지를 없애기 위해 확정한다.
-- payload 컬럼은 두지 않는다 — 입력은 FK로 참조하는 원본 행에서 읽는다 (YAGNI).
create table analysis_jobs (
  id uuid primary key default gen_random_uuid(),
  job_type text not null check (job_type in ('analyze_utterance', 'summarize_session')),
  utterance_id uuid references utterances (id) on delete cascade,
  session_id uuid references learning_sessions (id) on delete cascade,
  status text not null default 'pending'
    check (status in ('pending', 'running', 'done', 'failed')),
  available_at timestamptz not null default now(),
  attempts smallint not null default 0,
  locked_at timestamptz,
  locked_by text,
  last_error text,
  created_at timestamptz not null default now(),
  -- job_type에 따라 대상 컬럼이 상호배타적으로 채워진다 (§6.1a).
  constraint analysis_jobs_target_matches_job_type check (
    (job_type = 'analyze_utterance' and utterance_id is not null and session_id is null)
    or (job_type = 'summarize_session' and session_id is not null and utterance_id is null)
  )
);

-- partial unique: pending/running인 동안 같은 대상에 중복 등록을 차단한다 (§5.2).
create unique index uq_analysis_jobs_pending_utterance
  on analysis_jobs (job_type, utterance_id)
  where status in ('pending', 'running');

create unique index uq_analysis_jobs_pending_session
  on analysis_jobs (job_type, session_id)
  where status in ('pending', 'running');

-- claim 대상 조회(§5.4 FOR UPDATE SKIP LOCKED)를 위한 인덱스.
create index idx_analysis_jobs_status_available on analysis_jobs (status, available_at);
