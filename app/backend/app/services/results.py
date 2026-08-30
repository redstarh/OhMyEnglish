"""세션 결과 조회 — 상태 판정(R2) + 상위 2개 교정 선정(R1) + 부분 실패 표시(R3)
(설계서 §5.5, AC 문서 R1~R3).

이 모듈이 지키는 계약은 하나다: **R2의 다섯 규칙은 우선순위 순서대로 정확히
하나만** 매칭된다. 위에서부터 차례로 확인해 처음 맞는 것을 돌려주고, 그 뒤
규칙은 보지 않는다.

1. `learning_sessions.status='failed'` → `connection_failed` — 이 세션의 job이
   무엇이든 상관없다. 연결 실패가 분석 진행 상태보다 우선한다.
2. `analyze_utterance` job이 0건 → `no_utterances` — 빈 결과를 확정처럼
   보여주는 경로를 여기서 차단한다.
3. non-terminal(`pending`/`running`) job이 하나라도 있으면 → `analyzing`이고,
   이때 **교정 목록을 응답에 포함하지 않는다.** 이미 `done`인 발화가 있어도
   보여주지 않는다 — 잠정 결과를 확정처럼 노출하는 것을 막는 것이 이 규칙의
   전부다(§5.5).
4. `failed` job이 하나라도 있으면(그리고 non-terminal이 없으면) →
   `partial_failure`. 성공분(`done`) 교정은 포함한다.
5. 그 외(1건 이상이고 전부 `done`) → `final`.

상위 2개 선정(R1)은 세션의 `error_occurrences` ⨝ `utterances(session_id)` ⨝
`error_patterns` 조인을 **패턴 단위**로 묶어 `severity ordinal desc → 패턴 내
max(confidence) desc → 발생 수 desc` 순으로 정렬한다. `severity`는
`('low','medium','high')` 텍스트 컬럼이라 텍스트 `desc`를 쓰면 `medium`이
`high`보다 앞서는 함정이 있다(§5.5) — 그래서 `case ... end`로 ordinal을 만들어
정렬한다.

이 조인은 세션 범위로 한정되므로, 재분석으로 패턴이 사라져 `frequency=0`으로
남은 행(§5.2 replace — 행은 지우지 않는다)은 **이 세션에 연결된 occurrence가
없으면 자연히 걸러진다**: `error_occurrences`에 대한 inner join이 그 패턴을
아예 만들지 않는다. 별도 필터가 필요 없다.

패턴 하나에 여러 occurrence(같은 오류가 여러 문장에)가 있을 때 대표로 보여줄
`original_span`/`correction`/`explanation`(AC U2 "한 줄 이유" → 응답의 `reason`)은
그 패턴의 **가장 최근 발화**(`utterances.created_at` 최댓값) 것을 쓴다 —
`error_patterns.last_seen_at`(§5.2)과 같은 최신성 규칙을 따른 것이며, 임의의
한 행을 고르는 것보다 근거가 있다.

발음 카드(Task 8)는 **R2 판정과 독립적으로** 실린다. 다섯 규칙 중 어느 것이
매칭되든 같은 배열이 응답에 들어가고, 비어 있으면 빈 리스트다 —
`corrections`처럼 `None`으로 키를 지우지 않는다. 근거는 규칙 3이 막는 것이
*비동기 분석이 끝나지 않은* 문법 교정의 잠정 노출이라는 점이다: 발음 시도 행은
실시간 Nova 이벤트에서 만들어지고 종료 수렴(§3.2)이 `pending`을 없애므로
구조적으로 확정값이다. 그래서 `analyzing` 중에도 보여주는 것이 "잠정 결과를
확정처럼 노출"에 해당하지 않는다. 표시 규약(기계 키 미노출 · 시도 1건 = 1카드)의
정본은 설계서 §10 미결 4다.

Fix round 1 (I-1): 같은 발화의 같은 패턴에 occurrence가 2건 이상이면
`utterance_created_at`/`occurrence_created_at`이 완전히 동률일 수 있다 —
`_replace_occurrences`(§5.2)가 findings 전체를 **한 트랜잭션**에서 insert하고,
PostgreSQL의 `now()`는 트랜잭션 시작 시각으로 고정되므로 `error_occurrences.created_at`
이 마이크로초까지 같아진다. 이 동률을 그대로 두면 `distinct on`이 물리 스캔
순서에 좌우돼 대표 문구 선택이 비결정적이다. `eo.id`(uuid — 시간 순서는 아니지만
행마다 다르다)를 tie-break의 마지막 열로 추가해 **재조회 안정성**만 확보한다:
어떤 occurrence가 선택되는지 자체는 의미가 없고, 매번 같은 것이 선택되는지가
중요하다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import asyncpg

SessionResultStatus = Literal[
    "analyzing", "final", "partial_failure", "connection_failed", "no_utterances"
]

# PRD.md:29 "세션당 핵심 오류 1~2개 교정" — 상위 2개로 고정한다.
MAX_CORRECTIONS = 2


@dataclass(frozen=True, slots=True)
class Correction:
    pattern_key: str
    category: str
    original_span: str
    correction: str
    reason: str
    target_form: str
    occurrences: int


@dataclass(frozen=True, slots=True)
class PronunciationAttempt:
    """결과 화면 발음 카드 1장 (Task 8).

    ⚠️ **기계 키를 담지 않는다.** `pronunciation_attempts.target_sound`(예 `th_as_s`)와
    그것으로 만든 패턴 `target_form`은 이 계약에 없다 — 설계서 §10 미결 4 결정.
    `target_form`은 **이 표의** 컬럼이고 Nova가 시범한 문장(또는 신호 행의 설명 문구)이다.
    """

    target_form: str
    # 시범 시점에는 아직 못 들었고(003), 대답 없이 끝난 시도는 수렴 후에도 없다(§3.2).
    # 그래서 `None`이 정상값이며 API는 키를 지우지 않고 `null`로 싣는다.
    spoken_form: str | None
    outcome: str
    # 신호 행(`korean_transcript`)의 `target_form`은 시범 문장이 아니라 설명 문구다 —
    # 이 값 없이 렌더하면 그 문구가 "이렇게 발음하세요"로 보인다(TASKS.md A-2 후단 ①).
    signal_source: str


@dataclass(frozen=True, slots=True)
class SessionResult:
    status: SessionResultStatus
    # `None`은 "이 상태에서는 응답에 `corrections` 키 자체가 없다"는 뜻이다
    # (R2 규칙 3: analyzing / 규칙 1: connection_failed / 규칙 2: no_utterances).
    # API 계층이 이 구분을 JSON 키 존재 여부로 옮긴다.
    corrections: list[Correction] | None
    partial_failure: bool
    # R2 판정과 **독립**이다 — 5개 상태 전부에서 실리고, 비어 있으면 빈 리스트다
    # (`corrections`처럼 `None`으로 키를 지우지 않는다). 근거는 모듈 docstring 마지막 절.
    pronunciation: list[PronunciationAttempt]


_SESSION_STATUS_SQL = "select status from learning_sessions where id = $1"

_JOB_COUNTS_SQL = """
select
  count(*) as total,
  count(*) filter (where j.status in ('pending', 'running')) as non_terminal,
  count(*) filter (where j.status = 'failed') as failed
  from analysis_jobs j
  join utterances u on u.id = j.utterance_id
 where u.session_id = $1
   and j.job_type = 'analyze_utterance'
