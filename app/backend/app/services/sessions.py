"""세션 생성·종료 SQL 단일 소유 (설계서 §5.3, AC G1).

`api/ws.py`(생성)와 `audio_gateway/session.py`(종료)가 각자 들고 있던 두 문장을
여기 모은다 — 둘 다 `learning_sessions` 한 행의 생명주기 양끝일 뿐, 계층이
다르다고 SQL을 갈라 둘 이유가 없다.

* **생성**은 시나리오를 시드된 첫 행에 붙인다 — 첫 슬라이스에는 추천 로직이
  없고(YAGNI), 어떤 질문 세트로 대화했는지 결과가 참조할 수 있도록 연결만
  해둔다. 시드가 없으면 `scenario_id`는 null로 남고(컬럼 nullable) 세션은
  그대로 진행된다. 고정 사용자 id는 이 모듈이 알지 못한다 — 호출자(`api/ws.py`)가
  넘긴다: 단일 사용자 로컬 도구라는 사실은 API 계층의 관심사이고, 이 모듈은
  "누구의 세션인가"를 주입받기만 한다.
* **종료**는 `ended_at`과 `status`를 한 UPDATE로 묻는다 — 두 문장으로 갈라지면
  그 사이에 "끝났지만 active"인 상태가 관측된다. 시각은 DB 시계(timestamptz)로
  찍는다: 앱이 만든 naive datetime이 섞이는 경로를 아예 만들지 않는다.
"""

from __future__ import annotations

from collections.abc import Collection
from datetime import timedelta
from typing import Literal
from uuid import UUID

import asyncpg

SessionEndStatus = Literal["completed", "failed"]

# 설계 발명값 — **캡틴 결정 2026-09-03**: "1분 이상 답이 없으면 `failed`로 닫는다"(I-4).
# 무엇이 "답"인가: 그 세션의 마지막 발화(화자 무관 — agent 응답도 활동이다), 발화가
# 없으면 `started_at`. 이 값만으로는 진행 중 세션을 닫을 위험이 남으므로 리퍼는
# **live 가드**와 함께만 안전하다 (`reap_orphan_sessions` 참조).
ORPHAN_IDLE_GRACE = timedelta(seconds=60)

_CREATE_SESSION_SQL = """
insert into learning_sessions (user_id, scenario_id, mode)
values ($1, (select id from learning_scenarios order by created_at, id limit 1), 'speaking')
returning id
"""

_END_SESSION_SQL = """
update learning_sessions
   set status = $2,
       ended_at = now()
 where id = $1
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
    """
    await conn.execute(_END_SESSION_SQL, session_id, status)


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

    **무활동의 기준**은 그 세션 마지막 발화의 `created_at`이고, 화자를 가리지 않는다 —
    agent가 길게 답하는 동안 닫히면 안 된다. 발화가 없으면 `started_at`으로 잰다(연결만
    열고 죽은 세션). 시각 비교는 전부 DB 시계(`now()`, timestamptz)로 한다: 앱이 만든
    naive datetime이 이 판정에 섞이는 경로를 만들지 않는다.

    ⚠️ **`live_session_ids`가 이 함수의 안전성 전부다.** 유예만으로 판정하면 사용자가
    유예보다 길게 뜸을 들인 **진행 중** 세션이 닫히고, 그 직후 스윕이 아직 자라는 중인
    묶음을 걷어 조각 하나가 완전한 문장처럼 분석되는 I-1 오탐이 그대로 되살아난다 —
    고치려던 것을 회복 경로가 되돌리는 셈이다. 호출자는 **이 프로세스에서 살아있는
    WebSocket이 소유한 세션 id 집합**을 넘긴다(`api/ws.py`가 등록·해제한다). 단일
    프로세스라 그 집합이 곧 "살아있는 세션 전부"이고, 기동 직후에는 비어 있으므로
    이전 프로세스가 남긴 고아는 유예 후 전부 걷힌다.

    ⚠️ 리퍼가 닫은 세션의 결과 화면은 `results.py` **규칙 1**에 따라 `connection_failed`
    ("연결 실패")가 된다 — 규칙 1은 job 상태를 보지 않고 최우선하므로, 스윕이 걷은 묶음이
    분석을 끝내도 그 화면에 교정은 실리지 않는다. 오류 패턴·숙련도 같은 누적 데이터는
    정상 갱신된다. 프로세스가 죽어 끝난 세션이라는 사실을 그대로 표시하는 쪽을 택한 것이다.

    ⚠️ 죽은 세션의 마지막 묶음은 미완성 문장일 수 있다(말하는 중에 죽었으므로). 그 묶음이
    조각으로 분석되는 것은 I-1과 같은 모양이지만, 이미 끝난 세션에서는 더 붙을 발화가
    없으므로 피할 방법이 없다 — 받아들인 한계다.

    반환 순서는 보장하지 않는다(`update ... returning`은 물리 순서다). 호출자는 로그로만
    쓴다 — 순서에 의미를 두는 소비자가 생기면 그때 정렬을 넣는다.
    """
    records = await conn.fetch(_REAP_ORPHAN_SESSIONS_SQL, list(live_session_ids), idle_after)
    return [record["id"] for record in records]


async def mark_session_ended(
    pool: asyncpg.Pool, session_id: UUID, status: SessionEndStatus
) -> None:
    """묶을 것이 없는 호출자를 위한 편의 래퍼 — 연결을 하나 잡아 `end_session`을 부른다.

    SQL은 여전히 `_END_SESSION_SQL` 하나가 소유한다.
    """
    async with pool.acquire() as conn:
        await end_session(conn, session_id, status)
