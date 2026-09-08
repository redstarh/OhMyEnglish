-- 011_shadowing_items.sql
-- 쉐도잉 과제 — 클립 표 + 세션의 클립 선택 + 학습자 낭독 오디오의 표시
-- 설계: docs/design/2026-09-08-shadowing-task-design.md §3.3 (표) · §4.2 (오디오) · §4.6 (되돌리기)
-- 캡틴 결정: docs/ops/captain-instruction-register.md — 결정 6(재생 0.5~2배·반복 1~10회) ·
--            결정 25(클립 시드는 팀리드가 A2 자체 문장으로) · 결정 27(008·002 영구 결번) ·
--            결정 34(진입점까지 TASK-45 범위 — 이 파일을 쓸 수 있게 만든 결정)
-- 소유 태스크: TASK-45
--
-- 번호: `ls db/migrations/` 실측이 `001 · 003~007 · 009 · 010`이므로 **011**이다.
-- ⛔ 번호를 미리 예약하지 않는다(결정 27) — 이 파일도 쓰는 턴에 최대값을 다시 확인해 받았다.
--    ⚠️ 설계서 §3.5의 *"011도 확정이 아니다 — 008 이동안이 승인되면 012가 된다"*는 **거짓이 됐다**:
--    008 예약 자체가 풀려 영구 결번이 되었으므로 011이 확정이다(그 절을 함께 고쳤다).
--
-- **왜 이 표를 만들 수 있게 됐나** — 설계서 §9가 `data-first` §3(*"소비자가 0곳이면 진행하지
-- 않는다"* · 이 리포가 네 번 낸 실패)을 근거로 이 파일을 **선행 2개 뒤로 미뤄** 두었다:
-- ① 진입점이 정해졌다 ② `create_session`이 `mode`를 받는다. **결정 34가 둘을 이 태스크 범위로
-- 옮겨** 게이트를 풀었다 — 즉 이 마이그레이션은 **소비자와 같은 커밋에서 나간다.**
-- ⛔ 소비자 없이 이 파일만 적용하지 마라. 그러면 게이트가 막으려던 상태가 그대로 재현된다.

-- 1. 쉐도잉 클립. **저작물 전체를 저장하지 않는다**(PRD §5) — 링크와 시간 창만 담는다.
create table shadowing_items (
  id uuid primary key default gen_random_uuid(),
  source_title text not null check (length(btrim(source_title)) > 0),
  -- null = 내장·직접 입력 자료. 외부 영상은 **링크만** 보관한다(PRD §7).
  source_url text,
  -- 클립의 전사문. 문장 단위 제공은 이 값을 **런타임에 쪼개** 만든다(§3.2) — 문장 색인을
  -- 저장하지 않는다(설계서 유도 2: 쪼개는 규칙이 바뀌면 저장된 색인이 조용히 낡는다).
  transcript text not null check (length(btrim(transcript)) > 0),
  -- 출처 안에서의 시간 창. numeric(6,2) = 최대 9999.99초.
  clip_start_sec numeric(6, 2) not null check (clip_start_sec >= 0),
  clip_end_sec   numeric(6, 2) not null,
  -- `learning_scenarios.level`과 **같은 값역**을 쓴다 — 선택의 기준이 같기 때문이다.
  level text not null check (level in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
  created_at timestamptz not null default now(),
  constraint shadowing_items_span_ordered check (clip_end_sec > clip_start_sec),
  -- PRD §7이 정한 클립 길이 상한(90초). **발명값이 아니라 요구사항이다.**
  constraint shadowing_items_span_within_limit check (clip_end_sec - clip_start_sec <= 90)
);

-- 뜨거운 조회는 「학습자 수준에 맞는 클립 고르기」 하나다(§9의 소비자 1).
create index shadowing_items_level_idx on shadowing_items (level);

-- 2. 세션이 고른 클립. `scenario_id`와 **정확히 같은 자리·같은 모양**이다(nullable FK).
-- 이것이 「코드는 있는데 저장할 자리가 없다」를 막는다 — 선택이 재접속에서 살아남는다.
alter table learning_sessions
  add column shadowing_item_id uuid references shadowing_items (id) on delete set null;

-- 클립은 쉐도잉 세션에만 붙는다. **역방향은 강제하지 않는다**(`mode='shadowing'`이면 반드시
-- 클립) — 클립을 고르기 **전에** 세션이 열릴 수 있다.
alter table learning_sessions
  add constraint learning_sessions_shadowing_item_requires_mode
  check (shadowing_item_id is null or mode = 'shadowing');

-- 3. 학습자 낭독 오디오의 **표시**. CHECK는 행 지역이라 세션의 `mode`를 볼 수 없다 →
--    표시가 행에 있어야 한다(§4.1).
-- ⛔ **이것이 이 파일에서 되돌리기 가장 어려운 문장이다**(설계서 약점 1): 114행이 든 표의
--    CHECK를 DROP → ADD하고, `shadowing_recording` 행이 하나라도 생기면 §4.6의 되돌리기
--    스크립트가 값역 축소에서 **실패한다.** 그때 그 행들을 어떻게 할지는 데이터 판단이므로
--    스크립트가 조용히 결정하지 않는다.
-- **새 값을 쓰면 공짜로 얻는 것**(직접 grep해 확인한 4자리): `services/utterances.py`의 분석
-- 묶음 경계 · `services/analysis.py`의 분석 대상 · `services/results.py`의 교정 표시 ·
-- `services/plan_input.py`의 계획 입력이 모두 `utterance_type='learning'`으로 거른다 →
-- **쉐도잉 낭독이 오류 분석·교정 표시·계획 입력에서 자동으로 빠진다. 코드 변경 0.**
-- 반대로 `learning`으로 저장하면 **학습자가 짓지 않은 문장이 학습자의 오류 패턴을 오염시킨다** —
-- 쉐도잉은 남의 문장을 따라 읽는 것이므로 그 문장의 문법은 학습자의 것이 아니다.
-- ⚠️ AC#7이 금지한 값역 확장은 `task_type`·`category`·`mode` 3종이고 `utterance_type`은 그
--    목록에 없다 — **AC#7 위반이 아니다.**
alter table utterances drop constraint utterances_utterance_type_check;

alter table utterances
  add constraint utterances_utterance_type_check
  check (utterance_type in
         ('learning', 'voice_command', 'command_confirmation', 'shadowing_recording'));

-- R10-7(오디오를 저장하지 않는다)의 **예외 경계를 스키마에 새긴다**: 오디오가 있으면 그것은
-- 학습자의 쉐도잉 낭독이다. 캡틴이 연 예외는 이 하나이고, **다른 오디오가 조용히 쌓이는 길**을
-- 여기서 막는다. docstring은 그 함수를 읽을 이유가 없는 사람을 구속하지 못한다 — 스키마는 한다.
alter table utterances
  add constraint utterances_audio_only_for_shadowing
  check (audio_url is null
         or (utterance_type = 'shadowing_recording' and speaker = 'user'));

-- 삭제 스윕과 고아 파일 정리가 도는 유일한 조회. **부분 인덱스**라 지금 크기가 0이다.
create index utterances_stored_audio_idx
  on utterances (session_id, created_at)
  where audio_url is not null;

-- ⛔⛔ **적용 절차 — 이 파일을 돌리기 전에 읽어라** (010이 세운 5단계를 그대로 쓴다)
--   ① `pg_dump -n public` 으로 백업한다. ⚠️ `-n public`을 빼면 `permission denied for schema
--      en_coach`로 막힌다(공유 인스턴스 · `data-first` §5의 실측).
--   ② 표별 행 수를 기록한다(적용 후 대조용 — 특히 `utterances` 114행 유지).
--   ③ 적용한다 (`app/backend/.venv/bin/python scripts/migrate.py`).
--      ⚠️ `migrate.py`는 이미 적용된 파일에 **아무 것도 출력하지 않는다** — 조용한 성공이라
--      출력만 보면 알 수 없다. 반드시 `schema_migrations`를 조회해 확인한다.
--   ④ 재조회로 대조하고 출력을 태스크 노트에 남긴다.
--   ⑤ 어긋나면 **멈추고 캡틴에게 올린다.** 스스로 고치지 않는다.
-- ⚠️ **코드와 이 마이그레이션은 같은 커밋으로 함께 나간다** — 한쪽만 나가면 그 사이에 쉐도잉
--    경로가 깨진다(010이 겪은 형태).
-- 되돌리기 스크립트는 설계서 §4.6이 소유한다. **이 파일에 복제하지 않는다** — 두 곳이 갈라진다.
