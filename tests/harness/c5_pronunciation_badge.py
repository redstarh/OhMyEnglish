"""C5 실행체 — 발음 배지(A5-1·A5-2)를 한 프로세스 안에서 주입·판독·판정한다.

⛔ **왜 실행체가 필요한가** (`TASK-49`). C1·C2·C3·C4 는 실행체가 있는데 C5 만 없어서 판정을
대화형 왕복으로 해야 했고, 이 환경의 라운드트립(실측 **20,635 ms**)이 주입 창(**10,000 ms**)을
**반드시 넘긴다.** 5차수는 같은 문서에서 재시도를 합성 클릭하는 우회로 성립시켰고 그 결과
**A5-1 의 음성 대조 ①(주입 전 배지 부재)이 오염됐다** — 그 회차는 대조 ②만 근거로 `PASS` 를 냈다.
주입과 판독이 한 프로세스 안에서 끝나면 그 오염이 **원리적으로** 사라진다.

**판정은 순수 함수(`check_badges`)에 있고 CDP 는 관측만 한다.** 그래서 `test_c5_gates.py` 가
브라우저 없이 판별력을 고정할 수 있다 — `c3_results_screen.py` 와 같은 분리다.

기대 문구는 **ⓒ 하드코딩**이다: 프레임은 기계값 `outcome` 만 나르고 문구는 화면 상수다.
정본은 `app/frontend/app/page.tsx` 의 `PRONUNCIATION_BADGE` 이며 **거기서 바뀌면 여기도 고친다**
(그것을 잊으면 이 실행체가 거짓 실패를 낸다 — 그때 고칠 곳은 앱이 아니라 이 상수다).
"""

from __future__ import annotations

# ⓒ 하드코딩 — `app/page.tsx:21~26` 과 글자 단위로 같아야 한다. 순서도 주입 순서다.
BADGE_TEXT: dict[str, str] = {
    "pending": "🔊 발음 교정 중",
    "correct": "✓ 좋아요",
    "incorrect": "다시 연습해요",
    "unclear": "잘 안 들렸어요",
}

# A5-2 용. `target_sound` 는 기계 키라 **화면에 렌더되지 않아야** 한다(설계서 §10 미결 4 ·
# 2026-08-30 캡틴 결정). 앱이 실제로 쓰는 값과 겹치면 거짓 실패가 나므로 겹치지 않는 값을 쓴다.
SENTINEL = "ZZ_SENTINEL_TARGET_SOUND_ZZ"

# 배지 요소는 구조로 지목한다 — 프론트 전체에 `aria-live` 가 1건뿐임을 `browser_leg.md` §5 의
# A5-1 행이 확인해 뒀다. 전역 문구 검색을 쓰지 않는 이유도 그 행이 소유한다.
BADGE_SELECTOR = 'p[aria-live="polite"]'


def check_badges(observed: dict) -> tuple[int, list[str]]:
    """관측을 판정한다. 반환은 `(센 단정 수, 어긋남 메시지)`.

    ⛔ **비거나 빠진 입력을 통과로 만들지 않는다** — 그러면 실행체가 아무것도 안 해도 `PASS` 가
    된다(`c3_results_screen.py` 가 같은 이유로 키 존재를 먼저 단정한다).
    """
    checked = 0
    fails: list[str] = []

    before = observed.get("before_injection")
    if not isinstance(before, dict) or "badge_count" not in before:
        fails.append("관측에 before_injection.badge_count 가 없다 — 대조 ①을 평가할 수 없다")
    else:
        checked += 1
        if before["badge_count"] != 0:
            fails.append(
                f"주입 전 배지 요소가 {before['badge_count']}개다 (0이어야 한다) — "
                "대조 ①이 무력화됐다. 같은 문서에서 앞선 주입이 남아 있는지 본다"
            )

    seq = observed.get("sequence")
    if not isinstance(seq, list) or not seq:
        fails.append("관측에 sequence 가 없거나 비었다 — 주입이 한 번도 안 됐다")
        return checked, fails

    seen = [item.get("outcome") for item in seq]
    missing = [o for o in BADGE_TEXT if o not in seen]
    checked += 1
    if missing:
        fails.append(f"주입되지 않은 outcome 이 있다: {missing} — 네 종류를 모두 재야 한다")

    for i, item in enumerate(seq):
        outcome = item.get("outcome")
        expected = BADGE_TEXT.get(outcome)
        if expected is None:
            fails.append(f"[{i}] 알 수 없는 outcome {outcome!r} 이다")
            continue

        checked += 1
        count = item.get("badge_count")
        if count != 1:
            fails.append(
                f"[{outcome}] 배지 요소가 {count}개다 — **정확히 1개**여야 한다. "
                "4종을 전부 렌더하는 경로가 이 단정으로만 닫힌다"
            )

        checked += 1
        text = item.get("text")
        if text != expected:
            fails.append(
                f"[{outcome}] 배지 문구가 {text!r} 다 — {expected!r} 와 등호로 같아야 한다"
            )

        checked += 1
        hits = item.get("sentinel_hits")
        if hits != 0:
            fails.append(
                f"[{outcome}] sentinel 이 DOM 에서 {hits}건 잡혔다 (0이어야 한다) — "
                "target_sound 가 화면에 새어 나왔다 (A5-2)"
            )

    # 대조 ② — 상수를 렌더하고 있으면 네 문구가 바뀌지 않는다.
    texts = [item.get("text") for item in seq if item.get("outcome") in BADGE_TEXT]
    checked += 1
    if len(texts) > 1 and len(set(texts)) == 1:
        fails.append(
            f"네 outcome 의 배지 문구가 전부 {texts[0]!r} 로 같다 — 서로 달라야 한다. "
            "요소가 프레임에 의해 구동되지 않고 상수를 렌더한다"
        )

    return checked, fails


