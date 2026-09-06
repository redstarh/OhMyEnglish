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
- **한 문서에 세션 하나** — 모드마다 `Page.navigate`로 새 문서를 연다. `snapshots`가 페이지 수명
  전체에 쌓이기 때문이다. 근거는 `browser_leg.md` §5 A1-5 와 `instrument.js` 의
  `judgeFinalLines` docstring 이 소유한다.
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
  // ⚠️ **두 번 읽는 것은 A2-3의 음성 대조가 아니다 — 진단이다** (재검토 MEDIUM-4).
  //    같은 tick 안의 두 호출이라 **원리적으로 갈릴 수 없다.** A2-3의 실제 대조는
  //    ① 페이지가 보고한 스킴이 요청과 같은가(호출자가 회차를 죽인다) ② 모드가 하나면 미평가다.
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


def find_target(port: int, exact: str) -> tuple[str, str]:
    """**정확 일치 → 없으면 새 탭.** 부분일치 폴백은 두지 않는다.

    ⛔ **부분일치는 `browser_leg.md` §6이 금지한다 — 그리고 첫 판에 폴백으로 남아 있었다**
    (2026-09-06 재검토 MEDIUM-2). `localhost:3000` 부분일치는 열려 있던 `/results/<id>` 탭을
    먼저 잡아 **남의 화면을 하이재킹하고 그 위에서 `Page.navigate`로 지운다**(이 회차가 실제로
    관측하고 함정으로 적은 것이 바로 그것이다). docstring 이 위험을 경고하면서 **폴백이 살아 있는
    것은 밝히지 않아** 읽는 사람에게 정반대 인상을 줬다. → **경로를 지웠다.**
    (`measure_contrast.py`는 부분일치만 쓴다 — 거기서 물려받은 형태다.)
    """
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as fh:
        targets = json.load(fh)
    for t in targets:
        if t.get("type") == "page" and t.get("url", "") == exact:
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


FAILURE_DUMP_JS = r"""
(() => {
  const omy = window.__omy;
  const texts = (sel) => Array.from(document.querySelectorAll(sel))
    .map((e) => (e.textContent || "").trim().slice(0, 60));
  return {
    url: location.href,
    buttons: texts("button"),
    paragraphs: texts("p"),
    userActivation: navigator.userActivation
      ? { hasBeenActive: navigator.userActivation.hasBeenActive,
          isActive: navigator.userActivation.isActive }
      : null,
    visibility: document.visibilityState,
    focused: document.hasFocus(),
    // ⚠️ **아래 둘이 `H-AH`(배경 탭) 대 `H-AE`(합성 클릭)를 가르는 값이다** — 배경 탭이면
    //    `socketUrls`가 비어 있고 `resumeLog`가 1건(설치 시점)에 머문다.
    omy: omy ? {
      socketUrls: omy.meta.socketUrls.slice(),
      resumeLogLength: omy.meta.resumeLog.length,
      resumeLog: omy.meta.resumeLog,
      resumeErrors: omy.meta.resumeErrors,
      appHandlerAttached: omy.meta.appHandlerAttached,
      audioContextState: omy.meta.audioContextState,
      contextState: omy.contextState ? omy.contextState() : null,
      recv: JSON.parse(JSON.stringify(omy.recv)),
      sent: JSON.parse(JSON.stringify(omy.sent)),
      injected: omy.injected,
      snapshotCounts: omy.snapshots.map((s) => s.count),
    } : null,
  };
})()
"""


