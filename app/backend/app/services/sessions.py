"""세션 생성·종료 SQL 단일 소유 (설계서 §5.3, AC G1).

`api/ws.py`(생성)와 `audio_gateway/session.py`(종료)가 각자 들고 있던 두 문장을
여기 모은다 — 둘 다 `learning_sessions` 한 행의 생명주기 양끝일 뿐, 계층이
다르다고 SQL을 갈라 둘 이유가 없다.

* **생성**은 시나리오를 **학습자 수준에 맞는 행**에 붙이고, 맞는 행이 없으면
  가장 이른 행으로 떨어진다(설계서 §3.3). 시나리오가 아예 없으면 `scenario_id`는
  null로 남고(컬럼 nullable) 세션은 그대로 진행된다. 고정 사용자 id는 이 모듈이
  알지 못한다 — 호출자(`api/ws.py`)가 넘긴다: 단일 사용자 로컬 도구라는 사실은
  API 계층의 관심사이고, 이 모듈은 "누구의 세션인가"를 주입받기만 한다.
* **시작이 읽을 계획**은 `load_prepared_plan`이 돌려준다 — 직전 세션이 만들어 둔
  `session_plans` 최신 1행을 **조회만** 한다(§3.4). `api/ws.py`가
  `_load_prepared_plan_or_none`으로 이 함수를 감싸 어댑터 생성에 넘긴다(Task 10) —
  그래서 AS4("계획이 없어도 세션이 열린다")가 관통 경로로도 성립한다. 지시문 **조립**은
  이 모듈의 일이 아니다: 계획은 데이터로 팩토리까지 가고 문장이 되는 것은 거기서다(G-3).
* **시작이 읽을 무대**는 `load_session_scenario`가 돌려준다 — **생성이 이미 박아 둔**
  `scenario_id`를 읽는다(설계서 §2.1). 수준으로 다시 고르지 않는 것이 계약이다: 그러면
  학습자 수준이 올라간 뒤 지시문의 무대와 세션 행의 무대가 갈라진다.
* **시작이 쓰는 것이 하나 있다** — `record_drill_turns_expected`가 기대 exchange 수를
  `learning_sessions.drill_turns_expected`(009)에 남긴다(캡틴 결정 16). ⚠️ 그래서 "세션 시작은
  조회뿐"이 더 이상 참이 아니다: 기대값은 **복원 불가**라서(계획 조회가 「최신 1행」이다)
  그 순간에 남기지 않으면 영구히 알 수 없다. 실패해도 세션은 진행한다(부가 정보).
* **종료**는 `ended_at`과 `status`를 한 UPDATE로 묻는다 — 두 문장으로 갈라지면
  그 사이에 "끝났지만 active"인 상태가 관측된다. 시각은 DB 시계(timestamptz)로
  찍는다: 앱이 만든 naive datetime이 섞이는 경로를 아예 만들지 않는다. 그리고
  **`active`인 세션만** 닫는다 — 고아 리퍼의 판정을 덮지 않기 위해서다(`end_session` 참조).
* **고아 리퍼**(`reap_orphan_sessions`, I-4)는 종료 기록 없이 프로세스가 죽어 남은
  `active` 세션을 닫는다. 그 판정의 안전성은 호출자가 넘기는 live 세션 집합에 걸려 있다.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Collection, Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal
from uuid import UUID

import asyncpg
import pydantic

from app.models.plan import PlanQuestion, SessionInstruction
from app.models.scenario import SessionScenario
from app.services.jobs import enqueue_plan_next_session

logger = logging.getLogger(__name__)

SessionEndStatus = Literal["completed", "failed"]

# 설계 발명값 — **캡틴 결정 2026-09-03**: "1분 이상 답이 없으면 `failed`로 닫는다"(I-4).
# 무엇이 "답"인가: 그 세션의 마지막 발화(화자 무관 — agent 응답도 활동이다), 발화가
# 없으면 `started_at`. 이 값만으로는 진행 중 세션을 닫을 위험이 남으므로 리퍼는
# **live 가드**와 함께만 안전하다 (`reap_orphan_sessions` 참조).
ORPHAN_IDLE_GRACE = timedelta(seconds=60)

_CREATE_SESSION_SQL = """
insert into learning_sessions (user_id, scenario_id, mode)
values ($1,
        coalesce(
          -- 학습자 수준에 맞는 시나리오를 먼저 찾는다 (설계서 §3.3).
          (select s.id from learning_scenarios s
            where s.level = (select u.current_level from users u where u.id = $1)
            order by s.created_at, s.id limit 1),
          -- 없으면 가장 이른 행으로 떨어진다 — 시드가 `A2` 3행뿐이라 수준이 올라가면
          -- 일치가 0행이 되고 실제로 이 경로로 온다. 학습이 막히는 것보다 시나리오가
          -- 조금 쉬운 편이 낫다(§9 Failure). 시나리오가 아예 없으면 둘 다 null 이고
          -- `scenario_id`는 null 로 남는다(컬럼 nullable) — 세션은 그대로 진행된다.
          (select s.id from learning_scenarios s order by s.created_at, s.id limit 1)
        ),
        $2)
