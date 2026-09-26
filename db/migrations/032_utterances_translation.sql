-- 032_utterances_translation.sql
-- 튜터 발화의 한국어 번역을 발화 행에 남기고, 그 비용 갈래를 `llm_calls.purpose` 값역에 더한다
-- 요구: 사용자 요청 2026-09-26(말풍선 [번역] 버튼) · 소유 태스크: TASK-275
--
-- 번호: `ls db/migrations/` 실측 최대가 031 이고 `schema_migrations` 의 마지막 적용도
--       031_sessions_focus_pattern_key.sql 이다(이 파일을 쓰는 턴에 직접 조회했다).
-- ⛔ 번호를 미리 예약하지 않는다(결정 27).
--
-- 되돌리기:
--   alter table utterances drop column translation_ko;
--   alter table llm_calls drop constraint llm_calls_purpose_check;
--   alter table llm_calls add constraint llm_calls_purpose_check
--     check (purpose = any (array['plan','analysis','spike','nova','generate_scenario',
--                                 'summarize_session','summarize_week','vocab']));
-- ⚠️ 되돌리기 전에 `purpose='translation'` 행이 남아 있으면 그 CHECK 추가가 실패한다 — 비용
--    기록이므로 조용히 지우지 않는다(028 과 같은 규율).

-- ⚠️ **표를 새로 만들지 않고 컬럼 하나로 둔다** — 번역은 발화 한 행에 매이고 그 행과 함께 지워져야
--    한다(사용자 삭제의 cascade 가 그대로 덮는다). 표로 떼면 수명 규칙이 둘이 된다.
-- ⚠️ `null` 이 「아직 만들지 않았다」다. 모델 실패는 저장하지 않는다 — 저장하면 다시 눌러도 번역이
--    영원히 오지 않는다(`services/translation.py`).
alter table utterances add column translation_ko text;

alter table llm_calls drop constraint llm_calls_purpose_check;

alter table llm_calls
  add constraint llm_calls_purpose_check
  check (
    purpose = any (
      array[
        'plan',
        'analysis',
        'spike',
        'nova',
        'generate_scenario',
        'summarize_session',
        'summarize_week',
        'vocab',
        'translation'
      ]
    )
  );
