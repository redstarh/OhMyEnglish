"""복습 스케줄의 소유자 — 재발화 판정 기록과 복습 상태 재계산 (설계서 §4.1·§8.1).

`next_review_at`에 값을 넣는 코드는 이 모듈뿐이다. 세션·워커는 배선만 한다.

**단계를 증분하지 않고 이력에서 다시 접는다.** 이 모듈에서 이것 하나만 기억하면 된다.
`analyze_utterance` job은 재시도되고 결과 저장은 발화 단위 replace라서, `stage + 1`로
전이시키면 재실행마다 단계가 올라가 학습자가 하지 않은 복습이 완주된다. 그래서 상태를
**이력에서** 매번 다시 계산한다 — `frequency`를 `+1`하지 않고 행 수에서 다시 세는 것
(`services/analysis.py`)과 같은 규약이고, 같은 이유다.

**⚠️ 이력의 출처는 하나가 아니다 — 카테고리가 고른다** (`TASK-44`, 설계서
`2026-09-08-pronunciation-review-cycle-design.md` §5.2). `recompute`가 패턴의 `category`를
먼저 읽는다:

* `pronunciation_intonation` → `_PRONUNCIATION_HISTORY_SQL`
  (표 `pronunciation_attempts` · 앵커 **`resolved_at`**)
* 그 외 → `_HISTORY_SQL`
  (표 `error_occurrences` + `pattern_attempts` · 앵커 **발화 시각** `utterances.created_at`)

그 뒤는 **완전히 공유한다**(`fold_stages` → `_APPLY_PATTERN_SQL` → `review_tasks`) — 두 쿼리가
**같은 세 값**(`relapse_at`·`scenario_context`·`correct_times`)을 같은 의미로 돌려주는 것이
그 공유의 전제조건이다. ⛔ **한쪽만 고치지 마라.**

**그리고 정답 횟수를 세지 않는다 — 예정일을 하나씩 접는다.** §4.1의 "복습을 완주하면 다음
단계로 진행한다"는 그 단계의 예정일이 온 뒤에 다시 맞혔다는 뜻이고, 복습 목록의 판정도
`next_review_at <= clock_timestamp()`다. 단순히 correct를 3번 세면 같은 세션에서 세 번
맞히는 것으로 1·3·7일을 한 번도 경과하지 않고 완주해 간격 반복이 무의미해진다.
`fold_stages`가 그 조건을 담고, **순수 함수**라 DB 없이 검증된다.

**시각의 기준은 벽시계가 아니라 기록된 시각이다.** `now()`를 기준으로 쓰면 재실행마다
예정일이 밀려 멱등이 깨진다. **어느 기록된 시각인지는 위 표가 정한다** — 문법은 발화 시각,
발음은 `resolved_at`이다. 발음이 다른 이유: 문법 쪽 앵커가 발화 시각인 것은
`analyze_utterance` job이 재시도되고 결과가 발화 단위 replace라서인데 **발음 시도 행에는 그
이유가 없다**(웹소켓 이벤트에서 한 번 쓰이고 다시 계산되지 않으므로 `resolved_at`이 그 한 번에
확정된다). `docs/database-schema.md`가 이미 그렇게 정해 뒀다 — 새 경계가 아니다.

간격 연산은 `timedelta`라 타임존과 무관하다 — 달력 날짜를 쓰는 곳은 이 모듈에 없다
(만성 지표의 "재발 일수"가 그 경계를 갖고 `services/chronic.py`가 소유한다).

**`review_tasks`는 이력이다 — 지우지 않고 자연키로 upsert한다** (`TASK-43`, 마이그레이션 010,
설계서 `2026-09-08-review-task-history-design.md` §2.2). 정체성은
`(pattern_id, cycle_started_at, review_stage)`이고 재계산이 같은 사실에 같은 행으로 닿는다.

⛔ **뒤집힌 규약이다.** 이전 판은 "패턴당 0행 또는 1행이고 재계산은 그 패턴의 행을 전부 지운 뒤
현재 상태 1행을 넣는다"였다(캡틴 결정 2026-09-03). **그 결정의 근거는 파생값에 대해서는 지금도
참이다** — 완주·재발 여부는 `pattern_attempts`·`error_occurrences`에서 언제든 다시 계산된다.
바뀐 것은 그 근거가 **닿지 않는 값 세 개**를 분리했다는 것이다: `id`(화면·API가 과제를 가리키는
손잡이) · `created_at` · 학습자가 손으로 만든 상태. 삭제하면 이 셋이 매번 새로 발급되거나
사라진다 — 접힌 중간 단계와 끊긴 사이클도 흔적 없이 사라져 히스토리 화면을 그릴 근거가 없다.

`recompute`의 사후조건: **현재 사이클 행은 사다리와 정확히 일치하고, 과거 사이클 행은 파생값이
덮이지 않는다.** 과거 사이클에서 종료 상태를 못 받은 `pending` 행 하나만 `abandoned`로 내려가고
(재발이 그 사이클을 끊었다는 사실이 히스토리의 "여기서 끊겼다"다), 근거가 이력에서 사라진 행은
`superseded`로 은퇴한다 — **지우지 않는다**(미래에 그 행에 붙을 학습자 이력을 cascade로 날리지
않기 위해). 값역과 각 상태의 뜻은 010과 `docs/database-schema.md`가 정본이다.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.models.analysis import PRONUNCIATION_CATEGORY, PatternAttempt

logger = logging.getLogger(__name__)

# 복습 주기 1·3·7일 3단계. **문서로 확정된 값이다** (설계서 §4.1 "1일 → 3일 → 7일",
# `docs/database-schema.md`) — 발명값이 아니다. 완주까지 최소 11일이 실제로 경과한다.
STAGE_DAYS: tuple[int, ...] = (1, 3, 7)
FINAL_STAGE: int = len(STAGE_DAYS)

# mastery_score는 점수가 아니라 **상태 마커**다 (캡틴 결정 2026-09-03): 3단계를 재발 없이
# 완주했는지만 담는다. 중간값을 만들지 않는 이유는 설계서 §3.2 — 임계값을 발명하지 않는다.
# 재발로 100 → 0이 되어도 정보를 잃지 않는다: 완주 이력은 `pattern_attempts`에 그대로 남아
# "3단계 소진 후 재발"(§6.2의 결정론적 만성 신호)을 언제든 다시 계산할 수 있다.
MASTERED = Decimal("100")
NOT_MASTERED = Decimal("0")

# 슬라이스 1은 무엇도 생성하지 않으므로(§3.2의 경계) 과제 유형은 "다시 말해보기" 하나다.
# 슬라이스 2가 Claude 산출 상황(`suggested_contexts`)으로 이 자리를 넓힌다.
REVIEW_TASK_TYPE = "rephrase"

_DELETE_ATTEMPTS_SQL = """
delete from pattern_attempts where utterance_id = $1 returning pattern_id
"""

# pattern_key → pattern_id 해석을 insert 안에서 한다: 목록에 없는 key는 select가 0행을
# 돌려주어 **행이 생기지 않는다**. 별도 조회 없이 "조용히 버린다"가 성립한다.
_INSERT_ATTEMPT_SQL = """
insert into pattern_attempts (pattern_id, utterance_id, outcome)
select p.id, $2, $3
  from error_patterns p
 where p.user_id = $1 and p.pattern_key = $4
