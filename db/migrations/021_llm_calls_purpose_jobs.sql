-- 021_llm_calls_purpose_jobs.sql
-- `llm_calls.purpose` 값역에 **job 종류 둘**을 더한다 — `generate_scenario` · `summarize_session`.
-- 소유 태스크: `TASK-134`(결함) · 함께 걸린 것: `TASK-62` AC#4(총평도 돈이 나가는 호출이다).
--
-- 번호: `db/migrations/` 의 최대가 `020` 이고 dev DB `schema_migrations` 최대는 `019` 다(`H-AL`).
-- ⚠️ `020` 은 발음 축이 커밋했고 dev DB 에 **아직 적용되지 않았다** — 그쪽이 적용 시점을 따로
-- 판단한다. 이 파일은 그 뒤에 붙으므로 번호가 `021` 이다.
--
-- ⛔⛔ **무엇이 고장이었나 — 「호출은 성공하고 기록만 사라진다」.**
-- 013 이 값역을 `plan`·`analysis`·`spike`·`nova` 넷으로 두었는데 `services/scenario_generator.py`
-- 가 `purpose='generate_scenario'` 를 넘긴다. 그 값은 **삽입 자체가 불가능**하고,
-- `services/usage.py` 가 `asyncpg.PostgresError` 를 삼켜 `exception` 으로만 찍는다.
-- ⇒ 결정 66(`TASK-60`)이 요구한 토큰 기록이 그 job 에 대해 **0건**이었다.
-- 실측(2026-09-13 · dev DB 직접 조회): 값역은 넷 그대로이고 기록된 `purpose` 는 `nova` 1 · `spike` 3.
-- ⚠️ `plan`·`analysis` 가 0건인 것은 이 결함의 증거가 **아니다**(그 job 이 dev DB 에서 실물 Claude 로
-- 돈 적이 없을 수 있다). 확정 근거는 **CHECK 정의 하나**다.
--
-- ⛔⛔ **`drop`+`add` 는 값역을 «대체»한다 — 기존 값을 빠뜨리면 조용히 사라진다.** 아래 목록은
-- 2026-09-13 에 `pg_get_constraintdef` 로 dev DB 에서 직접 읽은 것이다: `plan`·`analysis`·`spike`·
-- `nova`. ⚠️ 018 의 초안이 같은 자리에서 `review` 를 빠뜨렸고 그 조회가 그것을 잡았다 — 같은 절차를
-- 그대로 밟았다.
--
-- ⚠️ **`purpose` 값은 job 종류 이름과 같게 둔다** — `analysis_jobs.job_type` 의 값(`generate_scenario`·
-- `summarize_session`)을 그대로 쓴다. 다른 이름을 발명하면 두 표를 조인해 읽는 사람이 매핑을 외워야
-- 한다. ⛔ 그렇다고 `job_type` 을 FK 로 걸지 않는다: `purpose` 는 **job 경로 밖 호출까지** 담는 것이
-- 이 표의 존재 이유이고(013 주석) `spike`·`nova` 가 그 증거다.
--
-- 되돌리기: 이 CHECK 를 013 의 넷으로 되돌린다. ⛔ 그 전에 새 값을 쓰는 행을 지워야 한다 —
-- 남아 있으면 CHECK 복원이 실패한다.

alter table llm_calls
  drop constraint llm_calls_purpose_check;

alter table llm_calls
  add constraint llm_calls_purpose_check
  check (
    purpose in (
      'plan',
      'analysis',
      'spike',
      'nova',
      'generate_scenario',
      'summarize_session'
    )
  );
