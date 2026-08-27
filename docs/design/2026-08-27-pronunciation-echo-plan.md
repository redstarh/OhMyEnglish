# 발음 시범·재발화 구현 계획 (Pronunciation Echo)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 학습자가 발음을 틀렸을 때 Agent가 올바른 발음으로 문장을 다시 읽어주고, 따라 말한 결과를 기록해 다음 학습에 쓰이게 한다.

**Architecture:** Nova 2 Sonic이 오디오를 직접 듣고 판정해 `toolUse`로 보고한다. Gateway는 그 페이로드를 **신뢰하지 않고 검증**해 `pronunciation_attempts`에 2단계 생명주기(`pending` → 판정)로 기록하고, 세션 종료 시 미판정 행을 `unclear`로 수렴시킨다. 전사문 경로는 발음을 판정하지 않는다 — 실측으로 흔적이 0이다. 분석 워커는 관여하지 않는다.

**Tech Stack:** Python 3.13 · FastAPI · asyncpg · pydantic v2 · PostgreSQL 16 · Nova 2 Sonic (`amazon.nova-2-sonic-v1:0`, bidirectional stream) · Next.js 16 · pytest (`asyncio_mode=auto`)

**Spec:** `docs/design/2026-08-27-pronunciation-echo-design.md` (요구사항: `docs/PRD.md` v1.1 §10)

---

## ⚠️ 구현 후 정정 (2026-08-28) — 이 계획의 일부 코드 블록은 낡았다

Task 1~6이 끝났고, 구현 중 실측·리뷰·캡틴 결정으로 **계획과 달라진 것 5건**이 있다.
아래 태스크 본문의 코드는 **당시 초안**이며 지금 코드와 다르다. 실제 계약의 정본은
**설계서 §3.1a·§3.2·§6.1**이고, 연속성 정본은 **`handoff/HANDOFF-v1.1-implementation.md`**다.

| # | 계획 | 실제 | 왜 |
|---|---|---|---|
| 1 | `order by created_at desc` | **`order by attempt_seq desc`** (004 신설) | `created_at` 기본값 `now()`는 트랜잭션 시각이라 한 트랜잭션의 두 행이 동값이다 — 실측 3회 중 1회 오래된 pending을 닫았다 |
| 2 | `record_attempt(..., signal_source=...)` 한 함수 | **`record_attempt` + `record_signal` 두 함수**, 그리고 감지기 진입점 **`note_transcript`** | 인자값이 생명주기 동작을 바꾸면 호출부에서 안 보인다. 감지 규칙을 세션에 두면 다음 감지기가 또 거기 박힌다(설계서 §3.1a) |
| 3 | 남은 pending을 `unclear`로 수렴 | **`incorrect` + `spoken_form=null`** | 캡틴 결정 — "대답을 못 한 것은 못 한 것"이고 이후 학습도 그냥 틀림으로 본다 |
| 4 | 한글 정규식·보조 신호를 `session.py`에 (Task 6 Step 3 a·c) | **`services/pronunciation.py`가 소유**. 세션은 `note_transcript` 한 줄 | 같음 — 규칙은 서비스, 배선은 세션 |
| 5 | `agent_reprompt`는 "5차수 관측 후 판정" | **만들지 않는다** (캡틴 결정) | 문구 매칭이라 케이스가 불어난다. R10-4 절반은 의도적 미충족 |

그리고 **예상 passed 수는 전부 낡았다** — 계획은 241 기준이고 실제 기준선은 **312**다.

Task 6 (d)의 "세션 상태를 기록하는 트랜잭션에 붙인다"는 당시 구조로 불가능했다
(`mark_session_ended`가 `pool`을 받아 자기 연결을 acquire했다). `sessions.py`에
`end_session(conn, …)`을 두고 `_close_and_record`가 트랜잭션을 여는 것으로 해결했다.

## Global Constraints

- **작업 디렉터리**: `/Users/redstar/MyProject/OhMyEnglish`. 새 워크트리를 만들지 않는다 — 테스트 스택이 이 워킹트리를 직접 서빙한다.
- **백엔드 포트는 8002**다. `:8000`은 다른 프로젝트(StockAgent)가 쓴다.
- **백엔드에 `--reload`가 없다.** 파이썬 소스를 고치면 반드시 재기동한다: `cd app/backend && .venv/bin/uvicorn app.api.main:app --port 8002 --log-level warning`
- **게이트는 `app/backend` cwd에서 판정한다.** 리포루트에는 ruff 설정이 없어 거기서 돌리면 기본 규칙으로 56 errors가 난다 — 그것은 회귀가 아니다.
  ```bash
  cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . \
    && .venv/bin/ruff format --check . && ty check
  ```
- **기준선: `241 passed`, skip/xfail 0.** 이 계획이 끝날 때 passed 수는 증가해야 하고 절대 감소하지 않는다.
- **`pytest`에 하위 경로를 직접 주면 `-c pyproject.toml`을 함께 준다** — rootdir이 리포 루트로 잡혀 `asyncio_mode=auto`를 못 찾는다.
- **`.env`를 편집하지 않는다.** 플래그는 환경변수로만 넘긴다.
- **오디오를 저장하지 않는다** (`PRD.md:107` opt-in 미저장 유지). 남기는 것은 판정과 시범 문장 텍스트뿐이다.
- **카테고리 코드값은 `pronunciation_intonation`이다** (`pronunciation`이 아니다). SoT는 `app/backend/app/models/analysis.py`의 `ErrorCategory` Literal이다.
- **임계값을 발명하지 않는다.** 발음 패턴은 `incorrect` **1회**에 생성한다 — 문법 오류와 같은 규약(`PRD.md:90`)이다. "N회 이상이면 만성" 같은 수치를 만들지 않는다.
- **스텁 어댑터는 새 이벤트를 흘리지 않는다.** 스텁 모드 화면에 발음 배지가 끼어들면 1·2차수 C2 판정이 바뀐다.
- **시각은 `timestamptz`**, 시간 기반 판정은 `clock_timestamp()`(`now()`는 트랜잭션 고정이다). naive datetime을 만들지 않는다.

---

## File Structure

| 파일 | 책임 |
|---|---|
| `db/migrations/003_pronunciation_echo.sql` (신규) | `pronunciation_attempts` 테이블 + 인덱스 |
| `app/backend/app/models/pronunciation.py` (신규) | tool 페이로드 검증 모델 + 결과 enum. **Nova 출력을 신뢰하지 않는 경계** |
| `app/backend/app/audio_gateway/port.py` (수정) | `PronunciationEvent`를 `AdapterEvent` 유니온에 추가 |
| `app/backend/app/audio_gateway/nova.py` (수정) | `promptStart.toolConfiguration` 전송 · `toolUse` → `PronunciationEvent` 변환 · `SYSTEM_PROMPT` 발음 규칙 |
| `app/backend/app/services/pronunciation.py` (신규) | 시도 생명주기(INSERT/UPDATE/수렴) + `error_patterns` upsert. **DB를 아는 유일한 곳** |
| `app/backend/app/audio_gateway/session.py` (수정) | 이벤트 분기 1개 추가 · 세션 종료 시 수렴 호출 · 한글 전사 신호 |
| `app/backend/app/services/results.py` (수정) | 결과 API에 발음 카드 포함 |
| `app/frontend/**` (수정) | 발음 배지 + 결과 화면 발음 카드 |

**왜 `services/pronunciation.py`를 따로 두는가**: `session.py`는 이미 세션 수명·저장·방송을 다 갖고 있어 크다. 발음 SQL을 거기 넣으면 두 책임이 섞인다. 그리고 생명주기 수렴 로직은 `session.py` 없이 단독 테스트해야 한다.

---

## Task 1: 003 마이그레이션 — `pronunciation_attempts`  —  ✅ 완료 `f7b8ccc`

