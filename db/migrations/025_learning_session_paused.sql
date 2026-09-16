-- 025_learning_session_paused.sql
-- 「일시 정지」의 상태 — `learning_sessions.status` 값역에 `paused` 하나를 더한다
-- 캡틴 결정: 115(025 발급·적용 승인) · 117(「학습 계속」은 **같은 세션을 그대로 잇는다**)
-- 소유 태스크: TASK-61.9(일시 정지) · TASK-61.11(학습 계속) — 결정 117 이 둘을 한 기능으로 묶었다
--
-- 번호: `ls db/migrations/` 실측 최대가 024 이므로 025 다(2026-09-16 에 쓰는 턴에 조회했다).
-- ⛔ `002`·`008` 은 영구 결번이다(결정 27).
-- ⛔ 소비자와 같은 커밋 흐름으로 나간다 — 011 이 세운 data-first 규약이다.
--
-- ⛔ **왜 새 값이 필요한가.** 「잠깐 멈춤」이 관측 가능해야 한다: 정지 중에 도착한 학습 발화를
-- 저장하지 않는 것이 이 기능의 계약인데, 그 판정을 메모리에만 두면 **프로세스가 죽은 뒤 그 세션이
-- 무엇이었는지 아무도 모른다.** 상태가 행에 남아야 리퍼가 그것을 걷을 수 있다(아래 ⚠️ 둘째).
--
-- ⛔ **`services/utterances.ENDED_SESSION_STATUSES` 에 이 값을 더하지 않는다.** 그 목록은
-- `SessionEndStatus`(= `completed`·`failed`)에서 나오는 **허용 목록**이고, 회복 스윕이 그것으로
-- 「끝난 세션」을 고른다. `paused` 를 더하면 **아직 자라는 중인 마지막 묶음이 분석에 걸려** I-1
-- 결함이 되살아난다. 허용 목록이라 **더하지 않는 것만으로** 안전하다 — 이 마이그레이션이 그 사실에
-- 의존한다(2026-09-16 에 그 코드를 직접 읽어 확인했다).
--
-- ⚠️ **리퍼는 함께 고쳐야 한다.** `services/sessions.reap_orphan_sessions` 는 `active` 만 닫으므로
-- 크래시로 남은 `paused` 세션이 **영구히 남는다**(스윕도 그것을 끝난 세션으로 보지 않으므로 분석이
-- 걸리지 않는다). 그래서 같은 커밋이 리퍼의 대상에 `paused` 를 더한다.
--
-- ⚠️ **되돌리기**: 값역을 좁히려면 `paused` 행이 0건인 것을 먼저 확인해야 한다 — 정지 중인 세션이
-- 남아 있으면 CHECK 가 실패한다. 그 조회를 먼저 돌린다.

alter table learning_sessions drop constraint learning_sessions_status_check;

alter table learning_sessions
  add constraint learning_sessions_status_check
  check (status in ('active', 'paused', 'completed', 'failed'));
