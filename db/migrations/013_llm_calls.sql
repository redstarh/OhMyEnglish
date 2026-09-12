-- 013_llm_calls.sql
-- LLM 호출 1건 = 행 1건. 토큰 사용량을 «호출 단위»로 적어 비용을 관측 가능하게 만든다.
-- 결정: docs/ops/captain-instruction-register.md 「결정 66」(2026-09-12 · 사용자가 후보 셋 중
--   「새 표」를 골랐다. 기각한 둘은 ①analysis_jobs 에 컬럼 둘 ②구조화 로그만이다)
-- 소유 태스크: TASK-60
--
-- 번호: `schema_migrations` 직접 조회가 `001 · 003~007 · 009~012` 이므로 013 임.
-- 002 와 008 은 영구 결번이라 되살리지 않음(결정 27).
--
-- ⛔ `analysis_jobs` 에 컬럼 둘을 더하는 안이 기각된 근거는 실측임 — job **밖** 호출(계획 생성
-- 스파이크 · Nova · 예열)이 그 표에 한 행도 남기지 않음. 2026-09-12 세션이 계획 스파이크로
-- Claude 16회를 돌렸고 job 은 0건이었음(`runs/2026-09-12-task108-deepest-marker.md` ·
-- `…-task119-extra-keys.md` · `…-task121-level-bullet.md`). 즉 job 단위 기록은 그 비용을
-- 구조적으로 못 봄.
--
-- 이 파일이 하는 것은 새 표 하나와 인덱스 둘임. 기존 표의 값역도 NOT NULL 도 건드리지 않으므로
-- data-first 규약 §2 의 위험 형태에 들지 않고, 되돌리기는 `drop table llm_calls` 하나임.
--
-- ⚠️ `called_at` 은 `timestamptz` 임 — 절대 시각을 잃지 않음. 「오늘 쓴 비용」 같은 달력 날짜
-- 집계는 읽을 때 `users.timezone` 으로 변환함(전역 시각 규약). 여기서 date 컬럼을 만들지 않음.

create table llm_calls (
  id uuid primary key default gen_random_uuid(),
  -- ⚠️ `provider` 에 CHECK 를 걸지 않음 — 값을 하나만 가두면 제공자가 늘 때마다 마이그레이션이
  -- 필요해지고, 이 컬럼은 값역을 강제할 이유가 없는 «출처 표시»임.
  provider text not null,
  model_id text not null,
  -- job 경로 밖 호출까지 담는 것이 이 표의 존재 이유이므로 갈래는 `purpose` 가 가짐.
  purpose text not null check (purpose in ('plan', 'analysis', 'spike', 'nova')),
  -- job 밖 호출은 null 임. `on delete set null` 인 이유: job 이 지워졌을 때 행을 함께 지우면
  -- 「그 비용은 쓴 적이 없다」가 되어 비용 관측이 거짓이 됨. 귀속만 잃고 금액은 남겨야 함.
  job_id uuid references analysis_jobs (id) on delete set null,
  input_tokens integer not null check (input_tokens >= 0),
  output_tokens integer not null check (output_tokens >= 0),
  called_at timestamptz not null default now()
);

-- 조회는 「기간」과 「기간 × 갈래」 둘로 함. 그 밖의 인덱스는 발명하지 않음.
create index idx_llm_calls_called_at on llm_calls (called_at desc);
create index idx_llm_calls_purpose_called_at on llm_calls (purpose, called_at desc);
