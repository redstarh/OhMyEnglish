# 학습 시나리오 생성기 구현 계획 (`TASK-5`)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 음성 세션에서 질문 5개로 좁힌 무대를 세션 뒤 job 이 `learning_scenarios` 행 하나로 만들고, 그 행이 다음 신규 차례에 가장 먼저 집히게 한다.

**Architecture:** 새 tool 을 만들지 않는다. 질문은 시스템 프롬프트가 지시하고, 생성은 기존 job 큐(`analysis_jobs`)에 `generate_scenario` 종류를 더해 `plan_next_session` 과 같은 형태로 처리한다. 파서는 DB 를 모르는 순수 함수이고 「모델이 만들 수 없는 값」(`level`·`source`)은 호출자가 준다.

**Tech Stack:** Python 3.12 · asyncpg · pytest · PostgreSQL 17 · Claude(Bedrock InvokeModel) · ruff · ty

**Spec:** `docs/design/2026-09-12-scenario-generator-design.md`

## Global Constraints

- 결정의 정본은 `docs/ops/captain-instruction-register.md` 의 **결정 79·80** 이다. 계획이 그것과 어긋나면 계획이 틀렸다.
- ⛔ **새 tool 을 만들지 않는다** — 발음 tool 계약을 다른 갈래(`TASK-128` · 세션 `ohmyenglish-19`)가 고치는 중이다.
- ⛔ **`level`·`source` 를 모델에게 만들라고 하지 않는다** — 호출자가 준다(`parse_plan` 선례).
- **마이그레이션 번호는 적용 시점의 `schema_migrations` 조회로 발급한다**(`H-AL`). 이 계획 작성 시점의 최대는 `017` 이므로 `018` 을 쓴다.
- ⛔ `job_type` CHECK 를 늘릴 때 **`analysis_jobs_target_matches_job_type` 도 함께** 고친다 — 007 의 주석이 *"값만 늘리면 안 된다"* 로 그 함정을 적었다.
- 게이트는 cwd `app/backend` 에서 돌린다. 부분 실행에 `-c pyproject.toml` 을 붙인다(`H-AJ`). `ty` 는 절대경로 `/Users/redstar/.local/bin/ty` 로 부른다.
- `git add` 에 디렉터리를 주지 않는다. push 전 `git log --oneline origin/<브랜치>..HEAD` 로 올라갈 커밋을 열거한다(`H-BO`).

---

### Task 1: 마이그레이션 018 — `source` 컬럼 · job 종류 · 진입 모드

**Files:**
- Create: `db/migrations/018_scenario_source_and_generate_job.sql`
- Modify: `tests/unit/test_schema.py` (파일 끝에 테스트 셋)

**Interfaces:**
- Produces: `learning_scenarios.source text not null default 'seed' check (source in ('seed','generated'))` · `analysis_jobs.job_type` 에 `'generate_scenario'` · `analysis_jobs_target_matches_job_type` 에 그 분기 · `learning_sessions_mode_check` 에 `'scenario_intake'`

⛔ **네 번째가 왜 필요한가**: `learning_source='additional'` 로는 이 진입을 가릴 수 없다 — 추가 학습 메뉴 여섯 중 다섯이 그 값이고 그중 셋이 `mode` 를 갖지 않아 서로 구별되지 않는다(설계서 §5). 그 값을 조건으로 쓰면 자유 대화·약점 패턴 세션에 질문 지시가 샌다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_schema.py` 끝에 붙인다:

```python
# ── 018 시나리오 출처 + 생성 job (`TASK-5` · 결정 79·80) ──────────────────────
#
# ⛔ `default 'seed'` 가 요구다 — 기존 30행이 전부 시드이므로 소급 UPDATE 없이 참이 된다.
@pytest.mark.asyncio
async def test_scenario_source_defaults_to_seed_and_is_bounded(db_conn: asyncpg.Connection):
    got = await db_conn.fetchval(
        "insert into learning_scenarios (category, level, title, prompt_template) "
        "values ('daily_life', 'A2', 'defaulted', 'You are someone.') returning source"
    )
    assert got == "seed", "기본값이 seed 가 아니면 기존 행이 출처 없이 남는다"

    made = await db_conn.fetchval(
        "insert into learning_scenarios (category, level, title, prompt_template, source) "
        "values ('daily_life', 'A2', 'made', 'You are someone.', 'generated') returning source"
    )
    assert made == "generated"

    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into learning_scenarios (category, level, title, prompt_template, source) "
                "values ('daily_life', 'A2', 'bad', 'You are someone.', 'imported')"
            )


