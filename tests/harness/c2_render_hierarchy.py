#!/usr/bin/env python3
"""C2 렌더 위계 관측 — `browser_leg.md` §6의 실행체 (A2-1 · A2-2 · A2-3).

**왜 에이전트 액션이 아니라 이 스크립트인가**: §6이 ⛔로 못 박은 것은 "전 과정을 한 `eval`에"이고
그 이유는 **에이전트 라운드트립(~30 s)이 주입 창(10 s)보다 길기 때문**이다. 이 스크립트는
`measure_contrast.py`와 **같은 수단**(디버깅 포트 9222 + CDP over websocket)으로 붙어 왕복이
밀리초 단위이므로 창 안에서 클릭·주입·판독을 끝낸다. 새 수단이 아니라 같은 수단의 재사용이다.

**모드 전환**도 `measure_contrast.py`가 이미 쓰는 `Emulation.setEmulatedMedia`를 재사용한다.

## 이 스크립트가 지키는 규약

- **대상 요소를 색으로 고르지 않는다**(§6) — 선별은 `<strong>`의 `질문: `/`답변: ` 접두로만 한다.
  색은 재려는 값이므로 선별에 쓰면 자기순환이다.
- **기대값을 하드코딩하지 않는다**(§6 · AC #3) — `omy.probeColor(token)`으로 런타임에 유도한다.
- **주입 전에 `active` 도달 후 접두 `<p>` 0개를 센다**(§6-0 · AC #4) — 클릭 전에 재면 컨테이너가
  아직 마운트되지 않아 0일 수 있고 그러면 주입 경로가 죽어 있어도 통과한다.
- **user activation을 진짜 CDP 클릭으로 만든다**(함정 `H-AE`) — 합성 `element.click()`은
  `lib/audio.ts`의 `await context.resume()`를 영원히 pending으로 만들어 `active`에 도달하지 못한다.
- **한 문서에 세션 하나**(§4-4 · 3규약 2) — 모드마다 `Page.navigate`로 새 문서를 연다.
- **계측을 sha256으로 고정한다**(§10-3) — 페이지가 받은 소스의 해시를 페이지 안에서 계산해
  파일 해시와 대조한다. 손으로 옮겨 적는 전사 드리프트가 구조적으로 0이 된다.
- **`eval` 반환값이 증거다**(§10-1) — 개수·`textContent`만 내지 않고 판정 대상의 `outerHTML`과
  컨테이너 `innerHTML`을 함께 담는다.

실행:
    cd app/backend && .venv/bin/python ../../tests/harness/c2_render_hierarchy.py
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from websockets.asyncio.client import connect

HARNESS = Path(__file__).resolve().parent
ROOT = HARNESS.parent.parent
INSTRUMENT = HARNESS / "instrument.js"
EVIDENCE = ROOT / ".harness" / "evidence"

# 주입 문구는 **서로 다르게** 둔다 — 같으면 "partial 줄이 사라졌다"를 텍스트로 확인할 수 없다.
PARTIAL_TEXT = "PARTIAL_PROBE_ALPHA 부분 전사문 표본"
FINAL_TEXT = "FINAL_PROBE_BETA 확정 전사문 표본"

# ── 창 안에서 한 번에 도는 블록 ────────────────────────────────────────────────
# ⚠️ 클릭은 이 블록 **밖**에서 CDP 마우스 이벤트로 한다(합성 클릭은 user activation을 못 만든다).
#    이 블록은 그 클릭 직후에 들어와 `active` 도달을 기다리고 나머지 전부를 끝낸다.
MEASURE_JS = r"""
(async () => {
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const omy = window.__omy;
  if (!omy) throw new Error("계측이 걸려 있지 않다 (window.__omy 부재)");

  const PREFIXES = ["질문: ", "답변: "];
  const prefixed = () =>
    Array.from(document.querySelectorAll("p")).filter((p) => {
      const s = p.querySelector("strong");
      return !!s && PREFIXES.indexOf(s.textContent) !== -1;
    });
  const reasonPs = () =>
    Array.from(document.querySelectorAll("p")).filter((p) =>
      (p.textContent || "").startsWith("사유: ")
    );
  const endButton = () =>
    Array.from(document.querySelectorAll("button")).find((b) =>
      /학습 종료|종료 중/.test(b.textContent || "")
    );
  const waitFor = async (fn, ms, label) => {
    const t0 = performance.now();
    for (;;) {
      let v;
      try { v = fn(); } catch (e) { v = false; }
      if (v) return Math.round(performance.now() - t0);
      if (performance.now() - t0 >= ms) throw new Error(`시간초과(${Math.round(ms)}ms): ${label}`);
      await sleep(16);
    }
  };

  const t0 = performance.now();

  // ① `active` 도달. 버튼 라벨이 `학습 종료`로 바뀌는 것이 그 지표다(page.tsx:346).
  const activeMs = await waitFor(() => !!endButton(), 8000, "active 도달(학습 종료 버튼)");

  // 전사문 컨테이너를 **구조로** 잡는다 — 대기 문구 `<p>`의 부모다. 그 문구는 주입 뒤 사라지므로
  // 참조를 지금 붙잡아 둔다(§10-1이 요구하는 컨테이너 innerHTML의 소유자).
  const waitingP = Array.from(document.querySelectorAll("p")).find(
    (p) => (p.textContent || "").trim() === "대화를 기다리는 중..."
  );
  const container = waitingP ? waitingP.parentElement : null;

  // ② §6-0 — **주입 전에, `active` 도달 후에** 센다. 0이 아니면 이 회차는 ERROR다.
  const beforeInjectCount = prefixed().length;
  const beforeInjectReason = reasonPs().length;

  // ③ 기대값을 런타임에 토큰에서 유도한다(AC #3).
  //    같은 모드에서 두 번 읽는 것이 A2-3의 음성 대조다.
  const probe = {
    muted1: omy.probeColor("--foreground-muted"),
    fg1: omy.probeColor("--foreground"),
    muted2: omy.probeColor("--foreground-muted"),
    fg2: omy.probeColor("--foreground"),
  };

  // ④ partial 주입 → 접두 `<p>` 1개 · 색 판독 (A2-1)
  const partialInjectedAt = Math.round(performance.now() - t0);
  omy.inject({ type: "partial", text: PARTIAL_TEXT, speaker: "agent" });
  const partialRenderMs = await waitFor(
    () => prefixed().length === 1 && prefixed()[0].textContent.indexOf(PARTIAL_TEXT) !== -1,
    3000,
    "partial 줄 렌더"
  );
  const pEl = prefixed()[0];
  const partial = {
    count: prefixed().length,
    color: getComputedStyle(pEl).color,
    text: pEl.textContent,
    outerHTML: pEl.outerHTML,
    reasonPs: reasonPs().length,
  };

  // ⚠️ **partial 상태를 눈으로 보기 위한 회차** — 여기서 멈추면 호출자가 창 안에서 스크린샷을
  // 뜬다. 판정에 쓰는 회차(`--phase both`)는 이 분기를 타지 않는다.
  if (window.__omyStopAfterPartial) {
    return {
      scheme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
      timing: { activeMs, partialInjectedAt, partialRenderMs,
                finalInjectedAt: null, finalRenderMs: null,
                totalMs: Math.round(performance.now() - t0) },
      beforeInject: { prefixedCount: beforeInjectCount, reasonPs: beforeInjectReason,
                      waitingTextPresent: !!waitingP },
      probe,
      partial,
      final: null,
      container: container ? container.innerHTML : null,
      omy: {
        recv: JSON.parse(JSON.stringify(omy.recv)),
        injected: omy.injected,
        appHandlerAttached: omy.meta.appHandlerAttached,
        socketUrls: omy.meta.socketUrls.slice(),
        snapshotCounts: omy.snapshots.map((s) => s.count),
        contextState: omy.contextState().state,
      },
    };
  }

  // ⑤ final 주입 → partial 줄이 사라지고 확정 줄의 색을 읽는다 (A2-2)
  const finalInjectedAt = Math.round(performance.now() - t0);
  omy.inject({ type: "final", text: FINAL_TEXT, speaker: "agent", sequence_no: 1 });
  const finalRenderMs = await waitFor(
    () => prefixed().length === 1 && prefixed()[0].textContent.indexOf(FINAL_TEXT) !== -1,
    3000,
    "final 줄 렌더"
  );
  const fEl = prefixed()[0];
  const finalLine = {
    count: prefixed().length,
    color: getComputedStyle(fEl).color,
    text: fEl.textContent,
    outerHTML: fEl.outerHTML,
    partialTextStillPresent: document.body.textContent.indexOf(PARTIAL_TEXT) !== -1,
    reasonPs: reasonPs().length,
  };

  return {
    scheme: matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light",
    timing: {
      activeMs,
      partialInjectedAt,
      partialRenderMs,
      finalInjectedAt,
      finalRenderMs,
      totalMs: Math.round(performance.now() - t0),
    },
    beforeInject: { prefixedCount: beforeInjectCount, reasonPs: beforeInjectReason,
                    waitingTextPresent: !!waitingP },
    probe,
    partial,
    final: finalLine,
    container: container ? container.innerHTML : null,
    omy: {
      recv: JSON.parse(JSON.stringify(omy.recv)),
      injected: omy.injected,
      appHandlerAttached: omy.meta.appHandlerAttached,
      socketUrls: omy.meta.socketUrls.slice(),
      snapshotCounts: omy.snapshots.map((s) => s.count),
      contextState: omy.contextState().state,
    },
  };
})()
"""


def find_target(port: int, url_substring: str, exact: str) -> tuple[str, str]:
    """⚠️ **정확 일치를 먼저 고른다.** `localhost:3000` 부분일치만 쓰면 열려 있는
    `/results/<id>` 탭을 먼저 잡아 **남의 화면을 하이재킹한다**(실측: 그 탭이 목록 앞에 있었다)."""
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as fh:
        targets = json.load(fh)
    pages = [t for t in targets if t.get("type") == "page"]
    for t in pages:
        if t.get("url", "") == exact:
            return t["webSocketDebuggerUrl"], t["url"]
    for t in pages:
        if url_substring in t.get("url", ""):
            return t["webSocketDebuggerUrl"], t["url"]
    # ⚠️ **없으면 만든다.** 플러그인 Chrome 의 탭은 회차 사이에 사라진다(실측: `json/list` 가
    #    0건이 됐다). 남의 탭을 뒤지지 않고 **전용 탭을 새로 연다** — 부작용이 가장 작다.
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{urllib.parse.quote(exact, safe=':/?=&')}",
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=10) as fh:
        created = json.load(fh)
    if not created.get("webSocketDebuggerUrl"):
        raise SystemExit(f"탭을 만들지 못했다: {created!r}")
    return created["webSocketDebuggerUrl"], created.get("url", exact)


class Cdp:
    """id 를 맞춰 응답을 골라내는 최소 클라이언트 — `measure_contrast.py`와 같은 형태다."""

    def __init__(self, ws) -> None:
        self.ws = ws
        self.msg_id = 0

    async def call(self, method: str, params: dict | None = None) -> dict:
        self.msg_id += 1
        mine = self.msg_id
        await self.ws.send(json.dumps({"id": mine, "method": method, "params": params or {}}))
        while True:
            payload = json.loads(await self.ws.recv())
            if payload.get("id") == mine:
                if "error" in payload:
                    raise SystemExit(f"{method} 실패: {payload['error']}")
                return payload.get("result", {})

    async def eval(self, expression: str, *, await_promise: bool = False) -> Any:
        out = await self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": await_promise},
        )
        if "exceptionDetails" in out:
            detail = out["exceptionDetails"]
            desc = (detail.get("exception") or {}).get("description") or detail.get("text")
            raise SystemExit(f"페이지 예외: {desc}")
        return out["result"].get("value")

    async def click(self, selector_js: str, label: str) -> dict:
        """**진짜** 마우스 이벤트를 보낸다.

        합성 `element.click()`은 user activation을 만들지 못한다(`H-AE`).
        """
        # ⚠️ 이어붙이는 조각 중 **f-string 인 것만** `{{`로 이스케이프한다. 평문 조각에 `}}`를 쓰면
        #    닫는 중괄호가 하나 더 붙어 `SyntaxError: Unexpected token '}'`가 난다(실측).
        rect = await self.eval(
            f"(() => {{ const el = {selector_js}; if (!el) return null;"
            " const r = el.getBoundingClientRect();"
            " return {x: r.left + r.width/2, y: r.top + r.height/2, w: r.width, h: r.height,"
            " text: (el.textContent||'').slice(0,40)}; })()"
        )
        if not rect or rect["w"] <= 0 or rect["h"] <= 0:
            raise SystemExit(f"클릭 대상을 찾지 못했다: {label} ({rect!r})")
        for kind in ("mousePressed", "mouseReleased"):
            await self.call(
                "Input.dispatchMouseEvent",
                {
                    "type": kind,
                    "x": rect["x"],
                    "y": rect["y"],
                    "button": "left",
                    "clickCount": 1,
                    "buttons": 1 if kind == "mousePressed" else 0,
                },
            )
        return rect


async def run_scheme(
    cdp: Cdp, scheme: str, src: str, file_sha: str, base_url: str, phase: str
) -> dict:
    # ⚠️ **배경 탭에서는 회차가 성립하지 않는다 (2026-09-06 실측).** 앞으로 끌어오지 않으면
    #    `Input.dispatchMouseEvent`가 페이지에 닿지 않고 `AudioContext.resume()`도 풀리지 않는다.
    #    증상은 `H-AE`와 글자 그대로 같다: `appHandlerAttached false` · `socketUrls []` ·
    #    `resumeLog[0].afterAwait null`(영원히 pending) · `active` 미도달.
    await cdp.call("Page.bringToFront")

    # ── 한 문서 = 한 세션 (§4-4). 모드마다 새로 연다.
    await cdp.call("Page.navigate", {"url": base_url})
    await asyncio.sleep(0.6)
    await cdp.call(
        "Emulation.setEmulatedMedia",
        {"features": [{"name": "prefers-color-scheme", "value": scheme}]},
    )
    await asyncio.sleep(0.3)

    # 앱이 상호작용 가능해질 때까지 기다린다.
    for _ in range(60):
        ready = await cdp.eval(
            "(() => document.readyState === 'complete' &&"
            " !!Array.from(document.querySelectorAll('button'))"
            "   .find(b => /학습 시작/.test(b.textContent||'')))()"
        )
        if ready:
            break
        await asyncio.sleep(0.25)
    else:
        raise SystemExit("학습 시작 버튼이 나타나지 않았다")

    reported = await cdp.eval(
        "matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'"
    )
    if reported != scheme:
        raise SystemExit(
            f"setEmulatedMedia 가 걸리지 않았다: 요청 {scheme} · 페이지 보고 {reported}"
        )

    # ── 3규약 1: 무해한 요소를 CDP로 한 번 클릭해 user activation 을 만든다 (H-AE).
    await cdp.click("document.querySelector('h1')", "h1 (user activation)")
    await asyncio.sleep(0.1)
    # ⚠️ **activation 을 추론하지 않고 직접 단정한다.** 없으면 `active` 미도달로 8초를 버리고
    #    원인이 화면 결함처럼 보인다 — 여기서 이름 있는 실패로 죽는 편이 낫다.
    activation = await cdp.eval(
        "(() => ({visible: document.visibilityState, focused: document.hasFocus(),"
        " hasBeenActive: !!(navigator.userActivation && navigator.userActivation.hasBeenActive),"
        " isActive: !!(navigator.userActivation && navigator.userActivation.isActive)}))()"
    )
    if not activation["hasBeenActive"]:
        raise SystemExit(
            f"user activation 이 생기지 않았다 — {activation!r}."
            " 탭이 배경이면 CDP 클릭이 페이지에 닿지 않는다"
        )

    # ── 계측 설치 + sha256 고정 (§10-3). 소스 사본은 하나이고 그것을 해싱하고 실행한다.
    await cdp.eval(f"window.__omySrc = {json.dumps(src)}; window.__omySrc.length")
    page_sha = await cdp.eval(
        "(async () => { const h = await crypto.subtle.digest('SHA-256',"
        " new TextEncoder().encode(window.__omySrc));"
        " return Array.from(new Uint8Array(h))"
        "   .map(b => b.toString(16).padStart(2,'0')).join(''); })()",
        await_promise=True,
    )
    if page_sha != file_sha:
        raise SystemExit(f"계측 전사 드리프트: 파일 {file_sha} · 페이지 {page_sha}")
    installed = await cdp.eval("eval(window.__omySrc)")
    if installed != "instrumented":
        raise SystemExit(f"계측 반환값이 'instrumented' 가 아니다: {installed!r} (§4-1 → ERROR)")

    # ── 학습 시작 클릭 → 그 직후 한 `eval` 안에서 전부 끝낸다 (§6 ⛔).
    await cdp.eval(f"window.__omyStopAfterPartial = {'true' if phase == 'partial' else 'false'}")
    t_click = time.monotonic()
    await cdp.click(
        "Array.from(document.querySelectorAll('button'))"
        "  .find(b => /학습 시작/.test(b.textContent||''))",
        "학습 시작",
    )
    data = await cdp.eval(
        MEASURE_JS.replace("PARTIAL_TEXT", json.dumps(PARTIAL_TEXT, ensure_ascii=False)).replace(
            "FINAL_TEXT", json.dumps(FINAL_TEXT, ensure_ascii=False)
        ),
        await_promise=True,
    )
    elapsed_ms = round((time.monotonic() - t_click) * 1000)

    shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
    suffix = "" if phase == "both" else f"-{phase}"
    shot_path = EVIDENCE / f"c2-{scheme}{suffix}.png"
    shot_path.write_bytes(base64.b64decode(shot["data"]))
    shot_ms = round((time.monotonic() - t_click) * 1000)

    data["emulated"] = scheme
    data["userActivation"] = activation
    data["instrumentSha256"] = page_sha
    data["clickToEvalReturnMs"] = elapsed_ms
    data["clickToScreenshotMs"] = shot_ms
    data["screenshot"] = str(shot_path.relative_to(ROOT))
    return data


async def main_async(args) -> int:
    src = INSTRUMENT.read_text(encoding="utf-8")
    file_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    ws_url, url = find_target(args.port, args.url_substring, args.url)
    print(f"target: {url}")
    print(f"instrument.js sha256(file): {file_sha}  ({len(src.encode('utf-8'))}B)")

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    results = []
    async with connect(ws_url, max_size=None) as ws:
        cdp = Cdp(ws)
        try:
            for scheme in args.schemes.split(","):
                print(f"\n=== {scheme} ===")
                results.append(
                    await run_scheme(cdp, scheme.strip(), src, file_sha, args.url, args.phase)
                )
        finally:
            # 에뮬레이션을 반드시 해제한다 — 남기면 이 탭이 계속 그 모드로 보인다.
            await cdp.call("Emulation.setEmulatedMedia", {"features": []})

    suffix = "" if args.phase == "both" else f"-{args.phase}"
    out = EVIDENCE / f"c2-render-hierarchy{suffix}.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1))

    for d in results:
        t = d["timing"]
        print(f"\n--- emulated={d['emulated']} (page reports {d['scheme']}) ---")
        print(
            f"  주입 전(active 도달 후) 접두 <p>: {d['beforeInject']['prefixedCount']}"
            f" · 사유 <p>: {d['beforeInject']['reasonPs']}"
            f" · 대기문구: {d['beforeInject']['waitingTextPresent']}"
        )
        print(f"  probe  muted={d['probe']['muted1']} (재판독 {d['probe']['muted2']})")
        print(f"  probe  fg   ={d['probe']['fg1']} (재판독 {d['probe']['fg2']})")
        print(
            f"  partial 줄  count={d['partial']['count']} color={d['partial']['color']}"
            f" → muted 일치: {d['partial']['color'] == d['probe']['muted1']}"
        )
        if d["final"] is None:
            print("  확정   줄  (이 회차는 partial 상태에서 멈췄다 — 판정에 쓰지 않는다)")
        else:
            print(
                f"  확정   줄  count={d['final']['count']} color={d['final']['color']}"
                f" → fg 일치: {d['final']['color'] == d['probe']['fg1']}"
                f" · partial 문구 잔존: {d['final']['partialTextStillPresent']}"
            )
        print(
            f"  timing active={t['activeMs']}ms partial+{t['partialInjectedAt']}ms"
            f" final+{t['finalInjectedAt']}ms total={t['totalMs']}ms"
            f" · 클릭→eval반환 {d['clickToEvalReturnMs']}ms"
            f" · 클릭→스크린샷 {d['clickToScreenshotMs']}ms"
        )
        print(
            f"  recv={d['omy']['recv']} injected={d['omy']['injected']}"
            f" snapshotCounts={d['omy']['snapshotCounts']}"
        )
        print(f"  shot -> {d['screenshot']}")

    if len(results) == 2:
        a, b = results
        print("\n--- A2-3 모드 대조 ---")
        print(
            f"  {a['emulated']} muted={a['probe']['muted1']}"
            f" · {b['emulated']} muted={b['probe']['muted1']}"
            f" → 서로 다름: {a['probe']['muted1'] != b['probe']['muted1']}"
        )
        print(
            f"  {a['emulated']} fg={a['probe']['fg1']} · {b['emulated']} fg={b['probe']['fg1']}"
            f" → 서로 다름: {a['probe']['fg1'] != b['probe']['fg1']}"
        )

    print(f"\nraw -> {out.relative_to(ROOT)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--url-substring", default="localhost:3000")
    ap.add_argument("--url", default="http://localhost:3000/")
    ap.add_argument("--schemes", default="light,dark")
    # `partial` 은 **눈으로 보기 위한 회차**다 — partial 상태에서 멈춰 창 안에서 스크린샷을 뜬다.
    ap.add_argument("--phase", choices=("both", "partial"), default="both")
    args = ap.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
