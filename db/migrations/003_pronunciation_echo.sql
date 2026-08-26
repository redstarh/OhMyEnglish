-- 003_pronunciation_echo.sql
-- 발음 시범·재발화 (설계서 §6 — docs/design/2026-08-27-pronunciation-echo-design.md)
-- 요구사항: docs/PRD.md v1.1 §10 (R10-2 재발화 결과 기록, R10-7 오디오 미저장)
--
-- 002는 학습 코치 설계서(2026-08-25)가 예약해 두었다. 두 설계의 구현 순서가 바뀌어도
-- migrate.py의 파일명 추적이 그대로 동작하므로 이쪽을 003으로 쌓는다.
--
-- 왜 error_occurrences를 쓰지 않는가: occurrence는 분석 워커가 **전사문에서** 찾은
-- 오류에 붙는다. 발음은 전사문에 흔적이 0이라(4차수 P2 실측: 음소를 치환해 발음해도
-- ASR이 원문으로 복원했다) 워커가 만들 수 없고, 이 표의 행은 실시간 Nova 이벤트에서
-- 만들어진다.
--
-- 왜 pattern_attempts(학습 코치 설계 §8.1)와 합치지 않는가: 그 표는
-- unique(pattern_id, utterance_id)로 "패턴이 있는 발화의 재발화"를 센다. 발음 시도는
-- ① 패턴이 아직 없을 수 있고 ② tool 호출이 발화가 아니며 ③ target_form·signal_source
-- 처럼 그 표에 자리가 없는 필드를 갖는다. 억지로 합치면 대부분 null인 표가 된다.

create table pronunciation_attempts (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references learning_sessions (id) on delete cascade,
  -- 시범을 유발한 발화. 보조 신호만으로 만든 행은 연결될 발화가 없을 수 있다.
  -- 발화가 지워져도 판정 기록은 남는다 — 그래서 cascade가 아니라 set null이다.
  utterance_id uuid references utterances (id) on delete set null,
  -- outcome='incorrect'이고 target_sound가 있을 때만 연결된다 (설계서 §4.3).
  pattern_id uuid references error_patterns (id) on delete set null,
  -- 올바른 발음으로 읽어준 문장. 이것이 없으면 시범이 없었다는 뜻이라 not null이다.
  target_form text not null check (length(btrim(target_form)) > 0),
  -- 학습자가 어떻게 들렸는지. 시범 시점에는 아직 못 들었다 (설계서 F3).
  spoken_form text,
  -- pattern_key 생성 재료. 예: 'th_as_s'. 모델이 안 줄 수도 있어 nullable이다.
  target_sound text,
  -- 'pending'은 정식 값이다 — Nova는 재발화 **전에** tool을 부른다(설계서 F3·F4:
  -- 스파이크에서 outcome="pending"을 실제로 냈다). 세션 종료 시 남은 pending은
  -- 'unclear'로 수렴된다(설계서 §3.2) — 미판정을 영구히 남기면 숙련도가 왜곡된다.
  outcome text not null check (
    outcome in ('pending', 'correct', 'incorrect', 'unclear')
  ),
  -- 이 행이 무엇 때문에 생겼는지. Nova가 놓쳤을 때 보조 신호로 만든 행을 구분한다(R10-4).
  -- agent_reprompt는 값역에만 두고 첫 구현에서는 쓰지 않는다 — 문구 매칭이라 취약해
  -- 5차수 관측 후 판정한다(설계서 §10 미결 2).
  signal_source text not null default 'nova_tool' check (
    signal_source in ('nova_tool', 'korean_transcript', 'agent_reprompt')
  ),
  created_at timestamptz not null default now(),
  -- pending을 벗어난 시각.
  resolved_at timestamptz,
  -- pending이면 resolved_at이 없고, 판정되면 반드시 있다. 두 상태가 어긋나면 거부한다 —
  -- "판정됐는데 언제인지 모르는" 행이 생기면 수렴 여부를 사후에 알 수 없다.
  constraint pronunciation_attempts_resolved_consistency
    check ((outcome = 'pending') = (resolved_at is null))
);

-- 세션 종료 시 남은 pending을 찾는 경로가 유일한 뜨거운 조회다 (설계서 §6.2).
create index pronunciation_attempts_session_outcome_idx
  on pronunciation_attempts (session_id, outcome);

-- 계획 생성이 최근 창으로 시도를 읽는 경로 (학습 코치 설계서 §4.4).
create index pronunciation_attempts_created_at_idx
  on pronunciation_attempts (created_at desc);
