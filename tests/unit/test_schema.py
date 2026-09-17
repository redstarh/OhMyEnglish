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
import re
import sys
import types
from datetime import UTC, date, datetime, timedelta
from itertools import count
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest

from app.models.session import SESSION_MODES
from app.models.user import FIXED_USER_ID

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
        # ⛔ `public` 이 아니라 `current_schema()` 다 — 026 이 우리 표를 `ohmyenglish` 로 옮겼고
        #    `public` 에는 En-Coach 호환 뷰 셋만 남았다(`TASK-41`). 스키마를 이름으로 박으면 이
        #    단정이 그 뷰 셋을 「우리 표」로 세거나, 스키마 이름을 바꿀 때 조용히 0행이 된다.
        "where table_schema = current_schema() and table_type = 'BASE TABLE' "
        "order by table_name"
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
        # 012 — 일일 오류 요약 (docs/design/2026-09-11-daily-error-summary-design.md §3)
        "daily_error_summary",
        # 013 — LLM 호출 토큰 사용량 (결정 66 · `TASK-60`). 호출 1건 = 행 1건이고 job **밖**
        # 호출(계획 스파이크·Nova·예열)까지 담는 것이 이 표의 존재 이유다.
        "llm_calls",
        # 023 — 주간 학습 리포트 (`TASK-26` · 결정 4·91). 사실(`metrics`)과 모델 판단(`insights`)을
        # 한 행에 함께 담는 이유는 설계서 §5 가 갖는다 — 나누면 판단이 근거로 삼은 사실과 어긋난다.
        "weekly_reports",
        # 027 — 담아 둔 YouTube 영상 (`TASK-162` · 결정 125·126). 담은 문장(`shadowing_items`)과
        # 갈라 두는 이유는 **수명이 다르기 때문**이다 — 제목·채널은 YouTube 에서 온 값이라 정책이
        # 보관을 30일로 제한하고, 문장은 사용자가 만든 학습 자산이라 그 제한 밖이다.
        "youtube_videos",
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


# ④-0 025 `learning_sessions.status='paused'` 허용 (결정 115·117)
@pytest.mark.asyncio
async def test_learning_sessions_status_check_accepts_paused(db_conn: asyncpg.Connection):
    """「일시 정지」의 상태가 값역에 있다 — 025 가 더했다.

    ⛔ **이 값이 행에 남아야 하는 이유**: 정지 판정을 메모리에만 두면 프로세스가 죽은 뒤 그 세션이
    무엇이었는지 알 수 없고 리퍼가 걷을 근거도 없다(025 머리말).
    """
    await _insert_user(db_conn)

    session_id = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode, status) "
        "values ($1, 'speaking', 'paused') returning id",
        migrate.USER_ID,
    )

    assert session_id is not None


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


