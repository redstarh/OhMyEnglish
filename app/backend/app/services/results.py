"""세션 결과 조회 — 상태 판정(R2) + 상위 2개 교정 선정(R1) + 부분 실패 표시(R3)
(설계서 §5.5, AC 문서 R1~R3).

이 모듈이 지키는 계약은 하나다: **R2의 다섯 규칙은 우선순위 순서대로 정확히
하나만** 매칭된다. 위에서부터 차례로 확인해 처음 맞는 것을 돌려주고, 그 뒤
규칙은 보지 않는다.

1. `learning_sessions.status='failed'` → `connection_failed` — 이 세션의 job이
   무엇이든 상관없다. 연결 실패가 분석 진행 상태보다 우선한다.
   ⚠️ `failed`를 만드는 곳은 연결 실패만이 아니다 — **고아 세션 리퍼**(I-4,
   `sessions.reap_orphan_sessions`)가 프로세스 사망으로 `active`에 남은 세션도
   `failed`로 닫는다. 그래서 이 규칙은 그 세션의 회복된 분석까지 함께 가린다:
   리퍼→스윕이 묶음을 걷어 분석을 끝내도 화면은 `connection_failed`다. 누적
   데이터(오류 패턴·숙련도)는 갱신되므로 잃는 것은 그 세션의 교정 표시뿐이다.
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

드릴 exchange 관측(§2.3 · 캡틴 결정 10·16)은 `corrections`와 **같은 R2 규약**을 따른다:
`analyzing`/`connection_failed`/`no_utterances`에서는 `drill`이 `None`이고 그때는
**미달 판정 자체를 하지 않아 로그도 나지 않는다.** 억제가 필요한 이유는 방어가 아니라
정상 경로다 — 어댑터 생성이 실패해 `learning_sessions.status='failed'`가 된 세션도
기대값은 이미 쓰여 있고(설계가 정한 순서: 계획을 읽은 뒤 어댑터를 만든다) 아래 규칙 1이
그 `'failed'`를 `connection_failed`로 매핑하므로, 막지 않으면 **연결 실패마다 「미달」이
API와 로그에 쌓인다.** 결정 10이 이 두 수의 용도를 「지시문을 고치는 입력」 하나로 정했는데
연결이 끊겨 끝난 세션의 미달은 지시문에 대해 아무것도 말하지 않는다 — 그 신호를 오염시킨다.

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

import logging
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

import asyncpg

# 묶음 정의의 정본은 `services/utterances.py`다 — 두 값을 여기서 리터럴로 다시 적으면 스윕이 걸
# 대상과 이 응답이 말하는 대상이 갈라진다(`_ANALYZABLE_UTTERANCES_SQL` 주석). 순환은 없다:
# `utterances.py`는 `jobs`·`sessions`만 import 한다.
from app.services.utterances import ANALYZED_SPEAKER, ANALYZED_UTTERANCE_TYPE

logger = logging.getLogger(__name__)

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
class DrillTurns:
    """드릴이 계획만큼 돌았는지 (설계서 §2.3 · 캡틴 결정 10·16).

    **두 수의 소비자는 서버와 로그다** — 「지시문을 고치는 입력」이 결정 10이 정한 용도
    하나이고, 화면은 이것을 렌더하지 않는다(`9 / 12`로 읽히면 가장 점수처럼 보이는 모양이고,
    미달의 주어는 학습자가 아니라 대화 모델이다). 그 어긋나 보이는 계약은 의도된 것이다.
    """

    exchanges_observed: int
    exchanges_expected: int


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
    # `corrections`와 **같은** 규약이다: `None`은 "응답에 `drill` 키 자체가 없다"는 뜻이고
    # R2 규칙 1·2·3에서 그렇게 된다. 계획 없이 시작한 세션(기대값 null)도 `None`이다 —
    # 그 세션은 관측 대상이 아니다(009: null = 기대가 없었다).
    drill: DrillTurns | None
    # `TASK-79` — **분석 대상 발화는 있는데 그 job 이 아직 하나도 없다.** 종료 flush 가 실패한
    # 세션의 모양이고(`api/ws._flush_analysis`가 예외를 삼킨다), `flush_ended_sessions`가
    # 나중에 그 묶음을 걷으므로 **그 `no_utterances`는 영구가 아니다.**
    #
    # ⚠️ **왜 이 필드가 필요한가**: 화면이 「지금 멈춰도 되는가」를 알 근거가 없었다. 이전 판은
    # 프론트 상수(`NO_UTTERANCES_RECHECKS = 3`, 약 6초)로 버텼는데 **스윕이 언제 도는지 보장하는
    # 계약이 없어 어떤 상수도 맞을 수 없다** — 게다가 워커는 큐가 빌 때만 스윕하므로 분석이
    # 밀리는 동안에는 아예 돌지 않는다(`services/utterances.flush_ended_sessions` 비용 절).
    #
    # ⛔ **「스윕이 돌았는가」를 묻지 않는다.** 그 질문은 큐가 밀린 상황에서 영구히
    # 답이 「아니오」라 지연 시나리오를 그대로 남긴다.
    # 대신 **「걸릴 대상이 남아 있는가」**를 묻는다 — 워커 상태와 무관한 DB 사실이다.
    # 발화가 있고 job 이 0건이면 묶음 끝 가운데 job 없는 것이 반드시 있다
    # (`_RUN_END_FLUSH_TEMPLATE`의 묶음 정의상 마지막 분석 대상 발화가 묶음 끝이다).
    # 그래서 이 조건이 스윕 대상 존재와 같은 뜻이다.
    #
    # ⛔ **`status`를 바꾸지 않는다** — R2 규칙 2 는 그대로다. 응답 키를 **더할** 뿐이라 기존
    # 소비자와 보존 표본이 깨지지 않는다. `pronunciation`과 같은 규약으로 **항상 실린다**
    # (`corrections`·`drill`의 키 생략 규약을 따르지 않는다): 프론트가 상태마다 키 존재를
    # 갈라 읽지 않게 한다.
    awaiting_analysis: bool


_SESSION_ROW_SQL = """
select status, drill_turns_expected
  from learning_sessions
 where id = $1
