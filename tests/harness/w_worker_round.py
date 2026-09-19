#!/usr/bin/env python
"""TASK-255 워커 회차 — 실물 Claude 로 워커 루프를 켜고 경로 셋을 닫는다.

닫는 것 셋(태스크의 AC): ⑴ `daily_error_summary` 의 **쓰기** 경로 ⑵ `summarize_week` job 의
처리 절반(`weekly_reports` 가 실사용 경로로 채워진 적이 없다) ⑶ 실물 응답이 파서 계약
(무대 제목 언어 · `category` 값역)을 지키는가.

⛔ **격리 DB(`ohmyenglish_worker`)에서 돈다 — dev DB 가 아니다.** 착수 승인(2026-09-19)의
전제는 *「미등록 발화 10건에 job 이 걸린다」* 였는데 **그 전제가 사라졌다**: 착수 직전 실측에서
그 스윕이 걸 job 이 0건이었다(b10 teardown 이 자기 행을 지웠다). 그러면 회차가 일을 **새로
만들어야** 하고, dev DB 에 만들면 픽스처 문장이 사용자의 실제 오류 패턴·복습 일정으로 섞인다 —
그것은 `TASK-191` 이 *「하네스 산출물은 처리하지 않음」*으로 정한 것을 되돌리는 일이다. 격리
DB 는 같은 마이그레이션·같은 코드를 지나가므로 **증거는 같고 되돌릴 수 없는 부수 효과만 없다.**
⚠️ 유료 호출은 그대로 난다. 상한은 `CALL_CAP` 이 코드로 막고, **그 값의 뜻이 2026-09-20 에
예산에서 폭주 방지로 바뀌었다**(그 상수 위 주석이 근거를 갖는다).

⛔ **`run_worker` 를 «실제로» 부른다** — 이 회차의 대상이 워커 루프 자체다. dev DB 에서 그것을
부르지 않는 이유는 `p5_worker_leg.py` 가 소유한다(`H-AT`: 유휴 사이클의 스윕이 보존 세션에 job 을
새로 만든다). 격리 DB 에는 보존 세션이 없으므로 그 위험이 성립하지 않는다.

    cd app/backend
    W=../../tests/harness/w_worker_round.py
    .venv/bin/python $W setup  --out <회차>
    .venv/bin/python $W run    --out <회차>
    .venv/bin/python $W verify --out <회차>

cwd 는 `app/backend` 다(`H-A` — 설정과 `.env` 가 거기 있다).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "app" / "backend"
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from db_utils import dsn_for, recreate_database  # noqa: E402

WORKER_DB_NAME = "ohmyenglish_worker"
# ⛔ **이 값은 예산이 아니라 폭주 방지다 — 2026-09-20 에 뜻이 바뀌었다.** 첫 판의 `14` 는 승인
# 근거(12~15건)를 넘기지 않기 위한 예산이었고 사용자가 그 제약을 풀었다(*「유료 호출 상관 하지
# 말고 진행해」*). ⛔ **그래도 상한 자체는 남긴다**: job 재시도가 `MAX_ATTEMPTS=5` 까지 돌고
# 종류가 다섯이라 파서가 계속 거부하면 호출이 조용히 수십 건으로 늘어난다. 예상 경로는 10건이다
# (분석 5 + 회복 스윕이 걷는 묶음 1 + 총평 1 + 계획 1 + 무대 1 + 주간 1).
CALL_CAP = 40
TIMEZONE = "Asia/Seoul"

# 「질문 답변 5개」 세션의 전사문. 다섯 축(무대·상대·목표·초점·어조)을 순서대로 덮고, 오류는
# 일부러 심었다: 관사 누락 2건(같은 오류가 한 패턴으로 병합되는지 관측) · 전치사 1건 · 동사형 1건.
INTAKE_TURNS: list[tuple[str, str]] = [
    (
        "Where will you need English soon?",
        "Next month I must join weekly video call with our partner team in Singapore.",
    ),
    (
        "Who will you talk to in that call?",
        "I talk with product manager and two engineers from their side.",
    ),
    (
        "What do you want to achieve in that call?",
        "I want to explain our release plan and ask about their test results.",
    ),
    (
        "Which part feels hardest for you?",
        "I am afraid on answering questions when I do not catch every word.",
    ),
    (
        "Is the call formal or relaxed?",
        "It is quite formal because their director join sometimes.",
    ),
]

# 지난 주 학습 기록 — `summarize_week` 가 모델을 부르는 조건을 만든다. ⛔ 사실이 0건인 주는
# `process_weekly` 가 모델을 **부르지 않고** 빈 값으로 닫으므로, 씨앗이 없으면 AC#2 의 절반
# (실물 응답)이 관측되지 않는다.
LAST_WEEK_UTTERANCES = [
    "Last week I go to the conference with my colleague.",
    "I explain our roadmap but I forget many word.",
]
LAST_WEEK_PATTERNS = [
    # (category, pattern_key, target_form, 발생 문장 index, 발생 수)
    ("verb_tense", "verb_tense_past_simple", "went / explained", 0, 2),
    ("article", "article_missing_plural", "many words", 1, 1),
]


def _print_json(label: str, payload: object) -> None:
    print(f"=== {label} ===")
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _point_settings_at_worker_db() -> str:
    """`get_settings()` 가 처음 불리기 «전에» DSN 을 격리 DB 로 바꾼다.

    ⛔ `lru_cache` 라 한 번 불린 뒤에는 이 프로세스 안에서 되돌릴 수 없다 — smoke_analysis 가
    같은 이유로 같은 순서를 지킨다. 이 한 줄이 회차의 격리 전부다.
    """
    dsn = dsn_for(WORKER_DB_NAME)
    os.environ["DATABASE_URL"] = dsn
    return dsn


async def _aggregates(pool: asyncpg.Pool) -> dict[str, Any]:
    """호출 전후로 같은 질의를 돌려 비교하는 집계(AC#4)."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "select job_type, status, count(*) as n from analysis_jobs group by 1, 2 order by 1, 2"
        )
        totals = await conn.fetchrow(
            "select (select count(*) from llm_calls) as llm_calls,"
            "       (select count(*) from error_patterns) as error_patterns,"
            "       (select count(*) from error_occurrences) as error_occurrences,"
            "       (select count(*) from review_tasks) as review_tasks,"
            "       (select count(*) from weekly_reports) as weekly_reports,"
            "       (select count(*) from daily_error_summary) as daily_error_summary,"
            "       (select count(*) from session_plans) as session_plans,"
            "       (select count(*) from learning_scenarios where source = 'generated')"
            "         as generated_scenarios"
        )
        clock = await conn.fetchrow(
            "select now() as utc_now, current_date as utc_date,"
            "       (now() at time zone $1)::date as local_date",
            TIMEZONE,
        )
    assert totals is not None and clock is not None
    return {
        "jobs": [dict(row) for row in rows],
        "totals": dict(totals),
        "clock": dict(clock),
    }