returning id
"""

# 세션이 고른 쉐도잉 클립을 붙인다 (`TASK-45` · 설계서 §12 요구 2·3).
# ⚠️ **선택 규칙이 위 시나리오 절과 같은 모양인 것은 의도다** — 설계서 §3.3이
# *"`learning_scenarios.level`과 같은 값역을 쓴다 — 선택의 기준이 같기 때문이다"*로 그 근거를
# 적었다. 수준 일치 우선 → 없으면 가장 이른 행 → 클립이 아예 없으면 **0행이 되어 update가
# 아무 것도 하지 않는다**(`shadowing_item_id`는 null로 남고 세션은 그대로 진행된다).
# ⛔ `mode`를 조건에 넣지 않는다 — 011의 CHECK가 이미 그것을 가둔다. 두 곳에 두면 갈라진다.
_ATTACH_SHADOWING_CLIP_SQL = """
update learning_sessions
   set shadowing_item_id = coalesce(
         (select i.id from shadowing_items i
           where i.level = (select u.current_level from users u where u.id = $2)
           order by i.created_at, i.id limit 1),
         (select i.id from shadowing_items i order by i.created_at, i.id limit 1)
       )
 where id = $1
"""

# `and status = 'active'`는 **캡틴 결정(2026-09-03)**이다 — `end_session`이 리퍼의 판정을 덮지
# 못하게 막는다. `returning id`는 그 가드가 걸렸는지(0행)를 호출자가 알기 위한 것이다.
_END_SESSION_SQL = """
update learning_sessions
   set status = $2,
       ended_at = now()
 where id = $1
   and status = 'active'
returning id
"""

# `status = 'failed'`는 `SessionEndStatus`의 한 값이다 — 리터럴로 박은 이유는 리퍼가
# 닫는 방식이 하나뿐이기 때문이다(정상 종료로 위장하지 않는다). 시각은 `_END_SESSION_SQL`과
# 같은 규약으로 DB 시계에서 찍는다.
_REAP_ORPHAN_SESSIONS_SQL = """
update learning_sessions s
   set status = 'failed',
       ended_at = now()
 where s.status = 'active'
   and not (s.id = any($1::uuid[]))
   and coalesce(
         (select max(u.created_at) from utterances u where u.session_id = s.id),
         s.started_at
       ) < now() - $2::interval
returning s.id
"""

# 계획은 **그것을 만든 세션**을 가리킨다 — 세션 N이 끝날 때 만들어져 세션 N+1이 읽는다.
# 생성 시점에 N+1은 존재하지 않으므로 소비 세션 id를 담을 수 없다(설계서 §8.1이 `not null`
# + `unique`를 요구한다). 그래서 시작은 "**직전 세션이 만든 계획**"을 조회한다.
#
# 소비 표시를 하지 않으므로 언제나 최신 1행을 읽는다 — 표시를 두면 007에 없는 컬럼을 발명하는
# 것이 된다.
#
# ⛔ **이 결론의 다리가 하나 없어졌다 — 그 없는 다리로 소비 표시를 기각하지 마라.** 이 줄은 한때
# *"표시를 두면 시작에 UPDATE가 생겨 「세션 시작은 조회 1회」(§3.4)가 깨진다"*를 첫 근거로 들었는데,
# **캡틴 결정 16이 시작에 UPDATE를 이미 하나 만들었다**(`record_drill_turns_expected` — 이 모듈
# docstring의 "시작이 쓰는 것이 하나 있다" 항목이 그 사실을 소유한다). 그래서 그 제약은 **더 이상
# 존재하지 않고**, 결론은 남은 다리 하나로만 선다.
# ⚠️ 이것이 §11 이월(소비 표시의 경계)을 재검토하는 사람에게 중요하다 — **이미 없는 제약을 근거로
# 그 변경을 기각하면 낡은 논거로 설계를 막는 것이 된다.**
#
# ⚠️ **그 값으로 받아들인 결과는 "같은 계획이 두 세션에 연속으로 쓰일 수 있다"다** — 같은
# 초점과 같은 질문이 두 번 나온다. 그 창은 엣지 케이스가 아니라 정상 경로에서 열린다:
# 직전 세션의 계획 job 이 아직 끝나지 않았거나 검증 거부로 실패한 채 다음 세션이 시작되면
# 그 앞 세션의 계획이 다시 읽힌다. 소비 표시의 경계를 정하는 것은 이 슬라이스의 범위가
# 아니다(설계서 §11 이월).
_PREPARED_PLAN_SQL = """
select sp.id as plan_id, sp.reason, sp.instruction, sp.questions
  from session_plans sp
  join learning_sessions ls on ls.id = sp.session_id
 where ls.user_id = $1
 order by sp.created_at desc, sp.id desc
 limit 1
