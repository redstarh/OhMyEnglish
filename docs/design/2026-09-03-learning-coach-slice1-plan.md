# 학습 코치 슬라이스 1 구현 계획 — 기록과 계산

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended)
> or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax
> for tracking.

**Goal:** 지금 산출되고도 버려지는 학습 데이터를 저장하기 시작하고, 아무도 쓰지 않는 `next_review_at`에
값이 들어가게 해서 "오늘 복습할 목록"이 처음으로 0행이 아니게 만든다.

**Architecture:** 새 인프라를 만들지 않는다. 이미 도는 분석 job(`analyze_utterance`)의 **결과 저장
트랜잭션 안에** 세 가지를 얹는다 — ① `suggested_contexts` 저장 ② `pattern_attempts`(재발화 정답 여부)
기록 ③ 그 두 이력에서 **복습 상태를 다시 계산**해 `error_patterns.next_review_at`·`mastery_score`와
`review_tasks` 1행에 반영. 여기에 읽기 전용 만성 지표 쿼리 1개를 더한다. 화면은 바뀌지 않는다.

**Tech Stack:** Python 3.13 · asyncpg · pydantic v2 · PostgreSQL 17.9 · pytest(asyncio_mode=auto) ·
ruff · ty. 프론트엔드는 **건드리지 않는다**.

**Spec:** `docs/design/2026-08-25-learning-coach-agent-design.md` (정본, 2026-08-27 승격) —
슬라이스 1의 범위는 그 문서 **§12.1 결정 표의 1행**이다: `suggested_contexts` 저장 · `pattern_attempts` ·
복습 스케줄 갱신(§4.1) · 만성 지표 쿼리(§6.1). 관련 AC는 §10의 **AS9**(연습 상황 저장)와
**AS10**(정답 기록 멱등성), 그리고 §4.1이 요구하는 "복습 목록이 값을 갖는다".

---

## 구현 전 정정 — 착수 전에 이 표를 먼저 읽는다 (함정 H-N)

설계서를 그대로 믿고 구현하면 깨지는 자리들이다. **전부 2026-09-03에 직접 실행해 확인했다.**

| 설계서/문서의 서술 | 실측 | 이 계획이 쓰는 것 |
|---|---|---|
| §8.4 "`002_learning_coach.sql`로 쌓는다" | `002`는 **만들어진 적이 없다** — 파일 0건, `git log --diff-filter=A -- 'db/migrations/002*'` 0건. `schema_migrations`에 적용된 것은 `001`·`003`·`004`·`005` 4건 | **`006_learning_coach_slice1.sql`** |
| §8.2가 전제하는 `error_occurrences.suggested_contexts` | `information_schema.columns`에 **없다**. 마이그레이션 참조도 0건 | 006이 **신설**한다 |
| `impact_score` | 컬럼 없음. §11 미결 3에서 **영구 제외** 확정 | **만들지 않는다** |
| §4.1 "재발하면 복습 단계를 되돌린다" — stage 2·3 행 처리는 미정 | `review_tasks`는 `unique(pattern_id, review_stage)`이고 `scenario_context`가 `not null`이라 그대로는 구현 불가 | **캡틴 결정 2026-09-03: 삭제하고 현재 단계 1행만 남긴다.** 완주 이력은 `pattern_attempts`·`error_occurrences`에 남아 재구성 가능하다 |
| `mastery_score` 공식 | 문서에 없다. §3.2는 임계값 발명을 금지한다 | **캡틴 결정 2026-09-03: 상태 마커만** — 3단계 완주 `100`, 재발 `0`. 중간값을 만들지 않는다 |
| handoff 표의 표 이름 `sessions`·`error_pattern_occurrences` | 실제 표는 **`learning_sessions`·`error_occurrences`** | 실제 이름을 쓴다 |
| jsonb 바인딩 관례 | 코드에 선례가 없다(`learning_sessions.summary`는 앱이 쓰지 않는다). 직접 확인: asyncpg는 jsonb에 **`str`만** 받고 파이썬 `list`는 `DataError: expected str, got list`로 거부한다. 읽을 때도 `str`로 돌아온다 | 쓸 때 `json.dumps(..., ensure_ascii=False)`, 읽을 때 `json.loads`. 한글은 그대로 보존된다(확인) |

---

## Global Constraints

모든 태스크의 요구사항에 아래가 암묵적으로 포함된다.

- **게이트는 `app/backend` cwd에서만 판정한다** (함정 H-A). 기준선(2026-09-03 실측):
  `pytest -q` **389 passed** · `ruff check .` + `ruff format --check .` **27 files** · `ty check` **All checks passed**.
  `tests/**`의 `ruff` **6 errors**·`format` **4 files**는 게이트 밖 베이스라인이다.
- **게이트를 `| tail`로 파이프하지 않는다** — exit code가 `tail`의 것이 되어 실패가 `&&`를 통과한다.
- **테스트 DB는 공유 자원이다**(함정 H-X) — 게이트를 겹쳐 돌리지 않는다. 매 실행이 `ohmyenglish_test`를
  DROP/CREATE한다.
- **시각은 전부 `timestamptz`. naive datetime을 만들지 않는다.** 복습 간격은 `interval` 연산이라
  타임존 무관이지만, **달력 날짜**(만성 지표의 "재발 일수")는 `current_date`로 구하지 않고
  `at time zone <users.timezone>`으로 변환한다 (함정 **H-S** — UTC 자정~09:00 KST 구간에 하루 어긋난다).
  타임존의 SoT는 **`users.timezone` 컬럼**이다(기본 `Asia/Seoul`). `ALTER DATABASE ... SET TimeZone` 금지 —
  En-Coach와 공유하는 인스턴스다.
- **증분 금지, 재계산.** 이 리포의 확립된 규약이다 — `frequency`는 `+1`하지 않고 `error_occurrences`
  행 수에서 다시 세고, `last_seen_at`은 `now()`가 아니라 발화 시각의 `max()`다
  (`app/backend/app/services/analysis.py` 모듈 docstring). **복습 상태도 같은 규약을 따른다**:
  단계를 `+1`하지 않고 이력에서 다시 센다. 이유는 같다 — job은 재시도되고, 증분은 재시도마다 밀린다.
- **임계값을 발명하지 않는다** (설계서 §3.2). 이 계획이 쓰는 수치는 전부 문서 근거가 있다:
  복습 **1·3·7일 3단계**(`database-schema.md`·설계서 §4.1) · 연습 상황 **3개**(`docs/PRD.md:92`
  "같은 패턴을 최소 세 개의 다른 상황에서 재사용한다" · `docs/agent-system-prompt.md:47`
  "suggested_contexts: three different contexts"). 그 밖의 수치를 새로 만들지 않는다.
- **프롬프트 문구는 h-doc 프로필을 따른다**: 단문·단일 절 기준, 일상 → 업무 협업 순서, 학습자용
  설명은 한국어. 목표 수준(AWS 보고) 문형으로 예문을 만들지 않는다.
- **슬라이스 1은 화면을 바꾸지 않는다.** `app/frontend/**` 수정 파일 수는 **0**이어야 한다.
- **커밋은 conventional commits.** `feat:`/`fix:`에는 `[skip ci]`를 붙이지 않는다.
- **원장과 handoff는 커밋과 같은 리듬으로 갱신한다** — 태스크 완료마다 `TASKS.md` C절의 상태와
  `handoff/HANDOFF.md`의 "다음 한 걸음"을 함께 고친다.
- ⚠️ **`scripts/migrate.py`를 실물 dev DB에 돌리는 것은 캡틴 승인 후에 한다.** 스키마 마이그레이션
  적용은 되돌리기 어려운 조작이다. 테스트 DB(`ohmyenglish_test`)는 매 실행마다 재생성되므로 승인 대상이 아니다.

---

## File Structure

| 파일 | 신규/수정 | 책임 |
|---|:--:|---|
| `db/migrations/006_learning_coach_slice1.sql` | 신규 | `error_occurrences.suggested_contexts` 컬럼 1개 + `pattern_attempts` 표 1개. **그것만** — `session_plans`·`learner_notes`·`job_type` CHECK 확장은 슬라이스 2다 |
| `app/backend/app/models/analysis.py` | 수정 | Claude 출력 계약 확장 — `ErrorFinding.suggested_contexts`, 새 `PatternAttempt`와 `AnalysisResult.attempts` |
| `app/backend/app/services/analysis.py` | 수정 | 프롬프트에 두 절 추가 · occurrence insert에 컬럼 1개 · 결과 저장 트랜잭션에서 attempts 저장과 복습 재계산 호출 |
| `app/backend/app/services/review.py` | 신규 | **복습 상태의 소유자** — 이력에서 단계를 다시 계산해 `error_patterns`(`next_review_at`·`mastery_score`)와 `review_tasks` 1행에 반영. `pattern_attempts` 저장도 여기 |
| `app/backend/app/services/chronic.py` | 신규 | 만성 지표 조회(§6.1) — **읽기 전용**. 쓰기 함수를 두지 않는다 |
| `tests/unit/test_schema.py` | 수정 | 006 스키마 단정 (표 목록·컬럼·CHECK·unique·cascade) |
| `tests/unit/test_analysis.py` | 수정 | 프롬프트 문구 · 출력 계약 파싱 단정 |
| `tests/unit/test_review.py` | 신규 | 복습 재계산 상태 함수의 단위 테스트 (경계값·멱등) |
| `tests/unit/test_chronic.py` | 신규 | 만성 지표 — 음수 span 금지·최대 공백·타임존 경계 |
| `tests/integration/test_pipeline.py` | 수정 | 분석 파이프라인 종단: 저장된 `suggested_contexts`·`pattern_attempts`·복습 상태 |
| `docs/database-schema.md` | 수정 | 006이 만든 표·컬럼 정의 반영 |
| `docs/design/2026-08-25-learning-coach-agent-design.md` | 수정 | §8.4 번호 정정, AS9 상태 갱신, 캡틴 결정 2건 기록 |

**새 워커·새 큐·새 job_type을 만들지 않는다.** 슬라이스 1의 모든 쓰기는 이미 존재하는
`analyze_utterance` job의 결과 저장 트랜잭션 안에서 일어난다.

---

## 복습 상태 재계산 — 이 계획의 핵심 계약

구현자가 여기서 가장 많이 실수한다. **읽고 시작한다.**

### 왜 증분이 아니라 재계산인가

`analyze_utterance` job은 재시도된다(상한 5). 같은 발화가 두 번 분석되면 결과 저장은
**발화 단위 replace**로 같은 집합을 다시 쓴다 — 그래서 멱등이다. 복습 단계를 `stage = stage + 1`로
전이시키면 이 재실행에서 단계가 두 번 올라가 학습자가 하지 않은 복습을 완주한 것이 된다.
그래서 단계도 **이력에서 다시 센다**. `frequency`를 `+1`하지 않는 것과 정확히 같은 이유다.

### 상태 함수 — 패턴 P 하나의 복습 상태

**핵심: 정답 횟수를 세는 것이 아니라 예정일을 하나씩 접는다.** 설계서 §4.1은 "**복습을 완주하면**
다음 단계로 진행한다: 1일 → 3일 → 7일"이고, 복습 목록의 판정은 `next_review_at <= clock_timestamp()`다.
즉 한 단계를 통과한다는 것은 **그 단계의 예정일이 온 뒤에** 다시 맞혔다는 뜻이다. 단순히 correct를
3번 세면 학습자가 **같은 세션에서 3번 맞히는 것으로 1·3·7일을 한 번도 경과하지 않고 완주**해
간격 반복 자체가 무의미해진다 (이 결함은 2026-09-03 계획 검토에서 잡혔고, 실제로 재현했다).

먼저 두 가지 사실만 읽는다. 둘 다 이력이라 재실행해도 변하지 않는다.

| 사실 | 정의 |
|---|---|
| `relapse_at` | P가 **마지막으로 틀린 시각** = P의 `error_occurrences`가 달린 발화의 `created_at`과, P의 `pattern_attempts(outcome='incorrect')`가 달린 발화의 `created_at`을 합친 집합의 `max()` |
| `correct_times` | `relapse_at` **이후**에 달린 P의 `pattern_attempts(outcome='correct')`의 발화 시각 — **오름차순 배열** |

그리고 이 목록을 접는다 (`fold_stages`, 순수 함수 — DB를 보지 않는다):

```text
relapse_at 이 없으면  → stage 1 · 미완주 · anchor 없음 · next_review_at 없음
                        (틀린 적이 없는 패턴은 복습할 것이 없다)

anchor := relapse_at ; stage := 1        # stage 는 **1-based** (1·2·3)
correct_times 를 순서대로 훑으며:
    due := anchor + STAGE_DAYS[stage - 1]  # ← 파이썬 인덱스는 0-based 다
    said_at < due   → **건너뛴다** (예정일 전의 정답 — 간격이 경과하지 않았다)
    said_at >= due  → anchor := said_at ; stage := stage + 1
                      stage > 3 이면 → 완주 (next_review_at 없음)

끝까지 완주하지 않았으면 → next_review_at := anchor + STAGE_DAYS[stage - 1]
```

`STAGE_DAYS = (1, 3, 7)`이고 **문서로 확정된 값**이다(설계서 §4.1 · `database-schema.md`) — 발명이 아니다.
완주까지 실제로 경과해야 하는 시간은 **최소 1 + 3 + 7 = 11일**이다.

| 결과 | `next_review_at` | `mastery_score` | `review_tasks` |
|---|---|:--:|---|
| 완주 (3단계를 예정일마다 통과) | `null` | `100` | `review_stage=3`, `status='done'`, `due_at=anchor` 1행 |
| 미완주이고 `relapse_at` 있음 | `anchor + STAGE_DAYS[stage - 1]` | `0` | `review_stage=stage`, `status='pending'`, `due_at=next_review_at` 1행 |
| `relapse_at` 없음 (틀린 적 없음) | `null` | `0` | 0행 |

- `anchor`는 항상 **발화 시각**이다. `now()`를 쓰지 않는다 — 재실행마다 예정일이 밀리면 멱등이 깨진다
- 예정일 **전**의 정답도 `pattern_attempts`에는 그대로 남는다. 단계만 올리지 않는다 — 기록을 버리는 것이
  아니라 간격 조건을 지키는 것이다
- **`review_tasks`는 항상 0행 또는 1행이다.** 재계산은 P의 행을 전부 `delete`한 뒤 위 1행을
  `insert`한다 — 캡틴 결정(2026-09-03)이고, `unique(pattern_id, review_stage)`와 정면으로 맞는
  유일한 형태다. 지운 이력이 손실이 아닌 근거: 완주 여부는 `pattern_attempts`에서, 재발 여부는
  `error_occurrences`에서 언제든 다시 계산된다
- `task_type='rephrase'` · `scenario_context` = P의 **최신 occurrence의 `original_span`**,
  없으면 `error_patterns.target_form`. 둘 다 실제 데이터이고 생성물이 아니다 —
  슬라이스 1은 무엇도 생성하지 않는다(§3.2의 경계). 슬라이스 2가 `suggested_contexts`로 이 자리를 대체한다
