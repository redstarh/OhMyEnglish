"""B6 회차 전용 — 낭독 판정 두 갈래를 «한 세션»으로 잰다 (TS-29 AC#1·AC#2).

⛔ 대상 소스를 고치지 않는다. `tests/harness/p_readback_leg.py` 의 JS 상수와 도우미를
   **그대로 import 해서 재사용**한다 — 새 계측을 만들지 않는다.

왜 이 파일이 필요한가:
  · `p_readback_leg.py` 는 낭독 1회 · 판정 1회로 끝나므로 404 갈래를 같은 세션에서 볼 수 없다.
  · 스텁 어댑터는 세션이 21ms 안에 끝나 화면이 뜨지 않는다(2026-09-19 실측 · 3회 재현) —
    그래서 「쓸 수 없어요」 화면을 스텁으로 관측할 수 없다.
  · 실물 회차는 3회 상한이라 성공 갈래와 404 갈래를 한 세션에 담아야 한다.

순서: 성공 갈래를 «먼저» 태운다 — 비용이 나는 쪽이고, 뒤에 죽어도 그 관측은 남는다.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

HARNESS = Path("/Users/redstar/MyProject/OhMyEnglish/tests/harness")
sys.path.insert(0, str(HARNESS))

import p_readback_leg as RB  # noqa: E402
from c2_render_hierarchy import Cdp, find_target  # noqa: E402
from websockets.asyncio.client import connect  # noqa: E402

PSQL = "/opt/homebrew/opt/postgresql@17/bin/psql"
DSN = "postgresql://ohmy:ohmy@localhost:5432/ohmyenglish"
UNAVAILABLE = "지금은 낭독 판정을 쓸 수 없어요."

# ⛔ 부분 관측이라도 반드시 남긴다 — 중간에 죽으면 그 자리까지가 증거다.
OUT: dict[str, Any] = {}


def psql(sql: str) -> str:
    out = subprocess.run(
        [PSQL, DSN, "-q", "-tAc", sql], check=True, capture_output=True, text=True
    )
    return out.stdout.strip()


async def shot(cdp: Any, path: str) -> None:
    data = await cdp.call("Page.captureScreenshot", {"format": "png"})
    Path(path).write_bytes(base64.b64decode(data["data"]))


async def read_leg(cdp: Any, args: argparse.Namespace, tag: str) -> float:
    """따라 읽기 → 낭독 흘림 → 읽기 끝 → 「내 낭독 듣기」가 뜰 때까지."""
    await cdp.click(
        "Array.from(document.querySelectorAll('button'))"
        "  .find(b => /따라 읽기/.test(b.textContent||''))",
        "따라 읽기",
    )
    played = await cdp.eval("window.__rbPlay()", await_promise=True)
    print(f"[{tag}] 낭독 흘림 {played}초")
    await asyncio.sleep(float(played) + args.tail_wait_s)
    await cdp.click(
        "Array.from(document.querySelectorAll('button'))"
        "  .find(b => /읽기 끝/.test(b.textContent||''))",
        "읽기 끝",
    )
    OUT[f"{tag}_buttons_after_recording"] = await RB._wait_for_button(
        cdp, "내 낭독 듣기", timeout_s=args.saved_timeout_s
    )
    return float(played)


async def judge(cdp: Any, *, timeout_s: float, want_words: bool) -> dict[str, Any]:
    """「낭독 판정 보기」를 누르고 낱말 또는 안내가 뜰 때까지 기다린다."""
    await cdp.click(
        "Array.from(document.querySelectorAll('button'))"
        "  .find(b => /낭독 판정 보기/.test(b.textContent||''))",
        "낭독 판정 보기",
    )
    deadline = asyncio.get_running_loop().time() + timeout_s
    words: list[dict[str, Any]] = []
    notices: list[str] = []
    while asyncio.get_running_loop().time() < deadline:
        words = await cdp.eval(RB.WORDS_JS)
        notices = await cdp.eval(RB.NOTICES_JS)
        if want_words and words:
            break
        if not want_words and any(UNAVAILABLE in n for n in notices):
            break
        await asyncio.sleep(0.5)
    return {"words": words, "notices": notices}


async def run(args: argparse.Namespace) -> None:
    ws_url, url = find_target(args.port, args.url)
    print(f"대상 탭: {url}")
    OUT["target_url"] = url

    async with connect(ws_url, max_size=None) as ws:
        cdp = Cdp(ws)
        await cdp.call("Page.bringToFront")
        nav = await cdp.call("Page.navigate", {"url": args.url})
        if nav.get("errorText"):
            raise SystemExit(f"navigate 실패: {nav['errorText']}")
        # ⛔ readyState 만 보면 **직전 문서**의 complete 에 즉시 만족한다(2026-09-19 실측 —
        #    about:blank 에 계측을 심고 새 문서가 그것을 지웠다). 버튼이 실제로 뜰 때까지 센다.
        for _ in range(60):
            await asyncio.sleep(0.5)
            here = await cdp.eval("location.href")
            btns = await cdp.eval(RB.BUTTONS_JS)
            if here.rstrip("/") == args.url.rstrip("/") and btns:
                break
        else:
            raise SystemExit("홈 화면 버튼이 30초 안에 뜨지 않았다")
        OUT["home_buttons"] = [b["text"] for b in await cdp.eval(RB.BUTTONS_JS)]

        installed = await cdp.eval(
            RB.MIC_JS.replace("FIXTURE_URL", args.fixture_url), await_promise=True
        )
        if installed != "mic-installed":
            raise SystemExit(f"마이크 대체 실패: {installed!r}")
        OUT["mic"] = await cdp.eval("window.__rb")
        print(f"마이크 대체: {OUT['mic']['durationSec']}초 · rate {OUT['mic']['bufferRate']}")

        await cdp.click(
            "Array.from(document.querySelectorAll('button'))"
            "  .find(b => /쉐도잉/.test(b.textContent||''))",
            "쉐도잉",
        )
        OUT["buttons_after_entry"] = await RB._wait_for_button(
            cdp, "따라 읽기", timeout_s=args.session_timeout_s
        )
        print(f"세션 화면: {[b['text'] for b in OUT['buttons_after_entry']]}")

        # ── 갈래 ① 성공 (비용이 나는 쪽을 먼저 태운다) ────────────────────────────
        await read_leg(cdp, args, "leg1")
        OUT["leg1_judge"] = await judge(cdp, timeout_s=args.judge_timeout_s, want_words=True)
        print(f"[leg1] 낱말 {len(OUT['leg1_judge']['words'])}개")
        if args.shot_prefix:
            await shot(cdp, f"{args.shot_prefix}-leg1.png")
        OUT["fetches_after_leg1"] = (await cdp.eval("window.__rb"))["fetches"]
        rb = [u for u in OUT["fetches_after_leg1"] if "/readback" in u]
        OUT["leg1_readback_urls"] = rb
        if rb:
            m = re.search(r"/api/sessions/([0-9a-f-]+)/recordings/([0-9a-f-]+)/readback", rb[0])
            if m:
                OUT["session_id"] = m.group(1)
                OUT["leg1_utterance_id"] = m.group(2)
                print(f"세션 {OUT['session_id']} · 낭독① {OUT['leg1_utterance_id']}")

        # ── 갈래 ② audio_url 을 지워 404 를 만든다 ──────────────────────────────
        await read_leg(cdp, args, "leg2")
        sid = OUT.get("session_id")
        if not sid:
            raise SystemExit("세션 ID 를 판정 요청 주소에서 얻지 못했다 — 갈래 ②를 태울 수 없다")
        rows = psql(
            "select id from utterances where session_id = '%s'"
            " and utterance_type = 'shadowing_recording' and readback_transcript is null"
            " and audio_url is not null order by created_at desc" % sid
        ).splitlines()
        OUT["leg2_candidates"] = rows
        if len(rows) != 1:
            raise SystemExit(f"낭독② 후보가 1건이 아니다: {rows!r}")
        OUT["leg2_utterance_id"] = rows[0]
        affected = psql(
            "with x as (update utterances set audio_url = null where id = '%s' returning 1)"
            " select count(*) from x" % rows[0]
        )
        OUT["leg2_audio_url_nulled"] = affected
        print(f"낭독② {rows[0]} 의 audio_url 을 지웠다 (갱신 {affected}행)")
        OUT["leg2_judge"] = await judge(cdp, timeout_s=args.notice_timeout_s, want_words=False)
        print(f"[leg2] 안내 {OUT['leg2_judge']['notices']}")
        if args.shot_prefix:
            await shot(cdp, f"{args.shot_prefix}-leg2.png")
        OUT["fetches_after_leg2"] = (await cdp.eval("window.__rb"))["fetches"]

        await cdp.click(
            "Array.from(document.querySelectorAll('button'))"
            "  .find(b => /학습 종료/.test(b.textContent||''))",
            "학습 종료",
        )
        await asyncio.sleep(args.tail_wait_s)
        OUT["url_after_end"] = await cdp.eval("location.href")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--url", default="http://localhost:3000/")
    ap.add_argument("--fixture-url", default="/harness/readback.wav")
    ap.add_argument("--session-timeout-s", type=float, default=60.0)
    ap.add_argument("--saved-timeout-s", type=float, default=40.0)
    ap.add_argument("--judge-timeout-s", type=float, default=90.0)
    ap.add_argument("--notice-timeout-s", type=float, default=30.0)
    ap.add_argument("--tail-wait-s", type=float, default=3.0)
    ap.add_argument("--shot-prefix")
    ap.add_argument("--out")
    args = ap.parse_args()
    try:
        asyncio.run(run(args))
    finally:
        if args.out:
            Path(args.out).write_text(
                json.dumps(OUT, ensure_ascii=False, indent=1), encoding="utf-8"
            )
            print(f"기록: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
