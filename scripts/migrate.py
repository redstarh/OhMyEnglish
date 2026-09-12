#!/usr/bin/env python3
"""Apply `db/migrations/*.sql` in order, then seed fixed dev/demo data.

Standalone ops script — no dependency on the `app.backend` package, so it
can run with just `asyncpg` installed (e.g. `app/backend/.venv/bin/python`).

    app/backend/.venv/bin/python scripts/migrate.py

Seeding is idempotent, but not the same way for every table. `users` uses
`on conflict (id) do nothing` — re-running never touches an existing row.
`learning_scenarios` and `shadowing_items` use `on conflict (id) do update` —
re-running never creates a duplicate row either, but it does overwrite the
mutable columns back to the constants in `SEED_SCENARIOS` /
`SEED_SHADOWING_ITEMS` below. Why `do update` was chosen anyway (fixed ids
would otherwise stay stale forever):
`docs/design/2026-09-07-scenario-and-drill-turns-design.md` §7 유도 8.

⚠️ **손으로 고친 시나리오·클립 행은 다음 실행에서 덮인다** — 그것이 위 선택의 대가다.
두 표 모두 **선택의 키가 되는 열은 갱신 대상에서 빼** 두었다(`learning_scenarios` 의
`category`·`level` · `shadowing_items` 의 `level`) — 각 상수 위 주석이 그 근거를 갖는다.

주의: 적용 추적은 파일명 기준이다 — pre-release 중 001을 재작성한 경우 이
스크립트는 (파일명이 그대로라) 재적용하지 않으므로 dev DB를 drop/재생성해야
한다 (`scripts/db_utils.recreate_database`).
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from pathlib import Path
from typing import NamedTuple
from uuid import UUID

import asyncpg
from db_utils import base_dsn

REPO_ROOT = Path(__file__).resolve().parent.parent
MIGRATIONS_DIR = REPO_ROOT / "db" / "migrations"

# Single-user local tool (§2 확정 실행 환경) — a fixed, deterministic id.
USER_ID = UUID("00000000-0000-0000-0000-000000000001")

# Fixed ids so the upsert below makes re-seeding idempotent.
#
# ⚠️ **이 3행은 「무대(상황·역할)」이고 질문이 아니다** — 캡틴 결정 14 (2026-09-07).
# 이전 판은 task brief 의 질문 3개를 그대로 넣고 `title`과 `prompt_template`에 **같은 문자열**을
# 썼다. 그 상태에서 지시문에 실으면 두 가지가 깨진다: ① 대화 지시문의 `Today's setting:` 자리에
# **질문**이 박혀 계획이 소유한 질문 3~5개와 종류가 겹친다 ② 「`title`은 지시문에 싣지 않는다」는
# 방어(SYSTEM_PROMPT 규칙 6: 메타데이터를 소리내어 읽지 마라)가 **공허해진다** — 같은 문자열이
# `prompt_template`으로 들어가므로. 근거의 정본은
# `docs/design/2026-09-07-scenario-and-drill-turns-design.md` §2.1·§2.2 다.
#
# **화제는 보존하고 종류만 바꿨다**(퇴근 후 · 주말 · 오늘 밤) — 원래 brief 의 화제를 잃지 않는다.
# 문구가 따른 학습자 프로필(h-doc) 규약은 **둘**이다: 난이도 상향 경로의 첫 칸(일상)에 머무르고
# **목표 수준(AWS 보고) 문형을 쓰지 않는다** — 그 문형으로 만들면 첫 세션에서 얼어붙는다.
# ⚠️ **셋 다 단문·단일 절인 것은 h-doc 규약이 아니라 판단이다** — h-doc 의 그 제약은 학습자가
# 말할 예문·질문에 걸린 것이고, 이 문장들은 학습자가 아니라 코치(모델)에게 가는 지시문이다.
# 짧게 쓴 이유는 짧을수록 모델이 무대를 덜 오해한다는 것뿐이다. 적용/비적용의 정본은
# `docs/design/2026-09-07-scenario-and-drill-turns-design.md` §2.1 의 갈라 적기다.
#
# ⛔ `category`·`level`을 바꾸지 마라. 세션 시작이 `users.current_level`(=`A2`)로 시나리오를
# 고르므로 `A2`가 아니면 그 경로가 폴백으로 떨어진다. `seed()`의 upsert가 그 두 열을 갱신
# 대상에서 빼 두는 것도 같은 이유다.
#
# ⚠️ **행을 15개로 늘렸다** (`TASK-4` · 결정 73·74·75 · 2026-09-12). 이전 주석은 *"여기서 행을
# 늘리지 않는다 — 업무 시나리오 추가는 캡틴 결정 5의 몫이고 `TASK-4`·`TASK-5`가 소유한다"* 였고,
# **그 조건이 충족돼 이 태스크가 늘린 것이다.**
# ⛔ **후보 수가 배치 규칙의 창보다 많아야 한다** — `services/scenario_rotation.WINDOW`(=10)가
# 그 값이고, 15가 10 이하로 줄면 신규가 마른다. 그 경계는 실측했다
# (`tests/unit/test_scenario_rotation.py::test_starvation_returns_when_topics_only_match_the_window`
# 이 후보 10에서 6회 마르는 것을 센다).
#
# ⛔⛔ **이 리스트의 «순서»가 제품 동작이다** (`TASK-4` · 결정 76). 배치 규칙은 신규를 고를 때
# 「한 번도 안 쓴 것 가운데 `created_at` 이 가장 이른 것」을 집고, 그 컬럼은 **이 배열의 삽입
# 순서**다. ⇒ **배열 끝에 붙인 상황은 「가장 늦게 나오는 상황」이 된다.**
# ⚠️ 그래서 업무 6종을 뒤에 몰아 두었던 첫 판은 **결정 75(「처음부터 섞는다」)를 문면만 이행했고**
# 실제로는 일상 9종을 다 소진한 뒤에야 업무가 나왔다 — dev DB 에서 실제 앱 경로로 12회를 열어
# **업무 0회**를 관측했다. 지금 순서가 그 관측의 결과다.
# ⛔ **새 상황을 그냥 끝에 붙이지 마라** — 어느 자리에 넣을지가 노출 순서를 정한다.
# `tests/unit/test_schema.py::test_seed_interleaves_business_stages_early` 가 이 계약을 지킨다.
#
# ⛔⛔ **그 순서는 `seed()` 가 트랜잭션 «밖»에서 도는 것에 걸려 있다** (2026-09-12 실측).
# `created_at` 의 기본값이 `now()` 이고 PostgreSQL 의 `now()` 는 **트랜잭션 시작 시각에 고정**된다
# ⇒ `seed()` 를 한 트랜잭션으로 감싸면 **15행의 `created_at` 이 전부 같아지고** 순서가 `id`(랜덤
# UUID)로 정해져 **결정 76 이 조용히 무너진다.** `main()` 은 지금 감싸지 않으므로 각 INSERT 가
# 자기 트랜잭션이고 순서가 유지된다 — ⚠️ **그것이 우연한 의존이라는 사실을 여기 적어 둔다.**
# ⛔ 성능이나 원자성을 이유로 `seed()` 를 트랜잭션으로 감싸려면 **먼저 순서를 명시 컬럼으로 옮겨야
# 한다**(`TASK-130`). 감싸는 것만 하면 게이트는 초록인 채 노출 순서가 뒤섞인다.
SEED_SCENARIOS: list[tuple[UUID, str, str, str, str]] = [
    # 일상 9종 — 이름은 `docs/PRD.md` §7 Daily Conversation 그대로다(v1.0 · 2026-08-24).
    # ⚠️ 캡틴 노트 항목 7이 새로 요구한 것은 이 이름 목록이 아니라 **배치 비율**이다.
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
    # ⚠️ `…103`은 *"Tonight's plans at home"* 에서 「식사」로 옮겼다 — 집·오늘 밤이라는 무대를
    # 유지하면서 9종의 한 자리를 채우는 가장 가까운 이동이다(설계서 §3).
    (
        UUID("00000000-0000-0000-0000-000000000103"),
        "daily_life",
        "A2",
        "Deciding what to eat tonight",
        "You are a housemate deciding with the learner what to eat tonight.",
    ),
    # ── 여기서부터 업무·일상을 번갈아 놓는다 (결정 76) ──────────────────────────
    # 업무 6종의 이름은 `docs/PRD.md` §7 Business English 그대로다. 캡틴 결정
    # (`docs/design/2026-09-06-captain-decisions.md` §1 항목 5)이 「주제 9종에 더한다」로 정했다.
    # ⛔ **`level`을 `A2`로 둔다 — 올리지 않는다**(결정 75의 완화 조항). 무대는 업무이고 문형
    # 난이도는 일상과 같다. `h-doc` 프로필이 경고한 실패(AWS 보고 수준 문형으로 예문을 만들면
    # 첫 세션에서 얼어붙는다)를 그것으로 피한다.
    (
        UUID("00000000-0000-0000-0000-000000000110"),
        "business",
        "A2",
        "Daily update in a short stand-up",
        "You are a teammate listening to the learner's short daily update.",
    ),
    # 여행 6종 — 017 이 값역에 `travel` 을 더했다(결정 77). 캡틴 예시 *"여행중 사고를 당한 상황"*
    # 이 이 계열의 첫 행이다. ⛔ `level` 은 `A2` 로 둔다 — 무대가 낯설수록 문형은 쉬워야 한다.
    (
        UUID("00000000-0000-0000-0000-000000000116"),
        "travel",
        "A2",
        "Getting help after an accident",
        "You are a passer-by helping the learner after a small accident.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000104"),
        "daily_life",
        "A2",
        "Meeting someone for the first time",
        "You are someone the learner has just met. Keep the small talk short and friendly.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000111"),
        "business",
        "A2",
        "Sharing a blocker",
        "You are a teammate the learner tells about something blocking their work.",
    ),
    # 쇼핑 3종 — 캡틴 예시 *"쇼핑중 물건을 교환하는 상황"* 이 이 계열의 첫 행이다.
    (
        UUID("00000000-0000-0000-0000-000000000122"),
        "shopping",
        "A2",
        "Exchanging something you bought",
        "You are a shop assistant the learner asks to exchange an item.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000105"),
        "daily_life",
        "A2",
        "Talking about a hobby",
        "You are a friend asking the learner about a hobby they enjoy.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000112"),
        "business",
        "A2",
        "Moving a deadline",
        "You are a teammate the learner asks to move a deadline.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000117"),
        "travel",
        "A2",
        "Checking in at a hotel",
        "You are a hotel receptionist checking the learner in.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000106"),
        "daily_life",
        "A2",
        "How the day felt",
        "You are a close friend asking the learner how their day felt.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000113"),
        "business",
        "A2",
        "Agreeing what comes first",
        "You are a teammate deciding with the learner which task comes first.",
    ),
    # 진료·건강 3종 — 017 이 값역에 `health` 를 더했다. ⚠️ 셋째 행(잠·피로)은 일상의 「감정」과
    # 가까우나 몸 상태를 말하는 어휘가 달라 갈라 두었다.
    (
        UUID("00000000-0000-0000-0000-000000000125"),
        "health",
        "A2",
        "Describing a symptom at a pharmacy",
        "You are a pharmacist the learner describes a symptom to.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000107"),
        "daily_life",
        "A2",
        "Asking the way to a station",
        "You are a passer-by the learner stops to ask for directions.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000114"),
        "business",
        "A2",
        "Reporting a small service problem",
        "You are a teammate the learner reports a small service problem to.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000118"),
        "travel",
        "A2",
        "Missing a train",
        "You are a station staff member the learner asks about a train they missed.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000108"),
        "daily_life",
        "A2",
        "Asking a small favour",
        "You are a neighbour the learner asks for a small favour.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000115"),
        "business",
        "A2",
        "Short report to a manager",
        "You are a manager listening to the learner's short project report.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000123"),
        "shopping",
        "A2",
        "Asking for a different size",
        "You are a shop assistant the learner asks for another size.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000109"),
        "daily_life",
        "A2",
        "Giving an opinion about a film",
        "You are a friend asking the learner what they thought about a film.",
    ),
    # ── 여기부터가 30개를 채우는 뒷부분이다 (`TASK-102` AC#3 · 결정 77) ─────────────
    # ⛔ 계열이 둘 연달아 오지 않게 이어 붙였다 — 앞부분과 같은 규약이고
    # `test_seed_interleaves_business_stages_early` 가 배열 전체에 그것을 강제한다.
    # ⚠️ 업무 셋(`…128`~`…130`)은 `h-doc` 프로필의 목표 수준(회의 참여·프로젝트 설명·보고)에
    # 직접 걸리는 무대다. 캡틴 예시 *"회의 중 보고상황"* · *"주제를 정한 회의에서 회의진행"* 이
    # 앞의 둘이다.
    (
        UUID("00000000-0000-0000-0000-000000000128"),
        "business",
        "A2",
        "Reporting in a team meeting",
        "You are a colleague listening to the learner report in a team meeting.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000119"),
        "travel",
        "A2",
        "Ordering at a restaurant abroad",
        "You are a waiter taking the learner's order.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000126"),
        "health",
        "A2",
        "Making a clinic appointment",
        "You are a clinic receptionist taking the learner's appointment.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000120"),
        "travel",
        "A2",
        "Asking about a day tour",
        "You are a tour desk staff member answering the learner's questions.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000129"),
        "business",
        "A2",
        "Running a meeting from an agenda",
        "You are a teammate in a meeting the learner runs from an agenda.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000121"),
        "travel",
        "A2",
        "Reporting lost luggage",
        "You are an airline staff member the learner reports lost luggage to.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000124"),
        "shopping",
        "A2",
        "Paying and asking for a receipt",
        "You are a cashier serving the learner.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000130"),
        "business",
        "A2",
        "Explaining what a project does",
        "You are a new teammate the learner explains their project to.",
    ),
    (
        UUID("00000000-0000-0000-0000-000000000127"),
        "health",
        "A2",
        "Talking about sleep and tiredness",
        "You are a friend asking the learner about their sleep.",
    ),
]

# 쉐도잉 클립 (`TASK-45` AC#8 · **캡틴 결정 25**). 표를 만들어도 0행이면 쉐도잉은 동작하지
# 않는다 — 설계서 `2026-09-08-shadowing-task-design.md` 약점 2 가 그것을 지목했고 결정 25 가
# 시드로 닫았다.
#
# ⛔ **외부 콘텐츠를 긁어오지 않는다.** PRD §5 가 자동 수집을 비범위로 두고 §7 이 *"외부 영상은
# 메타데이터·링크만 보관하고 사용자가 선택한 콘텐츠만 과제로 사용한다"* 고 정했다. 그래서
# 결정 25 가 고른 형태는 **학습자 수준에 맞춰 직접 작성한 자체 문장**이고 `source_url`은
# **null**이다(011 의 그 컬럼 주석: null = 내장·직접 입력 자료). 학습자가 링크를 넣는 경로는
# 이 상수가 아니라 `TASK-10` 의 진입점 설계가 소유한다.
#
# ⛔ `level`을 바꾸지 마라 — `SEED_SCENARIOS` 의 같은 경고와 **같은 이유이고 더 조용하다**:
# `_ATTACH_SHADOWING_CLIP_SQL` 이 `users.current_level`(=`A2`)로 좁힌 뒤 **없으면 가장 이른
# 행으로 폴백한다.** 즉 수준이 어긋나도 세션은 열리고 아무 것도 실패하지 않는다.
# `tests/unit/test_shadowing_seed.py` 가 그 침묵을 깨는 단정을 갖는다.
#
# **문구가 따른 학습자 프로필(h-doc) 규약 셋**: 단문·단일 절 · 난이도 상향 경로의 첫 칸(일상)에
# 머무른다 · **목표 수준(AWS 보고) 문형을 쓰지 않는다.** 담화 표지(`First` · `Then` ·
# `After that`)를 얹은 것은 규약이 아니라 판단이다 — 쉐도잉은 학습자가 짓지 않은 문장을 따라
# 읽는 것이므로, 아직 스스로 만들지 못하는 **발화 순서**를 발판으로 주는 값어치가 있다.
#
# ⚠️ **`clip_end_sec` 는 실측 낭독 길이가 아니다 — 발명을 명시한다.** 자체 문장이라 출처 오디오가
# 없어서 잴 대상이 아직 없다. 그래서 **PRD §7 의 하한 30초**를 그대로 썼다(요구사항 값이고 내가
# 고른 숫자가 아니다). TTS 로 실물 오디오를 만드는 턴에 **실측으로 고친다.**
#
# **분량은 늘리지 않는다** — 결정 25 가 *"학습 1회가 성립하는 최소"* 로 못 박았다. 선택 절이
# `limit 1`이므로 행을 늘려도 첫 행만 쓰인다: 늘리는 것은 죽은 데이터를 만드는 것이다.


class ShadowingSeedClip(NamedTuple):
    """시드 클립 1행. **필드 순서가 아래 insert 의 컬럼 순서와 묶여 있다**(`*clip`으로 넘긴다).

    ⚠️ **`SEED_SCENARIOS`가 평범한 5원소 튜플인데 이쪽만 `NamedTuple`인 것은 의도다.** 그 표는
    다섯 값이 전부 서로 다른 뜻의 문자열이라 위치로 읽히는데, 이쪽에는 **뒤바꿔도 타입이 같은
    이웃 둘**(`clip_start_sec`·`clip_end_sec`)이 있다. 이름이 없으면 순서를 뒤집은 시드가
    `clip_end_sec > clip_start_sec` CHECK 에서야 발각되고, 그것도 값에 따라 조용히 통과한다.
    """

    id: UUID
    source_title: str
    source_url: str | None
    transcript: str
    clip_start_sec: Decimal
    clip_end_sec: Decimal
    level: str


SEED_SHADOWING_ITEMS: list[ShadowingSeedClip] = [
    ShadowingSeedClip(
        id=UUID("00000000-0000-0000-0000-000000000201"),
        source_title="A morning routine before work",
        source_url=None,
        transcript=(
            "I usually wake up at seven. First, I check my phone for messages. "
            "Then I make a cup of coffee. After that, I get ready for work. "
            "The bus stop is close to my house. "
            "It takes about thirty minutes to get to the office."
        ),
        clip_start_sec=Decimal("0.00"),
        clip_end_sec=Decimal("30.00"),
        level="A2",
    ),
]


async def _ensure_migrations_table(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        create table if not exists schema_migrations (
            filename text primary key,
            applied_at timestamptz not null default now()
        )
        """
    )


