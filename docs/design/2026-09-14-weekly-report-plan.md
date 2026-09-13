# 주간 학습 리포트 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 주 단위 학습 리포트를 표에 적재하고 `/history/weekly` 화면까지 내서 학습자가 상위 오류 ·
개선 패턴 · 다음 주 추천 시나리오를 되짚게 함.

**Architecture:** 세션 종료 트랜잭션이 「지난 주 행이 없으면」 `summarize_week` job 을 걸고, 워커가
사실을 모아 Claude 에게 주고 판단을 받아 `weekly_reports` 한 행에 `metrics`(사실)와 `insights`(판단)를
함께 적재함. 주 경계는 `users.timezone` 으로 구한 **월요일**임.

**Tech Stack:** PostgreSQL 17 · asyncpg · FastAPI · Claude(`ClaudeClient`) · pytest ·
Next.js(app router · 인라인 style + CSS 변수).

**Spec:** `docs/design/2026-09-14-weekly-report-design.md`

## Global Constraints

- 태스크는 `TASK-26` 이고 **AC#1 은 이미 닫혔음**(결정 58). 이 계획이 AC#2·#3·#4 를 닫음.
- 게이트는 **cwd `app/backend`**(`H-A`·`H-BN`) · 부분 실행에 **`-c pyproject.toml`**(`H-AJ`) ·
  `ty` 는 절대경로 `/Users/redstar/.local/bin/ty`.
- ⛔ **`pytest` 전에 발음 축(`ohmyenglish-d9`)에 알림**(`H-X`).
- ⛔ `git add <디렉터리>` 금지(`H-BE`) · 커밋 **전** `git diff --cached --name-only` · push **전**
  `git log --oneline origin/<브랜치>..HEAD`(`H-BO`) · 공유 파일은 고친 턴에 커밋(`H-BR`).
- ⛔ 무력화 시험 되돌림 뒤 **`__pycache__` 를 지움**(`H-BS`).
- ⛔ 커밋 메시지 끝에 `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`.
- 마이그레이션 번호는 **적용 직전 조회로 발급**(`H-AL`). 이 계획을 쓴 시점의 최대는 `022` 이므로
  **`023`** 임. ⛔ `002`·`008` 은 영구 결번임(결정 27).
- ⛔ **dev DB 적용은 Task 7 이고 승인 사안임** — 사용자가 자리에 없는 동안 돌리지 않음.
- 점수·등급·달성률을 만들지 않음(R13-5 · PRD §15.3).

---

## Task 1: 마이그레이션 023 — 표 하나와 값역 셋

**Files:**
- Create: `db/migrations/023_weekly_reports.sql`
- Modify: `docs/database-schema.md`(「아직 SQL 에 없는 테이블」 절에서 `weekly_reports` 를 빼고 본문에
  명세를 넣음 — 010·011 이 세운 「마이그레이션과 문서를 한 커밋에」 규약)
- Test: `tests/unit/test_schema.py`

**Interfaces:**
- Produces: 표 `weekly_reports(id, user_id, week_start, metrics, insights, computed_at, created_at)` ·
  제약 `weekly_reports_week_starts_on_monday` · `weekly_reports_user_week_key` ·
  `analysis_jobs.job_type` 값역에 `summarize_week` · `llm_calls.purpose` 값역에 `summarize_week`.

- [ ] **Step 1: 실패하는 스키마 단정 넷을 쓴다**

`tests/unit/test_schema.py` 끝에 붙인다. 재는 것 넷: ⑴ 월요일이 아닌 `week_start` 거부
⑵ `(user_id, week_start)` 중복 거부 ⑶ `summarize_week` job 이 `session_id` 로만 들어가고
`utterance_id` 를 함께 주면 거부 ⑷ `llm_calls.purpose='summarize_week'` 가 받아진다.