# ─────────────────────────────────────────────────────────────────────────────
# 관측 — CDP. 판정은 위 순수 함수가 소유하고 여기서는 값만 모은다.
# ─────────────────────────────────────────────────────────────────────────────

# ⛔ **전 과정이 한 `eval` 안에 있다** (`browser_leg.md` §6). 주입과 판독 사이에 에이전트
# 라운드트립이 끼면 주입 창(10,000 ms)을 넘긴다 — 실측 라운드트립이 20,635 ms 라 반드시 넘긴다.
# 그것이 `TASK-49` 가 이 실행체를 만든 이유다.
OBSERVE_JS = """
(async () => {
  const omy = window.__omy;
  if (!omy) throw new Error("계측이 걸려 있지 않다 (window.__omy 부재)");
  if (typeof omy.inject !== "function") throw new Error("계측에 inject 가 없다");

  const SEL = SELECTOR_JSON;
  const SENT = SENTINEL_JSON;
  const ORDER = ORDER_JSON;
  const STEP = 50;
  const RENDER_TIMEOUT = 3000;

  const badges = () => Array.from(document.querySelectorAll(SEL));
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // ── 대조 ① — **주입 전** 배지 부재. 클릭보다 먼저 재므로 앞선 주입이 오염시킬 수 없다.
  const before = { badge_count: badges().length };

  // ⛔ **앱의 onmessage 핸들러 부착을 기다린다 — 이것을 빼면 주입이 비결정적으로 죽는다.**
  // 2026-09-09 실측: 초판이 클릭 직후 바로 주입해서 6회 중 2회가
  // `omy.inject` 의 "앱의 onmessage 핸들러가 아직 붙지 않았다" 로 죽었고, **그 exit 1 을 판별력으로
  // 오독할 뻔했다**(변이는 관측 뒤에 적용되므로 관측이 죽으면 변이는 적용조차 되지 않는다).
  // 계측이 `omy.meta.appHandlerAttached` 로 그 상태를 노출한다(`instrument.js:211·534`).
  const attachDeadline = Date.now() + 5000;
  while (!(omy.meta && omy.meta.appHandlerAttached)) {
    if (Date.now() > attachDeadline) {
      throw new Error(
        "앱 onmessage 핸들러가 5초 안에 붙지 않았다 — 세션 시작 클릭이 닿았는지 본다" +
          " (meta=" + JSON.stringify(omy.meta || null) + ")"
      );
    }
    await sleep(STEP);
  }

  const sequence = [];
  for (const outcome of ORDER) {
    const injectedBefore = omy.injected;
    omy.inject({
      type: "pronunciation",
      outcome,
      target_form: "target form for " + outcome,
      target_sound: SENT,
    });

    // 렌더를 기다린다 — 문구가 이 outcome 것으로 바뀌거나 타임아웃.
    const deadline = Date.now() + RENDER_TIMEOUT;
    let text = null;
    while (Date.now() < deadline) {
      const els = badges();
      if (els.length === 1) {
        const t = els[0].textContent;
        if (t && t !== (sequence.length ? sequence[sequence.length - 1].text : null)) {
          text = t;
          break;
        }
        text = t;
      }
      await sleep(STEP);
    }

    sequence.push({
      outcome,
      badge_count: badges().length,
      text,
      // A5-2 — 기계 키가 화면에 새어 나오지 않아야 한다. DOM 전체에서 센다.
      sentinel_hits: (document.body.innerText.match(new RegExp(SENT, "g")) || []).length,
      injected_delta: omy.injected - injectedBefore,
    });
  }

  return JSON.stringify({ before_injection: before, sequence });
})()
"""


def observe_js(order: list[str]) -> str:
    """치환자를 실제 값으로 채운다.

    치환 지점을 한 곳으로 모으는 이유는 `c2_render_hierarchy.measure_js` 와 같다 — 호출부에
    흩으면 일부만 채우는 실수가 난다.
    """
    import json

    return (
        OBSERVE_JS.replace("SELECTOR_JSON", json.dumps(BADGE_SELECTOR))
        .replace("SENTINEL_JSON", json.dumps(SENTINEL))
        .replace("ORDER_JSON", json.dumps(order, ensure_ascii=False))
    )


