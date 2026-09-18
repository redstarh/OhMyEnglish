-- 028_llm_calls_vocab_purpose.sql
-- 낱말 뜻 조회를 `llm_calls.purpose` 값역에 더한다
-- 캡틴 결정: 130(스토리보드 §6 이 뺀 열 가운데 「낱말 뜻 조회」 하나만 되살린다)
-- 소유 태스크: TASK-194
--
-- 번호: `ls db/migrations/` 실측 최대가 027 이고 `schema_migrations` 의 마지막 적용도
--       027_youtube_videos.sql 이다(이 파일을 쓰는 턴에 직접 조회했다).
-- ⛔ 번호를 미리 예약하지 않는다(결정 27).
--
-- 되돌리기:
--   alter table llm_calls drop constraint llm_calls_purpose_check;
--   alter table llm_calls add constraint llm_calls_purpose_check
--     check (purpose = any (array['plan','analysis','spike','nova','generate_scenario',
--                                 'summarize_session','summarize_week']));
-- ⚠️ 되돌리기 전에 `purpose='vocab'` 행이 남아 있으면 그 CHECK 추가가 실패한다 — 지우거나
--    남겨 둘지 정하고 되돌린다. **행을 조용히 지우지 않는다**(비용 기록이다).

-- ⛔ **사용량을 기록하지 않는 길을 고르지 않았다.** 그 길은 마이그레이션이 0건이지만
--    `services/usage.py` 가 *"이 비용은 복원할 수 없다"* 를 근거로 세운 규율을 깬다 —
--    낱말 조회 비용이 어느 집계에도 나타나지 않게 된다.
-- ⚠️ **`spike` 로 갈음하지 않은 이유**: 그 값은 「이름 없는 임시 호출」이고(그 상수의 주석)
--    낱말 조회는 제품 기능이다. 갈래를 틀리게 적으면 비용이 틀린 축에 얹히고 그 오류는 조용하다.
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
        'vocab'
      ]
    )
  );
