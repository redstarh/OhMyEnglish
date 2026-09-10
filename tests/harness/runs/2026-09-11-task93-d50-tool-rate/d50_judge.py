#!/usr/bin/env python3
"""TASK-93 — 결정 50 의 ② 판정기.

⛔ 판별력 확인을 비율 계산보다 «먼저» 한다. 대조군(팔 B)에서 tool 이 0건이면 앱 프롬프트 팔의
0건은 프롬프트 탓인지 픽스처 탓인지 가를 수 없으므로, 비율을 내는 대신 「이 픽스처로는 잴 수
없음」을 출력하고 멈춘다. TASK-90 이 그 구별을 못 해 두 번 틀렸다(그 회차 기록 §12.1·§12.3).

⚠️ `target_sound` 실림 비율은 «팔 A 에서만» 뜻이 있다 — 기반 프롬프트는 그 필드를 요구하지
않는다(`nova.py` `_pronunciation_tool_configuration` 주석).

사용법: 리포 최상위에서 `python3 <이 파일>`.
"""

import glob
import json
import os
import re
import sys
from math import comb


def read(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        events = json.load(fh)
    tools = [e["toolUse"] for e in events if isinstance(e, dict) and "toolUse" in e]
    users = [
        e["textOutput"]["content"]
        for e in events
        if isinstance(e, dict) and "textOutput" in e and e["textOutput"].get("role") == "USER"
    ]
    sounds = []
    for tool in tools:
        try:
            payload = json.loads(tool.get("content") or "{}")
        except (json.JSONDecodeError, TypeError):
            payload = {}
        sounds.append(payload.get("target_sound"))
    stamp = re.search(r"(\d{8}T\d{6})Z", os.path.basename(path))
    return {
        "stamp": stamp.group(1) if stamp else "",
        "turns": len(users),
        "transcripts": users,
        "n_tool": len(tools),
        "sounds": sounds,
    }


def fisher(a: int, b: int, c: int, d: int) -> float:
    """[[a,b],[c,d]] 양측 — 관측보다 확률이 같거나 작은 표를 더한다."""
    n, r1, c1 = a + b + c + d, a + b, a + c

    def prob(x: int) -> float:
        if not (0 <= x <= c1 and 0 <= r1 - x <= n - c1):
            return 0.0
        return comb(c1, x) * comb(n - c1, r1 - x) / comb(n, r1)

    obs = prob(a)
    return sum(prob(x) for x in range(c1 + 1) if prob(x) <= obs + 1e-12)


def summarize(label: str, rows: list[dict]) -> tuple[int, int, int]:
    total = len(rows)
    with_tool = sum(1 for r in rows if r["n_tool"] > 0)
    with_sound = sum(1 for r in rows if any(s for s in r["sounds"]))
    print(f"\n{label} — 세션 {total}개")
    for r in rows:
        keys = ",".join(str(x) for x in r["sounds"]) if r["sounds"] else "-"
        print(f"  {r['stamp']}  턴={r['turns']}  tool={r['n_tool']}  target_sound={keys}")
        for line in r["transcripts"]:
            print(f"      전사: {line!r}")
    print(f"  → tool 도착 세션 {with_tool}/{total} · target_sound 실린 세션 {with_sound}/{total}")
    return total, with_tool, with_sound


def main() -> None:
    # 접두를 인자로 받는다 — `D50`(p2m 회차, 기본값) · `D50k`(p2k 회차). 두 회차를 «같은 코드»로
    # 판정해야 대조가 정확하다. ⛔ 판정 논리를 회차마다 복사하지 않는다.
    prefix = sys.argv[1] if len(sys.argv) > 1 else "D50"
    # 팔 A 의 접미도 인자로 받는다 — `app`(AS4 프롬프트) · `prod`(제품 조립 프롬프트, TASK-98).
    arm_a = sys.argv[2] if len(sys.argv) > 2 else "app"
    ev = ".harness/evidence/"
    app = [read(p) for p in sorted(glob.glob(f"{ev}{prefix}-{arm_a}-*.json"))]
    base = [read(p) for p in sorted(glob.glob(f"{ev}{prefix}-base-*.json"))]
    print(f"접두 `{prefix}` — 팔 A `{prefix}-{arm_a}-*` · 팔 B `{prefix}-base-*`")

    # ⛔ 팔 A 를 「앱 프롬프트」로 부르지 않는다 — `--app-prompt` 는 `nova.SYSTEM_PROMPT`(규칙
    # 전문 2,339자)만 싣고, 앱이 실제로 보내는 것은 `build_system_prompt()` 가 계획·무대·초점을
    # 붙여 조립한 것이다(`TASK-67` 노트의 2026-09-10 정정). 즉 이 팔은 «제품 경로가 아니다».
    n_b, tool_b, sound_b = summarize("팔 B — 스파이크 전용 짧은 프롬프트 · 대조군", base)
    n_a, tool_a, sound_a = summarize("팔 A — nova.SYSTEM_PROMPT (규칙 전문 · 제품 조립 전)", app)

    print("\n" + "=" * 74)
    print("⛔ 1단계 — 판별력 확인 (비율보다 먼저)")
    if n_b == 0:
        print("  대조군이 없다 — 판정 불가.")
        return
    if tool_b == 0:
        print(f"  ⛔ 대조군에서도 tool 0/{n_b} 임 → 판별력 없음.")
        print("  이 픽스처·턴 구성으로는 「앱 프롬프트가 tool 을 막는가」를 잴 수 없다.")
        print("  ⛔ 프롬프트를 원인으로 지목하지 않는다 (AC#1 의 갈림길).")
        return
    print(f"  ✔ 대조군에서 tool {tool_b}/{n_b} 도착 → 판별력 있음. 2단계로 간다.")

    print("\n⛔ 2단계 — 결정 50 의 두 비율 (분모를 함께 적는다)")
    print(f"  팔 A(AS4)  tool 도착률 = {tool_a}/{n_a} · target_sound 실림 = {sound_a}/{n_a}")
    print(f"  팔 B(기반) tool 도착률 = {tool_b}/{n_b} · target_sound 실림 = {sound_b}/{n_b}")
    print("  ⚠️ 팔 B 의 target_sound 는 지표가 아니다 — 그 프롬프트가 요구하지 않는다.")
    p_two_sided = fisher(tool_a, n_a - tool_a, tool_b, n_b - tool_b)
    print(f"\n  두 팔의 tool 도착 대비 Fisher 양측 p = {p_two_sided:.4f}")
    print("  ⚠️ 표본이 작으면 「구별되지 않음」으로 적는다 — p 만으로 단정하지 않는다.")


if __name__ == "__main__":
    main()
