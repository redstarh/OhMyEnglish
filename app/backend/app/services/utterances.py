"""Transcript persistence — utterance append + atomic analysis enqueue (설계서 §5.2, W1/W6).

Two invariants live here:

* **`sequence_no`는 서버가 세션 안에서 단조 증가로 부여한다.** 클라이언트가 보낸
  값을 믿지 않는다. 부여와 insert가 한 문장이라 `select max()` 후 다른 문장에서
  insert할 때 생기는 틈이 없고, 그래도 두 연결이 같은 번호를 잡으면
  `unique (session_id, sequence_no)`가 이중 commit을 막는다 (001 스키마 주석).
* **전사문과 분석 job은 원자적으로 함께 남는다.** 두 write 모두 호출자가 준
  `conn`에서 실행하므로 `app.db.tx()` 하나의 트랜잭션에 들어간다. 발화만 남고
  job이 없으면 그 발화는 영원히 분석되지 않고, job만 남고 발화가 없으면 워커가
  읽을 입력이 없다 — 둘 다 데이터 정합성 붕괴라 부분 성공을 허용하지 않는다.

분석 job은 **사용자의 learning 발화에만** 등록한다 (W6). agent 발화와
voice_command / command_confirmation은 저장은 되지만 교정 대상이 아니다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

from app.services.jobs import enqueue_analyze

# 분석 대상 발화의 정의 (W6). enqueue 조건과 `pending_learning_utterances`의
# 선택 조건이 갈라지지 않도록 두 곳이 이 상수를 함께 참조한다.
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


def _is_analyzable(speaker: str, utterance_type: str) -> bool:
    return speaker == ANALYZED_SPEAKER and utterance_type == ANALYZED_UTTERANCE_TYPE


async def save_final_transcript(
    conn: asyncpg.Connection,
    session_id: UUID,
    text: str,
    *,
    speaker: str = "user",
    utterance_type: str = "learning",
) -> UtteranceRow:
    """Append a finalized transcript to its session and, for the user's learning
    speech, enqueue its analysis job in the caller's transaction.

    `sequence_no` is derived inside the insert (`max(sequence_no) + 1` over the
    session), so the number is assigned by the database rather than by the
    caller. Partial transcripts are never stored — only `final` events reach
    here (`TranscriptEvent.kind == "final"`).
    """
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
    utterance = _to_utterance(record)

    if _is_analyzable(speaker, utterance_type):
        # 같은 conn = 같은 트랜잭션. 중복 등록은 None을 돌려줄 뿐 예외를 올리지
        # 않으므로(`enqueue_analyze`) 전사문 저장이 중복 job 때문에 깨지지 않는다.
        await enqueue_analyze(conn, utterance.id)

    return utterance


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
                    and j.job_type = 'analyze_utterance'
                    and j.status in ('pending', 'running')
               )
         order by u.created_at, u.session_id, u.sequence_no
        """,
        ANALYZED_SPEAKER,
        ANALYZED_UTTERANCE_TYPE,
    )
    return [_to_utterance(record) for record in records]