# ⑤ 시드 후 users 1행 · learning_scenarios 는 **무대**다(질문이 아니다 — 캡틴 결정 14),
#    재실행해도 중복 없음(멱등 — 이제 `do nothing` 이 아니라 `do update` 로 멱등이다)
#
# ⚠️ **무대 개수를 이 주석과 테스트 이름에 적지 않는다.** 시드가 3 → 15 → 30 으로 늘면서 두 자리가
# 함께 낡았다(2026-09-14 감사가 잡았다). 옛 이름은 `…_fifteen_scenarios_…` 였고 계획서
# `docs/design/2026-09-12-scenario-rotation-70-30-plan.md:523` 이 그 이름을 인용하므로 그 문서를
# 읽을 때 이 자리를 함께 본다. 개수는 아래 단정이 지키고, 업무는 등호가 아니라 하한이다.
@pytest.mark.asyncio
async def test_seed_creates_the_fixed_user_and_the_scenarios_idempotently(
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

    # `TASK-4` · 결정 75 — 일상과 업무가 **섞여** 있어야 한다. ⚠️ **합계를 여기서 적지 않는다** —
    # 일상은 등호로, 업무는 하한으로 지킨다(바로 아래 두 단정). 이전 판은 「일상 9 + 업무 6 = 15」
    # 로 적었고 업무가 9로 늘면서 낡았다. ⚠️ 개수를 세는 이유는 배치 규칙이
    # 「창 10 보다 후보가 많다」에 걸려 있기 때문이다(설계서 §6 테스트 2 · `test_scenario_rotation`
    # 의 `test_starvation_returns_when_topics_only_match_the_window` 가 그 경계를 실측했다) —
    # 후보가 10 이하로 줄면 신규가 마른다.
    daily = await db_conn.fetch(
        "select title from learning_scenarios where category = 'daily_life' order by title"
    )
    business = await db_conn.fetch(
        "select title from learning_scenarios where category = 'business' order by title"
    )
    assert len(daily) == 9, "PRD §7 Daily Conversation 의 주제 9종"
    # ⚠️ 업무는 **6개보다 늘 수 있다** — PRD §7 의 6종이 하한이고 `TASK-102` AC#3 이 30개를
    # 요구하면서 회의 보고·회의 진행·프로젝트 설명 셋이 더해졌다(결정 77). 등호로 고정하면
    # 목표 수준(회의 참여·보고)에 맞는 무대를 더할 때마다 이 단정이 걸린다.
    assert len(business) >= 6, "PRD §7 Business English 의 시나리오 6종이 하한이다"

    # ⛔ 업무 6종의 `level` 을 올리지 않는다 — 결정 75 의 완화 조항이고, 이 단정이 그것을
    # 지킨다. 무대는 업무이고 문형 난이도는 일상과 같다.
    business_levels = await db_conn.fetch(
        "select distinct level from learning_scenarios where category = 'business'"
    )
    assert [row["level"] for row in business_levels] == ["A2"]


# ⑤-8 앱의 고정 사용자와 시드가 **같은 UUID** 여야 한다 (`TASK-148` ④ · 결정 122).
#
# ⛔ **값이 두 곳에 적혀 있다.** `scripts/migrate.py` 는 앱 패키지를 import 하지 않는 독립 ops
# 스크립트라(`db_utils` 만 쓴다) `models/user` 의 상수를 공유할 수 없다. 그 복제의 대가를 이 단정이
# 갚는다 — `services/sessions._DEFAULT_LEARNING_SOURCE` 가 `column_default` 와 대조되는 것과 같은
# 부류다.
# ⚠️ **이 단정이 없으면 어긋남이 조용하다**: 앱이 없는 사용자로 세션을 만들려 해 외래키 위반으로
# 떨어지고, 그 실패가 「시드를 안 돌렸다」와 구별되지 않는다.
def test_the_fixed_user_matches_the_seed() -> None:
    assert FIXED_USER_ID == migrate.USER_ID


# ⑤-5 시드 배열의 **순서**가 제품 동작이다 (`TASK-4` · 결정 76).
#
# ⛔ **이 테스트는 「비율이 맞는다」와 다른 것을 잰다.** 배치 규칙은 신규를 고를 때 `created_at` 이
# 가장 이른 후보를 집고, 그 컬럼은 시드 배열의 삽입 순서다. 업무 6종을 배열 뒤에 몰아 두었던 첫
# 판은 **결정 75(「처음부터 섞는다」)를 문면만 이행했고** 실제로는 일상 9종을 다 소진한 뒤에야
# 업무가 나왔다 — dev DB 에서 실제 앱 경로(`create_session`)로 12회를 열어 **업무 0회**를 관측했다.
# ⚠️ **단위 테스트가 그것을 못 잡았다** — 비율과 고갈은 셌지만 「무엇이 먼저 오는가」를 세지 않았다.
# 이 테스트가 그 구멍이다.
def test_seed_interleaves_business_stages_early() -> None:
    """업무 상황이 배열 앞쪽에 들어와 있다 — 창(10) 안에 최소 하나는 온다."""
    categories = [category for _, category, _, _, _ in migrate.SEED_SCENARIOS]

    first_business = categories.index("business")
    # 창이 10 이므로 첫 업무가 10번째 이후면 도입 첫 창에서 업무를 못 본다.
    assert first_business < 5, (
        f"첫 업무 상황이 배열 {first_business + 1}번째다 — 결정 76 이 요구한 「번갈아」가 아니다"
    )

    # 뒤쪽 절반에 업무가 몰려 있지 않다. 균등하지 않으면 후반부만 업무가 된다.
    half = len(categories) // 2
    front = categories[:half].count("business")
    assert front >= 2, f"앞 절반에 업무가 {front}개뿐이다 — 뒤로 몰렸다"

    # ⛔ **4번째부터는 같은 직종이 둘 연달아 오지 않는다** — 그것이 「번갈아」의 기계적 정의다.
    # ⚠️ 앞 3개를 제외하는 이유: `…101`·`…102`·`…103` 은 이 태스크 전부터 있던 행이고 `…101` 은
    # 세션 17건이 참조한다(dev DB 직접 조회). `created_at` 이 이미 박혀 있어 배열에서 앞으로
    # 당길 수 없다. 그 셋이 일상인 것은 PRD §7 의 「일상부터 연습한 뒤 업무로 전이」와도 맞는다.
    tail = categories[3:]
    for i in range(len(tail) - 1):
        assert tail[i] != tail[i + 1], f"배열 {i + 4}~{i + 5}번째가 같은 직종이다: {tail[i]}"


# ⑤-6 그 순서가 **DB 의 `display_order`** 에도 있는지 잰다 (019 · 결정 81 · `TASK-130.1`).
#
# ⛔ **위 ⑤-5 는 상수 배열만 본다 — 제품이 읽는 값은 DB 의 컬럼이다.** 「배열이 맞다」가
# 「노출 순서가 맞다」를 뜻하지 않는다.
# ⚠️ **이 단정은 019 전에는 `created_at` 축이었다.** 그 컬럼이 순서를 담고 있었고, `seed()` 를 한
# 트랜잭션으로 감싸면 `now()` 가 고정돼 순서가 무너졌다 — 019 가 그 의존을 없앴고 ⑤-7 이 그것을
# 잰다. ⛔ **축을 옮길 때 옛 축을 재는 단정을 남겨 두지 않는다** — 통과해도 아무것도 지키지 않는다.
# ⛔ `db_pool` 은 커밋되고 아무것도 정리하지 않는다 — **사용자를 먼저** 지워 세션이 cascade 된 뒤에
# 무대를 지운다(반대 순서는 FK 위반이다).
@pytest.mark.asyncio
async def test_seeded_display_order_carries_the_array_order(db_pool: asyncpg.Pool):
    """DB 의 `display_order` 가 `SEED_SCENARIOS` 배열의 자리와 같다 (결정 76 · 81)."""
    seed_ids = [scenario_id for scenario_id, *_ in migrate.SEED_SCENARIOS]
    clip_ids = [clip.id for clip in migrate.SEED_SHADOWING_ITEMS]
    try:
        async with db_pool.acquire() as conn:
            await migrate.seed(conn)
            rows = await conn.fetch(
                "select id, display_order from learning_scenarios "
                "where id = any($1::uuid[]) order by display_order, id",
                seed_ids,
            )

        assert [row["id"] for row in rows] == seed_ids, (
            "DB 의 display_order 순서가 배열 순서와 다르다 — 결정 76 의 노출 순서가 무너졌다"
        )

        # ⛔ 「순서가 같다」는 값이 서로 **다를 때만** 뜻이 있다. 겹치는 값이 있으면 그 구간의
        # 정렬이 뒷키로 넘어가고 그 순서는 배열과 무관하다.
        orders = [row["display_order"] for row in rows]
        assert orders == list(range(1, len(seed_ids) + 1)), (
            f"display_order 가 1..{len(seed_ids)} 가 아니다 — 겹치거나 빈 자리가 있다: {orders[:5]}"
        )
    finally:
        async with db_pool.acquire() as conn:
            await conn.execute("delete from users where id = $1", migrate.USER_ID)
            await conn.execute(
                "delete from learning_scenarios where id = any($1::uuid[])", seed_ids
            )
            await conn.execute("delete from shadowing_items where id = any($1::uuid[])", clip_ids)


# ⑤-7 `seed()` 를 트랜잭션 하나로 감싸도 순서가 유지된다 (019 · 결정 81 · `TASK-130.1`).
#
# ⛔ **이 테스트의 뜻이 019 에서 뒤집혔다.** 이전 판은 *"감싸면 무너진다"* 를 재는 재현 테스트였고
# (`TASK-130` AC#4 · 회차 §3-3), 019 가 순서를 `display_order` 로 옮겨 **그 무너짐을 없앴다.**
# 그래서 같은 조건에서 이제 **반대 결과**를 단정한다 — 뒤집힌 사실을 지우지 않고 여기 적어 둔다.
#
# ⚠️ **조건은 `db_conn` 픽스처가 그대로 만든다** — 그 픽스처가 테스트 하나를 트랜잭션 하나로 감싸므로
# `now()` 가 고정된다. 그 고정을 **함께 확인**하는 것이 이 테스트의 판별력이다: `created_at` 이
# 1종인 것을 확인하고도 순서가 살아 있어야 「`display_order` 가 순서를 지탱한다」가 성립한다.
# ⛔ `created_at` 이 여러 종으로 나오면 조건이 성립하지 않은 것이므로 **초록을 믿지 않는다.**
@pytest.mark.asyncio
async def test_wrapping_seed_in_one_transaction_keeps_the_order(db_conn: asyncpg.Connection):
    """트랜잭션 하나로 감싸 created_at 이 뭉개져도 배열 순서가 유지된다."""
    await migrate.seed(db_conn)

    seed_ids = [scenario_id for scenario_id, *_ in migrate.SEED_SCENARIOS]
    rows = await db_conn.fetch(
        "select id, created_at, display_order from learning_scenarios "
        "where id = any($1::uuid[]) order by display_order, id",
        seed_ids,
    )

    # ① 조건이 성립했는가 — 트랜잭션 안이므로 `now()` 가 고정돼 값이 1종이어야 한다.
    stamps = {row["created_at"] for row in rows}
    assert len(stamps) == 1, (
        f"트랜잭션 안인데 created_at 이 {len(stamps)}종이다 — now() 가 트랜잭션 시작에 "
        "고정된다는 전제가 틀렸고, 그러면 아래 단정이 아무것도 재지 않는다"
    )

    # ② 그런데도 순서는 살아 있다 — 019 전 코드는 이 자리에서 무너졌다.
    assert [row["id"] for row in rows] == seed_ids, (
        "created_at 이 뭉개진 상태에서 순서가 배열과 갈렸다 — display_order 가 순서를 담지 못한다"
    )


# ── 017 category 값역 확장 (분야 · `TASK-102` AC#3 · 결정 77) ──────────────────
#
# ⛔ **새 컬럼을 만들지 않고 기존 값역을 늘린 것이 결정 77 이다.** 그 대가로 `category` 가 두 축을
# 섞어 담는다 — `shadowing` 은 학습 **방식**이고 나머지는 **무대**다. 그 혼재가 이 결정으로 굳었고,
# 「무대별 통계」와 「방식별 통계」를 따로 내야 할 때 되돌려질 자리다.
@pytest.mark.asyncio
async def test_scenario_category_domain_includes_the_new_fields(db_conn: asyncpg.Connection):
    """캡틴 예시가 담기는지 잰다 — 여행·쇼핑이 값역에 없으면 30개를 채울 수 없다."""
    definition = await db_conn.fetchval(
        "select pg_get_constraintdef(oid) from pg_constraint "
        "where conname = 'learning_scenarios_category_check'"
    )
    assert definition is not None, "CHECK 가 없다 (001 미적용)"
    # ⛔ **따옴표까지 맞춰 비교한다** — 맨 문자열로 비교하면 부분 일치가 통과한다. 지금 값역에는
    # 서로의 부분 문자열이 없어 안전하지만 `business_report` 같은 값이 들어오면 `business` 가
    # 사라져도 이 단정이 통과한다. 값역을 늘린 일이 이미 세 번 있었다(014·017·018).
    for value in ("daily_life", "business", "shadowing", "travel", "shopping", "health"):
        assert f"'{value}'" in definition, f"{value!r}가 값역에서 빠졌다"

    # 값역 밖은 여전히 거부한다 — 늘리는 것이 «아무 값이나 받는 것»은 아니다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into learning_scenarios (category, level, title, prompt_template) "
                "values ('cooking', 'A2', 't', 'You are someone.')"
            )


