"""C1 실행체 — 세션 관통(A1-4·A1-5·A1-7)을 한 프로세스 안에서 관통·판독·판정한다.

⛔ **왜 실행체가 필요한가** (`TASK-52`). `TASK-30` 회차 2 를 위임했다가 검증자가 산출물 직전에
API 오류로 죽어 **관측값을 전부 잃었다**(`H-AO` 재발 · 2026-09-09). 무결성은 지켜졌으나 A1-4 의
`when` 배열 · A1-5 의 6줄 · A1-7 의 `sent` 계수가 사라졌다. C1 은 단정이 9건으로 가장 많아 유실
비용이 가장 크다. `TASK-49` 가 C5 에서 같은 판단을 내렸고 이것은 그 형태를 잇는다.

**판정은 순수 함수(`check_c1`)에 있고 CDP 는 관측만 한다.** 그래서 `test_c1_gates.py` 가 브라우저
없이 판별력을 고정한다.

⛔ **어댑터는 `VOICE_ADAPTER=stub` 이다**(`browser_leg.md` §5 C1). 다른 모드로 돌리면 픽스처 3턴이
나오지 않아 A1-4·A1-5 의 기대값이 성립하지 않는다.
"""

from __future__ import annotations

from typing import Any, cast

# ⓐ 픽스처 연역 — `fixtures.py:FIXTURE_TURNS` 가 3턴이고 `enqueueAudio` 가 프레임당 노드 1개를
# 만들어 `start` 를 1회 부른다. ⚠️ 픽스처가 바뀌면 `test_c1_gates.py` 가 먼저 죽는다(의도).
EXPECTED_START_CALLS = 3

# ⓐ 3턴 × (agent 1 + user 1). `질문: `/`답변: ` 접두 `<p>` 수와 같다.
EXPECTED_FINAL_LINES = 6

# `judgeFinalLines` 의 `verdict` 분류 — 정본은 `instrument.js:496~516` 이다.
# ⛔ **앱 결함과 측정 불가를 섞지 않는다.** 섞으면 하네스 사고가 앱 결함으로 보고되고,
# 그것이 `browser_leg.md` §4 가 「해석을 한 번 접는」 이유다.
APP_DEFECT_VERDICTS = frozenset(
    {
        "APP_UNDER_RENDER",
        "APP_EXCESS_RENDER",
        "APP_CONTENT_MISMATCH",
        "REMOUNT_OR_TWO_SESSIONS",
    }
)
UNMEASURABLE_VERDICTS = frozenset(
    {
        "UNMEASURABLE_NO_TERMINAL",
        "HARNESS_TRUNCATED_ACCRUAL",
        "HARNESS_MISSED_TERMINAL_MOMENT",
    }
)


