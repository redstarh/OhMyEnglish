# 대화 상황 배치 (반복 70 대 신규 30) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 세션이 열릴 때 고르는 대화 상황이 「직전 10회 안에 안 나온 것 3회 : 나온 것 7회」를 지키게 한다.

**Architecture:** 고르는 규칙을 DB 를 모르는 순수 함수(`services/scenario_rotation.py`)로 두고, `sessions.py` 가 이력·후보를 읽어 그 함수에 넘긴 뒤 고른 값과 고른 쪽을 세션 행에 함께 적는다. 지금 `_CREATE_SESSION_SQL` 안에 있는 시나리오 서브쿼리 둘을 지우고 그 자리를 파라미터로 바꾼다.

**Tech Stack:** Python 3.12 · asyncpg · pytest · PostgreSQL 17 · ruff · ty

**Spec:** `docs/design/2026-09-12-scenario-rotation-70-30-design.md`

> ⛔ **실행 중에 이 계획의 사실 오류 셋이 드러났다 — 아래 코드 블록을 그대로 베끼지 마라.**
> 정정된 내용은 **설계서 §4 가 갖는다**(여기서 재서술하지 않는다). 실제로 들어간 형태는 커밋
> `e057f55` 다.
>
> 1. `learning_sessions` 의 시각 컬럼은 `created_at` 이 아니라 **`started_at`** 이다. 이 계획의
>    `_RECENT_PICKS_SQL`·`_SCENARIO_CANDIDATES_SQL` 과 Task 5 의 테스트 쿼리가 틀렸다.
> 2. `Candidate` 에 **`created_at` 이 하나 더 필요하다.** 한 번도 안 쓴 후보끼리를 `scenario_id`
>    로 가르면 「수준 일치가 0행이면 가장 이른 행」이라는 **기존 계약이 깨진다.**
> 3. `_CREATE_SESSION_SQL` 을 쓰는 곳이 **둘**이다 — `create_session` 과 `start_shadowing_session`.
>    파라미터를 늘리면 뒤쪽도 함께 고쳐야 한다(Task 5 는 앞쪽만 적었다).
>
> ⚠️ **부분 실행에 `-c pyproject.toml` 을 빼면 `asyncio` 모드가 안 걸려 기존 테스트가 거짓
> 빨강이 된다** — Global Constraints 에 적어 두고도 한 번 어겼다. 「6 failed」를 회귀로 오독할
> 자리였다.

## Global Constraints

- 결정의 정본은 `docs/ops/captain-instruction-register.md` 의 **결정 73·74·75** 다. 계획이 그것과 어긋나면 계획이 틀린 것이다.
- **창 10 · 신규 문턱 3** — 결정 74 의 유도값이다. 두 수를 코드에 상수로 한 번만 둔다.
- **업무 6종의 `level` 은 `A2`** — 결정 75 의 완화 조항이다. 올리지 않는다.
- **표 구조를 바꾸지 않는다.** `learning_scenarios` 는 손대지 않고 `learning_sessions` 에 컬럼 **하나만** 더한다.
- **마이그레이션 번호는 `016`** — 2026-09-12 dev DB `schema_migrations` 직접 조회로 발급했다(최대 `015`).
- **난수를 쓰지 않는다.** 같은 입력에 같은 출력을 낸다.
- 게이트는 cwd `app/backend` 에서 돌린다. 게이트 밖 경로는 `../../tests` 로 준다. ⛔ `ty` 는 절대경로 `/Users/redstar/.local/bin/ty` 로 부른다(이름만으로는 exit 127).
- `git add` 에 디렉터리를 주지 않는다. 커밋 전 `git diff --cached --name-only`, 뒤 `git show --stat` 을 본다.

---

### Task 1: 고르는 규칙 — 순수 함수와 타입

**Files:**
- Create: `app/backend/app/services/scenario_rotation.py`
- Test: `tests/unit/test_scenario_rotation.py`

**Interfaces:**
- Consumes: 없음 (DB·앱 상태를 모른다)
- Produces: `WINDOW: int` · `NEW_PER_WINDOW: int` · `NEW: str` · `REPEAT: str` · `RecentPick(scenario_id: UUID, pick: str | None)` · `Candidate(scenario_id: UUID, last_used_at: datetime | None)` · `Pick(scenario_id: UUID, pick: str)` · `pick_scenario(*, recent: Sequence[RecentPick], candidates: Sequence[Candidate]) -> Pick | None`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_scenario_rotation.py`:

```python
"""`app.services.scenario_rotation` — 대화 상황을 고르는 규칙 (`TASK-4` · 결정 73·74).

⛔ 이 파일은 DB 를 쓰지 않는다. 고르는 규칙이 순수 함수라는 것이 설계의 요구이고
(설계서 §4), 그래서 비율 단정(§6)을 픽스처 없이 셀 수 있다.
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
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest ../../tests/unit/test_scenario_rotation.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.scenario_rotation'`

- [ ] **Step 3: 최소 구현을 쓴다**

`app/backend/app/services/scenario_rotation.py`:

```python
"""세션이 열릴 때 어느 대화 상황을 고를지 정하는 규칙 (`TASK-4`).