@pytest.mark.asyncio
async def test_seed_covers_at_least_thirty_stages_across_fields(db_conn: asyncpg.Connection):
    """캡틴 요구는 「분야별 30개 이상」이다 (`TASK-102` AC#3).

    ⚠️ 개수와 **분야 수**를 함께 잰다 — 30개를 두 분야에 몰아 담으면 「분야별」이 아니다.
    """
    await migrate.seed(db_conn)

    rows = await db_conn.fetch("select category, count(*) as n from learning_scenarios group by 1")
    counts = {row["category"]: row["n"] for row in rows}

    assert sum(counts.values()) >= 30, f"상황이 {sum(counts.values())}개다 — 30개 이상이어야 한다"
    assert len(counts) >= 4, f"분야가 {len(counts)}개다 — 「분야별」이 성립하지 않는다"

    # ⛔ 업무를 지운 채 개수만 채우지 않는다 — h-doc 의 목표 수준이 업무·보고다.
    assert counts.get("business", 0) >= 6, "업무 상황이 줄었다"


# ── 018 시나리오 출처 · 생성 job · 진입 모드 (`TASK-5` · 결정 79·80) ────────────
#
# ⛔ `default 'seed'` 가 요구다 — 기존 30행이 전부 시드이므로 소급 UPDATE 없이 참이 된다.
@pytest.mark.asyncio
async def test_scenario_source_defaults_to_seed_and_is_bounded(db_conn: asyncpg.Connection):
    got = await db_conn.fetchval(
        "insert into learning_scenarios (category, level, title, prompt_template) "
        "values ('daily_life', 'A2', 'defaulted', 'You are someone.') returning source"
    )
    assert got == "seed", "기본값이 seed 가 아니면 기존 행이 출처 없이 남는다"

    made = await db_conn.fetchval(
        "insert into learning_scenarios (category, level, title, prompt_template, source) "
        "values ('daily_life', 'A2', 'made', 'You are someone.', 'generated') returning source"
    )
    assert made == "generated"

    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into learning_scenarios "
                "(category, level, title, prompt_template, source) "
                "values ('daily_life', 'A2', 'bad', 'You are someone.', 'imported')"
            )


