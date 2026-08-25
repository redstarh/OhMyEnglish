#!/usr/bin/env python3
"""E계층 — 오류를 주입해 Agent의 학습 패턴 분석을 관측한다.

스텁 픽스처는 `article` 오류 하나만 만든다. 그래서 종단에서는
**R1("패턴 상위 2개만 반환")을 밟을 수 없다** — 패턴이 1개뿐이라 상한이 발동하지 않는다.
이 스크립트는 서로 다른 카테고리의 오류 문장을 앱 경로로 주입해 패턴을 여러 개 만든다.

앱 코드를 우회하지 않는다 — `create_session`과 `save_final_transcript`를 그대로 쓰므로
전사문 저장·job 등록·워커 분석·패턴 병합이 전부 실제 경로다. 스텁 어댑터만 건너뛴다
(스텁은 고정 3문장만 재생하므로 임의 문장을 넣을 수단이 없다).

실행:
    cd app/backend && .venv/bin/python ../../tests/harness/inject_errors.py --scenario E1
    cd app/backend && .venv/bin/python ../../tests/harness/inject_errors.py --scenario E3 --repeat
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "app" / "backend"
HARNESS = REPO_ROOT / ".harness"
sys.path.insert(0, str(BACKEND_DIR))

from app.db import close_pool  # noqa: E402
from app.db import pool as get_db_pool  # noqa: E402
from app.services.jobs import enqueue_analyze  # noqa: E402
from app.services.sessions import create_session, mark_session_ended  # noqa: E402
from app.services.utterances import save_final_transcript  # noqa: E402
from app.api.ws import FIXED_USER_ID  # noqa: E402

RUN_ID = (HARNESS / "run_id.txt").read_text().strip()

# 시나리오별 발화 종류. 기본은 분석 대상(user/learning)이고, E4만 명령 발화다 (W6).
UTTERANCE_TYPE = {"E4": "voice_command"}

# 서로 다른 카테고리를 노리는 문장. 실제 Claude가 무엇을 검출할지는 비결정적이므로
# "이 카테고리가 반드시 나온다"고 단정하지 않는다 — **여러 패턴이 생기는 것**과
# **그중 2개만 화면에 오는 것**이 이 시나리오의 단정이다.
INJECTIONS: dict[str, list[str]] = {
    # E1/E2: 카테고리 분산 — 패턴 3개 이상을 만들어 R1 상한을 밟는다
    "E1": [
        "Yesterday I go to the client meeting and present the project status.",
        "I will discuss about the deployment risk with my manager on next week.",
        "I know not why the migration failed during the last release.",
        "The team have finish the integration test already.",
        "I usually go to gym before the daily standup meeting.",
    ],
    # E3: 같은 오류 반복 — 학습 패턴 축적(frequency)이 실제로 쌓이는지
    "E3": [
        "I go to office by subway every morning.",
        "She go to gym after work on Tuesday.",
        "We go to airport by taxi tomorrow.",
    ],
    # E4: 음성 명령 발화 — 저장은 되지만 job이 생기지 않아야 한다 (W6)
    "E4": [
        "질문 다섯 개 더 해줘.",
        "오늘 학습 끝낼게.",
    ],
    # E5: 오류가 없는 문장 — occurrence 0건으로 정상 done, 화면은 "표시할 교정이 없습니다"
    "E5": [
        "I went to the gym after work yesterday.",
        "She usually takes the subway to the office.",
        "We need to finish the migration before the release.",
    ],
    # E6: 재분석 멱등 — 1문장 주입 후 같은 발화에 job을 다시 등록해 replace를 관측한다
    "E6": [
        "Yesterday I go to the office and present the quarterly plan.",
    ],
}


def psql(sql: str) -> str:
    out = subprocess.run(
        ["podman", "exec", "-i", "ohmy-pg", "psql", "-U", "ohmy", "-d", "ohmyenglish", "-tAc", sql],
        check=True, capture_output=True, text=True,
    )
    return out.stdout.strip()


async def wait_for_jobs(session_id, wait: float) -> float:
    """이 세션의 job이 전부 terminal이 될 때까지 기다린다. 상한을 넘기면 그대로 돌려준다."""
    started = time.monotonic()
    while time.monotonic() - started < wait:
        pending = psql(
            "select count(*) from analysis_jobs j join utterances u on u.id = j.utterance_id "
            f"where u.session_id = '{session_id}' and j.status in ('pending','running')"
        )
        if pending == "0":
            break
        await asyncio.sleep(2)
    return round(time.monotonic() - started, 1)


def occurrence_snapshot(utterance_id) -> dict:
    """한 발화의 occurrence 수와 그 패턴들의 frequency — 재분석 전후 대조용."""
    raw = psql(
        "select count(*)::text || '|' || coalesce(string_agg(distinct ep.pattern_key || '=' || "
        "ep.frequency, ',' order by ep.pattern_key || '=' || ep.frequency), '-') "
        "  from error_occurrences eo join error_patterns ep on ep.id = eo.pattern_id "
        f" where eo.utterance_id = '{utterance_id}'"
    )
    count, _, freqs = raw.partition("|")
    return {"occurrences": int(count), "pattern_frequencies": freqs}


async def run(scenario: str, sentences: list[str], wait: float) -> dict:
    pool = await get_db_pool()
    try:
        session_id = await create_session(pool, FIXED_USER_ID)
        psql(
            "insert into harness_sessions (run_id, session_id, scenario) values "
            f"('{RUN_ID}', '{session_id}', '{scenario}') on conflict do nothing"
        )
        print(f"session_id = {session_id}  (scenario {scenario})")

        utterance_type = UTTERANCE_TYPE.get(scenario, "learning")
        saved = []
        utterance_ids = []
        async with pool.acquire() as conn:
            for text in sentences:
                utterance = await save_final_transcript(
                    conn, session_id, text, utterance_type=utterance_type
                )
                saved.append({"seq": utterance.sequence_no, "text": text, "type": utterance_type})
                utterance_ids.append(utterance.id)
                print(f"  saved #{utterance.sequence_no} [{utterance_type}]: {text}")

        elapsed = await wait_for_jobs(session_id, wait)
        result: dict[str, object] = {
            "scenario": scenario, "session_id": str(session_id),
            "saved": saved, "wait_s": elapsed,
        }

        # E6: 같은 발화에 job을 다시 등록해 replace 멱등성을 종단에서 관측한다.
        # (같은 문장을 두 번 넣는 것은 발화가 둘이라 멱등 테스트가 아니다 — 재분석이어야 한다.)
        if scenario == "E6":
            uid = utterance_ids[0]
            result["before"] = occurrence_snapshot(uid)
            print(f"\n  1차 분석 결과: {result['before']}")
            async with pool.acquire() as conn:
                requeued = await enqueue_analyze(conn, uid)
            print(f"  재분석 job 등록: {'성공' if requeued else '거부(중복)'}")
            result["requeued"] = bool(requeued)
            result["wait2_s"] = await wait_for_jobs(session_id, wait)
            result["after"] = occurrence_snapshot(uid)
            print(f"  재분석 결과:   {result['after']}")

        await mark_session_ended(pool, session_id, "completed")
        return result
    finally:
        await close_pool()


def report(session_id: str) -> None:
    print("\n--- 검출된 패턴 (이 세션) ---")
    print(psql(
        "select ep.category, ep.pattern_key, count(eo.id) as occ_in_session, ep.frequency as total_freq, "
        "       max(eo.severity) as sev, round(max(eo.confidence),2) as conf "
        "  from error_occurrences eo "
        "  join error_patterns ep on ep.id = eo.pattern_id "
        "  join utterances u on u.id = eo.utterance_id "
        f" where u.session_id = '{session_id}' "
        " group by ep.category, ep.pattern_key, ep.frequency order by ep.category"
    ) or "(없음)")
    print("\n--- job 상태 ---")
    print(psql(
        "select j.status, count(*) from analysis_jobs j join utterances u on u.id = j.utterance_id "
        f"where u.session_id = '{session_id}' group by 1"
    ))
    print("\n--- 학습 제시 컬럼 (Phase 1 미구현 확인) ---")
    print(psql(
        "select count(*) filter (where next_review_at is not null) as next_review_set, "
        "       count(*) filter (where mastery_score <> 0) as mastery_set, "
        "       (select count(*) from review_tasks) as review_task_rows "
        "  from error_patterns where user_id = '00000000-0000-0000-0000-000000000001'"
    ))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True, choices=sorted(INJECTIONS))
    ap.add_argument("--wait", type=float, default=180.0)
    args = ap.parse_args()

    result = asyncio.run(run(args.scenario, INJECTIONS[args.scenario], args.wait))
    out = HARNESS / "evidence" / f"{args.scenario}-injection.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\nwaited {result['wait_s']}s for the worker")
    report(result["session_id"])
    print(f"\nraw -> {out}")
    print(f"결과 API: curl -s localhost:8002/api/sessions/{result['session_id']}/results")
    return 0


if __name__ == "__main__":
    sys.exit(main())