"""

# R1 상위 2개. `occ`가 세션 범위로 한정되므로 다른 세션의 occurrence나 frequency=0
# (occurrence 없이 행만 남은) 패턴은 join에서 자연히 빠진다.
_TOP_CORRECTIONS_SQL = """
with occ as (
  select eo.id as occurrence_id,
         eo.pattern_id,
         eo.original_span,
         eo.correction,
         eo.explanation,
         eo.severity,
         eo.confidence,
         u.created_at as utterance_created_at,
         eo.created_at as occurrence_created_at
    from error_occurrences eo
    join utterances u on u.id = eo.utterance_id
   where u.session_id = $1
),
agg as (
  select pattern_id,
         count(*) as occurrence_count,
         max(confidence) as max_confidence,
         max(case severity when 'high' then 3 when 'medium' then 2 else 1 end) as severity_rank
    from occ
   group by pattern_id
),
representative as (
  select distinct on (pattern_id) pattern_id, original_span, correction, explanation
    from occ
   -- Fix round 1 (I-1): 앞 두 열이 완전히 동률(같은 트랜잭션에서 insert된
   -- occurrence)이어도 `occurrence_id`가 마지막 tie-break로 결과를 고정한다.
   order by pattern_id, utterance_created_at desc, occurrence_created_at desc, occurrence_id
)
select ep.pattern_key,
       ep.category,
       ep.target_form,
       rep.original_span,
       rep.correction,
       rep.explanation,
       agg.occurrence_count
  from agg
  join error_patterns ep on ep.id = agg.pattern_id
  join representative rep on rep.pattern_id = agg.pattern_id
 order by agg.severity_rank desc, agg.max_confidence desc, agg.occurrence_count desc
 limit $2