def classify_failure(o: dict) -> str:
    """실패 원인을 계측 상태에서 가른다. **순서가 곧 판별력이다** — 앞의 조건이 더 상류다.

    ⛔ **`socketUrls` 공백을 배경 탭의 지표로 쓰지 마라 — 팀리드가 직접 반례를 만들었다**
    (2026-09-06: 백엔드를 내린 회차에서 `socketUrls=[]` · `resumeLog` **2건** ·
    `appHandlerAttached=True`였다. 클릭은 정상으로 닿았고 소켓만 열리지 않았다).
    `meta.socketUrls`는 **`send`가 불릴 때만** 채워지므로 소켓이 열려도 비어 있을 수 있다.

    **가장 상류의 지표는 `resumeLog` 길이다** — 계측의 `getUserMedia` 대체본이 호출마다
    `tryResume()`를 부르므로, 설치 시점의 1건에 머물면 **`getUserMedia`가 불리지 않았다**
    = `startSession`이 시작조차 못 했다 = **클릭이 페이지에 닿지 않았다**(`H-AH`).
    """
    if len(o.get("resumeLog") or []) <= 1:
        return (
            "resumeLog 가 1건 이하다 → getUserMedia 가 안 불렸다 → **클릭이 페이지에 닿지 않았다**"
            " (`H-AH` 배경 탭. `Page.bringToFront` 와 userActivation 단정을 확인하라)"
        )
    if not o.get("appHandlerAttached"):
        return (
            "클릭은 닿았는데(resumeLog 2건 이상) 앱 핸들러가 없다 → **소켓 생성 전에 죽었다**"
            " (`VoiceIo.start` 실패 등. `resumeErrors` 와 화면의 `사유:` 를 읽어라)"
        )
    if (o.get("recv") or {}).get("session_started", 0) == 0:
        return (
            "소켓은 만들었는데 서버 프레임이 0건이다 → **백엔드가 없거나 연결이 실패했다**"
            " (실측 재현: :8002 를 내린 회차가 정확히 이 모양이었다. `/health` 를 확인하라)"
        )
    return (
        "클릭·소켓·서버 프레임 모두 정상이다 → `H-AH`도 백엔드 부재도 아니다."
        " `H-AE`(합성 클릭으로 `resume()` pending)나 세션 길이 쪽을 본다 —"
        " `resumeLog[*].afterAwait` 와 `contextState` 를 읽어라"
    )


async def dump_failure(cdp: Cdp, scheme: str, elapsed_ms: int) -> str:
    """실패한 회차의 계측 상태와 화면을 **파일로 남기고** 요약 한 덩이를 돌려준다.

    ⚠️ 이 함수 자체가 실패해도 원래 예외를 가려서는 안 된다 — 그래서 전부 감싸고 삼킨다.
    """
    lines = [f"실패 진단 (클릭 후 {elapsed_ms}ms) — H-AH/H-AE 판별용:"]
    diag: dict = {"scheme": scheme, "elapsedMs": elapsed_ms}
    try:
        diag["page"] = await cdp.eval(FAILURE_DUMP_JS)
    except BaseException as e:  # noqa: BLE001 — 진단이 원인을 가리면 안 된다
        diag["page"] = f"진단 eval 실패: {e}"
    try:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
        path = EVIDENCE / f"c2-{scheme}-failure.png"
        path.write_bytes(base64.b64decode(shot["data"]))
        diag["screenshot"] = str(path.relative_to(ROOT))
    except BaseException as e:  # noqa: BLE001
        diag["screenshot"] = f"스크린샷 실패: {e}"
    try:
        out = EVIDENCE / f"c2-{scheme}-failure.json"
        out.write_text(json.dumps(diag, ensure_ascii=False, indent=1), encoding="utf-8")
        lines.append(f"  → {out.relative_to(ROOT)} · {diag.get('screenshot')}")
    except BaseException as e:  # noqa: BLE001
        lines.append(f"  진단 파일 쓰기 실패: {e}")
    page = diag.get("page")
    if isinstance(page, dict):
        o = page.get("omy")
        if isinstance(o, dict):
            lines.append(
                f"  socketUrls={o.get('socketUrls')} · resumeLog {o.get('resumeLogLength')}건"
                f" · appHandlerAttached={o.get('appHandlerAttached')}"
                f" · contextState={o.get('contextState')}"
            )
            lines.append(f"  recv={o.get('recv')} · snapshotCounts={o.get('snapshotCounts')}")
            lines.append("  판별: " + classify_failure(o))
        else:
            lines.append("  window.__omy 가 없다 — 계측 설치 전에 죽었다")
        lines.append(
            f"  buttons={page.get('buttons')} · userActivation={page.get('userActivation')}"
        )
    else:
        lines.append(f"  {page}")
    return "\n".join(lines)