**결정의 정본은 `docs/ops/captain-instruction-register.md` 의 결정 73·74 다** — 배치 단위가
대화 상황이고(73), 「신규」가 「최근 창 안에 안 나온 상황」이다(74). 왜 그렇게 정했는지는
그 대장이 갖고 여기서 재서술하지 않는다.

⛔ **이 모듈은 DB 를 모른다.** 이력과 후보를 받아 하나를 고르는 순수 함수만 둔다 —
그것이 설계서 §6 의 비율 단정을 픽스처 없이 셀 수 있게 하는 조건이다. 읽고 쓰는 겉면은
`services/sessions.py` 가 갖는다.

⛔ **난수를 쓰지 않는다.** 같은 입력에 같은 출력을 내지 않으면 「비율이 지켜진다」를
계산으로 확인할 수 없고, `TASK-4` AC#4 가 요구한 것이 그 계산이다.
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
    """고를 수 있는 상황 한 건. `last_used_at` 이 `None` 이면 한 번도 쓰이지 않았다."""

    scenario_id: UUID
    last_used_at: datetime | None


@dataclass(frozen=True, slots=True)
class Pick:
    """고른 결과 — 무엇을 골랐는지와 어느 쪽으로 셌는지."""

    scenario_id: UUID
    pick: str


def _staleness(candidate: Candidate) -> tuple[int, float, str]:
    """오래 안 쓴 것이 앞서는 정렬 키.

    `None`(한 번도 안 씀)을 가장 앞에 둔다 — `datetime` 과 `None` 을 직접 비교할 수 없어
    앞자리 정수로 가른다. 마지막 자리는 **동률을 결정론으로 가르기 위한** UUID 문자열이다.
    """
    if candidate.last_used_at is None:
        return (0, 0.0, str(candidate.scenario_id))
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
        # 창이 후보 전부를 덮었는데 신규 몫이 남지 않은 경우는 위에서 걸리므로, 여기 오는 것은
        # 「반복 후보가 0」인 경우뿐이다 — 창 밖에서 고르고 신규로 센다.
        pool, label = fresh, NEW

    chosen = min(pool, key=_staleness)
    return Pick(scenario_id=chosen.scenario_id, pick=label)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest ../../tests/unit/test_scenario_rotation.py -q`
Expected: PASS — 7 passed

- [ ] **Step 5: 커밋한다**

```bash
git add app/backend/app/services/scenario_rotation.py tests/unit/test_scenario_rotation.py
git diff --cached --name-only
git commit -m "feat(TASK-4): 대화 상황을 고르는 순수 규칙을 만들었음 (결정 73·74)"
git show --stat HEAD
```

---

### Task 2: 비율 성질 — 30회 9번 · 40회 12번 · 고갈 0회

**Files:**
- Modify: `tests/unit/test_scenario_rotation.py` (파일 끝에 절을 더한다)

**Interfaces:**
- Consumes: Task 1 의 `pick_scenario` · `RecentPick` · `Candidate` · `NEW` · `WINDOW`
- Produces: 없음 (테스트만)

- [ ] **Step 1: 성질 테스트를 쓴다 — 이것이 AC#4 의 실체다**

`tests/unit/test_scenario_rotation.py` 끝에 붙인다:

```python
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
```

- [ ] **Step 2: 돌려서 수치를 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest ../../tests/unit/test_scenario_rotation.py -q`
Expected: PASS — 11 passed

⛔ **실패하면 구현을 고치기 전에 기대값을 손으로 다시 센다.** 9·12 는 계획이 유도한 값이고 실측이 아니다. 셋을 다시 세서 계획이 틀렸으면 **이 파일과 설계서 §6 을 함께 고친다** — 한쪽만 고치면 두 문서가 갈라진다.

- [ ] **Step 3: 커밋한다**

```bash
git add tests/unit/test_scenario_rotation.py
git diff --cached --name-only
git commit -m "test(TASK-4): 비율 9/30 · 12/40 과 신규 고갈 0건을 세는 단정을 넣었음 (AC#4)"
git show --stat HEAD
```

---

### Task 3: 마이그레이션 016 — `learning_sessions.scenario_pick`

**Files:**
- Create: `db/migrations/016_session_scenario_pick.sql`
- Modify: `tests/unit/test_schema.py` (파일 끝에 테스트 하나를 더한다)

