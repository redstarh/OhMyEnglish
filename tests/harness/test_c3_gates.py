"""`c3_results_screen.py`의 판정 게이트가 **실제로 FAIL을 내는지** 잰다.

**왜 이 파일이 있는가**: C3 실행체는 「처음부터 게이트를 넣었다」로 만들었는데 그래도 리뷰가
**공허 통과 하나를 실증했다** — `final`에서 `corrections` 키를 지우고 화면도 0장이면 `checked`가
14 → **6**으로 줄고 **어긋남 0건**이 됐다(A4-1·A4-2 전체가 조용히 사라지는데 FAIL이 아니다).
그 형태를 회귀로 못 박는 것이 이 파일의 첫 목적이다.

⚠️ **입력은 실제 회차의 판독값이다** — 어느 회차인지는 **아래 `REAL` 하나가 갖는다.**
⛔ **여기에 파일 이름을 적지 않는다** — 2026-09-09 에 픽스처를 두 번 갈면서 이 자리가 **두 번
낡았다.** 이름을 두 곳에 두면 한쪽이 조용히 거짓이 되므로 가리키기만 한다.
손으로 만든 픽스처는 데이터 생성 경로의 결함에 눈이 먼다(`H-AF`). 그 위에 **한 필드씩** 변이를
얹는다.

⛔ **2026-09-09 에 픽스처를 갈았다 — 값을 고친 것이 아니라 회차를 다시 돌렸다.** `TASK-55` 가 없는
세션 화면의 문구를 `결과 API가 404을 반환했습니다`에서 학습자 언어로 바꿨고, `TASK-57` 이 부분 실패
안내의 문체를 통일했다. **앱의 계약이 바뀌면 낡는 것은 게이트가 아니라 관측값이다** — 그래서
브라우저 다리를 다시 돌려 새 판독을 얻었고(어긋남 0 / 단정 58건), `TASK-64` 가 A3-1 오탐을 없앤
뒤 **교정 2건 세션을 여섯째로 넣어 한 번 더** 돌렸다(어긋남 0 / 단정 82건 · 미확인 0). 이전 회차
둘은 **그 시점의 기록이므로 지우지 않았다.**

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

from c3_results_screen import (  # noqa: E402
    DRILL_SHORTFALL_NOTICE,
    check_drill_contract,
    check_missing,
    check_screen,
    check_status_label_variation,
)

REAL = HARNESS / "runs" / "2026-09-09-c3-dom-read-post-task34.json"
SESSION_IDS = {
    "analyzing": "210233be-ecaa-4409-a1af-8b7016cfe7e9",
    "final": "6225ddaf-90a8-43af-9aa8-e003921c75eb",
    # ⛔ **`final` 상태의 둘째 세션 — 교정이 2건이다** (`TASK-64` 가 이 자리를 열었다).
    #    `browser_leg.md` §11-9 가 요구한 표본이고, `check_screen` 의 주석이 지목한
    #    「`corrections` 키를 잃으면 A4-1·A4-2 가 조용히 사라진다」는 마스크를 이 세션이 벗긴다:
    #    하나가 키를 잃어도 primary 가 남는다. 이전에는 A3-1 음성 대조가 같은 상태의 세션 둘을
    #    오탐해서 이 표본을 넣을 수 없었다.
    "final_two": "e0c5e580-dfc0-4793-b02d-54cf4346c3c5",
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


def test_fixture_keeps_a_two_correction_session():
    """⛔ **A4-2 표본이 픽스처에서 사라지는 것을 막는다** (`browser_leg.md` §11-9 · `TASK-64`).

    교정 **2건 이상**인 세션이 없으면 A4-2 기대값 교차 대조가 「카드 1장 대 교정 1건」으로 줄어
    카드끼리 뒤바뀜을 검출하지 못한다. 픽스처를 새 회차로 갈 때 그 세션을 빼먹으면
    **어긋남 0건으로 조용히 통과**하므로 그 조건 자체를 단정한다.
    """
    d = load()
    counts = {k: len(v.get("corrections", [])) for k, v in d["api"].items()}
    assert max(counts.values()) >= 2, f"교정 2건 이상인 세션이 없다 — {counts}"


def test_real_round_passes_every_state():
    """green — 모든 상태 화면이 통과하고 **검사 수가 0이 아니다**."""
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
    # ⛔ **이 변이가 「기계 낱말 부재」 단정의 독립 판별력을 실증한다** (TASK-55). 첫 직계 `<p>` 는
    #    기대 문구 그대로 두고 **둘째 줄로** 상태 코드를 흘린다 → 등호는 통과하고 이 단정만 잡는다.
    #    잡지 못하면 그 단정은 등호의 종속절이므로 지워야 한다
    #    (`test_sentinel_control_is_gone` 이 같은 이유로 있다).
    (
        "상태 코드가 다른 줄로 새어 나왔다",
        lambda m: m.update(
            directPTexts=[m["firstDirectP"]["text"], "결과 API가 404을 반환했습니다"]
        ),
        "기계 낱말이 새어 나왔다",
    ),
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


def test_machine_word_check_has_independent_discrimination():
    """⛔ **TASK-55 의 단정이 등호의 종속절이 아님을 잰다.**

    `firstDirectP` 등호를 **만족시킨 채** 둘째 줄로만 상태 코드를 흘린다. 어긋남이 **정확히 1건**
    이어야 한다 — 2건이면 등호가 함께 잡은 것이므로 그 단정은 `checked` 부풀리기이고 지워야 한다
    (`test_sentinel_control_is_gone` 이 같은 이유로 존재한다).
    """
    dom = copy.deepcopy(load()["missing"])
    dom["directPTexts"] = [dom["firstDirectP"]["text"], "결과 API가 404을 반환했습니다"]
    _, fails = check_missing(dom)
    assert len(fails) == 1, f"이 단정만 잡아야 한다 — {fails}"
    assert "기계 낱말이 새어 나왔다" in fails[0]


# ── A3-1 음성 대조 (`TASK-64`) ────────────────────────────────────────────────────
# ⛔ **이 묶음의 첫 목적은 오탐 회귀 방지다.** 이전 판은 세션 목록의 중복을 봐서 같은 상태의
#    세션 둘을 FAIL 로 냈고, 그 오탐이 `browser_leg.md` §11-9(교정 2건 이상 세션 추가)를 막고
#    있었다. 그래서 「겹쳐도 통과」와 「겹치면 FAIL」을 **둘 다** 못 박는다.


def variation_legs() -> tuple[dict, dict, dict]:
    """실제 회차의 다섯 상태를 `(payloads, results, sessions)` 로 낸다."""
    d = load()
    return d["api"], d["dom"], dict(SESSION_IDS)


def test_variation_passes_on_real_round():
    payloads, results, sessions = variation_legs()
    checked, fails, unverified = check_status_label_variation(payloads, results, sessions)
    assert fails == [], fails
    assert unverified is None
    assert checked == 2, checked


def test_same_status_twice_is_not_a_failure():
    """⛔ **TASK-64 가 고친 오탐 그 자체다.** 같은 상태의 세션이 여럿이면 라벨이 정당하게 겹친다.

    실물 회차가 이미 `final` 을 둘 담으므로(`SESSION_IDS`) 위 `test_variation_passes_on_real_round`
    가 그것을 덮는다. 여기서는 **셋째**를 얹어 「겹침 수가 늘어도 통과」인 것까지 못 박는다 —
    이전 판은 겹침이 하나라도 있으면 FAIL 이었다.
    """
    payloads, results, sessions = variation_legs()
    payloads = {**payloads, "final_three": copy.deepcopy(payloads["final"])}
    results = {**results, "final_three": copy.deepcopy(results["final"])}
    sessions = {**sessions, "final_three": SESSION_IDS["final"]}
    checked, fails, unverified = check_status_label_variation(payloads, results, sessions)
    assert fails == [], f"같은 상태의 세션 셋을 오탐했다 — {fails}"
    assert unverified is None and checked == 2


def test_two_statuses_sharing_one_label_is_caught():
    """음성 대조의 본래 목적 — 상수를 렌더하면 서로 다른 상태가 같은 문구를 낸다."""
    payloads, results, sessions = variation_legs()
    results = copy.deepcopy(results)
    results["analyzing"]["firstDirectP"]["text"] = results["final"]["firstDirectP"]["text"]
    _, fails, unverified = check_status_label_variation(payloads, results, sessions)
    assert unverified is None
    assert any("서로 다른 상태가 같은 문구를 냈다" in m for m in fails), fails


def test_same_status_with_two_labels_is_caught():
    """화면이 status 의 함수가 아니면 잡는다 — 같은 상태가 두 문구를 낸 경우."""
    payloads, results, sessions = variation_legs()
    payloads = {**payloads, "final_three": copy.deepcopy(payloads["final"])}
    other = copy.deepcopy(results["final"])
    other["firstDirectP"]["text"] = "확정됨"
    results = {**results, "final_three": other}
    sessions = {**sessions, "final_three": SESSION_IDS["final"]}
    _, fails, unverified = check_status_label_variation(payloads, results, sessions)
    assert unverified is None
    assert any("같은 상태가 서로 다른 문구를 냈다" in m for m in fails), fails


def test_single_status_is_unverified_not_pass():
    """⛔ **항진명제를 PASS 로 세지 않는다** (C3 검토 ③의 근거를 상태 단위로 계승한다)."""
    payloads, results, sessions = variation_legs()
    one = {"final": sessions["final"]}
    checked, fails, unverified = check_status_label_variation(payloads, results, one)
    assert fails == []
    assert checked == 0, "미평가인데 검사 수를 세면 PASS 가 부풀려진다"
    assert unverified is not None and "2종 이상에서만" in unverified


# ── 드릴 계약 (`TASK-34` · 캡틴 결정 10·18) ──────────────────────────────────────
# ⛔ **AC1 이 요구하는 것은 「단정을 넣었다」가 아니라 「무력화에서 실제로 FAIL 한다」다.**
#    그래서 숫자를 **일부러 렌더한** 입력을 넣어 FAIL 을 관측한다. 그리고 그 단정이 잡음
#    생성기가 아님을 **음성 대조**로 함께 보인다 — API 가 준 문구의 숫자는 오탐하지 않는다.


def test_drill_contract_passes_on_real_round():
    """green — 실물 판독의 여섯 화면 전부 통과한다."""
    for key in SESSION_IDS:
        payload, dom, _ = leg(key)
        checked, fails, _ = check_drill_contract(payload, dom)
        assert fails == [], f"[{key}] {fails}"
        assert checked == 2, f"[{key}] 검사 {checked}건"


def test_drill_numbers_rendered_is_caught():
    """⛔ **AC1** — 두 수를 화면에 그리면 잡는다. `final_two` 의 drill 은 2 / 20 이다."""
    payload, dom, _ = leg("final_two")
    assert payload["drill"] == {"exchanges_observed": 2, "exchanges_expected": 20}, payload["drill"]
    dom["mainText"] += " 2 / 20"
    _, fails, _ = check_drill_contract(payload, dom)
    assert any("API 가 주지 않은 숫자가 있다" in m for m in fails), fails
    assert any("'2'" in m and "'20'" in m for m in fails), (
        f"새어 나온 수를 이름으로 적어야 한다 — {fails}"
    )


def test_other_number_leak_is_caught():
    """드릴 두 수만이 아니라 **모든** 숫자 누출을 잡는다 — `occurrences` 가 새는 경로."""
    payload, dom, _ = leg("final")
    dom["mainText"] += " 2회"
    _, fails, _ = check_drill_contract(payload, dom)
    assert any("API 가 주지 않은 숫자가 있다" in m for m in fails), fails


def test_api_supplied_number_is_not_a_false_positive():
    """⛔ **음성 대조** — API 가 실어 보낸 교정 문구의 숫자는 오탐하지 않는다.

    이것이 없으면 「숫자가 하나도 없다」로 재는 것과 구별되지 않고, 교정문에 연도가 든 세션에서
    게이트가 잡음 생성기가 된다.
    """
    payload, dom, _ = leg("final")
    payload["corrections"][0]["reason"] += " 2026년 표기입니다."
    dom["mainText"] += " 2026년 표기입니다."
    _, fails, _ = check_drill_contract(payload, dom)
    assert fails == [], f"API 가 준 숫자를 오탐했다 — {fails}"


def test_shortfall_notice_missing_is_caught():
    payload, dom, _ = leg("final_two")
    dom["mainText"] = dom["mainText"].replace(DRILL_SHORTFALL_NOTICE, "")
    _, fails, _ = check_drill_contract(payload, dom)
    assert any("드릴 미달 안내 존재" in m for m in fails), fails


def test_shortfall_notice_on_a_met_session_is_caught():
    """⛔ **AC2** — 달성 세션에 문장이 그려지면 잡는다. 달성 문장도 점수판이 된다(결정 10)."""
    payload, dom, _ = leg("final_two")
    payload["drill"] = {"exchanges_observed": 20, "exchanges_expected": 20}
    _, fails, unverified = check_drill_contract(payload, dom)
    assert any("드릴 미달 안내 존재" in m for m in fails), fails
    assert unverified is None, "달성 표본이면 미확인이 아니다"


def test_drillless_session_requires_no_notice():
    """`drill` 키가 없는 상태에서 문장이 그려지면 잡는다 — 서버 계약이 깨진 경우다."""
    payload, dom, _ = leg("analyzing")
    assert "drill" not in payload
    dom["mainText"] += DRILL_SHORTFALL_NOTICE
    _, fails, _ = check_drill_contract(payload, dom)
    assert any("드릴 미달 안내 존재" in m for m in fails), fails


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