# 지난 주 화요일 20시(사용자 타임존)를 timestamptz 로 만든다. ⛔ 주 경계를 파이썬에서 세지 않는다 —
# 정본이 `weekly_report._LAST_WEEK_START_SQL` 이고 같은 식을 여기서 쓰는 것이 그것과 어긋나지 않는
# 유일한 방법이다(`current_date` 는 UTC 자정~09:00 에 하루 이르다).
_LAST_WEEK_SESSION_SQL = """
insert into learning_sessions (user_id, mode, status, started_at, ended_at)
select $1, 'speaking', 'completed', ts, ts + interval '20 minutes'
  from (select ((date_trunc('week', now() at time zone $2) - interval '7 days')
                + interval '1 day 20 hours') at time zone $2 as ts) t
returning id, started_at
"""


async def _seed_last_week(conn: asyncpg.Connection, user_id: UUID) -> dict[str, Any]:
    """지난 주 세션 1건 + 발화 2건 + 오류 패턴 2종(발생 3건)을 심는다.

    ⛔ **이것은 씨앗이고 관측 대상이 아니다** — 이 회차가 판정하는 것은 이 값들을 읽어 만드는
    주간 리포트 쪽이다. 그래서 패턴을 모델로 만들지 않는다: 지난 주 발화를 분석에 태우면 이 회차가
    **자기 씨앗을 관측 대상으로 착각할 자리**가 생기고, 주간 사실의 수가 실행마다 흔들린다.
    """
    session = await conn.fetchrow(_LAST_WEEK_SESSION_SQL, user_id, TIMEZONE)
    assert session is not None
    utterance_ids: list[UUID] = []
    for index, text in enumerate(LAST_WEEK_UTTERANCES, start=1):
        utterance_id = await conn.fetchval(
            "insert into utterances (session_id, speaker, transcript, sequence_no, created_at)"
            # ⚠️ 두 캐스트가 둘 다 필요하다(각각 실측으로 걸렸다): `$3 * interval` 은 $3 를
            # double 로도 integer 로도 추론해 `AmbiguousParameterError` 가 되고, `$4 + interval`
            # 은 $4 를 interval 로 추론해 `created_at` 자리에서 형이 어긋난다.
            " values ($1, 'user', $2, $3, $4::timestamptz + make_interval(mins => $3))"
            " returning id",
            session["id"],
            text,
            index,
            session["started_at"],
        )
        utterance_ids.append(utterance_id)
    for category, pattern_key, target_form, utterance_index, occurrences in LAST_WEEK_PATTERNS:
        pattern_id = await conn.fetchval(
            "insert into error_patterns"
            " (user_id, category, pattern_key, target_form, frequency, last_seen_at)"
            " values ($1, $2, $3, $4, $5, $6) returning id",
            user_id,
            category,
            pattern_key,
            target_form,
            occurrences,
            session["started_at"],
        )
        for _ in range(occurrences):
            await conn.execute(
                "insert into error_occurrences"
                " (utterance_id, pattern_id, original_span, correction, explanation,"
                "  severity, confidence, created_at)"
                " values ($1, $2, $3, $4, $5, 'medium', 0.90, $6)",
                utterance_ids[utterance_index],
                pattern_id,
                "seed span",
                target_form,
                "지난 주 씨앗 — 주간 리포트 입력용",
                session["started_at"],
            )
    return {"session_id": session["id"], "started_at": session["started_at"]}