def check_c1(observed: dict[str, Any]) -> tuple[int, list[str]]:
    """관측을 판정한다. 반환은 `(센 단정 수, 어긋남 메시지)`.

    ⛔ **빠진 키를 통과로 만들지 않는다** — 그러면 실행체가 아무것도 안 해도 `PASS` 가 된다.
    """
    checked = 0
    fails: list[str] = []
    silent = bool(observed.get("silent_mic"))

    # ── A1-4 재생 시작 ──────────────────────────────────────────────────────
    started_raw = observed.get("started")
    started = cast(dict[str, Any], started_raw) if isinstance(started_raw, dict) else None
    if started is None:
        fails.append("관측에 started 가 없다 — A1-4 를 평가할 수 없다")
    else:
        checked += 1
        count = started.get("count")
        if count != EXPECTED_START_CALLS:
            fails.append(
                f"A1-4 재생 시작 호출이 {count} 회다 — {EXPECTED_START_CALLS} 여야 한다"
                " (ⓐ 픽스처 3턴 · 프레임당 노드 1개)"
            )

        when_raw = started.get("when")
        when = cast(list[Any], when_raw) if isinstance(when_raw, list) else None
        if when is None:
            fails.append("A1-4 의 when 배열이 없다 — 대조 ②를 평가할 수 없다")
        else:
            checked += 1
            if len(when) != count:
                fails.append(
                    f"A1-4 의 when 개수가 {len(when)} 인데 count 는 {count} 다 — 계측이 퇴화했다"
                )
            checked += 1
            # ⛔ 대조 ② — 스케줄이 상수면 세 값이 같다. `start` 를 부르되 시각을 계산하지 않는
            #    형태가 이 단정으로만 걸린다.
            if len(when) > 1 and len(set(when)) == 1:
                fails.append(
                    f"A1-4 의 when 이 전부 {when[0]!r} 로 같다 — 서로 달라야 한다"
                    " (재생 시각이 계산되지 않고 상수다)"
                )

    # ── A1-5 확정 줄 (판정은 계측의 judgeFinalLines 가 계산한다) ─────────────
    fl_raw = observed.get("final_lines")
    fl = cast(dict[str, Any], fl_raw) if isinstance(fl_raw, dict) else None
    if fl is None:
        fails.append("관측에 final_lines 가 없다 — A1-5 를 평가할 수 없다")
    else:
        checked += 1
        verdict = fl.get("verdict")
        if verdict == "PASS":
            pass
        elif verdict in UNMEASURABLE_VERDICTS:
            fails.append(
                f"A1-5 측정 불가 — verdict={verdict}. ⛔ 이것은 **앱 결함이 아니다**"
                " (하네스가 종단을 놓쳤거나 적립이 잘렸다). PASS 로도 올리지 않는다"
            )
        elif verdict in APP_DEFECT_VERDICTS:
            fails.append(f"A1-5 앱 결함 — verdict={verdict}")
        else:
            fails.append(f"A1-5 의 verdict 가 알 수 없는 값이다: {verdict!r}")

    # ── A1-7 실제 송신 ──────────────────────────────────────────────────────
    sent_raw = observed.get("sent")
    sent = cast(dict[str, Any], sent_raw) if isinstance(sent_raw, dict) else None
    if sent is None:
        fails.append("관측에 sent 가 없다 — A1-7 을 평가할 수 없다")
    else:
        checked += 1
        audio = sent.get("audio")
        if not isinstance(audio, int) or audio <= 0:
            fails.append(
                f"A1-7 의 sent.audio 가 {audio!r} 다 — 0 보다 커야 한다"
                " (WebSocket.prototype.send 를 통과한 실제 전송)"
            )

        checked += 1
        end_session = sent.get("end_session")
        if end_session != 1:
            fails.append(
                f"A1-7 의 sent.end_session 이 {end_session!r} 다 — 정확히 1 이어야 한다."
                " ⛔ 이것이 0 이면 audio 계수 0 은 「전송 없음」이 아니라 **후킹 고장**이다."
                " (⚠️ 이 값은 세션 종료 클릭 **후에** 읽는다)"
            )

    # ── A1-7 대체 대조 — PCM 내용을 센다 ────────────────────────────────────
    # ⛔ **무음에서 `sent.audio` 가 0 이 되기를 기대하지 않는다 — 그 갈래는 폐기됐다.**
    #    캡처 워클렛이 진폭과 무관하게 512샘플마다 보내므로 무음·유음의 프레임 수와 바이트가
    #    **완전히 같다**(실측 146건 · 199,728B). 가르는 유일한 값이 PCM 내용이다.
    nonzero = observed.get("sentAudioNonZeroFrames")
    if not isinstance(nonzero, int):
        fails.append("관측에 sentAudioNonZeroFrames 가 없다 — A1-7 대체 대조를 평가할 수 없다")
    else:
        checked += 1
        if silent and nonzero != 0:
            fails.append(
                f"무음 회차인데 nonZeroFrames 가 {nonzero} 다 — 0 이어야 한다."
                " config.silentMic 이 실제로 먹지 않았다"
            )
        if not silent and nonzero <= 0:
            fails.append(
                f"톤 회차인데 nonZeroFrames 가 {nonzero} 다 — 0 보다 커야 한다."
                " 마이크가 무음을 보내고 있다"
            )

    return checked, fails