returning pattern_id
"""

# 접기에 필요한 이력만 읽는다. 단계 전이는 파이썬(`fold_stages`)이 한다 — 각 단계의 통과
# 시각이 다음 단계의 기준이 되는 **연쇄**라서 집계 함수로 표현되지 않는다(재귀 CTE 회피).
#
# `greatest`는 NULL 인자를 건너뛴다(Postgres 의미론, 2026-09-03 실측) — 그래서 occurrence만
# 있거나 incorrect만 있는 경우가 분기 없이 처리된다.
# `u.created_at > r.at`의 strict `>`는 **관측 가능한 효과가 없다 — 중복 방어다**(2026-09-04
# 실측: `>=`로 바꿔도 전체 스위트가 통과한다). 이유: 재발과 같은 순간의 정답은 `anchor`와
# 시각이 같으므로 `fold_stages`의 간격 조건(`said_at < anchor + STAGE_DAYS[0]`)이 어차피
# 건너뛴다. **실제 방벽은 fold의 간격 조건 하나다** — 여기를 고치기 전에 그쪽을 본다.
# 그래도 `>`를 남기는 이유는 SQL만 읽는 사람에게 "재발 이후"라는 의도를 보이기 위해서다.
# `order by`를 지우지 말 것 — `fold_stages`의 전제조건이 오름차순이고, 순서가 흐트러지면
# 단계가 조용히 틀린다(예외도 실패도 없이).
_HISTORY_SQL = """
with relapse as (
      select greatest(
               (select max(u.created_at)
                  from error_occurrences eo
                  join utterances u on u.id = eo.utterance_id
                 where eo.pattern_id = $1),
               (select max(u.created_at)
                  from pattern_attempts pa
                  join utterances u on u.id = pa.utterance_id
                 where pa.pattern_id = $1 and pa.outcome = 'incorrect')
             ) as at
),
context as (
      select coalesce(
               (select eo.original_span
                  from error_occurrences eo
                  join utterances u on u.id = eo.utterance_id
                 where eo.pattern_id = $1
                 order by u.created_at desc, eo.id desc
                 limit 1),
               (select target_form from error_patterns where id = $1)
             ) as scenario_context
)
select r.at as relapse_at,
       ctx.scenario_context,
       coalesce(
         (select array_agg(u.created_at order by u.created_at, pa.id)
            from pattern_attempts pa
            join utterances u on u.id = pa.utterance_id
           where pa.pattern_id = $1
             and pa.outcome = 'correct'
             -- `r.at is null or`도 관측 불가능하다: relapse가 없으면 `fold_stages`가
             -- `correct_times`를 **읽기 전에** return하므로 이 배열이 무엇이든 결과가 같다.
             -- 남기는 이유는 SQL 단독으로도 의미가 통하게 하는 것이다(`> null`은 0행이 된다).
             and (r.at is null or u.created_at > r.at)),
         '{}'::timestamptz[]
       ) as correct_times
  from relapse r, context ctx