# ⛔ 값역만 늘리고 대상 제약을 안 고치면 job 을 «넣을 수 없다» — 007 이 그 함정을 적었다.
@pytest.mark.asyncio
async def test_generate_scenario_job_can_be_enqueued(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    job_id = await db_conn.fetchval(
        "insert into analysis_jobs (job_type, session_id) "
        "values ('generate_scenario', $1) returning id",
        session_id,
    )
    assert job_id is not None

    # 대상이 어긋나면 거부한다 — 발화 단위 job 이 아니다.
    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into analysis_jobs (job_type, utterance_id) values ('generate_scenario', $1)",
                uuid4(),
            )


# ⛔ 진입을 가릴 표지가 `learning_source` 로는 서지 않는다 — 추가 학습 메뉴 여섯 중 다섯이
# `additional` 이고 그중 셋이 `mode` 를 갖지 않아 서로 구별되지 않는다(설계서 §5). 그래서 014 가
# `pronunciation` 을 더한 것과 같은 형태로 `mode` 값역을 늘린다.
@pytest.mark.asyncio
async def test_session_mode_domain_includes_scenario_intake(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)

    got = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'scenario_intake') "
        "returning mode",
        migrate.USER_ID,
    )
    assert got == "scenario_intake"

    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into learning_sessions (user_id, mode) values ($1, 'intake')",
                migrate.USER_ID,
            )
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest -c pyproject.toml ../../tests/unit/test_schema.py -q -k "source_defaults or generate_scenario_job"`
Expected: FAIL — `column "source" of relation "learning_scenarios" does not exist`

- [ ] **Step 3: 마이그레이션을 쓴다**

`db/migrations/018_scenario_source_and_generate_job.sql`:

```sql
-- 018_scenario_source_and_generate_job.sql
-- ⑴ `learning_scenarios.source` 로 시드 행과 사용자 생성 행을 가른다.
-- ⑵ `analysis_jobs` 에 `generate_scenario` 종류를 더한다.
-- 결정: docs/ops/captain-instruction-register.md 「결정 79」(5회 질문은 음성 대화 · 생성은 세션 뒤
--   job) · 「결정 80」(사용자가 만든 상황은 신규 후보 맨 앞)
-- 소유 태스크: TASK-5 · 설계서: docs/design/2026-09-12-scenario-generator-design.md §4
--
-- 번호: `schema_migrations` 직접 조회로 발급한다(`H-AL`). ⛔ `008` 은 주간 리포트 예약 자리다.
--
-- ⛔ **`default 'seed'` 를 두는 이유**: 기존 행이 전부 시드이므로 소급 UPDATE 없이 참이 된다.
-- 소급 UPDATE 는 「값을 고쳐 표시를 맞추는」 부류라 이 리포가 금지한다.
-- ⛔ **`user_id` 를 두지 않는다** — 단일 사용자 로컬 도구이고(`api/ws.py` 의 `FIXED_USER_ID`)
-- 지금 두면 항상 같은 값이 들어가는 컬럼이 된다. 다중 사용자가 생기는 턴에 더한다.
--
-- ⛔ **`job_type` 값역만 늘리면 job 을 넣을 수 없다** — `analysis_jobs_target_matches_job_type` 이
-- 종류별로 대상 컬럼을 상호배타로 가두므로 그 분기를 함께 더해야 한다. 007 의 주석이 그 함정을
-- 이미 적었고 이 파일이 그것을 따른다.
--
-- 되돌리기: `source` 열 drop + 두 CHECK 를 017 상태로 되돌린다. ⚠️ `generated` 행이나
-- `generate_scenario` job 이 남아 있으면 CHECK 복원이 실패하므로 그 행을 먼저 지워야 한다.

alter table learning_scenarios
  add column source text not null default 'seed'
  check (source in ('seed', 'generated'));

alter table analysis_jobs
  drop constraint analysis_jobs_job_type_check;

alter table analysis_jobs
  add constraint analysis_jobs_job_type_check
  check (
    job_type in (
      'analyze_utterance',
      'summarize_session',
      'plan_next_session',
      'generate_scenario'
    )
  );

alter table analysis_jobs
  drop constraint analysis_jobs_target_matches_job_type;

