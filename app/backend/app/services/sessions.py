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
from collections.abc import Collection
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal
from uuid import UUID

import asyncpg
import pydantic

from app.models.plan import SessionInstruction
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
        'speaking')
returning id
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
# 소비 표시를 하지 않으므로 언제나 최신 1행을 읽는다 — 표시를 두면 시작에 UPDATE가 생겨
# "세션 시작은 조회 1회"(§3.4)가 깨지고, 007에 없는 컬럼을 발명하는 것이 된다.
#
# ⚠️ **그 값으로 받아들인 결과는 "같은 계획이 두 세션에 연속으로 쓰일 수 있다"다** — 같은
# 초점과 같은 질문이 두 번 나온다. 그 창은 엣지 케이스가 아니라 정상 경로에서 열린다:
# 직전 세션의 계획 job 이 아직 끝나지 않았거나 검증 거부로 실패한 채 다음 세션이 시작되면
# 그 앞 세션의 계획이 다시 읽힌다. 소비 표시의 경계를 정하는 것은 이 슬라이스의 범위가
# 아니다(설계서 §11 이월).
_PREPARED_PLAN_SQL = """
select sp.id as plan_id, sp.reason, sp.instruction
  from session_plans sp
  join learning_sessions ls on ls.id = sp.session_id
 where ls.user_id = $1
 order by sp.created_at desc, sp.id desc
 limit 1
"""


@dataclass(frozen=True, slots=True)
class PreparedPlan:
    """직전 세션이 만들어 둔 계획에서 **세션 시작이 쓰는 것만** 담는다.

    초점 패턴 id·질문 목록·목표 수준은 담지 않는다 — 대화 상대에게 넘어가는 것은
    `instruction`(§5.2 가변부)이고, 화면에 나가는 것은 `reason`이다(R11-3). `plan_id`는
    로그와 조회 경로가 어느 계획이 쓰였는지 가리키기 위한 것이다.
    """

    plan_id: UUID
    reason: str
    instruction: SessionInstruction


async def load_prepared_plan(conn: asyncpg.Connection, user_id: UUID) -> PreparedPlan | None:
    """이 학습자에게 준비된 최신 계획을 돌려준다 — 없으면 `None` (설계서 §3.3·§3.4).

    **조회만 한다.** 세션 시작에 Claude 호출도, 쓰기도 없다(§3.4).

    **§9 Contract: 이 함수는 실패로 세션 시작을 막지 않는다.** 계획 부재(`None`)는 정상
    경로이고 호출자는 고정 시나리오로 진행한다(AS4). 저장된 `instruction`이 지금의
    `SessionInstruction` 계약을 만족하지 못하는 경우도 같게 다룬다 — 그 상황은 계약에
    필수 필드가 늘었을 때 **이전에 저장된 모든 행**에서 한꺼번에 오므로, 예외로 새게 두면
    그 순간부터 세션이 아예 시작되지 않는다. 대신 `warning`을 남긴다(H-Z: 문서가 지정한
    실행에서 INFO는 보이지 않는다) — 계획이 매번 조용히 무시되는 것을 알 유일한 신호다.

    `instruction`을 `json.loads` → `model_validate`로 좁히는 이유: 이 리포에는 jsonb
    코덱이 설정돼 있지 않아(`set_type_codec` 0건) asyncpg가 `str`를 돌려준다. 문자열을
    그대로 넘기면 지시문을 조립하는 쪽이 문자열을 필드처럼 다루게 된다.
    """
    row = await conn.fetchrow(_PREPARED_PLAN_SQL, user_id)
    if row is None:
        return None
    try:
        instruction = SessionInstruction.model_validate(json.loads(row["instruction"]))
    except pydantic.ValidationError as error:
        logger.warning(
            "계획 %s의 지시문을 읽을 수 없어 계획 없이 시작한다 — 저장된 모양이 지금의 "
            "SessionInstruction 계약과 다르다: %s",
            row["plan_id"],
            error,
        )
        return None
    return PreparedPlan(plan_id=row["plan_id"], reason=row["reason"], instruction=instruction)


async def create_session(pool: asyncpg.Pool, user_id: UUID) -> UUID:
    """연결 하나에 대응하는 `active` 세션 행을 만든다."""
    async with pool.acquire() as conn:
        session_id = await conn.fetchval(_CREATE_SESSION_SQL, user_id)
    assert session_id is not None, "insert ... returning produced no row"
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
