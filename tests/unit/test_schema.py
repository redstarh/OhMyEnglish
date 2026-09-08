"""Task 2 — schema + seed tests.

Verifies the rewritten `db/migrations/001_initial_schema.sql` (design doc
§6/§6.1a) and `scripts/migrate.py`'s idempotent seed. Uses the `db_conn`
fixture from `tests/conftest.py`, which recreates `ohmyenglish_test` and
applies `db/migrations/*.sql` once per session, then hands each test a
connection inside a transaction that is always rolled back.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from datetime import UTC, datetime, timedelta
from itertools import count
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
MIGRATE_PATH = SCRIPTS_DIR / "migrate.py"


def _load_migrate_module() -> types.ModuleType:
    # `migrate.py`는 `from db_utils import base_dsn`을 쓴다 — 정상 실행(스크립트로
    # 직접 구동)에서는 인터프리터가 스크립트 자신의 디렉터리를 자동으로 sys.path에
    # 넣어주지만, 이 로더처럼 파일 경로로 직접 exec하면 그 자동 삽입이 없다.
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("migrate", MIGRATE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migrate = _load_migrate_module()


async def _insert_user(conn: asyncpg.Connection) -> None:
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'Test User', 'Asia/Seoul', 'A2')",
        migrate.USER_ID,
    )


async def _insert_session(conn: asyncpg.Connection, session_id) -> None:
    await conn.execute(
        "insert into learning_sessions (id, user_id, mode) values ($1, $2, 'speaking')",
        session_id,
        migrate.USER_ID,
    )


# 한 세션 안에서 `sequence_no`가 겹치지 않게 하는 카운터 (011 오디오 경계 테스트가 한 세션에
# 여러 발화를 넣는다 — 001의 `unique(session_id, sequence_no)`가 그것을 요구한다).
_SCHEMA_SEQ = count(1)


async def _insert_utterance(conn: asyncpg.Connection, utterance_id, session_id, sequence_no=1):
    await conn.execute(
        "insert into utterances (id, session_id, speaker, transcript, sequence_no) "
        "values ($1, $2, 'user', 'I go to gym.', $3)",
        utterance_id,
        session_id,
        sequence_no,
    )


# ① 001이 빈 DB에 오류 없이 적용된다 (conftest의 session fixture가 이미 적용을
#    시도하므로, 여기서는 기대하는 8개 테이블이 실제로 존재하는지 확인한다).
@pytest.mark.asyncio
async def test_001_migration_creates_expected_tables(db_conn: asyncpg.Connection):
    rows = await db_conn.fetch(
        "select table_name from information_schema.tables "
        "where table_schema = 'public' order by table_name"
    )
    table_names = {row["table_name"] for row in rows}
    assert table_names == {
        "analysis_jobs",
        "error_occurrences",
        "error_patterns",
        "learning_scenarios",
        "learning_sessions",
        "review_tasks",
        "users",
        "utterances",
        # 003 — 발음 시범·재발화 (docs/design/2026-08-27-pronunciation-echo-design.md §6)
        "pronunciation_attempts",
        # 006 — 학습 코치 슬라이스 1 (docs/design/2026-08-25-learning-coach-agent-design.md §8.1)
        "pattern_attempts",
        # 007 — 학습 코치 슬라이스 2 (docs/design/2026-08-25-learning-coach-agent-design.md §8.1)
        "session_plans",
        "learner_notes",
        # 011 — 쉐도잉 클립 (docs/design/2026-09-08-shadowing-task-design.md §3.3)
        # ⚠️ 이 단정이 **표 이름 집합을 정확히** 비교하므로 새 표는 반드시 여기 들어와야 한다 —
        # 그 설계서 §6이 「이 자리가 깨진다」고 미리 지목한 자산이다(빠뜨리면 red 로 즉시 드러난다).
        "shadowing_items",
    }


# ② analysis_jobs — 같은 (job_type, utterance_id)가 pending인 동안 중복 등록 차단
@pytest.mark.asyncio
async def test_analysis_jobs_pending_duplicate_violates_unique(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    utterance_id = uuid4()
    await _insert_session(db_conn, session_id)
    await _insert_utterance(db_conn, utterance_id, session_id)

    await db_conn.execute(
        "insert into analysis_jobs (job_type, utterance_id) values ('analyze_utterance', $1)",
        utterance_id,
    )

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_conn.execute(
            "insert into analysis_jobs (job_type, utterance_id) values ('analyze_utterance', $1)",
            utterance_id,
        )


# ③ error_patterns.category에 'noun' insert가 CHECK 위반
@pytest.mark.asyncio
async def test_error_patterns_category_check_rejects_unknown_code(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into error_patterns (user_id, category, pattern_key, target_form) "
            "values ($1, 'noun', 'noun_test_key', 'the noun')",
            migrate.USER_ID,
        )


# ④ learning_sessions.status='wrong' 거부
@pytest.mark.asyncio
async def test_learning_sessions_status_check_rejects_invalid_value(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into learning_sessions (user_id, mode, status) "
            "values ($1, 'speaking', 'wrong')",
            migrate.USER_ID,
        )


# ④-2 009 `learning_sessions.drill_turns_expected` — nullable + `check (> 0)` (캡틴 결정 16)
#
# **왜 `summary` jsonb 가 아니라 컬럼인가**는 설계서
# `docs/design/2026-09-07-scenario-and-drill-turns-design.md` §2.3 이 소유한다.
# 요지만: `summary` 에는 `docs/database-schema.md` 가 지정한 **다음 소유자**
# (`summarize_session`)가 이미 있고, CHECK 없는 jsonb 는 그 기능의 작성자를 구속하지 못한다.
#
# ⚠️ **nullable 인 것이 계약이다** — null 은 「계획 없이 시작한 세션 = 관측 대상 아님」이다.
# ⛔ **0 을 허용하지 않는 이유**: 0 은 「기대가 0 이었다」로 읽혀 **「기대가 없었다」와 구분되지
# 않는다.** 그 구분이 결과 화면의 `drill` 키 유무를 정하므로 값역에서 막는다.
@pytest.mark.asyncio
async def test_drill_turns_expected_is_nullable_and_rejects_non_positive(
    db_conn: asyncpg.Connection,
):
    await _insert_user(db_conn)
    session_id = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        migrate.USER_ID,
    )

    # 기본값은 null 이다 — INSERT 가 이 컬럼을 몰라도 세션이 만들어진다.
    assert (
        await db_conn.fetchval(
            "select drill_turns_expected from learning_sessions where id = $1", session_id
        )
        is None
    )

    # ⚠️ 위반 하나를 **savepoint 안에서** 낸다. `db_conn`은 테스트당 트랜잭션 하나를 열어 두므로
    # CHECK 위반이 그 트랜잭션을 abort시키고, 감싸지 않으면 **뒤따르는 문장이 전부
    # `InFailedSQLTransactionError`로 죽는다**(이 테스트를 쓰다가 실제로 그랬다). 중첩
    # `transaction()`은 asyncpg에서 savepoint가 되어 위반만 되돌린다.
    for rejected in (0, -1):
        with pytest.raises(asyncpg.CheckViolationError):
            async with db_conn.transaction():
                await db_conn.execute(
                    "update learning_sessions set drill_turns_expected = $2 where id = $1",
                    session_id,
                    rejected,
                )

    await db_conn.execute(
        "update learning_sessions set drill_turns_expected = 12 where id = $1", session_id
    )
    assert (
        await db_conn.fetchval(
            "select drill_turns_expected from learning_sessions where id = $1", session_id
        )
        == 12
    )


# ④-3 010 `review_tasks` 값역과 불변조건 (`TASK-43` · 설계서
# `docs/design/2026-09-08-review-task-history-design.md` §3.3 · §4 Contract)
#
# ⛔ **`skipped` 제거가 이 설계의 집행 장치다.** 그 값을 남겨 두면 `TASK-3`(학습 히스토리 화면)
# 구현자가 `update review_tasks set status='skipped'`를 쓰는 것이 **컬럼 이름과 문서를 따르는
# 정상 행동**이고, 그 칸은 재계산이 소유하므로 다음 재계산에 조용히 사라진다. 값역에서 막으면
# 그 시도가 즉시 실패해 학습자 행동을 둘 자리를 의도적으로 만들게 된다 — 009 가 같은 판단을 했다.
# ⚠️ `done → completed_at not null`은 **함의이고 동치가 아니다**: `superseded`로 은퇴한 행이
# 완주 시각을 그대로 들고 있어야 "우리가 그때 무엇을 믿었는지"가 남는다.
@pytest.mark.asyncio
async def test_review_tasks_status_domain_and_done_requires_completed_at(
    db_conn: asyncpg.Connection,
):
    await _insert_user(db_conn)
    pattern_id = await db_conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'article', 'article_test_key', 'a project') returning id",
        migrate.USER_ID,
    )
    cycle_started_at = datetime(2026, 9, 1, 3, 0, tzinfo=UTC)

    async def _insert(status: str, completed_at: datetime | None, stage: int = 1) -> None:
        await db_conn.execute(
            "insert into review_tasks (pattern_id, task_type, scenario_context, "
            "cycle_started_at, review_stage, due_at, status, completed_at) "
            "values ($1, 'rephrase', 'a project', $2, $3, $4, $5, $6)",
            pattern_id,
            cycle_started_at,
            stage,
            cycle_started_at + timedelta(days=1),
            status,
            completed_at,
        )

    # 위반은 **savepoint 안에서** 낸다 — `db_conn`이 테스트당 트랜잭션 하나를 열어 두므로
    # 감싸지 않으면 뒤따르는 문장이 전부 `InFailedSQLTransactionError`로 죽는다(④-2와 같은 함정).
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await _insert("skipped", None)

    # `done`인데 완주 시각이 없으면 거부된다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await _insert("done", None)

    # 파생 상태 넷은 전부 받는다. `superseded`가 완주 시각을 들고 있는 것도 정상이다(함의이므로).
    await _insert("pending", None, stage=1)
    await _insert("done", cycle_started_at + timedelta(days=1), stage=2)
    await _insert("abandoned", None, stage=3)
    assert (
        await db_conn.fetchval(
            "select count(*) from review_tasks where pattern_id = $1", pattern_id
        )
        == 3
    )
    await db_conn.execute(
        "update review_tasks set status = 'superseded' where pattern_id = $1 and review_stage = 2",
        pattern_id,
    )
    assert (
        await db_conn.fetchval(
            "select completed_at from review_tasks where pattern_id = $1 and review_stage = 2",
            pattern_id,
        )
        is not None
    )


# ④-4 010 유일키가 **사이클**을 가른다 — 같은 패턴의 같은 단계가 사이클마다 하나씩 존재한다.
# 옛 키 `unique(pattern_id, review_stage)`로는 재발 후의 1단계를 담을 자리가 없었다(설계서 §2.3).
@pytest.mark.asyncio
async def test_review_tasks_unique_key_separates_cycles(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    pattern_id = await db_conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'article', 'article_cycle_key', 'a project') returning id",
        migrate.USER_ID,
    )
    first_cycle = datetime(2026, 9, 1, 3, 0, tzinfo=UTC)
    second_cycle = datetime(2026, 9, 20, 3, 0, tzinfo=UTC)

    async def _insert(cycle_started_at: datetime) -> None:
        await db_conn.execute(
            "insert into review_tasks (pattern_id, task_type, scenario_context, "
            "cycle_started_at, review_stage, due_at, status) "
            "values ($1, 'rephrase', 'a project', $2, 1, $3, 'pending')",
            pattern_id,
            cycle_started_at,
            cycle_started_at + timedelta(days=1),
        )

    await _insert(first_cycle)
    await _insert(second_cycle)  # 다른 사이클의 1단계 — 옛 키에서는 여기서 막혔다
    assert (
        await db_conn.fetchval(
            "select count(*) from review_tasks where pattern_id = $1", pattern_id
        )
        == 2
    )

    with pytest.raises(asyncpg.UniqueViolationError):
        async with db_conn.transaction():
            await _insert(first_cycle)  # 같은 사이클의 같은 단계는 여전히 하나다


# ⑤ 시드 후 users 1행 · learning_scenarios 3행(**무대** 3개 — 질문이 아니다. 캡틴 결정 14),
#    재실행해도 중복 없음(멱등 — 이제 `do nothing` 이 아니라 `do update` 로 멱등이다)
@pytest.mark.asyncio
async def test_seed_creates_fixed_user_and_three_scenarios_idempotently(
    db_conn: asyncpg.Connection,
):
    await migrate.seed(db_conn)
    await migrate.seed(db_conn)  # re-run — must stay idempotent (on conflict do update)

    user_count = await db_conn.fetchval("select count(*) from users")
    assert user_count == 1

    seeded_user = await db_conn.fetchrow(
        "select display_name, timezone, current_level from users where id = $1",
        migrate.USER_ID,
    )
    assert seeded_user["timezone"] == "Asia/Seoul"
    assert seeded_user["current_level"] == "A2"

    scenario_rows = await db_conn.fetch(
        "select title from learning_scenarios where category = 'daily_life' order by title"
    )
    assert len(scenario_rows) == 3
    titles = {row["title"] for row in scenario_rows}
    assert titles == {
        "After work with a colleague",
        "Weekend plans with a friend",
        "Tonight's plans at home",
    }


# ⑤-2 시드 3행은 **무대**다 — 질문이 아니고 `title`과 `prompt_template`이 갈라져 있다.
#
# 캡틴 결정 14 (2026-09-07). 근거: 결정 9가 「시나리오 = 무대(상황·역할) · 계획 = 목표(질문)」로
# 역할을 갈랐는데 시드 3행은 **질문**이었고 두 컬럼이 **바이트 동일**이었다(psql 직접 조회).
# 그 상태에서는 ① `Today's setting:`에 질문이 박혀 계획의 질문 3~5개와 종류가 겹치고
# ② 「`title`을 지시문에 싣지 않는다」는 규칙 6 방어가 **공허해진다** — 같은 문자열이
# `prompt_template`으로 들어가므로. 설계서 §2.1·§2.2가 근거를 소유한다.
#
# ⚠️ 위 ⑤와 나누는 이유: ⑤는 **개수와 멱등성**을 지키고 이것은 **내용의 종류**를 지킨다.
# 한 테스트에 합치면 시드 문구를 고칠 때마다 멱등성 단정까지 함께 흔들린다.
@pytest.mark.asyncio
async def test_seeded_scenarios_are_stages_not_questions(
    db_conn: asyncpg.Connection,
):
    await migrate.seed(db_conn)

    rows = await db_conn.fetch(
        "select title, prompt_template from learning_scenarios "
        "where category = 'daily_life' order by title"
    )
    assert len(rows) == 3

    for row in rows:
        # 화면 라벨과 지시문 문구는 다른 문장이다.
        assert row["title"] != row["prompt_template"], (
            f"title 과 prompt_template 이 같다 — 규칙 6 방어가 공허해진다: {row['title']!r}"
        )
        # 무대는 질문이 아니다. 질문은 계획(`session_plans.questions`)이 소유한다.
        assert not row["prompt_template"].rstrip().endswith("?"), (
            f"prompt_template 이 질문이다 — 무대여야 한다: {row['prompt_template']!r}"
        )


# ── 003 pronunciation_attempts (발음 시범·재발화 설계서 §6.1) ──────────────────


async def _insert_pronunciation_session(conn: asyncpg.Connection):
    """발음 시도를 매달 세션 1개. 시나리오는 nullable 이라 생략한다."""
    session_id = uuid4()
    await _insert_user(conn)
    await _insert_session(conn, session_id)
    return session_id


# ⑥ 테이블·컬럼 nullability — 시범 시점에는 아직 없는 값들이 nullable 이어야 한다
@pytest.mark.asyncio
async def test_pronunciation_attempts_column_nullability(db_conn: asyncpg.Connection):
    columns = {
        row["column_name"]: row["is_nullable"]
        for row in await db_conn.fetch(
            "select column_name, is_nullable from information_schema.columns "
            "where table_name = 'pronunciation_attempts'"
        )
    }
    assert columns, "pronunciation_attempts 테이블이 없다 (003 미적용)"
    assert columns["session_id"] == "NO"
    assert columns["target_form"] == "NO"
    assert columns["outcome"] == "NO"
    assert columns["signal_source"] == "NO"
    # 시범 시점에는 재발화를 아직 못 들었다 (설계서 F3)
    assert columns["spoken_form"] == "YES"
    assert columns["utterance_id"] == "YES"
    assert columns["pattern_id"] == "YES"
    assert columns["target_sound"] == "YES"
    assert columns["resolved_at"] == "YES"


# ⑦ outcome CHECK — 열거값 밖은 DB가 거부한다 (앱의 강등은 그 앞단이다)
@pytest.mark.asyncio
async def test_pronunciation_attempts_rejects_unknown_outcome(db_conn: asyncpg.Connection):
    session_id = await _insert_pronunciation_session(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into pronunciation_attempts (session_id, target_form, outcome) "
            "values ($1, 'I think.', 'bogus')",
            session_id,
        )


# ⑧ pending은 정식 값이다 — Nova가 재발화 *전에* tool을 부른다 (설계서 F3·F4)
@pytest.mark.asyncio
async def test_pronunciation_attempts_accepts_pending(db_conn: asyncpg.Connection):
    session_id = await _insert_pronunciation_session(db_conn)

    row_id = await db_conn.fetchval(
        "insert into pronunciation_attempts (session_id, target_form, outcome) "
        "values ($1, 'I think I found three very useful videos.', 'pending') returning id",
        session_id,
    )
    assert row_id is not None


# ⑨ resolved_at 일관성 — 두 방향을 각각 본다.
#    CHECK 위반이 트랜잭션을 abort시키므로 한 테스트에 raise를 두 번 넣을 수 없다
#    (db_conn 픽스처는 테스트 하나를 트랜잭션 하나로 감싼다).
@pytest.mark.asyncio
async def test_pronunciation_attempts_pending_rejects_resolved_at(
    db_conn: asyncpg.Connection,
):
    session_id = await _insert_pronunciation_session(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into pronunciation_attempts "
            "(session_id, target_form, outcome, resolved_at) "
            "values ($1, 'I think.', 'pending', now())",
            session_id,
        )


@pytest.mark.asyncio
async def test_pronunciation_attempts_verdict_requires_resolved_at(
    db_conn: asyncpg.Connection,
):
    """판정됐는데 언제인지 모르는 행이 생기면 수렴 여부를 사후에 알 수 없다."""
    session_id = await _insert_pronunciation_session(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into pronunciation_attempts (session_id, target_form, outcome) "
            "values ($1, 'I think.', 'correct')",  # resolved_at 누락
            session_id,
        )


# ⑩ 빈 target_form 거부 — 시범이 없는 시범 기록은 의미가 없다
@pytest.mark.asyncio
async def test_pronunciation_attempts_rejects_blank_target_form(db_conn: asyncpg.Connection):
    session_id = await _insert_pronunciation_session(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into pronunciation_attempts (session_id, target_form, outcome) "
            "values ($1, '   ', 'pending')",
            session_id,
        )


# ⑪ signal_source CHECK — 보조 신호로 만든 행을 구분할 수 있어야 한다 (R10-4)
@pytest.mark.asyncio
async def test_pronunciation_attempts_signal_source_check(db_conn: asyncpg.Connection):
    session_id = await _insert_pronunciation_session(db_conn)

    # 판정된 행으로 확인한다 — `pending`은 005가 nova_tool로만 허용하므로 값역 확인에
    # 쓰면 두 제약이 얽힌다. 이 테스트가 보는 것은 **출처 값역 하나**다.
    for source in ("nova_tool", "korean_transcript", "agent_reprompt"):
        await db_conn.execute(
            "insert into pronunciation_attempts "
            "(session_id, target_form, outcome, signal_source, resolved_at) "
            "values ($1, 'I think.', 'unclear', $2, now())",
            session_id,
            source,
        )
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into pronunciation_attempts "
            "(session_id, target_form, outcome, signal_source, resolved_at) "
            "values ($1, 'I think.', 'unclear', 'telepathy', now())",
            session_id,
        )


# ⑫ 세션 삭제 시 cascade — teardown이 시도를 남기지 않는다 (하네스 격리 규약)
@pytest.mark.asyncio
async def test_pronunciation_attempts_cascades_with_session(db_conn: asyncpg.Connection):
    session_id = await _insert_pronunciation_session(db_conn)
    await db_conn.execute(
        "insert into pronunciation_attempts (session_id, target_form, outcome) "
        "values ($1, 'I think.', 'pending')",
        session_id,
    )

    await db_conn.execute("delete from learning_sessions where id = $1", session_id)

    assert await db_conn.fetchval("select count(*) from pronunciation_attempts") == 0


# ⑬ 발화 삭제는 시도를 지우지 않는다 — set null. 판정 기록이 발화보다 오래 산다
@pytest.mark.asyncio
async def test_pronunciation_attempts_utterance_delete_sets_null(db_conn: asyncpg.Connection):
    session_id = await _insert_pronunciation_session(db_conn)
    utterance_id = uuid4()
    await _insert_utterance(db_conn, utterance_id, session_id)
    await db_conn.execute(
        "insert into pronunciation_attempts (session_id, utterance_id, target_form, outcome) "
        "values ($1, $2, 'I think.', 'pending')",
        session_id,
        utterance_id,
    )

    await db_conn.execute("delete from utterances where id = $1", utterance_id)

    row = await db_conn.fetchrow(
        "select utterance_id from pronunciation_attempts where session_id = $1", session_id
    )
    assert row is not None
    assert row["utterance_id"] is None


# ── 004 attempt_seq (발음 시도의 삽입 순서를 DB가 강제한다) ─────────────────────


# ⑭ attempt_seq는 GENERATED ALWAYS identity다 — 앱이 순서를 위조할 수 없어야 한다
@pytest.mark.asyncio
async def test_pronunciation_attempts_attempt_seq_is_generated_always(
    db_conn: asyncpg.Connection,
):
    column = await db_conn.fetchrow(
        "select is_identity, identity_generation, is_nullable, data_type "
        "from information_schema.columns "
        "where table_name = 'pronunciation_attempts' and column_name = 'attempt_seq'"
    )
    assert column is not None, "attempt_seq 컬럼이 없다 (004 미적용)"
    assert column["is_identity"] == "YES"
    assert column["identity_generation"] == "ALWAYS"
    assert column["is_nullable"] == "NO"
    assert column["data_type"] == "bigint"


# ⑮ 한 트랜잭션에서 만든 두 행은 created_at이 같지만 attempt_seq는 갈린다.
#    이것이 004의 존재 이유다 — now()는 트랜잭션 고정이라 "최신 시도"를 못 고른다
#    (실측: created_at 정렬은 3회 중 1회 잘못된 행을 골랐다).
@pytest.mark.asyncio
async def test_pronunciation_attempts_attempt_seq_orders_within_one_transaction(
    db_conn: asyncpg.Connection,
):
    session_id = await _insert_pronunciation_session(db_conn)
    for target in ("First.", "Second."):
        await db_conn.execute(
            "insert into pronunciation_attempts (session_id, target_form, outcome) "
            "values ($1, $2, 'pending')",
            session_id,
            target,
        )

    rows = await db_conn.fetch(
        "select target_form, attempt_seq, created_at from pronunciation_attempts "
        "where session_id = $1 order by attempt_seq desc",
        session_id,
    )
    assert [row["target_form"] for row in rows] == ["Second.", "First."]
    assert rows[0]["created_at"] == rows[1]["created_at"], (
        "같은 트랜잭션이라 created_at은 동값이어야 한다 — 이 전제가 깨지면 이 테스트의 의미가 없다"
    )
    assert rows[0]["attempt_seq"] > rows[1]["attempt_seq"]


# ⑯ 앱이 attempt_seq를 직접 주는 것은 거부된다 — 순서가 규약이 아니라 강제여야 한다
@pytest.mark.asyncio
async def test_pronunciation_attempts_attempt_seq_rejects_supplied_value(
    db_conn: asyncpg.Connection,
):
    session_id = await _insert_pronunciation_session(db_conn)

    with pytest.raises(asyncpg.exceptions.GeneratedAlwaysError):
        await db_conn.execute(
            "insert into pronunciation_attempts "
            "(session_id, target_form, outcome, attempt_seq) "
            "values ($1, 'I think.', 'pending', 1)",
            session_id,
        )


# ── 005 — "대답 기다림 상태는 Nova tool만 만든다"를 DB가 강제한다 ────────────────
#
# 이 불변조건을 표에 두는 이유: 앱에서 지키면 판정 UPDATE가 `signal_source='nova_tool'`을
# 매번 필터해야 하고, 보조 신호 경로가 실수로 pending 행을 만들면 판정이 그 행을 닫아
# "누가 관측했나"가 뒤섞인다. 제약 한 줄로 그 케이스 자체를 없앤다.
@pytest.mark.asyncio
async def test_pending_requires_the_nova_tool_source(db_conn: asyncpg.Connection):
    session_id = await _insert_pronunciation_session(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into pronunciation_attempts "
            "(session_id, target_form, outcome, signal_source) "
            "values ($1, 'I think.', 'pending', 'korean_transcript')",
            session_id,
        )


# 판정된 행은 어느 출처든 허용된다 — 보조 신호는 항상 판정된 상태로 태어난다
@pytest.mark.asyncio
async def test_a_resolved_row_accepts_any_source(db_conn: asyncpg.Connection):
    session_id = await _insert_pronunciation_session(db_conn)

    for source in ("nova_tool", "korean_transcript", "agent_reprompt"):
        row_id = await db_conn.fetchval(
            "insert into pronunciation_attempts "
            "(session_id, target_form, outcome, signal_source, resolved_at) "
            "values ($1, 'I think.', 'unclear', $2, now()) returning id",
            session_id,
            source,
        )
        assert row_id is not None


# ── 006 학습 코치 슬라이스 1 (학습 코치 설계서 §8.1·§8.2) ────────────────────────


async def _insert_pattern_and_occurrence(conn: asyncpg.Connection):
    """user → session → utterance → pattern 한 벌. 006 테스트의 공통 전제.

    `_insert_user`는 고정 USER_ID를 넣으므로 한 테스트에서 두 번 부르면 PK를 위반한다 —
    이 헬퍼가 한 번만 부르고 나머지를 이어 만든다.
    """
    session_id = uuid4()
    utterance_id = uuid4()
    await _insert_user(conn)
    await _insert_session(conn, session_id)
    await _insert_utterance(conn, utterance_id, session_id)
    pattern_id = await conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'article', 'article_missing_before_place_noun', 'go to the + 장소 명사') "
        "returning id",
        migrate.USER_ID,
    )
    return utterance_id, pattern_id


# ② suggested_contexts — jsonb 이고 nullable 이어야 한다 (설계서 §8.2: 기존 발화에는 없다)
@pytest.mark.asyncio
async def test_error_occurrences_has_nullable_jsonb_suggested_contexts(
    db_conn: asyncpg.Connection,
):
    column = await db_conn.fetchrow(
        "select data_type, is_nullable from information_schema.columns "
        "where table_name = 'error_occurrences' and column_name = 'suggested_contexts'"
    )
    assert column is not None, "suggested_contexts 컬럼이 없다 (006 미적용)"
    assert column["data_type"] == "jsonb"
    # nullable 이어야 소급 불가능한 과거 발화가 저장을 막지 않는다 (§8.2)
    assert column["is_nullable"] == "YES"


# ③ 상황 배열이 그대로 왕복한다 — 개수 CHECK를 두지 않으므로 2개도 통과해야 한다 (§8.2)
@pytest.mark.asyncio
async def test_suggested_contexts_round_trips_without_a_length_constraint(
    db_conn: asyncpg.Connection,
):
    utterance_id, pattern_id = await _insert_pattern_and_occurrence(db_conn)
    contexts = ["퇴근 후 운동 계획 말하기", "동료에게 오늘 일정 알려주기"]

    stored = await db_conn.fetchval(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, "
        " confidence, suggested_contexts) "
        "values ($1, $2, 'go to gym', 'go to the gym', '정관사가 필요합니다.', 'medium', 0.9, $3) "
        "returning suggested_contexts",
        utterance_id,
        pattern_id,
        json.dumps(contexts, ensure_ascii=False),
    )

    # asyncpg는 jsonb를 str로 돌려준다 (파이썬 list를 바인딩하면 DataError다 — 2026-09-03 실측)
    assert json.loads(stored) == contexts


# ④ pattern_attempts — 같은 (pattern, utterance) 두 번은 거부된다 (AS10 멱등의 바닥)
@pytest.mark.asyncio
async def test_pattern_attempts_rejects_a_duplicate_pattern_utterance_pair(
    db_conn: asyncpg.Connection,
):
    utterance_id, pattern_id = await _insert_pattern_and_occurrence(db_conn)
    await db_conn.execute(
        "insert into pattern_attempts (pattern_id, utterance_id, outcome) "
        "values ($1, $2, 'correct')",
        pattern_id,
        utterance_id,
    )

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_conn.execute(
            "insert into pattern_attempts (pattern_id, utterance_id, outcome) "
            "values ($1, $2, 'incorrect')",
            pattern_id,
            utterance_id,
        )


# ⑤ outcome 값역 — 'pending'은 이 표에 없다. 발음 표(pronunciation_attempts)와 다르다:
#    이 표의 행은 재발화 전사문을 이미 본 뒤에 만들어지므로 "대답 기다림" 상태가 없다.
@pytest.mark.asyncio
async def test_pattern_attempts_outcome_check_rejects_pending(db_conn: asyncpg.Connection):
    utterance_id, pattern_id = await _insert_pattern_and_occurrence(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into pattern_attempts (pattern_id, utterance_id, outcome) "
            "values ($1, $2, 'pending')",
            pattern_id,
            utterance_id,
        )


# ⑥ 발화가 지워지면 판정도 지워진다 — 이 표의 행은 발화 1건이 유일한 근거라서 cascade다
#    (발음 표는 set null 이다: 그 행은 발화 없이 tool 이벤트만으로도 생긴다)
@pytest.mark.asyncio
async def test_pattern_attempts_cascades_with_the_utterance(db_conn: asyncpg.Connection):
    utterance_id, pattern_id = await _insert_pattern_and_occurrence(db_conn)
    await db_conn.execute(
        "insert into pattern_attempts (pattern_id, utterance_id, outcome) "
        "values ($1, $2, 'correct')",
        pattern_id,
        utterance_id,
    )

    await db_conn.execute("delete from utterances where id = $1", utterance_id)

    assert await db_conn.fetchval("select count(*) from pattern_attempts") == 0


# ── 007 학습 코치 슬라이스 2 (학습 코치 설계서 §8.1·§8.3) ────────────────────────


# ⑫ 007 — analysis_jobs 가 계획 job 을 받는다 (설계서 §8.3)
@pytest.mark.asyncio
async def test_analysis_jobs_accepts_plan_next_session(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    await db_conn.execute(
        "insert into analysis_jobs (job_type, session_id) values ('plan_next_session', $1)",
        session_id,
    )
    assert (
        await db_conn.fetchval(
            "select count(*) from analysis_jobs where job_type = 'plan_next_session'"
        )
        == 1
    )


# ⑬ 007 — 계획 job 은 utterance 를 대상으로 삼을 수 없다 (대상 컬럼 배타 CHECK 3분기)
@pytest.mark.asyncio
async def test_plan_job_rejects_utterance_target(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    utterance_id = uuid4()
    await _insert_session(db_conn, session_id)
    await _insert_utterance(db_conn, utterance_id, session_id)

    # 기존 job_type CHECK가 이미 이 값을 거부하므로(007 이전에도 우연히 green), 예외 타입만으로는
    # "대상 컬럼 배타 CHECK"가 실제로 걸렸는지 구분되지 않는다 — constraint_name으로 못박는다.
    with pytest.raises(asyncpg.CheckViolationError) as excinfo:
        await db_conn.execute(
            "insert into analysis_jobs (job_type, utterance_id) values ('plan_next_session', $1)",
            utterance_id,
        )
    # asyncpg가 constraint_name을 메타클래스에서 동적으로 setattr하므로(_base.py의
    # _field_map) ty가 클래스 선언만 보고는 이 속성을 못 찾는다 — getattr로 우회한다.
    assert getattr(excinfo.value, "constraint_name", None) == (
        "analysis_jobs_target_matches_job_type"
    )


# ⑭ 007 — session_plans 불변조건: 초점 1~2개 · 질문 3~5개 · 이유 비어있지 않음 (설계서 §9 Contract)
@pytest.mark.asyncio
async def test_session_plans_invariants(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)
    pattern_a, pattern_b, pattern_c = uuid4(), uuid4(), uuid4()

    def insert(focus: list, questions: str, reason: str) -> tuple[str, list]:
        return (
            "insert into session_plans "
            "(session_id, focus_pattern_ids, questions, target_level, reason, instruction, source) "
            "values ($1, $2, $3::jsonb, 'A2', $4, '{}'::jsonb, 'agent')",
            [session_id, focus, questions, reason],
        )

    ok_questions = (
        '[{"prompt":"q1","context":"c1"},'
        '{"prompt":"q2","context":"c2"},'
        '{"prompt":"q3","context":"c3"}]'
    )

    # CHECK 위반은 트랜잭션을 abort시킨다. db_conn 픽스처는 테스트 하나를 트랜잭션
    # 하나로 감싸므로, 이 위반들을 이어서 검증하려면 각각 savepoint(중첩 트랜잭션)로
    # 격리해야 다음 assert가 이어질 수 있다(다른 곳의 pronunciation_attempts 테스트가
    # 이 문제를 별도 테스트 분리로 피한 것과 같은 근본 원인).

    # 초점 0개 → 거부. array_length('{}', 1)은 NULL이라 CHECK가 만족으로 오판할 수 있는
    # 자리라서 하한을 반드시 직접 확인한다(cardinality로 고친 이유 — 007 SQL 주석 참조).
    sql, args = insert([], ok_questions, "이유")
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(sql, *args)

    # 초점 3개 → 거부
    sql, args = insert([pattern_a, pattern_b, pattern_c], ok_questions, "이유")
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(sql, *args)

    # 질문 2개 → 거부
    sql, args = insert(
        [pattern_a], '[{"prompt":"q1","context":"c1"},{"prompt":"q2","context":"c2"}]', "이유"
    )
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(sql, *args)

    # 질문 6개 → 거부 (상한도 하한만큼 직접 확인한다)
    too_many_questions = (
        '[{"prompt":"q1","context":"c1"},{"prompt":"q2","context":"c2"},'
        '{"prompt":"q3","context":"c3"},{"prompt":"q4","context":"c4"},'
        '{"prompt":"q5","context":"c5"},{"prompt":"q6","context":"c6"}]'
    )
    sql, args = insert([pattern_a], too_many_questions, "이유")
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(sql, *args)

    # 이유가 공백뿐 → 거부
    sql, args = insert([pattern_a], ok_questions, "   ")
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(sql, *args)

    # 정상 1행은 들어간다
    sql, args = insert(
        [pattern_a, pattern_b], ok_questions, "관사를 계속 빼먹어서 오늘 그것만 봅니다"
    )
    await db_conn.execute(sql, *args)
    assert await db_conn.fetchval("select count(*) from session_plans") == 1


# ⑮ 007 — 세션이 지워지면 계획도 함께 지워진다 · 세션당 1행
@pytest.mark.asyncio
async def test_session_plans_unique_and_cascade(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)
    questions = (
        '[{"prompt":"q1","context":"c1"},'
        '{"prompt":"q2","context":"c2"},'
        '{"prompt":"q3","context":"c3"}]'
    )
    sql = (
        "insert into session_plans "
        "(session_id, focus_pattern_ids, questions, target_level, reason, instruction, source) "
        "values ($1, $2, $3::jsonb, 'A2', '이유', '{}'::jsonb, 'agent')"
    )
    await db_conn.execute(sql, session_id, [uuid4()], questions)

    # UNIQUE 위반도 트랜잭션을 abort시킨다 — savepoint로 격리해야 아래 delete가 이어진다.
    with pytest.raises(asyncpg.UniqueViolationError):
        async with db_conn.transaction():
            await db_conn.execute(sql, session_id, [uuid4()], questions)

    await db_conn.execute("delete from learning_sessions where id = $1", session_id)
    assert await db_conn.fetchval("select count(*) from session_plans") == 0


# ⑯ 007 — learner_notes: window_to가 window_from보다 앞서면 거부된다 (§6.3)
@pytest.mark.asyncio
async def test_learner_notes_rejects_window_out_of_order(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    window_to = datetime(2026, 9, 1, tzinfo=UTC)
    window_from = datetime(2026, 9, 2, tzinfo=UTC)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into learner_notes (user_id, note, window_from, window_to) "
            "values ($1, '{}'::jsonb, $2, $3)",
            migrate.USER_ID,
            window_from,
            window_to,
        )


# ⑰ 007 — learner_notes: 사용자가 지워지면 그 사용자의 노트도 함께 지워진다
@pytest.mark.asyncio
async def test_learner_notes_cascades_with_the_user(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    now = datetime.now(UTC)

    await db_conn.execute(
        "insert into learner_notes (user_id, note, window_from, window_to) "
        "values ($1, '{}'::jsonb, $2, $3)",
        migrate.USER_ID,
        now,
        now,
    )

    await db_conn.execute("delete from users where id = $1", migrate.USER_ID)

    assert await db_conn.fetchval("select count(*) from learner_notes") == 0


# ⑤ 011 `shadowing_items` 값역·불변조건 (`TASK-45` · 설계서
#    `docs/design/2026-09-08-shadowing-task-design.md` §3.3)
#
# ⛔ **90초 상한은 발명값이 아니라 PRD §7의 요구사항이다.** 스키마에 두는 이유: 클립을 넣는
#    경로가 손이라(PRD가 자동 수집을 비범위로 뒀다) 사람이 실수로 긴 창을 넣을 수 있고,
#    그때 조용히 저장되면 「쉐도잉 1회」의 정의가 문서와 갈라진다.
# ⚠️ 위반은 **savepoint 안에서** 낸다 — `db_conn`이 테스트당 트랜잭션 하나를 열어 두므로
#    감싸지 않으면 뒤따르는 문장이 전부 `InFailedSQLTransactionError`로 죽는다.
@pytest.mark.asyncio
async def test_shadowing_items_span_must_be_ordered_and_within_the_prd_limit(
    db_conn: asyncpg.Connection,
):
    async def _insert(start: float, end: float) -> None:
        await db_conn.execute(
            "insert into shadowing_items (source_title, transcript, clip_start_sec, "
            "clip_end_sec, level) values ('Standup', 'I hit a blocker today.', $1, $2, 'A2')",
            start,
            end,
        )

    # 정상 창 — 30~90초 안이고 순서가 맞다.
    await _insert(0, 42.5)
    assert await db_conn.fetchval("select count(*) from shadowing_items") == 1

    # 끝이 시작보다 앞이면 거부된다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await _insert(50, 10)

    # 같아도 거부된다 — 길이 0인 클립은 학습이 성립하지 않는다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await _insert(10, 10)

    # 90초를 **넘으면** 거부된다(PRD §7).
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await _insert(0, 90.01)

    # ⛔ 정확히 90초는 **받는다** — 상한이 포함이다. `<`로 잘못 쓰면 이 단정만 깨진다.
    await _insert(0, 90)
    assert await db_conn.fetchval("select count(*) from shadowing_items") == 2


# ⑤-2 클립은 **쉐도잉 세션에만** 붙는다. 역방향은 강제하지 않는다 — 클립을 고르기 전에
#      세션이 열릴 수 있다(§3.3).
@pytest.mark.asyncio
async def test_shadowing_item_can_only_attach_to_a_shadowing_session(
    db_conn: asyncpg.Connection,
):
    await _insert_user(db_conn)
    item_id = await db_conn.fetchval(
        "insert into shadowing_items (source_title, transcript, clip_start_sec, "
        "clip_end_sec, level) values ('Standup', 'I hit a blocker today.', 0, 40, 'A2') "
        "returning id"
    )

    # `mode='speaking'` 세션에는 붙지 않는다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into learning_sessions (user_id, mode, shadowing_item_id) "
                "values ($1, 'speaking', $2)",
                migrate.USER_ID,
                item_id,
            )

    # `mode='shadowing'`이면 붙는다.
    session_id = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode, shadowing_item_id) "
        "values ($1, 'shadowing', $2) returning id",
        migrate.USER_ID,
        item_id,
    )
    assert session_id is not None

    # 역방향은 열려 있다 — 클립 없는 쉐도잉 세션이 정상이다(고르기 전 상태).
    assert (
        await db_conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'shadowing') "
            "returning shadowing_item_id",
            migrate.USER_ID,
        )
        is None
    )


# ⑤-3 011 오디오 경계 — **R10-7 예외를 스키마가 가둔다** (§4.2)
# ⛔ 이 단정이 무너지면 「오디오를 저장하지 않는다」는 규약이 코드 리뷰에만 의존하게 된다.
#    캡틴이 연 예외는 **쉐도잉 낭독 하나**이고, 다른 오디오가 조용히 쌓이는 길을 막는다.
@pytest.mark.asyncio
async def test_audio_url_is_only_allowed_on_a_learner_shadowing_recording(
    db_conn: asyncpg.Connection,
):
    await _insert_user(db_conn)
    session_id = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'shadowing') returning id",
        migrate.USER_ID,
    )

    async def _insert(utterance_type: str, speaker: str, audio_url: str | None) -> None:
        await db_conn.execute(
            "insert into utterances (session_id, speaker, utterance_type, transcript, "
            "audio_url, sequence_no) values ($1, $2, $3, 'I hit a blocker today.', $4, $5)",
            session_id,
            speaker,
            utterance_type,
            audio_url,
            next(_SCHEMA_SEQ),
        )

    # 학습자의 쉐도잉 낭독 — 유일하게 오디오가 허용되는 조합이다.
    await _insert("shadowing_recording", "user", "/audio/x.wav")

    # 오디오 없는 낭독 행도 정상이다(§4.5: DB 포인터를 **마지막에** 쓰므로 그 사이 상태다).
    await _insert("shadowing_recording", "user", None)

    # 학습 발화에 오디오를 붙이면 거부된다 — R10-7이 그대로 산다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await _insert("learning", "user", "/audio/x.wav")

    # agent 낭독은 없다 — 저장 대상은 **학습자 목소리**뿐이다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await _insert("shadowing_recording", "agent", "/audio/x.wav")

    # 음성 명령에도 붙지 않는다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await _insert("voice_command", "user", "/audio/x.wav")


# ⑤-4 `shadowing_recording`이 **값역에 들어왔다** — 그리고 그 값이 분석 경로에서 자동으로
#      빠지는 것이 이 선택의 근거였다(§4.1). 값역 자체를 여기서 잠근다.
@pytest.mark.asyncio
async def test_utterance_type_domain_includes_shadowing_recording(db_conn: asyncpg.Connection):
    definition = await db_conn.fetchval(
        "select pg_get_constraintdef(oid) from pg_constraint "
        "where conname = 'utterances_utterance_type_check'"
    )
    assert definition is not None
    for value in ("learning", "voice_command", "command_confirmation", "shadowing_recording"):
        assert value in definition, f"{value}가 값역에서 빠졌다"