**Interfaces:**
- Consumes: Task 1 의 `NEW`·`REPEAT` 값(`'new'`·`'repeat'`) — CHECK 가 같은 두 값을 가둔다
- Produces: 컬럼 `learning_sessions.scenario_pick text null check (scenario_pick in ('new','repeat'))`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_schema.py` 끝에 붙인다:

```python
# ⑥ 016 — 세션이 상황을 「신규로 골랐는지 반복으로 골랐는지」를 남긴다 (`TASK-4` · 결정 74).
#
# ⚠️ **nullable 이 요구다.** 016 이전 세션에는 이 값이 없고 소급해 채우지 않는다 — 과거 세션의
# 신규 여부는 그 시점의 창에 달렸고 지금 창으로 다시 접으면 실제로 일어난 것과 다른 값이 된다
# (설계서 §5). `pick_scenario` 가 `None` 을 세지 않는 것이 그 짝이다.
@pytest.mark.asyncio
async def test_scenario_pick_is_nullable_and_bounded(db_conn: asyncpg.Connection):
    user_id = await db_conn.fetchval(
        "insert into users (display_name, timezone, current_level) "
        "values ('t', 'Asia/Seoul', 'A2') returning id"
    )

    # ⑴ 값을 주지 않아도 행이 만들어진다 — 과거 행과 같은 모양이다.
    null_row = await db_conn.fetchval(
        "insert into learning_sessions (user_id) values ($1) returning scenario_pick",
        user_id,
    )
    assert null_row is None

    # ⑵ 값역 안의 두 값은 받는다.
    for value in ("new", "repeat"):
        got = await db_conn.fetchval(
            "insert into learning_sessions (user_id, scenario_pick) values ($1, $2) "
            "returning scenario_pick",
            user_id,
            value,
        )
        assert got == value

    # ⑶ 값역 밖은 거부한다 — 오타가 조용히 집계를 틀리게 하는 것을 막는다.
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into learning_sessions (user_id, scenario_pick) values ($1, 'fresh')",
            user_id,
        )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest ../../tests/unit/test_schema.py::test_scenario_pick_is_nullable_and_bounded -q`
Expected: FAIL — `UndefinedColumnError: column "scenario_pick" of relation "learning_sessions" does not exist`

- [ ] **Step 3: 마이그레이션 파일을 쓴다**

`db/migrations/016_session_scenario_pick.sql`:

```sql
-- 016_session_scenario_pick.sql
-- `learning_sessions` 에 「이 세션의 상황을 신규로 골랐는지 반복으로 골랐는지」를 더한다.
-- 결정: docs/ops/captain-instruction-register.md 「결정 73」(배치 단위는 대화 상황) ·
--   「결정 74」(신규는 최근 10회 안에 안 나온 상황)
-- 소유 태스크: TASK-4 · 설계서: docs/design/2026-09-12-scenario-rotation-70-30-design.md §5
--
-- 번호: dev DB `schema_migrations` 직접 조회가 `001 · 003~007 · 009~015` 이므로 016 임(`H-AL`).
-- ⛔ `008` 은 주간 리포트(`TASK-26`)용 예약 자리이므로 쓰지 않는다.
--
-- 왜 필요한가: 이 칸이 없으면 「신규를 몇 번 골랐는가」를 셀 수 없고, 그러면 `TASK-4` AC#4 가
-- 요구한 「문구 단정이 아니라 계산 검증」을 할 수단이 없다. 이력에서 매번 재계산하는 대안은
-- 재귀가 되고 창 크기를 바꾸면 과거 판정이 소급해 흔들린다(설계서 §7 대안 2).
--
-- ⚠️ **nullable 이고 소급해 채우지 않는다.** 016 이전 세션의 신규 여부는 그 시점의 창에 달렸고,
-- 지금 창으로 다시 접으면 **실제로 일어난 것과 다른 값**이 된다. 앱은 `null` 을 「신규였다」로
-- 세지 않는다(`services/scenario_rotation.pick_scenario` 가 그것을 명시한다).
-- ⇒ 도입 직후에는 신규가 먼저 3회 연달아 나온다. 그것은 창이 채워지는 과정이고 결함이 아니다.
--
-- ⛔ 값역을 앱과 두 곳에 두지 않는다 — 이 CHECK 가 정본이고 앱은 상수 두 개(`NEW`·`REPEAT`)만
-- 갖는다. 되돌리기는 이 열을 drop 하는 것이고, 값이 있으면 그 값은 사라진다.

alter table learning_sessions
  add column scenario_pick text
  check (scenario_pick in ('new', 'repeat'));
```

- [ ] **Step 4: 적용하고 통과를 확인한다**

⛔ **`scripts/migrate.py` 를 돌리지 않는다** — 그 스크립트의 시드 upsert 가 공유 dev DB 의 가변 컬럼을 덮는다. `psql` 로 파일만 적용하고 `schema_migrations` 행을 같은 트랜잭션에서 직접 넣는다.

```bash
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy -d ohmyenglish -1 -v ON_ERROR_STOP=1 \
  -c "$(cat db/migrations/016_session_scenario_pick.sql)" \
  -c "insert into schema_migrations (filename) values ('016_session_scenario_pick.sql')"
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy -d ohmyenglish -tAc \
  "select * from schema_migrations order by 1 desc limit 2"
