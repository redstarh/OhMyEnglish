"""P계층 앱 경로 드라이버 — 픽스처 WAV 한 개를 세션의 «첫» 발화로 흘린다.

⛔ **왜 이 파일이 필요한가.** `TASK-65` 가 *"파일이 아니라 순서가 ASR 언어를 정한다"* 를 확정했고
`scenarios-P-pronunciation.md` §3.2 가 그래서 **`p2k` 를 세션의 첫 발화로 줄 것**을 요구한다.
그런데 앱 경로로 픽스처를 흘리는 실행체가 리포에 없었다 — `TASK-78` 의 브라우저 회차는 대화형
왕복으로 했고 스크립트가 남지 않았다(회차 기록 `2026-09-10-task78-app-path.md` §1 에 절차만 있다).
`c1_session_walkthrough.py` 는 `VOICE_ADAPTER=stub` 전용이라 실물 Nova 를 지나가지 않는다.

**계측은 `instrument.js` 를 그대로 쓴다**(sha256 대조 포함) — 새 계측을 만들지 않는다.
이 파일이 더하는 것은 셋뿐이다:

1. **마이크를 톤에서 픽스처 WAV 로 바꾼다.** `instrument.js` 의 합성 마이크는 220Hz 톤이라
   ASR 관측에 쓸 수 없다. 교체본은 instrument 의 `getUserMedia` 를 **먼저 호출해**
   `meta.resumeLog` 진단을 살려 둔 뒤 자기 스트림을 돌려준다.
2. **`recv` 에 키를 더한다.** `instrument.js` 의 계수기는 자기 키만 세므로(`hasOwnProperty` 게이트)
   `pronunciation`·`speech_start`·`speech_end`·`interrupted` 가 **조용히 0으로 보인다.**
   ⚠️ 파일을 고치지 않고 런타임에 키를 더한다 — 그러면 그 프레임이 실제로 오는지 관측된다.
3. **판정하지 않는다.** 이 드라이버는 관측만 하고 `PASS`/`FAIL` 을 계산하지 않는다 — P1·P4 의 단정은
   전사문 내용과 agent 발화라서 회차가 원자료를 읽고 판정한다(`scenarios-P-pronunciation.md` §4).

⛔ **어댑터는 `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` 여야 한다**(`H-AS`·`H-AT`).
이 파일은 그것을 세우지 않는다 — **호출자의 몫이다**(`browser_leg.md` §8-⑤ 예외).

⛔ **한 문서(페이지 로드)에 세션 하나만 돌린다.** `finalLinesAtTerminal` 과 `startedSessionId` 가
first-wins 라서 두 번째 세션이 첫 세션의 값을 조용히 덮는다. 그래서 이 스크립트는 실행마다
`Page.navigate` 로 새 문서를 열고 **세션 1개만** 만든다.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

# 마이크 교체 — 픽스처 WAV 를 합성 스트림으로 흘린다.
#
# ⚠️ **`sampleRate` 를 픽스처와 맞춘다(16000).** 앱은 자기 `AudioContext` 를 16kHz 로 만들므로
#    (`lib/audio.ts:129`) 여기서 48kHz 기본값을 쓰면 16k→48k→16k 로 두 번 리샘플된다.
#    `TASK-65` 가 그것을 P4 미재현의 원인에서 배제했지만 **배제된 것을 일부러 다시 넣을 이유는
#    없다** — 스파이크(한글 전사가 나오는 경로)는 리샘플이 0회다. 실제 값은 관측에 기록한다.
MIC_JS = r"""
(async () => {
  const omy = window.__omy;
  if (!omy) throw new Error("계측이 걸려 있지 않다 (window.__omy 부재)");

  // instrument.js 가 이미 갈아 둔 것을 보관한다 — 제스처 안에서 함께 불러 resumeLog 를 살린다.
  const instrumented = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);

  const ctx = new AudioContext({ sampleRate: FIXTURE_RATE });
  const res = await fetch(FIXTURE_URL, { cache: "no-store" });
  if (!res.ok) throw new Error("픽스처 fetch 실패: " + FIXTURE_URL + " → " + res.status);
  const bytes = await res.arrayBuffer();
  const buf = await ctx.decodeAudioData(bytes);
  const destination = ctx.createMediaStreamDestination();

  omy.fixture = {
    url: FIXTURE_URL,
    bytes: bytes.byteLength,
    ctxSampleRate: ctx.sampleRate,
    bufferSampleRate: buf.sampleRate,
    durationSec: Math.round(buf.duration * 1000) / 1000,
    startedAt: null,
    endedAt: null,
    micCalls: 0,
  };

  navigator.mediaDevices.getUserMedia = async (...args) => {
    omy.fixture.micCalls += 1;
    // instrument 의 것을 먼저 부른다 — `tryResume()` 기록(meta.resumeLog)이 진단의 정본이다.
    // 반환 스트림은 버린다(톤이다). 실패해도 이 경로를 막지 않는다.
    try { await instrumented(...args); } catch (e) { omy.fixture.instrumentedError = String(e); }
    await ctx.resume();
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.connect(destination);
    src.onended = () => { omy.fixture.endedAt = Math.round(performance.now()); };
    src.start();
    omy.fixture.startedAt = Math.round(performance.now());
    // ⚠️ WAV 뒤로는 무음이 흐른다 — 그것이 Nova 의 endpointing 을 발동시킨다.
    return destination.stream;
  };

  // `recv` 키 보강 — instrument 의 계수기는 자기 키만 센다.
  for (const k of ["pronunciation", "speech_start", "speech_end", "interrupted"]) {
    if (!(k in omy.recv)) omy.recv[k] = 0;
  }
  return "mic-ready";
})()
"""

# 세션 관통 — 한 `eval` 안에서 대기하고 관측을 돌려준다(§6 의 라운드트립 규약).
WALK_JS = r"""
(async () => {
  const omy = window.__omy;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const t0 = performance.now();
  const log = [];

  // 앱 핸들러 부착을 기다린다 — 없으면 아래 대기가 「영원히 0」으로 보인다.
  const attachDeadline = Date.now() + 8000;
  while (!(omy.meta && omy.meta.appHandlerAttached)) {
    if (Date.now() > attachDeadline) {
      throw new Error("앱 onmessage 핸들러가 8초 안에 붙지 않았다 (meta=" +
        JSON.stringify(omy.meta || null) + ")");
    }
    await sleep(100);
  }
  log.push({ at: Math.round(performance.now() - t0), what: "appHandlerAttached" });

  // ① 사용자 final 을 기다린다 — 픽스처가 끝나고 무음이 endpointing 을 발동시킨 결과다.
  const finalDeadline = Date.now() + WALK_TIMEOUT_MS;
  while (Date.now() < finalDeadline) {
    if (omy.recv.final >= 1 || omy.recv.session_failed > 0) break;
    await sleep(150);
  }
  log.push({ at: Math.round(performance.now() - t0), what: "first-final-or-timeout",
             final: omy.recv.final, failed: omy.recv.session_failed });

  // ② agent 응답이 잦아들기를 기다린다 — `audio`·`final` 계수가 SETTLE_MS 동안 안 늘면 끝으로 본다.
  let lastChange = Date.now();
  let sig = omy.recv.final + ":" + omy.recv.audio + ":" + omy.recv.partial;
  const settleDeadline = Date.now() + SETTLE_TIMEOUT_MS;
  while (Date.now() < settleDeadline) {
    await sleep(200);
    const now = omy.recv.final + ":" + omy.recv.audio + ":" + omy.recv.partial;
    if (now !== sig) { sig = now; lastChange = Date.now(); }
    if (Date.now() - lastChange >= SETTLE_MS) break;
    if (omy.recv.session_failed > 0) break;
  }
  log.push({ at: Math.round(performance.now() - t0), what: "settled", recv: { ...omy.recv } });

  return JSON.stringify({
    phase: "walk",
    recv: { ...omy.recv },
    sent: { ...omy.sent },
    startedSessionId: omy.startedSessionId,
    fixture: omy.fixture,
    started: { count: omy.started.count, when: omy.started.when },
    snapshots: omy.snapshots,
    contextState: omy.contextState ? omy.contextState() : null,
    meta: omy.meta,
    lines: omy.snapshotNow(),
    url: location.href,
    log,
  });
})()
"""

# 종료 클릭 뒤 — 종단 프레임과 결과 화면 도달을 기다리고 화면을 읽는다.
END_JS = r"""
(async () => {
  const omy = window.__omy;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const deadline = Date.now() + END_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (/\/results\//.test(location.href) && omy.recv.session_ended + omy.recv.session_failed > 0) {
      break;
    }
    await sleep(200);
  }
  // 결과 화면의 첫 판독이 끝날 시간을 준다(폴링이 있다).
  await sleep(RESULT_SETTLE_MS);
  const main = document.querySelector("main");
  const texts = (sel) => Array.from(document.querySelectorAll(sel))
    .map((e) => (e.textContent || "").trim());
  return JSON.stringify({
    phase: "end",
    url: location.href,
    recv: { ...omy.recv },
    sent: { ...omy.sent },
    finalLinesAtTerminal: omy.finalLinesAtTerminal,
    resultParagraphs: main ? texts("main p") : null,
    resultH1: texts("h1"),
    buttons: texts("button"),
    mainInnerHTML: main ? main.innerHTML : null,
  });
})()
"""


async def run(args: argparse.Namespace) -> dict[str, Any]:
    from c2_render_hierarchy import INSTRUMENT, Cdp, find_target  # noqa: PLC0415
    from websockets.asyncio.client import connect  # noqa: PLC0415

    src = INSTRUMENT.read_text(encoding="utf-8")
    file_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    print(f"instrument.js sha256(파일): {file_sha}  ({len(src.encode('utf-8'))}B)")

    ws_url, url = find_target(args.port, args.url)
    print(f"대상 탭: {url}")
    out: dict[str, Any] = {"instrument_sha256": file_sha, "target_url": url}

    async with connect(ws_url, max_size=None) as ws:
        cdp = Cdp(ws)
        await cdp.call("Page.bringToFront")
        nav = await cdp.call("Page.navigate", {"url": args.url})
        if nav.get("errorText"):
            raise SystemExit(f"navigate 실패: {nav['errorText']}")
        await cdp.eval(
            "new Promise(r => document.readyState === 'complete'"
            " ? r(1) : window.addEventListener('load', () => r(1)))",
            await_promise=True,
        )

        # 계측 설치 — sha256 을 페이지 안에서 다시 계산해 전사·캐시 드리프트를 배제한다(§10-3).
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
            raise SystemExit(f"계측 반환값이 'instrumented' 가 아니다: {installed!r}")
        out["instrument_page_sha256"] = page_sha

        mic = await cdp.eval(
            MIC_JS.replace("FIXTURE_URL", json.dumps(f"/harness/{args.wav}")).replace(
                "FIXTURE_RATE", str(args.fixture_rate)
            ),
            await_promise=True,
        )
        if mic != "mic-ready":
            raise SystemExit(f"마이크 교체 반환값이 'mic-ready' 가 아니다: {mic!r}")
        out["fixture_pre"] = json.loads(await cdp.eval("JSON.stringify(window.__omy.fixture)"))
        print(f"마이크 교체 완료: {out['fixture_pre']}")

        # ⛔ CDP 실제 입력이다 — `eval` 의 `element.click()` 은 user activation 을 만들지 않는다.
        await cdp.click(
            "Array.from(document.querySelectorAll('button'))"
            "  .find(b => /학습 시작/.test(b.textContent||''))",
            "학습 시작",
        )
        act = json.loads(
            await cdp.eval(
                "JSON.stringify({hasBeenActive: navigator.userActivation.hasBeenActive})"
            )
        )
        if not act.get("hasBeenActive"):
            raise SystemExit(
                f"user activation 이 생기지 않았다 — {act!r}. 배경 탭이면 CDP 클릭이 닿지 않는다"
                " (H-AE). page 탭이 여러 개면 비결정적으로 실패한다"
            )
        out["user_activation"] = act

        walk = json.loads(
            await cdp.eval(
                WALK_JS.replace("WALK_TIMEOUT_MS", str(args.walk_timeout_ms))
                .replace("SETTLE_TIMEOUT_MS", str(args.settle_timeout_ms))
                .replace("SETTLE_MS", str(args.settle_ms)),
                await_promise=True,
            )
        )
        out["walk"] = walk
        print(f"관통: recv={walk['recv']} · session_id={walk['startedSessionId']}")
        print(f"      화면 줄={walk['lines']}")

        # 세션 화면 스크린샷 — 결과 화면으로 넘어가기 «전» 이다.
        if args.shot_prefix:
            shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
            p = Path(f"{args.shot_prefix}-session.png")
            p.write_bytes(base64.b64decode(shot["data"]))
            out["screenshot_session"] = str(p)
            print(f"스크린샷: {p}")

        end_click: dict[str, Any] = {"attempted": True, "ok": False, "error": None}
        out["end_click"] = end_click
        try:
            await cdp.click(
                "Array.from(document.querySelectorAll('button'))"
                "  .find(b => /학습 종료/.test(b.textContent||''))",
                "학습 종료",
            )
            end_click["ok"] = True
        except SystemExit as exc:
            # ⚠️ 여기서 죽지 않는다 — 앞서 얻은 관통 관측을 잃는 것이 더 비싸다(`H-AO`).
            end_click["error"] = str(exc)

        end = json.loads(
            await cdp.eval(
                END_JS.replace("END_TIMEOUT_MS", str(args.end_timeout_ms)).replace(
                    "RESULT_SETTLE_MS", str(args.result_settle_ms)
                ),
                await_promise=True,
            )
        )
        out["end"] = end
        print(f"종료: url={end['url']} · recv={end['recv']}")

        if args.shot_prefix:
            shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
            p = Path(f"{args.shot_prefix}-results.png")
            p.write_bytes(base64.b64decode(shot["data"]))
            out["screenshot_results"] = str(p)
            print(f"스크린샷: {p}")

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="P계층 앱 경로 드라이버 (픽스처를 첫 발화로 흘린다)")
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--url", default="http://localhost:3000/")
    ap.add_argument("--wav", required=True, help="public/harness/ 아래 파일명 (예: p2k.wav)")
    ap.add_argument("--fixture-rate", type=int, default=16000)
    ap.add_argument("--walk-timeout-ms", type=int, default=45000)
    ap.add_argument("--settle-timeout-ms", type=int, default=60000)
    ap.add_argument("--settle-ms", type=int, default=6000)
    ap.add_argument("--end-timeout-ms", type=int, default=20000)
    ap.add_argument("--result-settle-ms", type=int, default=4000)
    ap.add_argument("--shot-prefix", help="스크린샷 경로 접두 (없으면 안 찍는다)")
    ap.add_argument("--out", help="관측을 JSON 으로 쓸 경로")
    args = ap.parse_args()

    observed = asyncio.run(run(args))
    if args.out:
        Path(args.out).write_text(
            json.dumps(observed, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        print(f"기록: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