async def run_scheme(
    cdp: Cdp, scheme: str, src: str, file_sha: str, base_url: str, phase: str
) -> dict:
    # ⚠️ **배경 탭에서는 회차가 성립하지 않는다 (2026-09-06 실측).** 앞으로 끌어오지 않으면
    #    `Input.dispatchMouseEvent`가 페이지에 닿지 않고 `AudioContext.resume()`도 풀리지 않는다.
    #    증상은 `H-AE`와 글자 그대로 같다: `appHandlerAttached false` · `socketUrls []` ·
    #    `resumeLog[0].afterAwait null`(영원히 pending) · `active` 미도달.
    await cdp.call("Page.bringToFront")

    # ── 한 문서 = 한 세션 (`browser_leg.md` §5 A1-5). 모드마다 새로 연다.
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

    # ── 무해한 요소를 CDP로 한 번 클릭해 user activation 을 만든다 (`H-AE` 대응 ②).
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
    try:
        data = await cdp.eval(
            MEASURE_JS.replace(
                "PARTIAL_TEXT", json.dumps(PARTIAL_TEXT, ensure_ascii=False)
            ).replace("FINAL_TEXT", json.dumps(FINAL_TEXT, ensure_ascii=False)),
            await_promise=True,
        )
    except SystemExit as exc:
        failed_ms = round((time.monotonic() - t_click) * 1000)
        # ⛔ **실패한 회차가 판별에 필요한 바로 그 데이터를 버리면 안 된다** (재검토 MEDIUM-3).
        #    가장 흔한 실패는 `active` 8초 시간초과이고, 그때 `H-AH`(배경 탭)와 `H-AE`(합성 클릭)를
        #    가르는 값은 **`socketUrls` 공백 여부와 `resumeLog` 길이**다(`pitfalls.md` H-AH).
        #    첫 판은 그 시점에 바로 종료해 아티팩트를 0건 남겼고, 이 회차의 원인 판정은 팀리드가
        #    나중에 살아 있는 페이지를 손으로 들여다봐서 겨우 얻었다 — **스크립트가 자기 진단을
        #    재현하지 못했다.** 그래서 여기서 뜬다.
        raise SystemExit(f"{exc}\n\n{await dump_failure(cdp, scheme, failed_ms)}") from exc
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


