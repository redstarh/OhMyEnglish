"""`c2_render_hierarchy.py`의 판정 게이트가 **실제로 FAIL을 내는지** 잰다.

**왜 이 파일이 있는가**: 2026-09-06 리뷰(HIGH-1·MEDIUM-1)가 그 실행체의 첫 판을 뚫었다 — 값을
**인쇄만** 하고 아무것도 비교하지 않아서, 사람이 rgb 문자열을 눈으로 대조하지 않으면 PASS가
공허해졌다. 게이트를 넣은 뒤에도 **"게이트가 있다"는 "게이트가 판별력을 갖는다"가 아니다**
(`browser_leg.md` §5 ⛔ 상자와 같은 규약). 그래서 조건마다 **무력화 입력을 넣어 FAIL을 관측한다.**

⚠️ **입력은 합성이 아니라 실제 회차의 반환값이다** — `runs/2026-09-06-t3-c2-eval-return.json`.
손으로 만든 픽스처는 **데이터 생성 경로의 결함에 눈이 먼다**(함정 `H-AF`가 그 형태였다).
그 실물 위에 **한 필드씩** 변이를 얹어 어긋남이 그 조건에서만 나오는지 본다.

✅ **이 파일은 게이트 안이다 — 규약이 아니라 구조가 지킨다.**
`app/backend/pyproject.toml:33`의 `testpaths = ["../../tests"]`가 리포의 `tests/`를 가리키므로
`.venv/bin/pytest -q`가 이 파일을 **수집한다**(실측: 595 → **618 passed**, 정확히 이 파일의 23건).
그래서 함정 `H-AA`("게이트 밖 스크립트는 조용히 낡는다")가 이 파일에는 **적용되지 않는다.**

⚠️ **이 문단의 첫 판은 정반대를 적었다** — "게이트 밖이다, 그래서 문서 규약으로 지킨다".
게이트 수치가 **595에서 618로 뛴 것**이 그 서술을 반증했다. 규약으로 지킬 필요가 없는 것을
규약으로 지킨다고 적으면 다음 세션이 **없는 위험을 관리하고 진짜 위험을 놓친다.**

실행(단독으로 돌릴 때):
    cd app/backend && .venv/bin/pytest ../../tests/harness/test_c2_gates.py -q
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS))

import c2_render_hierarchy as c2  # noqa: E402
from c2_render_hierarchy import (  # noqa: E402
    check_cross,
    check_leg,
    classify_failure,
    find_target,
)

REAL = HARNESS / "runs" / "2026-09-06-t3-c2-eval-return.json"


def load() -> list[dict]:
    data = json.loads(REAL.read_text(encoding="utf-8"))
    assert len(data) == 2, f"실물 회차 파일이 2모드여야 한다 — {len(data)}건"
    return data


def test_real_round_passes_and_checks_a_nonzero_number_of_assertions():
    """green — 실물 회차는 통과한다. **검사한 수가 0이 아닌 것을 함께 단정한다.**

    0건을 검사하고 통과를 단정하는 것이 이 리포의 지배 실패 모드다.
    """
    data = load()
    total = 0
    for d in data:
        checked, fails = check_leg(d, "both")
        assert fails == [], f"[{d['emulated']}] 실물 회차가 어긋났다: {fails}"
        assert checked >= 20, f"검사한 단정이 {checked}건뿐이다 — 게이트가 비어 있다"
        total += checked
    checked, fails = check_cross(data)
    assert fails == []
    total += checked
    assert total >= 40, f"전체 검사 수가 {total}건뿐이다"


# (변이를 얹는 함수, 어긋남 메시지에 들어 있어야 하는 조각) — 조각은 그 조건을 특정한다.
MUTATIONS: list[tuple[str, object, str]] = [
    # ⛔ HIGH-1 이 지목한 바로 그 구멍: 두 토큰이 같아지면 위계 단정이 항진명제가 된다.
    (
        "두 토큰이 같은 값으로 회귀",
        lambda d: d["probe"].update(fg1=d["probe"]["muted1"], fg2=d["probe"]["muted1"]),
        "A2-2 대조 ②",
    ),
    # ⛔ MEDIUM-1: §6-0 이 게이트가 아니라 출력이었다.
    (
        "주입 전 접두 <p>가 이미 있다",
        lambda d: d["beforeInject"].update(prefixedCount=1),
        "§6-0 위반",
    ),
    (
        "컨테이너 마운트 증거가 없다",
        lambda d: d["beforeInject"].update(waitingTextPresent=False),
        "§6-0 의 0개가 공허하다",
    ),
    ("주입 전에 창을 넘겼다", lambda d: d["beforeInject"].update(reasonPs=1), "창 이탈: 주입 전"),
    (
        "partial 판독 시점에 창을 넘겼다",
        lambda d: d["partial"].update(reasonPs=1),
        "창 이탈: partial 판독",
    ),
    (
        "probe 재판독이 갈렸다",
        lambda d: d["probe"].update(muted2="rgb(1, 2, 3)"),
        "같은 모드 재판독이 갈렸다: muted",
    ),
    ("probe 가 빈 문자열", lambda d: d["probe"].update(muted1=""), "rgb 문자열이 아니다"),
    (
        "partial 이 foreground 로 렌더됐다",
        lambda d: d["partial"].update(color=d["probe"]["fg1"]),
        "A2-1: partial 색",
    ),
    ("partial 줄이 2개다", lambda d: d["partial"].update(count=2), "A2-1: partial 주입 후"),
    (
        "확정 줄이 muted 로 렌더됐다",
        lambda d: d["final"].update(color=d["probe"]["muted1"]),
        "A2-2: 확정 색",
    ),
    (
        "partial 줄이 사라지지 않았다",
        lambda d: d["final"].update(partialTextStillPresent=True),
        "partial 문구가 문서에 남아",
    ),
    ("확정 줄이 통째로 없다", lambda d: d.update(final=None), "final 이 비었다"),
    (
        "어댑터가 stub 이었다 (경쟁 프레임)",
        lambda d: d["omy"]["recv"].update(partial=6),
        "경쟁 프레임: recv.partial",
    ),
    (
        "한 문서에 세션이 둘",
        lambda d: d["omy"]["recv"].update(session_started=2),
        "세션이 하나여야 한다",
    ),
    (
        "앱 핸들러가 안 붙었다",
        lambda d: d["omy"].update(appHandlerAttached=False),
        "onmessage 핸들러가 붙지 않았다",
    ),
    ("주입 수가 모자라다", lambda d: d["omy"].update(injected=1), "주입 수가 1다"),
    ("초과 렌더", lambda d: d["omy"].update(snapshotCounts=[0, 1, 2, 1]), "초과 렌더"),
    ("적립이 비었다", lambda d: d["omy"].update(snapshotCounts=[]), "snapshotCounts 가 비었다"),
    (
        "모드 에뮬레이션이 안 걸렸다",
        lambda d: d.update(scheme="light", emulated="dark"),
        "모드 불일치",
    ),
    # ── ⛔ 아래 8건은 **재검토가 "판별력 미관측"으로 지목한 조건들**이다 (2026-09-06 ③).
    #    리뷰어가 독립 변이로 게이트가 잡는 것을 확인해 줬지만, **테스트가 보지 않으면 다음 변이에
    #    눈이 먼다.** 특히 `final["count"]` 와 `partial.color` rgb 가드는 대칭 논거로
    #    넘어가지 않는다:
    #    앞의 것은 `partial["count"]` 와 **다른 코드 경로**(`if final is not None` 안)이고,
    #    뒤의 것은 이 커밋이 새로 넣은 공허 통과 방어인데 형제(probe 쪽)만 덮여 있었다.
    ("probe.muted2 가 비-rgb", lambda d: d["probe"].update(muted2=None), "probe.muted2 가 rgb"),
    ("probe.fg1 가 비-rgb", lambda d: d["probe"].update(fg1=None), "probe.fg1 가 rgb"),
    ("probe.fg2 가 비-rgb", lambda d: d["probe"].update(fg2=123), "probe.fg2 가 rgb"),
    (
        "partial.color 가 비-rgb",
        lambda d: d["partial"].update(color=None),
        "partial.color 가 rgb 문자열이 아니다",
    ),
    (
        "fg 재판독이 갈렸다",
        lambda d: d["probe"].update(fg2="rgb(9, 9, 9)"),
        "같은 모드 재판독이 갈렸다: fg",
    ),
    ("확정 줄이 2개다", lambda d: d["final"].update(count=2), "A2-2: final 주입 후"),
    (
        "final 판독 시점에 창을 넘겼다",
        lambda d: d["final"].update(reasonPs=1),
        "창 이탈: final 판독",
    ),
    (
        "경쟁 프레임 recv.final",
        lambda d: d["omy"]["recv"].update(final=6),
        "경쟁 프레임: recv.final",
    ),
    # ⚠️ **등호가 `None == None` 으로 공허하게 참이 되는 조합** — rgb 가드가 먼저 잡는지 본다.
    (
        "partial.color 와 muted1 이 둘 다 None",
        lambda d: (d["partial"].update(color=None), d["probe"].update(muted1=None)),
        "rgb 문자열이 아니다",
    ),
    (
        "final.color 와 fg1 이 둘 다 None",
        lambda d: (d["final"].update(color=None), d["probe"].update(fg1=None)),
        "probe.fg1 가 rgb",
    ),
]


@pytest.mark.parametrize("label,mutate,expected", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_each_mutation_is_caught(label, mutate, expected):
    """red — 무력화마다 **그 조건이** 어긋나야 한다. 메시지 조각으로 조건을 특정한다."""
    d = copy.deepcopy(load()[0])
    mutate(d)
    _, fails = check_leg(d, "both")
    assert fails, f"{label}: 무력화했는데 어긋남이 0건이다 — 이 조건은 판별력이 없다"
    assert any(expected in m for m in fails), (
        f"{label}: 기대한 조건이 아니라 다른 것이 걸렸다 — {fails}"
    )


def test_cross_mode_control_catches_emulation_not_applied():
    """red — 두 모드의 토큰이 같아지면 A2-3 이 잡는다(모드 전환이 안 걸린 경우)."""
    data = copy.deepcopy(load())
    data[1]["probe"].update(muted1=data[0]["probe"]["muted1"], fg1=data[0]["probe"]["fg1"])
    _, fails = check_cross(data)
    assert any("두 모드의 muted 가 같다" in m for m in fails), fails
    assert any("두 모드의 foreground 가 같다" in m for m in fails), fails


def test_single_mode_run_is_not_a_pass():
    """red — 모드 하나만 돌면 A2-3 은 **평가할 수 없다.** §10: 판별력 미확인은 PASS 가 아니다."""
    checked, fails = check_cross([copy.deepcopy(load()[0])])
    assert checked == 0
    assert any("A2-3 미평가" in m for m in fails), fails


def test_partial_phase_expects_no_final_line():
    """partial 회차는 final 이 없는 것이 정상이고, 판정 회차에서는 그것이 어긋남이다."""
    partial_file = HARNESS / "runs" / "2026-09-06-t3-c2-eval-return-partial.json"
    data = json.loads(partial_file.read_text(encoding="utf-8"))
    for d in data:
        checked, fails = check_leg(d, "partial")
        assert fails == [], f"[{d['emulated']}] partial 회차가 어긋났다: {fails}"
        assert checked >= 20
    # 같은 데이터를 판정 회차로 재면 final 부재가 잡혀야 한다.
    _, fails = check_leg(copy.deepcopy(data[0]), "both")
    assert any("final 이 비었다" in m for m in fails), fails


# ── `classify_failure` — 분기 순서가 판별력 전부인 함수다. **첫 판의 판별 문구가 실제로 틀렸고**
#    (`socketUrls` 공백을 배경 탭의 지표로 적었다) 팀리드가 반례를 만들어 반증했다. 재검토는
#    거기서 **갈래 2의 의미가 도달 불가**이고 **창 이탈 갈래가 빠졌다**고 더 지적했다.
#    그래서 갈래마다 픽스처를 박아 둔다 — 순서가 바뀌면 여기서 red 가 난다.
def _omy(**over) -> dict:
    base = {
        "resumeLog": [{"at": 1, "afterAwait": "running"}, {"at": 2, "afterAwait": "running"}],
        "appHandlerAttached": True,
        "recv": {"session_started": 1, "session_failed": 0, "partial": 0, "final": 0},
        "socketUrls": [],
    }
    base.update(over)
    return base


CLASSIFY_CASES = [
    # (라벨, 계측 상태, 결과에 들어 있어야 하는 조각)
    ("배경 탭 — resumeLog 1건", _omy(resumeLog=[{"at": 1}]), "클릭이 페이지에 닿지 않았다"),
    ("resumeLog 0건도 같은 갈래", _omy(resumeLog=[]), "클릭이 페이지에 닿지 않았다"),
    (
        "핸들러 미부착 — getUserMedia~소켓 사이",
        _omy(appHandlerAttached=False),
        "page.tsx:177`~`:185",
    ),
    (
        "백엔드 부재 — 서버 프레임 0건",
        _omy(recv={"session_started": 0, "session_failed": 0}),
        "백엔드가 없거나 연결이 실패했다",
    ),
    (
        "창 이탈 — session_failed 가 왔다",
        _omy(recv={"session_started": 1, "session_failed": 1}),
        "주입 창을 넘겼다",
    ),
    (
        "세션 정상 종료 — 어댑터 모드 오선택",
        _omy(recv={"session_started": 1, "session_failed": 0, "session_ended": 1}),
        "어댑터가 `stub_unresponsive` 가 아니다",
    ),
    (
        "한 문서 두 세션",
        _omy(recv={"session_started": 2, "session_failed": 0, "session_ended": 0}),
        "한 문서 한 세션 규약 위반",
    ),
    (
        "셋 다 정상 — H-AE 나 세션 길이",
        _omy(),
        "`H-AH`도 백엔드 부재도 창 이탈도 아니다",
    ),
]


@pytest.mark.parametrize("label,omy,expected", CLASSIFY_CASES, ids=[c[0] for c in CLASSIFY_CASES])
def test_classify_failure_branches(label, omy, expected):
    """갈래마다 **그 갈래로** 떨어지는지 본다. 순서를 바꾸면 여기서 깨진다."""
    got = classify_failure(copy.deepcopy(omy))
    assert expected in got, f"{label}: 기대한 갈래가 아니다 — {got}"


def test_classify_failure_branches_are_mutually_exclusive():
    """⚠️ 상류 조건이 하류를 **가려야** 한다 — 배경 탭이면 나머지 신호와 무관하게 그 갈래다."""
    both = _omy(resumeLog=[{"at": 1}], recv={"session_started": 0, "session_failed": 1})
    assert "클릭이 페이지에 닿지 않았다" in classify_failure(both)


def test_classify_failure_does_not_claim_voiceio_start():
    """⛔ **회귀 방지** — 갈래 2에 `VoiceIo.start` 를 되살리지 마라.

    `page.tsx` 순서상 그 실패는 소켓 **뒤**(`:205`)라 `appHandlerAttached=true` 를 남기므로
    이 갈래에 **절대 오지 않는다**(재검토 ①). 문구를 되살리면 읽는 사람을 엉뚱한 줄로 보낸다.
    """
    got = classify_failure(_omy(appHandlerAttached=False))
    assert "VoiceIo.start" not in got, got


# ── `find_target` 우선순위 — 리뷰가 1차부터 요구한 테스트다. **MEDIUM-2 가 여기서 났다**:
#    부분일치 폴백이 열려 있던 판은 목록 앞의 `/results/<id>` 탭을 잡아 그 위에서 `navigate` 로
#    남의 화면을 지웠다. 폴백을 지운 뒤 그 동작을 **고정**한다.
class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


def _patch_urlopen(monkeypatch, listing: list[dict], created: dict | None = None) -> list[str]:
    """`json/list` 와 `json/new` 를 가로챈다. 돌려주는 리스트에 **호출 순서**가 쌓인다."""
    calls: list[str] = []

    def fake(req, timeout=None):  # noqa: ARG001
        url = req if isinstance(req, str) else req.full_url
        calls.append(url)
        if "/json/new" in url:
            assert created is not None, "탭 생성을 기대하지 않은 테스트인데 /json/new 가 불렸다"
            return _FakeResponse(created)
        return _FakeResponse(listing)

    monkeypatch.setattr(c2.urllib.request, "urlopen", fake)
    return calls


EXACT = "http://localhost:3000/"


def test_find_target_prefers_exact_over_results_tab(monkeypatch):
    """⛔ 목록 **앞**에 `/results/<id>` 탭이 있어도 정확 일치를 고른다 (MEDIUM-2 회귀 방지)."""
    listing = [
        {
            "type": "page",
            "url": "http://localhost:3000/results/abc",
            "webSocketDebuggerUrl": "ws://r",
        },
        {"type": "page", "url": EXACT, "webSocketDebuggerUrl": "ws://exact"},
    ]
    calls = _patch_urlopen(monkeypatch, listing)
    ws, url = find_target(9222, EXACT)
    assert (ws, url) == ("ws://exact", EXACT)
    assert not any("/json/new" in c for c in calls), "정확 일치가 있으면 탭을 만들지 않는다"


def test_find_target_ignores_non_page_targets(monkeypatch):
    """같은 url 이라도 `type` 이 page 가 아니면 고르지 않는다(iframe·browser_ui)."""
    listing = [
        {"type": "iframe", "url": EXACT, "webSocketDebuggerUrl": "ws://iframe"},
        {"type": "page", "url": EXACT, "webSocketDebuggerUrl": "ws://page"},
    ]
    _patch_urlopen(monkeypatch, listing)
    assert find_target(9222, EXACT)[0] == "ws://page"


def test_find_target_creates_tab_when_no_exact_match(monkeypatch):
    """⛔ **부분일치로 떨어지지 않는다** — `/results/` 탭만 있으면 **새 탭을 만든다**."""
    listing = [
        {
            "type": "page",
            "url": "http://localhost:3000/results/abc",
            "webSocketDebuggerUrl": "ws://r",
        },
    ]
    created = {"webSocketDebuggerUrl": "ws://new", "url": EXACT}
    calls = _patch_urlopen(monkeypatch, listing, created)
    ws, url = find_target(9222, EXACT)
    assert (ws, url) == ("ws://new", EXACT)
    assert any("/json/new" in c for c in calls), calls


def test_find_target_dies_when_tab_creation_returns_no_socket(monkeypatch):
    """탭 생성이 소켓을 안 주면 **이름 있는 실패**로 죽는다(조용히 진행하지 않는다)."""
    _patch_urlopen(monkeypatch, [], {"error": "nope"})
    with pytest.raises(SystemExit, match="탭을 만들지 못했다"):
        find_target(9222, EXACT)
