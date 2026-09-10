-- 012_daily_error_summary.sql
-- 일일 오류 요약 — 사용자 타임존 기준 달력 날짜 1일의 오류 집계 스냅샷
-- 요구사항: docs/PRD.md §13 (R13-1 ~ R13-7 · AC13-1 ~ AC13-5)
-- 설계: docs/design/2026-09-11-daily-error-summary-design.md §3(표) · §6(날짜 경계) · §7(적용) · §8(되돌리기)
-- 소유 태스크: TASK-1
--
-- 번호: `schema_migrations` 직접 조회가 `001 · 003~007 · 009 · 010 · 011` 이므로 012 임.
-- 002 와 008 은 영구 결번이라 되살리지 않음(결정 27).
--
-- 이 파일이 하는 것은 새 표 생성 한 문장뿐임. 기존 표의 값역도 NOT NULL 도 건드리지 않음 —
-- data-first 규약 §2 의 위험 형태 어디에도 들지 않고, 되돌리기는 drop table 하나임(설계서 §8).
--
-- 왜 표를 만드는가. 조회 시 계산으로는 「그날 무엇을 분석했는지」가 시간이 지나면 달라짐:
-- `services/analysis.py` 의 `_UPSERT_PATTERN_SQL` 이 패턴의 목표 형태를 가장 최근 분석 값으로
-- 갱신하고, `_DELETE_OCCURRENCES_SQL` 이 재분석에서 그 발화의 발생 행을 지우고 다시 넣음.
-- 조회 시 계산을 채택한 자리(만성 지표 · 2026-08-25 설계서 §6.1)와 이 표가 갈리는 이유가 그것임.
--
-- 소비자 없이 이 파일만 적용하지 않음 — 읽는 쪽 셋이 같은 커밋에 들어감(설계서 §4):
-- `services/daily_summary.load_daily_summary` → `api/daily.py` 의 `GET /api/daily-summary`
-- → 프론트 결과 화면의 「오늘 무엇을 틀렸는지」 절.

create table daily_error_summary (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (id) on delete cascade,
  -- 달력 날짜라 timestamptz 가 아님. 절대 시각을 담는 컬럼이 아니므로 전역 시각 규약의
  -- 「이벤트 시각은 timestamptz」에 걸리지 않음. 이 값을 구하는 규약은 아래 timezone 을 볼 것.
  summary_date date not null,
  -- 그 날짜를 그은 타임존의 스냅샷임. users.timezone 이 나중에 바뀌면 과거 요약이 어느 경계로
  -- 그어졌는지 복원할 수 없으므로 행에 남김. users.timezone 에는 CHECK 가 없어(001) 무효값이
  -- 실재할 수 있고, 그 거부는 조회 시점의 앱이 함 — 여기서는 빈 문자열만 막음.
  timezone text not null check (length(btrim(timezone)) > 0),
  -- 그날의 발생 행 수와 관여한 패턴 종 수. patterns 를 세어 얻을 수 있지만 그 목록은 상위
  -- 20종에서 잘릴 수 있으므로(설계서 §3.3) 전체 수를 따로 담음.
  occurrence_count integer not null check (occurrence_count >= 0),
  pattern_count integer not null check (pattern_count >= 0),
  -- 패턴별 상세. [{pattern_key, category, target_form, occurrences, example:{original_span,
  -- correction, reason}}] 이고 발생 수 내림차순 · 동률은 pattern_key 오름차순임(결정론).
  -- 표를 둘로 나누지 않은 이유: 스냅샷은 통째로 읽히고 부분 갱신이 없음. 이 리포는 이미
  -- learning_sessions.summary · learner_notes.note · error_occurrences.suggested_contexts 를
  -- 같은 용도로 씀. 대가는 패턴별 SQL 집계·인덱스가 안 되는 것이고, 필요해지면 표로 승격함.
  patterns jsonb not null,
  -- 이 스냅샷을 계산한 시각. 재분석으로 다시 쓰이면 함께 갱신됨.
  computed_at timestamptz not null default now(),
  -- 자연키 유일 제약. upsert 의 conflict 대상이고 조회 인덱스도 겸함 — 별도 인덱스를 만들지
  -- 않는 이유임. error_patterns 의 unique (user_id, pattern_key) 와 같은 관용.
  unique (user_id, summary_date)
);