```python
@pytest.mark.asyncio
async def test_weekly_report_week_start_must_be_monday(db_conn: asyncpg.Connection):
    """⛔ 결정 4·58 의 「월요일 시작」을 값역으로 새긴다 — 일요일 기준 계산이 조용히 섞이는 것을 막는다."""
    await _insert_user(db_conn)
    # 2026-09-14 는 월요일이다.
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start) values ($1, '2026-09-14')",
        migrate.USER_ID,
    )
    for bad in ("2026-09-13", "2026-09-15"):  # 일요일 · 화요일
        with pytest.raises(asyncpg.CheckViolationError):
            async with db_conn.transaction():
                await db_conn.execute(
                    "insert into weekly_reports (user_id, week_start) values ($1, $2::date)",
                    migrate.USER_ID,
                    bad,
                )


@pytest.mark.asyncio
async def test_weekly_report_is_one_row_per_user_and_week(db_conn: asyncpg.Connection):
    """재계산이 행을 늘리지 않는다 — 멱등의 뿌리다."""
    await _insert_user(db_conn)
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start) values ($1, '2026-09-14')",
        migrate.USER_ID,
    )
    with pytest.raises(asyncpg.UniqueViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into weekly_reports (user_id, week_start) values ($1, '2026-09-14')",
                migrate.USER_ID,
            )


@pytest.mark.asyncio
async def test_weekly_job_targets_a_session_and_nothing_else(db_conn: asyncpg.Connection):
    """⛔ 값역만 늘리면 job 이 들어가지 않는다 — 상호배타 CHECK 를 함께 고쳐야 한다(018 의 경고)."""
    await _insert_user(db_conn)
    session_id = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        migrate.USER_ID,
    )
    job_id = await db_conn.fetchval(
        "insert into analysis_jobs (job_type, session_id) values ('summarize_week', $1) returning id",
        session_id,
    )
    assert job_id is not None

    with pytest.raises(asyncpg.CheckViolationError):
        async with db_conn.transaction():
            await db_conn.execute(
                "insert into analysis_jobs (job_type) values ('summarize_week')"
            )


@pytest.mark.asyncio
async def test_llm_calls_accepts_the_weekly_purpose(db_conn: asyncpg.Connection):
    """⚠️ TASK-134 가 값역이 좁아 토큰 기록이 «조용히 사라진» 결함을 이미 잡았다 — 같은 실패를 막는다."""
    await _insert_user(db_conn)
    await db_conn.execute(
        "insert into llm_calls (purpose, model_id, input_tokens, output_tokens, user_id) "
        "values ('summarize_week', 'us.anthropic.claude-opus-5', 10, 20, $1)",
        migrate.USER_ID,
    )
```

⚠️ **`llm_calls` 의 실제 컬럼을 먼저 확인한다** — 위 insert 의 컬럼 목록이 다르면 그 표의 정의에
맞춘다(`db/migrations/001_initial_schema.sql` 과 021 을 읽는다).

- [ ] **Step 2: 돌려서 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_schema.py -q -k "weekly or weekly_purpose"`
Expected: FAIL — `UndefinedTableError: relation "weekly_reports" does not exist`
⛔ **선택된 개수를 본다** — `-k` 가 넷을 다 고르는지 확인하고 0 selected 를 통과로 읽지 않는다.

- [ ] **Step 3: 마이그레이션을 쓴다**

```sql
-- 023_weekly_reports.sql
-- 주간 학습 리포트 — 표 하나 + job 종류 하나 + 토큰 기록 값역
-- 설계: docs/design/2026-09-14-weekly-report-design.md §3·§6
-- 캡틴 결정: 4(주 시작은 월요일 · 표로 적재한다) · 58(같은 경계를 대장에 등재) ·
--            91(트리거는 세션 종료 · 범위는 셋 다 + 화면까지) · 27(008 은 영구 결번)
-- 소유 태스크: TASK-26
--
-- 번호: `ls db/migrations/` 실측 최대가 022 이므로 023 이다. ⛔ 008 을 쓰지 않는다(결정 27).
-- ⛔ 소비자와 같은 커밋 흐름으로 나간다 — 011 이 세운 data-first 규약이다.