```

Run: `cd app/backend && .venv/bin/python -m pytest ../../tests/unit/test_schema.py -q`
Expected: PASS — 테스트 DB 는 마이그레이션 파일을 처음부터 적용하므로 새 파일이 자동으로 걸린다

- [ ] **Step 5: 커밋한다**

```bash
git add db/migrations/016_session_scenario_pick.sql tests/unit/test_schema.py
git diff --cached --name-only
git commit -m "feat(TASK-4): 세션이 고른 쪽을 남기는 016 을 발급·적용했음 (결정 73·74)"
git show --stat HEAD
```

---

### Task 4: 시드 15행 — 일상 9 + 업무 6

**Files:**
- Modify: `scripts/migrate.py` (상수 `SEED_SCENARIOS`)
- Modify: `tests/unit/test_schema.py` (`test_seed_creates_fixed_user_and_three_scenarios_idempotently`)

**Interfaces:**
- Consumes: 없음
- Produces: `SEED_SCENARIOS` 15행 — `category` 는 `daily_life` 9행 · `business` 6행, `level` 은 전부 `A2`

- [ ] **Step 1: 기존 테스트가 3행을 단정하는 자리를 고친다**

⚠️ **이것은 새 테스트가 아니라 기존 단정의 갱신이다.** `tests/unit/test_schema.py` 의 `test_seed_creates_fixed_user_and_three_scenarios_idempotently` 가 `len(scenario_rows) == 3` 과 제목 3개를 고정하고 있어 시드를 늘리면 **먼저 빨강이 된다.** 함수 이름도 낡으므로 함께 고친다.

바꿀 부분 — 함수 이름과 시나리오 단정 블록:

```python
async def test_seed_creates_fixed_user_and_fifteen_scenarios_idempotently(
    db_conn: asyncpg.Connection,
):
    await migrate.seed(db_conn)
    await migrate.seed(db_conn)  # re-run — must stay idempotent (on conflict do update)

    user_count = await db_conn.fetchval("select count(*) from users")
    assert user_count == 1

    seeded_user = await db_conn.fetchrow(
        "select display_name, timezone, current_level from users where id = $1",
        migrate.USER_ID,
    )
    assert seeded_user["timezone"] == "Asia/Seoul"
    assert seeded_user["current_level"] == "A2"

    # `TASK-4` · 결정 75 — 일상 9 + 업무 6 = 15 다. ⚠️ 개수를 세는 이유는 배치 규칙이
    # 「창 10 보다 후보가 많다」에 걸려 있기 때문이다(설계서 §6 테스트 2) — 15가 10 아래로
    # 줄면 신규가 마른다.
    daily = await db_conn.fetch(
        "select title from learning_scenarios where category = 'daily_life' order by title"
    )
    business = await db_conn.fetch(
        "select title from learning_scenarios where category = 'business' order by title"
    )
    assert len(daily) == 9, "PRD §7 Daily Conversation 의 주제 9종"
    assert len(business) == 6, "PRD §7 Business English 의 시나리오 6종 (캡틴 결정 §1 항목 5)"

    # ⛔ 업무 6종의 `level` 을 올리지 않는다 — 결정 75 의 완화 조항이고, 이 단정이 그것을
    # 지킨다. 무대는 업무이고 문형 난이도는 일상과 같다.
    business_levels = await db_conn.fetch(
        "select distinct level from learning_scenarios where category = 'business'"
    )
    assert [row["level"] for row in business_levels] == ["A2"]
```

- [ ] **Step 2: 빨강을 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest "../../tests/unit/test_schema.py::test_seed_creates_fixed_user_and_fifteen_scenarios_idempotently" -q`
Expected: FAIL — `assert 3 == 9`

- [ ] **Step 3: `SEED_SCENARIOS` 를 15행으로 늘린다**

`scripts/migrate.py` 의 상수를 아래로 바꾼다. **`…101`·`…102`·`…103` 의 UUID 를 유지한다** — `seed()` 의 upsert 가 `title`·`prompt_template` 만 덮고 `category`·`level` 은 덮지 않으므로, 기존 행은 제목만 갱신된다.