"""

# 발음 패턴 하나의 이력 (설계서 `2026-09-08-pronunciation-review-cycle-design.md` §5.3).
# 위 `_HISTORY_SQL`과 **같은 세 값**을 돌려준다 — 그래서 그 뒤 경로(`fold_stages` →
# `_APPLY_PATTERN_SQL` → `review_tasks`)를 손대지 않고 공유한다.
#
# ⚠️ **`pattern_id`로 잇지 않는다.** `correct` 시도의 `pattern_id`는 영원히 null이다
# (`pronunciation.py`의 upsert가 `outcome = 'incorrect'`로 거른다) → 그것으로 이으면 단계가
# 영원히 오르지 않는다. 대신 `btrim(target_sound)`로 잇고, 그 값이 발음 패턴의 `target_form`과
# 같은 것은 같은 upsert가 보장한다(conflict에서도 같은 값을 다시 쓴다).
# `'pronunciation_' || …` 접두사 리터럴을 두 번째 장소에 복사하지 않기 위해 `pattern_key`가
# 아니라 `target_form`으로 잇는다.
#
# ⚠️ **앵커는 `resolved_at`이다 — `utterances.created_at`이 아니다**(§3.3). 문법 경로가 발화
# 시각을 쓰는 이유는 `analyze_utterance` job이 재시도되고 결과가 발화 단위 replace라 벽시계를
# 쓰면 재실행마다 예정일이 밀리는 것인데, **발음 경로에는 그 이유가 없다** — 시도 행은 웹소켓
# 이벤트에서 한 번 쓰이고 다시 계산되지 않는다. `docs/database-schema.md`가 이미 "발음 경로는
# 시도의 판정 시각"이라고 정해 두었다. `utterance_id`를 쓰지 않는 두 번째 이유: 그 컬럼은
# `on delete set null`이라 join하면 발화가 지워진 판정 기록이 **조용히 사라진다**.
#
# `resolved_at is not null`이 `pending`을 뺀다(004 CHECK가 `pending` ⟺ `resolved_at is null`).
# `unclear`는 outcome 필터 둘 어디에도 안 걸려 자동으로 빠진다 — 판정할 수 없는 발화를
# `incorrect`로 강제하면 숙련도가 부당하게 깎인다. `target_sound`가 null인 행도 자동으로
# 빠진다(`btrim(null) = x`가 null이라 조건이 참이 되지 않는다) — 소리를 못 짚은 행이라 어느
# 패턴의 것인지 정의되지 않는다.
_PRONUNCIATION_HISTORY_SQL = """
with pattern as (
      select user_id, btrim(target_form) as sound from error_patterns where id = $1
),
sound_attempts as (
      select a.id, a.outcome, a.resolved_at, a.target_form
        from pronunciation_attempts a
        join learning_sessions s on s.id = a.session_id
        join pattern p on p.user_id = s.user_id
       where a.resolved_at is not null
         and a.signal_source = 'nova_tool'
         and btrim(a.target_sound) = p.sound
),
relapse as (
      select max(resolved_at) as at from sound_attempts where outcome = 'incorrect'
),
context as (
      -- 연습할 것은 **시범 문장**이다. 소리 키(`an_as_a`)를 넣으면 1차수 F-2와 같은 부류의
      -- 오류다(카드의 두 값이 서로 다른 것을 가리킨다). coalesce의 두 번째 항은 시도가
      -- 사라진 패턴을 위한 방어이고, 그때만 소리 키가 쓰인다.
      select coalesce(
               (select target_form
                  from sound_attempts
                 where outcome = 'incorrect'
                 order by resolved_at desc, id desc
                 limit 1),
               (select sound from pattern)
             ) as scenario_context
)
-- ⛔ `signal_source = 'nova_tool'` 이 **보조 신호를 단계 전진에서 배제한다** (위 `sound_attempts`).
-- 사용자 판정 2026-09-11 · `TASK-74` · 캡틴 지시 대장 결정 59. **이전 판은 이 필터를 두지 않았고
-- 그 이유를 「설계가 정하지 않은 동작을 발명하지 않는다」로 적어 두었다** — 그 판단이 이 판정으로
-- 뒤집혔다. 뒤집은 근거: 한글 전사는 「학습자가 어느 소리를 틀렸다」가 아니라 「ASR 이 언어 판별을
-- 뒤집었다」는 관측이라 소리를 지목하지 못하므로 복습 단계를 전진시킬 자격이 없다. 같은 축의
-- 원칙을 결정 54 ①이 먼저 정했다 — 틀린 기록으로 시계를 돌리면 **엉뚱한 소리에** 걸린다.
--
-- ⚠️ **필터가 없어도 지금은 도달 불가였다. 그것이 필터를 넣은 이유다** — 도달 불가의 근거가
-- 전부 호출자 쪽 관례(유일한 생산자 `note_transcript`가 `unclear` + `target_sound=None`만 낸다)
-- 여서 이 쿼리 자체에는 방어가 0이었다. `AssistOutcome`(`pronunciation.py`)의 타입 잠금은 절반만
-- 막는다 — `incorrect`는 값역에 없지만 **`correct`는 허용된다.** 새 생산자가 `outcome='correct'`
-- + `target_sound`를 주는 순간 학습자가 다시 말하지 않았는데 단계가 접히고, `record_signal`이
-- `refresh_review`를 부르지 않으므로(§5.5 가 두 진입점만 배선했다) **나중에 조용히** 반영돼
-- 진단이 더 어렵다. 이제 그 경로가 쿼리에서 닫힌다.
--
-- **허용 목록으로 쓴다(`= 'nova_tool'`)** — `signal_source` 값역에 값이 늘면 새 값은 **기본으로
-- 배제**된다. 배제 목록(`not in (…)`)으로 쓰면 값을 더할 때마다 이 줄을 같이 고쳐야 하고 그것을
-- 빠뜨리는 것이 원래 결함의 모양이다.
--
-- ⚠️ 이 필터는 relapse 쪽(`outcome='incorrect'`)에도 걸리는데 **가리는 것이 없다**: 보조 신호는
-- `incorrect`가 될 수 없고(같은 타입 잠금) `resolve_dangling`의 수렴 대상도 아니다
-- (`record_signal`이 행을 이미 판정된 상태로 만든다).
--
-- ✅ 「그 감지기를 만드는 태스크가 이 줄을 함께 판정한다」는 요구가 **이 판정으로 해소됐다.**
-- 그 요구가 지목했던 소유자 `TASK-24`는 `agent_reprompt`를 **만들지 않는다**로 2026-09-09 에
-- 실측 판정하고 닫혔다(감지할 되묻기 문구가 사각 3턴 전부에 없었다) — 즉 그 감지기는 계획에 없다.
select r.at as relapse_at,
       ctx.scenario_context,
       coalesce(
         (select array_agg(sa.resolved_at order by sa.resolved_at, sa.id)
            from sound_attempts sa
           where sa.outcome = 'correct'
             -- `_HISTORY_SQL`과 같은 이유로 `r.at is null or`를 남긴다: relapse가 없으면
             -- `fold_stages`가 이 배열을 읽기 전에 return하므로 관측 불가능하지만, SQL
             -- 단독으로도 의미가 통해야 한다(`> null`은 0행이 된다).
             and (r.at is null or sa.resolved_at > r.at)),
         '{}'::timestamptz[]
       ) as correct_times
  from relapse r, context ctx