create table weekly_reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (id) on delete cascade,
  -- 그 주의 **월요일**. 계산은 `date_trunc('week', now() at time zone tz)` 이고 Postgres 가
  -- 월요일을 주 시작으로 쓴다(ISO 8601) — 아래 CHECK 가 그 경계를 값역으로 못박는다.
  week_start date not null,
  -- **사실**: 상위 오류 · 발생 수 · 패턴 종 수 · 세션 수. R11-8 의 「조회는 사실을 제공한다」.
  metrics jsonb not null default '{}',
  -- **모델 판단**: 개선 패턴 · 다음 주 추천 시나리오. R11-8 의 「판단은 학습 분석 Agent 가 한다」.
  -- ⛔ 점수·등급을 담지 않는다 — 프롬프트가 요구하지 않고 출력 규격에 그 키가 없다(R13-5 의 톤).
  insights jsonb not null default '{}',
  -- null = 아직 계산하지 않았다. `daily_error_summary.computed_at` 과 같은 규약이며
  -- 「분석이 돌고 담을 것이 0이었다」와 「아직 안 돌았다」를 구별한다(R13-7 과 같은 축).
  computed_at timestamptz,
  created_at timestamptz not null default now(),
  -- 재계산이 행을 늘리지 않게 한다 — 멱등의 뿌리이고 `on conflict` 가 이 키를 쓴다.
  constraint weekly_reports_user_week_key unique (user_id, week_start),
  -- ⛔ 일요일 시작으로 계산한 코드가 조용히 섞이는 것을 막는다.
  constraint weekly_reports_week_starts_on_monday check (extract(isodow from week_start) = 1)
);

-- 뜨거운 조회는 「그 사용자의 최근 주」 하나다.
create index weekly_reports_user_week_idx on weekly_reports (user_id, week_start desc);

-- job 종류를 늘린다. ⛔ **값역만 늘리면 job 이 들어가지 않는다** — 상호배타 CHECK 를 함께 고친다
-- (018 주석이 그 함정을 이미 적었다: "분기를 함께 더해야 한다").
alter table analysis_jobs drop constraint analysis_jobs_job_type_check;

alter table analysis_jobs
  add constraint analysis_jobs_job_type_check
  check (job_type in ('analyze_utterance', 'summarize_session', 'plan_next_session',
                      'generate_scenario', 'summarize_week'));

alter table analysis_jobs drop constraint analysis_jobs_target_matches_job_type;

alter table analysis_jobs
  add constraint analysis_jobs_target_matches_job_type
  check ((job_type = 'analyze_utterance' and utterance_id is not null and session_id is null)
      or (job_type = 'summarize_session' and session_id is not null and utterance_id is null)
      or (job_type = 'plan_next_session' and session_id is not null and utterance_id is null)
      or (job_type = 'generate_scenario' and session_id is not null and utterance_id is null)
      -- ⚠️ 대상이 **세션**인 이유: 그 세션의 종료가 트리거다. 「어떤 주」는 job 이 들고 다니지 않고
      -- 워커가 세션 시각과 `users.timezone` 으로 다시 구한다(설계서 §6) — 공용 큐 표에 종류별
      -- 컬럼을 더하지 않는 것이 그 선택의 값어치다.
      or (job_type = 'summarize_week' and session_id is not null and utterance_id is null));

-- 토큰 기록의 값역. ⚠️ **021 이 이 자리를 늘리지 않아 기록이 «조용히 사라진» 결함이 있었다**
-- (`TASK-134` · `usage.py` 가 `PostgresError` 를 삼켰다). 같은 실패를 반복하지 않는다.
alter table llm_calls drop constraint llm_calls_purpose_check;