```python
SEED_SCENARIOS: list[tuple[UUID, str, str, str, str]] = [
    # 일상 9종 — 이름은 `docs/PRD.md` §7 Daily Conversation 그대로다(v1.0 · 2026-08-24).
    # ⚠️ 캡틴 노트 항목 7 이 새로 요구한 것은 이 이름 목록이 아니라 **배치 비율**이다.
    (
        UUID("00000000-0000-0000-0000-000000000101"),
        "daily_life",
        "A2",
        "After work with a colleague",
        "You are a friendly colleague chatting with the learner after work.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000102"),
        "daily_life",
        "A2",
        "Weekend plans with a friend",
        "You are a friend catching up with the learner about the weekend.",
    ),
    # ⚠️ `…103` 은 *"Tonight's plans at home"* 에서 「식사」로 옮겼다 — 집·오늘 밤이라는 무대를
    # 유지하면서 9종의 한 자리를 채우는 가장 가까운 이동이다(설계서 §3).
    (
        UUID("00000000-0000-0000-0000-000000000103"),
        "daily_life",
        "A2",
        "Deciding what to eat tonight",
        "You are a housemate deciding with the learner what to eat tonight.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000104"),
        "daily_life",
        "A2",
        "Meeting someone for the first time",
        "You are someone the learner has just met. Keep the small talk short and friendly.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000105"),
        "daily_life",
        "A2",
        "Talking about a hobby",
        "You are a friend asking the learner about a hobby they enjoy.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000106"),
        "daily_life",
        "A2",
        "How the day felt",
        "You are a close friend asking the learner how their day felt.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000107"),
        "daily_life",
        "A2",
        "Asking the way to a station",
        "You are a passer-by the learner stops to ask for directions.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000108"),
        "daily_life",
        "A2",
        "Asking a small favour",
        "You are a neighbour the learner asks for a small favour.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000109"),
        "daily_life",
        "A2",
        "Giving an opinion about a film",
        "You are a friend asking the learner what they thought about a film.",
    ),
    # 업무 6종 — 이름은 `docs/PRD.md` §7 Business English 그대로다. 캡틴 결정
    # (`docs/design/2026-09-06-captain-decisions.md` §1 항목 5)이 「주제 9종에 더한다」로 정했다.
    # ⛔ **`level` 을 `A2` 로 둔다 — 올리지 않는다**(결정 75 의 완화 조항). 무대는 업무이고
    # 문형 난이도는 일상과 같다. `h-doc` 프로필이 경고한 실패(AWS 보고 수준 문형으로 예문을
    # 만들면 첫 세션에서 얼어붙는다)를 그것으로 피한다.
    (
        UUID("00000000-0000-0000-0000-000000000110"),
        "business",
        "A2",
        "Daily update in a short stand-up",
        "You are a teammate listening to the learner's short daily update.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000111"),
        "business",
        "A2",
        "Sharing a blocker",
        "You are a teammate the learner tells about something blocking their work.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000112"),
        "business",
        "A2",
        "Moving a deadline",
        "You are a teammate the learner asks to move a deadline.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000113"),
        "business",
        "A2",
        "Agreeing what comes first",
        "You are a teammate deciding with the learner which task comes first.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000114"),
        "business",
        "A2",
        "Reporting a small service problem",
        "You are a teammate the learner reports a small service problem to.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000115"),
        "business",
        "A2",
        "Short report to a manager",
        "You are a manager listening to the learner's short project report.",
    ),
]
```

- [ ] **Step 4: 통과를 확인하고 이웃 테스트가 깨졌는지 본다**

Run: `cd app/backend && .venv/bin/python -m pytest ../../tests/unit/test_schema.py ../../tests/unit/test_shadowing_seed.py -q`
Expected: PASS

⚠️ **`test_seeded_scenarios_are_stages_not_questions` 가 15행 전부에 걸린다.** 그 테스트는 시드가 「질문이 아니라 무대」임을 재는 것이고(캡틴 결정 14), 위 문구 15개는 전부 `You are …` 형태이므로 통과해야 한다. ⛔ **빨강이면 문구를 고친다 — 테스트를 느슨하게 하지 않는다.**

- [ ] **Step 5: 커밋한다**

```bash
git add scripts/migrate.py tests/unit/test_schema.py
git diff --cached --name-only
git commit -m "feat(TASK-4): 대화 상황 시드를 15행으로 늘렸음 — 일상 9 + 업무 6 (결정 75)"
git show --stat HEAD
```

---

### Task 5: 배선 — `sessions.py` 가 규칙을 쓰고 고른 쪽을 적는다

**Files:**
- Modify: `app/backend/app/services/sessions.py` (상수 `_CREATE_SESSION_SQL` · 함수 `create_session`)
- Test: `tests/unit/test_sessions.py` (파일 끝에 절을 더한다)

**Interfaces:**
- Consumes: Task 1 의 `pick_scenario` · `Candidate` · `RecentPick` · `WINDOW` / Task 3 의 컬럼 `scenario_pick` / Task 4 의 시드 15행
- Produces: `create_session` 이 `scenario_id` 와 `scenario_pick` 을 함께 적는다. 시그니처는 **바뀌지 않는다** — 호출자(`api/ws.py`·하네스)를 깨뜨리지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다 — 결함을 반증 가능하게 만드는 자리다**