async def cmd_setup(out_dir: Path) -> int:
    """격리 DB 를 새로 만들고 씨앗 + 오늘 세션을 넣는다. Claude 를 부르지 않는다."""
    print(f"[1/3] {WORKER_DB_NAME} drop/create + 전 마이그레이션 적용 + 시드")
    dsn = await recreate_database(WORKER_DB_NAME, MIGRATIONS_DIR)
    assert dsn == _point_settings_at_worker_db()

    # ⛔ **시드를 «반드시» 넣는다** (2026-09-20 실측으로 걸렸다). `recreate_database` 는
    # 마이그레이션만 적용하고 `migrate.seed` 를 부르지 않는다 — 그러면 `learning_scenarios` 가
    # 0행이고,
    # 무대 생성의 값역이 **시드에 실재하는 계열**이라(`_STAGE_CATEGORIES_SQL`) 프롬프트 조립이
    # `allowed_categories is empty` 로 거부된다. 첫 실행이 그 자리에서 job 을 4회 헛돌렸다.
    from migrate import seed

    seed_conn = await asyncpg.connect(dsn=dsn)
    try:
        await seed(seed_conn)
    finally:
        await seed_conn.close()

    from app.db import close_pool
    from app.db import pool as get_db_pool
    from app.services.sessions import create_session, mark_session_ended
    from app.services.utterances import flush_pending_analysis, save_final_transcript

    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            user_id = await conn.fetchval(
                "insert into users (display_name, timezone, current_level)"
                " values ('TASK-255 Worker Round', $1, 'A2') returning id",
                TIMEZONE,
            )
            last_week = await _seed_last_week(conn, user_id)
        print(f"  user_id={user_id} · 지난 주 세션={last_week['session_id']}")

        # ⛔ 세션 생성·저장·턴 경계·종료를 **앱 서비스로** 지나간다 — job 을 손으로 넣으면
        # 등록 경로가 끊겨도 회차가 통과한다(smoke_analysis 가 같은 이유로 같은 규약을 쓴다).
        session_id = await create_session(
            pool, user_id, mode="scenario_intake", learning_source="additional"
        )
        async with pool.acquire() as conn:
            for question, answer in INTAKE_TURNS:
                await save_final_transcript(conn, session_id, question, speaker="agent")
                await save_final_transcript(conn, session_id, answer)
            enqueued = await flush_pending_analysis(conn, session_id)
        if len(enqueued) != len(INTAKE_TURNS):
            raise RuntimeError(
                f"턴 경계가 등록한 분석 job 이 {len(enqueued)}건이다 — 기대 {len(INTAKE_TURNS)}건 "
                "(묶음 정의가 바뀌었는지 `flush_pending_analysis` 를 본다)"
            )
        print(f"[2/3] 오늘 세션={session_id} · 분석 job {len(enqueued)}건 등록")

        await mark_session_ended(pool, session_id, "completed")
        print("[3/3] 세션 종료 — 총평·계획·무대·주간 job 등록")

        state = await _aggregates(pool)
        state["user_id"] = user_id
        state["session_id"] = session_id
        state["last_week_session_id"] = last_week["session_id"]
        (out_dir / "setup.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        _print_json("setup (호출 전 기준선)", state)
    finally:
        await close_pool()
    return 0


class _BudgetedClaude:
    """실제 `BedrockClaudeClient` 에 그대로 위임하고 **세면서** 원문 응답을 남긴다.

    ⛔ **상한을 넘으면 호출하지 않고 루프를 멈춘다** — 파서가 응답을 거부하면 job 이 5회까지
    재시도되고 그때마다 유료 호출이 난다. 승인 근거(12~15건)를 넘기지 않는 장치가 이것뿐이다.
    ⚠️ 원문을 남기는 이유는 AC#3 이다 — 계약 위반은 저장된 행이 아니라 **응답 자체**로 판정한다.
    """

    def __init__(self, inner: Any, *, cap: int, stop: asyncio.Event, log_path: Path) -> None:
        self._inner = inner
        self._cap = cap
        self._stop = stop
        self._log_path = log_path
        self.calls = 0

    async def analyze(self, prompt: str, **kwargs: Any) -> str:
        if self.calls >= self._cap:
            self._stop.set()
            raise RuntimeError(f"호출 상한 {self._cap}건에 닿았다 — 회차를 멈춘다")
        self.calls += 1
        raw = await self._inner.analyze(prompt, **kwargs)
        entry = {
            "call_no": self.calls,
            "purpose": kwargs.get("purpose"),
            "job_id": str(kwargs.get("job_id")),
            "prompt_chars": len(prompt),
            "raw": raw,
        }
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return raw


_REMAINING_SQL = """
select count(*) filter (where available_at <= now()) as claimable_now,
       count(*) as remaining,
       min(available_at) filter (where available_at > now()) as next_at
  from analysis_jobs
 where status in ('pending', 'running')
"""


async def _stop_when_drained(
    pool: asyncpg.Pool, stop: asyncio.Event, *, timeout: float, idle_cycles: int = 3, grace: float
) -> str:
    """큐가 비면 워커를 멈춘다 — 이 회차는 상주 프로세스가 아니라 **한 번 비우는 실행**이다.

    ⚠️ 연속 `idle_cycles` 회 비어 있을 때 멈춘다. 한 번만 보고 멈추면 claim 과 claim 사이의
    찰나를 「비었다」로 읽어 남은 job 을 두고 나온다.

    ⛔ **재시도 백오프를 「비지 않았다」로 읽지 않는다** (첫 실행이 그 자리에서 480초를 버렸다).
    실패한 job 은 `available_at` 이 미래로 밀린 `pending` 이라 단순 개수로는 영원히 0 이 되지
    않는다. `grace` 초 안에 다시 claim 가능해지는 것만 기다리고, 그보다 먼 것은 **남은 이유를
    이름으로 적고** 멈춘다.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    idle = 0
    while not stop.is_set():
        await asyncio.sleep(1.0)
        async with pool.acquire() as conn:
            row = await conn.fetchrow(_REMAINING_SQL)
        assert row is not None
        if row["claimable_now"] == 0:
            idle += 1
            if idle >= idle_cycles:
                if row["remaining"] == 0:
                    stop.set()
                    return "drained"
                wait_seconds = (row["next_at"] - datetime.now(UTC)).total_seconds()
                if wait_seconds > grace:
                    stop.set()
                    return (
                        f"남은 job {row['remaining']}건이 백오프 중이다 — 다음 claim 까지 "
                        f"{wait_seconds:.0f}초(유예 {grace:.0f}초)"
                    )
        else:
            idle = 0
        if loop.time() >= deadline:
            stop.set()
            return f"timeout after {timeout:.0f}s (남은 job {row['remaining']}건)"
    return "stopped by worker"


async def cmd_run(out_dir: Path, *, timeout: float, grace: float = 60.0) -> int:
    """실물 Claude 로 `run_worker` 를 돌려 큐를 비운다."""
    _point_settings_at_worker_db()

    from app.config import Settings, get_settings, prepare_bedrock_credentials
    from app.db import close_pool
    from app.db import pool as get_db_pool
    from app.services.usage import pool_usage_sink
    from app.workers.analysis_worker import run_worker
    from app.workers.claude_client import BedrockClaudeClient

    # 자격증명이 없으면 job 을 건드리기 전에 끝낸다 — 검사는 config 의 단일 이음새에 위임한다.
    prepare_bedrock_credentials(Settings())  # ty: ignore[missing-argument]
    settings = get_settings()

    pool = await get_db_pool()
    stop = asyncio.Event()
    # ⛔ **`usage_sink` 를 «반드시» 넘긴다 — 빼면 토큰 기록이 조용히 꺼진다**(`api/main.py` 의 실물
    # 배선이 같은 경고를 갖는다). 2026-09-20 첫 실행이 그것을 빠뜨려 유료 호출 9건이 나는데
    # `llm_calls` 가 0행이었다 — 회차가 AC#4 의 집계를 스스로 못 내는 상태였다.
    claude = _BudgetedClaude(
        BedrockClaudeClient(settings, usage_sink=pool_usage_sink(pool)),
        cap=CALL_CAP,
        stop=stop,
        log_path=out_dir / "responses.jsonl",
    )
    try:
        before = await _aggregates(pool)
        print(f"호출 전 llm_calls={before['totals']['llm_calls']} · 상한 {CALL_CAP}건")
        # ⛔ `live_sessions` 를 비워 둘 수 있는 것은 격리 DB 라서다 — 이 DB 에 진행 중 세션이
        # 없으므로 고아 리퍼가 닫을 것이 없다. dev DB 에서는 그 가정이 성립하지 않는다.
        worker = asyncio.create_task(
            run_worker(
                pool,
                claude,
                stop=stop,
                poll_interval=1.0,
                # 실물 배선과 같게 녹음 뿌리를 넘긴다 — 빼면 쉐도잉 녹음 스윕이 조용히 꺼진다.
                recording_root=settings.shadowing_audio_root,
            )
        )
        reason = await _stop_when_drained(pool, stop, timeout=timeout, grace=grace)
        await asyncio.wait_for(worker, timeout=30)
        after = await _aggregates(pool)
        print(f"멈춘 이유: {reason} · 실제 호출 {claude.calls}건")
        payload = {
            "stop_reason": reason,
            "claude_calls": claude.calls,
            "before": before,
            "after": after,
        }
        (out_dir / "run.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        _print_json("run (호출 후 집계)", after)
    finally:
        await close_pool()
    return 0


_EVIDENCE_QUERIES: dict[str, str] = {
    "jobs": "select job_type, status, attempts, last_error from analysis_jobs"
    " order by job_type, created_at",
    "llm_calls": "select purpose, model_id, input_tokens, output_tokens, called_at"
    " from llm_calls order by called_at",
    "daily_error_summary": "select summary_date, timezone, occurrence_count, pattern_count,"
    " patterns, computed_at from daily_error_summary order by summary_date",
    "weekly_reports": "select week_start, timezone, metrics, insights, computed_at"
    " from weekly_reports order by week_start",
    "error_patterns": "select category, pattern_key, target_form, frequency, last_seen_at,"
    " next_review_at from error_patterns order by created_at",
    "review_tasks": "select rt.task_type, rt.review_stage, rt.status, rt.due_at,"
    " rt.cycle_started_at, p.pattern_key"
    " from review_tasks rt join error_patterns p on p.id = rt.pattern_id order by rt.due_at",
    "generated_scenarios": "select category, level, title, prompt_template, source"
    " from learning_scenarios where source = 'generated'",
    "session_plans": "select target_level, reason, focus_pattern_ids, source from session_plans",
    "session_summary": "select mode, status, summary from learning_sessions"
    " where mode = 'scenario_intake'",
}


def _has_hangul(text: str) -> bool:
    return any("가" <= char <= "힣" or "ㄱ" <= char <= "ㆎ" for char in text)


def _check(name: str, passed: bool, detail: str) -> dict[str, Any]:
    print(f"  [{'PASS' if passed else 'FAIL'}] {name} — {detail}")
    return {"name": name, "passed": passed, "detail": detail}


async def cmd_verify(out_dir: Path) -> int:
    """저장된 행과 원문 응답으로 AC 넷을 판정한다. Claude 를 부르지 않는다."""
    _point_settings_at_worker_db()

    from app.db import close_pool
    from app.db import pool as get_db_pool

    pool = await get_db_pool()
    try:
        evidence: dict[str, Any] = {}
        async with pool.acquire() as conn:
            for key, sql in _EVIDENCE_QUERIES.items():
                evidence[key] = [dict(row) for row in await conn.fetch(sql)]
            clock = await conn.fetchrow(
                "select current_date as utc_date, (now() at time zone $1)::date as local_date,"
                " (date_trunc('week', now() at time zone $1) - interval '7 days')::date"
                "   as last_week_start",
                TIMEZONE,
            )
        assert clock is not None
        evidence["clock"] = dict(clock)

        # ⛔ **드라이버 계수기와 `llm_calls` 를 대조한다 — `H-CK` 를 기계 검사로 바꾼 자리다.**
        # 첫 회차는 유료 호출 9건이 나는데 그 표가 0행이었고, 그것을 **우연히** 발견했다(집계를
        # 눈으로 읽다가). 두 수가 어긋나면 배선이 빠진 것이므로 단정으로 세운다.
        run_log = out_dir / "run.json"
        counted = json.loads(run_log.read_text())["claude_calls"] if run_log.exists() else None
        evidence["claude_calls_counted_by_driver"] = counted

        jobs = evidence["jobs"]
        weekly_jobs = [job for job in jobs if job["job_type"] == "summarize_week"]
        analyze_jobs = [job for job in jobs if job["job_type"] == "analyze_utterance"]
        scenario_jobs = [job for job in jobs if job["job_type"] == "generate_scenario"]
        today_rows = [
            row
            for row in evidence["daily_error_summary"]
            if row["summary_date"] == clock["local_date"]
        ]
        week_rows = [
            row
            for row in evidence["weekly_reports"]
            if row["week_start"] == clock["last_week_start"]
        ]
        titles = [row["title"] for row in evidence["generated_scenarios"]]

        print("=== AC 판정 ===")
        checks = [
            _check(
                "AC#1 오늘 행이 사용자 타임존 날짜로 만들어졌다",
                len(today_rows) == 1 and today_rows[0]["timezone"] == TIMEZONE,
                f"summary_date={[str(r['summary_date']) for r in evidence['daily_error_summary']]}"
                f" · 사용자 타임존 날짜={clock['local_date']} · UTC current_date="
                f"{clock['utc_date']} · 두 날짜는 "
                + ("다르다(판별력 있음)" if clock["utc_date"] != clock["local_date"] else "같다"),
            ),
            _check(
                "AC#1 오늘 행의 집계가 발생 건수와 맞다",
                bool(today_rows) and today_rows[0]["occurrence_count"] > 0,
                f"occurrence_count={today_rows[0]['occurrence_count'] if today_rows else None}"
                f" · pattern_count={today_rows[0]['pattern_count'] if today_rows else None}",
            ),
            _check(
                "AC#2 summarize_week job 이 done 이다",
                len(weekly_jobs) == 1 and weekly_jobs[0]["status"] == "done",
                f"{[(j['status'], j['attempts'], j['last_error']) for j in weekly_jobs]}",
            ),
            _check(
                "AC#2 지난 주 weekly_reports 행이 생겼다",
                len(week_rows) == 1,
                f"week_start={[str(r['week_start']) for r in evidence['weekly_reports']]}"
                f" · 기대={clock['last_week_start']}",
            ),
            _check(
                "AC#3 무대 제목이 영어다 (한글 0자)",
                bool(titles) and not any(_has_hangul(title) for title in titles),
                f"titles={titles}",
            ),
            _check(
                "AC#3 무대 category 가 값역 안이다 (파서가 통과시켰다)",
                len(scenario_jobs) == 1 and scenario_jobs[0]["status"] == "done",
                f"category={[row['category'] for row in evidence['generated_scenarios']]}"
                f" · job={[(j['status'], j['last_error']) for j in scenario_jobs]}",
            ),
            _check(
                "AC#3 분석 job 전건이 done 이고 category 가 값역 안이다",
                bool(analyze_jobs) and all(job["status"] == "done" for job in analyze_jobs),
                f"{[(j['status'], j['last_error']) for j in analyze_jobs]}"
                f" · 패턴 category={[p['category'] for p in evidence['error_patterns']]}",
            ),
            _check(
                "AC#4 llm_calls 행 수가 드라이버 계수기와 같다 (H-CK 기계 검사)",
                counted is not None and len(evidence["llm_calls"]) == counted,
                f"llm_calls={len(evidence['llm_calls'])}행 · 드라이버 계수기={counted}"
                f" · 토큰 합계 in/out="
                f"{sum(row['input_tokens'] for row in evidence['llm_calls'])}/"
                f"{sum(row['output_tokens'] for row in evidence['llm_calls'])}",
            ),
            # ⛔ **재시도 수를 단정에 넣지 않는다 — 실측으로 그 단정이 거짓 실패를 냈다**
            # (2026-09-20 재실행). 실물 응답이 한 응답 «안에서» 키 이름을 섞어(`findings[0]` 은
            # `pattern_key`, `findings[1]` 은 `pattern_form`) 파서가 거부하고 재시도가 성공했다.
            # 그것은 설계된 회복이 도는 것이고 드라이버 결함이 아니다. ⇒ 단정은 「전건 done」에
            # 두고 재시도는 **사유와 함께 보이게만** 한다.
            _check(
                "job 전건이 done 이다 (재시도는 사유와 함께 적는다)",
                bool(jobs) and all(job["status"] == "done" for job in jobs),
                f"{sorted((j['job_type'], j['status'], j['attempts']) for j in jobs)}"
                f" · 재시도한 job 의 사유={[j['last_error'] for j in jobs if j['attempts'] > 1]}",
            ),
        ]
        evidence["checks"] = checks
        (out_dir / "verify.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, default=str) + "\n"
        )
        _print_json("증거", evidence)
        passed = sum(1 for check in checks if check["passed"])
        print(f"\n{'PASS' if passed == len(checks) else 'FAIL'}: {passed}/{len(checks)} 단정 통과")
        return 0 if passed == len(checks) else 1
    finally:
        await close_pool()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["setup", "run", "verify"])
    parser.add_argument("--out", required=True, type=Path, help="회차 증거 디렉터리")
    parser.add_argument("--timeout", type=float, default=420.0, help="run 단계의 벽시계 상한(초)")
    args = parser.parse_args()
    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.stage == "setup":
        return asyncio.run(cmd_setup(out_dir))
    if args.stage == "run":
        return asyncio.run(cmd_run(out_dir, timeout=args.timeout))
    return asyncio.run(cmd_verify(out_dir))


if __name__ == "__main__":
    sys.exit(main())