- `status='skipped'`는 이 슬라이스가 쓰지 않는다(CHECK 값역에는 남는다)

⚠️ **왜 SQL 한 방이 아니라 파이썬 fold인가.** 접기는 각 단계의 통과 시각이 다음 단계의 기준이 되는
**연쇄**라서 집계 함수로 표현되지 않는다(재귀 CTE가 필요하다). 목록은 "마지막 재발 이후의 정답"뿐이라
항상 작고, 순수 함수로 떼어내면 DB 없이 경계값을 다 검증할 수 있다. 재계산이라는 성질은 그대로다 —
매번 이력 전체를 다시 접는다.

### `mastery_score`가 정보를 잃지 않는 이유

재발하면 `100 → 0`으로 되돌아가므로 "한때 완주했다"가 그 컬럼에서는 사라진다. 그래도 잃는 것이
없다 — `pattern_attempts`의 correct 행과 `error_occurrences` 행이 **둘 다 남아** 있어
"3단계를 소진한 뒤 재발했다"(§6.2의 결정론적 만성 신호)를 언제든 재계산할 수 있다.
그 신호를 **계산해 Claude에 넘기는 것은 슬라이스 2**다 — §12.1이 슬라이스 1에 배정한 것은 §6.1뿐이다.

### 언제 재계산이 도는가

`services/analysis.py`의 결과 저장 트랜잭션 안, **`pattern_attempts` 저장 다음**이다
(설계서 §9 Dependency: "정답 여부가 먼저 기록되고 그 다음 갱신이다. 같은 분석 트랜잭션 안에서 처리한다").
대상은 그 발화가 건드린 패턴 전부 — 지워진 occurrence의 패턴 + 새로 저장한 패턴 + **attempts가
가리킨 패턴**이다. 마지막 항목을 빠뜨리면 occurrence 없이 correct만 온 발화에서 단계가 오르지 않는다.

### 실측으로 확인한 SQL 의미 4건 (추측하지 말고 이 값을 신뢰한다)

2026-09-03에 PostgreSQL 17.9에서 직접 실행했다.

| 확인한 것 | 결과 |
|---|---|
| `greatest(null::timestamptz, ts)` | **NULL을 건너뛰고** `ts`를 돌려준다 (Postgres 의미론). 인자가 전부 null이면 NULL |
| `(array[1,3,7])[least(n + 1, 3)] * interval '1 day'` | 정상. `n=1` → `+3일`, `n=2` → `+7일` |
| `null::timestamptz + interval` | 예외가 아니라 **NULL**로 전파된다 — anchor 없는 패턴이 자연히 `next_review_at = null`이 된다 |
| 달력 날짜 세기 | `2026-09-02 08:00+09`와 `2026-09-02 23:30+09` 두 발화를 **UTC로 세면 2일, KST로 세면 1일**. 함정 H-S가 이 한 칸이다 — Task 6 테스트가 이 값을 쓴다 |

### 상태 계산을 실제 표에서 미리 돌린 결과 (2026-09-03, 롤백 트랜잭션)

`_HISTORY_SQL` + `fold_stages`를 **구현 전에** dev DB의 실제 `error_patterns`·`error_occurrences`·
`utterances`와 임시로 만든 `pattern_attempts`에 걸어 확인했다(전부 롤백 — dev DB는 그대로다).
**구현자는 아래를 기대값으로 써도 된다.** `T0 = 2026-09-01 12:00+09`, 재발은 `T0`.

| 이력 | stage | 완주 | anchor | `next_review_at` |
|---|:--:|:--:|---|---|
| 근거 0건 | 1 | false | — | `null` (`scenario_context`는 `target_form`으로 폴백) |
| occurrence 1건 (`T0`) | 1 | false | `09-01` | `09-02` (= `T0+1일`) |
| + correct `T0+1일` (**정확히 예정일**) | 2 | false | `09-02` | `09-05` (+3일) |
| + correct `T0+2일` (**예정일 전**) | 2 | false | `09-02` | `09-05` — **바뀌지 않는다** |
| + correct `T0+4일` (예정일) | 3 | false | `09-05` | `09-12` (+7일) |
| + correct `T0+11일` (예정일) | 3 | **true** | `09-12` | `null` |
| **한 세션 안에서 correct 3건** (`T0`+5·10·15분) | **1** | **false** | `09-01` | `09-02` — 완주하지 않는다 |

마지막 두 줄이 HIGH-1 수정의 핵심 증거다. 예정일 전의 정답은 `next_review_at`을 **전혀 움직이지 않고**,
같은 세션에서 세 번 맞혀도 1단계에 머문다. 완주 경로는 `T0 → +1일 → +4일 → +11일`로 **11일이 실제로
경과**한다.

한 가지 더 확인했다: `error_occurrences`와 `correct` attempt가 **같은 발화(같은 시각)** 에 함께 달리면
`u.created_at > relapse_at`의 strict `>` 때문에 그 정답은 세지 않는다 — 그 순간에는 틀린 것으로 남는다.

---

## Task 1: 006 마이그레이션 — 컬럼 1개 + 표 1개

**Files:**
- Create: `db/migrations/006_learning_coach_slice1.sql`
- Test: `tests/unit/test_schema.py` (기존 파일 끝에 006 절 추가 + 표 목록 단정 1곳 수정)

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `error_occurrences.suggested_contexts jsonb` (nullable) ·
  `pattern_attempts(id, pattern_id, utterance_id, outcome, created_at)` with `unique (pattern_id, utterance_id)` ·
  `outcome in ('correct','incorrect','unclear')`

- [ ] **Step 1: 표 목록 단정에 `pattern_attempts`를 더한다 (실패하는 테스트 ①)**

`tests/unit/test_schema.py`의 `test_001_migration_creates_expected_tables` 집합에 한 줄 추가:

```python
        # 003 — 발음 시범·재발화 (docs/design/2026-08-27-pronunciation-echo-design.md §6)
        "pronunciation_attempts",
        # 006 — 학습 코치 슬라이스 1 (docs/design/2026-08-25-learning-coach-agent-design.md §8.1)
        "pattern_attempts",
    }
```

- [ ] **Step 2: 006 스키마 단정을 쓴다 (실패하는 테스트 ②~⑤)**

`tests/unit/test_schema.py` 끝에 추가한다:

```python
# ── 006 학습 코치 슬라이스 1 (학습 코치 설계서 §8.1·§8.2) ────────────────────────


async def _insert_pattern_and_occurrence(conn: asyncpg.Connection):
    """user → session → utterance → pattern → occurrence 한 벌. 006 테스트의 공통 전제.

    `_insert_user`는 고정 USER_ID를 넣으므로 한 테스트에서 두 번 부르면 PK를 위반한다 —
    이 헬퍼가 한 번만 부르고 나머지를 이어 만든다.
    """
    session_id = uuid4()
    utterance_id = uuid4()
    await _insert_user(conn)
    await _insert_session(conn, session_id)
    await _insert_utterance(conn, utterance_id, session_id)
    pattern_id = await conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'article', 'article_missing_before_place_noun', 'go to the + 장소 명사') "
        "returning id",
        migrate.USER_ID,
    )
    return utterance_id, pattern_id


# ② suggested_contexts — jsonb 이고 nullable 이어야 한다 (설계서 §8.2: 기존 발화에는 없다)
@pytest.mark.asyncio
async def test_error_occurrences_has_nullable_jsonb_suggested_contexts(
    db_conn: asyncpg.Connection,
):
    column = await db_conn.fetchrow(
        "select data_type, is_nullable from information_schema.columns "
        "where table_name = 'error_occurrences' and column_name = 'suggested_contexts'"
    )
    assert column is not None, "suggested_contexts 컬럼이 없다 (006 미적용)"
    assert column["data_type"] == "jsonb"
    # nullable 이어야 소급 불가능한 과거 발화가 저장을 막지 않는다 (§8.2)
    assert column["is_nullable"] == "YES"


# ③ 상황 배열이 그대로 왕복한다 — 개수 CHECK를 두지 않으므로 2개도 통과해야 한다 (§8.2)
@pytest.mark.asyncio
async def test_suggested_contexts_round_trips_without_a_length_constraint(
    db_conn: asyncpg.Connection,
):
    utterance_id, pattern_id = await _insert_pattern_and_occurrence(db_conn)

    stored = await db_conn.fetchval(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, "
        " confidence, suggested_contexts) "
        "values ($1, $2, 'go to gym', 'go to the gym', '정관사가 필요합니다.', 'medium', 0.9, $3) "
        "returning suggested_contexts",
        utterance_id,
        pattern_id,
        json.dumps(["퇴근 후 운동 계획 말하기", "동료에게 오늘 일정 알려주기"], ensure_ascii=False),
    )
    # asyncpg는 jsonb를 str로 돌려준다 (파이썬 list를 바인딩하면 DataError다 — 2026-09-03 실측)
    assert json.loads(stored) == ["퇴근 후 운동 계획 말하기", "동료에게 오늘 일정 알려주기"]


# ④ pattern_attempts — 같은 (pattern, utterance) 두 번은 거부된다 (AS10 멱등의 바닥)
@pytest.mark.asyncio
async def test_pattern_attempts_rejects_a_duplicate_pattern_utterance_pair(
    db_conn: asyncpg.Connection,
):
    utterance_id, pattern_id = await _insert_pattern_and_occurrence(db_conn)
    await db_conn.execute(
        "insert into pattern_attempts (pattern_id, utterance_id, outcome) "
        "values ($1, $2, 'correct')",
        pattern_id,
        utterance_id,
    )

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_conn.execute(
            "insert into pattern_attempts (pattern_id, utterance_id, outcome) "
            "values ($1, $2, 'incorrect')",
            pattern_id,
            utterance_id,
        )


# ⑤ outcome 값역 — 'pending'은 이 표에 없다. 발음 표(pronunciation_attempts)와 다르다:
#    이 표의 행은 재발화 전사문을 이미 본 뒤에 만들어지므로 "대답 기다림" 상태가 없다.
@pytest.mark.asyncio
async def test_pattern_attempts_outcome_check_rejects_pending(db_conn: asyncpg.Connection):
    utterance_id, pattern_id = await _insert_pattern_and_occurrence(db_conn)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into pattern_attempts (pattern_id, utterance_id, outcome) "
            "values ($1, $2, 'pending')",
            pattern_id,
            utterance_id,
        )


# ⑥ 발화가 지워지면 판정도 지워진다 — 이 표의 행은 발화 1건이 유일한 근거라서 cascade다
#    (발음 표는 set null 이다: 그 행은 발화 없이 tool 이벤트만으로도 생긴다)
@pytest.mark.asyncio
async def test_pattern_attempts_cascades_with_the_utterance(db_conn: asyncpg.Connection):
    utterance_id, pattern_id = await _insert_pattern_and_occurrence(db_conn)
    await db_conn.execute(
        "insert into pattern_attempts (pattern_id, utterance_id, outcome) "
        "values ($1, $2, 'correct')",
        pattern_id,
        utterance_id,
    )

    await db_conn.execute("delete from utterances where id = $1", utterance_id)

    assert await db_conn.fetchval("select count(*) from pattern_attempts") == 0
```

`tests/unit/test_schema.py` 머리에 `import json`을 추가한다 (`from __future__` 다음, 표준 라이브러리 블록).

- [ ] **Step 3: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest ../../tests/unit/test_schema.py -q -c pyproject.toml
```

기대: **6건 red.** ①은 집합 불일치(`pattern_attempts`가 없다), ②는 `column is not None` 실패,
③~⑥은 `UndefinedTableError`/`UndefinedColumnError`. ⚠️ **부분 실행에는 `-c pyproject.toml`이 필요하다**
(함정 H-W) — 없으면 pytest가 리포 루트를 설정 파일로 잡아 `asyncio_mode`를 잃는다.

- [ ] **Step 4: 006 마이그레이션을 쓴다**

```sql
-- 006_learning_coach_slice1.sql
-- 학습 코치 슬라이스 1 — 기록과 계산
-- 설계: docs/design/2026-08-25-learning-coach-agent-design.md §8.1·§8.2 (정본)
-- 계획: docs/design/2026-09-03-learning-coach-slice1-plan.md
-- 요구사항: docs/PRD.md §11 · PRD.md:92 "같은 패턴을 최소 세 개의 다른 상황에서 재사용한다"
--
-- 번호: 설계서 §8.4는 002를 예약했지만 002는 **만들어진 적이 없고**(파일·git 이력 각 0건)
-- 003~005가 발음 설계에 쓰였다. migrate.py의 추적이 파일명 기준이라 006으로 쌓는다.
--
-- 여기 **없는 것**: session_plans · learner_notes · analysis_jobs.job_type 에
-- 'plan_next_session' 추가. 셋 다 슬라이스 2(판단과 적용)의 것이다 — 이 슬라이스는
-- 무엇도 생성하지 않고 기록과 계산만 한다(§12.1).

-- §8.2: Claude 분석이 이미 산출할 수 있는 "서로 다른 상황 3개". **지금 저장하지 않으면
-- 소급이 불가능하다** — 이 컬럼 하나가 슬라이스 1을 앞세운 이유다.
-- nullable: 기존 발화에는 없다. 배열 길이 CHECK를 두지 않는다 — 모델이 2개만 낸 것을
-- 실패로 만들면 그 발화의 교정 전체를 잃는다(§8.2).
-- "없음"의 표현은 null 하나다. 앱은 빈 배열을 쓰지 않는다.
alter table error_occurrences add column suggested_contexts jsonb;