alter table analysis_jobs
  add constraint analysis_jobs_target_matches_job_type
  check (
    (job_type = 'analyze_utterance' and utterance_id is not null and session_id is null)
    or (job_type = 'summarize_session' and session_id is not null and utterance_id is null)
    or (job_type = 'plan_next_session' and session_id is not null and utterance_id is null)
    or (job_type = 'generate_scenario' and session_id is not null and utterance_id is null)
  );

-- ⑷ 진입 모드. ⛔ `learning_source='additional'` 로는 이 진입을 «가릴 수 없다» — 추가 학습 메뉴
-- 여섯 중 다섯이 그 값이고 그중 셋(자유 대화·약점 패턴 집중·질문 답변 5개)이 `mode` 를 갖지 않아
-- 서로 구별되지 않는다(2026-09-12 에 `nova.py` 소유 갈래가 코드로 반증했다).
-- ⇒ 014 가 `pronunciation` 을 더한 것과 같은 형태로 값을 하나 더한다. 결정 67 이 세운 「세션 행이
-- 자기 진입을 적는다」 형태와 일관된다.
-- ⚠️ 값역 목록을 앱이 복제하지 않는다 — 이 CHECK 가 정본이고 `create_session` 은 목록을 갖지 않는다
-- (그 함수 docstring 이 그 근거를 이미 적었다).

alter table learning_sessions
  drop constraint learning_sessions_mode_check;

alter table learning_sessions
  add constraint learning_sessions_mode_check
  check (mode in ('speaking', 'shadowing', 'review', 'pronunciation', 'scenario_intake'));
```

⚠️ **위 네 값은 2026-09-12 에 dev DB 를 직접 조회해 얻은 것이다** — `speaking`·`shadowing`·
**`review`**·`pronunciation`. ⛔ **`review` 를 빠뜨리면 그 값이 지워진다.** 이 계획의 초안이 실제로
셋만 적었고 조회가 그것을 잡았다. ⇒ **적용 직전에 한 번 더 읽는다**:

```bash
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy -d ohmyenglish -tAc \
  "select pg_get_constraintdef(oid) from pg_constraint where conname='learning_sessions_mode_check'"
```

⛔ **출력의 값 전부를 새 CHECK 에 옮긴 뒤 `scenario_intake` 를 더한다.** `drop`+`add` 는 목록을
**대체**하므로 빠뜨린 값은 조용히 사라지고, 그 값을 쓰는 기존 행이 없으면 게이트도 침묵한다.

```bash
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy -d ohmyenglish -tAc \
  "select pg_get_constraintdef(oid) from pg_constraint where conname='learning_sessions_mode_check'"
```

- [ ] **Step 4: 발급 번호를 다시 확인하고 적용한다**

```bash
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy -d ohmyenglish -tAc \
  "select filename from schema_migrations order by 1 desc limit 1"
```

⛔ 그 출력이 `017*` 이 아니면 **파일 이름을 그 다음 번호로 고친 뒤** 적용한다.

```bash
PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h localhost -p 5432 -U ohmy -d ohmyenglish -1 -v ON_ERROR_STOP=1 \
  -f db/migrations/018_scenario_source_and_generate_job.sql \
  -c "insert into schema_migrations (filename) values ('018_scenario_source_and_generate_job.sql')"
```

Run: `cd app/backend && .venv/bin/python -m pytest -c pyproject.toml ../../tests/unit/test_schema.py -q`
Expected: PASS

- [ ] **Step 5: 커밋한다**

```bash
git add db/migrations/018_scenario_source_and_generate_job.sql tests/unit/test_schema.py
git diff --cached --name-only
git commit -m "feat(TASK-5): 시나리오 출처와 생성 job 종류를 더했음 (018 · 결정 79)"
git show --stat HEAD
```

---

### Task 2: 배치 규칙에 「사용자가 만든 것 먼저」 (결정 80)

**Files:**
- Modify: `app/backend/app/services/scenario_rotation.py` (`Candidate` · `_staleness`)
- Modify: `app/backend/app/services/sessions.py` (`_SCENARIO_CANDIDATES_SQL` · `_pick_scenario_for_user`)
- Modify: `tests/unit/test_scenario_rotation.py` (`_cands` 헬퍼 · 테스트 둘)
- Modify: `tests/unit/test_sessions.py` (DB 경로 테스트 하나)

**Interfaces:**
- Consumes: Task 1 의 `learning_scenarios.source`
- Produces: `Candidate(scenario_id, last_used_at, created_at, is_generated)` — 필드가 하나 늘어난다

- [ ] **Step 1: 순수 규칙 테스트를 쓴다**

`tests/unit/test_scenario_rotation.py` 의 `_cands` 를 고치고 테스트 둘을 더한다:

```python
def _cands(
    count: int,
    *,
    used: dict[int, int] | None = None,
    generated: set[int] | None = None,
) -> list[Candidate]:
    """`generated` 에 든 번호는 사용자가 만든 상황으로 둔다(결정 80)."""
    used = used or {}
    generated = generated or set()
    out = []
    for n in range(1, count + 1):
        ago = used.get(n)
        last = None if ago is None else _T0 - timedelta(days=ago)
        out.append(
            Candidate(
                scenario_id=_sid(n),
                last_used_at=last,
                created_at=_T0 + timedelta(seconds=n),
                is_generated=n in generated,
            )
        )
    return out