"""

# 이력 쿼리를 고르기 위해 카테고리를 먼저 읽는다 (설계서 §5.2).
# **분기를 호출자에 두지 않는 이유**: 두 곳에 두면 한쪽이 조용히 낡고, 발음 패턴에 문법 모양의
# 상태가 계산되는 조합이 생긴다. 여기 한 곳에 두면 `analysis.py`의 호출부도 백필
# (`recompute_all`)도 시그니처가 그대로다.
_PATTERN_CATEGORY_SQL = "select category from error_patterns where id = $1"

_APPLY_PATTERN_SQL = """
update error_patterns set next_review_at = $2, mastery_score = $3 where id = $1
"""

# 설계서 §4.1의 "오늘 다뤄야 하는 목록". **`clock_timestamp()`를 쓴다** — Postgres `now()`는
# 트랜잭션 시작 시각에 고정되므로 시간 기반 판정이 무력화된다(Phase 1 §5.4 실측).
# `order by`가 가장 밀린 것을 앞에 놓는다: 연체는 무효가 아니라 더 시급한 것이다.
_DUE_REVIEWS_SQL = """
select p.id as pattern_id, p.pattern_key, p.category, p.target_form,
       p.next_review_at, p.mastery_score
  from error_patterns p
 where p.user_id = $1
   and p.next_review_at is not null
   and p.next_review_at <= clock_timestamp()
 order by p.next_review_at
"""

# 백필 대상. 이력에서만 계산하므로 **전체를 훑는 것이 안전하고 멱등이다**.
_ALL_PATTERNS_SQL = "select id from error_patterns where user_id = $1 order by pattern_key"

# 사다리 한 칸을 쓴다. **conflict target이 자연키라 재실행이 같은 행에 다시 닿는다** — 그것이
# `id`·`created_at`이 살아남는 기전 전부다(설계서 §2.2). 010이 그 유일키를 만든다.
#
# ⚠️ **`scenario_context`는 `pending` 행에서만 갱신한다** (설계서 §7 약점 3의 완화). 지금 값은
# 재계산 시점의 **최신** occurrence 원문이므로(`_HISTORY_SQL`의 `context` CTE), 그냥 덮으면
# 1단계 행의 연습 문구가 나중 오류의 원문으로 바뀌어 "그때 무엇으로 연습했는가"가 틀어진다.
# 판정 기준은 **기존 행의** 상태다(`review_tasks.status`, `excluded`가 아니다) — 이미 종료된
# 행을 동결하는 것이 목적이므로 새로 쓰려는 상태를 보면 안 된다.
# ⛔ 완화일 뿐 해결이 아니다: **열린 행의 문맥은 여전히 바뀐다.**
#
# `task_type`은 `do update`에 넣지 않는다 — 유형이 바뀌는 경로가 없고, 넣으면 미래에 유형을
# 손으로 바꾼 행을 재계산이 되돌린다.
_UPSERT_TASK_SQL = """
insert into review_tasks (pattern_id, task_type, scenario_context, cycle_started_at,
                          review_stage, due_at, status, completed_at)
