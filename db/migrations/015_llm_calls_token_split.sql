-- 015_llm_calls_token_split.sql
-- `llm_calls` 에 speech·text 토큰 분해 열 넷을 더한다.
-- 결정: docs/ops/captain-instruction-register.md 「결정 68」(2026-09-12 · 사용자가 후보 셋 중
--   「토큰 열 넷을 더함」을 골랐다. 기각한 둘은 ①합계만 적기 ②details jsonb 한 컬럼)
-- 소유 태스크: TASK-124
--
-- 번호: `schema_migrations` 직접 조회가 `001 · 003~007 · 009~014` 이므로 015 임(`H-AL`).
--
-- 왜 필요한가: Nova 의 `usageEvent` 는 토큰을 `speechTokens`·`textTokens` 로 나눠 준다 —
-- 실물 산출물에서 직접 확인했음(`runs/2026-09-11-task97-tool-payload/B0-r2.json`).
-- 합계만 담으면 speech 와 text 의 단가가 다를 때 **금액을 재구성할 수 없음.**
--
-- ⚠️ 넷 다 `nullable` 임 — Claude(InvokeModel)는 그 분해를 주지 않으므로 `null` 이고, 그 `null` 이
-- 「분해 없음」을 뜻함. ⛔ 0 으로 채우지 않음: 0 은 「speech 토큰을 쓰지 않았다」는 주장이 되고
-- Claude 호출에는 그 축이 아예 없음.
-- ⛔ 단가·금액 컬럼을 만들지 않음 — 단가는 시점·리전에 따라 바뀌므로 읽을 때 곱함.
--
-- 기존 열(`input_tokens`·`output_tokens`)은 그대로 둠 — Nova 는 그 자리에 `totalInputTokens`·
-- `totalOutputTokens` 를 넣으므로 두 축이 **합계와 분해**로 나뉘고 서로를 대신하지 않음.
-- 되돌리기는 열 넷을 drop 하는 것임(값이 있으면 그 값은 사라짐).

alter table llm_calls
  add column input_speech_tokens integer check (input_speech_tokens >= 0),
  add column input_text_tokens integer check (input_text_tokens >= 0),
  add column output_speech_tokens integer check (output_speech_tokens >= 0),
  add column output_text_tokens integer check (output_text_tokens >= 0);