def check_leg(d: dict, phase: str) -> tuple[int, list[str]]:
    """한 모드 회차의 단정을 **판정한다.** 반환은 `(검사한 단정 수, 어긋난 것들)`.

    ⛔ **이 함수가 없던 판이 리뷰에서 뚫렸다 (2026-09-06 · HIGH-1 · MEDIUM-1).** 그 판은 값을
    **인쇄만** 하고 아무것도 비교하지 않아서, 사람이 rgb 문자열을 눈으로 대조하지 않으면 PASS가
    공허해졌다. 구체적으로 두 구멍이었다:
    ① `browser_leg.md` §5 A2-2의 음성 대조 ②(**probe 두 값이 실제로 서로 다름**)가 코드에 **없었다**
       → `--foreground-muted`와 `--foreground`가 같은 값으로 회귀하면 세 단정이
       **전부 항진명제**가 된다
       (모드 간 차이는 그대로 성립하므로 A2-3도 못 잡는다).
    ② §6-0의 **"0이 아니면 그 회차는 ERROR"**가 게이트가 아니라 출력이었다.

    ⚠️ **검사한 수를 함께 돌려주는 것이 의도된 것이다** — 0건을 검사하고 통과를 단정하는 것이
    이 리포의 지배 실패 모드다(`browser_leg.md` §2-P5의 `assert srcs`와 같은 이유).
    """
    fails: list[str] = []
    checked = 0

    def need(cond: object, msg: str) -> None:
        nonlocal checked
        checked += 1
        if not cond:
            fails.append(msg)

    probe, before, partial, final = d["probe"], d["beforeInject"], d["partial"], d["final"]
    omy, recv = d["omy"], d["omy"]["recv"]

    # ── 0. 공허 통과 방어: 빈 값·비문자열이면 아래 등호가 전부 참이 될 수 있다.
    for key in ("muted1", "muted2", "fg1", "fg2"):
        need(
            isinstance(probe.get(key), str) and probe[key].startswith("rgb"),
            f"probe.{key} 가 rgb 문자열이 아니다: {probe.get(key)!r} — 등호가 공허해진다",
        )
    need(
        isinstance(partial.get("color"), str) and partial["color"].startswith("rgb"),
        f"partial.color 가 rgb 문자열이 아니다: {partial.get('color')!r}",
    )

    # ── 1. §6-0 — 주입 전(`active` 도달 후) 접두 `<p>`가 0개. **아니면 ERROR다.**
    need(
        before["prefixedCount"] == 0,
        f"§6-0 위반: 주입 전 접두 <p>가 {before['prefixedCount']}개다 (0이어야 한다)",
    )
    need(
        before["waitingTextPresent"] is True,
        "§6-0 의 0개가 공허하다: `대화를 기다리는 중...`이 없다"
        " — 컨테이너가 마운트되기 전에 쟀을 수 있다",
    )
    # ── 2. §6 — 창 이탈 판별. `사유:` `<p>`가 보이면 창을 넘긴 것이고 FAIL 이 아니라 ERROR 다.
    need(before["reasonPs"] == 0, f"창 이탈: 주입 전 `사유:` <p>가 {before['reasonPs']}개다")
    need(
        partial["reasonPs"] == 0,
        f"창 이탈: partial 판독 시점에 `사유:` <p>가 {partial['reasonPs']}개다",
    )

    # ── 3. A2-2 음성 대조 ② — **probe 두 값이 서로 다르다.** 같으면 위계 단정이 무의미하다.
    need(
        probe["muted1"] != probe["fg1"],
        f"A2-2 대조 ② 위반: muted 와 foreground 가 같은 값이다({probe['muted1']})"
        " — 위계 단정이 항진명제가 된다",
    )
    # ── 4. 진단 — 같은 모드 재판독이 같다. ⚠️ **A2-3의 음성 대조가 아니다**(재검토 MEDIUM-4):
    #    같은 tick 안의 두 호출은 갈릴 수 없어 판별력이 0이다. A2-3은 §10의 모드 대조가 낸다.
    need(
        probe["muted1"] == probe["muted2"],
        f"같은 모드 재판독이 갈렸다: muted {probe['muted1']} vs {probe['muted2']}",
    )
    need(
        probe["fg1"] == probe["fg2"],
        f"같은 모드 재판독이 갈렸다: fg {probe['fg1']} vs {probe['fg2']}",
    )

    # ── 5. A2-1 — partial 줄은 muted 토큰이고 정확히 1개다.
    need(
        partial["count"] == 1,
        f"A2-1: partial 주입 후 접두 <p>가 {partial['count']}개다 (1이어야 한다)",
    )
    need(
        partial["color"] == probe["muted1"],
        f"A2-1: partial 색 {partial['color']} != muted probe {probe['muted1']}",
    )

    # ── 6. A2-2 — 확정 줄은 foreground 토큰이고 partial 줄은 사라진다.
    if phase == "partial":
        need(final is None, "partial 회차인데 final 이 채워졌다 — 분기가 어긋났다")
        need(omy["injected"] == 1, f"partial 회차의 주입 수가 {omy['injected']}다 (1이어야 한다)")
    else:
        need(final is not None, "판정 회차인데 final 이 비었다 — A2-2 를 평가할 수 없다")
        if final is not None:
            need(
                final["count"] == 1,
                f"A2-2: final 주입 후 접두 <p>가 {final['count']}개다 (1이어야 한다)",
            )
            need(
                final["color"] == probe["fg1"],
                f"A2-2: 확정 색 {final['color']} != foreground probe {probe['fg1']}",
            )
            need(
                final["partialTextStillPresent"] is False,
                "A2-2: final 뒤에도 partial 문구가 문서에 남아 있다"
                " — setPartialLine(null) 경로가 죽었다",
            )
            need(
                final["reasonPs"] == 0,
                f"창 이탈: final 판독 시점에 `사유:` <p>가 {final['reasonPs']}개다",
            )
        need(omy["injected"] == 2, f"판정 회차의 주입 수가 {omy['injected']}다 (2여야 한다)")

    # ── 7. 주입 창의 전제 — `stub_unresponsive` 이므로 **경쟁 프레임이 0**이다(§6 주입 창).
    #    `stub` 으로 잘못 띄우면 실물 partial/final 이 같은 상태를 덮어 측정이 조용히 무의미해진다.
    need(
        recv["partial"] == 0,
        f"경쟁 프레임: recv.partial={recv['partial']} — 어댑터가 stub_unresponsive 가 아니다",
    )
    need(
        recv["final"] == 0,
        f"경쟁 프레임: recv.final={recv['final']} — 어댑터가 stub_unresponsive 가 아니다",
    )
    # ── 8. 한 문서에 세션 하나(`browser_leg.md` §5 A1-5) + 계측이 살아 있었다는 증거.
    need(
        recv["session_started"] == 1,
        f"한 문서에 세션이 하나여야 한다: session_started={recv['session_started']}",
    )
    need(
        omy["appHandlerAttached"] is True,
        "앱 onmessage 핸들러가 붙지 않았다 — 주입 경로가 성립하지 않는다",
    )
    # ── 9. 초과 렌더 검출 — C2 회차에는 어느 시점에도 접두 `<p>`가 1개를 넘지 않는다.
    counts = omy["snapshotCounts"]
    need(bool(counts), "snapshotCounts 가 비었다 — 계측이 적립하지 않았다")
    need(
        max(counts or [0]) <= 1,
        f"초과 렌더: snapshotCounts 최대가 {max(counts or [0])}다 (1 이하여야 한다)",
    )
    # ── 10. 모드 에뮬레이션이 실제로 걸렸다.
    need(
        d["scheme"] == d["emulated"],
        f"모드 불일치: 요청 {d['emulated']} · 페이지 보고 {d['scheme']}",
    )

    return checked, fails