"""

# 실제 exchange 수 — **「코치 발화 바로 뒤에 온 사용자 발화」**를 센다(설계서 §2.3).
#
# ⛔ `count(*) … where speaker = 'agent'`가 아니다(H-3). `SYSTEM_PROMPT` 규칙 2·5가 침묵 뒤
# 시작 힌트를 **명령**하므로 학습자가 막히면 코치 발화 행만 늘고, 그때 `_flush_analysis`는
# 대기 발화가 없어 no-op이다 — **턴이 닫히지 않았는데 수만 오른다.** 전이를 세면 연속 코치
# 발화(힌트 반복)와 코치 선발화가 세어지지 않아 그 경로가 닫힌다.
# ⛔ 방향을 뒤집지 않는다(4판 정정). 3판은 `speaker='agent' and prev='user'`였고, 그러면
# 세션이 학습자 발화로 끝나는 정상 종료 모양에서 **완전 순응 세션도 1만큼 미달**로 세어졌다.
# `utterance_type = 'learning'`을 함께 거른다 — `plan_input.py`·`utterances.py`의 두 SQL이
# speaker와 함께 거르는 관례이고, 음성 명령이 exchange를 만들지 않는다.
#
# 새 감지기가 아니다: 세는 규칙은 실시간 턴 판별(`audio_gateway/session.py`)과 같은 것이고
# 저장된 순서(`sequence_no`)로 사후에 같은 판정을 한다. ⛔ 그래서 카운터를 `_flush_analysis`
# 경로에 얹지 않는다 — 그 함수는 예외를 밖으로 던지지 않는 계약이라 세는 일이 그 침묵 안으로
# 들어가면 누락이 관측되지 않는다.
_EXCHANGES_OBSERVED_SQL = """
select count(*) from (
  select speaker, lag(speaker) over (order by sequence_no) as prev
    from utterances
   where session_id = $1
     and utterance_type = 'learning'
) t
where t.speaker = 'user' and t.prev = 'agent'
"""

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

# `TASK-79` — 분석 대상 발화가 있는가. **`_JOB_COUNTS_SQL`에 합치지 않는다**: 그쪽은
# `join utterances`라서 job 없는 발화가 join 에서 빠지고, `left join`으로 바꾸면 `total`의 뜻이
# 「job 수」에서 「발화 수」로 조용히 옮겨 간다 — R2 규칙 2·3 이 그 수에 걸려 있다.
#
# 두 값(`speaker`·`utterance_type`)의 정본은 `services/utterances.py`다 — 여기서 리터럴로 다시
# 적으면 묶음 정의가 갈라지고, 갈라진 쪽은 조용히 틀린다(스윕은 걸 대상이 있는데 응답은 없다고
# 말하거나 그 반대).
_ANALYZABLE_UTTERANCES_SQL = """
select count(*)
  from utterances u
 where u.session_id = $1
   and u.speaker = $2
   and u.utterance_type = $3
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