# ⛔ 값역만 늘리고 대상 제약을 안 고치면 job 을 «넣을 수 없다» — 007 이 그 함정을 적었다.
@pytest.mark.asyncio
async def test_generate_scenario_job_can_be_enqueued(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    job_id = await db_conn.fetchval(
        "insert into analysis_jobs (job_type, session_id) "
        "values ('generate_scenario', $1) returning id",
        session_id,
    )
    assert job_id is not None

    # 대상이 어긋나면 거부한다 — 발화 단위 job 이 아니다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into analysis_jobs (job_type, utterance_id) "
                "values ('generate_scenario', $1)",
                uuid4(),
            )


# ⛔ 진입을 가릴 표지가 `learning_source` 로는 서지 않는다 — 추가 학습 메뉴 여섯 중 다섯이
# `additional` 이고 그중 셋이 `mode` 를 갖지 않아 서로 구별되지 않는다(설계서 §5). 014 가
# `pronunciation` 을 더한 것과 같은 형태로 `mode` 값역을 늘린다.
#
# ⚠️ **`review` 를 함께 잰다** — 018 이 `drop`+`add` 로 목록을 «대체»하므로 빠뜨린 값이 조용히
# 사라진다. 이 계획의 초안이 실제로 그것을 빠뜨렸고 dev DB 조회가 잡았다. 그 값을 쓰는 행이
# 지금 없어 이 단정이 없으면 게이트도 침묵한다.
@pytest.mark.asyncio
async def test_session_mode_domain_includes_scenario_intake(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)

    got = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'scenario_intake') "
        "returning mode",
        migrate.USER_ID,
    )
    assert got == "scenario_intake"

    definition = await db_conn.fetchval(
        "select pg_get_constraintdef(oid) from pg_constraint "
        "where conname = 'learning_sessions_mode_check'"
    )
    assert definition is not None
    # ⛔ **파이썬 값역을 여기서 함께 잰다** (`TASK-148` ③). `models/session.SESSION_MODES` 가 이
    # CHECK 의 파이썬 짝이고, 어긋나면 코드가 값역 밖 값을 쓰거나 열린 값을 못 쓴다.
    # ⛔ **아래 목록을 `SESSION_MODES` 로 대체하지 않는다 — 그러면 판별력이 사라진다**: 양쪽에서
    # 같은 값을 지우면 통과해 버린다. 목록을 손으로 적어 두면 어느 한쪽이 빠질 때 반드시 깨진다.
    expected = ("speaking", "shadowing", "review", "pronunciation", "scenario_intake")
    assert SESSION_MODES == expected, (
        "파이썬 값역이 018 의 CHECK 와 갈라졌다 — 어느 쪽을 고칠지 정하고 둘을 함께 고친다"
    )
    # ⛔ **따옴표까지 맞춘다** — `pronunciation_drill` 같은 값이 나중에 들어오면 맨 문자열 비교는
    # `pronunciation` 이 사라져도 통과한다. `ohmyenglish-19` 세션이 이 형태를 제안했고 근거가 맞다.
    for value in expected:
        assert f"'{value}'" in definition, (
            f"{value!r}가 값역에서 사라졌다 — `drop`+`add` 가 목록을 대체한다. "
            "쓰는 코드가 없는 값이라 다른 어떤 테스트도 이것을 잡지 않는다"
        )

    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into learning_sessions (user_id, mode) values ($1, 'intake')",
                migrate.USER_ID,
            )


