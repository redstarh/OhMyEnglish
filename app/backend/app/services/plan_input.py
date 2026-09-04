"""계획 입력 3계층(설계서 §4)을 한 자료구조로 모은다. **읽기 전용 모듈이다.**

전체 이력을 매번 넣지 않는 이유는 §4가 정한 그대로다 — 비용과 지연을 무의미하게 늘린다.
여기서 하는 일은 **사실을 모으는 것**뿐이고 무엇이 약점인지·무엇을 연습할지는 Claude가
판단한다(§3.2의 승인된 경계). 그래서 이 모듈에는 점수식도 임계값도 없다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

import asyncpg

from app.services.chronic import ChronicMetric, load_chronic_metrics
from app.services.review import DueReview, load_completed_then_relapsed, load_due_reviews
from app.services.utterances import ANALYZED_SPEAKER, ANALYZED_UTTERANCE_TYPE

# §4.2: 복습 최장 간격 7일의 2배. 설계서가 **유도값**임을 명시했으므로 바꿀 때 설계서를 함께 고친다.
RECENT_WINDOW_DAYS = 14

_TIMEZONE_SQL = "select timezone, current_level from users where id = $1"

# 대소문자를 가린다(리뷰 M2) — `pg_timezone_names.name`은 대소문자를 구분하지만
# `at time zone`(chronic.py가 실제로 쓰는 연산자)은 구분하지 않는다(2026-09-04 실측:
# `at time zone 'asia/seoul'`은 정상 동작). `users.timezone`에 CHECK가 없어 소문자 값이
# 들어올 수 있으므로, 이 검증이 DB 연산자보다 엄격하면 **동작하는 설정을 여기서만 거부**하게 된다.
_VALID_TIMEZONE_SQL = (
    "select exists (select 1 from pg_timezone_names where lower(name) = lower($1))"
)

# §4.2: 최근 창의 **학습자의 학습 발화만** 본다 — 말한 사람(`speaker`)과 발화 종류
# (`utterance_type`) 둘 다 걸러야 한다. 코치(`agent`) 발화도 `utterance_type='learning'`으로
# 저장되므로(`utterances.py`의 기본값) 종류만 걸면 코치 발화가 섞여 들어온다(리뷰 Important-1,
# 2026-09-04 dev DB 실측: 14일 창 92행 중 54행이 코치 발화였다). `ANALYZED_SPEAKER`·
# `ANALYZED_UTTERANCE_TYPE`은 같은 뜻을 재는 다른 세 곳(`analysis.py`·`utterances.py` 2곳)과
# 공유하는 단일 출처다 — 리터럴을 다시 쓰지 않는다.
# 창의 양끝을 다 건다(리뷰 M1) — `window_to`가 `PlanInput`에 닫힌 구간으로 기록되고
# (`learner_notes.window_from/window_to`로 이어진다), 하한만 걸면 그 주장이 거짓이 된다.
# 한 발화에 붙은 교정이 0~여러 건일 수 있어 `error_occurrences`를 left join한다 — 교정이
# 없는 발화도 "말했다"는 사실 자체가 계획 입력이다.
_RECENT_SQL = """
select u.id as utterance_id, u.created_at as said_at, u.transcript,
       eo.id as occurrence_id, p.pattern_key, p.category,
       eo.original_span, eo.correction, eo.explanation, eo.severity, eo.confidence
  from utterances u
  join learning_sessions s on s.id = u.session_id
  left join error_occurrences eo on eo.utterance_id = u.id
  left join error_patterns p on p.id = eo.pattern_id
 where s.user_id = $1
   and u.speaker = $2
   and u.utterance_type = $3
   and u.created_at >= $4
   and u.created_at <= $5
 order by u.created_at, u.id, eo.id
"""

# §4.4: 003이 `target_sound`를 nullable로 두었다(`outcome='incorrect'`이고 키가 있을 때만
# 채운다) — 키 없는 행은 "어느 소리인지 모르는 시도"라 초점 패턴 후보가 될 수 없으므로 함께
# 거른다. `outcome <> 'pending'`은 이연 항목 §4.4 주의 1: 미판정은 계획 근거가 아니다.
# 발음 `frequency`(시도 수 기준)는 문법의 occurrence 수 기준과 계산이 다르므로(§4.4 주의 2)
# 카테고리별로 따로 낸다 — 여기서 문법 패턴과 한 정렬에 섞지 않는다.
# 창의 양끝을 다 건다(리뷰 M1, 위 `_RECENT_SQL`과 같은 이유).
_PRONUNCIATION_SQL = """
select a.target_sound, a.outcome, count(*) as attempts, max(a.created_at) as last_seen
  from pronunciation_attempts a
  join learning_sessions s on s.id = a.session_id
 where s.user_id = $1
   and a.created_at >= $2
   and a.created_at <= $3
   and a.outcome <> 'pending'
   and a.target_sound is not null
 group by a.target_sound, a.outcome
 order by a.target_sound, a.outcome