alter table llm_calls
  add constraint llm_calls_purpose_check
  check (purpose in ('plan', 'analysis', 'spike', 'nova', 'generate_scenario',
                     'summarize_session', 'summarize_week'));

-- ⛔⛔ **적용 절차는 011 의 5단계를 그대로 쓴다** — 백업(⚠️ `-T 'harness_*'` · `H-BT`) · 행 수 기록 ·
-- 적용 · 재조회 대조 · 어긋나면 멈추고 올린다.
-- 되돌리기: `drop table weekly_reports` + 위 세 값역을 이전 판으로. ⚠️ **값역 축소이므로
-- `summarize_week` 행이 하나라도 있으면 실패한다**(011 이 겪은 형태) — 그 행을 어떻게 할지는
-- 데이터 판단이므로 스크립트가 조용히 정하지 않는다.
```

- [ ] **Step 4: 돌려서 통과를 확인하고 문서를 함께 고친다**

Run: `cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_schema.py -q -k "weekly"`
Expected: PASS 넷

`docs/database-schema.md` 를 같은 커밋에서 고친다: 「아직 SQL 에 없는 테이블」 표에서
`weekly_reports` 행을 빼고, 본문에 컬럼 명세를 넣는다. ⚠️ **제안과 달라진 둘을 적는다** —
`metrics_json` → `metrics` · `plan` 을 따로 두지 않고 `insights` 안에 담음(설계서 §3 이 근거를 가짐).

- [ ] **Step 5: 판별력을 확인한다**

월요일 CHECK 를 `check (true)` 로 무력화해 red 를 보고 되돌린다. ⛔ 변이 적용을 `s2 != s` 로 먼저
단정하고, 되돌린 뒤 `__pycache__` 를 지운다(`H-BS`).

- [ ] **Step 6: 커밋한다**

```bash
git add db/migrations/023_weekly_reports.sql docs/database-schema.md tests/unit/test_schema.py
git diff --cached --name-only
git commit -m "feat(TASK-26): 023 으로 weekly_reports 표와 값역 셋을 냈음 …"
```

---

## Task 2: 주 경계와 트리거 — 지난 주가 없을 때만 job 을 건다

**Files:**
- Create: `app/backend/app/services/weekly_report.py`(주 경계 SQL 과 조회를 소유)
- Modify: `app/backend/app/services/jobs.py`(`JOB_TYPE_SUMMARIZE_WEEK` · `enqueue_summarize_week`)
- Modify: `app/backend/app/services/sessions.py`(`end_session` 의 job 묶음에 한 줄)
- Test: `tests/unit/test_weekly_report.py`(신규)

**Interfaces:**
- Consumes: Task 1 의 표와 값역.
- Produces: `JOB_TYPE_SUMMARIZE_WEEK = "summarize_week"` ·
  `enqueue_summarize_week(conn, session_id) -> UUID | None` ·
  `last_week_start(conn, user_id) -> date` · `weekly_report_exists(conn, user_id, week_start) -> bool`.

- [ ] **Step 1: 실패하는 단정 넷을 쓴다**

재는 것 넷:

```python
@pytest.mark.asyncio
async def test_last_week_start_is_the_monday_before_this_week(db_conn: asyncpg.Connection) -> None:
    """⛔ 사용자 타임존으로 구한다 — `current_date` 를 쓰지 않는다(R13-3 · 전역 규약).

    ⚠️ **KST 새벽 구간이 이 단정의 판별력이다**: UTC 자정~09:00 에는 `current_date` 가 KST 날짜보다
    하루 이르므로, 그 구간에 주가 바뀌면 두 방식이 **다른 월요일**을 낸다.
    """
    user_id = await _insert_user_with_timezone(db_conn, "Asia/Seoul")

    got = await last_week_start(db_conn, user_id)

    assert got.isoweekday() == 1, f"{got} 가 월요일이 아니다"
    today_kst = await db_conn.fetchval("select (now() at time zone 'Asia/Seoul')::date")
    assert 7 <= (today_kst - got).days <= 13