def test_user_made_stage_wins_the_new_slot() -> None:
    """⛔ 결정 80 — 사용자가 만든 상황이 신규 차례에서 가장 먼저 집힌다.

    `_sid(5)` 는 배열 맨 뒤(가장 늦게 만들어진 행)인데도 먼저 나와야 한다. 그러지 않으면
    사용자가 만든 무대를 **넉 달 뒤에** 보게 된다(결정 78 의 노출 속도).
    """
    got = pick_scenario(recent=[], candidates=_cands(5, generated={5}))
    assert got is not None
    assert got.scenario_id == _sid(5), "생성 상황이 시드보다 뒤로 밀렸다"
    assert got.pick == NEW


def test_user_made_stage_does_not_break_the_ratio() -> None:
    """⛔ 결정 78 은 그대로다 — 생성 상황이 있어도 신규 몫이 3보다 늘지 않는다."""
    recent = [RecentPick(scenario_id=_sid(n), pick=NEW) for n in (3, 2, 1)]
    got = pick_scenario(
        recent=recent, candidates=_cands(5, used={1: 3, 2: 2, 3: 1}, generated={5})
    )
    assert got is not None
    assert got.pick == REPEAT, "생성 상황이 있다고 신규 문턱을 넘었다"
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest -c pyproject.toml ../../tests/unit/test_scenario_rotation.py -q`
Expected: FAIL — `Candidate.__init__() got an unexpected keyword argument 'is_generated'`

- [ ] **Step 3: 규칙을 고친다**

`scenario_rotation.py`:

```python
@dataclass(frozen=True, slots=True)
class Candidate:
    """고를 수 있는 상황 한 건. `last_used_at` 이 `None` 이면 한 번도 쓰이지 않았다.

    (기존 docstring 유지)

    ⚠️ `is_generated` 는 **사용자가 대화로 만든 무대**를 뜻한다(`TASK-5` · 결정 80).
    `_staleness` 의 맨 앞자리가 그것이므로 **신규 차례에서 시드보다 먼저 집힌다.**
    ⛔ 이 필드가 비율을 바꾸지는 않는다 — 신규 문턱(`NEW_PER_WINDOW`)은 그대로다.
    """

    scenario_id: UUID
    last_used_at: datetime | None
    created_at: datetime
    is_generated: bool = False


def _staleness(candidate: Candidate) -> tuple[int, int, float, str]:
    """오래 안 쓴 것이 앞서는 정렬 키. **맨 앞자리는 「사용자가 만든 것인가」다**(결정 80).

    자리 넷의 뜻: ⑴ 사용자 생성이 먼저 ⑵ 한 번도 안 쓴 것이 먼저 ⑶ 오래된 것이 먼저
    ⑷ 동률을 결정론으로 가르는 UUID. ⚠️ ⑶ 이 「수준 일치 0행이면 가장 이른 행」이라는 기존
    계약을 계속 지킨다 — 자리를 앞에 끼워도 그 계약이 살아 있는 것이 이 배치의 조건이다.
    """
    made_first = 0 if candidate.is_generated else 1
    if candidate.last_used_at is None:
        return (made_first, 0, candidate.created_at.timestamp(), str(candidate.scenario_id))
    return (made_first, 1, candidate.last_used_at.timestamp(), str(candidate.scenario_id))
```

`sessions.py` 의 `_SCENARIO_CANDIDATES_SQL` 에 `s.source` 를 더하고 매핑을 고친다:

```python
_SCENARIO_CANDIDATES_SQL = """
select s.id,
       s.created_at,
       s.source,
       (select max(ls.started_at)
          from learning_sessions ls
         where ls.user_id = $1
           and ls.scenario_id = s.id) as last_used_at
  from learning_scenarios s
 where $2::text is null or s.level = $2::text
"""
```

```python
    candidates = [
        Candidate(
            scenario_id=row["id"],
            last_used_at=row["last_used_at"],
            created_at=row["created_at"],
            is_generated=row["source"] == "generated",
        )
        for row in rows
    ]