`tests/unit/test_sessions.py` 끝에 붙인다:

```python
# --- Task 4: 대화 상황 배치 (`TASK-4` · 결정 73·74·75) ----------------------
#
# ⛔ **첫 테스트가 결함 재현이다.** 이 절을 쓰기 전에는 `_CREATE_SESSION_SQL` 이 level 일치 행 중
# `order by created_at, id limit 1` 로 골라서 **같은 사용자가 몇 번을 열어도 같은 상황**을 받았다
# (시드 3행 가운데 `…101` 하나만 쓰였다). 그 사실이 `TASK-4` 의 무게중심이었다.


@pytest.mark.asyncio
async def test_consecutive_sessions_do_not_repeat_the_same_scenario(
    db_pool: asyncpg.Pool,
) -> None:
    """연달아 열면 다른 상황이 온다 — 이 단정이 없으면 limit 1 회귀가 조용히 돌아온다."""
    async with db_pool.acquire() as conn:
        user_id = await conn.fetchval(
            "insert into users (display_name, timezone, current_level) "
            "values ('rotation', 'Asia/Seoul', 'A2') returning id"
        )
        ids = []
        for _ in range(3):
            ids.append(
                await conn.fetchval(
                    "insert into learning_scenarios (category, level, title, prompt_template) "
                    "values ('daily_life', 'A2', 'stage', 'You are someone.') returning id"
                )
            )

    first = await create_session(db_pool, user_id)
    second = await create_session(db_pool, user_id)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "select scenario_id, scenario_pick from learning_sessions "
            "where id = any($1::uuid[]) order by created_at",
            [first, second],
        )
    picked = [row["scenario_id"] for row in rows]
    assert picked[0] != picked[1], "같은 상황이 연달아 왔다 — limit 1 로 되돌아갔다"
    assert all(row["scenario_pick"] == "new" for row in rows), "창이 비어 있으면 둘 다 신규다"
    assert set(picked) <= set(ids)


@pytest.mark.asyncio
async def test_session_without_any_scenario_row_still_opens(db_pool: asyncpg.Pool) -> None:
    """후보가 0행이면 `scenario_id` 는 null 이고 세션은 열린다 — 기존 폴백을 보존한다."""
    async with db_pool.acquire() as conn:
        await conn.execute("delete from learning_sessions")
        await conn.execute("delete from learning_scenarios")
        user_id = await conn.fetchval(
            "insert into users (display_name, timezone, current_level) "
            "values ('empty', 'Asia/Seoul', 'A2') returning id"
        )

    session_id = await create_session(db_pool, user_id)

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "select scenario_id, scenario_pick from learning_sessions where id = $1",
            session_id,
        )
    assert row["scenario_id"] is None
    assert row["scenario_pick"] is None


@pytest.mark.asyncio
async def test_level_mismatch_falls_back_to_every_scenario(db_pool: asyncpg.Pool) -> None:
    """사용자 수준에 맞는 행이 0이면 전체에서 고른다 — 학습이 막히지 않는다(§9 Failure)."""
    async with db_pool.acquire() as conn:
        await conn.execute("delete from learning_sessions")
        await conn.execute("delete from learning_scenarios")
        user_id = await conn.fetchval(
            "insert into users (display_name, timezone, current_level) "
            "values ('c1', 'Asia/Seoul', 'C1') returning id"
        )
        only = await conn.fetchval(
            "insert into learning_scenarios (category, level, title, prompt_template) "
            "values ('daily_life', 'A2', 'stage', 'You are someone.') returning id"
        )

    session_id = await create_session(db_pool, user_id)

    async with db_pool.acquire() as conn:
        got = await conn.fetchval(
            "select scenario_id from learning_sessions where id = $1", session_id
        )
    assert got == only
```

⚠️ 이 절은 `db_pool` 을 쓴다(커밋된다). 파일 앞머리 docstring 이 그 픽스처의 teardown 을 이미 적어 두었다. `create_session` 이 import 목록에 이미 있는지 확인하고 없으면 더한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest ../../tests/unit/test_sessions.py -q -k "scenario"`
Expected: FAIL — 첫 테스트가 `picked[0] != picked[1]` 에서 깨진다(같은 행이 두 번 온다)

- [ ] **Step 3: `sessions.py` 를 고친다**

⑴ `_CREATE_SESSION_SQL` 을 **서브쿼리 없는 형태**로 바꾼다:

```python
# ⛔ **시나리오를 여기서 고르지 않는다** (`TASK-4` · 결정 73). 이전 판은 이 안에서
# `where s.level = (…) order by s.created_at, s.id limit 1` 로 골랐고, 그래서 **같은 사용자가
# 몇 번을 열어도 같은 행**을 받았다(시드 3행 중 `…101` 하나만 쓰였다). 배치 비율은 이력을
# 봐야 정해지므로 SQL 한 문장에 담기지 않는다 — `services/scenario_rotation` 이 규칙을
# 소유하고 `_pick_scenario_for_user` 가 그 입력을 읽는다.
# ⚠️ **폴백은 사라지지 않고 그 함수로 옮겼다** — 수준 일치가 0행이면 전체에서 고르고,
# 시나리오가 아예 없으면 `scenario_id`·`scenario_pick` 둘 다 null 로 세션이 열린다.
_CREATE_SESSION_SQL = """
insert into learning_sessions (user_id, scenario_id, mode, learning_source, scenario_pick)
values ($1, $4, $2, $3, $5)
returning id
"""

