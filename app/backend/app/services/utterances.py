"""Transcript persistence — utterance append + turn-boundary analysis enqueue (설계서 §5.2, W1/W6).

Two invariants live here:

* **`sequence_no`는 서버가 세션 안에서 단조 증가로 부여한다.** 클라이언트가 보낸
  값을 믿지 않는다. 부여와 insert가 한 문장이라 `select max()` 후 다른 문장에서
  insert할 때 생기는 틈이 없고, 그래도 두 연결이 같은 번호를 잡으면
  `unique (session_id, sequence_no)`가 이중 commit을 막는다 (001 스키마 주석).
  세션당 쓰기는 기본적으로 호출자(세션 하나에 gateway 하나)가 직렬화하며, 그럼에도
  발생하는 unique 충돌은 **1회 재시도**로 흡수한다 — 가드가 전사문을 잃는 수단이
  되어선 안 된다. 재시도가 올바른 번호를 계산하는 것은 READ COMMITTED(Postgres
  기본) 덕분이다: 재시도 문장은 새 스냅샷에서 승자의 커밋된 행을 본다.
* **분석 job은 저장 시점이 아니라 턴 경계에서 등록한다** (I-1, 2026-09-01).
  저장하는 순간에는 그 발화가 턴의 마지막인지 알 수 없다 — Nova의 발화 종료
  감지가 이르면(임계 약 480ms) 다음 말을 고르는 1초가 종료로 읽혀 한 문장이
  여러 final로 쪼개진다. 조각마다 job을 걸면 조각 하나가 완전한 문장처럼
  분석되어 "주어 없음"·"목적어 없음" 오탐이 나온다(실물 마이크 1회에서
  occurrence 13건 중 7건). 그래서 등록은 `flush_pending_analysis`가 맡고,
  **화면 표시와 `sequence_no`는 쪼개진 그대로 둔다** — 합치는 것은 분석 입력만이다.

분석 job은 **사용자의 learning 발화에만** 등록한다 (W6). agent 발화와
voice_command / command_confirmation은 저장은 되지만 교정 대상이 아니다 —
대신 **묶음을 닫는 신호**로 쓰인다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import get_args
from uuid import UUID

import asyncpg

from app.services.jobs import JOB_TYPE_ANALYZE
from app.services.sessions import SessionEndStatus

# "끝난 세션"의 정의는 `services/sessions.py`의 `SessionEndStatus`가 소유한다 —
# 값을 여기 다시 적으면 종료 상태가 하나 늘 때 회복 스윕만 조용히 낡는다.
# 나머지 하나는 `active`이고, 그것이 스윕에서 빠져야 하는 유일한 상태다.
ENDED_SESSION_STATUSES: tuple[str, ...] = get_args(SessionEndStatus)

# 분석 대상 발화의 정의 (W6). 묶음 판정·`pending_learning_utterances`의 선택 조건·
# 분석 입력 병합(`services/analysis.py`)이 갈라지지 않도록 모두 이 상수를 참조한다.
ANALYZED_SPEAKER = "user"
ANALYZED_UTTERANCE_TYPE = "learning"

_SELECT_COLUMNS = "id, session_id, speaker, utterance_type, transcript, sequence_no, created_at"


@dataclass(frozen=True, slots=True)
class UtteranceRow:
    id: UUID
    session_id: UUID
    speaker: str
    utterance_type: str
    transcript: str
    sequence_no: int
    created_at: datetime


def _to_utterance(record: asyncpg.Record) -> UtteranceRow:
    return UtteranceRow(
        id=record["id"],
        session_id=record["session_id"],
        speaker=record["speaker"],
        utterance_type=record["utterance_type"],
        transcript=record["transcript"],
        sequence_no=record["sequence_no"],
        created_at=record["created_at"],
    )


async def _insert_with_next_sequence_no(
    conn: asyncpg.Connection,
    session_id: UUID,
    speaker: str,
    utterance_type: str,
    text: str,
) -> asyncpg.Record:
    """Insert the utterance with `max(sequence_no) + 1` computed in the same
    statement. Re-running this after a unique violation recomputes the number
    from a fresh snapshot, which is what makes the retry converge."""
    record = await conn.fetchrow(
        f"""
        insert into utterances (session_id, speaker, utterance_type, transcript, sequence_no)
        select $1, $2, $3, $4, coalesce(max(sequence_no), 0) + 1
          from utterances
         where session_id = $1
        returning {_SELECT_COLUMNS}
        """,
        session_id,
        speaker,
        utterance_type,
        text,
    )
    # 집계 select는 항상 1행을 만들므로 insert가 성공하면 record는 None이 아니다.
    assert record is not None, "insert ... returning produced no row"
    return record


async def save_final_transcript(
    conn: asyncpg.Connection,
    session_id: UUID,
    text: str,
    *,
    speaker: str = "user",
    utterance_type: str = "learning",
) -> UtteranceRow:
    """Append a finalized transcript to its session.

    **분석 job은 여기서 걸지 않는다** — 이 발화가 턴의 마지막 조각인지 저장
    시점에는 알 수 없다(모듈 docstring, I-1). 등록은 턴이 닫힐 때
    `flush_pending_analysis`가 한다.

    `sequence_no` is derived inside the insert (`max(sequence_no) + 1` over the
    session), so the number is assigned by the database rather than by the
    caller. Partial transcripts are never stored — only `final` events reach
    here (`TranscriptEvent.kind == "final"`).

    If another connection commits the same `sequence_no` first, the unique guard
    fires and the insert is retried **once** with a recomputed number: the guard
    exists to stop double-commits, not to drop a transcript whose only sin was
    losing a race. The first attempt gets its own savepoint so the violation can
    be rolled back without taking the caller's transaction down with it.

    두 시도를 감싸는 바깥 `conn.transaction()`을 유지하는 이유는 **2차 시도가 또
    위반했을 때**다: 그것까지 savepoint 안에 있어야 호출자의 작업 단위가 abort되지
    않는다. I-1에서 enqueue가 빠지며 "두 write의 원자성"이라는 원래 목적은 사라졌지만
    이 성질은 남아 있으므로 지운 것을 되돌렸다(코드 리뷰 지적).
    """
    async with conn.transaction():
        try:
            async with conn.transaction():
                record = await _insert_with_next_sequence_no(
                    conn, session_id, speaker, utterance_type, text
                )
        except asyncpg.UniqueViolationError:
            record = await _insert_with_next_sequence_no(
                conn, session_id, speaker, utterance_type, text
            )
    return _to_utterance(record)


# 묶음의 끝을 `lead()`로 찾는다 — "다음 발화가 분석 대상이 아니거나 없다"가 곧
# 묶음의 경계다. 데이터 수정 CTE(`enqueued`)와 `run_ends`는 같은 스냅샷을 보므로
# `not exists`가 방금 넣은 행을 보지 못한다(그래서 자기 자신과 충돌하지 않는다).
# 마지막 select로 순서를 확정한다 — `insert ... returning`의 행 순서는 계약이 아니다.
#
# **세션 하나를 걷는 것과 끝난 세션 전체를 걷는 것이 같은 SQL을 쓴다** — 묶음의 정의가
# 두 벌로 갈라지면 한쪽만 고쳐졌을 때 회복 스윕이 턴 경계와 다른 경계를 계산한다.
# 다른 것은 `{session_filter}` 하나뿐이다. `partition by u.session_id`는 단일 세션에서는
# 무의미하지만 스윕에서는 **필수다**: 없으면 전역 `sequence_no` 순서로 섞여 다른 세션의
# 발화가 앞 세션의 묶음을 닫는다.
_RUN_END_FLUSH_TEMPLATE = """
with boundaries as (
      select u.id,
             u.session_id,
             u.sequence_no,
             (u.speaker = $1 and u.utterance_type = $2) as analyzable,
             lead((u.speaker = $1 and u.utterance_type = $2))
               over (partition by u.session_id order by u.sequence_no) as next_analyzable
        from utterances u
       where {session_filter}
),
run_ends as (
      select b.id, b.session_id, b.sequence_no
        from boundaries b
       where b.analyzable
         and not coalesce(b.next_analyzable, false)
         and not exists (
               select 1
                 from analysis_jobs j
                where j.utterance_id = b.id
                  and j.job_type = $3
             )
),
enqueued as (
      insert into analysis_jobs (job_type, utterance_id)
      select $3, r.id from run_ends r
      on conflict do nothing
      returning utterance_id
)
select e.utterance_id
  from enqueued e
  join run_ends r on r.id = e.utterance_id
 -- ⚠️ 이 order by를 지우지 말 것. 제거해도 전체 스위트가 통과한다(실측) — 물리 행
 -- 순서를 테스트에서 통제할 수 없기 때문이고, 불필요하다는 뜻이 아니다. 근거와
 -- 같은 계열의 가드는 `services/analysis.py` `_LOAD_INPUT_SQL`과
 -- `tests/integration/test_pipeline.py`의 ⚠️ 블록이 소유한다. 텍스트 tripwire는
 -- `tests/unit/test_analysis.py`에 있다.
 order by r.session_id, r.sequence_no
