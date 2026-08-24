create table users (
  id uuid primary key,
  display_name text not null,
  timezone text not null default 'Asia/Seoul',
  current_level text not null default 'A2',
  goal text,
  created_at timestamptz not null default now()
);

create table learning_scenarios (
  id uuid primary key,
  category text not null check (category in ('daily_life', 'business', 'shadowing')),
  level text not null,
  title text not null,
  prompt_template text not null,
  created_at timestamptz not null default now()
);

create table learning_sessions (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  scenario_id uuid references learning_scenarios(id),
  mode text not null check (mode in ('speaking', 'shadowing', 'review')),
  learning_source text not null default 'recommended' check (learning_source in ('recommended', 'additional', 'user_requested')),
  started_via text not null default 'ui' check (started_via in ('ui', 'voice_command', 'schedule')),
  started_at timestamptz not null default now(),
  ended_at timestamptz,
  summary jsonb not null default '{}'::jsonb
);

create table utterances (
  id uuid primary key,
  session_id uuid not null references learning_sessions(id) on delete cascade,
  speaker text not null check (speaker in ('user', 'agent')),
  utterance_type text not null default 'learning' check (utterance_type in ('learning', 'voice_command', 'command_confirmation')),
  transcript text not null,
  audio_url text,
  sequence_no integer not null,
  created_at timestamptz not null default now(),
  unique (session_id, sequence_no)
);

create table error_patterns (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  category text not null,
  pattern_key text not null,
  target_form text not null,
  frequency integer not null default 0,
  mastery_score numeric(5,2) not null default 0 check (mastery_score between 0 and 100),
  last_seen_at timestamptz,
  next_review_at timestamptz,
  created_at timestamptz not null default now(),
  unique (user_id, pattern_key)
);

create table error_occurrences (
  id uuid primary key,
  utterance_id uuid not null references utterances(id) on delete cascade,
  pattern_id uuid not null references error_patterns(id) on delete cascade,
  original_span text not null,
  correction text not null,
  severity text not null check (severity in ('low', 'medium', 'high')),
  confidence numeric(3,2) not null check (confidence between 0 and 1),
  created_at timestamptz not null default now()
);

create table review_tasks (
  id uuid primary key,
  user_id uuid not null references users(id) on delete cascade,
  pattern_id uuid not null references error_patterns(id) on delete cascade,
  task_type text not null check (task_type in ('rephrase', 'role_play', 'shadowing')),
  scenario_context text not null,
  due_at timestamptz not null,
  status text not null default 'pending' check (status in ('pending', 'done', 'skipped')),
  created_at timestamptz not null default now()
);

create index idx_error_patterns_review on error_patterns (user_id, next_review_at);
create index idx_review_tasks_due on review_tasks (user_id, status, due_at);
