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
from app.services.plan_input import PlanInput, PronunciationTally, RecentCorrection, RecentUtterance
from app.services.review import DueReview
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
    않았다 — 무효값의 거부는 `load_plan_input`이 조회 시점에 한다."""

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
    """

    def make(
        *,
        due_keys: Sequence[str] = (),
        chronic_flagged: Sequence[str] = (),
        pronunciation: Sequence[tuple[str, str, int]] = (),
        recent: Sequence[tuple[str, Sequence[tuple[str, str, str, str, str, str, float]]]] = (),
    ) -> PlanInput:
        now = datetime.now(UTC)
        pattern_ids: dict[str, UUID] = {}
        for key in (*due_keys, *chronic_flagged):
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
                max_gap=timedelta(days=3),
            )
            for key in chronic_flagged
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