@pytest.mark.asyncio
async def test_timezone_changes_the_week_in_the_early_utc_window(db_conn: asyncpg.Connection) -> None:
    """타임존이 다르면 같은 순간에 다른 주를 가리킬 수 있다 — 그 성질이 살아 있는지 잰다.

    ⛔ 두 사용자를 만들어 `Pacific/Kiritimati`(UTC+14)와 `Pacific/Niue`(UTC-11)로 두고, 두 값의
    차이가 **0 또는 7일**임을 잰다(같은 주이거나 한 주 차이다). 값을 고정하지 않는 이유는 이 단정이
    도는 시각에 따라 어느 쪽인지 달라지기 때문이다 — 고정하면 하루 뒤 낡는다.
    """
    east = await _insert_user_with_timezone(db_conn, "Pacific/Kiritimati")
    west = await _insert_user_with_timezone(db_conn, "Pacific/Niue")

    gap = (await last_week_start(db_conn, east)) - (await last_week_start(db_conn, west))

    assert gap.days in (0, 7)


@pytest.mark.asyncio
async def test_the_job_is_enqueued_when_last_week_has_no_row(db_conn: asyncpg.Connection) -> None:
    session_id = await _new_session(db_conn)

    assert await enqueue_summarize_week(db_conn, session_id) is not None


@pytest.mark.asyncio
async def test_the_job_is_not_enqueued_when_last_week_already_has_a_row(
    db_conn: asyncpg.Connection,
) -> None:
    """⛔ 결정 91 의 「지난 주 리포트가 없으면」이 이 단정에 걸린다."""
    session_id = await _new_session(db_conn)
    user_id = await db_conn.fetchval(
        "select user_id from learning_sessions where id = $1", session_id
    )
    await db_conn.execute(
        "insert into weekly_reports (user_id, week_start) values ($1, $2)",
        user_id,
        await last_week_start(db_conn, user_id),
    )

    assert await enqueue_summarize_week(db_conn, session_id) is None
```

- [ ] **Step 2: 돌려서 실패를 확인한다** — `ModuleNotFoundError` 또는 `ImportError` 여야 한다.

- [ ] **Step 3: 서비스를 쓴다**

`services/weekly_report.py` 에 주 경계를 **한 곳에서** 소유한다.

```python
# 사용자 타임존의 「지금」에서 **지난 주 월요일**. ⛔ `current_date` 를 쓰지 않는다 —
# UTC 자정~09:00(KST) 구간에 그 값이 KST 날짜보다 하루 이르다(이 리포의 실측).
# ⚠️ `date_trunc('week', …)` 가 월요일을 주 시작으로 쓰는 것은 Postgres 의 성질이고 발명이 아니다
# (ISO 8601). 023 의 CHECK 가 같은 경계를 값역으로 못박는다 — 둘이 갈리면 그 CHECK 가 잡는다.
_LAST_WEEK_START_SQL = """
select (date_trunc('week', now() at time zone u.timezone) - interval '7 days')::date
  from users u
 where u.id = $1
"""
```

`jobs.py` 에 상수와 enqueue 를 더한다. ⛔ **한 문장으로 가드를 함께 건다** — 「없으면 넣는다」를
두 왕복으로 하면 그 사이에 다른 세션이 같은 job 을 넣는다.

```python
JOB_TYPE_SUMMARIZE_WEEK = "summarize_week"