# ─────────────────────────────────────────────────────────────────────────────
# 관측 — CDP. 판정은 위 순수 함수가 소유하고 여기서는 값만 모은다.
# ─────────────────────────────────────────────────────────────────────────────


def fixture_expected_lines() -> list[str]:
    """A1-5 기대값을 `fixtures.py` 에서 **파싱해** 만든다 — 손 전사하지 않는다.

    접두는 화면이 소유한다 — `app/page.tsx:309` 가 `speaker === "agent"` 면 `질문`,
    아니면 `답변` 을 `<strong>` 으로 그린다.
    순서는 `stub.py` 가 적은 재생 순서(질문=agent final → 답변=user final)를 따른다.
    """
    import re
    from pathlib import Path

    src = (Path(__file__).parents[2] / "app/backend/app/audio_gateway/fixtures.py").read_text(
        encoding="utf-8"
    )
    block = re.search(r"FIXTURE_TURNS[^=]*=\s*\[(.*?)\n\]", src, re.S)
    if not block:
        raise SystemExit("fixtures.py 에서 FIXTURE_TURNS 를 찾지 못했다 — A1-5 기대값을 못 만든다")
    pairs = re.findall(
        r'\(\s*"((?:[^"\\]|\\.)*)"\s*,\s*"((?:[^"\\]|\\.)*)"\s*,?\s*\)', block.group(1)
    )
    if len(pairs) != EXPECTED_START_CALLS:
        raise SystemExit(
            f"픽스처 턴이 {len(pairs)} 개인데 기대 재생 시작은"
            f" {EXPECTED_START_CALLS} 다 — 둘이 갈렸다"
        )
    lines: list[str] = []
    for question, answer in pairs:
        lines.append(f"질문: {question}")
        lines.append(f"답변: {answer}")
    return lines


# ⛔ 세션 완주를 기다린 뒤 한 번에 읽는다. C1 은 주입이 없으므로(픽스처 자동 재생)
# §6 의 「한 `eval`」 제약은 왕복을 줄이는 목적으로만 적용된다.
WALK_JS = """
(async () => {
  const omy = window.__omy;
  if (!omy) throw new Error("계측이 걸려 있지 않다 (window.__omy 부재)");
  if (typeof omy.judgeFinalLines !== "function") {
    throw new Error("계측에 judgeFinalLines 가 없다 — A1-5 를 판정할 수 없다");
  }

  const EXPECTED = EXPECTED_JSON;
  const STEP = 100;
  const WALK_TIMEOUT = WALK_TIMEOUT_MS;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // 앱 핸들러 부착을 기다린다 — 이것이 없으면 아래 대기가 「영원히 0」으로 보인다.
  const attachDeadline = Date.now() + 5000;
  while (!(omy.meta && omy.meta.appHandlerAttached)) {
    if (Date.now() > attachDeadline) {
      throw new Error(
        "앱 onmessage 핸들러가 5초 안에 붙지 않았다 (meta=" +
          JSON.stringify(omy.meta || null) + ")"
      );
    }
    await sleep(STEP);
  }

  // 세션 완주를 기다린다 — 종단은 `session_ended` 이고, final 수가 기대에 닿는 것도 함께 본다.
  const deadline = Date.now() + WALK_TIMEOUT;
  while (Date.now() < deadline) {
    if (omy.recv.session_ended > 0 || omy.recv.final >= EXPECTED.length) break;
    await sleep(STEP);
  }

  return JSON.stringify({
    recv: omy.recv,
    started: { count: omy.started.count, when: omy.started.when },
    final_lines: omy.judgeFinalLines(EXPECTED),
    sent: omy.sent,
    sentAudioBytes: omy.sentAudioBytes,
    sentAudioNonZeroFrames: omy.sentAudioNonZeroFrames,
    meta: omy.meta,
  });
})()
"""


def walk_js(expected: list[str], timeout_ms: int) -> str:
    import json

    return WALK_JS.replace("EXPECTED_JSON", json.dumps(expected, ensure_ascii=False)).replace(
        "WALK_TIMEOUT_MS", str(timeout_ms)
    )