"""

# `questions`는 jsonb **배열**이라 `SessionInstruction`처럼 단일 모델의 `model_validate`로 좁힐
# 수 없다. `TypeAdapter`가 그 자리를 맡고, 모듈 상수로 두는 이유는 검증기를 한 번만 만들면
# 되는 것을 세션 시작마다 다시 만들 이유가 없기 때문이다.
_QUESTIONS_ADAPTER = pydantic.TypeAdapter(list[PlanQuestion])


@dataclass(frozen=True, slots=True)
class PreparedPlan:
    """직전 세션이 만들어 둔 계획에서 **세션 시작이 쓰는 것만** 담는다.

    초점 패턴 id는 담지 않는다. 대화 상대에게 넘어가는 것은 `instruction`(§5.2 가변부)과
    **`questions`**(오늘 드릴할 질문 3~5개)이고, `plan_id`는 로그와 조회 경로가 어느 계획이
    쓰였는지 가리킨다.

    **화면에 나가는 것은 `reason`과 `instruction.target_level` 둘이다**(R11-3) —
    `api/results.py`의 `next_plan`이 이 두 값으로 시작 화면의 한 줄을 만든다. 목표 수준을
    별도 필드로 담지 않는 것은 "안 쓴다"가 아니라 **지시문 안의 값이 그 하나**라는 뜻이다:
    `session_plans.target_level` 컬럼과 같은 값임을 저장 시점에 `PlanOutput`이 강제하고
    (`models/plan.py` `_target_level_matches_level_and_instruction`), 지시문을 읽을 수 없어
    이 함수가 `None`을 돌려주면 세션도 화면도 그 계획을 함께 버린다.

    ⚠️ **`questions`를 `SessionInstruction`에 넣지 않고 이 자리에 둔 이유**: 그 모델은
    `extra="forbid"`이고 필수 필드가 하나 늘면 **이전에 저장된 모든 행**이 한꺼번에 검증
    실패한다(`load_prepared_plan` docstring이 그 실패 모드에 이름을 붙여 뒀다). `questions`는
    007이 **별도 컬럼**으로 이미 저장하므로 지시문 안에 넣을 이유가 없다.
    """

    plan_id: UUID
    reason: str
    instruction: SessionInstruction
    questions: list[PlanQuestion]


async def load_prepared_plan(conn: asyncpg.Connection, user_id: UUID) -> PreparedPlan | None:
    """이 학습자에게 준비된 최신 계획을 돌려준다 — 없으면 `None` (설계서 §3.3·§3.4).

    **조회만 한다.** 세션 시작에 Claude 호출도, 쓰기도 없다(§3.4).

    ⚠️ **소비자가 둘이다.** 세션 시작(`api/ws.py`)과 **시작 화면의 `/next-plan`**
    (`api/results.py`의 `next_plan`)이 이 함수를 공유한다. 그래서 아래 「계획 전체 포기」는
    대화에서 끝나지 않고 **시작 화면의 추천 이유 한 줄(R11-3)도 같은 조건에서 사라지게 한다.**
    그것을 받아들인 판단이다(설계서 §2.1): 저장된 모양이 계약과 어긋났다면 대화와 화면이
    **함께** 그 계획을 버리는 것이 한쪽만 믿는 것보다 낫다.

    **§9 Contract: 이 함수는 실패로 세션 시작을 막지 않는다.** 계획 부재(`None`)는 정상
    경로이고 호출자는 고정 시나리오로 진행한다(AS4). 저장된 `instruction`·`questions`가 지금의
    계약을 만족하지 못하는 경우도 같게 다룬다 — 그 상황은 계약에 필수 필드가 늘었을 때
    **이전에 저장된 모든 행**에서 한꺼번에 오므로, 예외로 새게 두면 그 순간부터 세션이 아예
    시작되지 않는다. 대신 `warning`을 남긴다(H-Z: 문서가 지정한 실행에서 INFO는 보이지 않는다)
    — 계획이 매번 조용히 무시되는 것을 알 유일한 신호다.

    ⛔ **질문 검증이 실패하면 계획 전체를 포기한다** — 질문만 빈 목록으로 떨어뜨리고 계획을
    살리지 않는다(설계서 §2.1). 근거: `session_plans_questions_len`(007)이 3~5개 배열을 지키므로
    정상 경로에서 깨질 수 없고, 깨졌다면 계약이 어긋난 것이다. **반쯤 유효한 계획을 쓰는 것**이
    이 리포의 지배 실패 모드(*"통과했는데 통과한 이유가 틀렸다"*)에 가장 가깝다 — 그러면
    「드릴 지시 없는 세션」이 정상처럼 보인다.

    두 값을 `json.loads` → 모델 검증으로 좁히는 이유: 이 리포에는 jsonb 코덱이 설정돼 있지
    않아(`set_type_codec` 0건) asyncpg가 `str`를 돌려준다. 문자열을 그대로 넘기면 지시문을
    조립하는 쪽이 문자열을 필드처럼 다루게 된다.
    """
    row = await conn.fetchrow(_PREPARED_PLAN_SQL, user_id)
    if row is None:
        return None
    try:
        instruction = SessionInstruction.model_validate(json.loads(row["instruction"]))
        questions = _QUESTIONS_ADAPTER.validate_python(json.loads(row["questions"]))
    except pydantic.ValidationError as error:
        logger.warning(
            "계획 %s를 읽을 수 없어 계획 없이 시작한다 — 저장된 모양이 지금의 "
            "SessionInstruction·PlanQuestion 계약과 다르다: %s",
            row["plan_id"],
            error,
        )
        return None
    return PreparedPlan(
        plan_id=row["plan_id"],
        reason=row["reason"],
        instruction=instruction,
        questions=questions,
    )


# 세션 행에 **이미 박힌** `scenario_id`를 join해 읽는다 (설계서 §2.1, `TASK-25` AC#1·#3).
#
# ⛔ **INSERT가 고른 행을 다시 고르지 않는다.** `_CREATE_SESSION_SQL`처럼 학습자 수준으로
# 재조회하면 수준이 올라간 뒤 두 값이 갈라져, 지시문이 「그 세션이 실제로 받은 무대」와 다른
# 무대를 말한다. 그 폴백 경로는 실제로 발동한다(시드가 `A2` 3행뿐이다 — 위 SQL 주석).
#
# `scenario_id`가 null이면 join이 **0행**이라 `None`이 된다 — AC#3("null이면 지금 동작 유지")이
# **코드 분기 없이** 충족되는 형태를 고른 것이다. `if scenario_id is None`을 쓰지 않는다.
_SESSION_SCENARIO_SQL = """
select s.title, s.prompt_template
  from learning_sessions ls
  join learning_scenarios s on s.id = ls.scenario_id
 where ls.id = $1