# ⚠️ 위 `_ENQUEUE_PLAN_SQL` 을 쓰지 않는 이유: 이 job 은 **조건부**다(결정 91 의 「지난 주가 없으면」).
# 그 조건을 파이썬으로 옮기면 조회와 삽입 사이가 벌어져 중복이 생긴다.
_ENQUEUE_WEEK_SQL = """
insert into analysis_jobs (job_type, session_id)
select $1, s.id
  from learning_sessions s
  join users u on u.id = s.user_id
 where s.id = $2
   and not exists (
         select 1
           from weekly_reports w
          where w.user_id = s.user_id
            and w.week_start
                = (date_trunc('week', now() at time zone u.timezone) - interval '7 days')::date
       )
on conflict do nothing
returning id
"""
```

`sessions.py:end_session` 의 job 묶음 끝에 한 줄을 더한다.

```python
    # `TASK-26` · 결정 91 — 주간 리포트. ⛔ **조건부다**: 지난 주 행이 이미 있으면 넣지 않는다.
    # ⚠️ 이 리포에 스케줄러가 없어서 세션 종료가 유일한 주기 신호다 — 한 주에 한 번도 학습하지
    # 않으면 그 주 리포트가 생기지 않고, 그것은 결함이 아니라 이 트리거의 성질이다.
    await enqueue_summarize_week(conn, session_id)
```

- [ ] **Step 4: 통과를 확인한다** · **Step 5: 판별력** — `not exists` 절을 지워 「이미 있어도 넣는다」로
      만들고 넷째 단정이 red 인지 본다. 되돌린 뒤 `__pycache__` 를 지운다.
- [ ] **Step 6: 커밋한다**

---

## Task 3: 사실 모으기 — `metrics`

**Files:**
- Modify: `app/backend/app/services/weekly_report.py`(`load_week_facts`)
- Test: `tests/unit/test_weekly_report.py`

**Interfaces:**
- Produces: `load_week_facts(conn, user_id, week_start) -> WeekFacts`(frozen dataclass:
  `session_count: int` · `occurrence_count: int` · `pattern_count: int` ·
  `top_patterns: list[TopPattern]`), `TopPattern(category, pattern_key, target_form, occurrences)`.

- [ ] **Step 1: 단정을 쓴다** — 재는 것 넷: ⑴ 그 주 밖의 발생은 세지 않는다(경계의 앞·뒤 하루를 심어
      확인) ⑵ 상위 패턴이 발생 수 내림차순이고 동수는 `pattern_key` 로 갈린다(일일 요약의
      `ranked` CTE 와 같은 규약) ⑶ 오류 0건인 주는 빈 목록과 0 셋을 준다 ⑷ **다른 사용자의 발생이
      섞이지 않는다.**

```python
@pytest.mark.asyncio
async def test_week_facts_exclude_occurrences_outside_the_week(db_conn: asyncpg.Connection) -> None:
    """⛔ 경계가 이 단정의 축이다 — 하루 밀리면 지난 주와 이번 주가 섞인다."""