"""

_FLUSH_ONE_SESSION_SQL = _RUN_END_FLUSH_TEMPLATE.format(session_filter="u.session_id = $4")

# 회복 스윕은 **끝난** 세션만 본다. 진행 중(`active`) 세션의 마지막 묶음은 아직 자라는
# 중이라, 여기서 걸면 조각 하나가 완전한 문장처럼 분석되는 I-1 결함이 그대로 되살아난다.
_FLUSH_ENDED_SESSIONS_SQL = _RUN_END_FLUSH_TEMPLATE.format(
    session_filter="""u.session_id in (
                 select s.id from learning_sessions s where s.status = any($4::text[])
               )"""
)


async def flush_pending_analysis(conn: asyncpg.Connection, session_id: UUID) -> list[UUID]:
    """턴이 닫힌 사용자 발화 **묶음**마다 분석 job을 1건 등록하고, 그 대상 발화
    id를 `sequence_no` 순으로 돌려준다 (I-1).

    **묶음**은 같은 세션에서 `speaker='user'`·`utterance_type='learning'` 발화가
    `sequence_no`로 연속되며 사이에 다른 발화가 없는 최대 구간이다. job은 그 묶음의
    **마지막 발화**에 걸고, 워커는 그 발화로 끝나는 묶음의 전사문을 이어붙여 입력으로
    쓴다(`services/analysis.py` `_LOAD_INPUT_SQL`) — 두 곳이 같은 묶음 정의를 봐야
    하므로 `ANALYZED_*` 상수를 함께 참조한다.

    묶음의 마지막인지는 **다음 발화**로 판정한다: 뒤에 아무것도 없거나 뒤가 분석
    대상이 아니면(agent 발화·voice_command) 그 발화가 묶음을 닫는다. 그래서 이
    함수는 세션이 진행되는 동안 여러 번 불려도 안전하다 — 조각이 더 붙으면 이전
    조각은 더 이상 묶음의 끝이 아니게 되므로 대상에서 빠진다.

    **이미 job이 있는 발화는 건너뛴다.** `uq_analysis_jobs_pending_utterance`는
    `pending`/`running`만 덮으므로 그것만 믿으면 분석이 끝난(`done`) 묶음이 다음
    flush에서 다시 등록되어 같은 전사문을 Claude로 두 번 보낸다. 세션 하나에서
    flush는 턴마다 + 종료 시 불리므로 이 조건이 없으면 첫 묶음이 턴 수만큼
    재분석된다. `on conflict do nothing`은 두 flush가 겹칠 때의 경합 방어다.
    """
    records = await conn.fetch(
        _FLUSH_ONE_SESSION_SQL,
        ANALYZED_SPEAKER,
        ANALYZED_UTTERANCE_TYPE,
        JOB_TYPE_ANALYZE,
        session_id,
    )
    return [record["utterance_id"] for record in records]


async def flush_ended_sessions(conn: asyncpg.Connection) -> list[UUID]:
    """**끝난** 세션에서 job이 없는 묶음을 걷어 등록한다 — I-1의 회복 경로.

    `flush_pending_analysis`와 같은 묶음 정의를 쓰고(`_RUN_END_FLUSH_TEMPLATE`) 대상
    세션만 다르다. 존재 이유: **러너가 `_close_and_record`까지 도달했는데 그 flush가
    실패한 경우**(연결 획득 실패·SQL 오류)에 그 묶음을 다시 걸어줄 사람이 없다. 잃으면
    결과 화면이 **terminal** 상태 `no_utterances`("분석 대상 없음")를 띄운다
    (`services/results.py` 규칙 2 → 프론트가 폴링을 멈춘다) — 45초를 말한 사용자가
    영구히 그 화면을 본다.

    ⚠️ **이 함수가 덮지 못하는 것: 종료 기록 전에 프로세스가 죽는 경우.** 그러면
    `end_session`이 돌지 않아 세션이 `active`로 남고, 이 스윕은 정의상 `active`를
    건너뛰므로 그 묶음은 **영구히** 걷히지 않는다. 같은 증상(terminal
    `no_utterances`)이 남는다. 해소에는 `active` 고아 세션 리퍼가 필요하고, 그것은
    "얼마나 오래 `active`면 죽은 것인가"라는 새 발명값을 요구해 I-1 범위 밖이다 —
    별건으로 `TASKS.md` **I-4**가 소유한다. 코드 리뷰가 잡은 과대 주장이다.

    **`active` 세션을 포함하지 않는 것이 이 함수의 안전성 전부다.** 진행 중 세션의
    마지막 묶음은 사용자가 말하는 중이라 아직 자란다. 그것을 걸면 조각 하나가 완전한
    문장처럼 분석되는 I-1 결함이 되살아난다 — 고치려던 것을 회복 경로가 되돌리는 셈이다.

    비용: 끝난 세션의 발화를 훑는 seq scan 1회다. 워커는 **큐가 비었을 때만** 부르므로
    (`workers/analysis_worker.py`) 분석이 밀리는 동안에는 돌지 않는다 — 단 **유휴
    정상 상태에서는 poll 주기마다 돈다**(기본 1초 = 1 Hz). 실측(코드 리뷰,
    `explain analyze`): Execution Time **0.400 ms**. 단일 사용자 로컬 도구 기준으로
    이 비용을 받아들였다 — 이력이 커져 문제가 되면 그때 좁힌다. 시간 창으로 자르지
    않은 이유는 워커가 그 창보다 오래 내려가 있으면 **조용히** 묶음을 잃기 때문이다.
    """
    records = await conn.fetch(
        _FLUSH_ENDED_SESSIONS_SQL,
        ANALYZED_SPEAKER,
        ANALYZED_UTTERANCE_TYPE,
        JOB_TYPE_ANALYZE,
        list(ENDED_SESSION_STATUSES),
    )
    return [record["utterance_id"] for record in records]


async def pending_learning_utterances(conn: asyncpg.Connection) -> list[UtteranceRow]:
    """Utterances still waiting on analysis: the user's learning speech whose
    `analyze_utterance` job has not reached a terminal state (`done`/`failed`).

    `exists` rather than a join — even though the partial unique index allows at
    most one live job per utterance, a semi-join can never fan a row out.
    `created_at` alone does not order rows written in one transaction (they
    share the transaction timestamp), so the sort key ends in `sequence_no`.
    """
    records = await conn.fetch(
        f"""
        select {_SELECT_COLUMNS}
          from utterances u
         where u.speaker = $1
           and u.utterance_type = $2
           and exists (
                 select 1
                   from analysis_jobs j
                  where j.utterance_id = u.id
                    and j.job_type = $3
                    and j.status in ('pending', 'running')
               )
         order by u.created_at, u.session_id, u.sequence_no
        """,
        ANALYZED_SPEAKER,
        ANALYZED_UTTERANCE_TYPE,
        JOB_TYPE_ANALYZE,
    )
    return [_to_utterance(record) for record in records]