```

⛔ **두 자리를 같은 커밋에서 고친다** — 필드만 더하면 항상 `False` 가 들어가 결정 80 이 조용히 죽는다(설계서 §6 Dependency 가 그것을 지목했다).

- [ ] **Step 4: DB 경로 테스트를 더한다**

`tests/unit/test_sessions.py` 끝에 붙인다:

```python
@pytest.mark.asyncio
async def test_generated_stage_is_picked_before_seeded_ones(db_pool: asyncpg.Pool):
    """⛔ 결정 80 이 DB 경로에서도 성립한다 — 필드만 더하고 SQL 을 빼먹으면 여기서 깨진다."""
    async with db_pool.acquire() as conn:
        await conn.execute("delete from learning_sessions")
        await conn.execute("delete from learning_scenarios")
        user_id = await conn.fetchval(
            "insert into users (display_name, timezone, current_level) "
            "values ('made', 'Asia/Seoul', 'A2') returning id"
        )
        await conn.fetchval(
            "insert into learning_scenarios (category, level, title, prompt_template) "
            "values ('daily_life', 'A2', 'seeded', 'You are someone.') returning id"
        )
        made = await conn.fetchval(
            "insert into learning_scenarios (category, level, title, prompt_template, source) "
            "values ('daily_life', 'A2', 'made by user', 'You are someone.', 'generated') "
            "returning id"
        )

    session_id = await create_session(db_pool, user_id)

    async with db_pool.acquire() as conn:
        got = await conn.fetchval(
            "select scenario_id from learning_sessions where id = $1", session_id
        )
    assert got == made, "시드 행이 먼저 집혔다 — SQL 에 source 가 안 실렸다"
```

- [ ] **Step 5: 통과를 확인하고 커밋한다**

Run: `cd app/backend && .venv/bin/python -m pytest -c pyproject.toml ../../tests/unit/test_scenario_rotation.py ../../tests/unit/test_sessions.py -q`
Expected: PASS

```bash
git add app/backend/app/services/scenario_rotation.py app/backend/app/services/sessions.py tests/unit/test_scenario_rotation.py tests/unit/test_sessions.py
git diff --cached --name-only
git commit -m "feat(TASK-5): 사용자가 만든 상황을 신규 차례 맨 앞으로 올렸음 (결정 80)"
git show --stat HEAD
```

---

## 남은 태스크 개요 — Task 3~6

⛔ **Task 6 만 `nova.py` 를 만진다.** 그 파일을 소유한 갈래와 조율했고 「먼저 해도 된다」는 답을
받았다(설계서 §6 Dependency). 앞의 셋은 그 파일과 무관하므로 순서를 그렇게 두었다.

| # | 무엇 | `nova.py` | DB |
|--:|---|---|---|
| 3 | 파서 `parse_scenario` — 모델 출력 검증 (순수 함수) | 안 만짐 | 안 탐 |
| 4 | 프롬프트 조립 `build_scenario_prompt` (순수 함수) | 안 만짐 | 안 탐 |
| 5 | job 처리 `process_scenario` + 세션 종료 시 job 등록 | 안 만짐 | 탐 |
| 6 | 질문 5개 블록을 시스템 프롬프트에 · 진입 배선 | **만짐** | 탐 |

---

### Task 3: 파서 `parse_scenario` — 모델 출력을 검증한다 (AC#3)

**Files:**
- Create: `app/backend/app/models/scenario_draft.py`
- Test: `tests/unit/test_scenario_draft.py`

**Interfaces:**
- Consumes: 없음 (DB·모델 호출을 모른다)
- Produces: `ScenarioValidationError(ValueError)` · `ScenarioDraft(category: str, title: str, prompt_template: str)` · `parse_scenario(raw: str, *, allowed_categories: frozenset[str], existing_titles: frozenset[str]) -> ScenarioDraft` · `normalize_title(title: str) -> str`

⛔ **`level` 과 `source` 가 반환에 없는 것이 이 파서의 계약이다**(AC#3 · 설계서 §5). 둘은 모델이
만들 수 없는 값이라 호출자가 붙인다 — `parse_plan` 이 `current_level` 을 인자로 받는 것과 같은 형태다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_scenario_draft.py` — 거부 조건 여섯과 통과 하나를 각각 잰다. 값역·중복 목록을
**인자로 받는다**는 것이 계약이므로 테스트가 그 인자를 직접 준다(DB 를 타지 않는다).

