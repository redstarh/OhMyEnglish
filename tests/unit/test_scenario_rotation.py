"""`app.services.scenario_rotation` — 대화 상황을 고르는 규칙 (`TASK-4` · 결정 73·74).

⛔ 이 파일은 DB 를 쓰지 않는다. 고르는 규칙이 순수 함수라는 것이 설계의 요구이고
(`docs/design/2026-09-12-scenario-rotation-70-30-design.md` §4), 그래서 비율 단정(§6)을
픽스처 없이 셀 수 있다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.services.scenario_rotation import (
    NEW,
    REPEAT,
    WINDOW,
    Candidate,
    Pick,
    RecentPick,
    pick_scenario,
)

_T0 = datetime(2026, 9, 1, tzinfo=UTC)


def _sid(n: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{n:012d}")


def _cands(count: int, *, used: dict[int, int] | None = None) -> list[Candidate]:
    """`count` 개의 후보. `used[n] = 일수` 면 그만큼 전에 쓴 것으로 둔다.

    `created_at` 은 `n` 순서로 준다 — 번호가 작은 것이 먼저 만들어진 행이다. 한 번도 안 쓴
    후보끼리의 순서를 그것이 가른다(기존 계약 「가장 이른 행」).
    """
    used = used or {}
    out = []
    for n in range(1, count + 1):
        ago = used.get(n)
        last = None if ago is None else _T0 - timedelta(days=ago)
        out.append(
            Candidate(
                scenario_id=_sid(n),
                last_used_at=last,
                created_at=_T0 + timedelta(seconds=n),
            )
        )
    return out


def test_empty_history_picks_new() -> None:
    """이력이 0이면 신규다 — 창이 비어 `new_count` 가 0 이다."""
    got = pick_scenario(recent=[], candidates=_cands(3))
    assert got == Pick(scenario_id=_sid(1), pick=NEW)


def test_no_candidates_returns_none() -> None:
    """후보가 0행이면 `None` — 세션은 `scenario_id` 없이 진행한다(기존 폴백 보존)."""
    assert pick_scenario(recent=[], candidates=[]) is None


def test_third_new_is_the_last_new_in_the_window() -> None:
    """창 안에 신규가 이미 3건이면 반복으로 넘어간다 — 문턱이 3 이다."""
    recent = [RecentPick(scenario_id=_sid(n), pick=NEW) for n in (3, 2, 1)]
    got = pick_scenario(recent=recent, candidates=_cands(5, used={1: 3, 2: 2, 3: 1}))
    assert got is not None
    assert got.pick == REPEAT
    # 반복 묶음 안에서 가장 오래 안 쓴 것 — 3일 전에 쓴 `_sid(1)`.
    assert got.scenario_id == _sid(1)


def test_null_pick_rows_are_not_counted_as_new() -> None:
    """`scenario_pick` 이 `None` 인 과거 행은 세지 않는다 (마이그레이션 016 이전 행)."""
    recent = [RecentPick(scenario_id=_sid(n), pick=None) for n in (3, 2, 1)]
    got = pick_scenario(recent=recent, candidates=_cands(5, used={1: 3, 2: 2, 3: 1}))
    assert got is not None
    assert got.pick == NEW, "null 을 신규로 세면 여기서 반복이 나온다"


def test_never_used_beats_long_unused() -> None:
    """한 번도 안 쓴 후보가 가장 오래된 것보다 앞선다."""
    cands = [
        Candidate(
            scenario_id=_sid(1),
            last_used_at=_T0 - timedelta(days=99),
            created_at=_T0,
        ),
        Candidate(scenario_id=_sid(2), last_used_at=None, created_at=_T0),
    ]
    got = pick_scenario(recent=[], candidates=cands)
    assert got == Pick(scenario_id=_sid(2), pick=NEW)


def test_falls_back_to_the_other_pool_when_one_is_empty() -> None:
    """창 밖 후보가 0이면 신규를 원해도 반복으로 넘어간다 — 멈추지 않는다."""
    recent = [RecentPick(scenario_id=_sid(1), pick=REPEAT)]
    got = pick_scenario(recent=recent, candidates=_cands(1, used={1: 1}))
    assert got == Pick(scenario_id=_sid(1), pick=REPEAT)


def test_is_deterministic() -> None:
    """같은 입력에 같은 출력 — 난수를 쓰지 않는다는 것이 §6 검증의 전제다."""
    recent = [RecentPick(scenario_id=_sid(1), pick=NEW)]
    cands = _cands(4, used={1: 1})
    first = pick_scenario(recent=recent, candidates=cands)
    second = pick_scenario(recent=recent, candidates=cands)
    assert first == second


# --- 비율 성질 (설계서 §6) -------------------------------------------------
#
# ⛔ 「비율이 지켜진다」를 문장으로 쓰지 않고 센다. 9 와 12 는 규칙을 손으로 돌려 얻은
# 값이다 — 창 10 · 문턱 3 이면 주기가 11회(신규 3 + 반복 8)로 수렴하고 신규 회차가
# 1·2·3 → 12·13·14 → 23·24·25 → 34·35·36 이다. ⚠️ 구현과 다르면 **구현이 아니라 이
# 수치를 먼저 다시 센다.**


def _simulate(rounds: int, topics: int) -> tuple[list[str], int, int]:
    """빈 이력에서 `rounds` 회 연속으로 고른다.

    돌려주는 것 셋: 회차별 `pick` 목록 · 신규 후보가 0이었던 횟수 ·
    직전과 같은 상황을 고른 횟수.
    """
    history: list[RecentPick] = []
    last_used: dict[UUID, int] = {}
    picks: list[str] = []
    starved = 0
    repeated_back_to_back = 0
    previous: UUID | None = None

    for turn in range(1, rounds + 1):
        cands = [
            Candidate(
                scenario_id=_sid(n),
                last_used_at=None
                if _sid(n) not in last_used
                else _T0 + timedelta(days=last_used[_sid(n)]),
                created_at=_T0 + timedelta(seconds=n),
            )
            for n in range(1, topics + 1)
        ]
        window = history[:WINDOW]
        recent_ids = {row.scenario_id for row in window}
        if not [c for c in cands if c.scenario_id not in recent_ids]:
            starved += 1

        got = pick_scenario(recent=window, candidates=cands)
        assert got is not None
        picks.append(got.pick)
        if got.scenario_id == previous:
            repeated_back_to_back += 1
        previous = got.scenario_id
        last_used[got.scenario_id] = turn
        history.insert(0, RecentPick(scenario_id=got.scenario_id, pick=got.pick))

    return picks, starved, repeated_back_to_back


def test_thirty_rounds_yield_exactly_nine_new() -> None:
    """빈 이력에서 30회 — 신규 9 · 반복 21. 도입 직후 3회 연속 신규를 포함한다."""
    picks, _, _ = _simulate(rounds=30, topics=15)
    assert picks.count(NEW) == 9
    assert picks.count(REPEAT) == 21
    assert picks[:3] == [NEW, NEW, NEW], "창이 비어 있는 동안은 신규가 연달아 나온다"


def test_forty_rounds_never_starve_for_new_topics() -> None:
    """⛔ 이 설계의 핵심 단정 — 15종을 다 써도 신규 후보가 마르지 않는다.

    「신규」를 *한 번도 안 한 것*으로 읽으면 15회 뒤 후보가 0이 된다. 결정 74 의 창
    정의가 그것을 막는 기전은 **창 10 이 15종보다 작다**는 것이다 ⇒ 항상 창 밖에 최소
    5종이 남는다.
    """
    picks, starved, _ = _simulate(rounds=40, topics=15)
    assert picks.count(NEW) == 12
    assert starved == 0


def test_same_topic_never_comes_twice_in_a_row() -> None:
    """연달아 같은 상황을 고르지 않는다 — 반복 묶음에서 가장 오래된 것을 고르므로."""
    _, _, back_to_back = _simulate(rounds=40, topics=15)
    assert back_to_back == 0


def test_ratio_holds_when_topics_barely_exceed_the_window() -> None:
    """후보가 창보다 1개 많은 최소 조건에서도 마르지 않는다 — 15종이 상한이 아님을 본다."""
    picks, starved, _ = _simulate(rounds=30, topics=WINDOW + 1)
    assert starved == 0
    assert picks.count(NEW) == 9


def test_starvation_returns_when_topics_only_match_the_window() -> None:
    """⛔ 판별력 확인 — 후보가 창과 «같으면» 신규가 마른다.

    위 두 테스트의 `starved == 0` 이 **늘 참인 단정이 아님**을 이것이 보인다. 창보다 후보가
    많으면 구조적으로 0 이므로, 0 을 재는 것만으로는 그 단정이 무엇을 배제하는지 알 수 없다.

    후보를 창 크기(`WINDOW` = 10)로 낮추면 창이 후보 전부를 덮는 구간이 생겨 신규 후보가
    0 이 되고, 40회의 신규가 **12 에서 10 으로 떨어진다**(직접 돌려 얻은 값이다).
    ⇒ **후보 수가 창보다 많아야 한다**는 것이 이 설계의 요구다. 시드 15행이 그 요구를
    만족하는 근거이고(설계서 §3), 시드를 10행 이하로 줄이면 이 테스트가 그 사실을 알린다.
    """
    picks, starved, _ = _simulate(rounds=40, topics=WINDOW)
    assert starved == 6
    assert picks.count(NEW) == 10
