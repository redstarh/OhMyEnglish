-- 029_utterances_readback_transcript.sql
-- 낭독 판정의 입력 하나를 담는다 — 학습자가 실제로 낸 소리의 전사문
-- 캡틴 결정: 131(낭독 판정의 전사는 저장한 WAV 를 Nova 에 다시 흘려 얻는다)
-- 소유 태스크: TASK-205 · 설계서 docs/design/2026-09-18-read-aloud-judgment-design.md §4
--
-- 번호: `ls db/migrations/` 실측 최대가 028 이고 `schema_migrations` 의 마지막 적용도
--       028_llm_calls_vocab_purpose.sql 이다(이 파일을 쓰는 턴에 직접 조회했다).
-- ⛔ 번호를 미리 예약하지 않는다(결정 27).
--
-- 되돌리기:
--   alter table utterances drop constraint utterances_readback_only_for_shadowing;
--   alter table utterances drop column readback_transcript;
-- ⚠️ 되돌리면 이미 얻은 전사가 사라지고 그것을 다시 얻으려면 Nova 를 다시 부른다(비용이 든다).
--    되돌리기 전에 그 값이 필요한지 정한다.

-- 왜 컬럼 하나인가 (설계서 §4):
-- ⛔ **새 job 종류를 만들지 않는다.** `analysis_jobs` 에 종류를 더하려면
--    `analysis_jobs_target_matches_job_type` CHECK 를 DROP → ADD 해야 하고
--    `workers/analysis_worker.py` 의 `sweep_recordings` docstring 이 그것을 *"data-first 가 말하는
--    가장 위험한 형태"* 로 이미 금지했다. 낭독 판정은 학습자가 볼 때만 필요하므로 큐가 필요 없다.
-- ⛔ **새 표를 만들지 않는다.** 값이 발화 한 행에 1:1 로 붙고 수명도 그 행과 같다(세션을 지우면
--    cascade 로 함께 사라진다) — 표를 늘리면 그 cascade 를 다시 배선해야 한다.
-- ⛔ **`utterance_type` 값역에 값을 더하지 않는다.** 그것은 `011` 이 CHECK 를 DROP → ADD 해야 했던
--    자리다. 낭독 전사는 **같은 행의 다른 면**이지 다른 종류의 발화가 아니다.
-- ⇒ 남는 것은 **덧붙이는 컬럼 하나**이고 기존 CHECK 를 하나도 건드리지 않는다.

-- 왜 nullable 인가:
-- 기존 행에는 값이 없고, **학습자가 판정을 보지 않은 낭독은 영구히 비어 있다**(요청할 때만 계산한다).
-- 즉 빈 값이 정상 상태이므로 not null 로 만들면 그 상태를 표현할 자리가 없어진다.
alter table utterances
  add column readback_transcript text;

-- 이 컬럼은 낭독 녹음 행에만 뜻이 있다. 다른 종류의 발화에 값이 들어가면 판정이 엉뚱한 행을 읽는다.
-- ⚠️ 새 CHECK 를 **더하는** 것이고 기존 CHECK 를 DROP 하지 않는다.
alter table utterances
  add constraint utterances_readback_only_for_shadowing
  check (readback_transcript is null or utterance_type = 'shadowing_recording');
