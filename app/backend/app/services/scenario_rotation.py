"""세션이 열릴 때 어느 대화 상황을 고를지 정하는 규칙 (`TASK-4`).

**결정의 정본은 `docs/ops/captain-instruction-register.md` 의 결정 73·74 다** — 배치 단위가
대화 상황이고(73), 「신규」가 「최근 창 안에 안 나온 상황」이다(74). 왜 그렇게 정했는지는
그 대장이 갖고 여기서 재서술하지 않는다.

⛔ **이 모듈은 DB 를 모른다.** 이력과 후보를 받아 하나를 고르는 순수 함수만 둔다 —
그것이 설계서 §6 의 비율 단정을 픽스처 없이 셀 수 있게 하는 조건이다. 읽고 쓰는 겉면은
`services/sessions.py` 의 `_pick_scenario_for_user` 가 갖는다.

⛔ **난수를 쓰지 않는다.** 같은 입력에 같은 출력을 내지 않으면 「비율이 지켜진다」를
계산으로 확인할 수 없고, `TASK-4` AC#4 가 요구한 것이 그 계산이다.

설계서: `docs/design/2026-09-12-scenario-rotation-70-30-design.md` §4
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# `learning_sessions.scenario_pick` 의 값역. ⛔ 016 의 CHECK 와 같은 두 값이고
# 여기서 목록을 늘리면 그 CHECK 가 거부한다 — 두 곳이 갈라지지 않게 값만 둔다.
NEW = "new"
REPEAT = "repeat"

# 결정 74 의 유도값이다. 반복 7 대 신규 3 이면 한 주기가 10회이므로 창이 10 이고
# 그 창에 신규가 3회다. ⚠️ **캡틴 문서에 이 두 수의 직접 근거는 없다** — 비율에서
# 유도했다. ⛔ 복습 사다리 `1·3·7일` 과 다른 축이므로 섞지 않는다.
WINDOW = 10
NEW_PER_WINDOW = 3


@dataclass(frozen=True, slots=True)
class RecentPick:
    """직전 창 안의 세션 한 건. `pick` 이 `None` 인 것은 016 이전에 열린 세션이다."""

    scenario_id: UUID
    pick: str | None


@dataclass(frozen=True, slots=True)
class Candidate:
    """고를 수 있는 상황 한 건. `last_used_at` 이 `None` 이면 한 번도 쓰이지 않았다.

    ⚠️ `created_at` 을 함께 받는 이유는 **기존 계약 하나를 지키기 위해서다.** 세션 시작은
    이전부터 *"수준 일치가 0행이면 가장 이른 행으로 떨어진다"* 를 계약으로 갖고 있고
    (`tests/harness/scenarios-E-agent-learning.md` 가 문서에 못 박은 값이다), 그것을
    `test_session_creation_falls_back_to_the_earliest_scenario` 가 지킨다. 한 번도 안 쓴
    후보끼리는 「오래 안 씀」으로 순서를 가릴 수 없으므로 **그때 생성 순서가 가른다.**
    """

    scenario_id: UUID
    last_used_at: datetime | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class Pick:
    """고른 결과 — 무엇을 골랐는지와 어느 쪽으로 셌는지."""

    scenario_id: UUID
    pick: str


def _staleness(candidate: Candidate) -> tuple[int, float, str]:
    """오래 안 쓴 것이 앞서는 정렬 키.

    `None`(한 번도 안 씀)을 가장 앞에 둔다 — `datetime` 과 `None` 을 직접 비교할 수 없어
    앞자리 정수로 가른다. ⚠️ **한 번도 안 쓴 것끼리는 `created_at` 이 가른다** — 그것이
    「수준 일치가 0행이면 가장 이른 행」이라는 기존 계약을 지키는 자리다(`Candidate` 참조).
    마지막 자리는 **동률을 결정론으로 가르기 위한** UUID 문자열이다.
    """
    if candidate.last_used_at is None:
        return (0, candidate.created_at.timestamp(), str(candidate.scenario_id))
    return (1, candidate.last_used_at.timestamp(), str(candidate.scenario_id))


def pick_scenario(
    *,
    recent: Sequence[RecentPick],
    candidates: Sequence[Candidate],
) -> Pick | None:
    """직전 창과 후보를 받아 상황 하나를 고른다. 후보가 0이면 `None`.

    `recent` 는 **최신 먼저**로 최대 `WINDOW` 건이다. 창을 자르는 것은 호출자의 몫이다 —
    이 함수는 받은 것을 그대로 창으로 본다(테스트가 창 밖 상황을 만들 수 있어야 한다).

    ⚠️ `pick` 이 `None` 인 행은 `new_count` 에서 **세지 않는다.** 016 이전 세션에는 그 값이
    없고 소급해 채우지 않기로 했으므로(설계서 §5), 세면 「신규였다」를 지어내는 것이 된다.
    ⇒ 도입 직후에는 `new_count` 가 0 이라 **신규가 먼저 3회 연달아 나온다.** 그것은 결함이
    아니라 창이 채워지는 과정이다.
    """
    if not candidates:
        return None

    new_count = sum(1 for row in recent if row.pick == NEW)
    recent_ids = {row.scenario_id for row in recent}
    fresh = [c for c in candidates if c.scenario_id not in recent_ids]
    seen = [c for c in candidates if c.scenario_id in recent_ids]

    if new_count < NEW_PER_WINDOW and fresh:
        pool, label = fresh, NEW
    elif seen:
        pool, label = seen, REPEAT
    else:
        # 신규 몫이 남지 않았는데 반복 후보가 0인 경우다 — 창 밖에서 고르고 신규로 센다.
        # (후보가 0이면 위에서 이미 `None` 을 냈으므로 `fresh` 는 여기서 비지 않는다.)
        pool, label = fresh, NEW

    chosen = min(pool, key=_staleness)
    return Pick(scenario_id=chosen.scenario_id, pick=label)