"""


# 발음 카드(Task 8). R2 다섯 규칙과 **독립**이다 — 판정 로직을 건드리지 않는다.
#
# `outcome <> 'pending'`이 유일한 필터다: 미판정을 학습자에게 보이지 않는다(PS9 단정 3).
# 정상 종료한 세션에는 종료 수렴(§3.2)이 이미 pending을 없앴으므로 이 필터가 거르는 것은
# **아직 끝나지 않은 세션**의 진행 중 시도뿐이다.
#
# `order by attempt_seq`: `created_at`은 `now()` 기본값이라 한 트랜잭션의 두 행이 동값이다
# (004가 이 컬럼을 신설한 이유). ⚠️ `attempt_seq`는 **표 전역** identity라 롤백이 번호에
# 구멍을 낸다 — 정렬에만 쓰고 값 자체는 응답에 싣지 않는다(004 경고). 학습자에게 보이는
# 순번은 배열 위치가 만든다.
_PRONUNCIATION_SQL = """
select target_form, spoken_form, outcome, signal_source
  from pronunciation_attempts
 where session_id = $1
   and outcome <> 'pending'
 order by attempt_seq
"""


async def _load_pronunciation(
    conn: asyncpg.Connection, session_id: UUID
) -> list[PronunciationAttempt]:
    records = await conn.fetch(_PRONUNCIATION_SQL, session_id)
    return [
        PronunciationAttempt(
            target_form=record["target_form"],
            spoken_form=record["spoken_form"],
            outcome=record["outcome"],
            signal_source=record["signal_source"],
        )
        for record in records
    ]


async def _load_top_corrections(conn: asyncpg.Connection, session_id: UUID) -> list[Correction]:
    records = await conn.fetch(_TOP_CORRECTIONS_SQL, session_id, MAX_CORRECTIONS)
    return [
        Correction(
            pattern_key=record["pattern_key"],
            category=record["category"],
            original_span=record["original_span"],
            correction=record["correction"],
            reason=record["explanation"],
            target_form=record["target_form"],
            occurrences=record["occurrence_count"],
        )
        for record in records
    ]


async def get_session_result(conn: asyncpg.Connection, session_id: UUID) -> SessionResult | None:
    """세션 결과를 조회한다. 세션이 없으면 `None` — 호출자(API 계층)가 404로 옮긴다.

    R2의 다섯 규칙을 우선순위 그대로 하나의 if/elif 사슬로 옮긴다: 각 분기는
    앞의 분기가 매칭되지 않았을 때만 평가되므로 "정확히 하나"가 코드 구조로
    보장된다.

    발음 카드는 그 사슬 **밖**에서 한 번 읽어 모든 분기에 같은 값으로 실린다
    (모듈 docstring 마지막 절).
    """
    session = await conn.fetchrow(_SESSION_STATUS_SQL, session_id)
    if session is None:
        return None

    pronunciation = await _load_pronunciation(conn, session_id)

    # 규칙 1 — 연결 실패는 job 상태를 보지 않고 최우선한다.
    if session["status"] == "failed":
        return SessionResult(
            status="connection_failed",
            corrections=None,
            partial_failure=False,
            pronunciation=pronunciation,
        )

    counts = await conn.fetchrow(_JOB_COUNTS_SQL, session_id)

    # 규칙 2 — 분석 대상 자체가 없다.
    if counts["total"] == 0:
        return SessionResult(
            status="no_utterances",
            corrections=None,
            partial_failure=False,
            pronunciation=pronunciation,
        )

    # 규칙 3 — 진행 중인 job이 있으면 결과가 확정되지 않았다. 교정을 계산조차
    # 하지 않는다 — 계산해서 숨기는 것과 계산하지 않는 것은 "잠정 노출 금지"
    # 원칙 아래 같은 결과이지만, 후자가 실수로 새어나갈 표면을 만들지 않는다.
    if counts["non_terminal"] > 0:
        return SessionResult(
            status="analyzing",
            corrections=None,
            partial_failure=False,
            pronunciation=pronunciation,
        )

    # 규칙 4 — 실패한 job이 있다(그리고 진행 중인 job은 없다). 성공분 교정은
    # 그대로 보여준다 — 아래 쿼리는 세션의 occurrence 전체를 보므로 실패한
    # job의 발화는 (occurrence가 없어) 자연히 기여하지 않을 뿐이다.
    if counts["failed"] > 0:
        corrections = await _load_top_corrections(conn, session_id)
        return SessionResult(
            status="partial_failure",
            corrections=corrections,
            partial_failure=True,
            pronunciation=pronunciation,
        )

    # 규칙 5 — 1건 이상이고 전부 done.
    corrections = await _load_top_corrections(conn, session_id)
    return SessionResult(
        status="final",
        corrections=corrections,
        partial_failure=False,
        pronunciation=pronunciation,
    )