values ($1, $2, $3, $4, $5, $6, $7, $8)
on conflict (pattern_id, cycle_started_at, review_stage) do update
   set status           = excluded.status,
       completed_at     = excluded.completed_at,
       due_at           = excluded.due_at,
       scenario_context = case
                            when review_tasks.status = 'pending' then excluded.scenario_context
                            else review_tasks.scenario_context
                          end
"""

# 근거가 이력에서 사라진 행을 은퇴시킨다 — **지우지 않는다**(설계서 §4 Failure).
# 둘을 한 문장으로 잡는다: ① 현재 사이클보다 **뒤에** 시작한 행 = 재분석이 그 재발을 지웠다
# ② 같은 사이클인데 사다리 길이를 **넘는** 단계 행 = 정답 attempt가 재분석으로 사라져 사다리가
# 짧아졌다. 판정이 시각·정수 비교뿐이라 결정론적이다.
# `status <> 'superseded'`는 이미 은퇴한 행을 다시 쓰지 않게 해 멱등을 값 수준에서 지킨다.
_SUPERSEDE_TASKS_SQL = """
update review_tasks
   set status = 'superseded'
 where pattern_id = $1
   and status <> 'superseded'
   and (cycle_started_at > $2 or (cycle_started_at = $2 and review_stage > $3))
"""

# 재발이 이전 사이클을 끊었다. 그 사이클의 **열린** 행만 내린다 — `done`은 실제로 접힌 단계라
# 그대로 살고, 그것이 히스토리가 "1·2단계는 했고 3단계에서 끊겼다"를 그릴 근거다.
# ⚠️ 이 전이가 §4 Contract의 "과거 사이클 행은 건드리지 않는다"와 문자대로는 부딪힌다.
# 채택한 읽기: **파생값(due_at·completed_at·문맥)은 덮지 않고, 종료 상태를 못 받은 행에
# 종료 상태만 준다.** 근거는 같은 §4 Failure가 이 전이의 목적을 명시한 것이다 — 그것이 없으면
# 이 설계가 고치려는 병(끊긴 사이클이 흔적 없이 사라진다)이 그대로 남는다.
_ABANDON_TASKS_SQL = """
update review_tasks
   set status = 'abandoned'
 where pattern_id = $1
   and status = 'pending'
   and cycle_started_at < $2
"""

# 재발 자체가 사라진 경우(재분석으로 occurrence·incorrect가 전부 지워졌다) — 현재 사이클이
# 없으므로 **모든** 행이 근거를 잃는다. `_SUPERSEDE_TASKS_SQL`은 기준 시각이 필요해 쓸 수 없다.
_SUPERSEDE_ALL_TASKS_SQL = """
update review_tasks
   set status = 'superseded'
 where pattern_id = $1
   and status <> 'superseded'