```

- [ ] **Step 2~6**: 실패 확인 → 구현(주 경계를 `[week_start, week_start + 7)` 반열림으로 씀 ·
      ⛔ `between` 을 쓰지 않는다: 끝을 포함해 다음 주 월요일이 함께 들어온다) → 통과 → 판별력
      (반열림을 `between` 으로 바꿔 red 를 봄) → 커밋.

---

## Task 4: 판단 받기 — 프롬프트 · 파서 · `process_weekly` · 워커 분기

**Files:**
- Modify: `app/backend/app/services/weekly_report.py`(`build_weekly_prompt` · `parse_weekly_insights`
  · `process_weekly` · `_store`)
- Modify: `app/backend/app/workers/analysis_worker.py`(분기 한 줄)
- Test: `tests/unit/test_weekly_report.py` · `tests/integration/test_worker.py`

**Interfaces:**
- Consumes: Task 2 의 `last_week_start` · Task 3 의 `load_week_facts` ·
  기존 `ClaudeClient` · `services/jobs.report_failure`·`complete`.
- Produces: `process_weekly(pool, claude, job) -> None` · `EMPTY_INSIGHTS` 상수 ·
  `WeeklyInsights(improving: list[str], next_scenarios: list[str])`.

- [ ] **Step 1: 단정을 쓴다** — 재는 것 여섯:
  ⑴ 프롬프트에 **한국어 요구**가 있고 인용은 영어 원문이다(`TASK-62` 결정 89 와 같은 규약)
  ⑵ ⛔ **프롬프트가 점수·등급을 «요구하지 않고» 출력 규격에 그 키가 없다** — 두 축을 갈라 잰다
     (`TASK-62` 가 「낱말의 부재」로만 재면 틀린 축이 된다는 것을 이미 겪었다)
  ⑶ 사실이 0건인 주는 **모델을 부르지 않고** 빈 모양으로 `done` 이 된다(총평의 규약)
  ⑷ 저장이 멱등이다 — 같은 job 을 두 번 처리해도 행이 하나다
  ⑸ `computed_at` 이 선다
  ⑹ 토큰 기록이 `purpose='summarize_week'` 로 **행을 남긴다**(⚠️ `TASK-134` 가 이 자리에서 조용한
     소실을 잡았으므로 「행이 남는지」를 직접 센다)
- [ ] **Step 2**: 실패 확인.
- [ ] **Step 3**: 구현. ⛔ **모델 호출은 트랜잭션 «밖»** 이고 저장은 한 트랜잭션 + `complete` 다
      (`process_summary` 와 같은 규약). 실패를 예외로 올리지 않는다 — 워커 루프가 죽으면 기능이
      영구히 멈춘다.
- [ ] **Step 4**: 워커 분기를 더한다.

```python
    elif job.job_type == JOB_TYPE_SUMMARIZE_WEEK:
        await process_weekly(pool, claude, job)