- [ ] **Step 2: 실패를 확인한다**

Run: `cd app/backend && .venv/bin/python -m pytest -c pyproject.toml ../../tests/unit/test_scenario_draft.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.scenario_draft'`

- [ ] **Step 3: 파서를 쓴다** — `models/plan.py` 의 `_json_candidates` 를 재사용한다(복제하지 않는다).

- [ ] **Step 4: 통과를 확인한다** — 그 파일만 돌린다(DB 를 타지 않으므로 다른 세션의 게이트와 겹치지 않는다).

- [ ] **Step 5: 커밋한다**

---

### Task 5: job 처리와 세션 종료 시 등록

**Files:**
- Modify: `app/backend/app/services/jobs.py` (상수 · `enqueue_generate_scenario`)
- Modify: `app/backend/app/services/scenario_generator.py` (`process_scenario` · 조회 SQL)
- Modify: `app/backend/app/services/sessions.py` (종료 경로에서 job 등록)
- Modify: `app/backend/app/workers/analysis_worker.py` (분기 추가)
- Test: `tests/unit/test_scenario_generation.py`

**Interfaces:**
- Consumes: Task 1 의 `source`·job 종류·`scenario_intake` / Task 3 의 `parse_scenario`·`normalize_title` / Task 4 의 `build_scenario_prompt`
- Produces: `JOB_TYPE_GENERATE_SCENARIO = "generate_scenario"` · `enqueue_generate_scenario(conn, session_id) -> UUID | None` · `process_scenario(pool, claude, job) -> None`

⛔ **워커 분기를 반드시 더한다.** 지금 `analysis_worker.py` 는 `JOB_TYPE_PLAN` 만 갈라내고 나머지를
`process_analysis` 로 보내며, 그 함수는 종류가 다르면 **실패로 보고한다**(그 파일 주석이 그 설계를
적었다). ⇒ 분기를 안 더하면 job 이 걸리기만 하고 **5회 재시도 뒤 영원히 `failed`** 가 된다.
⚠️ 조용히 잘못 처리되지는 않지만 **기능이 아예 돌지 않는다** — 그것을 재는 단정이 이 태스크의 핵심이다.

⛔ **Claude 호출을 트랜잭션 «밖»에서 한다** — `process_plan` 의 규약이다. 안에서 부르면 커넥션을
잡고 모델을 기다린다.

⛔ **모든 실패를 `report_failure` 로 보고하고 예외를 올리지 않는다.** 워커 루프가 한 job 때문에
죽으면 그 기능이 영구히 멈춘다.

**흐름**: `job.session_id` 검사 → 입력 읽기(전사문 · `users.current_level` · 기존 `generated` 제목 ·
`category` 값역) → 트랜잭션 밖 Claude → `parse_scenario` → 저장 트랜잭션 + `complete`.

**⛔ 즉시 종결(재시도 없음) 조건 하나**: 전사문이 비었다. 재시도해도 입력이 같으므로 재시도가
무의미하다(설계서 §6 Failure). ⚠️ 그것을 어떻게 표현할지는 구현에서 정한다 — `fail_or_retry` 는
5회까지 재시도하므로 그 경로를 그대로 쓰면 5회를 헛돈다.

- [ ] **Step 1: 테스트를 쓴다** — 아래 여덟을 잰다.
  1. `scenario_intake` 세션이 끝나면 `generate_scenario` job 이 걸린다.
  2. ⛔ **일반 세션이 끝나면 그 job 이 걸리지 «않는다»**(판별력 — 1번만 있으면 늘 거는 구현도 통과).
  3. 워커가 이 job 을 `process_analysis` 로 보내지 않는다.
  4. 정상 응답 → `learning_scenarios` 에 `source='generated'` 행 하나.
  5. ⛔ `level` 이 `users.current_level` 과 같다 — 모델이 준 값을 무시한다.
  6. 파서 거부 → 저장 0행 · `last_error` 채워짐.
  7. 전사문이 비면 즉시 종결(재시도 대기 상태로 남지 않는다).
  8. 이미 같은 제목의 `generated` 행이 있으면 거부.

- [ ] **Step 2~5**: 실패 확인 → 구현 → 통과 → 커밋. ⚠️ DB 를 타므로 게이트 전에 다른 세션에 알린다.
