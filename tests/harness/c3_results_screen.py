#!/usr/bin/env python3
"""C3 결과 화면 5상태 + C4 교정 카드 관측 — `browser_leg.md` §5 C3·C4의 실행체 (T4).

**설계 원칙은 `c2_render_hierarchy.py`에서 그대로 물려받는다** — 그리고 그 파일이 2026-09-06
리뷰에서 뚫린 이유(값을 **인쇄만** 하고 판정하지 않았다)를 되풀이하지 않기 위해 **처음부터
`check_*` 게이트를 넣고 어긋나면 비영 종료한다.** `Cdp`·`find_target`은 그 모듈에서 **재사용**한다
(같은 CDP :9222 수단. 새 수단 0개).

## 이 스크립트가 지키는 규약

- **요소를 구조로 지목하고 등호로 잰다**(§5 A3-1·A4-2) — DOM 전역 포함 검사를 쓰지 않는다.
  상태 라벨은 `main`의 **첫 직계 `<p>`**이고(`results/[sessionId]/page.tsx`가 `result`가 있을 때
  그 자리에 `STATUS_LABEL[result.status]`를 한 번 렌더한다), 교정 카드는 `<strong>`이 `원문:`인
  `<p>`를 **직계로 가진 `<div>`**다.
- **기대값은 결과 API에서 유도한다**(ⓑ) — `corrections` 개수·`reason` 문자열을 하드코딩하지 않는다.
  API는 화면의 **상류**라 순환이 아니다. 단 상태 라벨 5개는 화면이 소유하는 한국어 문구이므로 ⓒ다.
- **A3-1의 음성 대조는 「상태별 세션 재방문」이다** — 5상태를 차례로 방문해 **같은 요소의 문구가
  매번 바뀌는지** 본다. 상수를 렌더하고 있으면 바뀌지 않는다.
- **A4-1의 음성 대조는 `corrections`가 빈 세션에서 두 접두가 0개**인 것이다. 그 세션을 primary로
  쓰지 않는다 — `N == 0`을 primary로 잡으면 `0 == 0`이라 카드 구현이 없어도 통과한다.
- **판별력 미확인을 PASS로 적지 않는다**(§10) — A4-2의 기대값 교차 대조는 교정 **2건 이상**인
  세션이 필요하다. 없으면 그 사실을 보고에 남기고 그 대조를 통과로 세지 않는다.

실행:
    cd app/backend && .venv/bin/python ../../tests/harness/c3_results_screen.py \
        --session analyzing=<uuid> --session final=<uuid> ...
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import sys
import urllib.request
from pathlib import Path

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))

from c2_render_hierarchy import Cdp, find_target  # noqa: E402
from websockets.asyncio.client import connect  # noqa: E402

ROOT = HARNESS.parent.parent
EVIDENCE = ROOT / ".harness" / "evidence"

# ⓒ 하드코딩 — 화면이 소유하는 한국어 문구다(`results/[sessionId]/page.tsx:22~28`). API는
# 기계값(`status`)만 준다. **요소 지목 + 등호**로 재므로 전역 검색의 항진명제 경로는 닫혀 있다.
STATUS_LABEL = {
    "analyzing": "분석 중",
    "final": "확정",
    "partial_failure": "부분 실패",
    "connection_failed": "연결 실패",
    "no_utterances": "분석 대상 없음",
}
PARTIAL_NOTICE = "분석하지 못한 발화가 있습니다 — 재시도되지 않습니다"
# 없는 세션 화면의 문구 — TASK-55 로 바뀌었다. 이전 값은 `결과 API가 404을 반환했습니다`로
# HTTP 상태 코드를 학습자에게 그대로 보여줬다. 지금 화면은 상태 코드를 **분류에만** 쓰고
# 문구는 자기가 소유한다(`results/[sessionId]/page.tsx`의 `failureNotice`).
MISSING_NOTICE = "그 학습 결과를 찾을 수 없습니다."
MISSING_UUID = "00000000-0000-0000-0000-0000000000ff"

READ_JS = r"""
(() => {
  const main = document.querySelector("main");
  if (!main) return { error: "main 이 없다" };
  const directPs = Array.from(main.children).filter((e) => e.tagName === "P");
  const strongOf = (p) => {
    const s = p.querySelector("strong");
    return s ? s.textContent : null;
  };
  const isCard = (d) =>
    Array.from(d.children).some((c) => c.tagName === "P" && strongOf(c) === "원문:");
  const cards = Array.from(document.querySelectorAll("div")).filter(isCard);
  const countPrefix = (label) =>
    Array.from(document.querySelectorAll("p")).filter((p) => strongOf(p) === label).length;
  return {
    url: location.href,
    directPCount: directPs.length,
    firstDirectP: directPs.length
      ? { text: directPs[0].textContent, outerHTML: directPs[0].outerHTML }
      : null,
    directPTexts: directPs.map((p) => p.textContent),
    prefixCounts: { 원문: countPrefix("원문:"), 교정문: countPrefix("교정문:") },
    cards: cards.map((d) => {
      const ps = Array.from(d.children).filter((e) => e.tagName === "P");
      return {
        pCount: ps.length,
        strongs: ps.map(strongOf),
        texts: ps.map((p) => p.textContent),
        outerHTML: d.outerHTML,
      };
    }),
    bodyHasPartialNotice: document.body.textContent.indexOf(PARTIAL_NOTICE) !== -1,
    labelsAnywhere: LABELS.filter((l) => document.body.textContent.indexOf(l) !== -1),
    bodyText: document.body.textContent.replace(/\s+/g, " ").slice(0, 300),
  };
})()
"""


def api_results(session_id: str, base: str) -> dict:
    """결과 API를 **파이썬에서** 부른다 — 화면의 상류이므로 기대값의 출처다."""
    with urllib.request.urlopen(f"{base}/api/sessions/{session_id}/results", timeout=10) as fh:
        return json.load(fh)


async def visit(cdp: Cdp, url: str, expect_label: str | None) -> dict:
    """한 화면을 열고 판독한다. 라벨(또는 오류 문구)이 뜰 때까지 기다린 뒤 한 번에 읽는다."""
    await cdp.call("Page.navigate", {"url": url})
    js = READ_JS.replace(
        "LABELS", json.dumps(list(STATUS_LABEL.values()), ensure_ascii=False)
    ).replace("PARTIAL_NOTICE", json.dumps(PARTIAL_NOTICE, ensure_ascii=False))
    want = expect_label or MISSING_NOTICE
    data: dict | None = None
    for _ in range(60):
        await asyncio.sleep(0.25)
        data = await cdp.eval(js)
        if isinstance(data, dict) and data.get("firstDirectP"):
            if want in data["firstDirectP"]["text"]:
                return data
    raise SystemExit(
        f"{url} 에서 기대 문구({want!r})가 15초 안에 나타나지 않았다 — 마지막 판독: {data!r}"
    )


def check_screen(payload: dict, dom: dict, session_id: str) -> tuple[int, list[str]]:
    """한 상태 화면의 단정을 **판정한다.** 반환 `(검사 수, 어긋난 것들)`."""
    fails: list[str] = []
    checked = 0

    def need(cond: object, msg: str) -> None:
        nonlocal checked
        checked += 1
        if not cond:
            fails.append(msg)

    status = payload["status"]
    expected = STATUS_LABEL[status]
    # ── ⛔ **`READ_JS` 가 `location.href` 를 담고도 아무도 단정하지 않았다** (C3 검토 ④).
    #    `Page.navigate` 직후 폴링이 **이전 문서**를 읽을 수 있고, 두 세션이 같은 status 면
    #    스테일 판독이 조용히 통과한다. C2 의 MEDIUM-1 과 **같은 형태**(측정만 하고 게이트 안 함)다.
    need(
        isinstance(dom.get("url"), str) and dom["url"].rstrip("/").endswith(session_id),
        f"내비게이션 커밋 미확인: url={dom.get('url')!r} 이"
        f" 세션 {session_id} 로 끝나지 않는다"
        " — 이전 문서를 읽었을 수 있다",
    )
    # ── A3-1: 요소 지목 + 등호. 전역 포함 검사를 쓰지 않는다.
    need(
        dom.get("firstDirectP") is not None,
        "main 의 첫 직계 <p> 가 없다 — 상태 요소를 지목할 수 없다",
    )
    if dom.get("firstDirectP"):
        need(
            dom["firstDirectP"]["text"] == expected,
            f"A3-1: 첫 직계 <p> 가 {dom['firstDirectP']['text']!r} 인데 기대는 {expected!r}",
        )
    # ── 부분 실패 안내 문구는 그 상태에서만 뜬다.
    need(
        dom["bodyHasPartialNotice"] == (status == "partial_failure"),
        f"부분 실패 안내 문구 존재={dom['bodyHasPartialNotice']} 인데 status={status}",
    )
    # ── ⛔ **키 부재를 0으로 만드는 것이 공허 통과를 만든다 — 리뷰가 실증했다** (C3 검토 ①).
    #    `final` 에서 `corrections` 키를 지우고 화면도 0장이면 `checked` 가 14 → **6** 으로 줄고
    #    **어긋남 0건**이 된다: A4-1·A4-2 전체가 조용히 사라지는데 그것이 FAIL 이 아니다.
    #    지금은 `primaries`(교정 보유 세션 0건 → BLOCKED)가 막지만, **§11-9 가 요구하는
    #    「교정 2건 이상 세션 추가」가 그 마스크를 벗긴다** — 하나가 키를 잃어도 primary 가 남는다.
    #    → **상태별로 키의 존재 자체를 단정한다.** `results.py`/`api/results.py` 의 계약이
    #    `final`·`partial_failure` 에만 키를 싣는다(직접 관측: 나머지 셋은 키가 없다).
    key_expected = status in ("final", "partial_failure")
    need(
        ("corrections" in payload) == key_expected,
        f"`corrections` 키 존재={('corrections' in payload)} 인데 status={status} 의 계약은"
        f" {key_expected} 다 — 키 부재를 0으로 읽으면 A4-1·A4-2 가 조용히 사라진다",
    )
    # ── A4-1: 접두 개수 == API 의 corrections 길이.
    n = len(payload.get("corrections", []))
    need(
        dom["prefixCounts"]["원문"] == n,
        f"A4-1: `원문:` <p> {dom['prefixCounts']['원문']}개 != API {n}",
    )
    need(
        dom["prefixCounts"]["교정문"] == n,
        f"A4-1: `교정문:` <p> {dom['prefixCounts']['교정문']}개 != API {n}",
    )
    need(len(dom["cards"]) == n, f"A4-1: 카드 <div> {len(dom['cards'])}개 != API {n}")
    for i, card in enumerate(dom["cards"]):
        # ⛔ **경계를 먼저 지킨다** — 화면 카드가 API 보다 많으면 `payload["corrections"][i]` 가
        #    `IndexError` 로 죽어 **이름 있는 FAIL 대신 트레이스백**이 나고 나머지 어긋남도 잃는다.
        #    (내가 쓴 게이트 테스트가 이 결함을 잡았다 — 카드 초과는 앱이 낼 수 있는 결함이다.)
        if i >= n:
            need(False, f"A4-1: 카드[{i}] 가 API corrections({n}건) 범위를 넘는다 — 초과 렌더다")
            continue
        need(card["pCount"] == 3, f"A4-1: 카드[{i}] 의 <p> 가 {card['pCount']}개다 (3이어야 한다)")
        need(
            card["strongs"][:2] == ["원문:", "교정문:"],
            f"A4-1: 카드[{i}] 의 라벨이 {card['strongs'][:2]!r} 다",
        )
        if card["pCount"] >= 3:
            third = card["texts"][2]
            need(card["strongs"][2] is None, f"A4-1: 카드[{i}] 셋째 줄에 라벨이 있다")
            need(third.strip() != "", f"A4-1: 카드[{i}] 셋째 줄이 비어 있다")
            # ── A4-2: 카드별 관통 — 그 카드 안 셋째 줄이 **그 교정의** reason 과 정확히 같다.
            expected_reason = payload["corrections"][i]["reason"]
            need(
                expected_reason.strip() != "",
                f"A4-2 표본 조건: corrections[{i}].reason 이 비었다 → FAIL 이 아니라 BLOCKED 다",
            )
            # ⛔ **여기 있던 sentinel 대조를 지웠다 — 독립 판별력이 0이었다** (C3 검토 ②).
            #    `third == expected_reason` 이 참이면 `third != expected + "__SENTINEL__"` 는
            #    **필연적으로** 참이다. 그것을 반증하는 유일한 입력을 넣으면
            #    **위 등호가 함께 잡는다**(리뷰 재현: fails 2건). 즉 대조가 아니라
            #    `checked` 를 카드마다 1씩 부풀리는 줄이었다.
            #    **문자열 변형 대조의 실체는 등호 자신이다** —
            #    `browser_leg.md` §5 A4-2 도 함께 고쳤다.
            need(third == expected_reason, f"A4-2: 카드[{i}] 셋째 줄 != API reason")
            # 카드가 실제로 그 교정을 담는지 — 원문도 함께 맞춘다(카드끼리 뒤바뀜 검출).
            need(
                card["texts"][0] == f"원문: {payload['corrections'][i]['original_span']}",
                f"A4-2: 카드[{i}] 원문 줄이 corrections[{i}] 와 다르다 — 카드 순서가 뒤바뀌었다",
            )
    return checked, fails


def check_missing(dom: dict) -> tuple[int, list[str]]:
    """A3-2 — 없는 세션: 5개 라벨 전부 부재 + 오류 문구."""
    fails: list[str] = []
    checked = 0

    def need(cond: object, msg: str) -> None:
        nonlocal checked
        checked += 1
        if not cond:
            fails.append(msg)

    need(dom.get("firstDirectP") is not None, "A3-2: 첫 직계 <p> 가 없다")
    if dom.get("firstDirectP"):
        need(
            dom["firstDirectP"]["text"] == MISSING_NOTICE,
            f"A3-2: 오류 문구가 {dom['firstDirectP']['text']!r} 다",
        )
    # ── ⛔ **TASK-55 의 회귀를 못 박는다. 그리고 이것은 위 등호에 종속되지 않는다** —
    #    등호는 **첫** 직계 `<p>` 하나만 고정하므로 상태 코드가 **다른 줄로** 새어 나오면 통과한다.
    #    그래서 직계 `<p>` **전체**에서 기계 낱말의 부재를 잰다. `bodyText` 를 쓰지 않는 이유는
    #    거기에 Next 개발 서버가 주입하는 스크립트가 섞여 판정이 도구 버전에 매이기 때문이다.
    leaked = [t for t in dom["directPTexts"] if any(k in t for k in ("API", "404", "422", "HTTP"))]
    need(leaked == [], f"A3-2: 학습자 문구에 기계 낱말이 새어 나왔다 — {leaked}")
    need(dom["labelsAnywhere"] == [], f"A3-2: 상태 라벨이 남아 있다 — {dom['labelsAnywhere']}")
    need(dom["prefixCounts"]["원문"] == 0, "A3-2: 없는 세션인데 교정 카드가 있다")
    return checked, fails


async def main_async(args) -> int:
    sessions = dict(pair.split("=", 1) for pair in args.session)
    if not sessions:
        raise SystemExit("--session 이 0건이다 — 0건을 검사하고 통과를 단정하지 않는다")
    payloads = {k: api_results(v, args.api) for k, v in sessions.items()}
    print(
        f"세션 {len(sessions)}건 · API 상태: "
        + " · ".join(f"{k}={payloads[k]['status']}" for k in sessions)
    )

    EVIDENCE.mkdir(parents=True, exist_ok=True)
    ws_url, url = find_target(args.port, args.url)
    print(f"target: {url}")
    results: dict[str, dict] = {}
    async with connect(ws_url, max_size=None) as ws:
        cdp = Cdp(ws)
        await cdp.call("Page.bringToFront")
        for key, sid in sessions.items():
            label = STATUS_LABEL[payloads[key]["status"]]
            dom = await visit(cdp, f"{args.base}/results/{sid}", label)
            shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
            path = EVIDENCE / f"c3-{key}.png"
            path.write_bytes(base64.b64decode(shot["data"]))
            dom["screenshot"] = str(path.relative_to(ROOT))
            results[key] = dom
            print(
                f"  {key:<18} 첫 직계 <p> = {dom['firstDirectP']['text']!r}"
                f" · 원문/교정문 = {dom['prefixCounts']['원문']}/{dom['prefixCounts']['교정문']}"
                f" · 카드 {len(dom['cards'])} · shot -> {dom['screenshot']}"
            )
        missing = await visit(cdp, f"{args.base}/results/{MISSING_UUID}", None)
        shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
        (EVIDENCE / "c3-missing.png").write_bytes(base64.b64decode(shot["data"]))
        missing["screenshot"] = ".harness/evidence/c3-missing.png"
        print(
            f"  {'missing-uuid':<18} 첫 직계 <p> = {missing['firstDirectP']['text']!r}"
            f" · 라벨 잔존 {missing['labelsAnywhere']}"
        )

    out = EVIDENCE / "c3-results-screen.json"
    out.write_text(
        json.dumps(
            {"api": payloads, "dom": results, "missing": missing}, ensure_ascii=False, indent=1
        ),
        encoding="utf-8",
    )
    print(f"\nraw -> {out.relative_to(ROOT)}")

    # ── 판정 ────────────────────────────────────────────────────────────────
    checked, fails = 0, []
    for key in sessions:
        c, f = check_screen(payloads[key], results[key], sessions[key])
        checked += c
        fails += [f"[{key}] {m}" for m in f]
    c, f = check_missing(missing)
    checked += c
    fails += [f"[missing-uuid] {m}" for m in f]

    # A3-1 음성 대조 — 같은 요소의 문구가 상태마다 **실제로 바뀐다**.
    # ⛔ **세션이 1건이면 이 대조는 항진명제다** (C3 검토 ③): `len(set(x)) != len(x)` 는 원소가
    #    하나면 **절대 참이 되지 않는다.** C2 의 `check_cross` 는 단일 모드를 `미평가`로 갈랐는데
    #    여기엔 그 분기가 없었다. → **2건 미만이면 평가하지 않고 미확인으로**
    #    낸다(PASS 로 세지 않는다).
    texts = [results[k]["firstDirectP"]["text"] for k in sessions if results[k].get("firstDirectP")]
    if len(texts) < 2:
        unverified_extra = (
            f"A3-1 음성 대조 미평가: 상태 화면이 {len(texts)}건뿐이다 —"
            " 「상태마다 문구가 바뀐다」는 2건 이상에서만 평가된다(§10)"
        )
    else:
        unverified_extra = None
        checked += 1
        if len(set(texts)) != len(texts):
            fails.append(f"A3-1 음성 대조: 같은 요소의 문구가 상태마다 바뀌지 않았다 — {texts}")
    # 실제 세션에는 A3-2 의 오류 문구가 없어야 한다(상호 대조).
    for key in sessions:
        checked += 1
        if any(MISSING_NOTICE in t for t in results[key]["directPTexts"]):
            fails.append(f"[{key}] A3-2 상호 대조: 정상 세션에 오류 문구가 있다")
    # A4-1 표본 조건 — primary(교정 1건 이상)가 실재해야 한다. 없으면 FAIL 이 아니라 BLOCKED 다.
    primaries = [k for k in sessions if len(payloads[k].get("corrections", [])) >= 1]
    empties = [
        k for k in sessions if "corrections" in payloads[k] and not payloads[k]["corrections"]
    ]
    blocked, unverified = [], []
    if unverified_extra:
        unverified.append(unverified_extra)
    if not primaries:
        blocked.append(
            "A4-1: corrections >= 1 인 세션이 없다 — 화면 결함이 아니라 표본 선택 실패(BLOCKED)"
        )
    if not empties:
        unverified.append("A4-1 음성 대조(빈 세션에서 접두 0개)를 평가할 세션이 없다")
    if not any(len(payloads[k].get("corrections", [])) >= 2 for k in sessions):
        unverified.append(
            "A4-2 기대값 교차 대조: 교정 **2건 이상**인 세션이 없어 평가할 수 없다 → 판별력 미확인"
        )

    print(f"\n--- 판정 (단정 {checked}건 검사) ---")
    for m in blocked:
        print(f"  BLOCKED  {m}")
    for m in unverified:
        print(f"  미확인   {m}  ← PASS 로 세지 않는다 (§10)")
    if fails:
        for m in fails:
            print(f"  FAIL  {m}")
        raise SystemExit(f"판정 FAIL — 어긋난 단정 {len(fails)}건 / 검사 {checked}건")
    if blocked:
        raise SystemExit(f"판정 BLOCKED — 표본 조건 {len(blocked)}건")
    print(
        f"  PASS  {checked}건 전건 통과"
        + (f" · 미확인 {len(unverified)}건은 통과로 세지 않았다" if unverified else "")
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9222)
    ap.add_argument("--base", default="http://localhost:3000")
    ap.add_argument("--api", default="http://localhost:8002")
    ap.add_argument("--url", default="http://localhost:3000/")
    ap.add_argument("--session", action="append", default=[], metavar="LABEL=UUID")
    args = ap.parse_args()
    return asyncio.run(main_async(args))


if __name__ == "__main__":
    sys.exit(main())
