-- 030_analysis_jobs_indexes.sql
-- `analysis_jobs` 인덱스 둘 — 결과 폴링(2초)과 claim(1초)이 표 전체를 훑던 것을 좁힌다
-- 소유 태스크: TASK-227 (정리 회차 `TASK-222` 의 효율 지적 4·5)
--
-- 번호: `ls db/migrations/` 실측 최대가 029 이고 `schema_migrations` 의 마지막 적용도
--       029_utterances_readback_transcript.sql 이다(이 파일을 쓰는 턴에 직접 조회했다).
-- ⛔ 번호를 미리 예약하지 않는다(결정 27).
--
-- 되돌리기:
--   drop index if exists analysis_jobs_utterance_job_type_idx;
--   drop index if exists analysis_jobs_claimable_available_at_idx;
--
-- ⛔ **두 인덱스 다 계획이 바뀌는 것을 직접 재고 넣었다.** 측정은 테스트 DB 에서 트랜잭션을 열어
--    합성 20만 행을 넣고 `EXPLAIN ANALYZE` 를 전후로 돌린 뒤 **롤백**했다(2026-09-19).
--
-- ① `(utterance_id, job_type)` — 결과 폴링(`services/results._JOB_COUNTS_SQL`).
--    실측(세션 1만 개 × 발화 20건 · job 20만 행):
--      전: Parallel Seq Scan + Hash Join · Execution Time **7.417 ms**
--      후: Nested Loop + 이 인덱스 Index Scan · Execution Time **0.139 ms**
--    ⚠️ **세션이 큰 모양에서는 계획이 바뀌지 않는다** — 한 세션에 발화 1,000건을 넣으면
--       플래너가 여전히 해시 조인을 고른다(그쪽이 실제로 싸다). 그 갈림을 적어 두는 이유:
--       「인덱스를 넣었는데 계획이 그대로다」를 다음 사람이 결함으로 오독하지 않게 한다.
--    ⚠️ 회복 스윕(`utterances._FLUSH_ENDED_SESSIONS_SQL` 의 `not exists`)은 **계획이 바뀌지
--       않았다**(Hash Right Anti Join 유지 · 87.081 ms → 85.037 ms = 잡음 범위). 정리 회차의
--       지적은 그 조회까지 이 인덱스가 덮는다고 적었으나 **실측은 그렇지 않았다.**
--
-- ② `(available_at) where status in ('pending','running')` — claim 대상 선택
--    (`services/jobs.claim_next` 의 서브쿼리). 실측(같은 20만 행):
--      전: BitmapAnd + BitmapOr + Sort(3,973행 훑음) · Execution Time **1.375 ms**
--      후: 이 부분 인덱스 Index Scan + Limit(1행) · cost 0.28..7.61
--    ⛔ **부분 인덱스인 것이 요점이다** — 종단 행(`done`·`failed`)이 표의 대부분이고 그 행은
--       claim 대상이 아니다. 전체 인덱스로 두면 쓰기마다 갱신되는 크기가 그만큼 커진다.
--    ⚠️ `idx_analysis_jobs_status_available` 가 이미 있으나 그것으로는 위 계획이 나오지 않았다
--       (`status` 가 선두라 두 갈래를 각각 비트맵으로 훑고 합친다) — 그래서 대체가 아니라 추가다.
--
-- ⚠️ **`concurrently` 를 쓰지 않는다**: `scripts/migrate.py` 가 파일마다 트랜잭션으로 감싸므로
--    (그 문서의 표가 근거) `create index concurrently` 는 그 안에서 실행될 수 없다. 단일 사용자
--    로컬 도구이고 표가 작아 잠금 시간이 문제가 되지 않는다.

create index if not exists analysis_jobs_utterance_job_type_idx
    on analysis_jobs (utterance_id, job_type);

create index if not exists analysis_jobs_claimable_available_at_idx
    on analysis_jobs (available_at)
 where status in ('pending', 'running');