# ⑤-2 시드 행은 **무대**다 — 질문이 아니고 `title`과 `prompt_template`이 갈라져 있다.
# ⚠️ 머리 문장에서 개수를 뺐다 — 이 테스트의 범위가 `daily_life` 3행에서 전체로 넓어졌는데
# (아래 주석) 머리만 「3행」으로 남아 있었다(2026-09-14 감사).
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

    # ⚠️ **범위를 `daily_life` 에서 전체로 넓혔다** (`TASK-4` · 2026-09-12). 이전 판은
    # `where category = 'daily_life'` 로 좁히고 `len(rows) == 3` 을 함께 단정했는데, 위 주석이
    # 말하는 이 테스트의 몫은 **내용의 종류**이고 개수는 ⑤가 지킨다 — 개수 단정이 여기 있으면
    # 시드를 늘릴 때마다 두 곳이 함께 흔들린다. 업무 6종도 같은 규칙을 받아야 하므로
    # 필터를 걷는 것이 커버리지를 넓히면서 그 어긋남을 없앤다.
    rows = await db_conn.fetch(
        "select title, prompt_template from learning_scenarios order by category, title"
    )
    assert rows, "시드가 0행이다"

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
            # ⛔ **스키마를 걸어야 한다** — `public` 에 같은 이름의 호환 뷰가 있고(026) 뷰는 모든
            #    컬럼을 `is_nullable=YES` 로 보고한다. 걸지 않으면 두 행이 섞여 판정이 뒤집힌다
            #    (`TASK-41` 에서 실제로 이 단정이 그렇게 깨졌다).
            "where table_name = 'pronunciation_attempts' "
            "and table_schema = current_schema()"
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
    #
    # ⚠️ `transcript_analysis`는 **024**가 더했다(`TASK-88` · 결정 93). 전사문 분석이 발음
    # 기원으로 판정한 오류가 그 값으로 들어온다. ⛔ **네 값을 전부 넣어 본다** — 아래 주석이 그
    # 전수 삽입에 기대어 목록 재확인을 생략하는 근거를 갖는다.
    for source in ("nova_tool", "korean_transcript", "agent_reprompt", "transcript_analysis"):
        await db_conn.execute(
            "insert into pronunciation_attempts "
            "(session_id, target_form, outcome, signal_source, resolved_at) "
            "values ($1, 'I think.', 'unclear', $2, now())",
            session_id,
            source,
        )

    # ⛔ **`pg_get_constraintdef` 로 목록을 다시 확인하지 않는다 — 이 자리에서는 판별력이 0이다.**
    # 2026-09-14에 그 단정을 넣었다가 무력화로 빼냈다: 024에서 `transcript_analysis`를 지우면
    # **위 삽입 루프가 `CheckViolationError`로 먼저 실패**하므로 목록 단정에는 도달하지 않는다.
    # ⚠️ 이 파일의 `learning_sessions_mode_check`(`:586`)·`learning_scenarios_category_check`
    # (`:481`)는 같은 단정을 **정당하게** 갖는다 — 그쪽은 값역의 값을 **전부 삽입해 보지 않기**
    # 때문이다. ⇒ 그 형태를 베낄 때는 「값을 다 넣어 보는가」를 먼저 본다.
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
        # ⛔ 스키마를 건다 — `public` 의 호환 뷰와 이름이 같다(026 · 위 단정의 주석 참조).
        "where table_name = 'error_occurrences' and column_name = 'suggested_contexts' "
        "and table_schema = current_schema()"
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
        # ⛔ **따옴표까지 맞춘다** (`TASK-131`) — 맨 부분 일치는 «다른 값이 그 문자열을 품으면»
        # 통과한다. 직접 잼: `learning` 이 사라지고 `learning_drill` 이 들어온 가짜 정의로
        # `'learning' in definition` 은 **True**, `"'learning'" in definition` 은 **False** 였다.
        # ⚠️ 이 값역 넷은 서로의 부분 문자열이 아니라 **아직** 안전하다 — 고치는 이유는 값역을
        # 늘리는 일이 이미 세 번 있었다는 것이다(014·017·018).
        assert f"'{value}'" in definition, (
            f"{value!r}가 값역에서 빠졌다 — `drop`+`add` 로 목록을 «대체»하며 흘렸을 자리다. "
            "dev DB 의 실제 행은 `learning` 뿐이므로(직접 조회: 128행) 나머지 셋은 «데이터로는» "
            "아무도 그 삭제를 알아채지 못한다"
        )


# ── 016 scenario_pick (대화 상황 배치 · `TASK-4` · 결정 73·74) ─────────────────
#
# ⚠️ **nullable 이 요구다.** 016 이전 세션에는 이 값이 없고 소급해 채우지 않는다 — 과거 세션의
# 신규 여부는 그 시점의 창에 달렸고 지금 창으로 다시 접으면 실제로 일어난 것과 다른 값이 된다
# (설계서 §5). `scenario_rotation.pick_scenario` 가 `None` 을 세지 않는 것이 그 짝이다.
@pytest.mark.asyncio
async def test_scenario_pick_is_nullable_and_bounded(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)

    # ⑴ 값을 주지 않아도 행이 만들어진다 — 과거 행과 같은 모양이다.
    null_row = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') "
        "returning scenario_pick",
        migrate.USER_ID,
    )
    assert null_row is None

    # ⑵ 값역 안의 두 값은 받는다.
    for value in ("new", "repeat"):
        got = await db_conn.fetchval(
            "insert into learning_sessions (user_id, mode, scenario_pick) "
            "values ($1, 'speaking', $2) returning scenario_pick",
            migrate.USER_ID,
            value,
        )
        assert got == value

    # ⑶ 값역 밖은 거부한다 — 오타가 조용히 집계를 틀리게 하는 것을 막는다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into learning_sessions (user_id, mode, scenario_pick) "
                "values ($1, 'speaking', 'fresh')",
                migrate.USER_ID,
            )


