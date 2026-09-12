-- 014_pronunciation_session_mode.sql
-- `learning_sessions.mode` 값역에 `pronunciation` 을 더한다.
-- 결정: docs/ops/captain-instruction-register.md 「결정 67」(2026-09-12 · 사용자가 후보 둘 중
--   「값역을 늘림」을 골랐다. 기각한 안은 「늘리지 않고 집계 문서에 명시」임)
-- 소유 태스크: TASK-112
--
-- 번호: 013 과 같은 턴에 발급했음(`schema_migrations` 최대가 012 였음 · `H-AL`).
--
-- 무엇이 걸려 있었나: `TASK-10.1` 이 발음 전용 모드를 «지시문만» 바꾸는 방식으로 넣어 세션 행의
-- `mode` 가 `speaking` 으로 남았음 — 001 의 CHECK 값역에 그 값이 없었기 때문임. 대가는 결과
-- 화면·집계·일일 완료 판정이 발음 세션을 «말하기»로 세는 것이었음.
--
-- ⚠️ 값역 «확장» 이므로 기존 행 전부가 새 CHECK 를 만족함 — 검증 실패로 막힐 행이 없음.
-- 그래서 data-first 규약 §2 의 위험 형태에 들지 않음.
-- ⛔ 되돌리기는 역순(`pronunciation` 을 뺀 CHECK 로 되돌리기)이지만, 그 값으로 기록된 세션 행이
-- 하나라도 있으면 **되돌릴 수 없음**. 되돌릴 것이면 그 행들을 어떻게 셀지 먼저 정해야 함.
--
-- ⛔ 모드 리터럴의 소유자는 결정 11 이 `TASK-27` 로 지목했음 — 이 파일은 그 소유를 옮기지 않고
-- 값역 한 칸만 엶. 값역 목록을 코드에 복제하지 않는 기존 규약(`services/sessions.py`
-- `create_session` docstring · `api/ws.py:67` 주석)도 그대로 유지함.

alter table learning_sessions drop constraint learning_sessions_mode_check;

alter table learning_sessions
  add constraint learning_sessions_mode_check
  check (mode in ('speaking', 'shadowing', 'review', 'pronunciation'));
