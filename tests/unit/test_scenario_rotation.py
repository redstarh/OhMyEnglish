"""`app.services.scenario_rotation` — 대화 상황을 고르는 규칙 (`TASK-4` · 결정 73·74).

⛔ 이 파일은 DB 를 쓰지 않는다. 고르는 규칙이 순수 함수라는 것이 설계의 요구이고
(`docs/design/2026-09-12-scenario-rotation-70-30-design.md` §4), 그래서 비율 단정(§6)을
픽스처 없이 셀 수 있다.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.services.scenario_rotation import (
    NEW,
    REPEAT,
    Candidate,
    Pick,
    RecentPick,
    pick_scenario,
)

_T0 = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _sid(n: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{n:012d}")


def _cands(count: int, *, used: dict[int, int] | None = None) -> list[Candidate]:
    """`count` 개의 후보. `used[n] = 일수` 면 그만큼 전에 쓴 것으로 둔다."""
    used = used or {}
    out = []
    for n in range(1, count + 1):
        ago = used.get(n)
        last = None if ago is None else _T0 - timedelta(days=ago)
        out.append(Candidate(scenario_id=_sid(n), last_used_at=last))
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
        Candidate(scenario_id=_sid(1), last_used_at=_T0 - timedelta(days=99)),
        Candidate(scenario_id=_sid(2), last_used_at=None),
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
