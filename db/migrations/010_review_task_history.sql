-- 010_review_task_history.sql
-- 복습 과제 히스토리 — 번호(`id`)와 상태가 재계산마다 초기화되지 않게 한다
-- 설계: docs/design/2026-09-08-review-task-history-design.md §5.3 (정본) · §2.2 자연키 · §3.3 값역
-- 캡틴 결정: docs/ops/captain-instruction-register.md — 결정 26(기존 행 삭제 승인) · 결정 27(008 영구 결번)
-- 소유 태스크: TASK-43
--
-- 번호: `ls db/migrations/` 실측이 `001 · 003 · 004 · 005 · 006 · 007 · 009`이므로 **010**이다.
-- ⚠️ **002·008은 영구 결번이다**(결정 27). 008은 주간 리포트(TASK-26)에 예약돼 있었으나
--    009·010이 먼저 나가 적용 순서가 갈라지는 것이 실측으로 확인돼 예약을 풀었다.
--    → 009가 경고한 "008이 이 표를 건드리면 실제 사고가 된다"(설계서 §5.2)는 **닫혔다.**
--    ⛔ 앞으로 번호를 미리 예약하지 않는다 — 발급은 그 마이그레이션을 실제로 쓰는 턴에 한다.
--
-- **이 마이그레이션이 고치는 병**: `recompute`가 그 패턴의 `review_tasks` 행을 **전부 지운 뒤
-- 현재 상태 1행을 넣는다**. 그래서 재계산마다 ① `id`가 새로 발급되고(화면이 과제를 가리킬 손잡이가
-- 사라진다) ② `created_at`이 배치 시각으로 덮이고 ③ 접힌 중간 단계와 끊긴 사이클이 흔적 없이
-- 사라진다. 파생값은 이력에서 다시 계산되므로 삭제가 무손실이었지만(2026-09-03 결정),
-- **`id`·`created_at`·학습자가 손으로 만든 상태에는 그 근거가 닿지 않는다**(설계서 §3.1).
--
-- ⛔⛔ **적용 절차 — 이 파일을 돌리기 전에 읽어라** (캡틴 결정 26·33 · 설계서 §5.5 · `TASK-43` AC#7)
-- 이 파일은 2번에서 **되돌릴 수 없는 `delete`** 를 한다. 그래서 순서와 제약이 있다:
--   ① **`pg_dump` 로 `review_tasks` 를 백업한다.** 백업 없이 돌리지 않는다.
--   ② 이 파일을 적용한다 (`app/backend/.venv/bin/python scripts/migrate.py`).
--   ③ **`scripts/backfill_review_state.py` 를 한 번 돌린다 — 이것이 필수다.**
--      010 은 표를 비우고 채우지 않는다. 백필을 빠뜨리면 표가 **빈 채로 남고** 각 패턴이 다시
--      발생할 때까지 채워지지 않는다("오늘 복습할 목록"이 0행으로 되돌아간다).
--   ④ **행 수와 내용이 복원됐는지 직접 확인해 출력을 태스크 노트에 남긴다**
--      (`count(*)` · `count(distinct cycle_started_at)` · status 분포).
--   ⑤ **복원되지 않으면 멈추고 캡틴에게 올린다.** 스스로 고치지 않는다.
-- ⚠️ **코드와 이 마이그레이션은 같은 커밋으로 함께 나간다.** 새 `review.py` 는 010 을 전제하므로
--    적용 전 상태에서 분석 워커가 돌면 `cycle_started_at` 컬럼이 없어 `recompute` 가 매 job 실패한다.
--    반대로 코드 없이 010 만 적용하면 옛 코드가 `cycle_started_at` 을 안 넣어 not null 위반이 난다.
-- ⚠️ 결정 33 이 정한 순서: **코드 리뷰가 CRITICAL·HIGH 0건을 낸 뒤**에 적용한다 — 리뷰가 이 파일에서
--    결함을 찾으면 지운 뒤에 고치게 되기 때문이다.
--
-- **해법은 자연키다**(설계서 §2.2): 정체성을 `(pattern_id, cycle_started_at, review_stage)`로 두면
-- 재계산이 delete+insert 대신 upsert로 **같은 행에 다시 닿을** 수 있고, 그 결과로 대리키 `id`와
-- `created_at`이 살아남는다. 사이클 판별자를 **재발 시각**으로 둔 이유(카운터가 아니라)는 §2.3 —
-- 카운터는 과거 재발 하나가 재분석으로 지워질 때 뒤의 모든 번호가 한 칸씩 밀려 남의 번호를
-- 물려받는다. 그것이 지금 고치려는 병과 같은 부류다.

-- 1. 새 컬럼 둘. `cycle_started_at`은 일단 nullable로 붙인다 — 기존 행에 줄 값이 없기 때문이고,
--    3번에서 표가 빈 뒤 not null로 올린다.
-- ⚠️ 둘 다 **이벤트 시각이므로 `timestamptz`다.** naive `timestamp`를 만들지 않는다.
--    이 표에 **달력 날짜 컬럼을 두지 않는다** — "며칠에 완주했는가"는 읽을 때
--    `users.timezone`으로 변환해 구한다(설계서 §4 Boundary). UTC 자정~09:00(KST)에
--    `current_date`가 KST 날짜보다 하루 이르기 때문이다.
alter table review_tasks
  add column cycle_started_at timestamptz,
  add column completed_at timestamptz;

-- 2. 기존 행을 지운다 — **캡틴 결정 26이 승인한 것이 정확히 이 문장이다.**
-- 무손실 근거(설계서 §5.4, 전부 직접 확인된 것): ① `review_tasks`를 읽는 앱 코드가 0곳이다
-- ② 행 전부 `status='pending'`이고 `skipped`는 0행이라 재계산이 복원할 수 없는 값이 행에 없다
-- ③ 복원 경로 `recompute_all`이 실재하고 멱등이다 ④ 복습 목록은 `error_patterns`를 읽으므로
-- 이 사이 멈추지 않는다(이 마이그레이션은 그 표를 건드리지 않는다).
-- ⚠️ **백필하는 대신 지우는 이유**: `cycle_started_at`을 SQL로 채우려면 `_HISTORY_SQL`의
--    `greatest(...)` 재발 로직을 이 파일에 복제하게 되고 두 곳이 갈라진다. `created_at` 같은
--    임의값을 넣는 것은 더 나쁘다 — 그 값은 재계산 배치 시각이라 사이클 시작이 아니고,
--    **틀린 값을 유일키에 넣는 것**이기 때문이다.
-- ⛔ **010이 "지우고 다시 만들기"가 공짜인 마지막 순간이다.** 학습자 행동 이력이 한 번 붙으면
--    같은 삭제가 되돌릴 수 없는 손실이 된다 → 010 이후의 마이그레이션은 이 표를 비우는 방식을
--    쓸 수 없다.
delete from review_tasks;

-- 3. 표가 빈 뒤이므로 무조건 성공한다. `completed_at`은 nullable로 남는다 — 열린 단계에는
--    완주 시각이 없는 것이 정상이다.
alter table review_tasks
  alter column cycle_started_at set not null;

-- 4. 유일키를 자연키로 교체한다. 옛 키 `unique (pattern_id, review_stage)`(001)로는 히스토리를
--    담을 수 없다: 같은 패턴이 재발하면 1단계가 **다시** 필요한데 그 키가 1단계를 하나만 허용한다.
-- ⚠️ **제약 이름은 실측이다** — `pg_constraint` 직접 조회로 확인했다(추측한 이름이 아니다).
alter table review_tasks
  drop constraint review_tasks_pattern_id_review_stage_key;

alter table review_tasks
  add constraint review_tasks_cycle_stage_key
  unique (pattern_id, cycle_started_at, review_stage);

-- 5. `status` 값역을 파생 전용으로 좁힌다(설계서 §3.3).
--    `pending` 열린 단계 · `done` **이 단계를** 접었다 · `abandoned` 접기 전에 재발이 와서 사이클이
--    끊겼다 · `superseded` 이 행의 근거가 이력에서 사라졌다(재분석 — 화면에서 감춘다).
-- ⚠️ **`done`의 뜻이 바뀐다**: 「사이클 완주」에서 「단계 완주」로. 옛 뜻을 박고 있던
--    `docs/database-schema.md`와 테스트를 같은 커밋에서 함께 고친다(설계서 §6).
-- ⛔ **`skipped`를 뺀다 — 이것이 이 설계의 집행 장치다.** 지금 그 값을 쓰는 코드는 0곳이고
--    dev DB에도 0행이다. 남겨 두면 `TASK-3`(학습 히스토리 화면) 구현자가
--    `update review_tasks set status='skipped'`를 쓰는 것이 **컬럼 이름과 문서를 따르는 정상
--    행동**이고, 그 값은 재계산이 소유한 칸에 있으므로 다음 재계산에 조용히 사라진다.
--    값역에서 막으면 그 시도가 **CHECK 위반으로 즉시 실패**해 학습자 행동을 둘 자리를
--    의도적으로 만들게 된다. 009가 같은 판단을 했다 — "docstring은 그 함수를 읽을 이유가 없는
--    사람을 구속하지 못한다. 스키마는 구속한다."
-- ⚠️ 학습자 행동 표를 **지금 만들지 않는다**(설계서 §3.3): 006이 `suggested_contexts`를 미리 만든
--    근거는 "지금 저장하지 않으면 소급이 불가능하다"였고 **그때 데이터가 흐르고 있었다.**
--    학습자 건너뛰기는 지금 흐르지 않는다(UI가 없다). 값역을 발명해 writer 없는 빈 표를 만드는
--    대신 CHECK로 막고, 실제 행동이 정해지는 `TASK-3`에서 만든다.
alter table review_tasks
  drop constraint review_tasks_status_check;

alter table review_tasks
  add constraint review_tasks_status_check
  check (status in ('pending', 'done', 'abandoned', 'superseded'));

-- 6. 불변조건 ②: `done`이면 완주 시각이 있다.
-- ⚠️ **동치가 아니라 함의다**(설계서 §4 Contract). 역방향(`completed_at is not null` → `done`)을
--    강제하지 않는 이유: `superseded`로 내려간 행이 완주 시각을 그대로 들고 있어야
--    "우리가 그때 무엇을 믿었는지"가 남는다. 동치로 걸면 은퇴시킬 때 그 시각을 지워야 한다.
alter table review_tasks
  add constraint review_tasks_done_has_completed_at
  check (status <> 'done' or completed_at is not null);

-- 7. `idx_review_tasks_due`(001, `(status, due_at)`)는 **그대로 둔다.** 읽는 코드가 0곳이라
--    지금 인덱스를 발명하지 않는다 — `abandoned`·`superseded`가 이 인덱스에 섞이지만,
--    조회가 생길 때 그 조회의 모양을 보고 정한다(설계서 §5.3-7).