# ⑥ 022 — 합성 클립 오디오의 자리와 예외 경계 (`TASK-66` · 결정 90 ·
#      설계서 `2026-09-14-shadowing-clip-audio-design.md` §3).
@pytest.mark.asyncio
async def test_shadowing_clip_audio_filename_must_equal_the_row_id(
    db_conn: asyncpg.Connection,
):
    """파일명 규약을 스키마가 강제한다 — 경로 구분자와 확장자 변경이 같은 CHECK 에 걸린다.

    ⛔ **이 단정이 경로 이탈 방어의 첫 겹이다.** 서버는 경로를 `item_id` 로 조립하지만(둘째 겹),
    DB 에 `../` 가 들어갈 수 있으면 그 조립을 신뢰하는 다음 사람이 뚫린다.
    """
    item_id = await db_conn.fetchval(
        "insert into shadowing_items (source_title, transcript, clip_start_sec, "
        "clip_end_sec, level) values ('Morning', 'I wake up at seven.', 0, 16.64, 'A2') "
        "returning id"
    )

    # 규약대로면 받는다.
    await db_conn.execute(
        "update shadowing_items set audio_filename = $2 where id = $1", item_id, f"{item_id}.wav"
    )
    assert (
        await db_conn.fetchval("select audio_filename from shadowing_items where id = $1", item_id)
        == f"{item_id}.wav"
    )

    # 확장자가 다르거나 경로가 섞이거나 남의 이름이면 거부된다.
    for bad in (f"{item_id}.opus", f"clips/{item_id}.wav", "../secrets.wav", "x.wav"):
        with pytest.raises(asyncpg.CheckViolationError):
            async with db_conn.transaction():
                await db_conn.execute(
                    "update shadowing_items set audio_filename = $2 where id = $1", item_id, bad
                )


@pytest.mark.asyncio
async def test_shadowing_clip_audio_is_rejected_when_the_clip_has_a_source_url(
    db_conn: asyncpg.Connection,
):
    """R10-7 예외의 경계 — 출처 링크가 있는 클립에는 오디오가 붙지 않는다.

    결정 47 이 연 범위는 「합성한 쉐도잉 클립 오디오」 하나이고, 출처 링크가 있는 것은 외부
    저작물이라 PRD §5(*"저작물 전체를 저장하지 않는다"*)가 막는다. 011 의
    `utterances_audio_only_for_shadowing` 이 학습자 낭독 자리에서 한 일과 같다.
    """
    item_id = await db_conn.fetchval(
        "insert into shadowing_items (source_title, source_url, transcript, clip_start_sec, "
        "clip_end_sec, level) values ('Talk', 'https://example.com/v', 'I wake up.', 0, 40, 'A2') "
        "returning id"
    )

    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "update shadowing_items set audio_filename = $2 where id = $1",
                item_id,
                f"{item_id}.wav",
            )


# ⑦ 023 — 주간 리포트 (`TASK-26.1` · 결정 4·58·91 ·
#      설계서 `2026-09-14-weekly-report-design.md` §3·§6).
@pytest.mark.asyncio
async def test_weekly_report_week_start_must_be_monday(db_conn: asyncpg.Connection):
    """⛔ 결정 4·58 의 「월요일 시작」을 값역으로 새긴다.

    계산은 `date_trunc('week', …)` 이고 Postgres 가 월요일을 주 시작으로 쓴다(ISO 8601). 이 CHECK 가
    없으면 **일요일 기준으로 계산한 코드가 조용히 섞이고** 두 주가 겹친 행이 생긴다.
    """
    await _insert_user(db_conn)

    # 2026-09-14 는 월요일이다.
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start, timezone) "
        "values ($1, '2026-09-14', 'Asia/Seoul')",
        migrate.USER_ID,
    )

    # ⚠️ asyncpg 는 `date` 파라미터에 문자열을 받지 않는다(`'str' object has no attribute
    # 'toordinal'`) — 날짜는 `date` 객체로 준다.
    for bad in (date(2026, 9, 13), date(2026, 9, 15)):  # 일요일 · 화요일
        with pytest.raises(asyncpg.CheckViolationError):
            async with db_conn.transaction():
                await db_conn.execute(
                    "insert into weekly_reports (user_id, week_start, timezone) "
                    "values ($1, $2, 'Asia/Seoul')",
                    migrate.USER_ID,
                    bad,
                )


@pytest.mark.asyncio
async def test_weekly_report_is_one_row_per_user_and_week(db_conn: asyncpg.Connection):
    """재계산이 행을 늘리지 않는다 — `on conflict (user_id, week_start)` 가 이 키를 쓴다."""
    await _insert_user(db_conn)
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start, timezone) "
        "values ($1, '2026-09-14', 'Asia/Seoul')",
        migrate.USER_ID,
    )

    with pytest.raises(asyncpg.UniqueViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into weekly_reports (user_id, week_start, timezone) "
                "values ($1, '2026-09-14', 'Asia/Seoul')",
                migrate.USER_ID,
            )