def check_cross(results: list[dict]) -> tuple[int, list[str]]:
    """A2-3 — **모드 간** 토큰이 다르다.

    두 모드가 없으면 평가할 수 없고 **그것은 PASS 가 아니다**(§10).
    """
    schemes = [r["emulated"] for r in results]
    if len(set(schemes)) < 2:
        return 0, [
            f"A2-3 미평가: 모드가 {schemes} 하나뿐이다 — 판별력 미확인은 PASS 가 아니다(§10)"
        ]
    a, b = results[0], results[1]
    fails = []
    if a["probe"]["muted1"] == b["probe"]["muted1"]:
        fails.append(
            f"A2-3: 두 모드의 muted 가 같다({a['probe']['muted1']}) — 모드 전환이 안 걸렸다"
        )
    if a["probe"]["fg1"] == b["probe"]["fg1"]:
        fails.append(f"A2-3: 두 모드의 foreground 가 같다({a['probe']['fg1']})")
    return 2, fails


async def main_async(args) -> int:
    src = INSTRUMENT.read_text(encoding="utf-8")
    file_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    ws_url, url = find_target(args.port, args.url)
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

    # ── 판정 — 인쇄로 끝내지 않는다. 어긋나면 **비영 종료**다.
    if not results:
        raise SystemExit("회차 결과가 0건이다 — 0건을 검사하고 통과를 단정하지 않는다")
    checked, fails = 0, []
    for d in results:
        n, f = check_leg(d, args.phase)
        checked += n
        fails += [f"[{d['emulated']}] {m}" for m in f]
    n, f = check_cross(results)
    checked += n
    fails += f

    print(f"\n--- 판정 (단정 {checked}건 검사) ---")
    if fails:
        for m in fails:
            print(f"  FAIL  {m}")
        raise SystemExit(f"판정 FAIL — 어긋난 단정 {len(fails)}건 / 검사 {checked}건")
    print(f"  PASS  {checked}건 전건 통과")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--url", default="http://localhost:3000/")
    ap.add_argument("--schemes", default="light,dark")
    # `partial` 은 **눈으로 보기 위한 회차**다 — partial 상태에서 멈춰 창 안에서 스크린샷을 뜬다.
    ap.add_argument("--phase", choices=("both", "partial"), default="both")
    args = ap.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
