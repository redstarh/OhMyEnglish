"""쉐도잉 낭독 판정을 브라우저에서 태우는 드라이버 (`TASK-210` · 결정 131).

설계: `docs/design/2026-09-18-read-aloud-judgment-design.md`.

⛔ **`p_app_path.py` 와 다른 흐름이다.** 그 드라이버는 「말하기」 세션을 태우고 `instrument.js` 의
`window.__omy` 에 마이크 대체가 매여 있다. 여기서 재는 것은 **낭독 흐름과 판정 화면**이므로 계측을
설치하지 않고 마이크 대체와 DOM 관측만 한다 — 필요 없는 의존을 늘리지 않는다.

⛔ **쿼리 없이 `/` 로 열고 화면의 「쉐도잉」 버튼을 누른다**(`H-CC`). `?mode=…` 로 열면 페이지 로드
즉시 `getUserMedia` 가 불려 마이크 대체를 심을 틈이 없다.
⛔ **`localhost:3000` 으로 연다**(`H-CA`). `127.0.0.1` 은 Next dev 가 다른 origin 으로 보고 dev
리소스를 막아 hydration 이 아예 안 된다.
⛔ **전용 Chrome 이어야 한다**(`H-BD`): `--remote-debugging-port=9333 --user-data-dir=<임시>
--use-fake-device-for-media-stream --use-fake-ui-for-media-stream
--autoplay-policy=no-user-gesture-required`.
⛔ **백엔드는 `VOICE_ADAPTER=nova` · `WORKER_ENABLED=false` 여야 한다** — 이 파일은 세우지 않는다.
⚠️ **`stub` 으로 돌리면 판정이 503 이고 화면이 「지금은 낭독 판정을 쓸 수 없어요」를 보인다**
(`TASK-213`). 그 갈래를 일부러 볼 때는 `--judge-timeout-s` 를 줄인다 — 낱말은 영원히 뜨지 않는다.

⛔ **세션 ID 를 시각창으로 찾지 않는다.** 판정 요청 URL 이
`/api/sessions/<sid>/recordings/<uid>/readback` 이므로 `fetch` 를 감싸 그 주소를 그대로 잡는다 —
teardown 대상의 정본이 그것이다(`TASK-193`).
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import re
import sys
from pathlib import Path
from typing import Any

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))

MIC_JS = """
(async () => {
  // 낭독 오디오를 마이크로 흘린다. `--use-fake-device-for-media-stream` 의 가짜 장치는 톤이라
  // ASR 에 쓸 수 없으므로 픽스처 WAV 를 디코드해 MediaStreamDestination 으로 내보낸다.
  const ctx = new AudioContext({ sampleRate: 16000 });
  const res = await fetch("FIXTURE_URL", { cache: "no-store" });
  if (!res.ok) throw new Error("픽스처 fetch 실패: " + res.status);
  const buffer = await ctx.decodeAudioData(await res.arrayBuffer());
  const destination = ctx.createMediaStreamDestination();
  window.__rb = {
    gumCalls: 0,
    played: 0,
    durationSec: Math.round(buffer.duration * 1000) / 1000,
    ctxRate: ctx.sampleRate,
    bufferRate: buffer.sampleRate,
    fetches: [],
  };
  // ⛔ 원본 `fetch` 를 감싸 판정 요청 주소를 잡는다 — 세션·발화 ID 의 정본이다.
  const originalFetch = window.fetch.bind(window);
  window.fetch = (...args) => {
    try {
      window.__rb.fetches.push(String(args[0]));
    } catch (_) {}
    return originalFetch(...args);
  };
  navigator.mediaDevices.getUserMedia = async () => {
    window.__rb.gumCalls += 1;
    await ctx.resume();
    return destination.stream;
  };
  window.__rbPlay = async () => {
    await ctx.resume();
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(destination);
    source.start();
    window.__rb.played += 1;
    return buffer.duration;
  };
  return "mic-installed";
})()
"""

BUTTONS_JS = """
Array.from(document.querySelectorAll('button')).map(b => ({
  text: (b.textContent || '').trim(),
  disabled: b.disabled,
}))
"""

# 판정 결과를 화면에서 읽는다. ⛔ **색만 읽지 않는다** — 화면이 색과 장식 둘로 가르므로
# `text-decoration-line` 도 함께 읽어야 「다름」과 「빠짐」이 갈린다.
WORDS_JS = """
(() => {
  const spans = Array.from(document.querySelectorAll('section p span'));
  return spans.map(s => {
    const st = getComputedStyle(s);
    return {
      text: (s.textContent || '').trim(),
      color: st.color,
      decoration: st.textDecorationLine,
    };
  });
})()
"""

NOTICES_JS = """
Array.from(document.querySelectorAll('section p')).map(p => (p.textContent || '').trim())
"""


async def _wait_for_button(cdp: Any, label: str, *, timeout_s: float) -> list[dict[str, Any]]:
    """그 라벨의 버튼이 뜰 때까지 기다린다. 못 뜨면 **그때의 버튼 목록을 담아** 죽는다."""
    deadline = asyncio.get_running_loop().time() + timeout_s
    buttons: list[dict[str, Any]] = []
    while asyncio.get_running_loop().time() < deadline:
        buttons = await cdp.eval(BUTTONS_JS)
        if any(label in b["text"] for b in buttons):
            return buttons
        await asyncio.sleep(0.5)
    raise SystemExit(f"「{label}」 버튼이 {timeout_s}초 안에 뜨지 않았다 — 그때 화면: {buttons}")


async def run(args: argparse.Namespace) -> dict[str, Any]:
    from c2_render_hierarchy import Cdp, find_target  # noqa: PLC0415
    from websockets.asyncio.client import connect  # noqa: PLC0415

    ws_url, url = find_target(args.port, args.url)
    print(f"대상 탭: {url}")
    out: dict[str, Any] = {"target_url": url}

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

        installed = await cdp.eval(
            MIC_JS.replace("FIXTURE_URL", args.fixture_url), await_promise=True
        )
        if installed != "mic-installed":
            raise SystemExit(f"마이크 대체 실패: {installed!r}")
        out["mic"] = await cdp.eval("window.__rb")
        print(f"마이크 대체: {out['mic']['durationSec']}초 · rate {out['mic']['bufferRate']}")

        await cdp.click(
            "Array.from(document.querySelectorAll('button'))"
            "  .find(b => /쉐도잉/.test(b.textContent||''))",
            "쉐도잉",
        )
        out["buttons_after_entry"] = await _wait_for_button(
            cdp, "따라 읽기", timeout_s=args.session_timeout_s
        )
        print(f"세션 화면: {[b['text'] for b in out['buttons_after_entry']]}")

        await cdp.click(
            "Array.from(document.querySelectorAll('button'))"
            "  .find(b => /따라 읽기/.test(b.textContent||''))",
            "따라 읽기",
        )
        played = await cdp.eval("window.__rbPlay()", await_promise=True)
        print(f"낭독 흘림: {played}초 — 끝까지 기다린다")
        await asyncio.sleep(float(played) + args.tail_wait_s)
        await cdp.click(
            "Array.from(document.querySelectorAll('button'))"
            "  .find(b => /읽기 끝/.test(b.textContent||''))",
            "읽기 끝",
        )

        out["buttons_after_recording"] = await _wait_for_button(
            cdp, "내 낭독 듣기", timeout_s=args.saved_timeout_s
        )
        print(f"낭독 저장 뒤: {[b['text'] for b in out['buttons_after_recording']]}")

        await cdp.click(
            "Array.from(document.querySelectorAll('button'))"
            "  .find(b => /낭독 판정 보기/.test(b.textContent||''))",
            "낭독 판정 보기",
        )
        # 판정은 첫 호출에 Nova 를 한 번 타므로 몇 초 걸린다 — 낱말이 뜰 때까지 기다린다.
        deadline = asyncio.get_running_loop().time() + args.judge_timeout_s
        words: list[dict[str, Any]] = []
        while asyncio.get_running_loop().time() < deadline:
            words = await cdp.eval(WORDS_JS)
            if words:
                break
            await asyncio.sleep(0.5)
        out["words"] = words
        out["notices"] = await cdp.eval(NOTICES_JS)
        out["mic_after"] = await cdp.eval("window.__rb")
        print(f"낱말 {len(words)}개 · 안내 {out['notices']}")

        fetches = out["mic_after"]["fetches"]
        readback = [u for u in fetches if "/readback" in u]
        out["readback_urls"] = readback
        if readback:
            matched = re.search(
                r"/api/sessions/([0-9a-f-]+)/recordings/([0-9a-f-]+)/readback", readback[0]
            )
            if matched:
                out["session_id"] = matched.group(1)
                out["utterance_id"] = matched.group(2)
                print(f"세션 {out['session_id']} · 발화 {out['utterance_id']}")

        if args.shot:
            shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
            Path(args.shot).write_bytes(base64.b64decode(shot["data"]))
            out["screenshot"] = args.shot
            print(f"스크린샷: {args.shot}")

        # ⛔ 세션을 닫는다 — 열어 둔 채 떠나면 서버가 계속 오디오를 받는다.
        await cdp.click(
            "Array.from(document.querySelectorAll('button'))"
            "  .find(b => /학습 종료/.test(b.textContent||''))",
            "학습 종료",
        )
        await asyncio.sleep(args.tail_wait_s)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="쉐도잉 낭독 판정 드라이버 (TASK-210)")
    ap.add_argument("--port", type=int, default=9333)
    ap.add_argument("--url", default="http://localhost:3000/")
    ap.add_argument("--fixture-url", default="/harness/readback.wav")
    ap.add_argument("--session-timeout-s", type=float, default=45.0)
    ap.add_argument("--saved-timeout-s", type=float, default=30.0)
    ap.add_argument("--judge-timeout-s", type=float, default=60.0)
    ap.add_argument("--tail-wait-s", type=float, default=3.0)
    ap.add_argument("--shot", help="스크린샷 경로 (없으면 안 찍는다)")
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