@pytest.mark.asyncio
async def test_weekly_job_targets_a_session_and_nothing_else(db_conn: asyncpg.Connection):
    """⛔ `job_type` 값역만 늘리면 job 이 들어가지 않는다 — 상호배타 CHECK 를 함께 고쳐야 한다.

    018 주석이 그 함정을 이미 적었다: *"분기를 함께 더해야 한다"*. 대상이 **세션**인 이유는 그
    세션의 종료가 트리거이기 때문이고, 「어떤 주」는 워커가 다시 구한다(설계서 §6).
    """
    await _insert_user(db_conn)
    session_id = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        migrate.USER_ID,
    )

    assert (
        await db_conn.fetchval(
            "insert into analysis_jobs (job_type, session_id) "
            "values ('summarize_week', $1) returning id",
            session_id,
        )
        is not None
    )

    # 대상이 없으면 거부된다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute("insert into analysis_jobs (job_type) values ('summarize_week')")

    # 발화를 함께 주는 것도 거부된다 — 상호배타다.
    utterance_id = await db_conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no) "
        "values ($1, 'user', 'I worked on the API.', 1) returning id",
        session_id,
    )
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into analysis_jobs (job_type, session_id, utterance_id) "
                "values ('summarize_week', $1, $2)",
                session_id,
                utterance_id,
            )


@pytest.mark.asyncio
async def test_llm_calls_accepts_the_weekly_purpose(db_conn: asyncpg.Connection):
    """⚠️ `TASK-134` 가 이 자리에서 **조용한 소실**을 잡았다 — 값역이 좁아 토큰 기록이 사라졌고
    `usage.py` 가 `PostgresError` 를 삼켜 아무도 몰랐다. 같은 실패를 반복하지 않는다.
    """
    await db_conn.execute(
        "insert into llm_calls (provider, model_id, purpose, input_tokens, output_tokens) "
        "values ('bedrock', 'us.anthropic.claude-opus-5', 'summarize_week', 10, 20)"
    )

    assert (
        await db_conn.fetchval("select count(*) from llm_calls where purpose = 'summarize_week'")
        == 1
    )


# ── 파이썬 값역과 DB CHECK 의 «양방향» 대조 (`TASK-150` · 사용자 결정 122) ──────────
#
# ⛔ **닫는 것은 한 방향뿐이다 — 「DB 가 바뀌고 파이썬이 안 바뀐 경우」다.** 반대 방향
# (파이썬만 바뀜)은 이미 `tests/unit/test_claude_schema.py` 와 `test_pronunciation.py` 의 리터럴
# 단정이 잡는다. 그 두 단정의 **이름**이 「마이그레이션과 일치」를 약속하면서 실제로는
# 마이그레이션을
# 한 번도 읽지 않는다는 것이 정리 회차(`TASK-144`)의 R5 각도가 찾은 것이고, 이 절이 그 약속을
# 실제로 이행한다.
#
# ⚠️ **`pg_get_constraintdef` 단정이 판별력을 갖는 조건이 있다** — 같은 테스트가 값역의 값을 **전부
# 삽입해 보면** 그 루프가 먼저 `CheckViolationError` 로 실패해서 목록 단정에 도달하지 않는다
# (이 파일 `test_pronunciation_attempts_signal_source_check` 의 주석이 그 무력화를 기록한다).
# ⇒ 그래서 이 절의 단정들은 **삽입을 하지 않는다.** 읽고 대조만 한다.
_CHECK_VALUE_RE = re.compile(r"'([a-z_0-9]+)'::text")


async def _check_values(conn: asyncpg.Connection, constraint: str) -> set[str]:
    """그 CHECK 제약이 허용하는 문자열 값 집합. 제약이 없으면 실패한다(이름 오타를 잡는다)."""
    definition = await conn.fetchval(
        "select pg_get_constraintdef(oid) from pg_constraint where conname = $1", constraint
    )
    assert definition is not None, (
        f"제약 {constraint} 이 없다 — 이름이 바뀌었거나 마이그레이션이 빠졌다"
    )
    values = set(_CHECK_VALUE_RE.findall(definition))
    assert values, f"제약 {constraint} 의 정의에서 값을 뽑지 못했다: {definition}"
    return values


@pytest.mark.asyncio
async def test_error_category_check_matches_the_python_value_domain(db_conn: asyncpg.Connection):
    from app.models.analysis import ERROR_CATEGORIES

    assert await _check_values(db_conn, "error_patterns_category_check") == set(ERROR_CATEGORIES)


@pytest.mark.asyncio
async def test_severity_check_matches_the_python_value_domain(db_conn: asyncpg.Connection):
    from app.models.analysis import SEVERITIES

    assert await _check_values(db_conn, "error_occurrences_severity_check") == set(SEVERITIES)


@pytest.mark.asyncio
async def test_pronunciation_outcome_check_matches_the_python_value_domain(
    db_conn: asyncpg.Connection,
):
    from app.models.pronunciation import PRONUNCIATION_OUTCOMES

    assert await _check_values(db_conn, "pronunciation_attempts_outcome_check") == set(
        PRONUNCIATION_OUTCOMES
    )


@pytest.mark.asyncio
async def test_signal_source_check_matches_the_python_value_domain(db_conn: asyncpg.Connection):
    """⚠️ 024 가 `transcript_analysis` 를 더한 자리다 — 그 값이 파이썬 쪽에도 있는지 여기서 잰다."""
    from app.models.pronunciation import SIGNAL_SOURCES

    assert await _check_values(db_conn, "pronunciation_attempts_signal_source_check") == set(
        SIGNAL_SOURCES
    )