"""


@dataclass(frozen=True, slots=True)
class ReviewStageRow:
    """사다리 한 칸 — 한 사이클 안의 단계 하나 (`TASK-43`, 설계서 §3.2).

    `due_at`은 **그 단계를 촉발한 시각 + `STAGE_DAYS[stage-1]`**이고, `completed_at`은 그 단계를
    접은 정답의 시각이다(열린 단계는 `None`). 촉발 시각은 1단계에서는 재발 시각이고 그 뒤로는
    앞 단계를 접은 정답의 시각이다 — 즉 사다리는 **연쇄**다.
    """

    stage: int
    due_at: datetime
    completed_at: datetime | None


@dataclass(frozen=True, slots=True)
class ReviewState:
    """패턴 하나의 복습 상태 — 이력에서 계산된 파생물이고 그 자체로는 저장되지 않는다."""

    stage: int
    completed: bool
    next_review_at: datetime | None
    anchor: datetime | None
    scenario_context: str
    # 이 사다리를 연 재발 시각. `review_tasks`의 자연키 한 칸이고 `anchor`와 **겸용하지 않는다** —
    # `anchor`는 현재 단계의 기준이라 단계가 오를 때마다 이동하지만 이것은 사이클 내내 고정이다
    # (설계서 §3.2가 겸용을 명시적으로 금지한다). 재발이 없으면 사이클이 없으므로 `None`이다.
    cycle_started_at: datetime | None
    # 1단계부터 도달한 단계까지의 사다리. 완주 사이클은 3칸(전부 `completed_at` 있음), 진행 중은
    # 접힌 칸들 + 열린 칸 1개다. 재발이 없으면 빈 튜플이다.
    ladder: tuple[ReviewStageRow, ...]


def fold_stages(
    relapse_at: datetime | None, correct_times: list[datetime], scenario_context: str
) -> ReviewState:
    """마지막 재발 이후의 정답들을 훑어 **예정일을 넘긴 것만** 단계로 센다 (순수 함수).

    ⛔ **`correct_times`는 오름차순이어야 한다 — 이것이 이 함수의 전제조건이고, 어긋나면
    예외도 실패도 없이 단계가 조용히 틀린다.** 생산자는 **둘**이고 각자 자기 `order by`로 그
    순서를 만든다: `_HISTORY_SQL`(발화 시각 `u.created_at`) · `_PRONUNCIATION_HISTORY_SQL`
    (`resolved_at` — 발음은 앵커가 다르다, 모듈 docstring의 표 참조). **어느 쪽의 `order by`도
    「중복」이 아니다.** 이 함수는 시각의 출처를 모르고 알 필요도 없다 — 순수 함수라 표가
    무엇이든 상관없는 것이 재사용의 근거다.
    예정일 전의 정답은 건너뛴다: 기록(`pattern_attempts`)에는 남고 단계만 올리지 않는다.
    한 세션에서 여러 번 맞히는 것으로 1·3·7일을 건너뛰는 경로를 막는 것이 이 조건이다.
    반대로 예정일을 **한참 지나** 맞힌 것은 그대로 통과시킨다 — "너무 늦은 복습"의 상한을
    발명하지 않는다(§3.2). 늦게 맞히는 쪽이 더 어려운 조건이라 약한 증거일 이유도 없다.

    `relapse_at`이 없으면 틀린 적이 없는 패턴이므로 복습할 것이 없다 — 재분석으로
    occurrence가 전부 지워진 패턴도 이 경로로 목록에서 빠진다.
    """
    if relapse_at is None:
        return ReviewState(
            stage=1,
            completed=False,
            next_review_at=None,
            anchor=None,
            scenario_context=scenario_context,
            cycle_started_at=None,
            ladder=(),
        )

    anchor = relapse_at
    stage = 1
    ladder: list[ReviewStageRow] = []
    for said_at in correct_times:
        due_at = anchor + timedelta(days=STAGE_DAYS[stage - 1])
        if said_at < due_at:
            continue  # 예정일 전 — 간격이 경과하지 않았다
        # 이 칸을 접는다. `due_at`은 **이동 전** 앵커에서 계산한 값이어야 한다 — 접은 시각으로
        # 다시 재면 그 단계의 예정일이 아니라 다음 단계의 기준이 된다.
        ladder.append(ReviewStageRow(stage=stage, due_at=due_at, completed_at=said_at))
        anchor = said_at
        stage += 1
        if stage > FINAL_STAGE:
            return ReviewState(
                stage=FINAL_STAGE,
                completed=True,
                next_review_at=None,
                anchor=anchor,
                scenario_context=scenario_context,
                cycle_started_at=relapse_at,
                ladder=tuple(ladder),
            )
    # 열린 칸 하나를 얹는다. 그 예정일이 곧 `next_review_at`이라 두 값이 갈라질 수 없다.
    next_review_at = anchor + timedelta(days=STAGE_DAYS[stage - 1])
    ladder.append(ReviewStageRow(stage=stage, due_at=next_review_at, completed_at=None))
    return ReviewState(
        stage=stage,
        completed=False,
        next_review_at=next_review_at,
        anchor=anchor,
        scenario_context=scenario_context,
        cycle_started_at=relapse_at,
        ladder=tuple(ladder),
    )


async def store_attempts(
    conn: asyncpg.Connection,
    utterance_id: UUID,
    user_id: UUID,
    attempts: list[PatternAttempt],
) -> set[UUID]:
    """이 발화의 재시도 판정을 **replace 저장**하고 건드린 패턴 id 집합을 돌려준다.

    지워진 행의 pattern_id도 집합에 넣는다 — 재분석에서 사라진 판정의 패턴을 다시 계산하지
    않으면 그 패턴이 낡은 단계에 남는다(`_DELETE_OCCURRENCES_SQL`이 pattern_id를 돌려받는
    것과 같은 이유).

    호출자의 트랜잭션 안에서 돈다. 자기 트랜잭션을 열지 않는다 — 판정 기록과 그에 따른 단계
    갱신이 갈라지면 절반만 반영된 상태가 남는다(설계서 §9 Dependency).

    ⚠️ **전제조건: `attempts`는 canonical `pattern_key`로 중복이 제거돼 있어야 한다.**
    같은 key가 두 번 오면 `unique(pattern_id, utterance_id)` 위반으로 호출자의 트랜잭션이
    통째로 깨진다 — 그 발화의 교정까지 함께 사라진다. 지금 그것을 보장하는 것은
    `services.analysis.resolve_pattern_keys`의 dict 수집 하나다(그 함수를 고칠 때 이 계약을 본다).
    """
    removed = await conn.fetch(_DELETE_ATTEMPTS_SQL, utterance_id)
    touched: set[UUID] = {record["pattern_id"] for record in removed}
    for attempt in attempts:
        pattern_id = await conn.fetchval(
            _INSERT_ATTEMPT_SQL, user_id, utterance_id, attempt.outcome, attempt.pattern_key
        )
        if pattern_id is None:
            # `resolve_pattern_keys`의 정규화를 통과했는데도 행이 없다 = 그 사이 패턴이
            # 사라졌다(재분석으로 occurrence가 0이 되어 정리된 경우). 버리고 계속한다.
            logger.warning(
                "attempt for pattern_key %r stored no row — pattern is gone", attempt.pattern_key
            )
            continue
        touched.add(pattern_id)
    return touched


async def recompute(conn: asyncpg.Connection, pattern_id: UUID) -> ReviewState:
    """패턴 하나의 복습 상태를 이력에서 다시 계산해 반영한다 (멱등).

    `error_patterns`(`next_review_at`·`mastery_score`)와 `review_tasks`의 **사다리 행들**을 함께
    맞춘다. 호출자의 트랜잭션 안에서 돈다 — 사다리 upsert 여러 건과 상태 전이가 한 트랜잭션에
    들어가야 절반만 반영된 사다리가 남지 않는다.

    **사후조건** (`TASK-43`, 마이그레이션 010): 현재 사이클 행은 `state.ladder`와 정확히 일치하고,
    과거 사이클 행은 파생값이 덮이지 않는다. 과거 사이클의 `pending` 행은 `abandoned`가 되고,
    근거가 이력에서 사라진 행은 `superseded`가 된다 — **어느 경로에서도 행을 지우지 않는다.**

    멱등의 기전은 upsert의 conflict target이 자연키라는 것이다. 그래서 `id`·`created_at`이
    재실행에도 불변이고, **그것을 검증하려면 테스트가 그 두 컬럼을 select해야 한다** — 그러지
    않으면 이 설계의 핵심이 무보호로 남는다(설계서 §1.3).
    """
    # 카테고리로 이력 쿼리를 고른다 (설계서 §5.2). 그 뒤는 두 경로가 **완전히 공유한다** —
    # `fold_stages`는 순수 함수라 어느 표에서 읽었는지 알 필요가 없다.
    category = await conn.fetchval(_PATTERN_CATEGORY_SQL, pattern_id)
    history_sql = _PRONUNCIATION_HISTORY_SQL if category == PRONUNCIATION_CATEGORY else _HISTORY_SQL
    record = await conn.fetchrow(history_sql, pattern_id)
    if record is None:  # 방어: 교차 조인이라 항상 1행이지만 계약을 코드로 남긴다
        raise LookupError(f"review history query returned no row for pattern {pattern_id}")

    state = fold_stages(
        record["relapse_at"], list(record["correct_times"] or []), record["scenario_context"]
    )

    await conn.execute(
        _APPLY_PATTERN_SQL,
        pattern_id,
        state.next_review_at,
        MASTERED if state.completed else NOT_MASTERED,
    )
    if state.cycle_started_at is None:
        # 재발이 이력에서 사라졌다 — 현재 사이클이 없으므로 남은 행 전부가 근거를 잃는다.
        # 행이 애초에 없던 패턴은 0행 그대로다(update가 0행을 건드린다).
        await conn.execute(_SUPERSEDE_ALL_TASKS_SQL, pattern_id)
        return state

    # 사다리를 먼저 쓴다. 각 칸이 자기 예정일과 완주 시각을 들고 있어 `next_review_at or anchor`
    # 폴백이 필요 없다 — 완주한 3단계 행도 실제 예정일(2단계를 접은 시각 + 7일)을 갖는다.
    for row in state.ladder:
        await conn.execute(
            _UPSERT_TASK_SQL,
            pattern_id,
            REVIEW_TASK_TYPE,
            state.scenario_context,
            state.cycle_started_at,
            row.stage,
            row.due_at,
            "done" if row.completed_at is not None else "pending",
            row.completed_at,
        )
    # 그 다음에 은퇴·중단을 정리한다.
    # ⚠️ **순서가 방벽이 아니다 — 세 문장이 건드리는 행 집합이 서로소다** (코드 리뷰 MEDIUM-1이
    # 이전 주석의 "순서가 중요하다"를 반박했고, `where` 절 대조로 확인했다). `C`를 현재
    # `cycle_started_at`, `L`을 새 사다리 길이라 하면:
    #   upsert    → `cycle = C ∧ stage ∈ 1..L`  (`fold_stages`가 `stage=1`부터 `+1`로만
    #                append하므로 사다리 단계는 **정확히 `1..L` 연속**이다)
    #   supersede → `cycle > C` ∨ (`cycle = C ∧ stage > L`)
    #   abandon   → `cycle < C ∧ status = 'pending'`
    # 셋이 쌍마다 서로소이므로 어느 순서로 돌려도 결과가 같다. 읽는 순서로 사다리를 먼저 두었다.
    # ⛔ **진짜 불변조건은 `$3`이 「새」 사다리 길이라는 것이다.** 옛 길이를 쓰면 두 방향으로 깨지고
    # 둘의 순서 민감도가 **다르다**(재리뷰 새-LOW-3이 이 구분을 요구했다 — 아래를 뭉개면 다음 사람이
    # 틀린 확신을 갖는다):
    #   * 사다리가 **길어졌을 때**(`L_old=1 → L_new=2`, `$3=1`): **이 순서에서만** 깨진다.
    #     upsert가 `(C,2)`를 만든 뒤 supersede가 `stage > 1`로 그것을 내린다. 순서를 뒤집으면
    #     그 행이 아직 없어 supersede가 걸리지 않고 upsert가 나중에 만들어 **깨지지 않는다.**
    #   * 사다리가 **짧아졌을 때**(`L_old=3 → L_new=1`, `$3=3`): **어느 순서에서도** 깨진다.
    #     supersede가 `stage > 3`만 보아 은퇴시켜야 할 2·3단계 행을 놓친다.
    # 즉 순서를 지키는 것으로는 첫째만 가려지고 둘째는 남는다. **순서가 아니라 이 인자를 지켜라.**
    await conn.execute(_SUPERSEDE_TASKS_SQL, pattern_id, state.cycle_started_at, len(state.ladder))
    await conn.execute(_ABANDON_TASKS_SQL, pattern_id, state.cycle_started_at)
    return state


@dataclass(frozen=True, slots=True)
class DueReview:
    """복습 예정일이 지난 패턴 한 건 (설계서 §4.1의 목록 항목)."""

    pattern_id: UUID
    pattern_key: str
    category: str
    target_form: str
    next_review_at: datetime
    mastery_score: float


async def load_due_reviews(conn: asyncpg.Connection, user_id: UUID) -> list[DueReview]:
    """오늘 다뤄야 하는 복습 목록 — 예정일이 지난 것만, **가장 밀린 것부터** (설계서 §4.1).

    **놓치면 안 되는 목록이라 판정을 Claude에 맡기지 않는다**(§3.2의 경계). 소비자는 슬라이스 2의
    계획 생성이고, 이 슬라이스에서 함수를 두는 이유는 두 가지다: ① 슬라이스 1의 완료 판정
    ("복습 목록이 처음으로 값을 갖는다")을 **실제로 증명할 수 있게** 한다 ② `now()` 대신
    `clock_timestamp()`를 써야 한다는 §4.1의 함정을 이 슬라이스 안에서 고정한다 —
    아니면 슬라이스 2가 같은 함정을 다시 밟는다.
    """
    records = await conn.fetch(_DUE_REVIEWS_SQL, user_id)
    return [
        DueReview(
            pattern_id=record["pattern_id"],
            pattern_key=record["pattern_key"],
            category=record["category"],
            target_form=record["target_form"],
            next_review_at=record["next_review_at"],
            mastery_score=float(record["mastery_score"]),
        )
        for record in records
    ]


# 완주 판정에는 **재발 이전** 정답까지 필요하다 — `_HISTORY_SQL`은 마지막 재발 이후만 보므로
# 이 판정에 쓸 수 없다. 그래서 전체 이력을 시각만 뽑아 온다(단일 사용자 규모라 전량이 싸다).
_FULL_HISTORY_SQL = """
select p.id as pattern_id,
       coalesce((
         select array_agg(t.at order by t.at)
           from (
                 select u.created_at as at
                   from error_occurrences eo
                   join utterances u on u.id = eo.utterance_id
                  where eo.pattern_id = p.id
                 union all
                 select u.created_at as at
                   from pattern_attempts pa
                   join utterances u on u.id = pa.utterance_id
                  where pa.pattern_id = p.id and pa.outcome = 'incorrect'
                ) t
       ), '{}'::timestamptz[]) as relapse_times,
       coalesce((
         select array_agg(u.created_at order by u.created_at, pa.id)
           from pattern_attempts pa
           join utterances u on u.id = pa.utterance_id
          where pa.pattern_id = p.id and pa.outcome = 'correct'
       ), '{}'::timestamptz[]) as correct_times
  from error_patterns p
 where p.user_id = $1
 order by p.pattern_key
