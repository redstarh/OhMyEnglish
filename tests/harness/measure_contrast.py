#!/usr/bin/env python3
"""색상 위계·대비를 두 색상 스킴에서 실측한다 (R1·R2).

`prefers-color-scheme`은 페이지 안에서 바꿀 수 없다 — CDP `Emulation.setEmulatedMedia`가
유일한 수단이다. superpowers-chrome 플러그인에는 그 액션이 없으므로 이 스크립트가
디버깅 포트로 직접 붙는다(플러그인이 띄운 Chrome을 그대로 쓴다).

전제: 대상 탭이 이미 원하는 화면을 띄우고 있어야 한다. 세션 화면을 측정하려면
큐를 멈춘 상태(부분 전사문이 남아 있는 상태)로 만들어 두고 이 스크립트를 돌린다.

실행:
    .venv/bin/python ../../tests/harness/measure_contrast.py --url-substring localhost:3000
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import urllib.request
from pathlib import Path

from websockets.asyncio.client import connect

HARNESS = Path(__file__).resolve().parent.parent.parent / ".harness"

# 페이지에서 실행할 측정식. 배경 대비를 WCAG 공식으로 계산한다.
MEASURE_JS = r"""
(() => {
  const lum = (rgb) => {
    const [r, g, b] = rgb.match(/[\d.]+/g).slice(0, 3).map(Number).map((v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * r + 0.7152 * g + 0.0722 * b;
  };
  const bgOf = (el) => {
    let node = el;
    while (node) {
      const c = getComputedStyle(node).backgroundColor;
      if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') return c;
      node = node.parentElement;
    }
    return getComputedStyle(document.body).backgroundColor;
  };
  const ratio = (fg, bg) => {
    const a = lum(fg), b = lum(bg);
    const [hi, lo] = a > b ? [a, b] : [b, a];
    return Number(((hi + 0.05) / (lo + 0.05)).toFixed(2));
  };
  const rows = [...document.querySelectorAll('main p, main h1')].map((el) => {
    const cs = getComputedStyle(el);
    const bg = bgOf(el);
    return {
      text: el.innerText.replace(/\s+/g, ' ').slice(0, 40),
      color: cs.color,
      bg,
      contrast: ratio(cs.color, bg),
    };
  });
  const root = getComputedStyle(document.documentElement);
  return {
    scheme: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
    tokens: {
      background: root.getPropertyValue('--background').trim(),
      foreground: root.getPropertyValue('--foreground').trim(),
      'foreground-muted': root.getPropertyValue('--foreground-muted').trim(),
      danger: root.getPropertyValue('--danger').trim(),
    },
    path: location.pathname,
    rows,
  };
})()
"""


def find_target(port: int, url_substring: str) -> tuple[str, str]:
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list", timeout=5) as fh:
        targets = json.load(fh)
    for t in targets:
        if t.get("type") == "page" and url_substring in t.get("url", ""):
            return t["webSocketDebuggerUrl"], t["url"]
    raise SystemExit(f"{url_substring} 을 띄운 page 타겟이 없다. 열린 탭: "
                     + ", ".join(t.get("url", "?") for t in targets))


async def measure(ws_url: str, schemes: list[str], shot_prefix: str | None) -> list[dict]:
    results = []
    async with connect(ws_url, max_size=None) as ws:
        msg_id = 0

        async def call(method: str, params: dict | None = None) -> dict:
            nonlocal msg_id
            msg_id += 1
            await ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
            while True:
                payload = json.loads(await ws.recv())
                if payload.get("id") == msg_id:
                    if "error" in payload:
                        raise SystemExit(f"{method} 실패: {payload['error']}")
                    return payload.get("result", {})

        for scheme in schemes:
            await call("Emulation.setEmulatedMedia",
                       {"features": [{"name": "prefers-color-scheme", "value": scheme}]})
            await asyncio.sleep(0.4)
            out = await call("Runtime.evaluate", {"expression": MEASURE_JS, "returnByValue": True})
            data = out["result"]["value"]
            data["emulated"] = scheme
            if shot_prefix:
                shot = await call("Page.captureScreenshot", {"format": "png"})
                path = Path(f"{shot_prefix}-{scheme}.png")
                path.write_bytes(base64.b64decode(shot["data"]))
                data["screenshot"] = str(path)
            results.append(data)

        # 에뮬레이션을 해제해 브라우저를 원래 상태로 돌려둔다.
        await call("Emulation.setEmulatedMedia", {"features": []})
    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--url-substring", default="localhost:3000")
    ap.add_argument("--schemes", default="light,dark")
    ap.add_argument("--shot-prefix", default=None)
    args = ap.parse_args()

    ws_url, url = find_target(args.port, args.url_substring)
    print(f"target: {url}")
    results = asyncio.run(measure(ws_url, args.schemes.split(","), args.shot_prefix))

    for data in results:
        print(f"\n=== emulated={data['emulated']} (page reports {data['scheme']}) {data['path']} ===")
        print("  tokens: " + " · ".join(f"{k}={v}" for k, v in data["tokens"].items()))
        for row in data["rows"]:
            flag = "OK " if row["contrast"] >= 4.5 else "AA!"
            print(f"  [{flag}] {row['contrast']:>6}:1  {row['color']:<22} {row['text']!r}")
        if "screenshot" in data:
            print(f"  shot -> {data['screenshot']}")

    out = HARNESS / "evidence" / "contrast.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1))
    print(f"\nraw -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
