"""C1(세션 관통) 판정 함수의 게이트 — A1-4·A1-5·A1-7 의 판별력을 코드로 고정한다.

`test_c3_gates.py`·`test_c5_gates.py` 와 같은 형태다: 판정 함수를 직접 불러 ① 정상 관측이
통과하고 ② **각 변이가 반드시 잡히는지** 센다.

⛔ **왜 이 파일이 필요한가** (`TASK-52`): `TASK-30` 회차 2 를 위임했다가 검증자가 산출물 직전에
API 오류로 죽어 **관측값을 전부 잃었다**(`H-AO` 재발). C1 은 단정이 9건으로 가장 많아 유실 비용이
가장 크고, 실행체 + 게이트가 있으면 유실이 **구조적으로** 불가능해진다.
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from c1_session_walkthrough import (  # noqa: E402
    APP_DEFECT_VERDICTS,
    EXPECTED_START_CALLS,
    UNMEASURABLE_VERDICTS,
    check_c1,
)


def observed_pass() -> dict:
    """정상 회차(톤 마이크)에서 실행체가 내야 하는 모양."""
    return {
        "silent_mic": False,
        "started": {"count": 3, "when": [0.0, 1.25, 2.5]},
        "final_lines": {"verdict": "PASS", "judgeable": True},
        "sent": {"audio": 146, "end_session": 1},
        "sentAudioNonZeroFrames": 146,
    }


def observed_silent() -> dict:
    """무음 회차 — A1-7 대체 대조. `audio` 는 **줄지 않고** 내용만 0 이 된다."""
    d = observed_pass()
    d["silent_mic"] = True
    d["sentAudioNonZeroFrames"] = 0
    return d


def test_clean_tone_round_passes():
    checked, fails = check_c1(observed_pass())
    assert fails == []
    assert checked >= 6


def test_clean_silent_round_passes():
    """⛔ 무음에서 `sent.audio` 가 0 이 되기를 기대하지 않는다 — 폐기된 갈래다."""
    checked, fails = check_c1(observed_silent())
    assert fails == [], f"무음 회차가 통과해야 한다 — {fails}"
    assert checked >= 6


# (라벨, 변이, 어긋남에 있어야 하는 조각)
MUTATIONS = [
    (
        "A1-4 재생 시작이 3회가 아니다",
        lambda d: d["started"].update({"count": 2, "when": [0.0, 1.25]}),
        "재생 시작",
    ),
    (
        "A1-4 when 이 전부 같다 (대조 ② 무력화 · 상수 스케줄)",
        lambda d: d["started"].update({"when": [1.0, 1.0, 1.0]}),
        "when",
    ),
    (
        "A1-4 when 개수가 count 와 어긋난다 (계측 퇴화)",
        lambda d: d["started"].update({"when": [0.0, 1.25]}),
        "when",
    ),
    (
        "A1-5 앱이 덜 그렸다",
        lambda d: d["final_lines"].update({"verdict": "APP_UNDER_RENDER"}),
        "APP_UNDER_RENDER",
    ),
    (
        "A1-5 본문이 어긋났다",
        lambda d: d["final_lines"].update({"verdict": "APP_CONTENT_MISMATCH"}),
        "APP_CONTENT_MISMATCH",
    ),
    (
        "A1-7 실제 송신이 0이다",
        lambda d: d["sent"].update({"audio": 0}),
        "audio",
    ),
    (
        "A1-7 end_session 이 0이다 (후킹 고장 — audio 0 의 원인을 가르는 값)",
        lambda d: d["sent"].update({"end_session": 0}),
        "end_session",
    ),
    (
        "A1-7 톤인데 PCM 내용이 전부 0이다 (마이크가 죽었다)",
        lambda d: d.update({"sentAudioNonZeroFrames": 0}),
        "nonZero",
    ),
]


@pytest.mark.parametrize("label,mutate,expected", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_each_mutation_is_caught(label, mutate, expected):
    """⛔ 이것이 판별력이다 — 무력화에서 반드시 어긋남이 나야 한다."""
    d = copy.deepcopy(observed_pass())
    mutate(d)
    _, fails = check_c1(d)
    assert fails, f"{label}: 변이를 넣었는데 어긋남이 0건이다 — 판별력이 없다"
    assert any(expected in f for f in fails), f"{label}: 어긋남에 {expected!r} 이 없다 — {fails}"


def test_silent_round_catches_nonzero_pcm():
    """무음인데 내용이 남아 있으면 그것이 대조 실패다 — `silentMic` 이 안 먹은 것이다."""
    d = observed_silent()
    d["sentAudioNonZeroFrames"] = 12
    _, fails = check_c1(d)
    assert fails
    assert any("nonZero" in f for f in fails)


def test_unmeasurable_verdict_is_not_a_pass_and_not_an_app_defect():
    """`UNMEASURABLE_*`·`HARNESS_*` 는 **앱 결함이 아니고 PASS 도 아니다** — 그 구분을 고정한다."""
    for verdict in sorted(UNMEASURABLE_VERDICTS):
        d = observed_pass()
        d["final_lines"] = {"verdict": verdict, "judgeable": False}
        _, fails = check_c1(d)
        assert fails, f"{verdict}: 측정 불가인데 통과했다"
        assert any("측정 불가" in f for f in fails), f"{verdict}: 앱 결함으로 분류됐다 — {fails}"


def test_app_defect_verdicts_are_labeled_as_such():
    for verdict in sorted(APP_DEFECT_VERDICTS):
        d = observed_pass()
        d["final_lines"] = {"verdict": verdict, "judgeable": True}
        _, fails = check_c1(d)
        assert any(verdict in f for f in fails)


def test_missing_keys_are_reported_not_ignored():
    """빈 입력이 조용히 통과하면 실행체가 아무것도 안 해도 PASS 가 된다."""
    _, fails = check_c1({})
    assert fails
    d = observed_pass()
    del d["final_lines"]
    _, fails = check_c1(d)
    assert fails


def test_expected_start_calls_matches_fixture_turns():
    """A1-4 기대값 3 은 픽스처 연역이다(ⓐ) — 픽스처가 바뀌면 여기서 죽어야 한다."""
    import re

    src = (Path(__file__).parents[2] / "app/backend/app/audio_gateway/fixtures.py").read_text(
        encoding="utf-8"
    )
    block = re.search(r"FIXTURE_TURNS[^=]*=\s*\[(.*?)\n\]", src, re.S)
    assert block, "fixtures.py 에서 FIXTURE_TURNS 를 찾지 못했다"
    turns = re.findall(r'\(\s*"', block.group(1))
    assert len(turns) == EXPECTED_START_CALLS, (
        f"픽스처 턴 수가 {len(turns)} 인데 기대 재생 시작이 {EXPECTED_START_CALLS} 다 — "
        "둘은 같아야 한다(프레임당 노드 1개 · `start` 1회)"
    )