**Files:**
- Create: `db/migrations/003_pronunciation_echo.sql`
- Test: `tests/unit/test_schema.py` (기존 파일에 추가)

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: 테이블 `pronunciation_attempts` — 컬럼 `id, session_id, utterance_id, pattern_id, target_form, spoken_form, target_sound, outcome, signal_source, created_at, resolved_at`. `outcome` CHECK `in ('pending','correct','incorrect','unclear')`, `signal_source` CHECK `in ('nova_tool','korean_transcript','agent_reprompt')`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_schema.py` 맨 아래에 추가한다. `db_conn` 픽스처가 `db/migrations/*.sql`을 전부 적용하므로 003이 없으면 실패한다.

```python
# ── 003 pronunciation_echo (발음 시범·재발화 설계서 §6.1) ────────────────────
async def test_pronunciation_attempts_table_exists(db_conn: asyncpg.Connection) -> None:
    columns = {
        r["column_name"]: r["is_nullable"]
        for r in await db_conn.fetch(
            "select column_name, is_nullable from information_schema.columns "
            "where table_name = 'pronunciation_attempts'"
        )
    }
    assert columns, "pronunciation_attempts 테이블이 없다 (003 미적용)"
    # not null 이어야 하는 것
    assert columns["session_id"] == "NO"
    assert columns["target_form"] == "NO"
    assert columns["outcome"] == "NO"
    # nullable 이어야 하는 것 — 시범 시점에는 아직 값이 없다 (설계서 F3)
    assert columns["spoken_form"] == "YES"
    assert columns["utterance_id"] == "YES"
    assert columns["pattern_id"] == "YES"
    assert columns["target_sound"] == "YES"
    assert columns["resolved_at"] == "YES"


async def test_pronunciation_attempts_rejects_unknown_outcome(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _seed_session(db_conn)
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into pronunciation_attempts (session_id, target_form, outcome) "
            "values ($1, 'I think.', 'bogus')",
            session_id,
        )


async def test_pronunciation_attempts_accepts_pending(db_conn: asyncpg.Connection) -> None:
    """`pending`은 정식 값이다 — Nova가 재발화 *전에* tool을 부르기 때문(설계서 F3·F4)."""
    session_id = await _seed_session(db_conn)
    row_id = await db_conn.fetchval(
        "insert into pronunciation_attempts (session_id, target_form, outcome, signal_source) "
        "values ($1, 'I think I found three very useful videos.', 'pending', 'nova_tool') "
        "returning id",
        session_id,
    )
    assert row_id is not None


async def test_pronunciation_attempts_cascades_with_session(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _seed_session(db_conn)
    await db_conn.execute(
        "insert into pronunciation_attempts (session_id, target_form, outcome) "
        "values ($1, 'I think.', 'pending')",
        session_id,
    )
    await db_conn.execute("delete from learning_sessions where id = $1", session_id)
    assert await db_conn.fetchval("select count(*) from pronunciation_attempts") == 0
```

`_seed_session`이 그 파일에 없으면 함께 추가한다 (기존 테스트가 세션을 만드는 방식을 그대로 따른다):

```python
async def _seed_session(conn: asyncpg.Connection) -> uuid4.__class__:
    """고정 사용자 + 첫 시나리오로 세션 1개를 만든다."""
    user_id = await conn.fetchval("select id from users limit 1")
    scenario_id = await conn.fetchval(
        "select id from learning_scenarios order by created_at, id limit 1"
    )
    return await conn.fetchval(
        "insert into learning_sessions (user_id, scenario_id, mode) "
        "values ($1, $2, 'speaking') returning id",
        user_id,
        scenario_id,
    )
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_schema.py -k pronunciation -v
```
Expected: 4건 전부 FAIL — `assert columns, "pronunciation_attempts 테이블이 없다"` 및 `UndefinedTableError`

- [ ] **Step 3: 마이그레이션을 쓴다**

`db/migrations/003_pronunciation_echo.sql`:

```sql
-- 003 — 발음 시범·재발화 (docs/design/2026-08-27-pronunciation-echo-design.md §6)
--
-- 요구사항: docs/PRD.md v1.1 §10 (R10-2 재발화 결과 기록, R10-7 오디오 미저장).
--
-- 왜 error_occurrences 를 쓰지 않는가: occurrence 는 분석 워커가 전사문에서 찾은
-- 오류에 붙는다. 발음은 전사문에 흔적이 0이라(4차수 P2 실측) 워커가 만들 수 없고,
-- 이 표의 행은 실시간 Nova 이벤트에서 만들어진다.
--
-- 왜 pattern_attempts 와 합치지 않는가: 그 표는 unique(pattern_id, utterance_id) 로
-- "패턴이 있는 발화의 재발화"를 센다. 발음 시도는 패턴이 아직 없을 수 있고, tool
-- 호출이 발화가 아니며, target_form/signal_source 처럼 그 표에 자리가 없는 필드를 갖는다.

create table pronunciation_attempts (
    id            uuid primary key default gen_random_uuid(),
    session_id    uuid not null references learning_sessions (id) on delete cascade,
    -- 시범을 유발한 발화. 보조 신호만으로 만든 행은 연결될 발화가 없을 수 있다.
    utterance_id  uuid references utterances (id) on delete set null,
    -- outcome='incorrect' 이고 target_sound 가 있을 때만 연결된다.
    pattern_id    uuid references error_patterns (id) on delete set null,
    -- 올바른 발음으로 읽어준 문장. 이것이 없으면 시범이 없었다는 뜻이라 not null.
    target_form   text not null check (length(btrim(target_form)) > 0),
    -- 학습자가 어떻게 들렸는지. 시범 시점에는 아직 없다 (설계서 F3).
    spoken_form   text,
    -- pattern_key 생성 재료. 예: 'th_as_s'
    target_sound  text,
    -- 'pending' 은 정식 값이다 — Nova 가 재발화 전에 tool 을 부른다 (설계서 F3·F4).
    -- 세션 종료 시 남은 pending 은 'unclear' 로 수렴된다 (설계서 §3.2).
    outcome       text not null
                  check (outcome in ('pending', 'correct', 'incorrect', 'unclear')),
    -- 이 행이 무엇 때문에 생겼는지. Nova 가 놓쳤을 때 보조 신호로 만든 행을 구분한다.
    signal_source text not null default 'nova_tool'
                  check (signal_source in ('nova_tool', 'korean_transcript', 'agent_reprompt')),
    created_at    timestamptz not null default now(),
    -- pending 을 벗어난 시각. outcome != 'pending' 일 때만 채워진다.
    resolved_at   timestamptz,
    constraint pronunciation_attempts_resolved_consistency
        check ((outcome = 'pending') = (resolved_at is null))
);

-- 세션 종료 시 남은 pending 행을 찾는 경로가 유일한 뜨거운 조회다 (설계서 §6.2).
create index pronunciation_attempts_session_outcome_idx
    on pronunciation_attempts (session_id, outcome);

-- 계획 생성이 최근 창으로 시도를 읽는 경로 (학습 코치 설계서 §4.4).
create index pronunciation_attempts_created_at_idx
    on pronunciation_attempts (created_at desc);
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_schema.py -k pronunciation -v
```
Expected: 4 passed

⚠️ `db_conn` 픽스처는 테스트 DB를 세션 스코프로 재생성한다. **dev DB(`:5433` `ohmyenglish`)에는 아직 적용되지 않았다** — 종단 테스트 전에 `app/backend/.venv/bin/python scripts/migrate.py`를 돌린다.

- [ ] **Step 5: 전체 게이트를 돌린다**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
```
Expected: `245 passed` (241 + 4), ruff·format·ty clean

- [ ] **Step 6: 커밋**

```bash
git add db/migrations/003_pronunciation_echo.sql tests/unit/test_schema.py
git commit -m "feat: 003 마이그레이션 — pronunciation_attempts (발음 시범·재발화 기록)"
```

---

## Task 2: tool 페이로드 검증 모델  —  ✅ 완료 `a0eff8e`

**Files:**
- Create: `app/backend/app/models/pronunciation.py`
- Test: `tests/unit/test_pronunciation.py` (신규)

**Interfaces:**
- Consumes: Task 1의 `outcome`·`signal_source` 값역
- Produces:
  - `PronunciationOutcome = Literal["pending", "correct", "incorrect", "unclear"]`
  - `SignalSource = Literal["nova_tool", "korean_transcript", "agent_reprompt"]`
  - `PRONUNCIATION_TOOL_NAME: str = "report_pronunciation_coaching"`
  - `PRONUNCIATION_TOOL_SCHEMA_JSON: str` — Nova `inputSchema.json`에 넣는 **문자열**
  - `parse_tool_payload(raw: str) -> PronunciationReport | None` — 신뢰할 수 없는 입력을 받아 검증된 모델 또는 `None`
  - `class PronunciationReport(pydantic.BaseModel)` — `target_form: str`, `spoken_form: str | None`, `target_sound: str | None`, `outcome: PronunciationOutcome`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_pronunciation.py`:

```python
"""발음 tool 페이로드 검증 (설계서 §4.2).

Nova 출력은 **신뢰할 수 없는 외부 데이터**다. 스파이크에서 실제로 스키마를 어겼다
(`outcome: "pending"`을 enum 밖에서 냈다 — 설계서 F4). 그래서 강등·폐기 규칙을
계약으로 못박는다.

픽스처의 원본은 실제 Nova 응답이다:
`tests/harness/runs/2026-08-27-P-tooluse-spike/P-tooluse-nova-events.json`
"""

from __future__ import annotations

import json

from app.models.pronunciation import (
    PRONUNCIATION_TOOL_NAME,
    PRONUNCIATION_TOOL_SCHEMA_JSON,
    parse_tool_payload,
)

# 2026-08-27 스파이크가 실제로 받은 페이로드 (그대로).
SPIKE_PAYLOAD = (
    '{"target_form":"I think I found three very useful videos.",'
    '"spoken_form":"[awaiting user repetition]","outcome":"pending"}'
)


def test_tool_name_is_stable() -> None:
    """어댑터와 모델이 같은 이름을 써야 한다 — 다르면 tool 이벤트가 조용히 버려진다."""
    assert PRONUNCIATION_TOOL_NAME == "report_pronunciation_coaching"


def test_tool_schema_is_a_json_string() -> None:
    """Nova Sonic 의 `inputSchema.json` 은 객체가 아니라 **문자열**이다 (스파이크 F1)."""
    assert isinstance(PRONUNCIATION_TOOL_SCHEMA_JSON, str)
    parsed = json.loads(PRONUNCIATION_TOOL_SCHEMA_JSON)
    assert parsed["type"] == "object"
    assert "target_form" in parsed["properties"]
    assert set(parsed["properties"]["outcome"]["enum"]) == {
        "pending", "correct", "incorrect", "unclear",
    }


def test_parses_the_real_spike_payload() -> None:
    report = parse_tool_payload(SPIKE_PAYLOAD)
    assert report is not None
    assert report.target_form == "I think I found three very useful videos."
    assert report.outcome == "pending"
    assert report.spoken_form == "[awaiting user repetition]"
    assert report.target_sound is None


def test_unknown_outcome_is_demoted_to_unclear() -> None:
    """열거값 밖이면 강등한다. 세션을 깨뜨리지 않는다 — 1차수 I-5에서 엄격 검증이
    발화를 5회 재시도 끝에 failed 로 만든 전례가 있다."""
    report = parse_tool_payload('{"target_form":"I think.","outcome":"kinda_ok"}')
    assert report is not None
    assert report.outcome == "unclear"


def test_missing_outcome_is_demoted_to_unclear() -> None:
    report = parse_tool_payload('{"target_form":"I think."}')
    assert report is not None
    assert report.outcome == "unclear"


def test_empty_target_form_is_discarded() -> None:
    """시범이 없는 시범 기록은 의미가 없다."""
    assert parse_tool_payload('{"target_form":"   ","outcome":"correct"}') is None
    assert parse_tool_payload('{"outcome":"correct"}') is None


def test_broken_json_is_discarded_without_raising() -> None:
    assert parse_tool_payload("not json at all") is None
    assert parse_tool_payload("") is None
    assert parse_tool_payload('{"target_form":') is None


def test_extra_fields_do_not_break_parsing() -> None:
    """모델이 새 필드를 더해도 우리가 죽지 않아야 한다."""
    report = parse_tool_payload(
        '{"target_form":"I think.","outcome":"correct","confidence":0.9,"nested":{"a":1}}'
    )
    assert report is not None
    assert report.outcome == "correct"


def test_target_sound_is_carried_when_present() -> None:
    report = parse_tool_payload(
        '{"target_form":"I think.","outcome":"incorrect","target_sound":"th_as_s"}'
    )
    assert report is not None
    assert report.target_sound == "th_as_s"
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_pronunciation.py -v
```
Expected: collection error — `ModuleNotFoundError: No module named 'app.models.pronunciation'`

- [ ] **Step 3: 최소 구현을 쓴다**

`app/backend/app/models/pronunciation.py`:

```python
"""발음 시범·재발화의 타입 경계 (설계서 §4.2).

**Nova 출력을 신뢰하지 않는다.** 2026-08-27 스파이크에서 모델이 실제로 스키마를
어겼다 — `outcome` enum 에 없는 `"pending"` 을 냈다(설계서 F4). 그래서 여기서 하는
일은 파싱이 아니라 **강등과 폐기**다:

* 열거값 밖 / 누락 → `unclear` 로 **강등**. 세션을 깨뜨리지 않는다.
* `target_form` 이 비었거나 JSON 이 깨졌으면 → **폐기**(`None`). 시범이 없는
  시범 기록은 의미가 없다.

엄격 검증으로 거부하지 않는 이유는 전례다 — 1차수 I-5 에서 모델 출력에 엄격 검증을
걸었을 때 그 발화가 5회 재시도 끝에 `failed` 가 됐다.
"""

from __future__ import annotations

import json
import logging
from typing import Literal, get_args

import pydantic

logger = logging.getLogger(__name__)

PronunciationOutcome = Literal["pending", "correct", "incorrect", "unclear"]
SignalSource = Literal["nova_tool", "korean_transcript", "agent_reprompt"]

PRONUNCIATION_OUTCOMES: tuple[PronunciationOutcome, ...] = get_args(PronunciationOutcome)
SIGNAL_SOURCES: tuple[SignalSource, ...] = get_args(SignalSource)

# 어댑터와 이 모듈이 같은 이름을 써야 한다 — 다르면 tool 이벤트가 조용히 버려진다.
PRONUNCIATION_TOOL_NAME = "report_pronunciation_coaching"

# Nova Sonic 의 `inputSchema.json` 은 **JSON 문자열**이다(객체가 아니다) — 스파이크 F1.
PRONUNCIATION_TOOL_SCHEMA_JSON = json.dumps(
    {
        "type": "object",
        "properties": {
            "target_form": {
                "type": "string",
                "description": "The full sentence you modeled with correct pronunciation.",
            },
            "spoken_form": {
                "type": "string",
                "description": "How the learner actually sounded, if you have heard it yet.",
            },
            "target_sound": {
                "type": "string",
                "description": "Reusable key for the sound that was off, e.g. th_as_s.",
            },
            "outcome": {
                "type": "string",
                "enum": list(PRONUNCIATION_OUTCOMES),
                "description": (
                    "Use pending when you have modeled the sentence but not yet heard "
                    "the learner repeat it."
                ),
            },
        },
        "required": ["target_form", "outcome"],
    }
)


class PronunciationReport(pydantic.BaseModel):
    """검증을 통과한 발음 보고. 여기까지 오면 신뢰할 수 있다."""

    model_config = pydantic.ConfigDict(extra="ignore", frozen=True)

    target_form: str
    outcome: PronunciationOutcome
    spoken_form: str | None = None
    target_sound: str | None = None


def parse_tool_payload(raw: str) -> PronunciationReport | None:
    """Nova tool 의 `content`(JSON 문자열)를 검증한다. 예외를 던지지 않는다."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        logger.warning("발음 tool 페이로드가 JSON 이 아니다 — 버렸다")
        return None
    if not isinstance(data, dict):
        logger.warning("발음 tool 페이로드가 객체가 아니다 — 버렸다")
        return None

    target_form = data.get("target_form")
    if not isinstance(target_form, str) or not target_form.strip():
        logger.warning("발음 tool 페이로드에 target_form 이 없다 — 버렸다")
        return None

    outcome = data.get("outcome")
    if outcome not in PRONUNCIATION_OUTCOMES:
        logger.warning("발음 outcome %r 을 unclear 로 강등했다", outcome)
        outcome = "unclear"

    def _text(key: str) -> str | None:
        value = data.get(key)
        return value if isinstance(value, str) and value.strip() else None

    return PronunciationReport(
        target_form=target_form.strip(),
        outcome=outcome,
        spoken_form=_text("spoken_form"),
        target_sound=_text("target_sound"),
    )
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_pronunciation.py -v
```
Expected: 9 passed

- [ ] **Step 5: 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
git add app/backend/app/models/pronunciation.py tests/unit/test_pronunciation.py
git commit -m "feat: 발음 tool 페이로드 검증 모델 (강등·폐기 규칙)"
```
Expected: `254 passed`

---

## Task 3: 포트 확장 — `PronunciationEvent`  —  ✅ 완료 `e6833c9`

**Files:**
- Modify: `app/backend/app/audio_gateway/port.py:80` (`AdapterEvent` 유니온)
- Test: `tests/unit/test_pronunciation.py` (같은 파일에 추가)

**Interfaces:**
- Consumes: Task 2의 `PronunciationOutcome`
- Produces: `class PronunciationEvent(pydantic.BaseModel)` — `target_form: str`, `outcome: PronunciationOutcome`, `spoken_form: str | None`, `target_sound: str | None`. `AdapterEvent`에 포함됨.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
def test_pronunciation_event_is_part_of_adapter_event_union() -> None:
    """세션 루프가 isinstance 로 분기하므로 유니온에 들어 있어야 한다."""
    from typing import get_args

    from app.audio_gateway.port import AdapterEvent, PronunciationEvent

    assert PronunciationEvent in get_args(AdapterEvent)


def test_pronunciation_event_is_frozen_and_rejects_extra() -> None:
    import pydantic
    import pytest as _pytest

    from app.audio_gateway.port import PronunciationEvent

    event = PronunciationEvent(target_form="I think.", outcome="pending")
    with _pytest.raises(pydantic.ValidationError):
        PronunciationEvent(target_form="I think.", outcome="pending", bogus=1)
    with _pytest.raises(pydantic.ValidationError):
        event.target_form = "changed"  # type: ignore[misc]
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_pronunciation.py -k adapter_event -v
```
Expected: FAIL — `ImportError: cannot import name 'PronunciationEvent'`

- [ ] **Step 3: 포트를 확장한다**

`port.py`의 `InterruptionEvent` 정의 **뒤**에 추가한다:

```python
class PronunciationEvent(pydantic.BaseModel):
    """발음 시범 1회 또는 그 재발화 판정 (설계서 §4.2).

    **어댑터만 만들 수 있다** — 오디오를 직접 듣는 것이 어댑터뿐이고, 전사문에는
    발음의 흔적이 0이다(4차수 P2 실측). 게이트웨이가 추측할 수 있는 값이 아니다.

    `outcome='pending'` 은 "시범은 했고 재발화는 아직"이다. Nova 가 재발화 *전에*
    tool 을 부르기 때문에 정상 상태다(설계서 F3) — 세션 종료 시 수렴된다(§3.2).
    """

    model_config = pydantic.ConfigDict(extra="forbid", frozen=True)

    target_form: str
    outcome: PronunciationOutcome
    spoken_form: str | None = None
    target_sound: str | None = None
```

같은 파일 상단에 import를 더한다:

```python
from app.models.pronunciation import PronunciationOutcome
```

유니온을 고친다 (`port.py:80`):

```python
AdapterEvent = (
    TranscriptEvent | SpeechBoundaryEvent | InterruptionEvent | PronunciationEvent | bytes
)
```

⚠️ 모듈 docstring의 "Phase 2 확장" 문단 아래에 한 줄 더한다 — 왜 다섯 번째 타입이 필요한지 남긴다:

```
* `PronunciationEvent` — Nova `toolUse`. 발음 판정은 오디오를 들어야 하고 전사문에는
  흔적이 0이라(4차수 P2), 기존 네 타입 중 어느 것에도 담을 수 없다.
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_pronunciation.py -v && .venv/bin/pytest -q
```
Expected: 11 passed (신규), 전체 `256 passed`

- [ ] **Step 5: 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
git add app/backend/app/audio_gateway/port.py tests/unit/test_pronunciation.py
git commit -m "feat: 포트에 PronunciationEvent 추가 (다섯 번째 어댑터 이벤트)"
```

---

## Task 4: 시도 생명주기 서비스  —  ✅ 완료 `ed91363`·`582eef6` — 정정 1·2·3 적용

**Files:**
- Create: `app/backend/app/services/pronunciation.py`
- Test: `tests/integration/test_pronunciation_service.py` (신규 — DB가 필요하다)

**Interfaces:**
- Consumes: Task 1 테이블, Task 2 `PronunciationOutcome`/`SignalSource`
- Produces:
  - `async def record_attempt(conn, session_id: UUID, *, target_form: str, outcome: PronunciationOutcome, spoken_form: str | None = None, target_sound: str | None = None, utterance_id: UUID | None = None, signal_source: SignalSource = "nova_tool") -> UUID`
    — `pending`이면 새 행을 만든다. 판정값이면 **같은 세션의 최신 pending 행을 UPDATE**하고, 없으면 새 행을 그 값으로 INSERT한다.
  - `async def resolve_dangling(conn, session_id: UUID) -> int` — 남은 `pending`을 `unclear`로 수렴시키고 바뀐 행 수를 돌려준다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/integration/test_pronunciation_service.py`:

```python
"""발음 시도 생명주기 (설계서 §3.2).

Nova 는 시범 시점에 pending 으로 한 번, 재발화를 들은 뒤 판정값으로 한 번 tool 을
부른다 — 두 번째가 오지 않을 수도 있다(설계서 F3·F6). 그래서 생명주기를 Gateway 가
갖고, **세션 종료 시 남은 pending 을 unclear 로 수렴시킨다.** pending 을 영구히
남기면 미판정 시도가 조용히 쌓여 숙련도 계산을 왜곡한다.
"""

from __future__ import annotations

import asyncpg

from app.services.pronunciation import record_attempt, resolve_dangling

TARGET = "I think I found three very useful videos."


async def _session(conn: asyncpg.Connection) -> object:
    user_id = await conn.fetchval("select id from users limit 1")
    scenario_id = await conn.fetchval(
        "select id from learning_scenarios order by created_at, id limit 1"
    )
    return await conn.fetchval(
        "insert into learning_sessions (user_id, scenario_id, mode) "
        "values ($1, $2, 'speaking') returning id",
        user_id,
        scenario_id,
    )


async def test_pending_creates_a_row_with_null_resolved_at(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    attempt_id = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="pending"
    )
    row = await db_conn.fetchrow(
        "select outcome, resolved_at, signal_source from pronunciation_attempts where id = $1",
        attempt_id,
    )
    assert row["outcome"] == "pending"
    assert row["resolved_at"] is None
    assert row["signal_source"] == "nova_tool"


async def test_verdict_updates_the_latest_pending_row(db_conn: asyncpg.Connection) -> None:
    """두 번째 tool 호출은 **새 행을 만들지 않고** 첫 행을 닫는다."""
    session_id = await _session(db_conn)
    first = await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")
    second = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="correct", spoken_form="I think..."
    )
    assert second == first, "같은 시도여야 한다 — 행이 두 개가 되면 시도 수가 부풀어 오른다"
    assert await db_conn.fetchval("select count(*) from pronunciation_attempts") == 1
    row = await db_conn.fetchrow(
        "select outcome, spoken_form, resolved_at from pronunciation_attempts where id = $1",
        first,
    )
    assert row["outcome"] == "correct"
    assert row["spoken_form"] == "I think..."
    assert row["resolved_at"] is not None


async def test_verdict_without_a_pending_row_inserts_one(
    db_conn: asyncpg.Connection,
) -> None:
    """Nova 가 pending 을 건너뛰고 판정만 보낼 수도 있다 — 기록을 잃지 않는다."""
    session_id = await _session(db_conn)
    attempt_id = await record_attempt(
        db_conn, session_id, target_form=TARGET, outcome="incorrect"
    )
    row = await db_conn.fetchrow(
        "select outcome, resolved_at from pronunciation_attempts where id = $1", attempt_id
    )
    assert row["outcome"] == "incorrect"
    assert row["resolved_at"] is not None


async def test_two_pendings_resolve_newest_first(db_conn: asyncpg.Connection) -> None:
    """한 세션에 시도가 여러 번 있을 수 있다. 판정은 **가장 최근** pending 을 닫는다."""
    session_id = await _session(db_conn)
    old = await record_attempt(db_conn, session_id, target_form="First.", outcome="pending")
    new = await record_attempt(db_conn, session_id, target_form="Second.", outcome="pending")
    closed = await record_attempt(
        db_conn, session_id, target_form="Second.", outcome="correct"
    )
    assert closed == new
    assert (
        await db_conn.fetchval(
            "select outcome from pronunciation_attempts where id = $1", old
        )
        == "pending"
    )


async def test_resolve_dangling_converges_pending_to_unclear(
    db_conn: asyncpg.Connection,
) -> None:
    session_id = await _session(db_conn)
    await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")
    await record_attempt(db_conn, session_id, target_form="Other.", outcome="pending")
    changed = await resolve_dangling(db_conn, session_id)
    assert changed == 2
    rows = await db_conn.fetch(
        "select outcome, resolved_at from pronunciation_attempts where session_id = $1",
        session_id,
    )
    assert [r["outcome"] for r in rows] == ["unclear", "unclear"]
    assert all(r["resolved_at"] is not None for r in rows)


async def test_resolve_dangling_is_idempotent(db_conn: asyncpg.Connection) -> None:
    session_id = await _session(db_conn)
    await record_attempt(db_conn, session_id, target_form=TARGET, outcome="pending")
    assert await resolve_dangling(db_conn, session_id) == 1
    assert await resolve_dangling(db_conn, session_id) == 0


async def test_resolve_dangling_does_not_touch_other_sessions(
    db_conn: asyncpg.Connection,
) -> None:
    mine = await _session(db_conn)
    theirs = await _session(db_conn)
    await record_attempt(db_conn, theirs, target_form=TARGET, outcome="pending")
    assert await resolve_dangling(db_conn, mine) == 0
    assert (
        await db_conn.fetchval(
            "select outcome from pronunciation_attempts where session_id = $1", theirs
        )
        == "pending"
    )


async def test_signal_source_is_stored(db_conn: asyncpg.Connection) -> None:
    """Nova 가 놓쳤을 때 보조 신호로 만든 행을 구분할 수 있어야 한다 (R10-4)."""
    session_id = await _session(db_conn)
    attempt_id = await record_attempt(
        db_conn,
        session_id,
        target_form="(전사문이 한국어로 인식되었습니다)",
        outcome="unclear",
        signal_source="korean_transcript",
    )
    assert (
        await db_conn.fetchval(
            "select signal_source from pronunciation_attempts where id = $1", attempt_id
        )
        == "korean_transcript"
    )
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/integration/test_pronunciation_service.py -v
```
Expected: collection error — `No module named 'app.services.pronunciation'`

- [ ] **Step 3: 서비스를 쓴다**

`app/backend/app/services/pronunciation.py`:

```python
"""발음 시도의 생명주기 (설계서 §3.2).

`session.py` 에 이 SQL 을 넣지 않는 이유는 두 가지다. ① 그 모듈은 이미 세션 수명·
저장·방송을 갖고 있어 책임이 섞인다. ② 수렴 로직은 Nova 없이 단독 테스트해야 한다.

생명주기:

    toolUse(pending)  → INSERT (resolved_at is null)
    toolUse(판정값)    → 같은 세션의 **최신** pending 을 UPDATE
                         (없으면 그 값으로 INSERT — 기록을 잃지 않는다)
    세션 종료         → 남은 pending 을 unclear 로 수렴 (resolve_dangling)

마지막 규칙이 핵심 방어다. pending 을 영구히 남기면 "판정되지 않은 시도"가 조용히
쌓여 숙련도 계산을 왜곡한다. 학습자가 대답하지 않고 세션을 끝낸 것도 정보이므로
없는 일로 만들지 않는다.
"""

from __future__ import annotations

import logging
from uuid import UUID

import asyncpg

from app.models.pronunciation import PronunciationOutcome, SignalSource

logger = logging.getLogger(__name__)


async def record_attempt(
    conn: asyncpg.Connection,
    session_id: UUID,
    *,
    target_form: str,
    outcome: PronunciationOutcome,
    spoken_form: str | None = None,
    target_sound: str | None = None,
    utterance_id: UUID | None = None,
    signal_source: SignalSource = "nova_tool",
) -> UUID:
    """시도를 기록하고 그 행의 id 를 돌려준다."""
    if outcome == "pending":
        return await conn.fetchval(
            """
            insert into pronunciation_attempts
                (session_id, utterance_id, target_form, spoken_form, target_sound,
                 outcome, signal_source)
            values ($1, $2, $3, $4, $5, 'pending', $6)
            returning id
            """,
            session_id,
            utterance_id,
            target_form,
            spoken_form,
            target_sound,
            signal_source,
        )

    # 판정값 — 가장 최근 pending 을 닫는다. `for update` 로 같은 세션의 동시 판정을 막는다.
    updated = await conn.fetchval(
        """
        update pronunciation_attempts set
            outcome      = $2,
            spoken_form  = coalesce($3, spoken_form),
            target_sound = coalesce($4, target_sound),
            utterance_id = coalesce($5, utterance_id),
            resolved_at  = clock_timestamp()
        where id = (
            select id from pronunciation_attempts
             where session_id = $1 and outcome = 'pending'
             order by created_at desc
             limit 1
             for update
        )
        returning id
        """,
        session_id,
        outcome,
        spoken_form,
        target_sound,
        utterance_id,
    )
    if updated is not None:
        return updated

    logger.info("닫을 pending 시도가 없어 판정값으로 새 행을 만든다 (세션 %s)", session_id)
    return await conn.fetchval(
        """
        insert into pronunciation_attempts
            (session_id, utterance_id, target_form, spoken_form, target_sound,
             outcome, signal_source, resolved_at)
        values ($1, $2, $3, $4, $5, $6, $7, clock_timestamp())
        returning id
        """,
        session_id,
        utterance_id,
        target_form,
        spoken_form,
        target_sound,
        outcome,
        signal_source,
    )


async def resolve_dangling(conn: asyncpg.Connection, session_id: UUID) -> int:
    """세션에 남은 `pending` 을 `unclear` 로 수렴시킨다. 바뀐 행 수를 돌려준다.

    멱등이다 — 두 번 불러도 두 번째는 0 이다.
    """
    rows = await conn.fetch(
        """
        update pronunciation_attempts
           set outcome = 'unclear', resolved_at = clock_timestamp()
         where session_id = $1 and outcome = 'pending'
        returning id
        """,
        session_id,
    )
    if rows:
        logger.info("미판정 발음 시도 %d건을 unclear 로 수렴했다 (세션 %s)", len(rows), session_id)
    return len(rows)
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/integration/test_pronunciation_service.py -v
```
Expected: 8 passed

- [ ] **Step 5: 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
git add app/backend/app/services/pronunciation.py tests/integration/test_pronunciation_service.py
git commit -m "feat: 발음 시도 생명주기 — pending 수렴 포함"
```
Expected: `264 passed`

---

## Task 5: Nova 어댑터 — `toolConfiguration` 전송 + `toolUse` 변환  —  ✅ 완료 `b31227a`·`1a8c908` — ⚠️ 실물 왕복 미검증

**Files:**
- Modify: `app/backend/app/audio_gateway/nova.py` — `promptStart` 페이로드(약 `:413`), 이벤트 디스패치(`:138-150`), `SYSTEM_PROMPT`(`:77`)
- Test: `tests/unit/test_nova.py` (기존 파일에 추가)

**Interfaces:**
- Consumes: Task 2 (`PRONUNCIATION_TOOL_NAME`, `PRONUNCIATION_TOOL_SCHEMA_JSON`, `parse_tool_payload`), Task 3 (`PronunciationEvent`)
- Produces: `toolUse` 이벤트가 `PronunciationEvent`로 변환되어 `events()`에 흐른다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_nova.py`에 추가한다. 기존 테스트가 가짜 스트림으로 이벤트를 흘려보내는 방식을 그대로 따른다 — 그 헬퍼 이름은 파일을 열어 확인하고 재사용한다(새로 만들지 않는다).

```python
# ── 발음 tool (설계서 §4.2, 스파이크 F1·F3·F4) ────────────────────────────────
def test_prompt_start_carries_the_pronunciation_tool() -> None:
    """`toolConfiguration` 이 없으면 Nova 는 tool 을 부를 수 없다 (스파이크 F1)."""
    from app.models.pronunciation import PRONUNCIATION_TOOL_NAME

    payload = _prompt_start_payload()  # 기존 헬퍼 또는 어댑터에서 꺼내는 방식
    tools = payload["event"]["promptStart"]["toolConfiguration"]["tools"]
    spec = tools[0]["toolSpec"]
    assert spec["name"] == PRONUNCIATION_TOOL_NAME
    # Sonic 은 inputSchema.json 을 **문자열**로 받는다 (실측).
    assert isinstance(spec["inputSchema"]["json"], str)


def test_system_prompt_instructs_pronunciation_modeling() -> None:
    """4차수는 지시가 없어서 Nova 가 발음을 지적하지 않았다. 스파이크는 지시하면
    한다는 것을 보였다 — 그 지시가 프롬프트에 실제로 있는지 못박는다."""
    from app.audio_gateway.nova import SYSTEM_PROMPT

    lowered = SYSTEM_PROMPT.lower()
    assert "pronunc" in lowered
    assert "repeat" in lowered


async def test_tool_use_becomes_a_pronunciation_event() -> None:
    events = await _drain_adapter_events([
        {"event": {"contentStart": {"type": "TOOL", "role": "TOOL", "contentId": "c1"}}},
        {"event": {"toolUse": {
            "toolName": "report_pronunciation_coaching",
            "contentId": "c1",
            "content": '{"target_form":"I think I found three very useful videos.",'
                       '"spoken_form":"[awaiting user repetition]","outcome":"pending"}',
        }}},
        {"event": {"contentEnd": {"type": "TOOL", "stopReason": "TOOL_USE", "contentId": "c1"}}},
    ])
    pronunciation = [e for e in events if isinstance(e, PronunciationEvent)]
    assert len(pronunciation) == 1
    assert pronunciation[0].outcome == "pending"
    assert pronunciation[0].target_form == "I think I found three very useful videos."


async def test_unknown_tool_name_is_ignored() -> None:
    """다른 tool 이 생겨도 발음 경로가 오작동하지 않아야 한다."""
    events = await _drain_adapter_events([
        {"event": {"toolUse": {"toolName": "something_else", "content": "{}"}}},
    ])
    assert not [e for e in events if isinstance(e, PronunciationEvent)]


async def test_broken_tool_payload_does_not_kill_the_stream() -> None:
    """PS6 — 깨진 페이로드에 세션이 살아남는다."""
    events = await _drain_adapter_events([
        {"event": {"toolUse": {
            "toolName": "report_pronunciation_coaching", "content": "not json",
        }}},
        {"event": {"contentStart": {"type": "TEXT", "role": "USER",
                                   "additionalModelFields": '{"generationStage":"FINAL"}',
                                   "contentId": "t1"}}},
        {"event": {"textOutput": {"contentId": "t1", "content": "hello", "role": "USER"}}},
    ])
    assert not [e for e in events if isinstance(e, PronunciationEvent)]
    # 뒤따라온 전사문은 정상적으로 흘러야 한다 — 스트림이 죽지 않았다는 증거다.
    assert any(isinstance(e, TranscriptEvent) and e.text == "hello" for e in events)
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_nova.py -k "pronunciation or tool" -v
```
Expected: FAIL — `KeyError: 'toolConfiguration'`, `assert "pronunc" in lowered`, `PronunciationEvent` 0건

- [ ] **Step 3: 어댑터를 고친다**

**(a) `promptStart`에 tool을 싣는다** (`nova.py` 약 `:413`):

```python
            {
                "event": {
                    "promptStart": {
                        "promptName": self._prompt_name,
                        "textOutputConfiguration": {"mediaType": "text/plain"},
                        "audioOutputConfiguration": { ... 기존 그대로 ... },
                        # 발음 판정을 DB로 가져오는 유일한 수단이다 (설계서 §4.2).
                        # 2026-08-27 스파이크에서 이 형태가 받아들여지는 것을 실측했다.
                        "toolConfiguration": {
                            "tools": [
                                {
                                    "toolSpec": {
                                        "name": PRONUNCIATION_TOOL_NAME,
                                        "description": (
                                            "Report a pronunciation coaching attempt so "
                                            "the app can store it for later practice."
                                        ),
                                        # Sonic 은 이 값을 **문자열**로 받는다.
                                        "inputSchema": {
                                            "json": PRONUNCIATION_TOOL_SCHEMA_JSON
                                        },
                                    }
                                }
                            ]
                        },
                    }
                }
            },
```

**(b) `toolUse`를 이벤트로 바꾼다** — 기존 디스패치(`:138-150`)에 분기 하나를 더한다:

```python
        if name == "toolUse":
            return self._on_tool_use(body)
```

그리고 핸들러:

```python
    def _on_tool_use(self, body: dict[str, Any]) -> PronunciationEvent | None:
        """발음 tool 을 이벤트로 바꾼다. **예외를 던지지 않는다** — 발음 기록 실패가
        대화를 끊으면 안 된다(설계서 Contract).
        """
        if body.get("toolName") != PRONUNCIATION_TOOL_NAME:
            logger.debug("모르는 tool %r 을 무시했다", body.get("toolName"))
            return None
        report = parse_tool_payload(body.get("content") or "")
        if report is None:
            return None  # parse_tool_payload 가 이미 경고를 남겼다
        return PronunciationEvent(
            target_form=report.target_form,
            outcome=report.outcome,
            spoken_form=report.spoken_form,
            target_sound=report.target_sound,
        )
```

⚠️ `contentStart(type=TOOL)`에서 `generationStage`를 이어 붙이는 기존 상태 기계가 `TOOL` 타입에 혼동되지 않는지 확인한다. `TOOL`은 텍스트가 아니므로 `stage` 딕셔너리에 들어가도 무해하지만, `contentEnd(stopReason=TOOL_USE)`가 ASSISTANT 텍스트 확정 승격 로직(`completionEnd`)을 건드리지 않아야 한다.

**(c) `SYSTEM_PROMPT`에 발음 규칙을 넣는다** (`nova.py:77`). 스파이크에서 실효를 본 문구를 기준으로 한다:

```
Pronunciation coaching:
- You hear the learner's actual audio. The transcript does not show pronunciation
  errors, so you are the only one who can notice them.
- When a sound is clearly off, name the sound, then say the whole sentence back with
  correct pronunciation, then ask the learner to repeat it.
- Call report_pronunciation_coaching twice: once with outcome "pending" when you have
  modeled the sentence, and again with correct/incorrect/unclear after you hear the
  learner repeat it.
- This counts against the one-or-two corrections per turn limit in rule 4. Do not add
  a pronunciation correction on top of two grammar corrections.
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/unit/test_nova.py -v && .venv/bin/pytest -q
```
Expected: 신규 5건 passed, 전체 `269 passed`

- [ ] **Step 5: 스텁 무손상을 확인한다 (PS8 — 이 태스크의 회귀 위험)**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/integration/test_gateway.py ../../tests/integration/test_ws.py -v
```
Expected: 전부 passed. 스텁은 `toolUse`를 만들지 않으므로 발음 이벤트가 0이어야 한다.

- [ ] **Step 6: 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
git add app/backend/app/audio_gateway/nova.py tests/unit/test_nova.py
git commit -m "feat: Nova 어댑터에 발음 tool 연결 (toolConfiguration + toolUse 변환)"
```

---

## Task 6: 세션 통합 — 이벤트 분기 · 종료 수렴 · 한글 전사 신호  —  ✅ 완료 `0025301` — 정정 2·3·4·5 적용

**Files:**
- Modify: `app/backend/app/audio_gateway/session.py` — `_pump_adapter_events`(`:202`), `_close_and_record`(`:135`), `_save_final`(`:234`)
- Test: `tests/integration/test_gateway.py` (기존 파일에 추가)

**Interfaces:**
- Consumes: Task 3 `PronunciationEvent`, Task 4 `record_attempt`/`resolve_dangling`
- Produces: 클라이언트로 나가는 새 프레임 `{"type": "pronunciation", "outcome": ..., "target_form": ..., "target_sound": ...}`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
KOREAN_SYLLABLES = "아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈"


async def test_pronunciation_event_is_stored_and_broadcast(...) -> None:
    """PS1 — tool 전송 경로가 관통한다."""
    # 가짜 어댑터가 PronunciationEvent 를 흘리게 하고, 세션을 돌린 뒤:
    #   ① pronunciation_attempts 1행 (outcome='pending')
    #   ② 클라이언트 프레임에 {"type": "pronunciation", ...} 1건
    ...


async def test_pending_converges_when_session_ends(...) -> None:
    """PS4 — pending 이 남지 않는다."""
    # pending 만 흘리고 세션을 정상 종료시킨 뒤:
    #   outcome='unclear', pending 행 0개
    ...


async def test_korean_transcript_records_an_assist_signal(...) -> None:
    """PS5 — 한글 전사문이 신호로 기록되고 파이프라인이 죽지 않는다."""
    # 확정 USER 전사문이 KOREAN_SYLLABLES 일 때:
    #   signal_source='korean_transcript', outcome='unclear' 인 행 1개
    #   그리고 utterances 저장과 분석 job 등록은 그대로 일어난다
    ...


async def test_ascii_transcript_records_no_signal(...) -> None:
    """정상 영어 전사문에는 신호가 붙지 않는다 — 오탐 방지."""
    ...


async def test_stub_mode_produces_no_pronunciation_rows(...) -> None:
    """PS8 — 스텁 무손상."""
    ...
```

기존 `test_gateway.py`의 가짜 어댑터·세션 구동 헬퍼를 그대로 재사용한다. 이름은 파일을 열어 확인한다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest -c pyproject.toml ../../tests/integration/test_gateway.py -k "pronunciation or korean" -v
```
Expected: FAIL — 행이 만들어지지 않는다

- [ ] **Step 3: 구현한다**

**(a) 한글 감지** — `session.py` 상단에 상수와 함수를 둔다:

```python
# 한글 음절 블록. ASR 언어 판별이 뒤집히면 영어 문장이 이렇게 전사된다 —
# 4차수 P4 실측(`p1k` → '아이싱크 아이파운드 …'). 결정론적 신호다(R10-4 ①).
_HANGUL = re.compile(r"[가-힣]")


def has_hangul(text: str) -> bool:
    return _HANGUL.search(text) is not None
```

**(b) 이벤트 분기** — `_pump_adapter_events`의 `isinstance` 체인에 추가한다. `InterruptionEvent` 분기 **뒤**, `event.kind` 검사 **앞**에 둔다:

```python
            elif isinstance(event, PronunciationEvent):
                await self._record_pronunciation(event)
```

그리고 메서드:

```python
    async def _record_pronunciation(self, event: PronunciationEvent) -> None:
        """발음 시도를 저장하고 화면에 알린다.

        **예외를 세션 밖으로 던지지 않는다** — 발음 기록 실패가 대화를 끊으면 안 된다.
        """
        try:
            async with self._pool.acquire() as conn:
                await record_attempt(
                    conn,
                    self._session_id,
                    target_form=event.target_form,
                    outcome=event.outcome,
                    spoken_form=event.spoken_form,
                    target_sound=event.target_sound,
                )
        except Exception:  # noqa: BLE001 — 대화를 끊는 것보다 기록을 잃는 편이 낫다
            logger.exception("발음 시도 저장에 실패했다 (세션 %s)", self._session_id)
        await self._send(
            {
                "type": "pronunciation",
                "outcome": event.outcome,
                "target_form": event.target_form,
                "target_sound": event.target_sound,
            }
        )
```

**(c) 보조 신호** — `_save_final`에서 저장 직후, 사용자 발화일 때만:

```python
        if event.speaker == "user" and has_hangul(utterance.transcript):
            # Nova 가 발음 개입을 놓쳤을 수 있다. 다음 세션 계획이 볼 수 있게 남긴다(R10-4).
            try:
                async with self._pool.acquire() as conn:
                    await record_attempt(
                        conn,
                        self._session_id,
                        target_form="(전사문이 한국어로 인식되었습니다)",
                        outcome="unclear",
                        spoken_form=utterance.transcript,
                        utterance_id=utterance.id,
                        signal_source="korean_transcript",
                    )
            except Exception:  # noqa: BLE001
                logger.exception("한글 전사 신호 기록에 실패했다")
```

**(d) 종료 수렴** — `_close_and_record`에서 세션 상태를 기록하는 트랜잭션에 붙인다:

```python
            await resolve_dangling(conn, self._session_id)
```

⚠️ **세션 종료 기록과 같은 트랜잭션**에 둔다. 분리하면 그 사이 크래시에서 `pending`이 영구히 남는다.

- [ ] **Step 4: 통과 확인 + 스텁 회귀**

```bash
cd app/backend && .venv/bin/pytest -q
```
Expected: `274 passed`. **`test_gateway.py`·`test_ws.py`의 기존 케이스가 하나도 깨지지 않아야 한다.**

- [ ] **Step 5: 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
git add app/backend/app/audio_gateway/session.py tests/integration/test_gateway.py
git commit -m "feat: 세션에 발음 시도 기록·수렴·한글 전사 신호 연결"
```

---

## Task 7: 패턴 연결 — `error_patterns` upsert

**Files:**
- Modify: `app/backend/app/services/pronunciation.py`
- Test: `tests/integration/test_pronunciation_service.py`

**Interfaces:**
- Produces: `async def link_pattern(conn, user_id: UUID, attempt_id: UUID, *, target_sound: str) -> UUID | None` — `pronunciation_intonation` 패턴을 upsert하고 `attempt.pattern_id`를 채운다.

> ⚠️ **정정 (2026-08-28)** — 설계서 §3.2가 **경로 불문**을 요구한다: `outcome='incorrect'`가
> 되는 순간 패턴을 만든다. 즉 판정 경로(`record_attempt`)뿐 아니라 **종료 수렴
> (`resolve_dangling`)으로 `incorrect`가 된 행도 포함**이다. 경로에 따라 다르게 처리하면
> "대답 안 함"만 따로 세는 예외가 생기고 그것이 결과 화면·학습 계획으로 번진다.
> 착수 전 `handoff/HANDOFF-v1.1-implementation.md` §6 "내 작업"의 트랜잭션 항목도 읽어라 —
> `record_attempt`가 자기 트랜잭션을 열어야 부분 실행이 막힌다.

- [ ] **Step 1~2: 실패하는 테스트**

핵심 단정 4개:
1. `outcome='incorrect'` + `target_sound` 있음 → `error_patterns`에 `category='pronunciation_intonation'`, `pattern_key='pronunciation_th_as_s'` 행 1개, `attempt.pattern_id` 연결
2. 같은 `target_sound`가 두 번 → 패턴은 **1개**, `frequency`가 2 (`unique(user_id, pattern_key)` 재사용)
3. `target_sound`가 없으면 패턴을 만들지 않고 시도만 남는다
4. `outcome='correct'`면 패턴을 만들지 않는다

⚠️ **`frequency`는 델타로 단정한다** — 공유 dev DB에서 절대값 단정은 반드시 실패한다(하네스 함정 H-4).

- [ ] **Step 3: 구현**

```python
async def link_pattern(
    conn: asyncpg.Connection, user_id: UUID, attempt_id: UUID, *, target_sound: str
) -> UUID | None:
    """발음 오류를 재사용 가능한 패턴으로 만든다 (R10-6 → R11-9).

    **임계값을 두지 않는다** — `incorrect` 1회에 만든다. 문법 오류도 1회에 패턴이
    생기므로 같은 규약이다(`PRD.md:90`).

    `frequency` 는 occurrence 수가 아니라 **시도 수**로 센다 — 발음 시도는
    `error_occurrences` 를 만들지 않기 때문이다(설계서 §4.3, 스키마 문서 :137 참조).
    """
    pattern_key = f"pronunciation_{target_sound}"
    pattern_id = await conn.fetchval(
        """
        insert into error_patterns (user_id, category, pattern_key, frequency, last_seen_at)
        values ($1, 'pronunciation_intonation', $2, 1, clock_timestamp())
        on conflict (user_id, pattern_key) do update
            set frequency    = error_patterns.frequency + 1,
                last_seen_at = clock_timestamp()
        returning id
        """,
        user_id,
        pattern_key,
    )
    await conn.execute(
        "update pronunciation_attempts set pattern_id = $2 where id = $1",
        attempt_id,
        pattern_id,
    )
    return pattern_id
```

`record_attempt`가 `outcome='incorrect'`이고 `target_sound`가 있을 때 이것을 **같은 트랜잭션에서** 부른다. `user_id`는 `learning_sessions`에서 조인해 얻는다.

- [ ] **Step 4~5: 통과 확인 · 게이트 · 커밋**

```bash
git commit -m "feat: 발음 오류를 error_patterns 패턴으로 연결"
```

---

## Task 8: 결과 화면 — 발음 카드

**Files:**
- Modify: `app/backend/app/services/results.py`, `app/backend/app/api/results.py`
- Modify: `app/frontend/` — 결과 화면 컴포넌트 + 세션 화면 발음 배지
- Test: `tests/unit/test_results.py`, `tests/integration/test_pipeline.py`

**Interfaces:**
- Produces: 결과 응답에 `pronunciation: [{target_form, target_sound, outcome}]` 배열 추가

> ⚠️ **정정 (2026-08-28)** — 응답에 **`signal_source`도 실어야 한다.** 신호 행
> (`korean_transcript`)의 `target_form`은 Nova가 시범한 문장이 아니라 설명 문구
> (`"(전사문이 한국어로 인식되었습니다)"`)라서, 구분 없이 렌더하면 학습자에게 그 문구가
> "이렇게 발음해야 합니다"로 보인다. 그리고 `outcome='incorrect'`인데 `spoken_form`이
> null인 행은 **대답 없이 끝난 시도**다 — "들린 발음" 자리를 비워 두거나 "대답 없음"으로
> 렌더한다. `pending`은 여전히 결과에 포함하지 않는다(종료 수렴이 이미 처리했으므로
> 정상 종료한 세션에는 `pending`이 남지 않는다).

- [ ] **Step 1~2: 실패하는 테스트**

핵심 단정 3개 (PS9):
1. 발음 시도가 있는 세션의 결과에 `pronunciation` 배열이 채워진다
2. 발음 시도가 있으면 프론트가 **"표시할 교정이 없습니다."를 쓰지 않는다**
3. `pending`은 결과에 **포함하지 않는다** — 미판정을 학습자에게 보이지 않는다

- [ ] **Step 3: 구현**

백엔드: `results.py`의 5분기 우선순위(R2)를 **바꾸지 않는다.** 발음 배열은 그 판정과 독립적으로 실린다 — 판정 로직을 건드리면 기존 B1~B4 검증이 흔들린다.

프론트: `docs/storyboard.html` 03b의 배지·발음 카드 시각 규약을 따른다. 새 색 토큰을 만들지 않고 기존 테마 토큰만 쓴다 — **1차수 F-1(하드코딩 색으로 다크모드 위계가 역전됨)의 재발을 막는다.**

- [ ] **Step 4: 종단 확인**

```bash
app/backend/.venv/bin/python scripts/migrate.py          # dev DB 에 003 적용
cd app/backend && .venv/bin/uvicorn app.api.main:app --port 8002 --log-level warning &
cd app/frontend && npx tsc --noEmit
```

- [ ] **Step 5: 게이트 + 커밋**

```bash
git commit -m "feat: 결과 화면에 발음 카드 (PS9)"
```

---

## Task 9: 하네스 5차수에 P계층 시나리오 추가

**Files:**
- Modify: `tests/harness/scenarios-P-pronunciation.md` — P9~P12 신설

**Interfaces:** 없음 (문서)

- [ ] **Step 1: 시나리오를 쓴다**

| # | 단정 |
|---|---|
| **P9** | 실음성 발음 세션 1회 — `p1m` 주입 시 `pronunciation_attempts` 행이 생기고 화면에 배지가 뜬다 |
| **P10** | `pending` 수렴 — 재발화 없이 세션 종료 시 `pending` 0개 |
| **P11** | 한글 전사 신호 — `p1k` 주입 시 `signal_source='korean_transcript'` 행 1개, 분석 job은 `done` |
| **P12** | 스텁 무손상 — `VOICE_ADAPTER=stub`에서 발음 행 0개, 배지 미표시 |

**증거 규약**: agent 발화와 판정을 `runs/<차수>/`에 **덤프한다.** 4차수가 M계층 판정 근거를 남기지 않아 재검증 불가가 된 것을 반복하지 않는다.

- [ ] **Step 2: 커밋**

```bash
git commit -m "test: 5차수 P계층 시나리오 P9~P12 (발음 루틴 검증)"
```

---

## Self-Review

**1. Spec coverage** — 설계서 요구사항 → 태스크 매핑

| 요구사항 | 태스크 |
|---|---|
| R10-1 올바른 발음으로 문장 재현 | 5 (SYSTEM_PROMPT) |
| R10-2 재발화 결과 기록 | 1·2·4·5·6 |
| R10-3 판정 주체 = 실시간 음성 모델 | 5 (전사문 경로를 쓰지 않는다) |
| R10-4 보조 신호 2개 | 6 (`korean_transcript`) · **`agent_reprompt`는 미구현 — §미결 2에서 "기록 전용"으로 남겼고 값이 불확실하다. Task 6에서 신호 하나만 구현하고 나머지는 5차수 관측 후 결정한다** |
| R10-5 교정 예산 | 5 (프롬프트) — **코드 강제 없음**(설계서 D5-1이 이미 약점으로 명시) |
| R10-6 패턴으로 저장 | 7 |
| R10-7 오디오 미저장 | 전 태스크 — 오디오를 쓰는 코드가 없다 |
| R10-8 교정 상한 유지 | 5 (프롬프트) |
| AC10-1~5 | PS2·PS3·PS5·PS10·Task 8 |
| PS1~PS10 | 1~8 |

**갭 1건 발견 → 명시**: `agent_reprompt` 신호는 이 계획에서 **구현하지 않는다.** 설계서 §9 미결 2가 "문구 매칭이라 취약, 기본안은 기록 전용"이라 했고, 문구 매칭 규칙을 지금 발명하면 Nova 문구가 바뀔 때 조용히 깨진다. `korean_transcript`만으로 시작하고 5차수 관측으로 필요를 판정한다. **요구사항 R10-4의 절반이 미충족 상태로 남는다는 것을 Task 6에 적어 둔다.**

**2. Placeholder scan** — Task 6·8의 테스트 본문에 `...`가 있다. 이것은 **의도된 것**이다: 기존 `test_gateway.py`·`test_results.py`의 가짜 어댑터·세션 구동 헬퍼 이름을 내가 확인하지 않았고, 추측한 이름을 적으면 실행자가 없는 헬퍼를 찾게 된다. 각 자리에 **단정 내용은 전부 명시**했고 "파일을 열어 헬퍼 이름을 확인하고 재사용한다"를 지시로 남겼다.

**3. Type consistency** — `PronunciationOutcome`·`SignalSource`는 Task 2에서 정의하고 3·4·6이 그대로 쓴다. `record_attempt`의 인자 이름(`target_form`/`spoken_form`/`target_sound`/`utterance_id`/`signal_source`)이 Task 4 정의와 6·7 호출부에서 일치한다. `PRONUNCIATION_TOOL_NAME`은 Task 2가 소유하고 5가 import한다 — 문자열을 두 번 적지 않는다.

---

## 다음 계획 (이 계획의 범위 밖)

**학습 코치 슬라이스 1** — `2026-08-25-learning-coach-agent-design.md` §12.1. 별도 계획으로 쓴다: `suggested_contexts` 저장, `pattern_attempts`, 복습 스케줄 갱신(§4.1), 만성 지표 쿼리(§6.1). 이 계획과 독립이고(접합면이 `error_patterns` 한 행) 병행 가능하다. 설계서의 권고 순서는 **슬라이스1 → 발음 기록 → 슬라이스2**이지만, 발음 쪽이 요구사항 신설분이라 먼저 착수한다.
