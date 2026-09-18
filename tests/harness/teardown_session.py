"""회차가 만든 세션 하나를 걷는다 — 하네스가 앱 큐에 job 을 남기지 않게 하는 자리 (`TASK-193`).

왜 필요한가: 회차 하나가 큐에 **job 넷**을 남긴다(2026-09-18 실측 · 두 번 재현).
셋(`plan_next_session`·`summarize_session`·`summarize_week`)은 **세션 종료가 그 자리에서**
등록하므로 워커가 꺼져 있어도 쌓인다. 넷째(`analyze_utterance`)는 뒤에 워커가 기동할 때
`sweep_lost_runs` 가 **끝난 세션의 job 없는 발화 묶음을 걷어** 등록한다
(`workers/analysis_worker.py` · `H-CD`). ⇒ 큐를 비워 두는 것으로는 막을 수 없고
**회차가 자기 세션을 걷어야** 한다.

⛔ **식별은 회차가 기록한 `session_id` 하나로 한다 — job 을 따로 식별하지 않는다.**
`analysis_jobs` 는 `utterances`·`learning_sessions` 양쪽에서 `on delete cascade` 로 매달려 있어
(`db/migrations/001_initial_schema.sql`) 세션을 지우면 함께 사라진다. 그래서 시각창·개수 차이
같은 **앱 데이터 계산이 필요 없다** — 그런 계산은 같은 DB 를 쓰는 남의 행을 지운다
(`p_app_path.py` 머리말).

⛔ **`error_patterns`·`review_tasks` 는 지우지 않는다.** 회차가 만든 것이 아니라 **기존 행을
갱신한** 것이므로 삭제가 아니라 회차 전 스냅샷으로 복원해야 한다(`browser_leg.md` §8-②).

쓰는 법 — `--from-observation` 이 정본 경로다(`p_app_path.py --out` 이 쓴 JSON 을 그대로 받는다):

    ./app/backend/.venv/bin/python tests/harness/teardown_session.py \
      --from-observation tests/harness/runs/<회차>.json

브라우저 레그를 손으로 돌렸으면 화면이 보고한 ID 를 직접 준다:

    ./app/backend/.venv/bin/python tests/harness/teardown_session.py --session-id <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS.parent.parent / "app" / "backend"))

from app.config import get_settings  # noqa: E402
from app.db import close_pool  # noqa: E402
from app.db import pool as get_db_pool  # noqa: E402
from app.services.recordings import (  # noqa: E402
    PURGE_LIMIT_PER_CYCLE,
    recording_dir,
    remove_orphan_recordings_in,
    remove_recording_dir_if_empty,
)


def resolve_session_id(args: argparse.Namespace) -> UUID:
    """지울 세션 하나를 정한다 — 관측 JSON 이 정본이고 `--session-id` 는 수동 회차용이다."""
    if args.session_id:
        return UUID(args.session_id)
    observed = json.loads(Path(args.from_observation).read_text(encoding="utf-8"))
    raw = observed.get("walk", {}).get("startedSessionId")
    if not raw:
        raise SystemExit(
            f"{args.from_observation} 에 walk.startedSessionId 가 없다 — 회차가 세션을 열지"
            " 못했다면 지울 것도 없다. 열었는데 비어 있으면 그 회차의 관측 자체가 실패한 것이다"
        )
    return UUID(raw)


def _remove_recordings(session_id: UUID) -> int:
    """그 세션의 낭독 녹음 파일을 지운다 (2026-09-18 · `TASK-210` 실측으로 드러난 자리).

    ⛔ **DB 만 걷으면 파일이 고아로 남는다.** 실측: 행을 걷은 뒤 `파일 잔여: True` 였다. 앱에는
    고아 파일 스윕이 있지만(`recordings.sweep_orphan_recording_files`) **워커가 꺼진 개발 환경에서는
    돌지 않으므로** 회차가 자기 파일을 직접 걷어야 한다.
    ⛔ **세션 디렉터리만 지운다** — 뿌리를 지우면 남의 회차 파일까지 없어진다.

    ⛔ **삭제 규칙을 여기서 다시 구현하지 않는다** (`TASK-216`). 이전 판은 디렉터리의 **모든**
    파일을 지웠고 그것은 앱의 정책과 달랐다 — 앱은 *"이름 규칙에 맞지 않는 파일은 지우지 않고
    남긴다"* 로 되돌릴 수 없는 삭제를 막는다(`services/recordings` 가 그 절충의 근거를 가진다).
    규칙이 두 벌이면 한쪽만 고쳐져 조용히 갈라지므로 **그 함수를 그대로 쓴다.**
    ⚠️ **동작이 바뀌었다 — 삭제 범위가 좁아졌다.** 우리가 만든 `.pcm`·`.pcm.part` 만 지우고 그
    밖의 파일은 남는다. 그러면 디렉터리도 남고, **그 남은 디렉터리가 조사의 신호다.**

    ⛔ **살아 있는 포인터를 빈 집합으로 준다** — 호출 시점에 발화 행이 **이미 지워져 있으므로**
    (위 순서 주석) 그 세션의 우리 파일은 전부 고아다. ⚠️ 순서가 뒤집히면 이 빈 집합이 거짓이
    되는 것이 아니라 **그 세션의 살아 있는 녹음까지 지운다** — 순서가 계약인 이유가 하나 늘었다.
    ⚠️ **한 번 부르는 것으로 끝내지 않는다** — 그 함수는 사이클 상한(`PURGE_LIMIT_PER_CYCLE`)에서
    멈추고 남은 것을 다음 호출에 넘긴다(멱등). 회차가 원하는 것은 **그 세션의 전량**이므로 상한에
    닿는 동안 이어 부르고 개수를 더한다.
    """
    settings = get_settings()
    directory = recording_dir(settings.shadowing_audio_root, session_id)
    if not directory.is_dir():
        return 0
    removed = 0
    while True:
        batch = remove_orphan_recordings_in(directory, set(), limit=PURGE_LIMIT_PER_CYCLE)
        removed += batch
        if batch < PURGE_LIMIT_PER_CYCLE:
            break
    remove_recording_dir_if_empty(directory)
    return removed


async def teardown(session_id: UUID) -> dict[str, Any]:
    """그 세션과 거기 매달린 것만 지우고 개수를 돌려준다."""
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "select status, started_at from learning_sessions where id = $1", session_id
            )
            if row is None:
                raise SystemExit(
                    f"{session_id} 가 learning_sessions 에 없다 — 이미 걷혔거나 ID 가 틀렸다."
                    " ⛔ 다른 세션을 찾아 지우지 마라"
                )
            report: dict[str, Any] = {
                "session_id": str(session_id),
                "status": row["status"],
                "started_at": row["started_at"].isoformat(),
                "utterances": await conn.fetchval(
                    "select count(*) from utterances where session_id = $1", session_id
                ),
                "utterance_jobs_deleted": await conn.fetchval(
                    "with d as (delete from analysis_jobs j using utterances u "
                    "  where u.id = j.utterance_id and u.session_id = $1 returning 1) "
                    "select count(*) from d",
                    session_id,
                ),
                "session_jobs_deleted": await conn.fetchval(
                    "with d as (delete from analysis_jobs where session_id = $1 returning 1) "
                    "select count(*) from d",
                    session_id,
                ),
                "session_deleted": await conn.fetchval(
                    "with d as (delete from learning_sessions where id = $1 returning 1) "
                    "select count(*) from d",
                    session_id,
                ),
                # ⛔ 행을 지운 «뒤» 파일을 지운다 — 순서가 뒤집히면 행이 남은 채 파일만 없어져
                #    「포인터만 있는 상태」가 되고, 그것은 앱이 정상으로 인정하는 상태라 조용하다.
                "recordings_removed": _remove_recordings(session_id),
            }
        return report
    finally:
        await close_pool()


def main() -> int:
    ap = argparse.ArgumentParser(description="회차가 만든 세션 하나를 걷는다 (TASK-193)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--from-observation", help="p_app_path.py --out 이 쓴 관측 JSON 경로")
    src.add_argument("--session-id", help="수동 회차용 — 화면이 보고한 session_id")
    args = ap.parse_args()

    report = asyncio.run(teardown(resolve_session_id(args)))
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print(
        "⚠️ error_patterns·review_tasks 는 지우지 않았다 — 회차가 «갱신» 한 기존 행이므로 회차 전"
        " 스냅샷으로 복원한다(browser_leg.md §8-②)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