-- §8.1: 교정 후 재발화의 정답 여부. **복습 단계 전이의 유일한 신호원**이다 —
-- 이 표가 비면 모든 패턴이 1일 단계에서 영원히 머문다.
--
-- 왜 pronunciation_attempts와 합치지 않는가: 그 표는 발화 없이 tool 이벤트만으로도 행이
-- 생기고 target_form·signal_source·pending 상태를 갖는다(003 주석). 이 표의 행은 전사문을
-- 본 뒤 발화 1건에 붙는다 — 합치면 대부분 null인 표가 된다.
create table pattern_attempts (
  id uuid primary key default gen_random_uuid(),
  pattern_id uuid not null references error_patterns (id) on delete cascade,
  -- 재발화 발화. 이 행의 유일한 근거이므로 발화가 사라지면 판정도 사라진다(cascade).
  utterance_id uuid not null references utterances (id) on delete cascade,
  -- 'unclear'를 둔다 — 판정할 수 없는 발화를 incorrect로 강제하면 숙련도가 부당하게 깎인다(§8.1).
  -- 'pending'은 두지 않는다: 이 판정은 전사문을 이미 본 뒤에 이루어져 대기 상태가 없다.
  outcome text not null check (outcome in ('correct', 'incorrect', 'unclear')),
  created_at timestamptz not null default now(),
  -- AS10: 발화 단위 replace가 재실행돼도 행이 중복되지 않는다.
  -- pattern_id가 선두인 이 인덱스가 복습 상태 재계산의 조회 경로도 겸한다(별도 인덱스 불필요).
  unique (pattern_id, utterance_id)
);
```

- [ ] **Step 5: 통과를 확인한다**

```bash
cd app/backend && .venv/bin/pytest ../../tests/unit/test_schema.py -q -c pyproject.toml
```

기대: 전부 PASS. 테스트 DB는 세션마다 재생성되며 `db/migrations/*.sql`을 순서대로 적용하므로
006은 자동으로 들어간다 — `migrate.py`를 손으로 돌릴 필요가 없다.

- [ ] **Step 6: 전체 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
```
기대: **+5건 → 394 passed**. 신규는 ②~⑥ **5건**이고 ①은 기존 테스트 수정이라 수를 늘리지 않는다.
⚠️ **절대값보다 델타를 신뢰한다** — 다른 작업이 먼저 들어왔으면 기준선(389)이 다르다. 줄어들면 무회귀(T4) 위반이므로 멈춘다.

```bash
git add db/migrations/006_learning_coach_slice1.sql tests/unit/test_schema.py
git commit -m "feat: 006 — suggested_contexts 컬럼과 pattern_attempts 표 (학습 코치 슬라이스 1)"
```

⚠️ 실물 dev DB 적용(`scripts/migrate.py`)은 **여기서 하지 않는다** — 캡틴 승인 후 별도로 한다.

---

## Task 2: `suggested_contexts` — 산출·검증·저장 경로

지금 모델이 낼 수 있는데도 버려지는 데이터를 저장하기 시작한다. **AS9의 절반**(저장)이 여기서 닫힌다.

**Files:**
- Modify: `app/backend/app/models/analysis.py` (`ErrorFinding`에 필드 1개)
- Modify: `app/backend/app/services/analysis.py` (프롬프트 절 1개 · 출력 스켈레톤 · insert 컬럼 1개)
- Test: `tests/unit/test_analysis.py` · `tests/unit/test_claude_schema.py` · `tests/integration/test_pipeline.py`

**Interfaces:**
- Consumes: Task 1의 `error_occurrences.suggested_contexts jsonb`
- Produces: `ErrorFinding.suggested_contexts: list[str]` (기본값 `[]`) — Task 4의 `scenario_context`
  후속 개선과 슬라이스 2의 질문 생성이 이 값을 읽는다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_claude_schema.py`에 추가:

```python
def test_finding_accepts_suggested_contexts_and_strips_each_item():
    result = parse_analysis(
        json.dumps(
            {
                "findings": [
                    default_finding(
                        suggested_contexts=["  퇴근 후 운동 계획 말하기 ", "회의에서 진행 상황 보고"]
                    )
                ]
            }
        )
    )
    assert result.findings[0].suggested_contexts == [
        "퇴근 후 운동 계획 말하기",
        "회의에서 진행 상황 보고",
    ]


def test_finding_defaults_suggested_contexts_to_empty_when_absent():
    """필드가 없는 응답은 계약 위반이 아니다 — §8.2가 nullable로 뒀고, 이 기본값이
    기존 픽스처(conftest.default_finding 8필드)와 하네스 시나리오의 무회귀를 지킨다."""
    result = parse_analysis(json.dumps({"findings": [default_finding()]}))
    assert result.findings[0].suggested_contexts == []


def test_finding_rejects_a_blank_suggested_context():
    """공백만인 '상황'은 연습 재료가 되지 않는다 — 경계에서 거부한다."""
    with pytest.raises(AnalysisValidationError):
        parse_analysis(
            json.dumps({"findings": [default_finding(suggested_contexts=["   "])]})
        )
```

`tests/unit/test_analysis.py`에 추가:

```python
def test_prompt_asks_for_three_practice_contexts():
    """PRD.md:92 · agent-system-prompt.md:47이 요구하는 상황 3개. 프롬프트가 요구하지 않으면
    컬럼만 생기고 값은 영원히 null이다."""
    prompt = build_prompt("I go to gym.", [])
    assert "suggested_contexts" in prompt
    assert "3개" in prompt


def test_prompt_allows_fewer_contexts_rather_than_padding():
    """개수를 강제하면 모델이 같은 상황을 늘려 채운다 — §8.2가 길이 CHECK를 뺀 이유와 같다."""
    prompt = build_prompt("I go to gym.", [])
    assert "2개만 적어도 된다" in prompt


def test_prompt_keeps_contexts_within_the_learner_reach():
    """h-doc: 목표 수준(AWS 보고) 문형으로 상황을 만들면 첫 세션에서 얼어붙는다."""
    prompt = build_prompt("I go to gym.", [])
    assert "일상 → 회사 동료와의 협업 → 프로젝트 상황 보고" in prompt
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest ../../tests/unit/test_analysis.py ../../tests/unit/test_claude_schema.py -q -c pyproject.toml
```
기대: **5건 red** (`suggested_contexts` 필드가 없어 `extra="forbid"`에 걸리고, 프롬프트에 문구가 없다).
`test_finding_defaults_...` 1건은 이 시점에 이미 green일 수 있다 — 필드가 없으면 `default_finding()`은
그대로 통과한다. **red 건수를 세어 기록한다** ("6건 중 5건 red").

- [ ] **Step 3: 출력 계약을 확장한다**

`app/backend/app/models/analysis.py`:

```python
from typing import Annotated, Literal, get_args
```

`Severity` 정의 아래에 추가:

```python
# PRD.md:92 "같은 패턴을 최소 세 개의 다른 상황에서 재사용한다" ·
# agent-system-prompt.md:47 "suggested_contexts: three different contexts".
# 개수를 강제하지 않는다(설계서 §8.2) — 2개만 낸 응답을 거부하면 그 발화의 교정 전체를 잃는다.
# 항목의 빈 문자열은 거부한다: 공백만인 "상황"은 연습 재료가 되지 않는다.
# 상한을 두지 않는 이유: 출력 자체가 `claude_client.MAX_TOKENS`(16000)로 이미 묶여 있어
# 폭주하는 배열이 올 수 없다 — 여기서 개수를 발명하지 않는다.
SuggestedContext = Annotated[str, pydantic.Field(min_length=1)]
```

`ErrorFinding`의 `confidence` 다음 줄에 추가:

```python
    # 기본값을 둔다 — 필드가 없는 응답은 계약 위반이 아니다(§8.2 nullable). 필수로 만들면
    # conftest.default_finding(8필드)과 하네스 시나리오가 전부 깨진다(무회귀 T4).
    suggested_contexts: list[SuggestedContext] = pydantic.Field(default_factory=list)
```

- [ ] **Step 4: 프롬프트에 절을 추가한다**

`app/backend/app/services/analysis.py`의 `_TARGET_FORM_RULES` 다음에:

```python
# PRD.md:92 · agent-system-prompt.md:47이 요구하는 "서로 다른 상황 3개". 모델은 이미 낼 수 있는데
# 우리가 요구하지 않아 버려지고 있었다 — 소급이 불가능하므로(설계서 §8.2) 프롬프트가 요구한다.
# 문구는 h-doc 프로필을 따른다: 단문·단일 절, 일상 → 업무 협업 순서. 목표 수준(AWS 보고)
# 문형으로 상황을 만들면 첫 세션에서 얼어붙는다.
_SUGGESTED_CONTEXTS_RULES = """\
[suggested_contexts — 다시 연습할 상황 3개]
같은 패턴을 서로 다른 상황에서 다시 말해보게 할 재료다. 한국어 짧은 구로 3개 적는다.
- 서로 겹치지 않는 상황을 고른다. 같은 상황을 말만 바꿔 3개 적지 마라.
- 학습자가 실제로 겪는 범위에서 고른다: 일상 → 회사 동료와의 협업 → 프로젝트 상황 보고 순으로
  넓힌다. 학습자는 지금 단문 위주로 말하므로 상황도 한 문장으로 말할 수 있는 크기여야 한다.
- 예: `퇴근 후 운동 계획 말하기` / `동료에게 오늘 일정 알려주기` / `회의에서 진행 상황 한 줄 보고`
- 3개를 못 채우겠으면 2개만 적어도 된다. 억지로 채우려고 같은 상황을 늘리지 마라."""
```

`_OUTPUT_RULES`의 JSON 스켈레톤을 한 줄 늘린다 (필드 이름을 모델이 보게 한다):

```python
{"findings": [{"category": "...", "pattern_key": "...", "target_form": "...",
"original_span": "...", "correction": "...", "explanation": "...", "severity": "...",
"confidence": 0.0, "suggested_contexts": ["...", "...", "..."]}]}"""
```

`build_prompt`의 결합 목록에 `_SUGGESTED_CONTEXTS_RULES`를 `_TARGET_FORM_RULES` 다음으로 끼운다.

- [ ] **Step 5: 저장 경로를 잇는다**

`app/backend/app/services/analysis.py` 머리에 `import json`을 추가하고(표준 라이브러리 블록,
`import logging` 위) `_INSERT_OCCURRENCE_SQL`을 고친다:

```python
_INSERT_OCCURRENCE_SQL = """
insert into error_occurrences
       (utterance_id, pattern_id, original_span, correction, explanation, severity, confidence,
        suggested_contexts)
values ($1, $2, $3, $4, $5, $6, $7, $8)
"""
```

`_store_finding`의 `conn.execute` 마지막 인자로 추가:

```python
        Decimal(str(finding.confidence)),
        # asyncpg는 jsonb에 **str만** 받는다 — 파이썬 list를 바인딩하면
        # `DataError: expected str, got list`다 (2026-09-03 실측). 한글은 그대로 보존된다.
        # 없음은 null 하나로 표현한다: 빈 배열도 함께 쓰면 "없음"이 두 모양이 된다.
        json.dumps(finding.suggested_contexts, ensure_ascii=False)
        if finding.suggested_contexts
        else None,
```

- [ ] **Step 6: 통합 테스트로 종단을 단정한다 (AS9 저장 절반)**

`tests/integration/test_pipeline.py`에 추가:

```python
@pytest.mark.asyncio
async def test_analysis_stores_the_suggested_contexts_of_a_finding(
    db_pool: asyncpg.Pool, committed_session: Any, fake_claude: Any
):
    """AS9 — 모델이 낸 상황 3개가 error_occurrences에 보존된다.
    이 값이 없으면 슬라이스 2가 질문을 만들 재료가 없고, 소급도 불가능하다(§8.2)."""
    contexts = ["퇴근 후 운동 계획 말하기", "동료에게 오늘 일정 알려주기", "회의에서 진행 상황 한 줄 보고"]
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    claude = fake_claude(_response(default_finding(suggested_contexts=contexts)))
    job = await _claim(db_pool)

    await process_analysis(db_pool, claude, job)

    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select suggested_contexts from error_occurrences where utterance_id = $1",
            utterance.id,
        )
    assert json.loads(stored) == contexts


@pytest.mark.asyncio
async def test_analysis_leaves_suggested_contexts_null_when_the_model_omits_them(
    db_pool: asyncpg.Pool, committed_session: Any, fake_claude: Any
):
    """없음은 null 하나다 — 빈 배열을 쓰면 "모델이 안 냈다"와 "빈 배열을 냈다"가 갈린다."""
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    claude = fake_claude(_response(default_finding()))
    job = await _claim(db_pool)

    await process_analysis(db_pool, claude, job)

    async with db_pool.acquire() as conn:
        stored = await conn.fetchval(
            "select suggested_contexts from error_occurrences where utterance_id = $1",
            utterance.id,
        )
    assert stored is None
```

`_claim(pool)`은 `tests/integration/test_pipeline.py`에 **이미 있는** 헬퍼다(`claim_one`을 감싼다) —
새로 만들지 말고 그대로 쓴다. 2026-09-03에 그 파일에서 정의를 직접 확인했다.

추가로 **AS9의 나머지 절반**("재분석 후에도 최신 값이 남는다")을 덮는다 — 이것이 없으면 replace가
`suggested_contexts`를 낡은 값으로 남겨도 게이트가 통과한다:

```python
@pytest.mark.asyncio
async def test_reanalysis_replaces_the_stored_suggested_contexts(
    db_pool: asyncpg.Pool, committed_session: Any, fake_claude: Any
):
    """AS9 후단 — 같은 발화를 다시 분석하면 최신 상황 목록이 남는다(이전 값이 아니다)."""
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    first = ["퇴근 후 운동 계획 말하기"]
    second = ["동료에게 오늘 일정 알려주기", "회의에서 진행 상황 한 줄 보고"]
    await process_analysis(
        db_pool,
        fake_claude(_response(default_finding(suggested_contexts=first))),
        await _claim(db_pool),
    )

    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into analysis_jobs (job_type, utterance_id) values ('analyze_utterance', $1)",
            utterance.id,
        )
    await process_analysis(
        db_pool,
        fake_claude(_response(default_finding(suggested_contexts=second))),
        await _claim(db_pool),
    )

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "select suggested_contexts from error_occurrences where utterance_id = $1", utterance.id
        )
    assert len(rows) == 1, "replace가 이전 occurrence를 남겼다"
    assert json.loads(rows[0]["suggested_contexts"]) == second
```

- [ ] **Step 7: 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
```
기대: **+9건 → 403 passed** (claude_schema 3 · analysis 3 · pipeline 3). 프롬프트가 길어졌으므로 `test_build_prompt_is_pure_and_order_independent`가
여전히 통과하는지 확인한다 — 새 절이 순수 상수라 통과해야 한다.

```bash
git add app/backend/app/models/analysis.py app/backend/app/services/analysis.py tests/
git commit -m "feat: 분석이 연습 상황 3개를 산출·저장한다 (AS9 저장 경로)"
```

---

## Task 3: `attempts` 출력 계약 — 재시도 판정을 받아 정규화한다

DB를 건드리지 않는 순수 로직만. 저장은 Task 4다.

**Files:**
- Modify: `app/backend/app/models/analysis.py` (`PatternAttempt` 신설 + `AnalysisResult.attempts`)
- Modify: `app/backend/app/services/analysis.py` (프롬프트 절 1개 · `resolve_pattern_keys` 확장)
- Test: `tests/unit/test_claude_schema.py` · `tests/unit/test_analysis.py`

**Interfaces:**
- Consumes: Task 2가 확장한 `ErrorFinding`
- Produces: `PatternAttempt(pattern_key: str, outcome: Literal['correct','incorrect','unclear'])` ·
  `AnalysisResult.attempts: list[PatternAttempt]` (기본 `[]`) ·
  `resolve_pattern_keys(result, existing_patterns)`가 attempts의 key를 **기존 표기로 정규화하고
  미매치를 버린다**

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_claude_schema.py`:

```python
def test_result_parses_attempts_with_their_outcome():
    result = parse_analysis(
        json.dumps(
            {
                "findings": [],
                "attempts": [
                    {"pattern_key": "article_missing_before_place_noun", "outcome": "correct"}
                ],
            }
        )
    )
    assert result.attempts[0].pattern_key == "article_missing_before_place_noun"
    assert result.attempts[0].outcome == "correct"


def test_result_defaults_attempts_to_empty_when_absent():
    """대부분의 발화에는 재시도가 없다 — 기본값이 없으면 기존 픽스처가 전부 깨진다."""
    assert parse_analysis(json.dumps({"findings": []})).attempts == []


def test_attempt_rejects_an_outcome_outside_the_column_check():
    """'pending'은 pattern_attempts CHECK에 없다 — 경계에서 막지 않으면 저장 트랜잭션
    중간에 CheckViolation으로 터져 그 발화의 교정 전체가 사라진다."""
    with pytest.raises(AnalysisValidationError):
        parse_analysis(
            json.dumps(
                {"findings": [], "attempts": [{"pattern_key": "article_x", "outcome": "pending"}]}
            )
        )
```

`tests/unit/test_analysis.py`:

```python
def test_prompt_asks_whether_existing_patterns_were_retried():
    """이 판정이 복습 단계 전이의 유일한 신호원이다 — 프롬프트가 묻지 않으면
    모든 패턴이 1일 단계에 영원히 머문다(설계서 §4.1)."""
    prompt = build_prompt("I go to the gym.", [PatternRow("article", "article_x", "the + 명사")])
    assert "attempts" in prompt
    assert "시도하지 않은 패턴은 적지 마라" in prompt
    # 목록은 이 절 **아래**에 온다 — "위"라고 쓰면 모델이 다른 것을 찾는다
    assert "위 [이 학습자의 기존 패턴]" not in prompt


def test_resolve_pattern_keys_normalizes_an_attempt_key_to_the_existing_spelling():
    existing = [PatternRow("article", "article_missing_before_place_noun", "go to the + 장소 명사")]
    result = AnalysisResult(
        findings=[],
        attempts=[PatternAttempt(pattern_key="Article_Missing_Before_Place_Noun", outcome="correct")],
    )

    resolved = resolve_pattern_keys(result, existing)

    assert resolved.attempts[0].pattern_key == "article_missing_before_place_noun"


def test_resolve_pattern_keys_drops_an_attempt_for_an_unknown_pattern():
    """findings의 신규 key와 달리 **버린다** — 부가 신호 하나 때문에 그 발화의 교정
    전체를 잃으면 사용자가 보는 산출물을 저가치 필드에 내주는 것이 된다."""
    result = AnalysisResult(
        findings=[], attempts=[PatternAttempt(pattern_key="never_seen_key", outcome="correct")]
    )

    resolved = resolve_pattern_keys(result, [])

    assert resolved.attempts == []


def test_resolve_pattern_keys_keeps_the_last_verdict_for_a_repeated_key():
    """같은 패턴을 두 번 판정한 응답은 마지막 판정만 남긴다 —
    unique(pattern_id, utterance_id)에 두 행을 밀어넣을 수 없고, 순서 의존을 DB의
    on-conflict에 맡기지 않고 여기서 결정론으로 만든다."""
    existing = [PatternRow("article", "article_x", "the + 명사")]
    result = AnalysisResult(
        findings=[],
        attempts=[
            PatternAttempt(pattern_key="article_x", outcome="correct"),
            PatternAttempt(pattern_key="article_x", outcome="incorrect"),
        ],
    )

    resolved = resolve_pattern_keys(result, existing)

    assert [(a.pattern_key, a.outcome) for a in resolved.attempts] == [("article_x", "incorrect")]
```

`tests/unit/test_analysis.py`의 `from app.models.analysis import (...)`에 **`PatternAttempt`만**
더한다 — `AnalysisResult`·`ErrorFinding`은 이미 있고, `PatternRow`·`resolve_pattern_keys`·`build_prompt`도
`from app.services.analysis import (...)`에 이미 있다(2026-09-03 확인). 없는 것만 더한다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest ../../tests/unit/test_analysis.py ../../tests/unit/test_claude_schema.py -q -c pyproject.toml
```
기대: **7건 중 6건 red** (`test_result_defaults_attempts_to_empty_when_absent`는 `attempts` 속성이
없어 `AttributeError`로 red — 이것도 red로 센다). red 건수를 기록한다.

- [ ] **Step 3: 계약을 추가한다**

`app/backend/app/models/analysis.py`, `SEVERITIES` 아래:

```python
# 006 `pattern_attempts.outcome` CHECK와 **같은 집합**이다. 'pending'은 없다 —
# 이 판정은 전사문을 이미 본 뒤에 이루어져 대기 상태가 없다(발음 쪽 표와 다른 점).
AttemptOutcome = Literal["correct", "incorrect", "unclear"]
ATTEMPT_OUTCOMES: tuple[AttemptOutcome, ...] = get_args(AttemptOutcome)
```

`ErrorFinding` 아래:

```python
class PatternAttempt(pydantic.BaseModel):
    """이번 발화가 **기존 패턴**을 다시 시도한 결과 — 006 `pattern_attempts` 1행이 된다.

    `pattern_key`의 형식을 여기서 보지 않는 이유는 `ErrorFinding`과 같다: 기존 패턴
    목록과의 대조는 그 목록을 아는 저장 단계(`resolve_pattern_keys`)의 몫이다.
    """

    model_config = pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)

    pattern_key: str = pydantic.Field(min_length=1)
    outcome: AttemptOutcome
```

`AnalysisResult`:

```python
class AnalysisResult(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")

    findings: list[ErrorFinding]
    # 기본값을 둔다 — 재시도가 없는 발화가 대부분이고, 없는 것이 계약 위반이 아니다.
    attempts: list[PatternAttempt] = pydantic.Field(default_factory=list)
```

- [ ] **Step 4: 프롬프트에 절을 추가한다**

`app/backend/app/services/analysis.py`, `_PATTERN_KEY_RULES` 다음에:

```python
# 설계서 §11 미결 2 종결: **문법·표현** 재발화의 정답 여부는 분석 워커의 Claude가 판정한다
# (발음은 전사문에 흔적이 0이라 Nova가 판정해 `pronunciation_attempts`에 쌓인다 — 자매 설계).
# 이 판정이 복습 단계 전이의 **유일한 신호원**이다: 없으면 모든 패턴이 1일 단계에 머문다.
_ATTEMPT_RULES = """\
[attempts — 기존 패턴을 다시 시도했는가]
아래 [이 학습자의 기존 패턴] 목록의 패턴을 이번 발화에서 다시 시도했다면 그 결과를 적는다.
- correct: 그 패턴의 목표 형태를 옳게 썼다.
- incorrect: 같은 오류를 다시 냈다.
- unclear: 시도한 것 같지만 옳은지 판정할 수 없다. 모르겠으면 억지로 correct/incorrect로 정하지 마라.
- **시도하지 않은 패턴은 적지 마라.** 이번 발화에 그 문형이 아예 나타나지 않은 것은 시도가 아니다.
- 목록에 없는 pattern_key를 여기 적지 마라. 처음 발견한 오류는 findings에 넣는다.
- 시도한 패턴이 없으면 "attempts": [] 를 출력한다."""
```

`_OUTPUT_RULES`의 스켈레톤에 attempts를 더한다:

```python
{"findings": [{"category": "...", "pattern_key": "...", "target_form": "...",
"original_span": "...", "correction": "...", "explanation": "...", "severity": "...",
"confidence": 0.0, "suggested_contexts": ["...", "...", "..."]}],
"attempts": [{"pattern_key": "...", "outcome": "..."}]}"""
```

`build_prompt`의 결합 목록에서 `_PATTERN_KEY_RULES` 다음, `_existing_patterns_section(...)` **앞**에
`_ATTEMPT_RULES`를 넣는다 — 규칙이 먼저 오고 목록이 뒤에 오는 기존 순서를 유지한다.

- [ ] **Step 5: `resolve_pattern_keys`를 확장한다**

같은 파일. 함수 끝의 `return AnalysisResult(findings=findings)`를 아래로 바꾼다:

```python
    # attempts는 findings와 **다르게** 다룬다: 미매치 key를 예외로 올리지 않고 버린다.
    # 근거 — 이것은 복습 단계의 부가 신호이고, 버려도 손상되는 데이터가 없다. 반면
    # findings의 규격 밖 신규 key를 그냥 저장하면 병합되지 않는 쌍둥이 패턴이 영구히 남는다.
    # 성질이 다른 두 실패를 같은 강도로 다루면 저가치 필드 하나가 그 발화의 교정 전체를 태운다.
    # dict로 모으는 것은 같은 key를 두 번 판정한 응답에서 **마지막 판정만** 남기기 위한 것이다 —
    # unique(pattern_id, utterance_id)에 두 행을 넣을 수 없고, 순서 의존을 DB에 맡기지 않는다.
    attempts: dict[str, PatternAttempt] = {}
    for attempt in result.attempts:
        canonical = canonical_by_fold.get(attempt.pattern_key.casefold())
        if canonical is None:
            logger.warning(
                "dropping attempt for unknown pattern_key %r — not in this learner's patterns",
                attempt.pattern_key,
            )
            continue
        attempts[canonical] = (
            attempt
            if canonical == attempt.pattern_key
            else attempt.model_copy(update={"pattern_key": canonical})
        )
    return AnalysisResult(findings=findings, attempts=list(attempts.values()))
```

import에 `PatternAttempt`를 더한다 (`from app.models.analysis import (...)`).

- [ ] **Step 6: 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
```
기대: **+7건 → 410 passed** (claude_schema 3 · analysis 4).

```bash
git add app/backend/app/models/analysis.py app/backend/app/services/analysis.py tests/unit/
git commit -m "feat: 재발화 정답 여부를 분석 출력 계약에 넣는다 (attempts)"
```

---

## Task 4: `services/review.py` — 재시도 저장 + 복습 상태 재계산

**Files:**
- Create: `app/backend/app/services/review.py`
- Test: `tests/unit/test_review.py` (신규)

**Interfaces:**
- Consumes: Task 1의 `pattern_attempts` · Task 3의 `PatternAttempt`
- Produces:
  - `STAGE_DAYS: tuple[int, ...] = (1, 3, 7)` · `FINAL_STAGE: int = 3`
  - `ReviewState(stage, completed, next_review_at, anchor, scenario_context)`
  - `fold_stages(relapse_at: datetime | None, correct_times: list[datetime], scenario_context: str) -> ReviewState`
    — **순수 함수.** DB를 보지 않는다. 예정일 경계 판정 전체를 담는다
  - `async store_attempts(conn, utterance_id: UUID, user_id: UUID, attempts: list[PatternAttempt]) -> set[UUID]`
    — replace 저장 후 **건드린 pattern_id 집합**을 돌려준다
  - `async recompute(conn, pattern_id: UUID) -> ReviewState` — 이력을 읽어 접고 `error_patterns`·`review_tasks`에 반영

- [ ] **Step 1: 순수 함수부터 실패하는 테스트를 쓴다**

`tests/unit/test_review.py` (신규):

```python
"""복습 상태 재계산 — 설계서 §4.1 + 계획서 「복습 상태 재계산」 절.

두 층으로 나눠 본다. **앞쪽은 DB 없는 순수 함수**(`fold_stages`)로 예정일 경계를 전부 덮고,
뒤쪽은 `db_conn`(롤백되는 한 트랜잭션)으로 반영 결과를 본다 — `recompute`는 자기 트랜잭션을
열지 않고 호출자의 트랜잭션에서 도는 것이 계약이라 커밋 경계를 흉내낼 필요가 없다.

**발화 시각을 명시해 넣는다.** 단계 전이가 `now()`가 아니라 발화 시각을 기준으로 하는 것이
이 모듈의 멱등성 근거라서, 시각을 테스트가 통제하지 않으면 그 성질을 단정할 수 없다.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import asyncpg
import pytest

from app.models.analysis import PatternAttempt
from app.services.review import (
    FINAL_STAGE,
    STAGE_DAYS,
    fold_stages,
    recompute,
    store_attempts,
)

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
CONTEXT = "go to gym"
# KST 정오라 어느 타임존으로 읽어도 달력 날짜가 갈리지 않는다 — 이 파일은 간격만 보고
# 달력 날짜는 보지 않는다(그 경계는 test_chronic.py가 소유한다).
T0 = datetime.fromisoformat("2026-09-01T12:00:00+09:00")


def _days(count: int) -> timedelta:
    return timedelta(days=count)


# ── 순수 함수: 예정일 접기 ────────────────────────────────────────────────────


# ① 틀린 적이 없으면 복습할 것이 없다
def test_a_pattern_that_was_never_wrong_has_nothing_to_review():
    state = fold_stages(None, [], CONTEXT)

    assert state.stage == 1
    assert state.completed is False
    assert state.anchor is None
    assert state.next_review_at is None


# ② 틀린 직후는 1일 뒤다
def test_a_relapse_schedules_the_first_stage_one_day_later():
    state = fold_stages(T0, [], CONTEXT)

    assert state.stage == 1
    assert state.anchor == T0
    assert state.next_review_at == T0 + _days(1)


# ③ 예정일에 맞히면 다음 단계로 간다. anchor는 그 정답의 발화 시각이다
def test_a_correct_on_the_due_date_advances_to_the_next_stage():
    said_at = T0 + _days(1)

    state = fold_stages(T0, [said_at], CONTEXT)

    assert state.stage == 2
    assert state.anchor == said_at
    assert state.next_review_at == said_at + _days(3)


# ④ **회귀 방지** — 예정일 **전**의 정답은 단계를 올리지 않는다. 이것이 없으면 같은 세션에서
#    세 번 맞히는 것으로 1·3·7일을 한 번도 경과하지 않고 완주해 간격 반복이 무의미해진다.
#    (2026-09-03 계획 검토에서 잡힌 결함이고 실제로 재현했다.)
def test_a_correct_before_the_due_date_does_not_advance_anything():
    early = [T0 + timedelta(minutes=5), T0 + timedelta(minutes=10), T0 + timedelta(hours=20)]

    state = fold_stages(T0, early, CONTEXT)

    assert state.stage == 1
    assert state.completed is False
    assert state.next_review_at == T0 + _days(1), "예정일이 움직였다 — 간격 조건이 빠졌다"


# ⑤ 완주까지는 1 + 3 + 7 = 11일이 실제로 경과해야 한다
def test_completing_all_three_stages_takes_the_documented_intervals():
    first = T0 + _days(1)
    second = first + _days(3)
    third = second + _days(7)

    state = fold_stages(T0, [first, second, third], CONTEXT)

    assert state.completed is True
    assert state.stage == FINAL_STAGE
    assert state.anchor == third
    assert state.next_review_at is None
    assert third - T0 == _days(sum(STAGE_DAYS)) == _days(11)


# ⑥ 예정일 전 정답이 섞여 있어도 예정일을 넘긴 것만 센다
def test_early_corrects_mixed_with_on_time_ones_are_ignored():
    on_time = T0 + _days(1)
    too_early = on_time + _days(1)  # 2단계 예정일(+3일)보다 이르다
    next_on_time = on_time + _days(3)

    state = fold_stages(T0, [on_time, too_early, next_on_time], CONTEXT)

    assert state.stage == 3
    assert state.anchor == next_on_time
    assert state.next_review_at == next_on_time + _days(7)


# ── DB 반영 ──────────────────────────────────────────────────────────────────

_SEQ = iter(range(1, 10_000))


async def _seed(conn: asyncpg.Connection) -> tuple[UUID, UUID]:
    """user → session → pattern 한 벌. 발화는 테스트가 시각을 정해 따로 넣는다."""
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'Review Test', 'Asia/Seoul', 'A2')",
        USER_ID,
    )
    session_id = await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        USER_ID,
    )
    pattern_id = await conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'article', 'article_missing_before_place_noun', 'go to the + 장소 명사') "
        "returning id",
        USER_ID,
    )
    return session_id, pattern_id


async def _utterance(conn: asyncpg.Connection, session_id: UUID, at: datetime) -> UUID:
    return await conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
        "values ($1, 'user', 'I go to gym.', $2, $3) returning id",
        session_id,
        next(_SEQ),
        at,
    )


async def _occurrence(conn: asyncpg.Connection, utterance_id: UUID, pattern_id: UUID) -> None:
    await conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, 'go to gym', 'go to the gym', '정관사가 필요합니다.', 'medium', 0.9)",
        utterance_id,
        pattern_id,
    )


async def _attempt(
    conn: asyncpg.Connection, utterance_id: UUID, pattern_id: UUID, outcome: str
) -> None:
    await conn.execute(
        "insert into pattern_attempts (pattern_id, utterance_id, outcome) values ($1, $2, $3)",
        pattern_id,
        utterance_id,
        outcome,
    )


async def _review_on_time(
    conn: asyncpg.Connection, session_id: UUID, pattern_id: UUID, at: datetime
) -> datetime:
    """예정일마다 정확히 맞혀 3단계를 완주시킨다. 마지막 정답의 발화 시각을 돌려준다."""
    for days in STAGE_DAYS:
        at = at + _days(days)
        await _attempt(conn, await _utterance(conn, session_id, at), pattern_id, "correct")
    return at


async def _pattern_row(conn: asyncpg.Connection, pattern_id: UUID) -> asyncpg.Record:
    row = await conn.fetchrow(
        "select next_review_at, mastery_score from error_patterns where id = $1", pattern_id
    )
    assert row is not None
    return row


async def _task_rows(conn: asyncpg.Connection, pattern_id: UUID) -> list[asyncpg.Record]:
    return await conn.fetch(
        "select review_stage, status, due_at, scenario_context from review_tasks "
        "where pattern_id = $1 order by review_stage",
        pattern_id,
    )


# ⑦ 처음 틀린 패턴이 복습 목록에 들어간다 — 이 값이 있어야 "오늘 복습할 목록"이 0행을 벗어난다
@pytest.mark.asyncio
async def test_recompute_schedules_a_fresh_error(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)

    state = await recompute(db_conn, pattern_id)

    assert state.next_review_at == T0 + _days(1)
    row = await _pattern_row(db_conn, pattern_id)
    assert row["next_review_at"] == T0 + _days(1)
    assert row["mastery_score"] == 0
    assert [(t["review_stage"], t["status"], t["due_at"]) for t in await _task_rows(db_conn, pattern_id)] == [
        (1, "pending", T0 + _days(1))
    ]


# ⑧ 예정일에 맞히면 3일 뒤로 넘어간다 (DB 반영까지)
@pytest.mark.asyncio
async def test_recompute_advances_on_an_on_time_correct(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    due = T0 + _days(1)
    await _attempt(db_conn, await _utterance(db_conn, session_id, due), pattern_id, "correct")

    state = await recompute(db_conn, pattern_id)

    assert state.stage == 2
    assert (await _pattern_row(db_conn, pattern_id))["next_review_at"] == due + _days(3)
    assert [(t["review_stage"], t["status"]) for t in await _task_rows(db_conn, pattern_id)] == [
        (2, "pending")
    ]


# ⑨ 완주 — 목록에서 빠지고 mastery_score가 그 상태를 기록한다 (§4.1)
@pytest.mark.asyncio
async def test_recompute_marks_a_completed_review(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    await _review_on_time(db_conn, session_id, pattern_id, T0)

    state = await recompute(db_conn, pattern_id)

    assert state.completed is True
    row = await _pattern_row(db_conn, pattern_id)
    assert row["next_review_at"] is None
    assert row["mastery_score"] == 100
    assert [(t["review_stage"], t["status"]) for t in await _task_rows(db_conn, pattern_id)] == [
        (FINAL_STAGE, "done")
    ]


# ⑩ 재발하면 1단계로 되돌아가고 상위 단계 행이 남지 않는다 (캡틴 결정 2026-09-03)
@pytest.mark.asyncio
async def test_a_relapse_resets_to_stage_one_and_leaves_no_higher_row(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    completed_at = await _review_on_time(db_conn, session_id, pattern_id, T0)
    await recompute(db_conn, pattern_id)  # 완주 상태를 만든다

    relapse_at = completed_at + _days(5)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, relapse_at), pattern_id)
    state = await recompute(db_conn, pattern_id)

    assert state.stage == 1
    assert state.next_review_at == relapse_at + _days(1)
    assert (await _pattern_row(db_conn, pattern_id))["mastery_score"] == 0
    assert [(t["review_stage"], t["status"]) for t in await _task_rows(db_conn, pattern_id)] == [
        (1, "pending")
    ]


# ⑪ incorrect 판정도 재발이다 — occurrence 없이 attempts에만 적힌 경우에도 되돌린다
@pytest.mark.asyncio
async def test_an_incorrect_retry_counts_as_a_relapse(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    await _attempt(
        db_conn, await _utterance(db_conn, session_id, T0 + _days(1)), pattern_id, "correct"
    )
    fail_at = T0 + _days(2)
    await _attempt(db_conn, await _utterance(db_conn, session_id, fail_at), pattern_id, "incorrect")

    state = await recompute(db_conn, pattern_id)

    assert state.stage == 1
    assert state.next_review_at == fail_at + _days(1)


# ⑫ unclear는 단계를 움직이지 않는다 — 판정 불가를 진전으로도 후퇴로도 세지 않는다
@pytest.mark.asyncio
async def test_an_unclear_retry_moves_nothing(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    await _attempt(
        db_conn, await _utterance(db_conn, session_id, T0 + _days(1)), pattern_id, "unclear"
    )

    state = await recompute(db_conn, pattern_id)

    assert state.stage == 1
    assert state.next_review_at == T0 + _days(1)


# ⑬ **멱등** — 이 모듈의 존재 이유다. job은 재시도된다
@pytest.mark.asyncio
async def test_recompute_is_idempotent(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)
    await _attempt(
        db_conn, await _utterance(db_conn, session_id, T0 + _days(1)), pattern_id, "correct"
    )

    first = await recompute(db_conn, pattern_id)
    first_tasks = [
        (t["review_stage"], t["status"], t["due_at"]) for t in await _task_rows(db_conn, pattern_id)
    ]
    second = await recompute(db_conn, pattern_id)
    second_tasks = [
        (t["review_stage"], t["status"], t["due_at"]) for t in await _task_rows(db_conn, pattern_id)
    ]

    assert first == second
    assert first_tasks == second_tasks
    assert len(second_tasks) == 1


# ⑭ 근거가 사라진 패턴은 복습 목록에서도 빠진다 (재분석으로 occurrence가 전부 지워진 경우)
@pytest.mark.asyncio
async def test_a_pattern_without_evidence_leaves_the_due_list(db_conn: asyncpg.Connection):
    _, pattern_id = await _seed(db_conn)

    state = await recompute(db_conn, pattern_id)

    assert state.next_review_at is None
    assert state.anchor is None
    assert await _task_rows(db_conn, pattern_id) == []


# ⑮ scenario_context는 실제 데이터다 — 슬라이스 1은 무엇도 생성하지 않는다(§3.2)
@pytest.mark.asyncio
async def test_scenario_context_comes_from_the_latest_occurrence(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _occurrence(db_conn, await _utterance(db_conn, session_id, T0), pattern_id)

    await recompute(db_conn, pattern_id)

    assert (await _task_rows(db_conn, pattern_id))[0]["scenario_context"] == CONTEXT


# ⑯ store_attempts — replace 이고, 재계산 대상 패턴을 돌려준다
@pytest.mark.asyncio
async def test_store_attempts_replaces_and_reports_touched_patterns(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    utterance_id = await _utterance(db_conn, session_id, T0)

    touched = await store_attempts(
        db_conn,
        utterance_id,
        USER_ID,
        [PatternAttempt(pattern_key="article_missing_before_place_noun", outcome="correct")],
    )
    assert touched == {pattern_id}

    # 재분석: 같은 발화를 다시 저장해도 행이 늘지 않는다 (AS10)
    touched_again = await store_attempts(
        db_conn,
        utterance_id,
        USER_ID,
        [PatternAttempt(pattern_key="article_missing_before_place_noun", outcome="incorrect")],
    )
    assert touched_again == {pattern_id}
    rows = await db_conn.fetch(
        "select outcome from pattern_attempts where utterance_id = $1", utterance_id
    )
    assert [row["outcome"] for row in rows] == ["incorrect"]


# ⑰ 사라진 패턴을 가리키는 판정은 조용히 버려진다 — 분석 전체를 실패시키지 않는다
@pytest.mark.asyncio
async def test_store_attempts_skips_a_pattern_key_that_no_longer_exists(
    db_conn: asyncpg.Connection,
):
    session_id, _ = await _seed(db_conn)
    utterance_id = await _utterance(db_conn, session_id, T0)

    touched = await store_attempts(
        db_conn,
        utterance_id,
        USER_ID,
        [PatternAttempt(pattern_key="vanished_key", outcome="correct")],
    )

    assert touched == set()
    assert await db_conn.fetchval("select count(*) from pattern_attempts") == 0
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest ../../tests/unit/test_review.py -q -c pyproject.toml
```
기대: **17건 전부 red** — `ModuleNotFoundError: app.services.review`. ①~⑥은 DB를 쓰지 않으므로
모듈이 생기면 즉시 판정된다.

- [ ] **Step 3: 모듈을 만든다**

`app/backend/app/services/review.py` (신규):

```python
"""복습 스케줄의 소유자 — 재발화 판정 기록과 복습 상태 재계산 (설계서 §4.1·§8.1).

`next_review_at`에 값을 넣는 코드는 이 모듈뿐이다. 세션·워커는 배선만 한다.

**단계를 증분하지 않고 이력에서 다시 접는다.** 이 모듈에서 이것 하나만 기억하면 된다.
`analyze_utterance` job은 재시도되고 결과 저장은 발화 단위 replace라서, `stage + 1`로
전이시키면 재실행마다 단계가 올라가 학습자가 하지 않은 복습이 완주된다. 그래서 상태를
`error_occurrences`와 `pattern_attempts`에서 매번 다시 계산한다 — `frequency`를 `+1`하지
않고 행 수에서 다시 세는 것(`services/analysis.py`)과 같은 규약이고, 같은 이유다.

**그리고 정답 횟수를 세지 않는다 — 예정일을 하나씩 접는다.** §4.1의 "복습을 완주하면 다음
단계로 진행한다"는 그 단계의 예정일이 온 뒤에 다시 맞혔다는 뜻이다. 단순히 correct를 3번
세면 같은 세션에서 세 번 맞히는 것으로 1·3·7일을 한 번도 경과하지 않고 완주해 간격 반복이
무의미해진다. `fold_stages`가 그 조건을 담고, **순수 함수**라 DB 없이 검증된다.

시각의 기준은 **발화 시각**이다. `now()`를 기준으로 쓰면 재실행마다 예정일이 밀려 멱등이
깨진다. 간격 연산은 `timedelta`라 타임존과 무관하다 — 달력 날짜를 쓰는 곳은 이 모듈에
없다(만성 지표의 "재발 일수"가 그 경계를 갖고 `services/chronic.py`가 소유한다).

`review_tasks`는 패턴당 **0행 또는 1행**이다. 재계산은 그 패턴의 행을 전부 지운 뒤 현재
상태 1행을 넣는다 — `unique(pattern_id, review_stage)`와 맞물리는 유일한 형태이고, 지운
이력이 손실이 아닌 근거는 완주·재발 여부가 `pattern_attempts`·`error_occurrences`에서
언제든 다시 계산된다는 것이다 (캡틴 결정 2026-09-03).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import UUID

import asyncpg

from app.models.analysis import PatternAttempt

logger = logging.getLogger(__name__)

# 복습 주기 1·3·7일 3단계. **문서로 확정된 값이다** (설계서 §4.1 "1일 → 3일 → 7일",
# `docs/database-schema.md`) — 발명값이 아니다. 완주까지 최소 11일이 실제로 경과한다.
STAGE_DAYS: tuple[int, ...] = (1, 3, 7)
FINAL_STAGE: int = len(STAGE_DAYS)

# mastery_score는 점수가 아니라 **상태 마커**다 (캡틴 결정 2026-09-03): 3단계를 재발 없이
# 완주했는지만 담는다. 중간값을 만들지 않는 이유는 설계서 §3.2 — 임계값을 발명하지 않는다.
# 재발로 100 → 0이 되어도 정보를 잃지 않는다: 완주 이력은 `pattern_attempts`에 그대로 남아
# "3단계 소진 후 재발"(§6.2의 결정론적 만성 신호)을 언제든 다시 계산할 수 있다.
MASTERED = Decimal("100")
NOT_MASTERED = Decimal("0")

# 슬라이스 1은 무엇도 생성하지 않으므로(§3.2의 경계) 과제 유형은 "다시 말해보기" 하나다.
# 슬라이스 2가 Claude 산출 상황(`suggested_contexts`)으로 이 자리를 넓힌다.
REVIEW_TASK_TYPE = "rephrase"

_DELETE_ATTEMPTS_SQL = """
delete from pattern_attempts where utterance_id = $1 returning pattern_id
"""

# pattern_key → pattern_id 해석을 insert 안에서 한다: 목록에 없는 key는 select가 0행을
# 돌려주어 **행이 생기지 않는다**. 별도 조회 없이 "조용히 버린다"가 성립한다.
_INSERT_ATTEMPT_SQL = """
insert into pattern_attempts (pattern_id, utterance_id, outcome)
select p.id, $2, $3
  from error_patterns p
 where p.user_id = $1 and p.pattern_key = $4
returning pattern_id
"""

# 접기에 필요한 이력만 읽는다. 단계 전이는 파이썬(`fold_stages`)이 한다 — 각 단계의 통과
# 시각이 다음 단계의 기준이 되는 **연쇄**라서 집계 함수로 표현되지 않는다(재귀 CTE 회피).
#
# `greatest`는 NULL 인자를 건너뛴다(Postgres 의미론, 2026-09-03 실측) — 그래서 occurrence만
# 있거나 incorrect만 있는 경우가 분기 없이 처리된다.
# `u.created_at > r.at`의 **strict `>`**: 같은 발화에 오류와 정답이 함께 달린 모순된 판정에서
# 그 정답을 세지 않는다. 그 순간에는 틀린 것으로 남는다.
_HISTORY_SQL = """
with relapse as (
      select greatest(
               (select max(u.created_at)
                  from error_occurrences eo
                  join utterances u on u.id = eo.utterance_id
                 where eo.pattern_id = $1),
               (select max(u.created_at)
                  from pattern_attempts pa
                  join utterances u on u.id = pa.utterance_id
                 where pa.pattern_id = $1 and pa.outcome = 'incorrect')
             ) as at
),
context as (
      select coalesce(
               (select eo.original_span
                  from error_occurrences eo
                  join utterances u on u.id = eo.utterance_id
                 where eo.pattern_id = $1
                 order by u.created_at desc, eo.id desc
                 limit 1),
               (select target_form from error_patterns where id = $1)
             ) as scenario_context
)
select r.at as relapse_at,
       ctx.scenario_context,
       coalesce(
         (select array_agg(u.created_at order by u.created_at, pa.id)
            from pattern_attempts pa
            join utterances u on u.id = pa.utterance_id
           where pa.pattern_id = $1
             and pa.outcome = 'correct'
             and (r.at is null or u.created_at > r.at)),
         '{}'::timestamptz[]
       ) as correct_times
  from relapse r, context ctx
"""

_APPLY_PATTERN_SQL = """
update error_patterns set next_review_at = $2, mastery_score = $3 where id = $1
"""

_DELETE_TASKS_SQL = """
delete from review_tasks where pattern_id = $1
"""

_INSERT_TASK_SQL = """
insert into review_tasks (pattern_id, task_type, scenario_context, review_stage, due_at, status)
values ($1, $2, $3, $4, $5, $6)
"""


@dataclass(frozen=True, slots=True)
class ReviewState:
    """패턴 하나의 복습 상태 — 이력에서 계산된 파생물이고 그 자체로는 저장되지 않는다."""

    stage: int
    completed: bool
    next_review_at: datetime | None
    anchor: datetime | None
    scenario_context: str


def fold_stages(
    relapse_at: datetime | None, correct_times: list[datetime], scenario_context: str
) -> ReviewState:
    """마지막 재발 이후의 정답들을 훑어 **예정일을 넘긴 것만** 단계로 센다 (순수 함수).

    `correct_times`는 발화 시각 오름차순이어야 한다 — `_HISTORY_SQL`이 그 순서로 돌려준다.
    예정일 전의 정답은 건너뛴다: 기록(`pattern_attempts`)에는 남고 단계만 올리지 않는다.
    한 세션에서 여러 번 맞히는 것으로 1·3·7일을 건너뛰는 경로를 막는 것이 이 조건이다.

    `relapse_at`이 없으면 틀린 적이 없는 패턴이므로 복습할 것이 없다 — 재분석으로
    occurrence가 전부 지워진 패턴도 이 경로로 목록에서 빠진다.
    """
    if relapse_at is None:
        return ReviewState(
            stage=1,
            completed=False,
            next_review_at=None,
            anchor=None,
            scenario_context=scenario_context,
        )

    anchor = relapse_at
    stage = 1
    for said_at in correct_times:
        if said_at < anchor + timedelta(days=STAGE_DAYS[stage - 1]):
            continue  # 예정일 전 — 간격이 경과하지 않았다
        anchor = said_at
        stage += 1
        if stage > FINAL_STAGE:
            return ReviewState(
                stage=FINAL_STAGE,
                completed=True,
                next_review_at=None,
                anchor=anchor,
                scenario_context=scenario_context,
            )
    return ReviewState(
        stage=stage,
        completed=False,
        next_review_at=anchor + timedelta(days=STAGE_DAYS[stage - 1]),
        anchor=anchor,
        scenario_context=scenario_context,
    )


async def store_attempts(
    conn: asyncpg.Connection,
    utterance_id: UUID,
    user_id: UUID,
    attempts: list[PatternAttempt],
) -> set[UUID]:
    """이 발화의 재시도 판정을 **replace 저장**하고 건드린 패턴 id 집합을 돌려준다.

    지워진 행의 pattern_id도 집합에 넣는다 — 재분석에서 사라진 판정의 패턴을 다시 계산하지
    않으면 그 패턴이 낡은 단계에 남는다(`_DELETE_OCCURRENCES_SQL`이 pattern_id를 돌려받는
    것과 같은 이유).

    호출자의 트랜잭션 안에서 돈다. 자기 트랜잭션을 열지 않는다 — 판정 기록과 그에 따른 단계
    갱신이 갈라지면 절반만 반영된 상태가 남는다(설계서 §9 Dependency).
    """
    removed = await conn.fetch(_DELETE_ATTEMPTS_SQL, utterance_id)
    touched: set[UUID] = {record["pattern_id"] for record in removed}
    for attempt in attempts:
        pattern_id = await conn.fetchval(
            _INSERT_ATTEMPT_SQL, user_id, utterance_id, attempt.outcome, attempt.pattern_key
        )
        if pattern_id is None:
            # `resolve_pattern_keys`의 정규화를 통과했는데도 행이 없다 = 그 사이 패턴이
            # 사라졌다(재분석으로 occurrence가 0이 되어 정리된 경우). 버리고 계속한다.
            logger.warning(
                "attempt for pattern_key %r stored no row — pattern is gone", attempt.pattern_key
            )
            continue
        touched.add(pattern_id)
    return touched


async def recompute(conn: asyncpg.Connection, pattern_id: UUID) -> ReviewState:
    """패턴 하나의 복습 상태를 이력에서 다시 계산해 반영한다 (멱등).

    `error_patterns`(`next_review_at`·`mastery_score`)와 `review_tasks` 0~1행을 함께 맞춘다.
    호출자의 트랜잭션 안에서 돈다.
    """
    record = await conn.fetchrow(_HISTORY_SQL, pattern_id)
    if record is None:  # 방어: 교차 조인이라 항상 1행이지만 계약을 코드로 남긴다
        raise LookupError(f"review history query returned no row for pattern {pattern_id}")

    state = fold_stages(
        record["relapse_at"], list(record["correct_times"] or []), record["scenario_context"]
    )

    await conn.execute(
        _APPLY_PATTERN_SQL,
        pattern_id,
        state.next_review_at,
        MASTERED if state.completed else NOT_MASTERED,
    )
    # 지우고 다시 넣는다 — 한 statement 안의 delete/insert는 서로의 효과를 보지 못해
    # unique(pattern_id, review_stage)에 부딪힌다. 두 문장으로 나누는 것이 그 함정을 피한다.
    await conn.execute(_DELETE_TASKS_SQL, pattern_id)
    if state.anchor is not None:
        await conn.execute(
            _INSERT_TASK_SQL,
            pattern_id,
            REVIEW_TASK_TYPE,
            state.scenario_context,
            FINAL_STAGE if state.completed else state.stage,
            state.next_review_at or state.anchor,
            "done" if state.completed else "pending",
        )
    return state
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd app/backend && .venv/bin/pytest ../../tests/unit/test_review.py -q -c pyproject.toml
```
기대: 17건 전부 PASS. ⚠️ ④(예정일 전 정답)가 실패하면 `fold_stages`의 비교가 `<`가 아니라
`<=`이거나 `continue`가 빠진 것이다 — 그 한 줄이 간격 조건의 유일한 방벽이다.

- [ ] **Step 5: 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
```
기대: **+17건 → 427 passed**.

```bash
git add app/backend/app/services/review.py tests/unit/test_review.py
git commit -m "feat: 복습 상태를 예정일 기준으로 접어 재계산한다 (next_review_at·review_tasks·mastery_score)"
```

---

## Task 5: 분석 트랜잭션에 배선한다 — 종단 관통

**Files:**
- Modify: `app/backend/app/services/analysis.py` (`_replace_occurrences` 안 3줄)
- Test: `tests/integration/test_pipeline.py`

**Interfaces:**
- Consumes: Task 4의 `store_attempts` · `recompute`
- Produces: 없음 (배선). 이 태스크가 끝나면 **실제 대화 1턴이 복습 예정일을 만든다**

- [ ] **Step 1: 실패하는 통합 테스트를 쓴다**

`tests/integration/test_pipeline.py`에 추가:

```python
@pytest.mark.asyncio
async def test_analysis_schedules_the_first_review_for_a_new_pattern(
    db_pool: asyncpg.Pool, committed_session: Any, fake_claude: Any
):
    """§4.1 — 이 슬라이스의 완료 판정. 지금까지 next_review_at은 항상 null이었다."""
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    claude = fake_claude(_response(default_finding()))
    job = await _claim(db_pool)

    await process_analysis(db_pool, claude, job)

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "select p.next_review_at, p.mastery_score, u.created_at as said_at "
            "  from error_patterns p "
            "  join error_occurrences eo on eo.pattern_id = p.id "
            "  join utterances u on u.id = eo.utterance_id "
            " where p.pattern_key = $1",
            ARTICLE_PATTERN_KEY,
        )
        tasks = await conn.fetch(
            "select review_stage, status from review_tasks where pattern_id = "
            "(select id from error_patterns where pattern_key = $1)",
            ARTICLE_PATTERN_KEY,
        )
    assert row is not None
    # 발화 시각 + 1일이다 — now() 기준이 아니다
    assert row["next_review_at"] == row["said_at"] + timedelta(days=1)
    assert row["mastery_score"] == 0
    assert [(t["review_stage"], t["status"]) for t in tasks] == [(1, "pending")]


@pytest.mark.asyncio
async def test_a_correct_retry_advances_the_review_stage_end_to_end(
    db_pool: asyncpg.Pool, committed_session: Any, fake_claude: Any
):
    """1턴에서 오류를 내고, 다음 턴에서 같은 패턴을 맞히면 3일 뒤로 넘어간다."""
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    await process_analysis(
        db_pool, fake_claude(_response(default_finding())), await _claim(db_pool)
    )

    retry = await _save(db_pool, committed_session.session_id, OFFICE_ANSWER)
    retry_response = json.dumps(
        {"findings": [], "attempts": [{"pattern_key": ARTICLE_PATTERN_KEY, "outcome": "correct"}]}
    )
    await process_analysis(
        db_pool, fake_claude(retry_response), await _claim(db_pool)
    )

    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "select next_review_at from error_patterns where pattern_key = $1", ARTICLE_PATTERN_KEY
        )
        said_at = await conn.fetchval("select created_at from utterances where id = $1", retry.id)
        outcome = await conn.fetchval(
            "select outcome from pattern_attempts where utterance_id = $1", retry.id
        )
        stages = await conn.fetch(
            "select review_stage, status from review_tasks where pattern_id = "
            "(select id from error_patterns where pattern_key = $1)",
            ARTICLE_PATTERN_KEY,
        )
    assert outcome == "correct"
    assert row["next_review_at"] == said_at + timedelta(days=3)
    assert [(s["review_stage"], s["status"]) for s in stages] == [(2, "pending")]


@pytest.mark.asyncio
async def test_reanalysing_the_same_utterance_does_not_double_advance(
    db_pool: asyncpg.Pool, committed_session: Any, fake_claude: Any
):
    """AS10 + 멱등 — job은 재시도된다. 두 번 분석해도 단계가 두 칸 오르지 않는다."""
    await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    await process_analysis(
        db_pool, fake_claude(_response(default_finding())), await _claim(db_pool)
    )
    retry = await _save(db_pool, committed_session.session_id, OFFICE_ANSWER)
    retry_response = json.dumps(
        {"findings": [], "attempts": [{"pattern_key": ARTICLE_PATTERN_KEY, "outcome": "correct"}]}
    )

    first_job = await _claim(db_pool)
    await process_analysis(db_pool, fake_claude(retry_response), first_job)
    async with db_pool.acquire() as conn:
        after_first = await conn.fetchval(
            "select next_review_at from error_patterns where pattern_key = $1", ARTICLE_PATTERN_KEY
        )
        # 같은 발화를 다시 분석 대상으로 만든다 (재시도가 남긴 상태를 흉내낸다)
        await conn.execute(
            "insert into analysis_jobs (job_type, utterance_id) values ('analyze_utterance', $1)",
            retry.id,
        )
    await process_analysis(
        db_pool, fake_claude(retry_response), await _claim(db_pool)
    )

    async with db_pool.acquire() as conn:
        after_second = await conn.fetchval(
            "select next_review_at from error_patterns where pattern_key = $1", ARTICLE_PATTERN_KEY
        )
        attempt_count = await conn.fetchval(
            "select count(*) from pattern_attempts where utterance_id = $1", retry.id
        )
    assert after_second == after_first
    assert attempt_count == 1


@pytest.mark.asyncio
async def test_an_unknown_attempt_key_does_not_fail_the_analysis(
    db_pool: asyncpg.Pool, committed_session: Any, fake_claude: Any
):
    """부가 신호 하나가 그 발화의 교정 전체를 태우지 않는다 (Task 3의 비대칭)."""
    utterance = await _save(db_pool, committed_session.session_id, GYM_ANSWER)
    response = json.dumps(
        {
            "findings": [default_finding()],
            "attempts": [{"pattern_key": "hallucinated_key", "outcome": "correct"}],
        }
    )
    job = await _claim(db_pool)

    await process_analysis(db_pool, fake_claude(response), job)

    async with db_pool.acquire() as conn:
        occurrences = await conn.fetchval(
            "select count(*) from error_occurrences where utterance_id = $1", utterance.id
        )
        attempts = await conn.fetchval("select count(*) from pattern_attempts")
        status = await conn.fetchval("select status from analysis_jobs where id = $1", job.id)
    assert occurrences == 1  # 교정은 정상 저장됐다
    assert attempts == 0  # 판정만 버려졌다
    assert status == "done"
```

`tests/integration/test_pipeline.py`의 import에 `from datetime import timedelta`를 더한다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest ../../tests/integration/test_pipeline.py -q -c pyproject.toml
```
기대: 신규 4건 red (`next_review_at`이 여전히 null, `pattern_attempts` 0행).
기존 테스트는 전부 green이어야 한다 — 하나라도 red면 Task 2·3이 무회귀를 깼다는 뜻이므로 먼저 그것을 본다.

- [ ] **Step 3: 배선한다**

`app/backend/app/services/analysis.py`의 import에 추가:

```python
from app.services.review import recompute, store_attempts
```

`_replace_occurrences`의 본문을 아래로 바꾼다:

```python
    removed = await conn.fetch(_DELETE_OCCURRENCES_SQL, utterance_id)
    touched: set[UUID] = {record["pattern_id"] for record in removed}

    for finding in result.findings:
        touched.add(await _store_finding(conn, utterance_id, user_id, finding))

    # 설계서 §9 Dependency: **정답 여부가 먼저 기록되고 그 다음 갱신이다.** 같은 트랜잭션
    # 안에서 처리한다 — 판정과 그에 따른 단계가 갈라지면 절반만 반영된 상태가 남는다.
    touched |= await store_attempts(conn, utterance_id, user_id, result.attempts)

    for pattern_id in touched:
        await conn.execute(_RECOUNT_PATTERN_SQL, pattern_id)
        # frequency·last_seen_at 재계산 **다음**이다: 복습 상태는 같은 이력을 다시 세므로
        # 순서를 뒤집으면 한 턴 낡은 값 위에서 단계를 정한다.
        await recompute(conn, pattern_id)

    if not await complete(conn, job.id, job.lease_token):
        raise _LeaseLost
```

⚠️ **`_LeaseLost` 경로를 건드리지 말 것.** lease를 잃은 워커의 복습 갱신도 함께 롤백되어야 한다 —
`complete`를 마지막에 두는 기존 구조가 그것을 보장한다(모듈 docstring 3번째 항목).

- [ ] **Step 4: 통과를 확인한다 + 순환 import 확인**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
```
기대: **+4건 → 431 passed**. `services/review.py`는 `services/analysis.py`를 import하지
않으므로 순환은 생기지 않는다 — `ty check`가 통과하는 것으로 확인한다.

```bash
git add app/backend/app/services/analysis.py tests/integration/test_pipeline.py
git commit -m "feat: 분석 결과 저장이 재시도 판정과 복습 상태를 함께 반영한다"
```

---

## Task 6: `services/chronic.py` — 만성 지표 조회 (§6.1)

읽기 전용이다. **쓰기 함수를 두지 않는다** — 이 표를 만드는 안은 설계서 §6.1에서 YAGNI로 기각됐다
(조회 시 계산).

**Files:**
- Create: `app/backend/app/services/chronic.py`
- Test: `tests/unit/test_chronic.py` (신규)

**Interfaces:**
- Consumes: 기존 `error_patterns` · `error_occurrences` · `utterances` · `users.timezone`
- Produces: `ChronicMetric` 데이터클래스와
  `async load_chronic_metrics(conn, user_id: UUID) -> list[ChronicMetric]` — ⚠️ 시그니처는 **한 줄**로 쓴다
  (95자라 `line-length = 100`에서 `ruff format`이 3줄 버전을 한 줄로 접는다 — 2026-09-03 직접 확인).
  슬라이스 2의 계획 생성이 이 함수를 호출해 Claude 입력을 만든다

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_chronic.py` (신규):

```python
"""만성 지표 — 설계서 §6.1. 숫자는 계산, 판정은 Claude(§6.2)라서 이 모듈은 사실만 돌려준다.

세 가지를 단정한다: **지속 기간이 음수가 되지 않는다**(§6.1 함정), 휴면 후 재발의 최대 공백,
그리고 **재발 일수가 사용자 타임존 기준**이라는 것(함정 H-S).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID

import asyncpg
import pytest

from app.services.chronic import load_chronic_metrics

USER_ID = UUID("00000000-0000-0000-0000-000000000001")
PATTERN_KEY = "article_missing_before_place_noun"

_SEQ = iter(range(1, 10_000))


async def _seed(conn: asyncpg.Connection) -> tuple[UUID, UUID]:
    await conn.execute(
        "insert into users (id, display_name, timezone, current_level) "
        "values ($1, 'Chronic Test', 'Asia/Seoul', 'A2')",
        USER_ID,
    )
    session_id = await conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        USER_ID,
    )
    pattern_id = await conn.fetchval(
        "insert into error_patterns (user_id, category, pattern_key, target_form) "
        "values ($1, 'article', $2, 'go to the + 장소 명사') returning id",
        USER_ID,
        PATTERN_KEY,
    )
    return session_id, pattern_id


async def _said_wrong(
    conn: asyncpg.Connection, session_id: UUID, pattern_id: UUID, at: datetime
) -> None:
    """지정한 시각에 그 패턴의 오류를 1건 말했다 — 발화 + occurrence 한 벌."""
    utterance_id = await conn.fetchval(
        "insert into utterances (session_id, speaker, transcript, sequence_no, created_at) "
        "values ($1, 'user', 'I go to gym.', $2, $3) returning id",
        session_id,
        next(_SEQ),
        at,
    )
    await conn.execute(
        "insert into error_occurrences "
        "(utterance_id, pattern_id, original_span, correction, explanation, severity, confidence) "
        "values ($1, $2, 'go to gym', 'go to the gym', '정관사가 필요합니다.', 'medium', 0.9)",
        utterance_id,
        pattern_id,
    )


# ① AS2 — 지속 기간이 **음수가 되지 않는다**. error_patterns.created_at을 시작으로 쓰면
#    라이브 DB에서 -3.8초가 나왔다(§6.1 실측 함정). 발화 시각의 min/max로만 계산한다.
@pytest.mark.asyncio
async def test_span_uses_utterance_times_and_never_goes_negative(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    first = datetime.fromisoformat("2026-06-01T12:00:00+09:00")
    last = datetime.fromisoformat("2026-09-01T12:00:00+09:00")
    await _said_wrong(db_conn, session_id, pattern_id, first)
    await _said_wrong(db_conn, session_id, pattern_id, last)

    metrics = await load_chronic_metrics(db_conn, USER_ID)

    assert len(metrics) == 1
    metric = metrics[0]
    assert metric.first_seen == first
    assert metric.last_seen == last
    assert metric.span == last - first
    assert metric.span > timedelta(0)


# ② AS2 — 휴면 후 재발. 40일 공백이 가장 위험한 신호다(§6.1)
@pytest.mark.asyncio
async def test_max_gap_finds_the_dormant_period(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    base = datetime.fromisoformat("2026-06-01T12:00:00+09:00")
    for offset_days in (0, 1, 41, 42):  # 1일 → 40일 공백 → 1일
        await _said_wrong(db_conn, session_id, pattern_id, base + timedelta(days=offset_days))

    metrics = await load_chronic_metrics(db_conn, USER_ID)

    assert metrics[0].max_gap == timedelta(days=40)


# ③ 발생이 1건이면 공백이 없다 — lag()의 첫 행은 null이다
@pytest.mark.asyncio
async def test_max_gap_is_none_for_a_single_occurrence(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    await _said_wrong(
        db_conn, session_id, pattern_id, datetime.fromisoformat("2026-06-01T12:00:00+09:00")
    )

    metrics = await load_chronic_metrics(db_conn, USER_ID)

    assert metrics[0].max_gap is None


# ④ **함정 H-S** — 재발 일수는 사용자 타임존의 달력 날짜다. 같은 KST 날짜에 속한 두 발화를
#    UTC로 세면 2일이 된다(2026-09-03 실측). 이 한 칸에 복습 주기·일일 계획이 걸린다.
@pytest.mark.asyncio
async def test_recurring_days_counts_calendar_days_in_the_user_timezone(
    db_conn: asyncpg.Connection,
):
    session_id, pattern_id = await _seed(db_conn)
    # 둘 다 KST 2026-09-02이지만 UTC로는 09-01과 09-02로 갈린다
    await _said_wrong(
        db_conn, session_id, pattern_id, datetime.fromisoformat("2026-09-02T08:00:00+09:00")
    )
    await _said_wrong(
        db_conn, session_id, pattern_id, datetime.fromisoformat("2026-09-02T23:30:00+09:00")
    )

    metrics = await load_chronic_metrics(db_conn, USER_ID)

    assert metrics[0].recurring_days == 1, "UTC로 셌다 — users.timezone을 쓰지 않았다 (H-S)"
    assert metrics[0].frequency == 0, "frequency는 분석 워커가 재계산한다 — 이 쿼리는 읽기만 한다"


# ⑤ 발생이 없는 패턴은 목록에 없다 — 만성 지표는 실제 발생에서만 나온다
#    (번호가 ⑥·⑦보다 앞이지만 파일 안 순서는 그대로 둔다)
@pytest.mark.asyncio
async def test_a_pattern_without_occurrences_is_absent(db_conn: asyncpg.Connection):
    await _seed(db_conn)

    assert await load_chronic_metrics(db_conn, USER_ID) == []


# ⑥ **AS2 전체** — "서로 다른 4개 날짜 · 약 3개월 지속 · 40일 공백"을 한 번에 단정한다.
#    조각별로만 보면 recurring_days·recurring_sessions가 아무 테스트에도 걸리지 않는다.
#    간격을 40·30·20일로 잡아 합이 90일(≈3개월)이면서 최대 공백이 40일이 되게 한다.
@pytest.mark.asyncio
async def test_as2_counts_days_sessions_span_and_gap_together(db_conn: asyncpg.Connection):
    session_id, pattern_id = await _seed(db_conn)
    second_session = await db_conn.fetchval(
        "insert into learning_sessions (user_id, mode) values ($1, 'speaking') returning id",
        USER_ID,
    )
    base = datetime.fromisoformat("2026-06-01T12:00:00+09:00")
    await _said_wrong(db_conn, session_id, pattern_id, base)
    await _said_wrong(db_conn, session_id, pattern_id, base + timedelta(days=40))
    await _said_wrong(db_conn, second_session, pattern_id, base + timedelta(days=70))
    await _said_wrong(db_conn, second_session, pattern_id, base + timedelta(days=90))

    metric = (await load_chronic_metrics(db_conn, USER_ID))[0]

    assert metric.recurring_days == 4
    assert metric.recurring_sessions == 2
    assert metric.span == timedelta(days=90)
    assert metric.max_gap == timedelta(days=40)


# ⑦ 사용자가 없으면 타임존의 SoT가 없다 — 조용히 UTC로 떨어지지 않고 실패한다
@pytest.mark.asyncio
async def test_missing_user_raises_instead_of_defaulting_the_timezone(
    db_conn: asyncpg.Connection,
):
    with pytest.raises(LookupError):
        await load_chronic_metrics(db_conn, UUID("00000000-0000-0000-0000-0000000000ff"))
```

**기대값은 실측이다 (2026-09-04, 롤백 트랜잭션).** 위 ⑥과 ④의 숫자를 정하기 전에 `_METRICS_SQL`을
dev DB의 실제 표에 걸어 확인했다 — 구현자는 이 값을 그대로 기대값으로 쓴다:

| 확인한 것 | 결과 |
|---|---|
| 간격 40·30·20일로 4회 발생(세션 2개) | `recurring_days=4` · `recurring_sessions=2` · `span=90 days` · `max_gap=40 days` |
| 같은 KST 날짜의 두 발화 | `tz='Asia/Seoul'` → **1** · `tz='UTC'` → **2**. ④가 실제로 H-S를 잡는다 |
| `span > 0` | true — `error_patterns.created_at`을 쓰지 않으므로 음수가 나올 수 없다 |
| `frequency` | `0` — 이 쿼리는 그 값을 읽기만 한다. 재계산은 분석 워커의 몫이다 |

- [ ] **Step 2: 실패를 확인한다**

```bash
cd app/backend && .venv/bin/pytest ../../tests/unit/test_chronic.py -q -c pyproject.toml
```
기대: **7건 전부 red** — `ModuleNotFoundError: app.services.chronic`.

- [ ] **Step 3: 모듈을 만든다**

`app/backend/app/services/chronic.py` (신규):

```python
"""만성 약점 지표 — 조회 시 계산 (설계서 §6.1).

**읽기 전용이다.** 롤업 테이블을 두는 안은 설계서 §6.1에서 기각됐다 — 단일 사용자 규모에서
결과가 같고 갱신 시점·신선도 관리만 늘어난다(YAGNI). 그래서 이 모듈에 쓰기 함수가 없다.

두 가지가 이 쿼리의 존재 이유다.

* **지속 기간을 `error_patterns.created_at`으로 계산하지 않는다.** 라이브 DB에서
  `last_seen_at - created_at`이 **음수(-3.8초)** 로 나왔다(§6.1 실측) — 패턴 행의 insert
  시각과 발화 시각이 다른 출처이기 때문이다. 지속 기간은 발화 시각의 min/max로만 낸다.
* **재발 일수는 사용자 타임존의 달력 날짜다.** UTC로 세면 KST 자정 전후의 두 발화가 2일로
  갈린다(함정 H-S, 2026-09-03 실측). 타임존의 SoT는 `users.timezone` **컬럼**이고, 호스트
  시각이나 세션 기본값이 아니다 — 그래서 이 함수가 그 값을 먼저 읽는다.

**만성 여부를 판정하지 않는다** (§6.2) — 임계값을 발명하지 않고 사실만 돌려준다. 판정은
Claude가 하고, 그 호출은 슬라이스 2의 계획 생성이 소유한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

import asyncpg

_TIMEZONE_SQL = "select timezone from users where id = $1"

# `lag()`로 인접 발생의 간격을 내고 그 최대값을 취한다 — frequency=5가 하루에 몰린 것과
# 3개월에 흩어진 것은 완전히 다르고, 그중 **한동안 사라졌다가 다시 나온 것**이 가장
# 위험한 신호다(§6.1). 발생이 1건이면 prev_at이 없어 공백은 null이 된다.
_METRICS_SQL = """
with occurrence as (
      select eo.pattern_id, eo.id as occurrence_id, u.session_id, u.created_at
        from error_occurrences eo
        join utterances u on u.id = eo.utterance_id
        join error_patterns p on p.id = eo.pattern_id
       where p.user_id = $1
),
gap as (
      select pattern_id, max(created_at - prev_at) as max_gap
        from (
               select pattern_id, created_at,
                      lag(created_at) over (
                        partition by pattern_id order by created_at, occurrence_id
                      ) as prev_at
                 from occurrence
             ) windowed
       where prev_at is not null
       group by pattern_id
)
select p.id                                                        as pattern_id,
       p.pattern_key,
       p.category,
       p.frequency,
       p.mastery_score,
       p.next_review_at,
       count(distinct o.session_id)                                as recurring_sessions,
       -- 달력 날짜는 사용자 타임존으로 센다 (함정 H-S). current_date를 쓰지 않는다.
       count(distinct (o.created_at at time zone $2)::date)         as recurring_days,
       min(o.created_at)                                           as first_seen,
       max(o.created_at)                                           as last_seen,
       max(o.created_at) - min(o.created_at)                        as span,
       g.max_gap
  from error_patterns p
  join occurrence o on o.pattern_id = p.id
  left join gap g on g.pattern_id = p.id
 where p.user_id = $1
 group by p.id, g.max_gap
 order by p.pattern_key
"""


@dataclass(frozen=True, slots=True)
class ChronicMetric:
    """패턴 하나의 만성 지표 — 전부 사실이고, 판정은 들어 있지 않다(§6.2)."""

    pattern_id: UUID
    pattern_key: str
    category: str
    frequency: int
    mastery_score: float
    next_review_at: datetime | None
    recurring_sessions: int
    recurring_days: int
    first_seen: datetime
    last_seen: datetime
    span: timedelta
    max_gap: timedelta | None


async def load_chronic_metrics(conn: asyncpg.Connection, user_id: UUID) -> list[ChronicMetric]:
    """이 학습자의 패턴별 만성 지표. 발생이 0건인 패턴은 포함되지 않는다.

    타임존을 `users.timezone`에서 **읽어서** 쿼리에 넘긴다. 사용자가 없으면 그 SoT가 없으므로
    조용히 UTC로 떨어지지 않고 `LookupError`를 올린다 — 조용한 폴백은 재발 일수를 하루씩
    어긋나게 만들고, 그 오차는 복습 주기와 일일 계획으로 번진다(H-S).
    """
    timezone = await conn.fetchval(_TIMEZONE_SQL, user_id)
    if timezone is None:
        raise LookupError(f"user {user_id} not found — no timezone source of truth")

    records = await conn.fetch(_METRICS_SQL, user_id, timezone)
    return [
        ChronicMetric(
            pattern_id=record["pattern_id"],
            pattern_key=record["pattern_key"],
            category=record["category"],
            frequency=record["frequency"],
            mastery_score=float(record["mastery_score"]),
            next_review_at=record["next_review_at"],
            recurring_sessions=record["recurring_sessions"],
            recurring_days=record["recurring_days"],
            first_seen=record["first_seen"],
            last_seen=record["last_seen"],
            span=record["span"],
            max_gap=record["max_gap"],
        )
        for record in records
    ]
```

- [ ] **Step 4: 통과 확인 + 게이트 + 커밋**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
```
기대: **+7건 → 438 passed**.

```bash
git add app/backend/app/services/chronic.py tests/unit/test_chronic.py
git commit -m "feat: 만성 지표를 조회 시 계산한다 (재발 일수는 사용자 타임존 기준)"
```

---

## Task 7: 문서 정합화 — 코드가 문서를 앞서가지 않게 한다

**Files:**
- Modify: `docs/database-schema.md` (`pattern_attempts` 정의 + `error_occurrences`에 컬럼 1행)
- Modify: `docs/design/2026-08-25-learning-coach-agent-design.md` (§8.4 번호 · AS9 · 캡틴 결정 2건)
- Modify: `TASKS.md` C절 (슬라이스 1 상태) · `handoff/HANDOFF.md` (다음 한 걸음 = 슬라이스 2)

**Interfaces:** 코드 변경 없음. 테스트도 없다 — **C 트랙(문서)이라 TDD 대상이 아니다.**

- [ ] **Step 1: `docs/database-schema.md`에 006을 반영한다**

`### 아직 SQL에 없는 테이블` **앞**에 `pattern_attempts` 절을 넣는다 — D-5가 같은 자리에
`pronunciation_attempts`를 넣었을 때 `git diff -U0`이 순수 삽입(`@@ -218,0 +219,48 @@`)이었고,
살아 있는 줄 인용이 하나도 밀리지 않았다. 같은 방식을 쓴다. 넣을 내용:

- 컬럼 6개(`id`·`pattern_id`·`utterance_id`·`outcome`·`created_at`·unique)와 그 뜻
- **`pronunciation_attempts`와의 차이**: 이 표는 발화 1건이 유일한 근거라 cascade이고
  `pending` 상태가 없다. 그 표는 tool 이벤트만으로도 행이 생겨 set null이고 `pending`이 정식 값이다
- **`error_patterns.mastery_score`의 두 번째 writer가 아니라 유일한 writer**라는 사실 —
  `frequency`가 writer 둘(문법 occurrence 수 / 발음 시도 수, G-8)인 것과 대비된다

`error_occurrences` 절에 `suggested_contexts jsonb` 1행을 더하고 "nullable · 길이 CHECK 없음 ·
없음은 null 하나"를 적는다. ⚠️ **이 문서를 줄 번호로 인용하지 않는다** (함정 H-H — 줄 단위
인용이 실제로 깨진 전례가 있고, `:111`·`:161`은 지금도 어긋나 있다).

- [ ] **Step 2: 설계서를 정정한다 (H-N 표의 근거를 정본에 되돌린다)**

같은 파일 안에서 **한 줄 → 한 줄** 교체를 원칙으로 하고, `git diff -U0`의 `@@ -N +N @@`를 확인한다.

1. **§8.4** — "002_learning_coach.sql로 쌓는다"를 006으로 고치고, 002가 만들어진 적이 없다는
   실측(파일·git 이력 각 0건)과 슬라이스 2가 007을 쓴다는 것을 적는다.
2. **§9 Dependency** — "002 마이그레이션 → 폴백 뱅크 시드 → 워커 기동"의 번호를 006으로 고친다.
3. **AS9** — "⚠️ 이 컬럼은 아직 없다"를 "✅ 006이 신설했고 저장 경로가 관통했다(Task 2)"로 바꾼다.
4. **§4.1** — 재발 시 상위 단계 행을 **삭제**한다는 캡틴 결정(2026-09-03)과 그 근거
   (`unique(pattern_id, review_stage)`, 이력은 `pattern_attempts`·`error_occurrences`에 남는다)를 적는다.
5. **§4.1 / §7** — `mastery_score`는 **상태 마커**(완주 100 / 재발 0)라는 캡틴 결정을 적고,
   §3.2와 충돌하지 않는 이유(중간값을 만들지 않아 발명한 임계값이 0개)를 함께 남긴다.
6. **§6.2** — "3단계 소진 후 재발" 신호는 `pattern_attempts`에서 재계산되며 **슬라이스 2가
   계산해 Claude에 넘긴다**는 것을 적는다 (슬라이스 1이 `mastery_score`를 0으로 되돌려도
   정보가 사라지지 않는 근거).

- [ ] **Step 3: 원장과 handoff를 갱신한다**

- `TASKS.md` C절 표: `계획 문서 작성` → ✅ (이 계획서 경로를 적는다) · `슬라이스 1` → ✅ ·
  `슬라이스 2` → ⏭. §11의 "착수 전 실측"에서 이제 거짓이 된 항목을 **지우지 않고 해소 표시**한다
  (`next_review_at`·`mastery_score` 앱 참조 0곳 → 이제 `services/review.py`가 유일한 writer).
- `handoff/HANDOFF.md`: "다음 한 걸음"을 **§11 슬라이스 2**로 바꾸고, 「되는 것 / 안 되는 것」 표에서
  "복습 큐·주기 갱신 — 컬럼은 있고 앱 참조 0곳"을 **되는 것**으로 옮긴다. 실측값 표의 테스트 수와
  dev DB 행 수를 **그 턴에 직접 돌려** 갱신한다.

- [ ] **Step 4: 커밋**

```bash
git add docs/ TASKS.md handoff/HANDOFF.md
git commit -m "docs: 006과 복습 재계산을 문서에 반영 — 슬라이스 1 완료 [skip ci]"
```

`docs:` 접두어이므로 `[skip ci]`가 허용된다.
⚠️ **2026-09-09 경로 정정** — 이 허용을 정한 `rules/code-development-principles.md` §2 는 **삭제됐고
상시 로드 규칙에 후계가 없다**(직접 확인: `~/.claude` 의 `CLAUDE.md`·`AGENTS.md`·`rules/`·`docs/` 에
`skip ci` 가 0건이고 `backups/rules-2026-09-09/code-development-principles.md` 에만 남았다).
⛔ **이 리포에서는 그 태그가 애초에 동작상 무의미하다** — 근거는 `docs/ops/pitfalls.md` 의 **H-AQ** 다.

---

## 실물 검증 — 자동 테스트로 판정할 수 없는 것 2건

둘 다 **캡틴 승인 후에** 한다. 자동 테스트는 대역(`FakeClaudeClient`)을 쓰므로
"실제 모델이 그 필드를 내는가"와 "실물 DB에 마이그레이션이 적용되는가"를 증명하지 못한다.

| # | 무엇 | 어떻게 | 판정 |
|--:|---|---|---|
| L1 | 실물 dev DB에 006 적용 | `app/backend/.venv/bin/python scripts/migrate.py` 후 `schema_migrations`에 `006_...` 1행과 `information_schema`의 컬럼·표 확인 | 되돌리기 어려운 조작 — **캡틴 승인 필수** |
| L2 | 실물 Claude가 `suggested_contexts`·`attempts`를 실제로 내는가 | 마이크 회차나 W-live와 같은 방식으로 1턴 왕복 후 `error_occurrences.suggested_contexts`가 null이 아닌지 확인 | 사람이 판정한다(§10.1 AS-live와 같은 방식). null만 온다면 프롬프트 문구를 고친다 — **코드는 이미 옳다** |

L2가 이 슬라이스의 진짜 위험이다. 컬럼과 저장 경로가 옳아도 모델이 필드를 내지 않으면
값은 영원히 null이고, **그 사이의 데이터는 소급이 불가능하다**(§8.2). 그래서 L2를 슬라이스 2
착수 전에 한 번은 돌린다.

---

## 4 Lenses — 이 계획이 새로 만드는 계약

설계서 §9가 슬라이스 1·2를 함께 본 것이라, 여기서는 **이 계획이 새로 도입하는 것**만 적는다.

**Contract** — `fold_stages`는 순수 함수이고 전제조건은 `correct_times`가 **발화 시각 오름차순**인 것이다
(`_HISTORY_SQL`의 `array_agg(... order by ...)`가 그것을 보장한다 — 정렬을 지우면 단계가 조용히 틀린다).
`recompute(conn, pattern_id)`의 사후조건: 그 패턴의 `next_review_at`·`mastery_score`가
이력과 일치하고 `review_tasks`가 0행 또는 1행이다. 전제조건: 호출자가 트랜잭션을 열었고, 같은
트랜잭션에서 `pattern_attempts` 저장이 **먼저** 끝났다. `store_attempts`는 건드린 pattern_id를
빠짐없이 돌려준다 — 이것을 어기면 단계가 낡은 채 남는다.

**Boundary** — ① Claude 출력(JSON) → `attempts`·`suggested_contexts`: `extra="forbid"` + `Literal`로
006 CHECK와 같은 집합만 통과시킨다. ② 파이썬 ↔ jsonb: asyncpg는 `str`만 받는다(실측) — 이 경계를
틀리면 런타임 `DataError`다. ③ 시간: 간격은 `interval`(tz 무관), 달력 날짜는 `users.timezone`
(H-S). ④ 학습/명령: 재시도 판정도 `utterance_type='learning'` 발화에서만 나온다 — 기존 묶음
정의를 그대로 쓰므로 새 경계가 아니다.

**Failure** — ① 미매치 `pattern_key`: attempts는 **버리고** findings는 **실패시킨다**(비대칭이
의도다 — Task 3의 근거). ② lease 상실: `complete`가 마지막이라 복습 갱신까지 함께 롤백된다.
③ 모델이 필드를 안 냄: `suggested_contexts`는 null, `attempts`는 `[]` — 둘 다 정상 경로이고
단계가 멈출 뿐 깨지지 않는다. ④ 패턴이 사라짐: `store_attempts`가 0행을 관측해 건너뛴다.

**Dependency** — 초기화 순서는 **006 적용 → 워커 기동**이다(폴백 뱅크 시드는 슬라이스 2의 것).
모듈 방향은 `analysis.py → review.py` 한 방향이고 역참조가 없다 — `review.py`는 `models.analysis`의
`PatternAttempt`만 import한다. `chronic.py`는 아무도 import하지 않는다(슬라이스 2의 소비자를 기다린다).

---

## Self-Review

**1. Spec coverage** — 슬라이스 1의 4개 항목: `suggested_contexts` 저장 → Task 1·2 ·
`pattern_attempts` → Task 1·3·4 · 복습 스케줄 갱신(§4.1) → Task 4·5 · 만성 지표 쿼리(§6.1) → Task 6.
AC: **AS9**는 저장(Task 2)과 **재분석 후 최신 값 유지**(Task 2의 replace 테스트) 둘 다 덮는다 —
남는 것은 "모델이 실제로 그 필드를 낸다"뿐이고 그것은 자동 테스트로 판정 불가라 L2다.
**AS10** 멱등은 Task 4 ⑯과 Task 5의 재분석 테스트. **AS2**는 Task 6 ①(음수 span 금지)·②(최대 공백)·
**⑥(4개 날짜·2개 세션·3개월·40일 공백을 한 번에)** 가 덮는다.
**슬라이스 1에 없는 것**: AS1·AS3~AS8·AS-live는 계획 생성·지시문·수준 적응을 요구하므로 전부 슬라이스 2다.
§6.2의 "3단계 소진 후 재발" 신호도 슬라이스 2로 넘긴다(§12.1이 슬라이스 1에 §6.1만 배정했다).

**2. Placeholder scan** — TODO·"적절히 처리"·"위와 유사" 없음. 모든 코드 단계에 실제 코드가 있다.
단 두 곳이 **의도적으로** 지시문이다: Task 2 Step 6의 job claim 헬퍼 이름(그 파일의 기존 형태를
따르라고 명시했다)과 Task 7 전체(문서 편집이라 코드 블록이 없다).

**3. Type consistency** — `STAGE_DAYS`는 `review.py` 한 곳에만 있다. ⚠️ **정정(2026-09-04)**:
접기가 파이썬으로 옮겨져 ~~SQL이 `$2::int[]`로 받는다~~는 서술은 폐기됐다 — SQL에는 `1,3,7`이
아예 없다(그래서 이 항목이 더 강하게 참이다). `stage`는 **1-based**이고 파이썬 인덱스는
`STAGE_DAYS[stage - 1]`이다.
`FINAL_STAGE = len(STAGE_DAYS) = 3`이 `review_tasks.review_stage between 1 and 3`과 맞는다.
`AttemptOutcome` Literal 3값 = 006 `outcome` CHECK 3값. `recompute`·`store_attempts` 이름이
Task 4 정의와 Task 5 호출에서 일치한다. `mastery_score`는 `numeric(5,2)`이므로 `Decimal`로 바인딩하고
(`float`는 asyncpg가 거부한다 — `confidence`에서 같은 이유로 `Decimal(str(...))`을 쓴다)
읽을 때 `float()`로 좁힌다.

**2026-09-03 계획 검토에서 고친 것 (critic CHALLENGE → 반영)**

| 결함 | 무엇이 틀렸나 | 어떻게 고쳤나 |
|---|---|---|
| 완주 판정에 간격 조건이 없었다 | `correct`를 3번 세기만 해서 **같은 세션에서 3번 맞히면 1·3·7일을 한 번도 경과하지 않고 완주**했다. 간격 반복 자체가 무의미해진다 | 상태 함수를 `fold_stages`로 바꿨다 — 예정일을 넘긴 정답만 단계를 올린다. 완주까지 최소 11일이 실제로 경과한다. 회귀 방지 테스트 ④가 이것을 못 박는다 |
| `chronic.py` 시그니처가 `ruff format`에 걸렸다 | 3줄 시그니처가 95자라 한 줄로 접힌다 — Task 6 게이트가 그 자리에서 exit 1 | 한 줄로 고쳤다 (직접 `ruff format --check`로 확인) |
| 태스크별 기대 테스트 수가 전부 틀렸다 | 계획이 "줄어들면 멈추라"고 지시하는데 그 수치가 틀려서 없는 회귀를 조사하게 된다 | 델타 기준으로 다시 세어 6곳을 고쳤다 |
| 프롬프트가 목록을 "위"라고 가리켰다 | 목록은 그 절 **아래**에 온다. 기존 `_PATTERN_KEY_RULES`는 "아래"라고 쓴다 | "아래"로 고치고 `"위 [이 학습자의 기존 패턴]" not in prompt` 단정을 넣었다 |
| AS9의 후단이 안 덮였다 | "재분석 후에도 최신 값이 남는다"를 보는 테스트가 없었다 | Task 2에 replace 테스트 1건 추가 |
| AS2의 절반이 안 덮였다 | `recurring_days`·`recurring_sessions`를 아무 테스트도 보지 않았다 | Task 6에 ⑥ 추가 |
| 없는 헬퍼 이름을 썼다 | `_claim_only_job`은 그 파일에 없다. 실제 이름은 `_claim` | 전부 `_claim`으로 고쳤다 |

**미해결로 남기는 것 1건** — `review_tasks.task_type`은 `'rephrase'` 하나만 쓴다.
`'role_play'`·`'shadowing'`은 생성이 필요해 슬라이스 2 이후의 몫이다. 값역에는 남겨 둔다.
