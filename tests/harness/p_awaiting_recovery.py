#!/usr/bin/env python3
"""`TASK-79` AC#2 — **스윕이 늦어도 화면이 교정을 놓치지 않는지**를 브라우저 레그로 잰다.

## 무엇을 반증하려는가

옛 판은 `NO_UTTERANCES_RECHECKS = 3`(약 **6초**)에서 폴링을 멈췄다. 그러면 종료 flush 가 실패한
사이 워커가 다른 일을 하느라 스윕이 6초를 넘겨 지연되면, 네 번째 판독에서 폴링이 끝나고
**그 뒤 분석이 끝나도 화면이 교정을 영구히 표시하지 않는다.** `TASK-79` 는 그 상수를 없애고
결과 API 의 `awaiting_analysis` 로 폴링 여부를 정하게 고쳤다.

⛔ **그래서 이 계측이 잡아야 하는 것은 「6초를 넘겨도 살아 있는가」다.** 상수를 늘리는 수정으로는
통과할 수 없게, **flush 를 옛 상한보다 훨씬 늦게** 건다.

## 회차의 뼈대 — 한 문서를 끝까지 열어 두고 상태를 밖에서 움직인다

| 국면 | 밖에서 하는 일 | 화면이 보여야 하는 것 |
|---|---|---|
| A | 발화만 저장(job 0건) | `분석 대상 없음` · **폴링이 계속 는다** |
| B | 옛 상한을 훨씬 넘긴 뒤 `flush_pending_analysis` | `분석 중` — **새로고침 없이** |
| C | `p5_worker_leg.py guard` → `claim` (실물 분석 1회) | `확정` + 교정 카드 — **새로고침 없이** |

⛔ **`Page.navigate` 를 한 번만 한다.** 국면마다 다시 열면 「폴링이 살아 있었다」가 아니라
「다시 열면 보인다」를 재게 되고, 그것은 옛 판에서도 참이었다.

⚠️ **`claim` 을 이 스크립트가 직접 부르지 않고 `p5_worker_leg.py` 를 서브프로세스로 부른다** —
그 도구의 `guard`·`claim` 단정이 **성공 경로에서도 도는지**가 `TASK-101` AC#2·AC#3 이다.
거부만 확인하고 닫으면 「아무것도 거부하지 않는 도구」와 구별되지 않는다.

실행 (cwd 는 `app/backend`):
    .venv/bin/python ../../tests/harness/p_awaiting_recovery.py run --out-dir <회차>
    .venv/bin/python ../../tests/harness/p_awaiting_recovery.py teardown --in <회차>/report.json
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any
from uuid import UUID

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))
sys.path.insert(0, str(HARNESS.parent.parent / "app" / "backend"))

from c2_render_hierarchy import Cdp, find_target  # noqa: E402
from websockets.asyncio.client import connect  # noqa: E402

from app.api.ws import FIXED_USER_ID  # noqa: E402
from app.db import close_pool  # noqa: E402
from app.db import pool as get_db_pool  # noqa: E402
from app.services.sessions import create_session  # noqa: E402
from app.services.utterances import flush_pending_analysis, save_final_transcript  # noqa: E402

P5 = HARNESS / "p5_worker_leg.py"

# 문법 오류를 **일부러** 담는다 — 국면 C 가 「교정 카드가 왔는가」를 재기 때문이다.
# ⚠️ 기존 패턴을 다시 밟는 문장을 골랐다(시제·관사) — 새 패턴이 적게 생기면 복원할 것이 적다.
UTTERANCE = "Yesterday I go to the office and present the quarterly plan."

# 옛 상한은 3회 × 2초 = 약 6초다. **그보다 4배 이상 뒤에** flush 를 건다 —
# 「상수를 조금 늘린」 수정으로는 통과할 수 없어야 한다.
OLD_LIMIT_S = 6.0
FLUSH_AT_S = 26.0
PHASE_A_SAMPLES = (4.0, 10.0, 20.0, 26.0)
PHASE_B_SAMPLES = (3.0, 7.0)
PHASE_C_SAMPLES = (3.0, 8.0, 15.0)

# 폴링 계수기. **앱 코드보다 먼저** 문서에 심어야 하므로
# `Page.addScriptToEvaluateOnNewDocument` 로 넣는다.
# ⚠️ `fetch` 와 `XMLHttpRequest` 를 **둘 다** 감싼다 — 어느 것으로 폴링하는지 가정하지 않는다.
COUNTER_JS = """
(() => {
  window.__pollFetch = 0;
  window.__pollXhr = 0;
  const hit = (u) => { try { return String(u).includes('/results'); } catch (e) { return false; } };
  const of = window.fetch;
  window.fetch = function (...a) {
    const u = a[0] && a[0].url ? a[0].url : a[0];
    if (hit(u)) window.__pollFetch += 1;
    return of.apply(this, a);
  };
  const oo = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function (m, u, ...rest) {
    if (hit(u)) window.__pollXhr += 1;
    return oo.call(this, m, u, ...rest);
  };
})();
"""

# 화면 판독. **요소를 구조로 지목한다**(`browser_leg.md` §5) — 전역 텍스트 포함 검사를 쓰지 않는다.
SAMPLE_JS = """
(() => {
  const main = document.querySelector('main');
  const kids = main ? Array.from(main.children) : [];
  const label = (kids.find((el) => el.tagName === 'P') || {}).textContent || null;
  const strongs = Array.from(document.querySelectorAll('strong')).map((s) => s.textContent.trim());
  return JSON.stringify({
    poll_fetch: window.__pollFetch === undefined ? null : window.__pollFetch,
    poll_xhr: window.__pollXhr === undefined ? null : window.__pollXhr,
    label: label,
    original: strongs.filter((t) => t === '원문:').length,
    corrected: strongs.filter((t) => t === '교정문:').length,
  });
})()
"""


def _api(session_id: str, base: str = "http://127.0.0.1:8002") -> dict[str, Any]:
    with urllib.request.urlopen(f"{base}/api/sessions/{session_id}/results") as fh:  # noqa: S310
        return json.loads(fh.read())


async def _sample(cdp: Cdp, session_id: str, at: float) -> dict[str, Any]:
    raw = await cdp.eval(SAMPLE_JS)
    seen = json.loads(raw)
    api = _api(session_id)
    seen["t_s"] = round(at, 1)
    seen["api_status"] = api.get("status")
    seen["api_awaiting"] = api.get("awaiting_analysis")
    seen["api_corrections"] = None if api.get("corrections") is None else len(api["corrections"])
    print(
        f"  t={seen['t_s']:>5}s  poll(fetch/xhr)={seen['poll_fetch']}/{seen['poll_xhr']}"
        f"  라벨={seen['label']!r}  원문/교정문={seen['original']}/{seen['corrected']}"
        f"  api={seen['api_status']} awaiting={seen['api_awaiting']}"
        f" corrections={seen['api_corrections']}"
    )
    return seen


def _run_p5(*argv: str) -> dict[str, Any]:
    """`p5_worker_leg.py` 를 서브프로세스로 부르고 **종료 코드를 그대로 담는다.**"""
    cmd = [sys.executable, str(P5), *argv]
    print(f"  $ {' '.join(argv)}")
    done = subprocess.run(cmd, capture_output=True, text=True)  # noqa: S603
    tail = (done.stdout or "").strip().splitlines()[-3:]
    for line in tail:
        print(f"    {line}")
    if done.returncode != 0:
        for line in (done.stderr or "").strip().splitlines()[-4:]:
            print(f"    ! {line}", file=sys.stderr)
    return {
        "argv": list(argv),
        "returncode": done.returncode,
        "stdout": done.stdout,
        "stderr": done.stderr,
    }


async def run(args: argparse.Namespace) -> int:
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {"phases": {}}

    pool = await get_db_pool()
    session_id: UUID | None = None
    try:
        session_id = await create_session(pool, FIXED_USER_ID)
        report["session_id"] = str(session_id)
        print(f"session_id = {session_id}")
        async with pool.acquire() as conn:
            utterance = await save_final_transcript(
                conn, session_id, UTTERANCE, utterance_type="learning"
            )
        report["utterance_id"] = str(utterance.id)

        before = _api(str(session_id))
        report["api_before"] = before
        print(
            f"  회차 전 API: status={before.get('status')}"
            f" awaiting={before.get('awaiting_analysis')}"
        )
        if not before.get("awaiting_analysis"):
            print(
                "⛔ 거부한다 — awaiting_analysis 가 참이 아니다. 이 회차의 전제가 성립하지 않는다",
                file=sys.stderr,
            )
            return 1

        url = f"{args.base}/results/{session_id}"
        ws_url, _ = find_target(args.port, url)
        async with connect(ws_url, max_size=None) as ws:
            cdp = Cdp(ws)
            await cdp.call("Page.enable")
            await cdp.call("Runtime.enable")
            await cdp.call("Page.addScriptToEvaluateOnNewDocument", {"source": COUNTER_JS})
            await cdp.call("Page.navigate", {"url": url})
            started = time.monotonic()
            await asyncio.sleep(1.5)

            print("\n국면 A — 발화만 있고 job 0건. 폴링이 옛 상한을 넘겨 사는가")
            phase_a = []
            for mark in PHASE_A_SAMPLES:
                await asyncio.sleep(max(0.0, mark - (time.monotonic() - started)))
                phase_a.append(await _sample(cdp, str(session_id), time.monotonic() - started))
            report["phases"]["A"] = phase_a

            print(
                f"\n국면 B — t={FLUSH_AT_S}s 에 flush 를 건다"
                f" (옛 상한 {OLD_LIMIT_S}s 의 4배 이상 뒤)"
            )
            async with pool.acquire() as conn:
                await flush_pending_analysis(conn, session_id)
            print("  flush 완료 — 이제 job 이 있다")
            phase_b = []
            for gap in PHASE_B_SAMPLES:
                await asyncio.sleep(gap)
                phase_b.append(await _sample(cdp, str(session_id), time.monotonic() - started))
            report["phases"]["B"] = phase_b

            print("\n국면 C — p5_worker_leg.py 로 내 job 하나만 처리한다")
            guard_out = out_dir / "p5-guard.json"
            report["p5_guard"] = _run_p5(
                "guard", "--expect-session", str(session_id), "--out", str(guard_out)
            )
            if report["p5_guard"]["returncode"] != 0:
                print("⛔ guard 가 실패했다 — claim 을 돌리지 않는다", file=sys.stderr)
            else:
                report["p5_claim"] = _run_p5("claim", "--expect-session", str(session_id))
                report["p5_restore"] = _run_p5("restore", "--in", str(guard_out))

            phase_c = []
            for gap in PHASE_C_SAMPLES:
                await asyncio.sleep(gap)
                phase_c.append(await _sample(cdp, str(session_id), time.monotonic() - started))
            report["phases"]["C"] = phase_c

            shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
            (out_dir / "recovered-results.png").write_bytes(base64.b64decode(shot["data"]))
            print(f"\nshot -> {out_dir / 'recovered-results.png'}")

        report["api_after"] = _api(str(session_id))
        return 0
    finally:
        (out_dir / "report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"report -> {out_dir / 'report.json'}")
        await close_pool()


async def teardown(args: argparse.Namespace) -> int:
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    session_id = UUID(state["session_id"])
    pool = await get_db_pool()
    try:
        async with pool.acquire() as conn:
            report = {
                "occurrences_deleted": await conn.fetchval(
                    "with d as (delete from error_occurrences eo using utterances u "
                    "  where u.id = eo.utterance_id and u.session_id = $1 returning 1) "
                    "select count(*) from d",
                    session_id,
                ),
                "jobs_deleted": await conn.fetchval(
                    "with d as (delete from analysis_jobs j using utterances u "
                    "  where u.id = j.utterance_id and u.session_id = $1 returning 1) "
                    "select count(*) from d",
                    session_id,
                ),
                "plan_jobs_deleted": await conn.fetchval(
                    "with d as (delete from analysis_jobs where session_id = $1 returning 1) "
                    "select count(*) from d",
                    session_id,
                ),
                "session_deleted": await conn.fetchval(
                    "with d as (delete from learning_sessions where id = $1 returning 1) "
                    "select count(*) from d",
                    session_id,
                ),
            }
        print(json.dumps(report, ensure_ascii=False, indent=1))
        print(
            "⚠️ error_patterns·review_tasks 는 지우지 않았다 — 기존 패턴이 갱신된 것이라 "
            "회차 전 스냅샷으로 «복원»해야 한다(browser_leg.md §8-②). 삭제가 아니다."
        )
        return 0
    finally:
        await close_pool()


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out-dir", required=True)
    r.add_argument("--port", type=int, default=9222)
    r.add_argument("--base", default="http://localhost:3000")
    r.set_defaults(fn=run)
    d = sub.add_parser("teardown")
    d.add_argument("--in", dest="state", required=True)
    d.set_defaults(fn=teardown)
    args = ap.parse_args()
    return asyncio.run(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
