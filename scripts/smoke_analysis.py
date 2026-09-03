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
import json
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
from app.config import Settings, get_settings, prepare_bedrock_credentials  # noqa: E402
from app.db import close_pool  # noqa: E402
from app.db import pool as get_db_pool  # noqa: E402
from app.models.analysis import ATTEMPT_OUTCOMES  # noqa: E402
from app.services.analysis import process_analysis  # noqa: E402
from app.services.jobs import ClaimedJob  # noqa: E402
from app.services.utterances import (  # noqa: E402
    flush_pending_analysis,
    save_final_transcript,
)
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


# I-1(2026-09-02) 이후 분석 job은 **저장이 아니라 턴 경계**에서 걸린다
# (`services/utterances.save_final_transcript` docstring). 사용자 발화만 저장하면
# claim할 job이 없다 — 이 스크립트는 그 변경 전(2026-08-31)이 마지막 수정이라
# 그때부터 `claim할 job이 없다`로 죽어 있었다(2026-09-04 실측).
# 게이트웨이(`audio_gateway/session.py`)와 같은 순서로 agent final을 하나 끼워 턴을 닫는다.
AGENT_ACK = "Tell me more."


async def _save_user_turn(pool: asyncpg.Pool, session_id: UUID, text: str) -> None:
    """사용자 확정 전사문 저장 + 턴 닫기 — 이 두 번째 단계가 분석 job을 등록한다.

    **`flush_pending_analysis`의 반환값을 확인한다.** 버리면 다음 턴 경계 변경으로 flush가
    0건이나 2건을 등록해도 원인 지점에서 조용하고, 한참 뒤 `_claim`에서 엉뚱한 곳을 가리키는
    메시지로만 드러난다 — 이 스크립트를 이틀간 죽어 있게 만든 침묵이 정확히 그것이다(함정 H-AA).
    """
    async with pool.acquire() as conn:
        utterance = await save_final_transcript(conn, session_id, text)
        await save_final_transcript(conn, session_id, AGENT_ACK, speaker="agent")
        enqueued = await flush_pending_analysis(conn, session_id)
    if enqueued != [utterance.id]:
        raise RuntimeError(
            f"턴 경계가 등록한 job이 기대와 다르다: {enqueued!r} (기대 [{utterance.id}]) — "
            "flush_pending_analysis의 등록 규칙이 바뀌었는지 본다"
        )


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
            "claim할 job이 없다 — 등록 주체는 **턴 경계의 flush_pending_analysis**다"
            "(I-1 이후. save_final_transcript는 등록하지 않는다). `_save_user_turn`을 보라"
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
            "select category, pattern_key, target_form, frequency, next_review_at, mastery_score "
            "from error_patterns where user_id = $1 order by created_at",
            user_id,
        )


