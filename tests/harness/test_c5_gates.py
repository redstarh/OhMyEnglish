"""C5(발음 배지) 판정 함수의 게이트 — 판별력을 코드로 고정한다.

`test_c3_gates.py` 와 같은 형태다: 판정 함수를 직접 불러 ① 정상 관측이 통과하고 ② **각 변이가
반드시 잡히는지** 센다. 실행체가 조용히 퇴화하면 여기서 죽는다.

⛔ **왜 이 파일이 필요한가** (`TASK-49`): C5 만 실행체가 없어서 판정을 대화형 왕복으로 해야 했고,
이 환경의 라운드트립(실측 20,635 ms)이 주입 창(10,000 ms)을 **반드시 넘긴다.** 그래서 5차수는
같은 문서에서 재시도를 합성 클릭하는 우회로 성립시켰고 **A5-1 의 음성 대조 ①(주입 전 배지 부재)이
오염됐다.** 한 프로세스 안에서 주입·판독을 끝내면 그 오염이 원리적으로 사라진다.

기대 문구는 **ⓒ 하드코딩**이다 — 화면이 소유하는 한국어이고 프레임은 기계값 `outcome` 만 나른다.
정본은 `app/frontend/app/page.tsx` 의 `PRONUNCIATION_BADGE` 다.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from c5_pronunciation_badge import BADGE_TEXT, SENTINEL, check_badges  # noqa: E402


def observed_pass() -> dict:
    """실행체가 정상 회차에서 내야 하는 모양. 네 outcome 을 순차 주입한 결과다."""
    return {
        "before_injection": {"badge_count": 0},
        "sequence": [
            {
                "outcome": outcome,
                "badge_count": 1,
                "text": text,
                "sentinel_hits": 0,
            }
            for outcome, text in BADGE_TEXT.items()
        ],
    }


def test_clean_observation_passes():
    checked, fails = check_badges(observed_pass())
    assert fails == []
    # 단정이 실제로 여러 건 세어졌는지 — 0건이면 통과가 항진명제다
    assert checked >= 4


# (라벨, 변이 함수, 어긋남 메시지에 있어야 하는 조각)
MUTATIONS = [
    (
        "주입 전에 배지가 이미 있다 (대조 ① 무력화)",
        lambda d: d["before_injection"].update({"badge_count": 1}),
        "주입 전",
    ),
    (
        "배지 요소가 2개다 (4종을 전부 렌더하는 경로)",
        lambda d: d["sequence"][0].update({"badge_count": 2}),
        "정확히 1개",
    ),
    (
        "배지가 사라졌다",
        lambda d: d["sequence"][2].update({"badge_count": 0}),
        "정확히 1개",
    ),
    (
        "문구가 다른 outcome 것이다 (뒤바뀜)",
        lambda d: d["sequence"][1].update({"text": BADGE_TEXT["incorrect"]}),
        "문구가",
    ),
    (
        "문구에 군더더기가 붙었다 (포함 검사라면 통과한다)",
        lambda d: d["sequence"][3].update({"text": BADGE_TEXT["unclear"] + " 어쩌구"}),
        "문구가",
    ),
    (
        "네 문구가 전부 같다 (상수를 렌더한다 · 대조 ② 무력화)",
        lambda d: [item.update({"text": BADGE_TEXT["pending"]}) for item in d["sequence"]],
        "서로 달라야",
    ),
    (
        "target_sound 가 화면에 새어 나왔다 (A5-2)",
        lambda d: d["sequence"][0].update({"sentinel_hits": 1}),
        "sentinel",
    ),
]


@pytest.mark.parametrize("label,mutate,expected", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_each_mutation_is_caught(label, mutate, expected):
    """⛔ 이것이 판별력이다 — 무력화에서 반드시 어긋남이 나야 한다."""
    d = copy.deepcopy(observed_pass())
    mutate(d)
    _, fails = check_badges(d)
    assert fails, f"{label}: 변이를 넣었는데 어긋남이 0건이다 — 판별력이 없다"
    assert any(expected in f for f in fails), f"{label}: 어긋남에 {expected!r} 이 없다 — {fails}"


def test_missing_keys_are_reported_not_ignored():
    """관측이 비면 통과가 아니라 어긋남이다 — 빈 입력이 조용히 PASS 되는 경로를 닫는다."""
    _, fails = check_badges({})
    assert fails
    _, fails = check_badges({"before_injection": {"badge_count": 0}, "sequence": []})
    assert fails, "주입 결과가 0건인데 통과했다 — 실행체가 아무것도 안 해도 PASS 가 된다"


def test_sequence_must_cover_all_four_outcomes():
    d = observed_pass()
    d["sequence"] = d["sequence"][:3]
    _, fails = check_badges(d)
    assert fails


def test_sentinel_is_not_a_real_target_sound():
    """sentinel 은 앱이 실제로 쓰는 값과 겹치면 안 된다 — 겹치면 A5-2 가 거짓 실패를 낸다."""
    assert SENTINEL
    assert "_" in SENTINEL or SENTINEL.isupper()
    assert SENTINEL not in BADGE_TEXT.values()