"""

# 기대 exchange 수를 세션에 남긴다 (009, 캡틴 결정 16).
#
# **왜 저장하나**: 실제 exchange 수는 사후에 발화에서 도출되지만 **기대값은 복원 불가**다 —
# 계획 조회가 「사용자 최신 1건」(`_PREPARED_PLAN_SQL`)이므로 다음 세션이 지나면 그 세션이
# 어느 계획을 썼는지 알 길이 없다.
# ⛔ **`learning_sessions.summary`에 얹지 않는다.** 그 컬럼은 `docs/database-schema.md`가
# `summarize_session`(세션 총평)의 것으로 이미 지정했고 007이 그 job을 CHECK에 열어 뒀다 —
# 총평 구현자가 `set summary = $2`를 쓰는 것은 **정상 행동**이고 그때 이 값이 지워진다.
_DRILL_TURNS_EXPECTED_SQL = """
update learning_sessions
   set drill_turns_expected = $2
 where id = $1
"""


async def load_session_scenario(
    conn: asyncpg.Connection, session_id: UUID
) -> SessionScenario | None:
    """이 세션이 올라선 무대 — 없으면 `None` (설계서 §2.1, `TASK-25` AC#1·#3).

    **사후조건: 세션 부재 · `scenario_id` null · 무대 행 부재 → 전부 `None`.** 셋이 한 경로로
    수렴하는 것이 의도다(위 SQL 주석 — join 0행). 호출자는 무대 없이 진행한다.

    ⛔ **DB 오류는 던진다.** 흡수는 `api/ws.py`의 래퍼가 한다(`_load_known_sounds_or_empty`·
    `_load_prepared_plan_or_none`과 같은 분업). 예외를 여기서 삼키면 「조회가 깨졌다」와
    「무대가 없다」가 서비스 계층에서 구분되지 않아, 조회가 영구히 깨진 것을 아무도 모른다.

    반환 타입이 `models`에 있는 이유: `audio_gateway/factory.py`·`nova.py`가 `app.models`만 알고
    `app.services`가 그 값을 채우는 기존 방향(`SessionInstruction`)과 같다.
    """
    row = await conn.fetchrow(_SESSION_SCENARIO_SQL, session_id)
    if row is None:
        return None
    return SessionScenario(title=row["title"], prompt_template=row["prompt_template"])


async def record_drill_turns_expected(
    conn: asyncpg.Connection,
    session_id: UUID,
    *,
    questions: Sequence[PlanQuestion],
    drill_count: int,
    drill_turns_min: int,
) -> int | None:
    """세션 시작에 기대 exchange 수를 남긴다 — 쓴 값을 돌려준다 (설계서 §2.3, 캡틴 결정 16).

    값 = **열거되는 질문 수** × 드릴당 최소 exchange 수 = `len(questions[:drill_count])` ×
    `drill_turns_min`. ⛔ **`len(questions)`가 아니다** — 지시문이 열거하는 것도
    `questions[:drill_count]`이고(`audio_gateway/nova.build_system_prompt`), 두 수가 갈라지면
    설정값이 **대화를 바꾸지 않고 통과 문턱만 바꾸는 노브**가 된다(H-5). 두 곳이 같은 슬라이스를
    쓰는 것이 계약이고, 그 일치는 열거 수를 세는 테스트와 이 값을 재는 테스트가 함께 지킨다.

    **질문이 0건이면 아무것도 쓰지 않고 `None`을 돌려준다** → 컬럼은 null로 남는다 =
    **관측 대상이 아니다.** ⛔ 0을 쓰지 않는 이유가 둘이다: 0은 「기대가 0이었다」로 읽혀
    「기대가 없었다」와 구분되지 않고, 009의 `check (… > 0)`가 그것을 거부해 **부가 정보 때문에
    세션 시작이 깨진다.**

    ⛔ **DB 오류는 던진다** — `load_session_scenario`와 같은 분업이다. 이 값은 부가 정보이므로
    실패해도 세션은 진행해야 하고, 그 흡수와 로그는 `api/ws.py`의 래퍼가 소유한다.
    ⚠️ 그 결과 **실패한 세션은 관측 대상에서 조용히 빠진다** — 로그가 그 사실의 유일한 신호다.

    **전제** (설계서 §4 Contract): 세션 행이 **이미 있다** — `create_session` 뒤에 불린다.
    행이 없으면 UPDATE가 0행을 고치고 **조용히 성공한다**(아래 불변조건과 같은 성질이다).

    **불변조건: 한 세션에 한 번만 쓴다.** 재호출을 계약으로 **허용하지 않는다** — 두 번째 호출이
    있으면 어느 계획의 기대값인지가 갈리고, 기대값은 복원 불가라서 덮인 값을 되찾을 수 없다.
    ⚠️ **구현은 그것을 강제하지 않는다.** 조건 없는 UPDATE라 다시 부르면 그냥 덮어쓴다 — 가드를
    두지 않은 것은 **팀리드 판단이다(캡틴 결정이 아니다)**: 호출 지점이 `api/ws.py` 한 곳이고
    세션 시작 경로에 한 번 있으므로 가드는 YAGNI다. **계약과 강제가 다른 자리이므로 여기 적어 둔다**
    — 호출 지점이 둘이 되는 순간 이 줄이 그 사실을 알려 주는 유일한 곳이다.
    """
    expected = len(questions[:drill_count]) * drill_turns_min
    if expected == 0:
        return None
    await conn.execute(_DRILL_TURNS_EXPECTED_SQL, session_id, expected)
    return expected


async def create_session(pool: asyncpg.Pool, user_id: UUID, *, mode: str = "speaking") -> UUID:
    """연결 하나에 대응하는 `active` 세션 행을 만든다.

    `mode`는 **키워드 전용이고 기본값이 `'speaking'`**이다 (`TASK-45` · 결정 11이 미뤄 둔
    파라미터화가 여기서 발화한다). ⛔ **기존 호출자를 깨뜨리지 않는 것이 그 형태의 이유다** —
    `api/ws.py`와 하네스는 인자를 주지 않고 지금 그대로 말하기 세션을 연다.
    값역은 001의 `learning_sessions_mode_check`(`speaking`·`shadowing`·`review`)가 가둔다 —
    이 함수가 목록을 복제하지 않는다(두 곳이 갈라지지 않게).
    """
    async with pool.acquire() as conn:
        session_id = await conn.fetchval(_CREATE_SESSION_SQL, user_id, mode)
    assert session_id is not None, "insert ... returning produced no row"
    return session_id


async def start_shadowing_session(pool: asyncpg.Pool, user_id: UUID) -> UUID:
    """쉐도잉 세션을 열고 **학습자 수준에 맞는 클립 1개를 붙인다** (`TASK-45`).

    설계서 `2026-09-08-shadowing-task-design.md` §12가 진입점에 요구한 것 중 **1·2·3**을
    이 함수가 이행한다: `mode='shadowing'`으로 연다 · 클립 1개를 고르고 그 id를 세션에
    남긴다(선택이 재접속에서 살아남는다) · 선택 기준은 `users.current_level`이다.

    ⛔ **범위 경계**: 「추가 학습 5종을 어떻게 배치하나」는 **`TASK-10`의 설계 몫이고 이 함수가
    정하지 않는다**(캡틴 결정 34가 「최소한만 만든다」로 제약했다).

    ⚠️ **2026-09-09 정정 — 호출 표면이 생겼다.** 이전 판은 *"이 함수는 호출 표면을 갖지
    않는다"*로 적혀 있었고 그것이 그때는 참이었다. 캡틴 결정 35로 `api/ws.py`가
    **`?mode=shadowing`** 으로 이 함수를 부른다. 여전히 `TASK-10`의 몫으로 남은 것은 **어느
    화면·어느 버튼이 그 모드로 연결하는가**와 5종의 배치·우선순위다 — 프로토콜은 있고 UI가 없다.

    ⚠️ **선택 규칙은 발명이 아니라 선례다**: `learning_scenarios` 선택과 **같은 형태**
    (수준 일치 우선 → 없으면 가장 이른 행)를 쓴다. 설계서 §3.3이 *"`learning_scenarios.level`과
    같은 값역을 쓴다 — 선택의 기준이 같기 때문이다"*로 그 근거를 이미 적었다.

    ⛔ **클립이 0행이어도 세션을 연다.** 011의 CHECK가 역방향(`mode='shadowing'`이면 반드시
    클립)을 강제하지 않는 것과 같은 판단이다 — 여기서 예외를 던지면 시드가 비어 있는 DB에서
    쉐도잉 진입이 **전부** 막힌다. `shadowing_item_id`는 그때 null로 남는다.

    **한 트랜잭션이다** — 세션을 만든 뒤 클립을 붙이기 전에 죽으면 클립 없는 쉐도잉 세션이
    남는데, 그것은 위 문장대로 정상 상태이므로 부분 실행이 손상이 아니다. 그래도 한 단위로
    묶는 이유는 **선택이 세션과 함께 보이는 것**이 재접속 복원의 전제이기 때문이다.
    """
    async with pool.acquire() as conn, conn.transaction():
        session_id = await conn.fetchval(_CREATE_SESSION_SQL, user_id, "shadowing")
        assert session_id is not None, "insert ... returning produced no row"
        await conn.execute(_ATTACH_SHADOWING_CLIP_SQL, session_id, user_id)
    return session_id


async def end_session(conn: asyncpg.Connection, session_id: UUID, status: SessionEndStatus) -> None:
    """세션 종료를 기록한다 — `ended_at` + `status`를 한 UPDATE로.

    **연결을 받는 쪽이 원시 함수다.** 종료 기록을 다른 쓰기와 한 트랜잭션으로 묶어야 하는
    호출자가 있어서다(`audio_gateway/session.py`: 종료 기록 + 발음 시도 수렴을 한 단위로).
    `save_final_transcript(conn, …)`가 같은 이유로 연결을 받는다.

    ⚠️ **`active`인 세션만 닫는다** (캡틴 결정 2026-09-03). 가드가 없으면 고아 리퍼가 `failed`로
    닫은 세션을 나중에 소유자가 `completed`로 덮어써 **리퍼가 개입했다는 사실이 DB에서 사라진다**
    (`ended_at`까지 되돌아간다). 그 상황은 곧 **live 가드가 진행 중 세션을 놓쳤다**는 뜻이고,
    그때 스윕은 이미 자라는 묶음을 걷었을 수 있다 — 조용히 수렴시키면 그 사고가 흔적 없이
    사라진다. 그래서 **최초 판정을 남기고 경고를 찍는다.** 정상 흐름(`active` → 종료)에서는
    값이 그대로이므로 이 가드가 보이지 않는다.

    경고를 `warning`으로 찍는 이유는 함정 **H-Z**다 — 문서가 지정한 실행 명령에서 INFO는
    보이지 않는다. 이 로그가 가드 고장의 유일한 신호이므로 안 보이면 없는 것과 같다.
    """
    closed = await conn.fetchval(_END_SESSION_SQL, session_id, status)
    if closed is None:
        logger.warning(
            "세션 %s를 %s로 닫으려 했지만 이미 `active`가 아니다 — 최초 판정을 유지한다. "
            "고아 리퍼가 먼저 닫았다면 live 가드가 진행 중 세션을 놓쳤다는 신호다 (I-4)",
            session_id,
            status,
        )
        return
    # 설계서 §3.1: 같은 트랜잭션에서 다음 계획 job을 건다. `closed`가 있을 때만 거는 이유는
    # 이미 닫힌 세션 재호출(리퍼가 먼저 닫은 경우)에서 job이 중복되지 않게 하려는 것이다.
    await enqueue_plan_next_session(conn, session_id)


async def reap_orphan_sessions(
    conn: asyncpg.Connection,
    *,
    live_session_ids: Collection[UUID] = (),
    idle_after: timedelta = ORPHAN_IDLE_GRACE,
) -> list[UUID]:
    """유예를 넘겨 조용한 `active` 세션을 `failed`로 닫고 그 id들을 돌려준다 (I-4).

    **왜 필요한가**: 종료 기록 전에 프로세스가 죽으면 `end_session`이 돌지 않아 세션이
    `active`로 남는다. I-1 회복 스윕(`utterances.flush_ended_sessions`)은 **정의상
    `active`를 건너뛰므로** 그 세션의 발화 묶음은 아무도 걷지 않고, 결과 화면은 terminal
    상태 `no_utterances`("분석 대상 없음")에 고정된다. 리퍼가 닫아 스윕 대상으로 만든다 —
    그래서 이 함수와 스윕은 **리퍼 → 스윕** 순서로 불려야 같은 사이클에 회복이 끝난다
    (`workers/analysis_worker.py`).

    **무활동의 기준**은 그 세션 마지막 발화의 `created_at`이고, 화자를 가리지 않는다(agent
    final도 활동으로 센다). 발화가 없으면 `started_at`으로 잰다(연결만 열고 죽은 세션).
    ⚠️ **다만 시계가 전진하는 것은 final이 저장되는 순간뿐이다** — agent가 길게 말하는
    **동안**에는 아직 행이 없다(`audio_gateway/session.py` `_save_final`은 final 이벤트가
    도착할 때 쓴다. partial은 방송만 하고 저장하지 않는다). 그러니 "화자 무관"이 긴 agent
    턴을 지켜 주지는 않는다 — 그것을 지키는 것은 아래 live 가드다.
    시각 비교는 전부 DB 시계(`now()`, timestamptz)로 한다: 앱이 만든 naive datetime이 이
    판정에 섞이는 경로를 만들지 않는다.

    ⚠️ **`live_session_ids`가 이 함수의 안전성 전부다.** 유예만으로 판정하면 사용자가
    유예보다 길게 뜸을 들인 **진행 중** 세션이 닫히고, 그 직후 스윕이 아직 자라는 중인
    묶음을 걷어 조각 하나가 완전한 문장처럼 분석되는 I-1 오탐이 그대로 되살아난다 —
    고치려던 것을 회복 경로가 되돌리는 셈이다. 게다가 이것은 엣지 케이스가 아니라 **정상
    사용 핫패스**다: 활동 시각은 final이 저장될 때만 전진하므로(아래) 생각하는 사용자와
    긴 agent 턴이 정상적으로 유예를 넘긴다. 호출자는 **이 프로세스에서 살아있는 WebSocket이
    소유한 세션 id 집합**을 넘긴다(`api/ws.py`가 등록·해제하고, `api/main.py`의 lifespan이
    **집합 객체 자체**를 워커에 주입한다 — 복사본을 넘기면 가드가 통째로 무력해진다).
    기동 직후에는 비어 있으므로 이전 프로세스가 남긴 고아는 유예 후 전부 걷힌다.

    ⚠️ **가드는 프로세스 단위다 — 이 리포에는 실제로 가드 밖에서 `active` 세션을 만드는
    작성자가 있다.** `tests/harness/inject_errors.py`가 앱의 `create_session`을 **별도
    프로세스**에서 부르고(같은 DB), 백엔드 워커의 분석을 `--wait`(기본 180초) 동안 **새 발화
    없이** 기다린다 — 유예의 3배다. 그 창에서 백엔드 리퍼는 그 세션을 진행 중인데도 닫는다.
    **그러면 그 세션은 `failed`로 끝난다**: 스크립트 끝의 `mark_session_ended`는 위 `active`
    가드에 막혀 되돌리지 못하고 경고만 남긴다(그 경고가 바로 이 사고의 신호다). 하네스가 보는
    것은 패턴·occurrence이고 세션 status를 단정하지 않으므로 시나리오는 그대로 성립한다 —
    다만 그 세션의 결과 API는 `connection_failed`가 된다. 근거는 `TASKS.md` **I-4**가 소유한다.
    같은 DB를 보는 백엔드를 둘 띄우거나 `--workers 2`로 띄우면 같은 이유로 서로의 진행 중
    세션을 닫는다. 문서가 지정한 실행은 단일 프로세스다(`docs/ops/local-run.md`).

    ⚠️ 리퍼가 닫은 세션의 결과 화면은 `results.py` **규칙 1**에 따라 `connection_failed`
    ("연결 실패")가 된다 — 규칙 1은 job 상태를 보지 않고 최우선하므로, 스윕이 걷은 묶음이
    분석을 끝내도 그 화면에 교정은 실리지 않는다. 오류 패턴·숙련도 같은 누적 데이터는
    정상 갱신된다. 프로세스가 죽어 끝난 세션이라는 사실을 그대로 표시하는 쪽을 택한 것이다.

    ⚠️ 죽은 세션의 마지막 묶음은 미완성 문장일 수 있다(말하는 중에 죽었으므로). 그 묶음이
    조각으로 분석되는 것은 I-1과 같은 모양이지만, 이미 끝난 세션에서는 더 붙을 발화가
    없으므로 피할 방법이 없다 — 받아들인 한계다.

    ⚠️ 리퍼가 찍는 `ended_at`은 **실제 사망 시각이 아니라 리퍼가 알아챈 시각**이다(최소 유예만큼,
    워커가 내려가 있었으면 그만큼 더 늦다). 나이 상한이 없으므로 오래된 `active` 행이 쌓인 DB에서는
    첫 유휴 사이클이 그것들을 한 문장으로 닫고 뒤따르는 스윕이 묶음 전부에 job을 건다. 단일 사용자
    로컬 도구에서 받아들인 값이고, 현재 `ended_at`을 읽는 앱 코드는 없다(2026-09-03 grep — 정의와
    테스트 단정뿐). 상한을 넣지 않은 이유는 넣으면 **진짜 오래된 고아가 영구히 안 걷히기** 때문이다.

    반환 순서는 보장하지 않는다(`update ... returning`은 물리 순서다). 호출자는 로그로만
    쓴다 — 순서에 의미를 두는 소비자가 생기면 그때 정렬을 넣는다.
    """
    records = await conn.fetch(_REAP_ORPHAN_SESSIONS_SQL, list(live_session_ids), idle_after)
    return [record["id"] for record in records]


async def mark_session_ended(
    pool: asyncpg.Pool, session_id: UUID, status: SessionEndStatus
) -> None:
    """묶을 것이 없는 호출자를 위한 편의 래퍼 — 연결을 하나 잡아 트랜잭션을 열고 그 안에서
    `end_session`을 부른다.

    SQL은 여전히 `_END_SESSION_SQL` 하나가 소유한다.

    ⚠️ **`end_session`은 이제 항상 두 쓰기를 한다** — 종료 UPDATE와 계획 job 등록(§3.1,
    `closed`가 있을 때). 그래서 이 래퍼도 트랜잭션을 열어야 한다: 열지 않으면 asyncpg는
    문장마다 autocommit이라 종료 UPDATE가 커밋된 뒤 계획 job INSERT 전에 프로세스가
    죽으면 그 세션의 계획이 영구히 만들어지지 않는다(재시도는 `active` 가드에 막히고
    리퍼는 `active`만 건드린다 — 되살릴 경로가 없다).
    """
    async with pool.acquire() as conn, conn.transaction():
        await end_session(conn, session_id, status)
