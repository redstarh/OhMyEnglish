-- 024_pronunciation_signal_from_transcript_analysis.sql
-- 발음 기원 오류의 기록 경로 — `signal_source` 값역에 값 하나를 더한다
-- 설계: `TASK-88` 노트(구현 설계) ·
--       docs/design/2026-09-10-pronunciation-origin-error-attribution.md
-- 캡틴 결정: 93(024 발급 승인) · 92 ①(발음 기원 오류를 버리지 않는다) ·
--            94(기록만 남기고 복습 과제는 만들지 않는다 — 92 ②를 뒤집었다)
-- 소유 태스크: TASK-88
--
-- 번호: `ls db/migrations/` 실측 최대가 023 이므로 024 다(2026-09-14 에 쓰는 턴에 조회했다).
-- ⛔ `002`·`008` 은 영구 결번이다(결정 27).
-- ⛔ 소비자와 같은 커밋 흐름으로 나간다 — 011 이 세운 data-first 규약이다.
--
-- ⛔ **왜 이것이 020 의 기각과 어긋나지 않는가.** 020(21~24행)은 「그 기록이 **검증됐는가**」를
-- 이 컬럼에 넣는 안을 기각했고 근거가 「**다른 축**이다」였다. 이 값은 그 컬럼의 축 그대로다 —
-- 「이 행이 **어느 신호**에서 왔는가」이고 기존 셋과 같은 종류다.
--
-- ⛔ **복습 단계 전진은 이 마이그레이션이 막지 않는다 — 이미 막혀 있다.**
-- `services/review.py` 의 이력 쿼리가 `signal_source = 'nova_tool'` **허용 목록**을 쓰므로
-- (결정 59 의 정한 것 ①) 새 값은 그대로 배제된다. ⇒ 결정 94 의 「기록만 남긴다」가
-- **추가 코드 없이** 성립한다. ⛔ **그래서 이 값을 그 허용 목록에 더하지 않는다** —
-- 더하면 결정 94 가 뒤집힌다.
--
-- ⛔ **발음 패턴도 생기지 않는다.** `_UPSERT_PRONUNCIATION_PATTERN_SQL` 이
-- `length(btrim(coalesce(a.target_sound, ''))) > 0` 을 요구하고 이 신호는 `target_sound` 를
-- 갖지 않는다 — 분석기는 오디오를 듣지 않아 어느 소리가 틀렸는지 모르고, 그것을 산출하는 안은
-- 결정 59 ③ 과 결정 54 ① 이 이미 닫았다. ⇒ 결정 62 를 뒤집지 않는다.
--
-- ⚠️ `005` 의 `pronunciation_attempts_pending_is_nova_only` 는 고치지 않는다 — 이 신호는
-- `pending` 을 쓰지 않고 `incorrect` 로 태어나므로 그 CHECK 를 그대로 통과한다.
-- ⚠️ `pronunciation_attempts_resolved_consistency` 가
-- `(outcome = 'pending') = (resolved_at is null)` 이므로 이 신호를 넣는 코드는 `resolved_at` 을
-- 채워야 한다. 그 단정은 코드 쪽 테스트가 갖는다.
--
-- 무손실이다 — 값역을 **넓히기만** 하고 기존 세 값의 행은 그대로 통과한다.

alter table pronunciation_attempts
  drop constraint pronunciation_attempts_signal_source_check;

alter table pronunciation_attempts
  add constraint pronunciation_attempts_signal_source_check
  check (
    signal_source in ('nova_tool', 'korean_transcript', 'agent_reprompt', 'transcript_analysis')
  );
