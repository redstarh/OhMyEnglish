-- 006_learning_coach_slice1.sql
-- 학습 코치 슬라이스 1 — 기록과 계산
-- 설계: docs/design/2026-08-25-learning-coach-agent-design.md §8.1·§8.2 (정본)
-- 계획: docs/design/2026-09-03-learning-coach-slice1-plan.md
-- 요구사항: docs/PRD.md §11 · PRD.md:92 "같은 패턴을 최소 세 개의 다른 상황에서 재사용한다"
--
-- 번호: 설계서 §8.4는 002를 예약했지만 002는 **만들어진 적이 없고**(파일·git 이력 각 0건)
-- 003~005가 발음 설계에 쓰였다. migrate.py의 추적이 파일명 기준이라 006으로 쌓는다.
--
-- 여기 **없는 것**: session_plans · learner_notes · analysis_jobs.job_type 에
-- 'plan_next_session' 추가. 셋 다 슬라이스 2(판단과 적용)의 것이다 — 이 슬라이스는
-- 무엇도 생성하지 않고 기록과 계산만 한다(§12.1).

-- §8.2: Claude 분석이 이미 산출할 수 있는 "서로 다른 상황 3개". **지금 저장하지 않으면
-- 소급이 불가능하다** — 이 컬럼 하나가 슬라이스 1을 앞세운 이유다.
-- nullable: 기존 발화에는 없다. 배열 길이 CHECK를 두지 않는다 — 모델이 2개만 낸 것을
-- 실패로 만들면 그 발화의 교정 전체를 잃는다(§8.2).
-- "없음"의 표현은 null 하나다. 앱은 빈 배열을 쓰지 않는다.
alter table error_occurrences add column suggested_contexts jsonb;

-- §8.1: 교정 후 재발화의 정답 여부. **복습 단계 전이의 유일한 신호원**이다 —
-- 이 표가 비면 모든 패턴이 1일 단계에서 영원히 머문다.
--
-- 왜 pronunciation_attempts와 합치지 않는가: 그 표는 발화 없이 tool 이벤트만으로도 행이
-- 생기고 target_form·signal_source·pending 상태를 갖는다(003 주석). 이 표의 행은 전사문을
-- 본 뒤 발화 1건에 붙는다 — 합치면 대부분 null인 표가 된다.
create table pattern_attempts (
  id uuid primary key default gen_random_uuid(),
  pattern_id uuid not null references error_patterns (id) on delete cascade,
  -- 재발화 발화. 이 행의 유일한 근거이므로 발화가 사라지면 판정도 사라진다(cascade).
  utterance_id uuid not null references utterances (id) on delete cascade,
  -- 'unclear'를 둔다 — 판정할 수 없는 발화를 incorrect로 강제하면 숙련도가 부당하게 깎인다(§8.1).
  -- 'pending'은 두지 않는다: 이 판정은 전사문을 이미 본 뒤에 이루어져 대기 상태가 없다.
  outcome text not null check (outcome in ('correct', 'incorrect', 'unclear')),
  created_at timestamptz not null default now(),
  -- AS10: 발화 단위 replace가 재실행돼도 행이 중복되지 않는다.
  -- pattern_id가 선두인 이 인덱스가 복습 상태 재계산의 조회 경로도 겸한다(별도 인덱스 불필요).
  unique (pattern_id, utterance_id)
);