async def apply_migrations(conn: asyncpg.Connection) -> None:
    """Apply each `db/migrations/*.sql` file at most once, tracked by
    filename in `schema_migrations` — running this script again (e.g. on
    every backend startup, per design doc §7 Dependency init order) must
    not fail with "relation already exists".

    Deliberately not `db_utils.recreate_database`: this applies to the dev DB
    in place (no drop), accumulating idempotently — the destructive drop/create
    is only ever correct for disposable test/smoke databases.
    """
    await _ensure_migrations_table(conn)
    for sql_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        already_applied = await conn.fetchval(
            "select exists(select 1 from schema_migrations where filename = $1)",
            sql_file.name,
        )
        if already_applied:
            continue
        async with conn.transaction():
            await conn.execute(sql_file.read_text())
            await conn.execute(
                "insert into schema_migrations (filename) values ($1)", sql_file.name
            )


async def seed(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        insert into users (id, display_name, timezone, current_level)
        values ($1, 'Learner', 'Asia/Seoul', 'A2')
        on conflict (id) do nothing
        """,
        USER_ID,
    )
    for scenario_id, category, level, title, prompt_template in SEED_SCENARIOS:
        await conn.execute(
            """
            insert into learning_scenarios (id, category, level, title, prompt_template)
            values ($1, $2, $3, $4, $5)
            -- ⚠️ `do nothing` 이 아니라 **`do update`** 다 (캡틴 결정 14 · 설계서 §7 유도 8).
            -- id 가 고정이므로 `do nothing` 이면 **상수를 고쳐도 이미 시드된 행은 영원히 낡은
            -- 값으로 남는다** — 2026-09-07 에 실제로 그랬다(개발 DB 3행이 질문 문구인 채였다).
            -- ⛔ `category`·`level` 은 갱신 대상에서 뺀다. 그 둘은 세션 시작이 시나리오를 고르는
            -- 키이고(`_CREATE_SESSION_SQL` 이 `users.current_level` 로 고른다), 여기서 덮으면
            -- 학습자 수준과 시나리오 값역의 관계를 시드가 조용히 바꾼다.
            on conflict (id) do update
               set title = excluded.title,
                   prompt_template = excluded.prompt_template
            """,
            scenario_id,
            category,
            level,
            title,
            prompt_template,
        )
    for clip in SEED_SHADOWING_ITEMS:
        await conn.execute(
            """
            insert into shadowing_items
                (id, source_title, source_url, transcript,
                 clip_start_sec, clip_end_sec, level)
            values ($1, $2, $3, $4, $5, $6, $7)
            -- `SEED_SCENARIOS` 와 **같은 규약**이다 (결정 14 · 설계서 §7 유도 8): 고정 id +
            -- `do update`. `do nothing` 이면 위 상수를 고쳐도 이미 시드된 행이 영원히 낡은 값으로
            -- 남는다 — 2026-09-07 에 시나리오 3행에서 실제로 그랬다.
            -- ⛔ `level` 은 갱신 대상에서 뺀다. 그것은 클립 선택의 키이고
            -- (`_ATTACH_SHADOWING_CLIP_SQL` 이 `users.current_level` 로 좁힌다), 여기서 덮으면
            -- 학습자 수준과 클립 값역의 관계를 시드가 조용히 바꾼다.
            on conflict (id) do update
               set source_title = excluded.source_title,
                   source_url = excluded.source_url,
                   transcript = excluded.transcript,
                   clip_start_sec = excluded.clip_start_sec,
                   clip_end_sec = excluded.clip_end_sec
            """,
            # `ShadowingSeedClip` 의 필드 순서가 위 컬럼 순서다 — 그 묶음의 근거는 그 클래스의
            # docstring 이 갖는다. 순서를 뒤집으면 재시드 테스트가 `transcript` 대조에서 잡는다.
            *clip,
        )


async def main() -> None:
    conn = await asyncpg.connect(dsn=base_dsn())
    try:
        await apply_migrations(conn)
        await seed(conn)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