# `TASK-49` AC#3 — 실행체가 어긋난 관측에서 **exit 1** 을 내는지 관측하기 위한 변이다.
# ⛔ 앱을 고치지 않는다. 관측값만 비튼다.
MUTATIONS = {
    "badge-before": lambda d: d["before_injection"].update({"badge_count": 1}),
    "two-badges": lambda d: d["sequence"][0].update({"badge_count": 2}),
    "wrong-text": lambda d: d["sequence"][1].update({"text": BADGE_TEXT["incorrect"]}),
    "constant-text": lambda d: [
        item.update({"text": BADGE_TEXT["pending"]}) for item in d["sequence"]
    ],
    "sentinel-leak": lambda d: d["sequence"][0].update({"sentinel_hits": 1}),
}


def main() -> int:
    import argparse
    import asyncio
    import hashlib
    import json
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent))
    # ⛔ **계측은 `instrument.js` 다 — `measure_js()` 가 아니다.** 초판이 그것을 계측으로 써서
    #    `eval` 이 `{}` 를 돌려주고 §4-1 검사에서 이름 있게 죽었다(2026-09-09 실측).
    #    `measure_js()` 는 **C2 의 측정 스크립트**(6,029B)이고 계측은 `window.__omy` 를 설치하며
    #    끝에서 `"instrumented"` 를 반환하는 44,552B 파일이다. 둘을 섞지 않는다.
    from c2_render_hierarchy import INSTRUMENT, Cdp, find_target  # noqa: PLC0415
    from websockets.asyncio.client import connect  # noqa: PLC0415

    ap = argparse.ArgumentParser(description="C5 발음 배지 판정 (A5-1·A5-2)")
    ap.add_argument("--port", type=int, default=9222, help="CDP 포트")
    ap.add_argument("--url", default="http://localhost:3000/", help="대상 페이지")
    ap.add_argument("--out", help="관측·판정을 JSON 으로 쓸 경로")
    ap.add_argument(
        "--mutate",
        choices=sorted(MUTATIONS),
        help="관측을 일부러 어긋나게 만든다 (판별력 확인용 — exit 1 이 나야 한다)",
    )
    args = ap.parse_args()

    src = INSTRUMENT.read_text(encoding="utf-8")
    file_sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    print(f"instrument.js sha256(파일): {file_sha}  ({len(src.encode('utf-8'))}B)")

    async def run() -> dict:
        ws_url, url = find_target(args.port, args.url)
        print(f"대상: {url}")
        async with connect(ws_url, max_size=None) as ws:
            cdp = Cdp(ws)
            # ⚠️ 배경 탭에서는 CDP 클릭이 페이지에 닿지 않는다 (`H-AE`).
            await cdp.call("Page.bringToFront")

            nav = await cdp.call("Page.navigate", {"url": args.url})
            if nav.get("errorText"):
                raise SystemExit(f"navigate 실패: {nav['errorText']} — 프론트가 떠 있는지 본다")
            await cdp.eval(
                "new Promise(r => document.readyState === 'complete'"
                " ? r(1) : window.addEventListener('load', () => r(1)))",
                await_promise=True,
            )

            # 계측 설치 + 전사 드리프트 고정 (§10-3 · c2 와 같은 절차다).
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

            # ⛔ user activation 은 **CDP 클릭 1회**로만 만든다 — 같은 문서에서 합성 클릭으로
            #    재시도하면 대조 ①이 오염된다(`TASK-49` AC#2 · 5차수가 그렇게 오염됐다).
            await cdp.click(
                "Array.from(document.querySelectorAll('button'))"
                "  .find(b => /학습 시작/.test(b.textContent||''))",
                "학습 시작",
            )

            # ⛔ **user activation 을 단정한다 — c2 가 쓰는 안전장치이고 초판이 빼먹었다.**
            # 빼면 배경 탭 실패(`H-AE`)가 「주입 실패」로 늦게 드러나고, 그 exit 1 을 판별력으로
            # 오독할 수 있다(2026-09-09 실측: 변이 5건 중 2건이 그 형태였다).
            activation = await cdp.eval(
                "JSON.stringify({hasBeenActive: navigator.userActivation.hasBeenActive,"
                " isActive: navigator.userActivation.isActive})"
            )
            act = json.loads(activation)
            if not act.get("hasBeenActive"):
                raise SystemExit(
                    f"user activation 이 생기지 않았다 — {act!r}. 탭이 배경이면 CDP 클릭이"
                    " 페이지에 닿지 않는다 (H-AE). 다른 탭이 활성인지 본다"
                )

            raw = await cdp.eval(observe_js(list(BADGE_TEXT)), await_promise=True)
            return json.loads(raw)

    observed = asyncio.run(run())

    if args.mutate:
        MUTATIONS[args.mutate](observed)
        print(f"⚠️ 변이 적용: {args.mutate} — exit 1 이 나야 판별력이 있다")

    checked, fails = check_badges(observed)
    print(f"\n센 단정 {checked}건 · 어긋남 {len(fails)}건")
    for f in fails:
        print(f"  FAIL {f}")

    if args.out:
        Path(args.out).write_text(
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
    print("C5 PASS — A5-1 대조 ①·② 와 A5-2 를 모두 통과했다")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