"""


async def load_completed_then_relapsed(conn: asyncpg.Connection, user_id: UUID) -> set[UUID]:
    """3단계(1·3·7일)를 완주한 **뒤에** 다시 발생한 패턴들 (설계서 §6.2).

    이것이 설계서가 허용한 **유일한 결정론적 만성 신호**다 — 임계값이 아니라 문서로 확정된
    1·3·7일에서 유도되기 때문이다(§3.2). 판정 자체는 `fold_stages`가 하고 이 함수는
    사이클을 잘라 넘기기만 한다. **복습 단계의 정의를 여기 복제하지 않는다.**

    한 번 완주한 뒤 재발했다면 그 사실은 이후에도 참이므로, 연속한 재발 쌍을 모두 본다.
    마지막 재발 이후의 열린 구간은 세지 않는다 — 아직 "재발이 뒤따랐다"가 성립하지 않는다.
    """
    flagged: set[UUID] = set()
    for record in await conn.fetch(_FULL_HISTORY_SQL, user_id):
        relapses = list(record["relapse_times"])
        corrects = list(record["correct_times"])
        for start, end in zip(relapses, relapses[1:], strict=False):
            within = [at for at in corrects if start < at < end]
            if fold_stages(start, within, "").completed:
                flagged.add(record["pattern_id"])
                break
    return flagged


async def recompute_all(conn: asyncpg.Connection, user_id: UUID) -> int:
    """이 사용자의 **모든** 패턴에 `recompute`를 돌린다. 건드린 패턴 수를 돌려준다.

    **백필용이다.** `recompute`는 분석이 건드린 패턴에만 돌기 때문에, 006 **전에** 쌓인
    패턴은 그 패턴이 다시 발생할 때까지 예정일을 받지 못한다 — 마이그레이션 직후에도
    `load_due_reviews`가 0행이라 슬라이스 1의 완료 판정이 실물에서 성립하지 않는다
    (2026-09-04 dev DB 실측: 패턴 7행·occurrence 17행인데 예정일 0건).

    이력에서만 계산하므로 몇 번 돌려도 같은 결과다(멱등). 호출자의 트랜잭션에서 돈다.
    """
    pattern_ids = [record["id"] for record in await conn.fetch(_ALL_PATTERNS_SQL, user_id)]
    for pattern_id in pattern_ids:
        await recompute(conn, pattern_id)
    return len(pattern_ids)