# ⑤ 027 `youtube_videos` + `shadowing_items.youtube_video_id` (`TASK-162`)
#
# 설계: `docs/design/2026-09-18-video-learning-design.md` §2.
# ⛔ **`youtube_id` 의 형태를 스키마가 가두는 이유**: 그 값이 **URL 조립에 쓰인다**
# (`https://i.ytimg.com/vi/<id>/hqdefault.jpg` · `https://www.youtube.com/watch?v=<id>`).
# 파싱이 뚫려 임의 문자열이 들어오면 화면이 만드는 URL 이 우리 통제 밖으로 나간다 — 값역이 첫 겹이고
# `services/video_url.parse_youtube_id` 가 둘째 겹이다.
# ⚠️ **`youtube_video_id` 가 있으면 `source_url` 이 필수인 것이 정책 방어와 이어진다** — 기존
# `shadowing_items_audio_only_for_synthetic`(`audio_filename is null or source_url is null`)이
# 그러면 **오디오 저장을 자동으로 막는다**(YouTube Developer Policies III.E.1).
async def _insert_video(conn: asyncpg.Connection, youtube_id: str = "dQw4w9WgXcQ"):
    return await conn.fetchval(
        "insert into youtube_videos (youtube_id, title, channel_name) "
        "values ($1, 'A title', 'A channel') returning id",
        youtube_id,
    )


@pytest.mark.asyncio
async def test_youtube_videos_accepts_an_eleven_character_id(db_conn: asyncpg.Connection):
    video_id = await _insert_video(db_conn)

    assert video_id is not None


@pytest.mark.asyncio
async def test_youtube_videos_rejects_an_id_that_is_not_eleven_characters(
    db_conn: asyncpg.Connection,
):
    # ⚠️ 위반을 여러 번 내므로 각각을 **savepoint 안에서** 낸다 — 근거는 위
    # `test_drill_turns_expected_is_nullable_and_rejects_non_positive` 의 주석과 같다.
    for bad in ("dQw4w9WgXc", "dQw4w9WgXcQQ", "dQw4w9WgXc!", ""):
        with pytest.raises(asyncpg.CheckViolationError):
            async with db_conn.transaction():
                await _insert_video(db_conn, bad)


@pytest.mark.asyncio
async def test_youtube_videos_rejects_blank_title_and_channel(db_conn: asyncpg.Connection):
    for title, channel in (("   ", "A channel"), ("A title", "   ")):
        with pytest.raises(asyncpg.CheckViolationError):
            async with db_conn.transaction():
                await db_conn.execute(
                    "insert into youtube_videos (youtube_id, title, channel_name) "
                    "values ('dQw4w9WgXcQ', $1, $2)",
                    title,
                    channel,
                )


@pytest.mark.asyncio
async def test_youtube_videos_rejects_the_same_video_twice(db_conn: asyncpg.Connection):
    await _insert_video(db_conn)

    with pytest.raises(asyncpg.UniqueViolationError):
        await _insert_video(db_conn)


@pytest.mark.asyncio
async def test_a_shadowing_item_from_a_video_must_carry_its_source_url(
    db_conn: asyncpg.Connection,
):
    """⛔ 출처 링크 없이 영상에 매달 수 없다 — 기존 오디오 금지 CHECK 가 그 위에 선다."""
    video_id = await _insert_video(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into shadowing_items "
            "(source_title, transcript, clip_start_sec, clip_end_sec, level, youtube_video_id) "
            "values ('A title', 'Hello there', 0, 3, 'A2', $1)",
            video_id,
        )


@pytest.mark.asyncio
async def test_a_shadowing_item_from_a_video_cannot_carry_audio(db_conn: asyncpg.Connection):
    """정책 III.E.1(오디오 저장 금지)을 **기존** CHECK 가 지킨다 — 새 방어를 더하지 않았다."""
    video_id = await _insert_video(db_conn)
    item_id = await db_conn.fetchval(
        "insert into shadowing_items "
        "(source_title, source_url, transcript, clip_start_sec, clip_end_sec, level, "
        " youtube_video_id) "
        "values ('A title', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'Hello there', "
        "        0, 3, 'A2', $1) returning id",
        video_id,
    )

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "update shadowing_items set audio_filename = $2 where id = $1",
            item_id,
            f"{item_id}.wav",
        )


@pytest.mark.asyncio
async def test_deleting_a_video_keeps_the_phrases_and_clears_the_link(
    db_conn: asyncpg.Connection,
):
    """⛔ 설계서 §1 질문 1 의 답이다 — 문장은 사용자가 만든 학습 자산이므로 남는다."""
    video_id = await _insert_video(db_conn)
    item_id = await db_conn.fetchval(
        "insert into shadowing_items "
        "(source_title, source_url, transcript, clip_start_sec, clip_end_sec, level, "
        " youtube_video_id) "
        "values ('A title', 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'Hello there', "
        "        0, 3, 'A2', $1) returning id",
        video_id,
    )

    await db_conn.execute("delete from youtube_videos where id = $1", video_id)

    row = await db_conn.fetchrow(
        "select transcript, source_url, youtube_video_id from shadowing_items where id = $1",
        item_id,
    )
    assert row is not None, "영상을 지웠는데 문장이 함께 사라졌다"
    assert row["transcript"] == "Hello there"
    assert row["source_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert row["youtube_video_id"] is None, "연결이 null 로 끊기지 않았다"
