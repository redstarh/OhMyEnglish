#!/usr/bin/env python3
"""P8 — `pronunciation_intonation` 주입 내성. 저장·조회 경로가 카테고리를 차별하는지 본다.

⛔ **`inject_errors.py`로는 이 시나리오를 돌릴 수 없다.** 그 스크립트는 문장을 실제 분석
워커에 흘리는데, 워커 프롬프트는 이 카테고리를 **금지**한다(`analysis.py`
`UNJUDGEABLE_CATEGORY`). 그래서 아무리 발음이 틀린 문장을 넣어도 이 카테고리의 패턴이
생기지 않는다 — `scenarios-P-pronunciation.md` §4 P8이 지목한 도구가 그 단정을 만들 수 없다.
**이 스크립트가 대신 제품 writer를 직접 부른다**(`services/pronunciation.record_attempt`) —
그것이 이 카테고리를 만드는 앱의 유일한 경로다.

**두 writer를 한 회차에서 부딪힌다** — 그것이 P8의 핵심이다:

* 발음 경로는 `frequency`를 `pronunciation_attempts` **시도 수**에서 센다
  (`pronunciation._RECOUNT_PATTERN_FROM_ATTEMPTS_SQL`).
* 문법 경로는 같은 컬럼을 `error_occurrences` **행 수**에서 센다
  (`analysis._RECOUNT_PATTERN_SQL`).

`--cross-path`는 발음 패턴에 `error_occurrences` 행을 하나 넣고 **문법 재계산을 그대로
불러** 값이 덮이는지 잰다. 그 충돌이 실제로 도달 가능한지는 별개 문제이고 회차 기록이 갖는다.

⚠️ **기존 소리를 건드리지 않는다.** 기본 `--sound`는 `th_as_s`이고, 개발 DB에 이미 있는
`an_as_a`는 다른 태스크(`TASK-81` AC#4)의 재료라 기본값으로 고르지 않는다.

실행:
    cd app/backend && .venv/bin/python ../../tests/harness/p8_inject_pronunciation.py \
        inject --out <회차>/p8-inject.json --cross-path
    cd app/backend && .venv/bin/python ../../tests/harness/p8_inject_pronunciation.py \
        teardown --in <회차>/p8-inject.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "app" / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.api.ws import FIXED_USER_ID  # noqa: E402
from app.db import close_pool  # noqa: E402
from app.db import pool as get_db_pool  # noqa: E402
from app.services.analysis import _RECOUNT_PATTERN_SQL  # noqa: E402
from app.services.pronunciation import record_attempt  # noqa: E402
from app.services.sessions import create_session, mark_session_ended  # noqa: E402
from app.services.utterances import save_final_transcript  # noqa: E402

# 학습자가 말한 것으로 둘 문장. 문법은 옳다 — 그래야 관측된 것이 전부 발음 경로에서 왔다고
# 단정할 수 있다(`scenarios-P` §3의 같은 규약).
UTTERANCE = "I think the report is ready for the meeting."

# ⚠️ **`target_form`은 소리 키가 아니라 코치가 «시범한 문장»이다.** 화면이 그 값을
# `시범 문장` 자리에 그대로 렌더하므로(`results/[sessionId]/page.tsx`) 여기에 `th_as_s` 같은
# 기계 키를 넣으면 **화면에 기계 키가 뜨고 그것을 앱 결함으로 오독하게 된다** — 첫 회차에서
# 실제로 그렇게 관측했다. 제품 경로(`api/ws.py`의 tool 처리)가 넣는 것은 문장이다.
# 소리 키는 `target_sound` 인자가 따로 나른다.
TARGET_FORM = "I think the report is ready for the meeting."

# `--cross-path`가 넣는 문법 occurrence. **내용은 관측 대상이 아니다** — 행이 하나 있다는
# 것만으로 문법 재계산이 `frequency`를 1로 덮는지가 관측 대상이다.
CROSS_OCCURRENCE = {
    "original_span": "the report",
    "correction": "the report",
    "explanation": "P8 하네스가 넣은 교차 경로 행이다. 학습자 산출물이 아니다.",
    "severity": "low",
    "confidence": 0.5,
}

_PATTERN_SQL = """
select id, pattern_key, category, target_form, frequency, last_seen_at,
       next_review_at, mastery_score
  from error_patterns
 where user_id = $1 and pattern_key = $2
"""

_ATTEMPTS_SQL = """
select id, attempt_seq, target_form, target_sound, outcome, signal_source,
       pattern_id, resolved_at
  from pronunciation_attempts
 where session_id = $1
 order by attempt_seq