```

⛔ **이 줄을 빼면 `else` 가 `process_analysis` 로 보내고 그쪽 가드가 영구 `failed` 로 만든다** —
018 주석이 *"이 분기를 빼면 기능이 아예 돌지 않는다"* 로 적은 그 자리다.

- [ ] **Step 5**: 전체 게이트를 돌린다(`ShadowingClip` 때처럼 이웃이 깨질 수 있다) ·
      **Step 6**: 판별력 — 워커 분기를 지워 red 를 보고 되돌린다 · **Step 7**: 커밋.

---

## Task 5: API — `GET /api/weekly-report`

**Files:**
- Modify: `app/backend/app/api/daily.py`(같은 `/api` prefix 라우터에 라우트 하나) 또는
  Create: `app/backend/app/api/weekly.py`
- Modify: `app/backend/app/services/weekly_report.py`(`load_latest_report`)
- Test: `tests/integration/test_weekly_api.py`(신규)

**판정**: **`daily.py` 에 붙인다.** 근거 — 그 라우터의 prefix 가 이미 `/api` 이고 성격이 같다(되짚어
보는 조회). ⛔ 클립 오디오는 `/api/shadowing` 을 따로 만들었지만 그것은 **자원 계열이 달랐기**
때문이다(세션에 매이지 않은 제품 자산). 주간 리포트는 일일 요약과 같은 계열이다.
⚠️ `daily.py` 가 커지면 그때 가른다 — 지금 그 파일은 라우트 둘이다.

- [ ] **Step 1: 단정 셋을 쓴다** — ⑴ 계산된 주가 있으면 200 에 `week_start`·`analyzed=true`·
      `metrics`·`insights` ⑵ **행이 없으면 404 가 아니라 200 에 `analyzed=false`**(daily 의 규약)
      ⑶ ⛔ **asyncpg 가 jsonb 를 «문자열»로 준다** — `metrics` 가 dict 로 나가는지 직접 잰다
      (`TASK-62` 가 이 자리에서 API 가 총평을 한 번도 싣지 못한 결함을 겪었다).
- [ ] **Step 2~5**: 실패 확인 → 구현 → 통과 → 커밋.

---

## Task 6: 화면 — `/history/weekly`

**Files:**
- Create: `app/frontend/app/history/weekly/page.tsx`
- Modify: `app/frontend/lib/api.ts`(`fetchWeeklyReport`) · `app/frontend/app/history/page.tsx`(링크 하나)
- Test: 없음 — ⚠️ 프런트 테스트 인프라가 0이라 **브라우저 회차**가 검증이다.

- [ ] **Step 1**: `lib/api.ts` 에 타입과 fetch 를 더한다(`fetchHistory` 와 같은 모양 · `API_BASE` 를
      쓴다 — ⛔ 상대 경로를 쓰면 프런트 포트로 간다: `TASK-66.7` 회차가 그 결함을 잡았다).
- [ ] **Step 2**: 화면을 쓴다. 담는 것 넷: 주 범위(`week_start` ~ +6일) · 상위 오류 목록 ·
      개선 패턴 · 다음 주 추천. ⛔ 점수·등급·달성률을 그리지 않는다(PRD §15.3).
      `analyzed=false` 면 「아직 없어요」를 보이고 빈 표를 그리지 않는다.
- [ ] **Step 3**: `history/page.tsx` 에 링크 하나를 더한다 — 화면이 있어도 닿는 길이 없으면 소비자가
      0곳인 것과 같다.
- [ ] **Step 4**: `npx tsc --noEmit` · `npm run lint` 가 exit 0.
- [ ] **Step 5**: 브라우저 회차 — 검증 전용 스택(⛔ dev DB 를 쓰지 않는다) + 전용 Chrome.
      기록은 `tests/harness/runs/2026-09-14-task26-weekly/` 다.
- [ ] **Step 6**: 커밋.

---

## Task 7: dev DB 에 023 을 적용한다 — ⛔ **승인 없이 착수하지 않음**

- [ ] **Step 1**: 사용자 승인을 받는다(자리에 없는 동안 돌리지 않는다).
- [ ] **Step 2**: 011 의 5단계 — 백업(⚠️ `-T 'harness_*'` · `H-BT`) · 행 수 기록 · 적용 ·
      재조회 대조 · 어긋나면 멈추고 올린다.
- [ ] **Step 3**: 적용 전후 조회 출력을 원장에 남긴다. ⛔ `migrate.py` 는 조용한 성공이므로 출력만
      보고 판정하지 않는다.

---

## 자가 검토 — 계획을 설계서와 대조함

**설계서 절별 대응**: §3 스키마 → Task 1 · §4 주 경계 → Task 2 · §5 적재 근거 → Task 1·3
(문서에 적는 것은 설계서가 이미 했다) · §6 job·트리거 → Task 2·4 · §7 API·화면 → Task 5·6 ·
§8 테스트 축 → Task 1~6 의 단정과 Task 6 의 회차 · §9 되돌리기·위험 → 023 머리말과 Task 7 ·
§10 확인하지 못한 것 → Task 4 가 「모델에게 줄 사실」을 정하고 Task 6 회차가 사람 읽기를 연다.

**빠진 자리 하나를 적어 둠**: 설계서 §10 이 남긴 「개선 패턴의 판별력」은 Task 4 Step 3 에서
정한다 — 후보는 주별 발생 수 추이 · `review_tasks.review_stage` 의 이동 · 휴면 후 재발이고
⛔ `mastery_score` 는 쓰지 않는다(전부 `0.00` 이라 판별력 0).

**이름 대조**: `weekly_reports`(표) · `metrics`·`insights`·`computed_at`(컬럼) ·
`summarize_week`(job 종류·`llm_calls.purpose` 값 · 두 자리가 같은 철자여야 한다) ·
`JOB_TYPE_SUMMARIZE_WEEK`·`enqueue_summarize_week`·`last_week_start`·`weekly_report_exists`·
`load_week_facts`·`WeekFacts`·`TopPattern`·`build_weekly_prompt`·`parse_weekly_insights`·
`WeeklyInsights`·`process_weekly`·`load_latest_report`(심볼) ·
`GET /api/weekly-report`(경로) · `fetchWeeklyReport`(프런트).
