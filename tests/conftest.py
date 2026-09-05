"""Shared pytest fixtures for the OhMyEnglish backend test suite.

DB fixtures recreate the `ohmyenglish_test` database against the same
PostgreSQL server used for local development (see `scripts/dev_db.sh`) and
apply `db/migrations/*.sql` in order. The default `db_conn` fixture is not
pool-based on purpose: each test gets its own connection inside a rolled-back
transaction, so tests never leak state into each other regardless of
execution order.

`db_pool` exists for the code that **owns its own transactions** — the
analysis pipeline and the worker loop commit and re-read across several short
transactions, which a single rolled-back transaction cannot express. Anything
using it writes committed rows, so it must clean up after itself:
`committed_session` deletes its user on teardown and the cascade takes
sessions → utterances → analysis_jobs → error_occurrences (and
error_patterns) with it. Other tests assert on global row counts, so a
committed row that survives its test breaks them.

Task 1 tests (`tests/unit/test_config.py`) do not depend on any fixture
defined here — pytest fixtures are lazy, so no database is touched unless a
test explicitly requests one. Schema-level verification lives in Task 2
(`tests/unit/test_schema.py`).
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import AsyncIterator, Callable, Sequence
from datetime import UTC, datetime, timedelta
from itertools import count
from pathlib import Path
from typing import NamedTuple
from uuid import UUID, uuid4

import asyncpg
import pytest
import pytest_asyncio

# 공통 픽스처 발화 (AC 문서 §공통 픽스처) — 스텁·W-live·E2E-S가 같은 상수를 본다.
# 소유자는 `app.audio_gateway.fixtures` 하나다: 스텁이 재생하는 문장과 테스트가
# 기대하는 문장이 갈라지는 경로를 아예 만들지 않기 위해 여기서는 재수출만 한다.
from app.audio_gateway.fixtures import FIXTURE_TURNS as FIXTURE_TURNS
from app.services.chronic import ChronicMetric
from app.services.jobs import (
    JOB_TYPE_ANALYZE,
    JOB_TYPE_PLAN,
    ClaimedJob,
    claim_next,
    enqueue_plan_next_session,
)
from app.services.plan_input import PlanInput, PronunciationTally, RecentCorrection, RecentUtterance
from app.services.review import DueReview
from app.services.sessions import end_session
from app.workers.claude_client import FakeClaudeClient

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"
TEST_DB_NAME = "ohmyenglish_test"

# `scripts/db_utils.py`는 앱 패키지에 의존하지 않는 독립 모듈이라 일반 패키지
# 경로에 있지 않다 — pytest가 이 conftest를 최상위 모듈로 import할 때는
# 스크립트 실행과 달리 `scripts/`가 자동으로 sys.path에 오르지 않으므로 직접 넣는다.
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from db_utils import recreate_database  # noqa: E402


@pytest.fixture(scope="session")
def test_database() -> str:
    """Recreate `ohmyenglish_test` and apply migrations once per test session.

    Returns the DSN of the freshly migrated test database.
    """
    return asyncio.run(recreate_database(TEST_DB_NAME, MIGRATIONS_DIR))


@pytest_asyncio.fixture
async def db_conn(test_database: str) -> AsyncIterator[asyncpg.Connection]:
    """A connection to the migrated test database, wrapped in a transaction
    that is always rolled back — each test starts from a clean, seeded
    baseline and never leaks writes to the next test."""
    conn = await asyncpg.connect(dsn=test_database)
    transaction = conn.transaction()
    await transaction.start()
    try:
        yield conn
    finally:
        await transaction.rollback()
        await conn.close()


@pytest_asyncio.fixture
async def db_pool(test_database: str) -> AsyncIterator[asyncpg.Pool]:
    """A pool over the migrated test database, for code that owns its own
    transactions (`services.analysis`, `workers.analysis_worker`).

    Writes here **commit** — pair it with `committed_session` (or clean up by
    hand) so nothing survives the test.
    """
    pool = await asyncpg.create_pool(dsn=test_database, min_size=1, max_size=5)
    assert pool is not None
    try:
        yield pool
    finally:
        await pool.close()


class CommittedSession(NamedTuple):
    user_id: UUID
    session_id: UUID


@pytest_asyncio.fixture
async def committed_session(db_pool: asyncpg.Pool) -> AsyncIterator[CommittedSession]:
    """A committed user + `active` learning session, dropped again on teardown.

    Deleting the user cascades to the session → utterances → analysis_jobs →
    error_occurrences and to error_patterns, so the test leaves the database
    exactly as it found it even though its writes were committed.
    """
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval(
            "insert into users (display_name) values ('Pipeline Test User') returning id"
        )
        session_id = await conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
            user_id,
        )
    try:
        yield CommittedSession(user_id=user_id, session_id=session_id)
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", user_id)


@pytest.fixture
def fake_claude() -> Callable[..., FakeClaudeClient]:
    """Factory for the Claude 대역: `fake_claude(resp1, resp2)` answers the
    calls in order and records the prompts it received (`.prompts`)."""

    def make(*responses: str) -> FakeClaudeClient:
        return FakeClaudeClient(list(responses))

    return make


def default_finding(**overrides: object) -> dict[str, object]:
    """공통 픽스처 발화 1("I usually go to gym after work.")에 대한 유효한
    finding 리터럴 — 관사 누락 오류. `tests/unit/test_claude_schema.py`·
    `test_analysis.py`, `tests/integration/test_pipeline.py`·`test_worker.py`가
    이 8필드 리터럴을 각자 복붙해 갈라지지 않도록 여기 하나로 묻는다."""
    finding: dict[str, object] = {
        "category": "article",
        "pattern_key": "article_missing_before_place_noun",
        "target_form": "go to the gym",
        "original_span": "go to gym",
        "correction": "go to the gym",
        "explanation": "장소를 가리키는 명사 앞에는 정관사 the가 필요합니다.",
        "severity": "medium",
        "confidence": 0.9,
    }
    finding.update(overrides)
    return finding


async def backdate_session(conn: asyncpg.Connection, session_id: UUID, *, by: timedelta) -> None:
    """세션 시작 시각과 그 세션 발화들의 시각을 `by`만큼 과거로 민다 (I-4 리퍼 테스트).

    **경과 시간을 `sleep`으로 만들 수 없기 때문에 있는 헬퍼다.** PostgreSQL의 `now()`는
    트랜잭션 시작 시각에 고정되므로 `db_conn`(롤백되는 한 트랜잭션) 안에서는 아무리
    기다려도 유예를 넘길 수 없고, 커밋하는 테스트에서도 1분을 실제로 기다릴 수는 없다.
    행을 과거로 미는 방식은 벽시계에 의존하지 않아 느린 CI에서도 흔들리지 않는다.

    `ended_at`은 건드리지 않는다 — 이미 끝난 세션을 리퍼가 다시 닫지 않는지 보는 테스트가
    그 값의 불변을 단정한다. `tests/unit/test_sessions.py`와
    `tests/integration/test_worker.py`가 공유한다.

    ⚠️ 이것은 **테스트가 만든 합성 데이터**의 시각 조작이고, "표시가 틀렸다고 저장된
    `timestamptz`를 변환해 UPDATE한다"(전역 시각 규약의 금지 사항)와는 다른 조작이다 —
    실제 기록된 순간을 이동시키는 코드는 앱에 없다.
    """
    await conn.execute(
        "update learning_sessions set started_at = started_at - $2::interval where id = $1",
        session_id,
        by,
    )
    await conn.execute(
        "update utterances set created_at = created_at - $2::interval where session_id = $1",
        session_id,
        by,
    )


async def job_row(conn: asyncpg.Connection, job_id: UUID) -> asyncpg.Record:
    """`analysis_jobs` 한 행을 조회한다 — 사라졌으면 즉시 실패시킨다.
    `tests/unit/test_jobs.py`·`tests/integration/test_pipeline.py`가 공유한다."""
    row = await conn.fetchrow("select * from analysis_jobs where id = $1", job_id)
    assert row is not None, f"analysis_jobs row {job_id} disappeared"
    return row


# ── Task 4 (계획 입력) 픽스처 ────────────────────────────────────────────────
#
# 아래 7개는 `tests/unit/test_plan_input.py`·`test_chronic.py`(이연 LOW-12 추가분)가 쓴다.
# 위 7개 픽스처와 겹치지 않는다(2026-09-04 확인). 시각은 전부 `datetime.now(UTC) -
# timedelta(days=N)`로 만든다 — naive datetime을 절대 만들지 않는다(전역 시각 규약).


@pytest.fixture
def seed_due_patterns() -> Callable[..., object]:
    """복습 예정일이 지난 패턴 `count`개와 사용자 1명을 만든다 (AS1 — 하나라도 빠지면
    실패). `load_due_reviews`는 `error_patterns` 행만 보므로 발화·occurrence는 필요 없다."""

    async def make(conn: asyncpg.Connection, *, count: int) -> UUID:
        user_id = await conn.fetchval(
            "insert into users (display_name) values ('Plan Input Test') returning id"
        )
        for index in range(count):
            await conn.execute(
                "insert into error_patterns (user_id, category, pattern_key, target_form, "
                "next_review_at) values ($1, 'article', $2, 'x', $3)",
                user_id,
                f"plan_input_due_{index}",
                datetime.now(UTC) - timedelta(days=1 + index),
            )
        return user_id

    return make


@pytest.fixture
def seed_utterance_at() -> Callable[..., object]:
    """호출마다 **같은 사용자·세션**에 발화를 쌓는다(§4.2 최근 창·발화 유형·화자 필터
    검증용). 매번 새 사용자를 만들면 필터가 없어도 통과하는 테스트가 되므로, 이 클로저
    안에서 첫 호출이 만든 사용자를 이후 호출이 재사용한다.

    `speaker`가 기본값 `'user'`인 이유: 코치(`'agent'`) 발화도 `utterance_type='learning'`으로
    저장되므로(리뷰 Important-1), 그 누출을 막는 필터를 검증하려는 테스트만 명시적으로
    `speaker="agent"`를 넘긴다."""

    state: dict[str, UUID] = {}
    sequence = count(1)

    async def make(
        conn: asyncpg.Connection,
        *,
        days_ago: int,
        transcript: str,
        kind: str = "learning",
        speaker: str = "user",
    ) -> UUID:
        if "user_id" not in state:
            state["user_id"] = await conn.fetchval(
                "insert into users (display_name) values ('Plan Input Test') returning id"
            )
            state["session_id"] = await conn.fetchval(
                "insert into learning_sessions (user_id, mode) values ($1, 'speaking') "
                "returning id",
                state["user_id"],
            )
        await conn.execute(
            "insert into utterances "
            "(session_id, speaker, utterance_type, transcript, sequence_no, created_at) "
            "values ($1, $2, $3, $4, $5, $6)",
            state["session_id"],
            speaker,
            kind,
            transcript,
            next(sequence),
            datetime.now(UTC) - timedelta(days=days_ago),
        )
        return state["user_id"]

    return make


@pytest.fixture
def seed_pronunciation() -> Callable[..., object]:
    """`(target_sound, outcome)` 쌍마다 발음 시도 1건을 만든다(§4.4). `pending`은
    `resolved_at`을 비워 표의 CHECK(`..._resolved_consistency`)를 만족시키고, 그 외
    판정값은 판정 시각을 채운다 — 채우지 않으면 그 CHECK가 insert를 거부한다.

    `target_sound`가 `None`일 수 있다 — 003이 그 컬럼을 nullable로 뒀다(리뷰 M3:
    `outcome='incorrect'`이고 키가 있을 때만 채워지므로, 키 없는 행이 실물에 존재한다)."""

    async def make(conn: asyncpg.Connection, pairs: list[tuple[str | None, str]]) -> UUID:
        user_id = await conn.fetchval(
            "insert into users (display_name) values ('Plan Input Test') returning id"
        )
        session_id = await conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
            user_id,
        )
        for target_sound, outcome in pairs:
            resolved_at = None if outcome == "pending" else datetime.now(UTC)
            await conn.execute(
                "insert into pronunciation_attempts "
                "(session_id, target_form, target_sound, outcome, resolved_at) "
                "values ($1, 'the gym', $2, $3, $4)",
                session_id,
                target_sound,
                outcome,
                resolved_at,
            )
        return user_id

    return make


@pytest.fixture
def seed_cycle() -> Callable[..., object]:
    """`load_completed_then_relapsed`(§6.2) 테스트용 — 패턴 1개에 재발 시각(`relapses`)과
    정답 시각(`corrects`)을 일 단위 오프셋으로 심는다. 재발은 `error_occurrences`로, 정답은
    `pattern_attempts`(outcome='correct')로 심는다 — `_FULL_HISTORY_SQL`이 그 두 표에서
    시각만 뽑는다. 기준일을 충분히 과거로 잡아 오프셋이 커도 미래로 넘어가지 않게 한다."""

    sequence = count(1)

    async def make(
        conn: asyncpg.Connection, *, relapses: list[int], corrects: list[int]
    ) -> tuple[UUID, UUID]:
        user_id = await conn.fetchval(
            "insert into users (display_name) values ('Plan Input Test') returning id"
        )
        session_id = await conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
            user_id,
        )
        pattern_id = await conn.fetchval(
            "insert into error_patterns (user_id, category, pattern_key, target_form) "
            "values ($1, 'article', 'plan_input_cycle_pattern', 'x') returning id",
            user_id,
        )
        base = datetime.now(UTC) - timedelta(days=100)

        async def utterance_at(day: int) -> UUID:
            return await conn.fetchval(
                "insert into utterances (session_id, speaker, transcript, sequence_no, "
                "created_at) values ($1, 'user', 'x', $2, $3) returning id",
                session_id,
                next(sequence),
                base + timedelta(days=day),
            )

        for day in relapses:
            utterance_id = await utterance_at(day)
            await conn.execute(
                "insert into error_occurrences "
                "(utterance_id, pattern_id, original_span, correction, explanation, severity, "
                "confidence) values ($1, $2, 'x', 'y', 'z', 'medium', 0.9)",
                utterance_id,
                pattern_id,
            )
        for day in corrects:
            utterance_id = await utterance_at(day)
            await conn.execute(
                "insert into pattern_attempts (pattern_id, utterance_id, outcome) "
                "values ($1, $2, 'correct')",
                pattern_id,
                utterance_id,
            )
        return user_id, pattern_id

    return make


@pytest.fixture
def seed_user() -> Callable[..., object]:
    """`users.timezone`에 임의 값을 직접 넣는다(LOW-14). 001은 이 컬럼에 CHECK를 두지
    않았다 — 무효값의 거부는 `load_plan_input`이 조회 시점에 한다.

    ⚠️ **`tz`는 필수로 남긴다.** 기본값을 주면 LOW-14 가 의도한 "타임존을 명시해 넣는다"는
    강제가 약해진다(리뷰 라운드 1의 Minor — Task 8 이 잠시 기본값을 넣었다가 되돌렸다).
    수준을 정해야 하는 테스트는 `seed_scenarios_for_level`을 쓴다: 공유 픽스처의 계약을
    호출 한 건 때문에 넓히지 않는다."""

    async def make(conn: asyncpg.Connection, *, tz: str) -> UUID:
        return await conn.fetchval(
            "insert into users (display_name, timezone) values ('Plan Input Test', $1) "
            "returning id",
            tz,
        )

    return make


@pytest.fixture
def seed_two_patterns() -> Callable[..., object]:
    """`load_chronic_metrics`의 정렬(`order by pattern_key`) 검증용(이연 LOW-12 ①) —
    지정한 순서로 패턴을 만들고 각각 occurrence 1건을 붙인다. occurrence가 없는 패턴은
    그 쿼리의 join에서 빠지므로(chronic.py 모듈 docstring) 빈 패턴은 만들지 않는다."""

    sequence = count(1)

    async def make(conn: asyncpg.Connection, *, keys: list[str]) -> UUID:
        user_id = await conn.fetchval(
            "insert into users (display_name) values ('Chronic Order Test') returning id"
        )
        session_id = await conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
            user_id,
        )
        for key in keys:
            pattern_id = await conn.fetchval(
                "insert into error_patterns (user_id, category, pattern_key, target_form) "
                "values ($1, 'article', $2, 'x') returning id",
                user_id,
                key,
            )
            utterance_id = await conn.fetchval(
                "insert into utterances (session_id, speaker, transcript, sequence_no, "
                "created_at) values ($1, 'user', 'x', $2, $3) returning id",
                session_id,
                next(sequence),
                datetime.now(UTC),
            )
            await conn.execute(
                "insert into error_occurrences "
                "(utterance_id, pattern_id, original_span, correction, explanation, severity, "
                "confidence) values ($1, $2, 'x', 'y', 'z', 'medium', 0.9)",
                utterance_id,
                pattern_id,
            )
        return user_id

    return make


@pytest.fixture
def seed_occurrences_on_days() -> Callable[..., object]:
    """`load_chronic_metrics`의 최대 공백(`max_gap`) 검증용(이연 LOW-12 ②·③) — 패턴 1개에
    지정한 일 오프셋마다 occurrence 1건을 심는다. 기준일을 충분히 과거로 잡아 오프셋이
    커도 미래로 넘어가지 않게 한다."""

    sequence = count(1)

    async def make(conn: asyncpg.Connection, *, days: list[int]) -> tuple[UUID, UUID]:
        user_id = await conn.fetchval(
            "insert into users (display_name) values ('Chronic Gap Test') returning id"
        )
        session_id = await conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
            user_id,
        )
        pattern_id = await conn.fetchval(
            "insert into error_patterns (user_id, category, pattern_key, target_form) "
            "values ($1, 'article', 'chronic_gap_pattern', 'x') returning id",
            user_id,
        )
        base = datetime.now(UTC) - timedelta(days=100)
        for day in days:
            utterance_id = await conn.fetchval(
                "insert into utterances (session_id, speaker, transcript, sequence_no, "
                "created_at) values ($1, 'user', 'x', $2, $3) returning id",
                session_id,
                next(sequence),
                base + timedelta(days=day),
            )
            await conn.execute(
                "insert into error_occurrences "
                "(utterance_id, pattern_id, original_span, correction, explanation, severity, "
                "confidence) values ($1, $2, 'x', 'y', 'z', 'medium', 0.9)",
                utterance_id,
                pattern_id,
            )
        return user_id, pattern_id

    return make


# ── Task 6 (계획 프롬프트) 픽스처 ────────────────────────────────────────────
#
# `tests/unit/test_plan.py`가 쓴다. `build_plan_prompt`는 순수 함수라 DB가 필요 없으므로
# 이 팩토리도 DB 없이 `PlanInput`을 조립한다(위 7개와 달리 `conn`을 받지 않는다).


@pytest.fixture
def plan_input_factory() -> Callable[..., PlanInput]:
    """DB 없이 `PlanInput`을 조립한다 — 프롬프트 조립 테스트 전용.

    `chronic_flagged`는 **패턴 key**로 받는다(테스트가 그렇게 쓴다).
    `PlanInput.chronic_pattern_ids`는 `set[UUID]`이므로, 여기서 key → `pattern_id`로 바꿔 담는다 —
    키 문자열을 그대로 넣으면
    `build_plan_prompt`의 `metric.pattern_id in data.chronic_pattern_ids` 판정이 영원히 거짓이
    된다(Task 6 브리프 경고).

    ⚠️ **`chronic` 목록은 `chronic_flagged` 키에서만 만든다 — `due_keys`를 미러링하지 않는다.**
    처음에는 `due_keys`마다 `ChronicMetric`도 함께 만들었지만, 그러면 `due_reviews` 절이
    통째로 비어도(예: `_format_due_reviews`가 깨져도) 같은 key가 `chronic` 절에 그대로 남아
    `test_prompt_lists_every_due_pattern`이 **엉뚱한 이유로 통과**했다(2026-09-05 mutation
    테스트로 직접 확인 — 그 함수를 항상 `"(none due today)"`만 돌리게 바꿔도 이 테스트가
    초록으로 남았다). 두 목록을 분리하니 같은 mutation에 실패로 반응한다. `pattern_ids`는
    여전히 두 목록의 합집합에 미리 배정한다 — `chronic_flagged`가 `due_keys` 밖의 key를
    가리켜도(테스트가 그렇게 쓰지는 않지만) `KeyError`로 죽지 않게 하기 위해서다.

    `recent`는 `(transcript, corrections)` 튜플의 목록이다. `corrections`는 `RecentCorrection`의
    필드 순서 그대로인 7-튜플의 목록이다(`pattern_key, category, original_span, correction,
    explanation, severity, confidence`) — 교정이 없는 발화는 빈 목록을 준다. 리뷰
    Important-4: 이 파라미터가 없어서 `_format_recent`의 발화 줄·교정 줄 포맷이 한 번도
    실행되지 않았다.

    **재리뷰(라운드 2)가 요구한 파라미터 2개** — 없으면 잴 수 없는 것이 있었다:
    * `chronic_unflagged` — 만성 목록에 있지만 `chronic_pattern_ids`에는 **없는** 패턴.
      이것이 없으면 `_format_chronic`의 `if metric.pattern_id in chronic_pattern_ids` 조건을
      `if True`로 바꿔도 아무 테스트가 실패하지 않았다(직접 확인). §6.2의 유일한 결정론적
      신호가 전 패턴에 붙어 소음이 되는 것을 막는 음성 케이스가 이 파라미터로 성립한다.
    * `chronic_max_gap` — `max_gap`이 `None`인 패턴(발생이 1건뿐일 때 `chronic.py`가 그렇게
      낸다). 고정값이라 `"n/a"` 분기가 한 번도 실행되지 않았다.
    """

    def make(
        *,
        due_keys: Sequence[str] = (),
        chronic_flagged: Sequence[str] = (),
        chronic_unflagged: Sequence[str] = (),
        chronic_max_gap: timedelta | None = timedelta(days=3),
        pronunciation: Sequence[tuple[str, str, int]] = (),
        recent: Sequence[tuple[str, Sequence[tuple[str, str, str, str, str, str, float]]]] = (),
    ) -> PlanInput:
        now = datetime.now(UTC)
        pattern_ids: dict[str, UUID] = {}
        for key in (*due_keys, *chronic_flagged, *chronic_unflagged):
            pattern_ids.setdefault(key, uuid4())

        due_reviews = [
            DueReview(
                pattern_id=pattern_ids[key],
                pattern_key=key,
                category="grammar",
                target_form=f"target form for {key}",
                next_review_at=now - timedelta(days=1),
                mastery_score=0.0,
            )
            for key in due_keys
        ]
        chronic = [
            ChronicMetric(
                pattern_id=pattern_ids[key],
                pattern_key=key,
                category="grammar",
                frequency=3,
                mastery_score=0.0,
                next_review_at=now - timedelta(days=1),
                recurring_sessions=2,
                recurring_days=2,
                first_seen=now - timedelta(days=10),
                last_seen=now - timedelta(days=1),
                span=timedelta(days=9),
                max_gap=chronic_max_gap,
            )
            for key in (*chronic_flagged, *chronic_unflagged)
        ]
        chronic_pattern_ids = {pattern_ids[key] for key in chronic_flagged}
        pronunciation_tallies = [
            PronunciationTally(
                target_sound=sound, outcome=outcome, attempts=attempts, last_seen=now
            )
            for sound, outcome, attempts in pronunciation
        ]
        recent_utterances = [
            RecentUtterance(
                said_at=now - timedelta(hours=index),
                transcript=transcript,
                corrections=tuple(RecentCorrection(*fields) for fields in corrections),
            )
            for index, (transcript, corrections) in enumerate(recent)
        ]

        return PlanInput(
            user_id=uuid4(),
            timezone="Asia/Seoul",
            window_from=now - timedelta(days=14),
            window_to=now,
            current_level="A2",
            due_reviews=due_reviews,
            chronic=chronic,
            chronic_pattern_ids=chronic_pattern_ids,
            recent=recent_utterances,
            pronunciation=pronunciation_tallies,
        )

    return make


# ── Task 7 (계획·노트·수준을 한 트랜잭션에 저장) 픽스처 ──────────────────────
#
# `tests/integration/test_plan_pipeline.py`·`tests/integration/test_worker.py`가 쓴다.
# `process_plan`은 자기 트랜잭션을 여러 개 여므로(입력 읽기 → 트랜잭션 **밖** Claude 호출 →
# 저장 한 트랜잭션) `db_conn`(롤백되는 한 트랜잭션)으로는 잴 수 없다 — `db_pool`을 쓰고
# `committed_session`과 같은 규약으로 teardown 에서 사용자를 지운다.


class PlanHistory(NamedTuple):
    user_id: UUID
    session_id: UUID
    pattern_id: UUID
    # 복습 예정일이 **아직 오지 않은** 패턴 — `due_reviews`에는 없고 `chronic`에만 있다.
    # 허용 id 집합의 chronic 절이 실제로 쓰이는지 재려면 이것이 필요하다(아래 픽스처 docstring).
    chronic_pattern_id: UUID


async def end_new_session(pool: asyncpg.Pool, user_id: UUID) -> UUID:
    """이 사용자의 세션을 하나 더 만들고 `end_session`으로 닫는다 — 반환값은 세션 id.

    **노트가 덧붙여지는지 보려면 세션이 둘 필요하다**: `session_plans.session_id`가
    `unique`라 한 세션이 만드는 계획은 하나뿐이고(007), 같은 세션으로 두 번 돌리면
    두 번째 계획 insert 가 unique 위반으로 트랜잭션 전체를 되돌린다 — 그러면 노트도
    남지 않아 append-only 를 재는 것이 아니라 롤백을 재게 된다.

    `end_session`을 쓰는 이유: 그것이 같은 트랜잭션에서 `plan_next_session` job 을
    거는 실물 경로다(Task 2). 테스트가 job 을 손으로 넣으면 그 연결을 우회한다.
    """
    async with pool.acquire() as conn, conn.transaction():
        session_id = await conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
            user_id,
        )
        await end_session(conn, session_id, "completed")
    assert isinstance(session_id, UUID), f"세션을 만들지 못했다: {session_id!r}"
    return session_id


@pytest_asyncio.fixture
async def ended_session_with_history(db_pool: asyncpg.Pool) -> AsyncIterator[PlanHistory]:
    """계획을 만들 수 있는 최소 이력 — 끝난 세션 1개 + **복습 예정일이 지난 패턴 1개**.

    패턴을 반드시 하나 심는다: `process_plan`의 허용 id 집합은
    `due_reviews ∪ chronic`이고 **0건이면 Claude 를 부르지 않고 콜드스타트 사유로
    종결한다**(계획서 Task 7 ②). 패턴이 없으면 저장을 재려는 테스트가 그 경로로 빠져
    아무것도 저장되지 않은 채 "이유가 틀린" 초록/빨강을 낸다.

    쓰기는 커밋된다 — teardown 에서 사용자를 지우고 cascade 가 세션 → job → 계획 →
    노트를 함께 걷어간다(`committed_session`과 같은 규약).

    ⚠️ **패턴을 둘 심는다 — 하나로는 허용 id 집합의 절반이 죽은 채로 남는다.**
    `process_plan`의 집합은 `due_reviews ∪ chronic`인데 두 목록은 **구조적으로 갈라진다**:
    `load_due_reviews`는 `next_review_at <= clock_timestamp()`로 거르고(`review.py`),
    `load_chronic_metrics`는 그 컬럼으로 **거르지 않고 발생이 1건 이상인 패턴 전부**를 낸다.
    그래서 "발생은 있지만 아직 복습 예정일이 안 된" 패턴은 **chronic 에만** 있다.

    2026-09-05 실측(codex 리뷰): 이 픽스처가 due 패턴 하나만 심던 동안 `data.chronic`이
    **0건**이었고(발생·발화를 안 심어서 `_METRICS_SQL`의 `error_occurrences ⋈ utterances`
    조인이 비었다), 그래서 `process_plan`에서 `| {metric.pattern_id …}` 절을 **통째로 지워도
    549건이 전부 통과했다.** 그 절을 지키는 테스트가 하나도 없었다.
    → `chronic_pattern_id`는 미래 예정일 + 발생 1건으로 심어 그 절을 실제로 통과하게 만든다.
    """
    now = datetime.now(UTC)
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval(
            "insert into users (display_name) values ('Plan Pipeline Test') returning id"
        )
        pattern_id = await conn.fetchval(
            "insert into error_patterns (user_id, category, pattern_key, target_form, "
            "next_review_at) values ($1, 'article', 'plan_pipeline_due', 'go to the gym', $2) "
            "returning id",
            user_id,
            now - timedelta(days=1),
        )
        chronic_pattern_id = await conn.fetchval(
            "insert into error_patterns (user_id, category, pattern_key, target_form, "
            "next_review_at) values ($1, 'verb_tense', 'plan_pipeline_chronic', 'went', $2) "
            "returning id",
            user_id,
            now + timedelta(days=3),  # 미래 → due_reviews 에서 제외된다
        )
    session_id = await end_new_session(db_pool, user_id)
    # 발생 1건을 붙여야 `load_chronic_metrics`가 이 패턴을 낸다(발생 0건은 제외된다).
    # 발화는 이 세션에 매단다 — `_METRICS_SQL`이 `error_occurrences ⋈ utterances`로 조인한다.
    async with db_pool.acquire() as conn:
        utterance_id = await conn.fetchval(
            "insert into utterances (session_id, speaker, utterance_type, transcript, "
            "sequence_no, created_at) "
            "values ($1, 'user', 'learning', 'I go there yesterday.', 1, $2) returning id",
            session_id,
            now - timedelta(hours=1),
        )
        await conn.execute(
            "insert into error_occurrences "
            "(utterance_id, pattern_id, original_span, correction, explanation, severity, "
            "confidence) values ($1, $2, 'go there yesterday', 'went there yesterday', "
            "'과거 시점에는 과거형을 씁니다.', 'medium', 0.9)",
            utterance_id,
            chronic_pattern_id,
        )
        # ⚠️ 그 발화의 분석 job 을 **done 으로 남긴다.** 실물에서 occurrence 가 존재하는 것은
        # 분석이 이미 돌았기 때문이고, `flush_pending_analysis`의 회복 스윕은
        # `analyze_utterance` job 이 **없는** 발화만 새로 건다(`utterances.py` 의 `not exists`).
        # 이 행이 없으면 워커 테스트에서 스윕이 분석 job 을 하나 더 걸어 가짜 Claude 의 응답을
        # 계획 대신 분석이 먹는다 — 2026-09-05 에 실제로 그렇게 깨졌다(`prompts` 2건).
        await conn.execute(
            "insert into analysis_jobs (job_type, utterance_id, status) values ($1, $2, 'done')",
            JOB_TYPE_ANALYZE,
            utterance_id,
        )
    try:
        yield PlanHistory(
            user_id=user_id,
            session_id=session_id,
            pattern_id=pattern_id,
            chronic_pattern_id=chronic_pattern_id,
        )
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", user_id)


async def claim_plan_job(pool: asyncpg.Pool, session_id: UUID) -> ClaimedJob:
    """이 세션의 `plan_next_session` job 을 claim 한다 — 걸려 있지 않으면 먼저 등록한다.

    `end_session`이 이미 걸어 둔 job 이 있으면 `enqueue_plan_next_session`이 `None`을
    돌려주고(partial unique `uq_analysis_jobs_pending_session`) 그 job 을 claim 한다.
    앞선 job 이 terminal(`done`/`failed`)이 된 뒤에는 새 job 이 걸린다 — 큐의 멱등 규약
    그대로다.

    ⚠️ claim 한 것이 **이 세션의 계획 job 인지** 단정한다. `claim_next`는 큐 전체에서
    하나를 고르므로, 다른 테스트가 남긴 job 을 집어오면 이 헬퍼가 조용히 엉뚱한 job 을
    돌려주고 호출한 테스트가 이유 없이 초록이 된다.
    """
    async with pool.acquire() as conn:
        await enqueue_plan_next_session(conn, session_id)
        job = await claim_next(conn)
    assert job is not None, f"세션 {session_id} 의 계획 job 을 claim 하지 못했다"
    assert job.job_type == JOB_TYPE_PLAN, f"claim 한 job 종류가 다르다: {job.job_type}"
    assert job.session_id == session_id, f"claim 한 job 의 세션이 다르다: {job.session_id}"
    return job


def plan_json(
    pattern_id: UUID,
    *,
    level_action: str = "keep",
    target_level: str = "A2",
    reason: str = "관사를 계속 빼먹어서 오늘은 그것만 봅니다.",
    level_reason: str = "정답률이 아직 낮습니다.",
    notes: Sequence[str] = ("짧은 문장에서는 관사를 붙이는데 길어지면 빼먹는다",),
) -> str:
    """유효한 계획 응답 1건. `target_level`은 **세 자리 전부**에 들어간다.

    `PlanOutput`의 after-validator 가 `target_level`·`level.target_level`·
    `instruction.target_level`의 일치를 요구하므로 한 인자로 셋을 함께 움직인다 —
    따로 두면 이 팩토리를 쓰는 모든 테스트가 셋을 손으로 맞춰야 하고, 하나를 잊으면
    재려던 것과 무관한 불일치 오류로 거부된다.

    `level_action`은 **라벨**이다(계획서 Task 7 — `target_level`이 정본). 어긋난 조합을
    일부러 만들 수 있어야 그 어긋남이 경고로 드러나는지 잴 수 있다.
    """
    return json.dumps(
        {
            "focus": [
                {
                    "pattern_id": str(pattern_id),
                    "pattern_key": "plan_pipeline_due",
                    "target_form": "go to the gym",
                }
            ],
            "questions": [
                {"prompt": "What did you do at work today?", "context": "work update"},
                {"prompt": "Tell me about your morning.", "context": "daily life"},
                {"prompt": "What will you do tomorrow?", "context": "plan"},
            ],
            "target_level": target_level,
            "reason": reason,
            "instruction": {
                "target_level": target_level,
                "focus": [{"pattern_key": "plan_pipeline_due", "target_form": "go to the gym"}],
                "sentence_length": "two short clauses",
                "hint_timing": "offer a starter after one long pause",
                "contexts": ["work update", "daily life", "plan"],
            },
            "level": {
                "action": level_action,
                "target_level": target_level,
                "reason": level_reason,
            },
            "notes": list(notes),
        },
        ensure_ascii=False,
    )


# ── Task 8 (세션 시작이 준비된 계획을 읽는다) 픽스처 ─────────────────────────
#
# `tests/unit/test_sessions.py`가 쓴다. 둘로 나눈 이유는 재는 대상이 다르기 때문이다:
# `load_prepared_plan`은 **연결**을 받으므로 롤백 트랜잭션(`db_conn`)으로 재고,
# `create_session`은 **pool**을 받으므로(`create_session(pool, user_id)`) 커밋하는
# 픽스처가 필요하다. conn 을 pool 처럼 감싸는 헬퍼를 만들지 않는다.


@pytest.fixture
def seed_plan_for_session() -> Callable[..., object]:
    """`session_plans` 한 행을 그 계획을 **만든 세션**과 함께 심는다.

    `session_id`가 가리키는 것은 계획을 만든 세션(N)이고 소비하는 세션(N+1)이 아니다 —
    계획서 「구현 전 정정」이 그 결론과 근거를 소유한다. `session_plans.session_id`가
    `unique`(007)라 호출마다 세션을 새로 만든다: 같은 세션에 두 계획을 심으려 하면
    unique 위반이 나고, 최신 1행 선택을 재려던 테스트가 그 위반을 재게 된다.

    `instruction`·`questions`는 **`plan_json`에서 뽑는다.** 여기에 모양을 다시 적으면
    `SessionInstruction`(Task 5)이 바뀔 때 한쪽이 조용히 낡아, 저장된 jsonb 가 지금의
    계약과 다른 채로 테스트가 초록이 된다.

    `days_ago`로 `created_at`을 과거로 심는다 — `now()`가 트랜잭션에 고정되어 있어
    `db_conn` 안에서는 기다려도 시각이 벌어지지 않는다(`backdate_session`과 같은 이유).
    `instruction`에 문자열을 주면 그 값을 그대로 저장한다: 읽는 쪽이 **읽을 수 없는**
    지시문을 만났을 때의 경로를 재기 위한 자리다.
    """

    async def make(
        conn: asyncpg.Connection,
        *,
        user_id: UUID | None = None,
        reason: str = "관사를 계속 빼먹어서 오늘은 그것만 봅니다.",
        target_level: str = "A2",
        days_ago: int = 0,
        instruction: str | None = None,
    ) -> tuple[UUID, UUID]:
        if user_id is None:
            user_id = await conn.fetchval(
                "insert into users (display_name) values ('Prepared Plan Test') returning id"
            )
        session_id = await conn.fetchval(
            "insert into learning_sessions (user_id, mode, status, ended_at) "
            "values ($1, 'speaking', 'completed', now()) returning id",
            user_id,
        )
        payload = json.loads(plan_json(uuid4(), target_level=target_level))
        plan_id = await conn.fetchval(
            "insert into session_plans (session_id, focus_pattern_ids, questions, target_level, "
            "reason, instruction, source, created_at) "
            "values ($1, $2, $3, $4, $5, $6, 'agent', $7) returning id",
            session_id,
            [uuid4()],  # focus_pattern_ids 에 FK 는 없다 (007 주석) — 이 픽스처는 값만 채운다
            json.dumps(payload["questions"], ensure_ascii=False),
            target_level,
            reason,
            instruction
            if instruction is not None
            else json.dumps(payload["instruction"], ensure_ascii=False),
            datetime.now(UTC) - timedelta(days=days_ago),
        )
        assert isinstance(user_id, UUID) and isinstance(plan_id, UUID)
        return user_id, plan_id

    return make


@pytest_asyncio.fixture
async def seed_scenarios_for_level(db_pool: asyncpg.Pool) -> AsyncIterator[Callable[..., object]]:
    """수준이 정해진 사용자 1명 + `created_at`이 정해진 시나리오 여러 행을 **커밋한다.**

    `create_session`이 pool 을 받으므로 롤백 트랜잭션으로는 잴 수 없다. 그래서
    `committed_session`과 같은 규약으로 teardown 에서 직접 지운다 — **남기면 두 곳이 깨진다**:
    `tests/unit/test_schema.py`의 `count(*) from users == 1`, 그리고 남은 시나리오가 다른
    테스트의 시나리오 선택을 조용히 바꾼다(선택이 전역 `order by created_at, id`이므로).
    사용자를 먼저 지우고(세션이 cascade 로 따라간다) 그 다음에 시나리오를 지운다 —
    `learning_sessions.scenario_id`에는 cascade 가 없어(001) 순서를 뒤집으면 FK 에 막힌다.

    `scenarios`는 `(level, days_ago)` 목록이다. `days_ago`가 필요한 이유: 폴백 경로가
    `order by created_at, id`로 고르므로, 수준이 **안 맞는** 행을 더 이르게 심어야
    "수준을 보지 않는 구현"과 "보는 구현"이 서로 다른 행을 고른다.
    """
    user_ids: list[UUID] = []
    scenario_ids: list[UUID] = []

    async def make(*, level: str, scenarios: Sequence[tuple[str, int]]) -> tuple[UUID, list[UUID]]:
        created: list[UUID] = []
        async with db_pool.acquire() as conn:
            user_id = await conn.fetchval(
                "insert into users (display_name, current_level) "
                "values ('Scenario Level Test', $1) returning id",
                level,
            )
            user_ids.append(user_id)
            for scenario_level, days_ago in scenarios:
                scenario_id = await conn.fetchval(
                    "insert into learning_scenarios "
                    "(category, level, title, prompt_template, created_at) "
                    "values ('business', $1, $2, 'Tell me about your project.', $3) returning id",
                    scenario_level,
                    f"{scenario_level} scenario",
                    datetime.now(UTC) - timedelta(days=days_ago),
                )
                scenario_ids.append(scenario_id)
                created.append(scenario_id)
            # 이 테스트의 단정은 "심은 행 중 어느 것이 붙었는가"다 — 다른 테스트가 남긴
            # 시나리오가 있으면 폴백이 그것을 고를 수 있고, 그러면 실패 사유를 읽을 수 없다.
            # 누출을 조용한 오답이 아니라 시끄러운 실패로 바꾼다.
            leaked = await conn.fetchval(
                "select count(*) from learning_scenarios where not (id = any($1::uuid[]))",
                created,
            )
        assert leaked == 0, f"이 픽스처가 심지 않은 시나리오 {leaked}행이 남아 있다"
        assert isinstance(user_id, UUID)
        return user_id, created

    try:
        yield make
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = any($1::uuid[])", user_ids)
            await conn.execute(
                "delete from learning_scenarios where id = any($1::uuid[])", scenario_ids
            )
