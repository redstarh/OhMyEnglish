"""`c3_results_screen.py`의 판정 게이트가 **실제로 FAIL을 내는지** 잰다.

**왜 이 파일이 있는가**: C3 실행체는 「처음부터 게이트를 넣었다」로 만들었는데 그래도 리뷰가
**공허 통과 하나를 실증했다** — `final`에서 `corrections` 키를 지우고 화면도 0장이면 `checked`가
14 → **6**으로 줄고 **어긋남 0건**이 됐다(A4-1·A4-2 전체가 조용히 사라지는데 FAIL이 아니다).
그 형태를 회귀로 못 박는 것이 이 파일의 첫 목적이다.

⚠️ **입력은 실제 회차의 판독값이다** — `runs/2026-09-06-t4-c3-dom-read.json`. 손으로 만든 픽스처는
데이터 생성 경로의 결함에 눈이 먼다(`H-AF`). 그 위에 **한 필드씩** 변이를 얹는다.

⚠️ **이 파일도 게이트 안이다** — `app/backend/pyproject.toml:33`의 `testpaths = ["../../tests"]`가
리포의 `tests/`를 가리킨다. `test_c2_gates.py`와 같은 근거다.

⚠️ **추적 증거 사본이 테스트 픽스처를 겸한다**(리뷰 LOW). 그 파일은 **회차 기록이 소유**하고 이
테스트는 **읽기만** 한다 — 회차가 갱신되면 값이 바뀔 수 있고, 그때 이 테스트가 red를 내면
**픽스처를 맞추지 말고 게이트가 옳은지 먼저 본다.** 실패 방향이 안전한 결합이다.

실행(단독):
    cd app/backend && .venv/bin/pytest ../../tests/harness/test_c3_gates.py -q
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))

from c3_results_screen import check_missing, check_screen  # noqa: E402

REAL = HARNESS / "runs" / "2026-09-06-t4-c3-dom-read.json"
SESSION_IDS = {
    "analyzing": "210233be-ecaa-4409-a1af-8b7016cfe7e9",
    "final": "6225ddaf-90a8-43af-9aa8-e003921c75eb",
    "partial_failure": "b2f0d169-3d90-431b-b842-cce21125052a",
    "connection_failed": "76d9ef31-0d1b-4c50-b906-f16ee438080e",
    "no_utterances": "d127dece-d1d1-4329-802d-9b8fd1067388",
}


def load() -> dict:
    d = json.loads(REAL.read_text(encoding="utf-8"))
    assert set(d["api"]) == set(SESSION_IDS), f"판독 파일의 세션 집합이 다르다 — {sorted(d['api'])}"
    return d


def leg(key: str):
    d = load()
    return copy.deepcopy(d["api"][key]), copy.deepcopy(d["dom"][key]), SESSION_IDS[key]


def test_real_round_passes_every_state():
    """green — 다섯 상태 전부 통과하고 **검사 수가 0이 아니다**."""
    total = 0
    for key in SESSION_IDS:
        payload, dom, sid = leg(key)
        checked, fails = check_screen(payload, dom, sid)
        assert fails == [], f"[{key}] 실물 판독이 어긋났다: {fails}"
        assert checked >= 8, f"[{key}] 검사한 단정이 {checked}건뿐이다"
        total += checked
    assert total >= 40, total
    checked, fails = check_missing(load()["missing"])
    assert fails == [] and checked >= 4


# (라벨, 대상 상태, 변이, 어긋남 메시지 조각)
MUTATIONS = [
    # ⛔ 리뷰가 실증한 공허 통과 — 이 줄이 이 파일의 존재 이유다.
    (
        "corrections 키가 사라지고 화면도 0장",
        "final",
        lambda p, m: (
            p.pop("corrections"),
            m.update(prefixCounts={"원문": 0, "교정문": 0}, cards=[]),
        ),
        "`corrections` 키 존재=False",
    ),
    (
        "키 없어야 하는 상태에 키가 생겼다",
        "analyzing",
        lambda p, m: p.update(corrections=[]),
        "`corrections` 키 존재=True",
    ),
    (
        "상태 라벨이 다른 문구다",
        "final",
        lambda p, m: m["firstDirectP"].update(text="확정!"),
        "A3-1",
    ),
    (
        "첫 직계 <p> 가 없다",
        "final",
        lambda p, m: m.update(firstDirectP=None),
        "첫 직계 <p> 가 없다",
    ),
    (
        "부분 실패 안내가 엉뚱한 상태에 있다",
        "final",
        lambda p, m: m.update(bodyHasPartialNotice=True),
        "부분 실패 안내 문구 존재",
    ),
    (
        "부분 실패 상태인데 안내가 없다",
        "partial_failure",
        lambda p, m: m.update(bodyHasPartialNotice=False),
        "부분 실패 안내 문구 존재",
    ),
    (
        "접두 개수가 API 와 다르다",
        "final",
        lambda p, m: m["prefixCounts"].update(원문=2),
        "`원문:` <p> 2개",
    ),
    (
        "교정문 접두만 사라졌다",
        "final",
        lambda p, m: m["prefixCounts"].update(교정문=0),
        "`교정문:` <p> 0개",
    ),
    ("카드 수가 다르다", "final", lambda p, m: m["cards"].append(m["cards"][0]), "카드 <div> 2개"),
    (
        "카드의 <p> 가 3개가 아니다",
        "final",
        lambda p, m: m["cards"][0].update(pCount=2),
        "<p> 가 2개다",
    ),
    (
        "카드 라벨이 뒤바뀌었다",
        "final",
        lambda p, m: m["cards"][0].update(strongs=["교정문:", "원문:", None]),
        "라벨이",
    ),
    (
        "셋째 줄에 라벨이 붙었다",
        "final",
        lambda p, m: m["cards"][0].update(strongs=["원문:", "교정문:", "이유:"]),
        "셋째 줄에 라벨이 있다",
    ),
    (
        "셋째 줄이 비었다",
        "final",
        lambda p, m: m["cards"][0]["texts"].__setitem__(2, "   "),
        "셋째 줄이 비어 있다",
    ),
    (
        "이유가 API 와 다르다",
        "final",
        lambda p, m: m["cards"][0]["texts"].__setitem__(2, "다른 이유"),
        "셋째 줄 != API reason",
    ),
    (
        "API reason 이 빈 문자열이다 → BLOCKED 조건",
        "final",
        lambda p, m: p["corrections"][0].update(reason="  "),
        "reason 이 비었다",
    ),
    (
        "카드 원문이 그 교정과 다르다",
        "final",
        lambda p, m: m["cards"][0]["texts"].__setitem__(0, "원문: go to office"),
        "원문 줄이",
    ),
    # ⛔ 내비게이션 커밋 — `READ_JS` 가 url 을 담고도 아무도 단정하지 않던 자리다.
    (
        "이전 문서를 읽었다 (url 이 다른 세션)",
        "final",
        lambda p, m: m.update(url="http://localhost:3000/results/deadbeef"),
        "내비게이션 커밋 미확인",
    ),
    ("url 이 아예 없다", "final", lambda p, m: m.update(url=None), "내비게이션 커밋 미확인"),
]


@pytest.mark.parametrize("label,key,mutate,expected", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_each_mutation_is_caught(label, key, mutate, expected):
    payload, dom, sid = leg(key)
    mutate(payload, dom)
    _, fails = check_screen(payload, dom, sid)
    assert fails, f"{label}: 무력화했는데 어긋남이 0건이다 — 판별력이 없다"
    assert any(expected in m for m in fails), f"{label}: 다른 조건이 걸렸다 — {fails}"


MISSING_MUTATIONS = [
    ("오류 문구가 다르다", lambda m: m["firstDirectP"].update(text="어라"), "오류 문구가"),
    ("상태 라벨이 남아 있다", lambda m: m.update(labelsAnywhere=["확정"]), "상태 라벨이 남아 있다"),
    ("없는 세션인데 카드가 있다", lambda m: m["prefixCounts"].update(원문=1), "교정 카드가 있다"),
    ("첫 직계 <p> 가 없다", lambda m: m.update(firstDirectP=None), "첫 직계 <p> 가 없다"),
]


@pytest.mark.parametrize(
    "label,mutate,expected", MISSING_MUTATIONS, ids=[m[0] for m in MISSING_MUTATIONS]
)
def test_missing_session_mutations_are_caught(label, mutate, expected):
    """A3-2 — 없는 세션 화면의 단정도 무력화로 잰다."""
    dom = copy.deepcopy(load()["missing"])
    mutate(dom)
    _, fails = check_missing(dom)
    assert fails, f"{label}: 어긋남 0건"
    assert any(expected in m for m in fails), f"{label}: 다른 조건 — {fails}"


def test_sentinel_control_is_gone():
    """⛔ **회귀 방지** — 독립 판별력이 0인 sentinel 대조를 되살리지 마라.

    `third == reason` 이 참이면 `third != reason + "__SENTINEL__"` 는 **필연적으로** 참이다.
    그것을 반증하는 입력을 넣으면 등호가 함께 잡으므로 대조가 아니라 `checked` 부풀리기였다.
    """
    payload, dom, sid = leg("final")
    dom["cards"][0]["texts"][2] = payload["corrections"][0]["reason"] + "__SENTINEL__"
    _, fails = check_screen(payload, dom, sid)
    assert len(fails) == 1, f"등호 하나만 잡아야 한다 (sentinel 줄이 남아 있으면 2건) — {fails}"
    assert "셋째 줄 != API reason" in fails[0]