# 직전 창. ⚠️ `scenario_id is null` 인 세션은 창에서 뺀다 — 상황을 고르지 못한 세션은
# 「어느 상황을 했는가」에 대해 아무 말도 하지 않는다.
# ⛔ `created_at` 동률에서 순서가 흔들리지 않게 `id` 를 둘째 키로 둔다(결정론).
_RECENT_PICKS_SQL = """
select scenario_id, scenario_pick
  from learning_sessions
 where user_id = $1
   and scenario_id is not null
 order by created_at desc, id desc
 limit $2
"""

# 후보와 그 사용자의 마지막 사용 시각. `$2` 가 null 이면 수준 조건 없이 전체를 준다.
# ⛔ `category` 를 조건에 넣지 않는다 — 이전 판도 넣지 않았고, 값역을 좁히는 것은 이
# 결정의 범위가 아니다(설계서 §9).
_SCENARIO_CANDIDATES_SQL = """
select s.id,
       (select max(ls.created_at)
          from learning_sessions ls
         where ls.user_id = $1
           and ls.scenario_id = s.id) as last_used_at
  from learning_scenarios s
 where $2::text is null or s.level = $2::text
"""
```

⑵ 고르는 겉면을 더한다 — `create_session` 바로 위에 둔다:

```python
async def _pick_scenario_for_user(
    conn: asyncpg.Connection, user_id: UUID
) -> Pick | None:
    """이력과 후보를 읽어 `pick_scenario` 에 넘긴다. 규칙은 여기 없다.

    이 함수가 **DB 를 아는 유일한 자리**이고 규칙은 `services/scenario_rotation` 이 갖는다 —
    그 분리가 설계서 §6 의 비율 단정을 픽스처 없이 세게 한다.
    """
    level = await conn.fetchval("select current_level from users where id = $1", user_id)
    rows = await conn.fetch(_SCENARIO_CANDIDATES_SQL, user_id, level)
    if not rows:
        # 수준 일치가 0행 — 전체로 떨어진다. 학습이 막히는 것보다 시나리오가 조금 쉬운 편이
        # 낫다(이전 판 SQL 주석이 그 근거를 갖고 있었고 그것을 그대로 계승한다).
        rows = await conn.fetch(_SCENARIO_CANDIDATES_SQL, user_id, None)
    candidates = [
        Candidate(scenario_id=row["id"], last_used_at=row["last_used_at"]) for row in rows
    ]
    recent_rows = await conn.fetch(_RECENT_PICKS_SQL, user_id, WINDOW)
    recent = [
        RecentPick(scenario_id=row["scenario_id"], pick=row["scenario_pick"])
        for row in recent_rows
    ]
    return pick_scenario(recent=recent, candidates=candidates)
```

⑶ `create_session` 의 본문(docstring 아래)을 바꾼다. **docstring 과 시그니처는 건드리지 않고** 아래 단락 하나를 그 docstring 끝에 더한다:

```
    ⚠️ **시나리오 선택이 이 함수 안에서 두 단계다** (`TASK-4` · 결정 73). 이전 판은 insert 한
    문장이 서브쿼리로 골랐지만 배치 비율은 이력을 봐야 정해진다. 두 단계를 **한 트랜잭션**에
    두는 이유: 고르는 사이에 다른 세션이 열리면 창이 어긋난다.
```

본문:

```python
    async with pool.acquire() as conn:
        async with conn.transaction():
            picked = await _pick_scenario_for_user(conn, user_id)
            session_id = await conn.fetchval(
                _CREATE_SESSION_SQL,
                user_id,
                mode,
                learning_source or _DEFAULT_LEARNING_SOURCE,
                picked.scenario_id if picked is not None else None,
                picked.pick if picked is not None else None,
            )
    assert session_id is not None, "insert ... returning produced no row"
    return session_id
