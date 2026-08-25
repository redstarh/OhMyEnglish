#!/usr/bin/env python3
"""W-live 스모크 — 실제 Claude로 분석 파이프라인 전체를 관통시킨다.

AC 정본: `docs/design/2026-08-25-first-slice-acceptance-criteria.md` §W-live.
Task 정본: `.superpowers/sdd/2026-08-25-phase1-implementation-plan/task-11-brief.md`.

기존 앱 코드를 그대로 쓴다 — `app.audio_gateway.fixtures.FIXTURE_TURNS`,
`app.services.utterances.save_final_transcript`, `app.workers.analysis_worker.claim_one`,
`app.services.analysis.process_analysis`, `app.workers.claude_client.BedrockClaudeClient`,
`app.config`. 이 스크립트가 새로 만드는 것은 (1) 전용 스모크 DB 준비
(`scripts/db_utils.recreate_database` — tests/conftest.py와 공유하는 drop/create
+ 마이그레이션 적용, DB명만 다르다)와 (2) Claude 프롬프트/응답을 기록하는 얇은
래퍼(`_RecordingClaudeClient`, 실제 호출은 그대로 위임)뿐이다.

**dev DB(`ohmyenglish`)·test DB(`ohmyenglish_test`)를 쓰지 않는다** — 매 실행마다
`ohmyenglish_smoke`를 drop/create해 001 마이그레이션을 새로 적용한다. 실행이 끝난
뒤에도 DB를 지우지 않는다 — 실패 시 `psql`로 상태를 들여다볼 수 있어야 증거로서
의미가 있다(다음 실행이 다시 drop/create한다).

흐름은 AC 문서가 명시한 순서 그대로다: 세션 생성 → 발화 1 저장 → claim →
(실제 Claude) process_analysis → 발화 2 저장 → claim → (실제 Claude)
process_analysis → 단정. **재시도 없음** — 실제 Claude 출력은 비결정적이므로
이 스크립트를 1회 실행하면 1회 판정으로 끝낸다. 실행:

    cd app/backend && .venv/bin/python ../../scripts/smoke_analysis.py
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from uuid import UUID

import asyncpg
from db_utils import recreate_database

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "app" / "backend"
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

# `app` 패키지는 app/backend 아래에 있다. 이 스크립트는 `cd app/backend &&
# .venv/bin/python ../../scripts/smoke_analysis.py` 형태로 실행되므로 스크립트
# 파일 경로에서 backend 디렉터리를 계산해 넣는다 — cwd에 의존하지 않는다.
sys.path.insert(0, str(BACKEND_DIR))

from app.audio_gateway.fixtures import FIXTURE_TURNS  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import close_pool  # noqa: E402
from app.db import pool as get_db_pool  # noqa: E402
from app.services.analysis import process_analysis  # noqa: E402
from app.services.jobs import ClaimedJob  # noqa: E402
from app.services.utterances import save_final_transcript  # noqa: E402
from app.workers.analysis_worker import claim_one  # noqa: E402
from app.workers.claude_client import BedrockClaudeClient, ClaudeClient  # noqa: E402

SMOKE_DB_NAME = "ohmyenglish_smoke"

# AC W-live 단정 4: 이 스모크는 공통 픽스처 발화 1·2(관사 누락 오류)만 다루므로
# 신규 key의 category는 반드시 article이어야 한다 — 일반 규칙(`{category}_snake`)이
# 아니라 AC가 못박은 리터럴 접두어다.
NEW_KEY_PATTERN = re.compile(r"^article_[a-z0-9_]+$")


class _RecordingClaudeClient:
    """실제 `BedrockClaudeClient`를 그대로 호출하고 프롬프트·원문 응답만 기록한다.

    분석 로직은 전혀 재구현하지 않는다 — `analyze()`는 내부 클라이언트에 위임만
    한다. 단정 3(두 번째 프롬프트에 첫 pattern_key 포함)과 진단(비결정적 실패 시
    Claude가 실제로 뭐라 답했는지)을 위해 호출 순서대로 기록만 남긴다.
    """

    def __init__(self, inner: ClaudeClient) -> None:
        self._inner = inner
        self.prompts: list[str] = []
        self.raw_responses: list[str] = []

    async def analyze(self, prompt: str) -> str:
        self.prompts.append(prompt)
        raw = await self._inner.analyze(prompt)
        self.raw_responses.append(raw)
        return raw


async def _seed_user_and_session(pool: asyncpg.Pool) -> tuple[UUID, UUID]:
    """`tests/conftest.py`의 `committed_session` 픽스처와 같은 패턴 — 고정 사용자
    1명 + `active` 학습 세션 1개. 스모크 DB는 다음 실행에서 drop되므로 teardown이
    필요 없다."""
    async with pool.acquire() as conn:
        user_id = await conn.fetchval(
            "insert into users (display_name) values ('W-live Smoke User') returning id"
        )
        session_id = await conn.fetchval(
            "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
            user_id,
        )
    assert user_id is not None and session_id is not None
    return user_id, session_id


async def _claim(pool: asyncpg.Pool) -> ClaimedJob:
    job = await claim_one(pool)
    if job is None:
        raise RuntimeError(
            "claim할 job이 없다 — save_final_transcript가 analyze_utterance job을 "
            "등록했는지 확인하라"
        )
    return job


async def _job_row(pool: asyncpg.Pool, job_id: UUID) -> asyncpg.Record:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select status, attempts, last_error from analysis_jobs where id = $1", job_id
        )
    assert row is not None
    return row


async def _patterns(pool: asyncpg.Pool, user_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "select category, pattern_key, target_form, frequency "
            "from error_patterns where user_id = $1 order by created_at",
            user_id,
        )


async def _occurrences(pool: asyncpg.Pool, session_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "select eo.original_span, eo.correction, eo.explanation, eo.severity, eo.confidence "
            "from error_occurrences eo join utterances u on u.id = eo.utterance_id "
            "where u.session_id = $1 order by u.created_at, eo.created_at",
            session_id,
        )


def _report(
    job_label: str, row: asyncpg.Record, claude: _RecordingClaudeClient, index: int
) -> None:
    print(f"  {job_label}: status={row['status']} attempts={row['attempts']}", end="")
    if row["last_error"]:
        print(f" last_error={row['last_error']!r}")
    else:
        print()
    if len(claude.raw_responses) > index:
        preview = claude.raw_responses[index][:300]
        print(f"  {job_label} Claude 원문 응답(앞 300자): {preview!r}")


class Check:
    def __init__(self, name: str, passed: bool, detail: str = "") -> None:
        self.name = name
        self.passed = passed
        self.detail = detail


def _print_checks(checks: list[Check]) -> bool:
    print("\n=== 단정 (AC §W-live) ===")
    all_passed = True
    for check in checks:
        mark = "✓" if check.passed else "✗"
        line = f"{mark} {check.name}"
        if not check.passed:
            all_passed = False
            if check.detail:
                line += f" — {check.detail}"
        print(line)
    return all_passed


async def main() -> int:
    # AWS_BEARER_TOKEN_BEDROCK 없으면 DB조차 만들지 않고 즉시 종료한다 — 뒤늦게
    # Claude 호출 단계에서 실패하면 스모크 DB만 만들고 아무 의미 있는 진단 없이
    # 끝나기 때문이다.
    if not os.environ.get("AWS_BEARER_TOKEN_BEDROCK"):
        print(
            "ERROR: AWS_BEARER_TOKEN_BEDROCK 환경변수가 없다 — 실제 Claude 호출이 "
            "즉시 실패한다. `export AWS_BEARER_TOKEN_BEDROCK=...` 후 재실행하라.",
            file=sys.stderr,
        )
        return 1

    print(f"[1/4] {SMOKE_DB_NAME} drop/create + 001 마이그레이션 적용")
    try:
        smoke_dsn = await recreate_database(SMOKE_DB_NAME, MIGRATIONS_DIR)
    except (OSError, asyncpg.PostgresError) as exc:
        print(
            f"ERROR: 스모크 DB 준비 실패 — {type(exc).__name__}: {exc}\n"
            "podman DB(5433)가 기동 중인지 확인하라: scripts/dev_db.sh status",
            file=sys.stderr,
        )
        return 1

    # get_settings()가 처음 호출되기 전에 덮어써야 한다 — lru_cache라 그 이후로는
    # 이 프로세스 안에서 영구히 이 DSN을 쓴다(스모크 전용, dev/test DB와 분리).
    os.environ["DATABASE_URL"] = smoke_dsn

    try:
        settings = get_settings()
    except Exception as exc:  # pydantic ValidationError 등 — 원인을 그대로 보여준다
        print(
            f"ERROR: Settings 로드 실패 — {type(exc).__name__}: {exc}\n"
            "AWS_REGION 등 필수 환경변수를 확인하라.",
            file=sys.stderr,
        )
        return 1

    db_pool = await get_db_pool()
    try:
        user_id, session_id = await _seed_user_and_session(db_pool)
        print(f"  user_id={user_id} session_id={session_id}")

        claude = _RecordingClaudeClient(BedrockClaudeClient(settings))
        turn1_answer = FIXTURE_TURNS[0][1]
        turn2_answer = FIXTURE_TURNS[1][1]

        print(f"[2/4] 발화 1 저장 → claim → process_analysis (실제 Claude): {turn1_answer!r}")
        async with db_pool.acquire() as conn:
            await save_final_transcript(conn, session_id, turn1_answer)
        job1 = await _claim(db_pool)
        await process_analysis(db_pool, claude, job1)
        job1_row = await _job_row(db_pool, job1.id)
        _report("job1", job1_row, claude, 0)
        patterns_after_1 = await _patterns(db_pool, user_id)

        print(f"[3/4] 발화 2 저장 → claim → process_analysis (실제 Claude): {turn2_answer!r}")
        async with db_pool.acquire() as conn:
            await save_final_transcript(conn, session_id, turn2_answer)
        job2 = await _claim(db_pool)
        await process_analysis(db_pool, claude, job2)
        job2_row = await _job_row(db_pool, job2.id)
        _report("job2", job2_row, claude, 1)

        patterns = await _patterns(db_pool, user_id)
        occurrences = await _occurrences(db_pool, session_id)
        pattern = patterns[0] if len(patterns) == 1 else None
        first_key = patterns_after_1[0]["pattern_key"] if len(patterns_after_1) == 1 else None
        second_prompt = claude.prompts[1] if len(claude.prompts) >= 2 else None

        print("[4/4] 단정 검사")
        checks = [
            Check(
                "error_patterns 1행",
                len(patterns) == 1,
                f"실제 {len(patterns)}행: {[r['pattern_key'] for r in patterns]!r}",
            ),
            Check(
                "error_occurrences 2행",
                len(occurrences) == 2,
                f"실제 {len(occurrences)}행",
            ),
            Check(
                "frequency=2",
                pattern is not None and pattern["frequency"] == 2,
                f"실제 frequency={pattern['frequency'] if pattern else 'N/A (patterns != 1행)'}",
            ),
            Check(
                "category=article",
                pattern is not None and pattern["category"] == "article",
                f"실제 category={pattern['category'] if pattern else 'N/A'} "
                "— Claude가 다르게 분류했을 수 있다(비결정적). 위 Claude 원문 응답 참조.",
            ),
            Check(
                "target_form에 'the' 포함",
                pattern is not None and "the" in pattern["target_form"],
                f"실제 target_form={pattern['target_form'] if pattern else 'N/A'!r}",
            ),
            Check(
                "두 번째 분석 프롬프트에 첫 pattern_key 포함",
                first_key is not None and second_prompt is not None and first_key in second_prompt,
                f"first_key={first_key!r}, second_prompt 존재={second_prompt is not None}",
            ),
            Check(
                "신규 key 형식 ^article_[a-z0-9_]+$",
                first_key is not None and NEW_KEY_PATTERN.fullmatch(first_key) is not None,
                f"실제 pattern_key={first_key!r}",
            ),
        ]
        all_passed = _print_checks(checks)

        print("\n=== 저장된 데이터 (증거) ===")
        for row in patterns:
            print(
                f"pattern: category={row['category']!r} pattern_key={row['pattern_key']!r} "
                f"target_form={row['target_form']!r} frequency={row['frequency']}"
            )
        for index, row in enumerate(occurrences, start=1):
            print(
                f"occurrence[{index}]: original_span={row['original_span']!r} "
                f"correction={row['correction']!r} explanation={row['explanation']!r} "
                f"severity={row['severity']!r} confidence={row['confidence']}"
            )

        print(
            f"\n{'PASS' if all_passed else 'FAIL'}: "
            f"{sum(1 for c in checks if c.passed)}/{len(checks)} 단정 통과"
        )
        return 0 if all_passed else 1
    finally:
        await close_pool()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