"""


class InvalidTimezoneError(ValueError):
    """`users.timezone`이 Postgres가 모르는 값이다 (이연 LOW-14).

    조용히 UTC로 떨어지지 않는 이유: 이 값은 달력 날짜 계산의 SoT이고, UTC로 흘리면
    재발 일수가 하루씩 어긋난 채 계획이 만들어진다(함정 H-S). 틀린 계획보다 실패가 낫다.
    """


@dataclass(frozen=True, slots=True)
class RecentCorrection:
    """발화 하나에 붙은 교정 한 건. DB 컬럼 이름을 그대로 쓴다 — `explanation`이다.

    `reason`으로 쓰지 않는 이유: 이 값은 Claude 프롬프트로 가는 내부 값이고, `reason`은
    이미 `session_plans.reason`(학습자에게 보여줄 추천 이유)이 쓰고 있어 이름이 겹치면
    서로 다른 두 값이 같은 말로 불린다.
    """

    pattern_key: str
    category: str
    original_span: str
    correction: str
    explanation: str
    severity: str
    confidence: float


@dataclass(frozen=True, slots=True)
class RecentUtterance:
    """최근 창(14일) 안의 학습 발화 한 건 — 교정이 없으면 `corrections`가 빈 튜플이다.

    `tuple`인 이유(리뷰 M6): 이 클래스는 `frozen=True`인데 예전 구현은 `list`를 만들고
    `.append()`로 채워 "불변"이라는 이름과 실제가 어긋났다 — 필드 재할당은 막히지만 리스트
    내용은 바깥에서 여전히 바뀔 수 있었다. `_load_recent`가 조립을 마친 뒤 `tuple`로 굳힌다.
    """

    said_at: datetime
    transcript: str
    corrections: tuple[RecentCorrection, ...]


@dataclass(frozen=True, slots=True)
class PronunciationTally:
    """발음 시도 집계 한 건(소리·판정 조합). `pending`은 이미 제외됐다(§4.4 주의 1)."""

    target_sound: str
    outcome: str
    attempts: int
    last_seen: datetime


@dataclass(frozen=True, slots=True)
class PlanInput:
    """계획 생성 프롬프트가 조립할 3계층 재료 (설계서 §4) — 사실만 담고 판단은 없다."""

    user_id: UUID
    timezone: str
    window_from: datetime
    window_to: datetime
    current_level: str
    due_reviews: list[DueReview]
    chronic: list[ChronicMetric]
    chronic_pattern_ids: set[UUID]
    recent: list[RecentUtterance]
    pronunciation: list[PronunciationTally]


async def _load_recent(
    conn: asyncpg.Connection, user_id: UUID, window_from: datetime, window_to: datetime
) -> list[RecentUtterance]:
    records = await conn.fetch(
        _RECENT_SQL, user_id, ANALYZED_SPEAKER, ANALYZED_UTTERANCE_TYPE, window_from, window_to
    )
    said_at_by_utterance: dict[UUID, datetime] = {}
    transcript_by_utterance: dict[UUID, str] = {}
    corrections_by_utterance: dict[UUID, list[RecentCorrection]] = {}
    order: list[UUID] = []
    for record in records:
        utterance_id = record["utterance_id"]
        if utterance_id not in corrections_by_utterance:
            said_at_by_utterance[utterance_id] = record["said_at"]
            transcript_by_utterance[utterance_id] = record["transcript"]
            corrections_by_utterance[utterance_id] = []
            order.append(utterance_id)
        if record["occurrence_id"] is not None:
            corrections_by_utterance[utterance_id].append(
                RecentCorrection(
                    pattern_key=record["pattern_key"],
                    category=record["category"],
                    original_span=record["original_span"],
                    correction=record["correction"],
                    explanation=record["explanation"],
                    severity=record["severity"],
                    confidence=float(record["confidence"]),
                )
            )
    return [
        RecentUtterance(
            said_at=said_at_by_utterance[utterance_id],
            transcript=transcript_by_utterance[utterance_id],
            corrections=tuple(corrections_by_utterance[utterance_id]),
        )
        for utterance_id in order
    ]


async def _load_pronunciation(
    conn: asyncpg.Connection, user_id: UUID, window_from: datetime, window_to: datetime
) -> list[PronunciationTally]:
    records = await conn.fetch(_PRONUNCIATION_SQL, user_id, window_from, window_to)
    return [
        PronunciationTally(
            target_sound=record["target_sound"],
            outcome=record["outcome"],
            attempts=record["attempts"],
            last_seen=record["last_seen"],
        )
        for record in records
    ]


async def load_plan_input(conn: asyncpg.Connection, user_id: UUID) -> PlanInput:
    row = await conn.fetchrow(_TIMEZONE_SQL, user_id)
    if row is None:
        raise LookupError(f"user {user_id} not found")
    tz = row["timezone"]
    if not await conn.fetchval(_VALID_TIMEZONE_SQL, tz):
        raise InvalidTimezoneError(f"users.timezone is not a known zone: {tz!r}")

    window_to = await conn.fetchval("select clock_timestamp()")
    window_from = window_to - timedelta(days=RECENT_WINDOW_DAYS)

    return PlanInput(
        user_id=user_id,
        timezone=tz,
        window_from=window_from,
        window_to=window_to,
        current_level=row["current_level"],
        due_reviews=await load_due_reviews(conn, user_id),
        chronic=await load_chronic_metrics(conn, user_id),
        chronic_pattern_ids=await load_completed_then_relapsed(conn, user_id),
        recent=await _load_recent(conn, user_id, window_from, window_to),
        pronunciation=await _load_pronunciation(conn, user_id, window_from, window_to),
    )