```

⑷ import 를 더한다:

```python
from app.services.scenario_rotation import (
    WINDOW,
    Candidate,
    Pick,
    RecentPick,
    pick_scenario,
)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest ../../tests/unit/test_sessions.py -q`
Expected: PASS

⚠️ **`_CREATE_SESSION_SQL` 을 문자열로 고정한 다른 테스트가 있으면 함께 빨강이 된다.** 그때는 그 단정이 무엇을 지키려던 것인지 읽고 고친다 — 지우지 않는다.

- [ ] **Step 5: 커밋한다**

```bash
git add app/backend/app/services/sessions.py tests/unit/test_sessions.py
git diff --cached --name-only
git commit -m "feat(TASK-4): 세션이 열릴 때 배치 규칙으로 상황을 고르게 했음 (결정 73)"
git show --stat HEAD
```

---

### Task 6: 게이트와 원장 마감

**Files:**
- Modify: `backlog/tasks/task-4 - 신규-요구사항-주제-9종-반복-70-대-신규-30-배치.md` (AC#1 체크 · 상태 `Done`)

**Interfaces:**
- Consumes: Task 1~5 전부
- Produces: 없음

- [ ] **Step 1: 게이트 여섯을 돌린다 — 파이프 없이 종료 코드로 받는다**

```bash
cd app/backend
.venv/bin/python -m pytest -q > /tmp/g1.out 2>&1; echo "pytest=$?"
.venv/bin/ruff check . > /tmp/g2.out 2>&1; echo "check=$?"
.venv/bin/ruff format --check . > /tmp/g3.out 2>&1; echo "format=$?"
.venv/bin/ruff check ../../tests ../../scripts > /tmp/g4.out 2>&1; echo "check_out=$?"
.venv/bin/ruff format --check ../../tests ../../scripts > /tmp/g5.out 2>&1; echo "format_out=$?"
/Users/redstar/.local/bin/ty check > /tmp/g6.out 2>&1; echo "ty=$?"
```

Expected: 여섯 다 `0`. ⛔ **cwd 가 `app/backend` 여야 한다** — 리포 루트에서 부르면 `line-length` 를 기본 88 로 재서 게이트 밖 검사가 거짓 빨강이 된다(`H-BN`). ⛔ `ty` 를 이름만으로 부르면 exit 127 이다.

- [ ] **Step 2: 빠뜨린 항목이 없는지 센다**

⛔ **여섯 개의 종료 코드를 모두 출력에서 읽는다.** 빠뜨린 항목은 「초록」이 아니라 「보지 않은 것」이다.

- [ ] **Step 3: 원장을 닫는다**

```bash
cd /Users/redstar/MyProject/OhMyEnglish
backlog task edit TASK-4 --check-ac 1
backlog task edit TASK-4 -s Done
backlog task view TASK-4 --plain
```

Expected: AC 4/4 · Status `Done`

- [ ] **Step 4: 커밋한다**

```bash
git add "backlog/tasks/task-4 - 신규-요구사항-주제-9종-반복-70-대-신규-30-배치.md"
git diff --cached --name-only
git commit -m "chore(TASK-4): 배치 구현을 마쳐 원장을 닫았음 — 게이트 여섯 exit 0"
git show --stat HEAD
```

---

## 자체 검토 — 계획을 설계서와 대조했다

**⑴ 설계서 절 대응**: §3(시드 15행) → Task 4 · §4(선택 규칙) → Task 1 · §4(DB 겉면) → Task 5 ·
§5(마이그레이션 016) → Task 3 · §6(검증 7개) → Task 2(1·2·3·7)와 Task 5(4·5)와 Task 1(6) ·
§7(단순 대안) → 코드 주석으로 근거를 옮겼다 · §8(대가) → Task 1·3 의 주석 · §9(범위 밖) → 계획에 작업 없음.

**⑵ 자리옮김 하나를 명시한다**: 설계서 §4 는 겉면 함수 이름을 `load_rotation_inputs` 로 적었고 계획은
`_pick_scenario_for_user` 로 바꿨다. 이유는 그 함수가 읽기만 하지 않고 **고른 결과를 돌려주기** 때문이다
— 이름이 하는 일과 맞아야 한다. ⚠️ 설계서를 고치지 않고 이 문장으로 대조를 남긴다(계획이 더 뒤에 쓰였다).

**⑶ 이름 일관성**: `pick_scenario`(순수 규칙) · `_pick_scenario_for_user`(DB 겉면) · `scenario_pick`
(컬럼) 셋이 비슷하다. 그래서 Task 1·5 의 주석이 **어느 것이 규칙이고 어느 것이 겉면인지**를 각각 적는다.

**⑷ 계획이 세지 못하는 것 하나**: 업무 상황에서 학습자가 얼어붙는지는 단위 테스트로 잴 수 없다
(결정 75 의 관측 항목). ⛔ **이 계획을 다 돌려도 그 관측은 열린 채다** — 회차로 보는 항목이고
`TASK-4` 를 닫는 조건이 아니다.