"""

_REVIEW_TASKS_SQL = """
select id, task_type, review_stage, status, due_at, completed_at, cycle_started_at
  from review_tasks
 where pattern_id = $1
 order by review_stage, created_at
"""

_OCCURRENCES_SQL = """
select count(*) from error_occurrences where pattern_id = $1
"""


def _plain(value: Any) -> Any:
    """asyncpg 레코드 값을 JSON으로 낼 수 있는 형태로 바꾼다."""
    if isinstance(value, UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "quantize"):  # Decimal
        return str(value)
    return value


def _show(label: str, pattern: dict[str, Any] | None) -> None:
    """`frequency`·`last_seen_at` 두 값만 한 줄로 낸다 — 이 회차의 판정이 그 둘에 걸린다."""
    if pattern is None:
        print(f"  {label}: 패턴 없음")
        return
    print(f"  {label}: frequency={pattern['frequency']} last_seen={pattern['last_seen_at']}")


async def _observe(conn: Any, session_id: UUID, pattern_key: str) -> dict[str, Any]:
    """이 회차가 만든 것 전부 — 패턴 · 시도 · 복습 과제 · occurrence 수."""
    pattern = await conn.fetchrow(_PATTERN_SQL, FIXED_USER_ID, pattern_key)
    attempts = await conn.fetch(_ATTEMPTS_SQL, session_id)
    out: dict[str, Any] = {
        "pattern": {k: _plain(v) for k, v in dict(pattern).items()} if pattern else None,
        "attempts": [{k: _plain(v) for k, v in dict(r).items()} for r in attempts],
    }
    if pattern is not None:
        tasks = await conn.fetch(_REVIEW_TASKS_SQL, pattern["id"])
        out["review_tasks"] = [{k: _plain(v) for k, v in dict(r).items()} for r in tasks]
        out["occurrences"] = await conn.fetchval(_OCCURRENCES_SQL, pattern["id"])
    return out


async def inject(sound: str, cross_path: bool) -> dict[str, Any]:
    pattern_key = f"pronunciation_{sound}"
    pool = await get_db_pool()
    try:
        session_id = await create_session(pool, FIXED_USER_ID)
        print(f"session_id = {session_id}")
        result: dict[str, Any] = {
            "session_id": str(session_id),
            "sound": sound,
            "pattern_key": pattern_key,
        }

        async with pool.acquire() as conn:
            utterance = await save_final_transcript(
                conn, session_id, UTTERANCE, utterance_type="learning"
            )
            result["utterance_id"] = str(utterance.id)
            print(f"  utterance #{utterance.sequence_no} 저장")

            # 규칙 10이 지시하는 두 호출을 그대로 낸다 — 시범 직후 `pending`, 재발화를 듣고 판정.
            await record_attempt(
                conn,
                session_id,
                target_form=TARGET_FORM,
                outcome="pending",
                target_sound=sound,
                utterance_id=utterance.id,
            )
            result["after_pending"] = await _observe(conn, session_id, pattern_key)
            print(f"  pending 후 패턴: {result['after_pending']['pattern']}")

            await record_attempt(
                conn,
                session_id,
                target_form=TARGET_FORM,
                outcome="incorrect",
                spoken_form="sink",
                target_sound=sound,
                utterance_id=utterance.id,
            )
            result["after_incorrect"] = await _observe(conn, session_id, pattern_key)
            print(f"  incorrect 후 패턴: {result['after_incorrect']['pattern']}")

            if cross_path:
                pattern = result["after_incorrect"]["pattern"]
                if pattern is None:
                    raise RuntimeError("패턴이 없어 교차 경로를 잴 수 없다")
                pattern_id = UUID(pattern["id"])
                occurrence_id = await conn.fetchval(
                    """
                    insert into error_occurrences
                        (utterance_id, pattern_id, original_span, correction, explanation,
                         severity, confidence)
                    values ($1, $2, $3, $4, $5, $6, $7)
                    returning id
                    """,
                    utterance.id,
                    pattern_id,
                    CROSS_OCCURRENCE["original_span"],
                    CROSS_OCCURRENCE["correction"],
                    CROSS_OCCURRENCE["explanation"],
                    CROSS_OCCURRENCE["severity"],
                    CROSS_OCCURRENCE["confidence"],
                )
                result["cross_occurrence_id"] = str(occurrence_id)
                result["after_occurrence_insert"] = await _observe(conn, session_id, pattern_key)

                # ⛔ 문법 경로의 재계산을 **그대로** 부른다 — 하네스가 SQL을 베끼면 제품이
                # 바뀔 때 이 관측이 조용히 낡는다.
                await conn.execute(_RECOUNT_PATTERN_SQL, pattern_id)
                result["after_grammar_recount"] = await _observe(conn, session_id, pattern_key)
                print(f"  문법 재계산 후 패턴: {result['after_grammar_recount']['pattern']}")

        await mark_session_ended(pool, session_id, "completed")
        return result
    finally:
        await close_pool()


async def collide(state: dict[str, Any]) -> dict[str, Any]:
    """두 writer의 **개수가 갈리는** 조건을 만든다 — 시도 2 대 occurrence 1.

    `inject --cross-path`만으로는 `frequency`가 우연히 양쪽 다 1이어서 **덮였는지 아닌지가
    구별되지 않는다.** 시도를 하나 더 넣어 발음 경로가 2로 세게 한 뒤 문법 재계산을 부르면,
    값이 1로 내려가는 것이 곧 「덮었다」의 증거다. ⛔ 이 판별력 없이 「충돌한다」를 적지 않는다.
    """
    session_id = UUID(state["session_id"])
    sound = state["sound"]
    pattern_key = state["pattern_key"]
    utterance_id = UUID(state["utterance_id"])
    pool = await get_db_pool()
    try:
        report: dict[str, Any] = {}
        async with pool.acquire() as conn:
            await record_attempt(
                conn,
                session_id,
                target_form=TARGET_FORM,
                outcome="incorrect",
                spoken_form="sinking",
                target_sound=sound,
                utterance_id=utterance_id,
            )
            report["after_second_attempt"] = await _observe(conn, session_id, pattern_key)
            pattern = report["after_second_attempt"]["pattern"]
            _show("시도 2건 후", pattern)

            await conn.execute(_RECOUNT_PATTERN_SQL, UUID(pattern["id"]))
            report["after_grammar_recount"] = await _observe(conn, session_id, pattern_key)
            _show("문법 재계산 후", report["after_grammar_recount"]["pattern"])
        return report
    finally:
        await close_pool()


async def teardown(state: dict[str, Any]) -> dict[str, Any]:
    """이 회차가 만든 것만 지운다 — ID를 명시해서만 지운다."""
    pool = await get_db_pool()
    try:
        session_id = UUID(state["session_id"])
        pattern_key = state["pattern_key"]
        report: dict[str, Any] = {"session_id": str(session_id)}
        async with pool.acquire() as conn:
            pattern = await conn.fetchrow(_PATTERN_SQL, FIXED_USER_ID, pattern_key)
            if pattern is not None:
                pattern_id = pattern["id"]
                report["review_tasks_deleted"] = await conn.fetchval(
                    "with d as (delete from review_tasks where pattern_id = $1 returning 1) "
                    "select count(*) from d",
                    pattern_id,
                )
                report["occurrences_deleted"] = await conn.fetchval(
                    "with d as (delete from error_occurrences where pattern_id = $1 returning 1) "
                    "select count(*) from d",
                    pattern_id,
                )
                report["attempts_unlinked"] = await conn.fetchval(
                    "with d as (update pronunciation_attempts set pattern_id = null "
                    "  where pattern_id = $1 returning 1) select count(*) from d",
                    pattern_id,
                )
                report["pattern_deleted"] = await conn.fetchval(
                    "with d as (delete from error_patterns where id = $1 returning 1) "
                    "select count(*) from d",
                    pattern_id,
                )
            report["attempts_deleted"] = await conn.fetchval(
                "with d as (delete from pronunciation_attempts where session_id = $1 returning 1) "
                "select count(*) from d",
                session_id,
            )
            report["session_deleted"] = await conn.fetchval(
                "with d as (delete from learning_sessions where id = $1 returning 1) "
                "select count(*) from d",
                session_id,
            )
            report["pattern_left"] = await conn.fetchval(
                "select count(*) from error_patterns where user_id = $1 and pattern_key = $2",
                FIXED_USER_ID,
                pattern_key,
            )
        return report
    finally:
        await close_pool()


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    inj = sub.add_parser("inject")
    inj.add_argument("--sound", default="th_as_s")
    inj.add_argument("--out", required=True)
    inj.add_argument("--cross-path", action="store_true")

    col = sub.add_parser("collide")
    col.add_argument("--in", dest="state", required=True)
    col.add_argument("--out", required=True)

    down = sub.add_parser("teardown")
    down.add_argument("--in", dest="state", required=True)

    args = ap.parse_args()

    if args.cmd == "inject":
        result = asyncio.run(inject(args.sound, args.cross_path))
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1))
        print(f"\nraw -> {args.out}")
        return 0

    if args.cmd == "collide":
        state = json.loads(Path(args.state).read_text())
        report = asyncio.run(collide(state))
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=1))
        print(f"\nraw -> {args.out}")
        return 0

    state = json.loads(Path(args.state).read_text())
    report = asyncio.run(teardown(state))
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