async def _occurrences(pool: asyncpg.Pool, session_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return await conn.fetch(
            "select eo.original_span, eo.correction, eo.explanation, eo.severity, eo.confidence, "
            "       eo.suggested_contexts "
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
    # 자격증명이 없으면 DB조차 만들지 않고 즉시 종료한다 — 뒤늦게 Claude 호출
    # 단계에서 실패하면 스모크 DB만 만들고 아무 의미 있는 진단 없이 끝나기 때문이다.
    #
    # 검사는 config의 단일 이음새에 위임한다(F5) — 이 스크립트는 자격증명
    # 환경변수 이름을 알지 않는다. `get_settings()`를 쓰지 않는 이유는 아래
    # DATABASE_URL 덮어쓰기 주석과 같다 — lru_cache에 dev DSN이 고정된다.
    try:
        prepare_bedrock_credentials(Settings())  # ty: ignore[missing-argument]
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"[1/4] {SMOKE_DB_NAME} drop/create + 001 마이그레이션 적용")
    try:
        smoke_dsn = await recreate_database(SMOKE_DB_NAME, MIGRATIONS_DIR)
    except (OSError, asyncpg.PostgresError) as exc:
        print(
            f"ERROR: 스모크 DB 준비 실패 — {type(exc).__name__}: {exc}\n"
            "DB가 기동 중인지 확인하라 — 기본은 homebrew :5432"
            " (brew services list | grep postgresql@17)."
            " 폴백은 podman :5433 (scripts/dev_db.sh status).",
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
        await _save_user_turn(db_pool, session_id, turn1_answer)
        job1 = await _claim(db_pool)
        await process_analysis(db_pool, claude, job1)
        job1_row = await _job_row(db_pool, job1.id)
        _report("job1", job1_row, claude, 0)
        patterns_after_1 = await _patterns(db_pool, user_id)

        print(f"[3/4] 발화 2 저장 → claim → process_analysis (실제 Claude): {turn2_answer!r}")
        await _save_user_turn(db_pool, session_id, turn2_answer)
        job2 = await _claim(db_pool)
        await process_analysis(db_pool, claude, job2)
        job2_row = await _job_row(db_pool, job2.id)
        _report("job2", job2_row, claude, 1)

        patterns = await _patterns(db_pool, user_id)
        occurrences = await _occurrences(db_pool, session_id)
        pattern = patterns[0] if len(patterns) == 1 else None
        # 학습 코치 슬라이스 1(006)의 산출물. 이 단정이 없으면 저장이 깨져도 PASS를 찍는다.
        contexts = [row["suggested_contexts"] for row in occurrences]
        async with db_pool.acquire() as conn:
            attempt_rows = await conn.fetch(
                "select pa.outcome from pattern_attempts pa "
                "  join utterances u on u.id = pa.utterance_id "
                " where u.session_id = $1",
                session_id,
            )
            review_rows = await conn.fetch(
                "select rt.review_stage, rt.status from review_tasks rt "
                "  join error_patterns p on p.id = rt.pattern_id "
                " where p.user_id = $1",
                user_id,
            )
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
            # ── 학습 코치 슬라이스 1 (006) ─────────────────────────────────────
            # L2의 목적은 "**실물 모델이** 새 필드를 내는가"다. 사람이 DB를 열어 보는 것으로
            # 대신하면 다음 회차에 그 저장이 깨져도 이 스크립트는 PASS를 찍는다.
            Check(
                "실물 모델이 suggested_contexts를 냈다 (occurrence마다)",
                bool(contexts) and all(item is not None for item in contexts),
                f"실제 {[('null' if c is None else json.loads(c)) for c in contexts]!r} — "
                "null이면 컬럼·저장 경로가 아니라 **프롬프트**를 본다",
            ),
            Check(
                "next_review_at이 채워졌다 (복습 목록이 0행을 벗어난다)",
                pattern is not None and pattern["next_review_at"] is not None,
                f"실제 next_review_at={pattern['next_review_at'] if pattern else 'N/A'}",
            ),
            Check(
                "review_tasks가 패턴당 0~1행이다",
                len(review_rows) <= len(patterns),
                f"실제 {len(review_rows)}행 / 패턴 {len(patterns)}개: "
                f"{[(r['review_stage'], r['status']) for r in review_rows]!r}",
            ),
            # 재시도 판정은 **모델 판단**이라 0건일 수 있다 — 그것을 실패로 만들지 않는다.
            # 값역만 본다: 규격 밖 outcome이 저장됐다면 경계 검증이 뚫린 것이다.
            Check(
                "pattern_attempts의 outcome이 전부 값역 안이다",
                all(row["outcome"] in ATTEMPT_OUTCOMES for row in attempt_rows),
                f"실제 {[r['outcome'] for r in attempt_rows]!r} (값역 {list(ATTEMPT_OUTCOMES)})",
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
            stored = row["suggested_contexts"]
            print(
                f"occurrence[{index}]: original_span={row['original_span']!r} "
                f"correction={row['correction']!r} explanation={row['explanation']!r} "
                f"severity={row['severity']!r} confidence={row['confidence']} "
                f"suggested_contexts={'null' if stored is None else json.loads(stored)!r}"
            )
        print(f"pattern_attempts: {[r['outcome'] for r in attempt_rows]!r}")
        print(
            f"review_tasks: {[(r['review_stage'], r['status']) for r in review_rows]!r} · "
            f"next_review_at={pattern['next_review_at'] if pattern else 'N/A'}"
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