async def _load_drill(
    conn: asyncpg.Connection, session_id: UUID, expected: int | None
) -> DrillTurns | None:
    """실제 exchange 수를 세어 기대값과 함께 돌려준다. 미달이면 `warning` 한 줄을 남긴다.

    **기대값이 `None`이면 세지도 않는다** — 계획 없이 시작한 세션은 관측 대상이 아니다(009).
    `INFO`가 아니라 `warning`인 이유는 함정 **H-Z**다: 문서가 지정한 실행에서 INFO는 보이지
    않으므로 미달이 조용히 지나간다.

    ⛔ **호출자는 R2 규칙 1·2·3에서 이 함수를 부르지 않는다** — 그 세 상태에서는 미달 판정
    자체를 하지 않는다(모듈 docstring). 그 조건을 여기 두지 않은 것은 판정이 이미 호출
    지점에서 if/elif 사슬로 표현돼 있어서다: 상태를 인자로 받아 다시 분기하면 "정확히
    하나"를 보장하는 그 구조가 둘로 갈라진다.
    """
    if expected is None:
        return None
    observed: int = await conn.fetchval(_EXCHANGES_OBSERVED_SQL, session_id)
    if observed < expected:
        logger.warning(
            "세션 %s: 드릴 exchange 미달 — 관측 %d건 / 기대 %d건 "
            "(지시문을 고치는 입력이다 — 캡틴 결정 10)",
            session_id,
            observed,
            expected,
        )
    return DrillTurns(exchanges_observed=observed, exchanges_expected=expected)


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

    드릴 관측은 반대로 사슬 **안**에 있다 — `corrections`와 같은 자리에서만 실린다.
    규칙 1·2·3은 `drill=None`으로 돌려주고 세지도 로그하지도 않는다(모듈 docstring).
    """
    session = await conn.fetchrow(_SESSION_ROW_SQL, session_id)
    if session is None:
        return None

    pronunciation = await _load_pronunciation(conn, session_id)

    # 규칙 1 — 연결 실패는 job 상태를 보지 않고 최우선한다.
    #
    # ⚠️ `awaiting_analysis`가 **여기서만** 정의상 확정이 아니다: 이 분기는 job 수를 세지 않으므로
    # 「발화는 있고 job 은 0건」인지 알 수 없다. `False`로 두는 이유는 이 상태에서 그 값이 판정에
    # 쓰이지 않기 때문이다 — 화면은 `connection_failed`를 종단으로 보고 즉시 멈춘다(`TASK-56`).
    # ⛔ 값을 얻으려고 job 쿼리를 이 분기 위로 올리지 않는다: 그러면 *"job 상태를 보지 않고
    # 최우선한다"*는 이 규칙의 서술이 코드와 어긋나 보인다.
    if session["status"] == "failed":
        return SessionResult(
            status="connection_failed",
            corrections=None,
            partial_failure=False,
            pronunciation=pronunciation,
            drill=None,
            awaiting_analysis=False,
        )

    counts = await conn.fetchrow(_JOB_COUNTS_SQL, session_id)

    # 규칙 2 — 분석 대상 자체가 없다.
    #
    # `TASK-79` — **같은 상태가 두 가지 뜻을 가진다.** 발화가 0건이면 영구이고, 발화가 있는데
    # job 만 0건이면 종료 flush 가 실패한 것이라 회복 대상이다. 그 갈림을 응답이 알려 화면이
    # 폴링을 이어갈 근거로 쓴다. **여기가 그 조건이 성립할 수 있는 유일한 분기다** — 아래 규칙
    # 3·4·5 는 `counts["total"] > 0`이므로 정의상 거짓이다.
    if counts["total"] == 0:
        analyzable = await conn.fetchval(
            _ANALYZABLE_UTTERANCES_SQL, session_id, ANALYZED_SPEAKER, ANALYZED_UTTERANCE_TYPE
        )
        return SessionResult(
            status="no_utterances",
            corrections=None,
            partial_failure=False,
            pronunciation=pronunciation,
            drill=None,
            awaiting_analysis=analyzable > 0,
        )

    # 규칙 3 — 진행 중인 job이 있으면 결과가 확정되지 않았다. 교정을 계산조차
    # 하지 않는다 — 계산해서 숨기는 것과 계산하지 않는 것은 "잠정 노출 금지"
    # 원칙 아래 같은 결과이지만, 후자가 실수로 새어나갈 표면을 만들지 않는다.
    # 드릴 관측도 같은 이유로 계산하지 않는다: 세면 미달 로그가 따라온다.
    if counts["non_terminal"] > 0:
        return SessionResult(
            status="analyzing",
            corrections=None,
            partial_failure=False,
            pronunciation=pronunciation,
            drill=None,
            # 여기 아래는 전부 `counts["total"] > 0`이라 정의상 거짓이다(규칙 2 주석).
            awaiting_analysis=False,
        )

    drill = await _load_drill(conn, session_id, session["drill_turns_expected"])

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
            drill=drill,
            awaiting_analysis=False,
        )

    # 규칙 5 — 1건 이상이고 전부 done.
    corrections = await _load_top_corrections(conn, session_id)
    return SessionResult(
        status="final",
        corrections=corrections,
        partial_failure=False,
        pronunciation=pronunciation,
        drill=drill,
        awaiting_analysis=False,
    )
