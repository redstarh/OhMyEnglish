-- 033_course_progress_attempts.sql
-- 문법 코스(Grammar in Use BASIC 이어 듣기 · 한 문장 따라 말하기)의 진도와 따라 하기 기록
-- 설계: docs/design/2026-10-26-grammar-course-design.md §5 · 소유 태스크: TASK-286
--
-- 번호: `ls db/migrations/` 실측 최대가 032 이고 `schema_migrations` 의 마지막 적용도
--       032_utterances_translation.sql 이다(이 파일을 쓰는 턴에 직접 조회했다).
-- ⛔ 번호를 미리 예약하지 않는다(결정 27).
--
-- 되돌리기:
--   drop table course_attempts;
--   drop table course_day_progress;
-- ⚠️ 되돌리면 학습자의 따라 하기 기록이 사라진다 — 되돌리기 전에 `pg_dump -n ohmyenglish` 백업이
--    선행되어야 함.

-- ⚠️ **콘텐츠(Day · 단원 · 문장)는 표로 두지 않는다** — 정본은 `app/backend/app/content/grammar_basic.json`
--    이다. 문장은 사람이 고치는 학습 자산이고 리포에서 리뷰되어야 하므로 파일이 맞다. 표는 학습자가
--    만드는 상태(진도 · 기록)만 갖는다.
-- ⚠️ `day` 의 값역(1~6)은 콘텐츠 파일이 정하지만 여기서도 막는다 — 잘못된 값이 들어오면 목록 화면이
--    없는 Day 를 그리게 된다.
create table course_day_progress (
  user_id uuid not null references users (id) on delete cascade,
  day smallint not null check (day between 1 and 6),
  position_sec numeric(7, 2) not null default 0 check (position_sec >= 0),
  unit smallint not null check (unit between 1 and 113),
  sentence_index smallint not null default 0 check (sentence_index >= 0),
  completed_count integer not null default 0 check (completed_count >= 0),
  last_completed_at timestamptz,
  updated_at timestamptz not null default now(),
  primary key (user_id, day)
);

-- 따라 하기 한 번 = 한 행. ⛔ 녹음은 남기지 않는다 — 전사문과 낱말 판정만 남긴다(설계서 §2 반목표).
-- ⚠️ `transcript` 가 빈 문자열인 행도 시도다 — 「못 알아들었다」도 학습자가 따라 한 횟수에 든다(§4).
-- ⚠️ 날짜 버킷은 저장하지 않는다 — `(created_at at time zone users.timezone)::date` 로 읽을 때 가른다.
create table course_attempts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (id) on delete cascade,
  sentence_key text not null check (sentence_key ~ '^u[0-9]{3}-s[0-9]$'),
  transcript text not null,
  words jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create index course_attempts_user_created_idx on course_attempts (user_id, created_at);
create index course_attempts_user_sentence_idx on course_attempts (user_id, sentence_key);