def main() -> int:
    import argparse
    import asyncio
    import hashlib
    import json
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    # ⛔ 계측은 `instrument.js` 다 — `measure_js()`(C2 측정 스크립트)가 아니다.
    #    `TASK-49` 가 그것을 혼동해 한 번 죽었다.
    from c2_render_hierarchy import INSTRUMENT, Cdp, find_target  # noqa: PLC0415
    from websockets.asyncio.client import connect  # noqa: PLC0415

    ap = argparse.ArgumentParser(description="C1 세션 관통 판정 (A1-4·A1-5·A1-7)")
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--url", default="http://localhost:3000/")
    ap.add_argument("--out", help="관측·판정을 JSON 으로 쓸 경로")
    ap.add_argument(
        "--silent-mic",
        action="store_true",
        help="A1-7 대체 대조 — 마이크 게인을 0 으로 두고 nonZeroFrames 가 0 이 되는지 본다",
    )
    ap.add_argument("--walk-timeout-ms", type=int, default=60000)
    args = ap.parse_args()

    expected = fixture_expected_lines()
    print(f"A1-5 기대 줄 {len(expected)}개 (fixtures.py 에서 파싱)")
    src = INSTRUMENT.read_text(encoding="utf-8")
    file_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    print(f"instrument.js sha256(파일): {file_sha}  ({len(src.encode('utf-8'))}B)")

    async def run() -> dict[str, Any]:
        ws_url, url = find_target(args.port, args.url)
        print(f"대상: {url} · silent_mic={args.silent_mic}")
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

            # ⚠️ 마이크 게인은 **클릭 전에** 정한다 — `getUserMedia` 가 클릭 안에서 불린다.
            if args.silent_mic:
                await cdp.eval("window.__omy.config.silentMic = true; true")

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
                    f"user activation 이 생기지 않았다 — {act!r}. 탭이 배경이면 CDP 클릭이"
                    " 페이지에 닿지 않는다 (H-AE). page 탭이 여러 개면 비결정적으로 실패한다"
                )

            observed = cast(
                dict[str, Any],
                json.loads(
                    await cdp.eval(walk_js(expected, args.walk_timeout_ms), await_promise=True)
                ),
            )

            # ⛔ `end_session` 은 **종료 클릭 후에** 세어진다 (§5 A1-7 행 ①).
            await cdp.click(
                "Array.from(document.querySelectorAll('button'))"
                "  .find(b => /학습 종료/.test(b.textContent||''))",
                "학습 종료",
            )
            after = json.loads(
                await cdp.eval(
                    "(async () => { const s = () => JSON.stringify(window.__omy.sent);"
                    " for (let i = 0; i < 50; i++) {"
                    "   if (window.__omy.sent.end_session > 0) break;"
                    "   await new Promise(r => setTimeout(r, 100)); }"
                    " return s(); })()",
                    await_promise=True,
                )
            )
            observed["sent"] = after
            observed["silent_mic"] = args.silent_mic
            return observed

    observed = asyncio.run(run())
    checked, fails = check_c1(observed)

    print(f"\nrecv={observed.get('recv')}")
    print(f"started={observed.get('started')}")
    fl_obs = cast(dict[str, Any], observed.get("final_lines") or {})
    print(f"final_lines.verdict={fl_obs.get('verdict')}")
    print(f"sent={observed.get('sent')} nonZeroFrames={observed.get('sentAudioNonZeroFrames')}")
    print(f"\n센 단정 {checked}건 · 어긋남 {len(fails)}건")
    for f in fails:
        print(f"  FAIL {f}")

    if args.out:
        from pathlib import Path as _P

        _P(args.out).write_text(
            json.dumps(
                {"observed": observed, "checked": checked, "fails": fails},
                ensure_ascii=False,
                indent=1,
            ),
            encoding="utf-8",
        )
        print(f"기록: {args.out}")

    if fails:
        return 1
    print("C1 PASS — A1-4·A1-5·A1-7 을 모두 통과했다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
