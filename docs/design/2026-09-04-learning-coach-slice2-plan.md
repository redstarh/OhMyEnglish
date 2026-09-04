# 학습 코치 슬라이스 2 구현 계획 — 판단과 적용

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended)
> or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax
> for tracking.

**Goal:** 세션이 끝날 때 학습자의 오류 이력에서 **다음 세션 계획**을 미리 만들고, 다음 세션이 그 계획을
읽어 대화 상대의 지시문과 화면의 추천 이유에 실제로 반영한다 — 고정 시나리오 1개로 모든 세션을 돌리는
현재 동작을 끝낸다.

**Architecture:** 새 큐·새 워커를 만들지 않는다. 이미 도는 `analysis_jobs` 큐에 **job 종류 하나**
(`plan_next_session`)를 더하고, 세션 종료 기록과 **같은 트랜잭션**에서 등록한다. 워커가 그 job을 집으면
슬라이스 1이 만든 세 자산(복습 목록·만성 지표·발음 시도)을 읽어 Claude 1회 호출 → `session_plans` 1행 +
`learner_notes` 1행 + `users.current_level` 갱신을 **한 트랜잭션**으로 저장한다. 다음 세션 시작은 그 행을
읽기만 하고, 지시문은 **이미 있는 조립 지점**(`audio_gateway/factory.py`)을 넓혀 넘긴다 — 어댑터 포트는
건드리지 않는다.

**Tech Stack:** Python 3.13 · asyncpg · pydantic v2 · PostgreSQL 17.9 · pytest(asyncio_mode=auto) ·
ruff · ty · Next.js(App Router)/TypeScript. **슬라이스 1과 달리 프론트엔드를 건드린다** (추천 이유 표시).

**Spec:** `docs/design/2026-08-25-learning-coach-agent-design.md` (정본, 2026-08-27 승격) — 이 계획의 범위는
그 문서 **§12.1 결정 표의 2행**이다: 계획 생성 job · `session_plans` · `learner_notes` · 지시문 전달(§5.2) ·
수준 갱신(§7). 관련 수용 시나리오는 §10의 **AS1~AS8**과 신설 **AS11**(아래 Task 12).
**함께 읽어야 하는 문서**: `docs/consistency-audit-2026-09-04.md` — 이 계획이 닫는 어긋남 9건의 근거와
캡틴 결정 2건이 거기 있다.

---

## Global Constraints

모든 태스크의 요구사항에 아래가 암묵적으로 포함된다.

- **게이트는 `app/backend` cwd에서만 판정한다** (함정 H-A). 기준선(2026-09-04 직접 실행):
  `pytest -q` **454 passed** · `ruff check .` + `ruff format --check .` **29 files** · `ty check` **All checks passed**.
  프론트는 `app/frontend`에서 `npx tsc --noEmit`·`npx eslint app lib` 둘 다 exit 0.
  `tests/**`+`scripts/**`의 `ruff` **6 errors**·`format` **4 files**는 게이트 밖 베이스라인이다.
- **게이트를 `| tail`로 파이프하지 않는다** — exit code가 `tail`의 것이 되어 실패가 `&&`를 통과한다.
- **테스트 DB는 공유 자원이다**(함정 H-X) — 게이트를 겹쳐 돌리지 않는다. 매 실행이 `ohmyenglish_test`를
  DROP/CREATE한다. 게이트 전에 `brew services list | grep postgresql@17`로 DB가 떠 있는지 본다(함정 H-T) —
  안 떠 있으면 대량 errors가 나는데 **회귀가 아니라 연결 거부다.** 인스턴스는 En-Coach와 **공유**하므로
  재시작·`ALTER SYSTEM`·`ALTER DATABASE … SET TimeZone` 금지.
- **시각은 전부 `timestamptz`. naive datetime을 만들지 않는다.** 시간 기반 판정은 `now()`가 아니라
  **`clock_timestamp()`** 다 — `now()`는 트랜잭션 고정이라 한 트랜잭션 안에서 시간이 흐르지 않는다(설계서 §4.1).
  **달력 날짜**(재발 일수 등)는 `current_date`로 구하지 않고 `at time zone <users.timezone>`으로 변환한다
  (함정 **H-S** — UTC 자정~09:00 KST 구간에 하루 어긋난다). 타임존의 SoT는 **`users.timezone` 컬럼**이다.
- **증분 금지, 재계산.** 이 리포의 확립된 규약이다. 계획 생성도 같다 — 이전 계획을 읽어 수정하지 않고
  매번 이력에서 새로 만든다. 이유: job은 재시도되고, 증분은 재시도마다 밀린다.
- **임계값을 발명하지 않는다** (설계서 §3.2). 이 계획이 쓰는 수치는 전부 문서 근거가 있다:
  초점 패턴 **1~2개**(`docs/PRD.md:188` R11-2) · 질문 **3~5개**(같은 줄) · 최근 창 **14일**(설계서 §4.2,
  복습 최장 7일의 2배라는 유도값임이 그 절에 명시돼 있다) · 복습 **1·3·7일**(설계서 §4.1) ·
  CEFR 값역 **A1·A2·B1·B2·C1·C2**(`db/migrations/001_initial_schema.sql:18`) · 수준 이동 **한 단계**(설계서 §7).
  **그 밖의 수치를 새로 만들지 않는다.** 특히 지시문 크기 상한은 **정하지 않는다** — 설계서 §3.4가
  "Nova 초기화 시간을 실측해 정한다, 지금 발명하지 않는다"고 명시했고 그 실측은 이 계획의 범위가 아니다.
- **프롬프트 문구는 h-doc 프로필을 따른다**: 단문·단일 절 기준, 일상 → 업무 협업 순서, 학습자용 설명은 한국어.
  목표 수준(AWS 보고) 문형으로 예문을 만들지 않는다. **발음 채점을 하지 않는다**
  (`docs/requirements-summary.md:120-121` — 점수·등급·원어민 유사도 지표는 하지 않는 것).
- ⚠️ **테스트는 "왜 통과하는지"까지 확인한다** (Task 1·2에서 **연속 두 번** 나온 결함 부류다).
  통과하는 테스트가 의도한 것을 재고 있는지 반드시 따진다. 실제로 겪은 두 사례:
  ① 예외 **타입**만 단정해서 두 CHECK 중 어느 것이 걸렸는지 구분하지 못했다 → 마이그레이션 **전에도**
  초록이었다. ② 가드를 재는 테스트가 부분 유니크 인덱스에 가려져 **가드를 지워도 초록**이었다.
  **판별법**: 검증하려는 코드를 실제로 **지우거나 되돌려 red를 관측**하라. red가 안 나면 그 테스트는
  그 코드를 재지 않는 것이다. 관측한 red 출력을 보고서에 적는다.
- ⚠️ **주석·docstring은 참인 것만 말한다.** 이 리포는 슬라이스 1에서 "있지도 않은 순서 의존을 주석이
  단정했다"로 지적받았고, 이 계획에서도 낡은 서술이 **여러 건** 나왔다. 코드를 고칠 때 그 코드를
  설명하는 서술을 함께 본다. **거짓이 된 문구는 덧붙여 정정하지 말고 교체한다** — 요약줄 관행상
  IDE 툴팁·`help()`는 **첫 줄만** 보여주므로 아래에 경고를 붙이는 것으로는 오해가 남는다(Task 2 실측).
  같은 문구가 여러 파일에 있으면 **전부 grep해서** 함께 고친다(한 곳만 고치면 다음 작업자가 다른 쪽을 믿는다).
- **커밋은 conventional commits.** `feat:`/`fix:`에는 `[skip ci]`를 붙이지 않는다.
- **원장과 handoff는 커밋과 같은 리듬으로 갱신한다** — 태스크 완료마다 `TASKS.md` C절의 상태와
  `handoff/HANDOFF.md`의 "다음 한 걸음"을 함께 고친다.
- ⚠️ **`scripts/migrate.py`를 실물 dev DB에 돌리는 것은 캡틴 승인 후에 한다.** 스키마 변경 적용은
  되돌리기 어려운 조작이다. 테스트 DB(`ohmyenglish_test`)는 매 실행마다 재생성되므로 승인 대상이 아니다.
- ⚠️ **이 리포에는 git remote가 없다** — 푸시할 대상이 없다. `git remote -v`가 비어 있다.

---

## 구현 전 정정 — 착수 전에 이 표를 먼저 읽는다 (함정 H-N)

설계서를 그대로 믿고 구현하면 깨지는 자리들이다. **전부 2026-09-04에 직접 실행해 확인했다.**

| 설계서/문서의 서술 | 실측 | 이 계획이 쓰는 것 |
|---|---|---|
| §5.2 "`start()`가 인자를 못 받으니 `start(instruction: SessionInstruction)`으로 **포트를 확장한다**" (§9 Dependency·AS6도 이 전제) | `port.py:118` `async def start(self) -> None` — 인자 없음은 맞다. 그런데 지시문을 넣는 자리가 **이미 있다**: `factory.py:42`가 `NovaVoiceAdapter(settings, instructions=build_system_prompt(known_sounds))`로 생성자에 넘긴다. 조립 주체는 팩토리이고 `factory.py:31-36` docstring이 "소켓은 데이터만 넘기고 조립은 여기서 한다"를 G-3 근거로 못 박았다 | **캡틴 결정 2026-09-04: 기존 팩토리 경로를 확장한다.** `port.py` 무변경. 지시문 통로를 둘로 만들지 않는다. 설계서 §5.2·§9·AS6도 Task 12에서 정정 |
| §5.2 "고정부는 `docs/agent-system-prompt.md`(한 번에 질문 하나 · **65% 발화** · **교정 5단계** · **종료 형식**)" | 실제 어댑터가 받는 문구는 `nova.py`의 `SYSTEM_PROMPT`다. 그 4개 중 **3개가 없다** — `65%` 0건(코드의 65% 언급은 `nova.py:219` 주석), `one simple Korean sentence` 0건, `variations in different contexts` 0건, `Focus next time`·`preparation task` 각 0건. `nova.py:94-96`이 "Nova가 실제로 할 수 있는 부분만 옮긴다"고 스스로 적어 뒀다 | **얹는 대상은 `nova.py`의 실제 지시문이다.** 문서를 믿고 "이미 있다"고 가정하지 않는다. **65% 규칙은 Task 10에서 실제 지시문에 넣는다**(`docs/PRD.md:59` 요구사항인데 대화 상대가 모르고 있었다) |
| §5.2 가변부에 "**힌트를 얼마나 이르게 줄지**"를 담는다 | 그 지시가 **이미 고정돼 있다**: `nova.py:116`(긴 침묵 뒤에만 문장 시작 힌트), `nova.py:121`(막히면 정답 전체가 아니라 시작 힌트) | 가변부가 이 두 줄을 **대체한다**는 것을 지시문에 명시한다(Task 10). 명시하지 않으면 모순된 지시가 함께 나간다 |
| §8.1 `session_plans.instruction`은 `jsonb` | 어댑터가 받는 것은 문자열이다(`nova.py:444` `self.instructions = instructions or SYSTEM_PROMPT`). **jsonb → 문자열 변환 규칙이 어느 문서에도 없다** | 이 계획이 정한다: **저장은 구조화된 jsonb, 문장 조립은 읽는 쪽**(`build_system_prompt`)이 한다. Task 5가 형태를, Task 10이 조립을 소유한다 |
| §5.2 "스텁 어댑터는 지시문을 **받아서 기록만 한다**"·AS6 "스텁이 기록한 지시문에 값이 들어 있다" | `stub.py:40` `def __init__(self, mode: StubMode = "fixture") -> None:` — **지시문을 받는 인자 자체가 없다.** 오늘 AS6을 판정할 수단이 없다 | **Task 9가 그 자리를 만든다.** 2026-09-04 결정("실물 음성은 나중, 스텁 관통으로 검증")의 유일한 검증 수단이므로 필수다 |
| §3.1 "세션 종료와 **같은 트랜잭션**에서 job 등록" — 어디인지 미지정 | `sessions.py:83` `async def end_session(conn, session_id, status)`가 **연결을 받는 원시 함수**이고 docstring이 "종료 기록을 다른 쓰기와 한 트랜잭션으로 묶어야 하는 호출자가 있어서"라고 적었다. `sessions.py:100` `closed = await conn.fetchval(_END_SESSION_SQL, …)`이 **실제로 닫혔을 때만** id를 돌려준다(`and status = 'active'` 가드) | **`end_session` 안에서, `closed is not None`일 때만** 등록한다. 이미 닫힌 세션 재호출에서 job이 중복 등록되지 않는다 |
| §8.3 "`job_type`에 `plan_next_session`을 **추가**한다. 기존 CHECK와 partial unique 형태를 그대로 따른다" | `job_type` CHECK는 2값이고(`001:138`), 대상 컬럼 CHECK `analysis_jobs_target_matches_job_type`은 **2분기 OR**이다(`001:150-153`). 값만 늘리면 `session_id not null` 조합이 **거부된다**. partial unique `uq_analysis_jobs_pending_session`은 `(job_type, session_id)`로 **이미 있다**(`001:162`) | 007이 **CHECK 2개를 재작성**한다(값 3개 + 대상 3분기). **새 인덱스는 만들지 않는다** — 이미 있는 것이 그대로 덮는다 |
| §3.1 "워커가 claim → Claude 1회 호출" | `claim_next`의 `returning id, utterance_id, attempts`(`jobs.py:177`)에 **`job_type`·`session_id`가 없고** `ClaimedJob`에도 없다. 게다가 `analysis.py:489-494`가 `utterance_id is None`을 **즉시 실패**로 처리한다 → 오늘 계획 job을 넣으면 그 자리에서 `failed`가 된다 | Task 3이 `returning`·`ClaimedJob`에 두 필드를 더하고 워커를 **`job_type`으로 분기**시킨다. `utterance_id is None` 판정을 job_type 기준으로 교체한다 |
| §3.3 "`learning_scenarios`에서 학습자 **수준에 맞는** 행을 골라 시작한다" | 시드 3행이 **전부 `A2`·`daily_life`**(`scripts/migrate.py:34-48`). `current_level`이 `B1`로 올라가면 수준 일치가 **0행**이 된다 | 폴백은 **수준 일치 → 없으면 현재 동작(`order by created_at, id limit 1`)**. 새 시나리오를 발명해 시드하지 않는다 |
| §7 수준 갱신 근거는 "`pattern_attempts`의 정답률과 **발화 길이 추이**" | `pattern_attempts`는 문법·표현 전용이고 발음은 `pronunciation_attempts`에 쌓인다. 즉 **발음은 수준 판단에 안 들어간다** — 그런데 그 이유가 어디에도 없었다 | **캡틴 결정 2026-09-04: 지금은 넣지 않고 MVP 이후 재검토.** ⚠️ **영구 제외로 적지 마라** — 재검토가 예정된 이월이다. Task 12가 설계서 §11 이월에 그렇게 기록한다 |
| 머리말 "요구사항 근거: R11-1~10, **AC11-1~6**" (전부 커버한다고 선언) | **AC11-5·AC11-6이 설계서 어디에도 없다** — 리터럴 0건이고 수용 시나리오 11개에 발음을 다루는 것이 0건이다 | **AC11-6은 이 계획이 닫는다**(Task 12가 AS11을 신설). **AC11-5는 실물 음성 확인이 필요해 이 계획의 범위 밖이고**, Task 12가 그 미충족 사실을 설계서에 적는다 |
| §8.1 `session_plans.session_id`는 "FK → `learning_sessions`, **unique**(세션당 1개)"이고 §3.3은 "계획 미사용을 `session_plans` **부재**로 판별한다" | **어느 세션인지 정해져 있지 않다.** 계획은 세션 N이 끝날 때 만들어져 세션 N+1이 쓴다. 생성 시점에 N+1은 **존재하지 않으므로** 소비 세션 id를 넣을 수 없다 | **계획을 만든 세션(N)을 가리킨다.** 설계서 자신의 두 제약이 이 답을 강제한다: ① §8.1이 `not null` + `unique`를 요구하는데 소비 세션으로 읽으면 생성 시 null이어야 한다 ② §3.4가 **세션 시작은 조회 1회**라고 못 박았는데 소비 세션으로 읽으면 시작 시 UPDATE가 필요하다. 그래서 세션 시작은 "**직전 세션이 만든 계획**"을 조회한다. §3.3의 "부재"도 그렇게 읽는다. 소비 표시 컬럼을 **만들지 않는다** — 항상 최신 계획을 읽으므로 중복 소비가 실질 문제를 만들지 않고, 만드는 순간 §8.1에 없는 컬럼을 발명하는 것이 된다 |
| §12.1 "슬라이스 2는 **화면 변화가 없다**"는 암묵 전제 (슬라이스 1 계획서가 "프론트 수정 0건"을 제약으로 삼았다) | `docs/PRD.md:189`(R11-3)·`docs/requirements-summary.md:131`이 추천 이유를 **화면에서 볼 수 있어야 함**으로 요구한다. 화면 코드의 `reason`은 교정 이유·연결 실패 이유뿐이다 | **캡틴 결정 2026-09-04: 간략하게 표시한다.** Task 11이 조회 경로 1개 + 화면 한 줄을 만든다. **슬라이스 1의 "프론트 0건" 제약은 이어지지 않는다** |

⚠️ **다시 조사하지 말 것 2건** (알고 남긴 축소다):
1. **발음 패턴의 `next_review_at`은 영구히 null이고 `review_tasks` 행도 생기지 않는다.** 근거는
   설계서 §4.1 「구현이 채운 공백」 4번. 발음은 **§4.4의 별도 경로**로 계획 입력에 들어오므로 요구사항
   R11-9는 그 경로로 충족된다. **버그가 아니다.**
2. **`review_tasks` 행의 `id`·`created_at`은 재계산마다 새로 생기고 `status`가 덮인다.** 이 계획은
   `review_tasks`를 **읽지 않는다**(복습 목록은 `error_patterns` 기준의 `load_due_reviews`가 돌려준다).
   과제 id로 "완료 표시"를 하려면 그 전에 경계를 정해야 하지만 **이 계획의 범위가 아니다**(설계서 §11 이월).

---

## File Structure

| 파일 | 신규/수정 | 책임 |
|---|:--:|---|
| `db/migrations/007_learning_coach_slice2.sql` | 신규 | `session_plans`·`learner_notes` 표 2개 + `analysis_jobs` CHECK 2개 재작성. **그것만** |
| `app/backend/app/services/jobs.py` | 수정 | `JOB_TYPE_PLAN` 상수 · `enqueue_plan_next_session` · `claim_next`의 `returning`에 2필드 · `ClaimedJob`에 2필드 |
| `app/backend/app/services/sessions.py` | 수정 | `end_session`이 실제로 닫았을 때 계획 job을 **같은 연결로** 등록 · 폴백 시나리오 선택 SQL |
| `app/backend/app/workers/analysis_worker.py` | 수정 | job 종류로 분기 — 분석이면 기존 경로, 계획이면 새 경로 |
| `app/backend/app/services/plan_input.py` | 신규 | **계획 입력의 소유자** — 복습 목록·최근 창·만성 지표·발음 시도·만성 신호를 한 자료구조로 모은다. **읽기 전용** |
| `app/backend/app/services/review.py` | 수정 | 공개 함수 1개 추가 — "3단계를 완주한 뒤 재발했는가"를 판정한다(§6.2의 결정론적 만성 신호). **복습 상태의 소유자가 계속 review.py이므로** 이 판정을 plan_input에 복제하지 않는다 |
| `app/backend/app/models/plan.py` | 신규 | **Claude 출력 계약의 소유자** — 계획·관찰 노트·수준 판단 모델과 검증. `AnalysisValidationError`와 같은 방식 |
| `app/backend/app/services/plan.py` | 신규 | 프롬프트 조립 · Claude 1회 호출 · 저장 한 트랜잭션 · job 종결. `process_plan`이 진입점 |
| `app/backend/app/audio_gateway/stub.py` | 수정 | 지시문을 **받아서 보관**한다 (AS6의 유일한 검증 수단) |
| `app/backend/app/audio_gateway/nova.py` | 수정 | `build_system_prompt`가 계획 가변부를 함께 엮는다 · 실제 지시문에 65% 규칙 추가 |
| `app/backend/app/audio_gateway/factory.py` | 수정 | `create_voice_adapter`가 계획을 **데이터로** 받아 넘긴다 (조립은 계속 여기가 소유) |
| `app/backend/app/api/ws.py` | 수정 | 세션 시작이 준비된 계획을 읽어 팩토리에 넘긴다 |
| `app/backend/app/api/results.py` | 수정 | 준비된 계획의 추천 이유를 내려주는 조회 경로 1개 |
| `app/frontend/lib/api.ts` | 수정 | 그 조회 경로의 타입과 호출 함수 |
| `app/frontend/app/page.tsx` | 수정 | 시작 화면에 추천 이유 **한 줄** |
| `tests/unit/test_schema.py` | 수정 | 007 스키마 단정 (표·컬럼·CHECK·unique·cascade) |
| `tests/unit/test_jobs.py` | 수정 | 계획 job 등록·claim의 2필드·중복 방지 |
| `tests/unit/test_plan_input.py` | 신규 | 계획 입력 — 누락 없음(AS1)·타임존 경계·발음 pending 제외·만성 신호 |
| `tests/unit/test_plan_models.py` | 신규 | 출력 계약 거부 경계 (AS5) — 이유 빈값·질문 수·초점 수·CEFR 값역·두 단계 도약 |
| `tests/unit/test_plan.py` | 신규 | 프롬프트 문구 · 저장 트랜잭션 · 수준 한 단계 제약(AS7) · 노트 append(AS8) |
| `tests/unit/test_nova.py` | 수정 | 지시문에 계획 가변부·65% 규칙이 들어가고 힌트 대체가 명시되는지 |
| `tests/integration/test_plan_pipeline.py` | 신규 | 종단 — 세션 종료 → job → 계획 저장 → 다음 세션이 읽어 스텁 지시문에 도달(AS6)·폴백(AS4) |
| `tests/integration/test_ws.py` | 수정 | 세션 시작이 계획 유무에 따라 갈리는 것 |
| `docs/database-schema.md` | 수정 | 007이 만든 표 2개 정의 반영 |
| `docs/design/2026-08-25-learning-coach-agent-design.md` | 수정 | §5.2·§9·AS6 정정 · AS11 신설 · §7 이월 기록 · AC11-5 미충족 명시 |
| `tests/harness/` 스모크 단정 | 수정 | 슬라이스 2 산출물을 보는 단정 추가 |

**새 워커·새 큐를 만들지 않는다.** 계획 생성은 이미 도는 워커 루프가 job 종류로 분기해 처리한다.

---

### Task 1: 007 마이그레이션 — 표 2개 + CHECK 2개 재작성

**Files:**
- Create: `db/migrations/007_learning_coach_slice2.sql`
- Test: `tests/unit/test_schema.py` (수정)

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: 표 `session_plans`(컬럼 `id`·`session_id`·`focus_pattern_ids`·`questions`·`target_level`·`reason`·
  `instruction`·`source`·`created_at`) · 표 `learner_notes`(`id`·`user_id`·`note`·`window_from`·`window_to`·`created_at`) ·
  `analysis_jobs.job_type`이 `'plan_next_session'`을 받고 그 경우 `session_id not null and utterance_id is null`을 요구한다

**결정 기록 — `questions`·`instruction`의 jsonb 모양은 이 태스크가 정한다.** 설계서는 형식을 정하지 않았다.
`questions`는 `[{"prompt": str, "context": str}, …]`, `instruction`은
`{"target_level": str, "focus": [{"pattern_key": str, "target_form": str}], "sentence_length": str, "hint_timing": str, "contexts": [str]}`.
`sentence_length`·`hint_timing`은 **자유 문장 조각**이다 — 값역을 열거하면 설계서가 금지하는 임계값 발명이 되므로
비어 있지 않은 것만 검증하고 문장 조립은 Task 10이 한다. DB CHECK는 배열 길이만 본다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tests/unit/test_schema.py`의 표 목록 단정에 두 줄을 더하고, 새 테스트 4개를 추가한다.

```python
# 기존 test_001_migration_creates_expected_tables 의 집합에 추가
        # 007 — 학습 코치 슬라이스 2 (docs/design/2026-08-25-learning-coach-agent-design.md §8.1)
        "session_plans",
        "learner_notes",
```

```python
# ⑫ 007 — analysis_jobs 가 계획 job 을 받는다 (설계서 §8.3)
@pytest.mark.asyncio
async def test_analysis_jobs_accepts_plan_next_session(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    await db_conn.execute(
        "insert into analysis_jobs (job_type, session_id) values ('plan_next_session', $1)",
        session_id,
    )
    assert await db_conn.fetchval(
        "select count(*) from analysis_jobs where job_type = 'plan_next_session'"
    ) == 1


# ⑬ 007 — 계획 job 은 utterance 를 대상으로 삼을 수 없다 (대상 컬럼 배타 CHECK 3분기)
@pytest.mark.asyncio
async def test_plan_job_rejects_utterance_target(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    utterance_id = uuid4()
    await _insert_session(db_conn, session_id)
    await _insert_utterance(db_conn, utterance_id, session_id)

    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(
            "insert into analysis_jobs (job_type, utterance_id) "
            "values ('plan_next_session', $1)",
            utterance_id,
        )


# ⑭ 007 — session_plans 불변조건: 초점 1~2개 · 질문 3~5개 · 이유 비어있지 않음 (설계서 §9 Contract)
@pytest.mark.asyncio
async def test_session_plans_invariants(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)
    pattern_a, pattern_b, pattern_c = uuid4(), uuid4(), uuid4()

    def insert(focus: list, questions: str, reason: str) -> tuple[str, list]:
        return (
            "insert into session_plans "
            "(session_id, focus_pattern_ids, questions, target_level, reason, instruction, source) "
            "values ($1, $2, $3::jsonb, 'A2', $4, '{}'::jsonb, 'agent')",
            [session_id, focus, questions, reason],
        )

    ok_questions = '[{"prompt":"q1","context":"c1"},{"prompt":"q2","context":"c2"},{"prompt":"q3","context":"c3"}]'

    # 초점 3개 → 거부
    sql, args = insert([pattern_a, pattern_b, pattern_c], ok_questions, "이유")
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(sql, *args)

    # 질문 2개 → 거부
    sql, args = insert([pattern_a], '[{"prompt":"q1","context":"c1"},{"prompt":"q2","context":"c2"}]', "이유")
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(sql, *args)

    # 이유가 공백뿐 → 거부
    sql, args = insert([pattern_a], ok_questions, "   ")
    with pytest.raises(asyncpg.CheckViolationError):
        await db_conn.execute(sql, *args)

    # 정상 1행은 들어간다
    sql, args = insert([pattern_a, pattern_b], ok_questions, "관사를 계속 빼먹어서 오늘 그것만 봅니다")
    await db_conn.execute(sql, *args)
    assert await db_conn.fetchval("select count(*) from session_plans") == 1


# ⑮ 007 — 세션이 지워지면 계획도 함께 지워진다 · 세션당 1행
@pytest.mark.asyncio
async def test_session_plans_unique_and_cascade(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)
    questions = '[{"prompt":"q1","context":"c1"},{"prompt":"q2","context":"c2"},{"prompt":"q3","context":"c3"}]'
    sql = (
        "insert into session_plans "
        "(session_id, focus_pattern_ids, questions, target_level, reason, instruction, source) "
        "values ($1, $2, $3::jsonb, 'A2', '이유', '{}'::jsonb, 'agent')"
    )
    await db_conn.execute(sql, session_id, [uuid4()], questions)

    with pytest.raises(asyncpg.UniqueViolationError):
        await db_conn.execute(sql, session_id, [uuid4()], questions)

    await db_conn.execute("delete from learning_sessions where id = $1", session_id)
    assert await db_conn.fetchval("select count(*) from session_plans") == 0
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_schema.py -c pyproject.toml -v -k "plan or session_plans or expected_tables"`
Expected: **5건 FAIL** — 표 목록 단정은 `session_plans`·`learner_notes`가 없어 집합 불일치, 나머지 4건은
`UndefinedTableError` 또는 CHECK 위반이 나지 않아 실패. **부재를 단정하는 테스트가 아니라 실제 동작을
요구하는 테스트여야 한다** — "5건 중 5건 red"를 출력으로 확인하고 기록한다.

- [ ] **Step 3: 마이그레이션을 쓴다**

```sql
-- 007_learning_coach_slice2.sql
-- 학습 코치 슬라이스 2 — 판단과 적용
-- 설계: docs/design/2026-08-25-learning-coach-agent-design.md §8.1 · §8.3
-- 계획: docs/design/2026-09-04-learning-coach-slice2-plan.md
-- 요구사항: docs/PRD.md §11 R11-2(계획) · R11-10(관찰 기록)
--
-- 번호가 007인 이유: 006이 슬라이스 1이었고 002는 만들어진 적이 없다(설계서 §8.4 정정).
-- 트랜잭션은 scripts/migrate.py 가 감싼다 — 이 파일에 begin/commit 을 쓰지 않는다.
--
-- 여기 **없는 것**: users.current_level 은 001 이 이미 만들었고 CEFR CHECK 도 거기 있다.
-- pattern_attempts·suggested_contexts 는 006(슬라이스 1)이 만들었다.

-- §8.1: 세션이 만든 계획 1행. session_id 는 **계획을 만든 세션**이다(계획 문서 「구현 전 정정」)
-- — 소비 세션은 생성 시점에 존재하지 않는다. 세션 시작은 직전 세션이 만든 계획을 조회한다.
create table session_plans (
  id uuid primary key default gen_random_uuid(),
  -- unique: 한 세션이 계획을 두 번 만들지 않는다. cascade: 세션이 지워지면 계획도 무의미하다.
  session_id uuid not null unique references learning_sessions (id) on delete cascade,
  -- 초점 패턴 1~2개 (PRD §11 R11-2). uuid[] 로 두는 이유: 순서가 의미를 갖고 행이 2개뿐이라
  -- 별도 연결 표를 만들면 조회가 늘기만 한다(YAGNI).
  focus_pattern_ids uuid[] not null,
  -- 질문 3~5개. 모양은 [{"prompt","context"}, …] — 계획서 Task 1 이 정했다.
  questions jsonb not null,
  -- CEFR 값역은 001 의 users.current_level·learning_scenarios.level 과 **같은 값**을 쓴다.
  target_level text not null check (target_level in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2')),
  -- not null + 공백 금지: 이유 없는 추천은 사용자가 판단을 검증할 수 없다(PRD.md:189 R11-3).
  reason text not null,
  -- 세션 지시문 가변부(§5.2). 구조로 저장하고 문장 조립은 읽는 쪽이 한다.
  instruction jsonb not null,
  -- 계획 품질 관측용. 폴백으로 시작한 세션은 애초에 이 행이 없으므로 'fallback' 은
  -- "계획 생성은 됐지만 뱅크 내용을 썼다"는 뜻이다.
  source text not null check (source in ('agent', 'fallback')),
  created_at timestamptz not null default now(),
  -- ⚠️ `cardinality`를 쓴다. `array_length('{}', 1)`은 **NULL**이고 CHECK 식이 NULL이면
  -- Postgres가 **만족으로 취급**하므로 빈 배열이 그대로 통과한다(2026-09-04 실측: 통과 1행).
  -- `cardinality('{}')`는 0이라 하한 1이 실제로 막힌다(같은 실측에서 거부 확인).
  -- 바로 아래 `questions`가 안전한 것은 `jsonb_array_length('[]')`가 0을 돌려주기 때문이다 —
  -- 두 함수의 빈값 처리가 달라서 생긴 비대칭이다.
  constraint session_plans_focus_len
    check (cardinality(focus_pattern_ids) between 1 and 2),
  constraint session_plans_questions_len
    check (jsonb_typeof(questions) = 'array' and jsonb_array_length(questions) between 3 and 5),
  constraint session_plans_reason_not_blank
    check (btrim(reason) <> '')
);

-- §6.3: 덧붙이기만 한다. 갱신·삭제하지 않으므로 updated_at 을 두지 않는다.
create table learner_notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users (id) on delete cascade,
  -- 관찰 항목 배열 + 수준 변경 사유. 별도 이력 표를 만들지 않는다(§7).
  note jsonb not null,
  -- 이 노트가 읽은 발화 범위 — 어떤 근거로 쓰인 노트인지 추적한다(§6.3).
  window_from timestamptz not null,
  window_to timestamptz not null,
  created_at timestamptz not null default now(),
  constraint learner_notes_window_ordered check (window_from <= window_to)
);

-- 최신 행이 현행 노트다(§6.3). 조회가 항상 "이 사용자의 가장 최근 1행"이라 이 인덱스를 둔다.
create index idx_learner_notes_latest on learner_notes (user_id, created_at desc);

-- §8.3: job_type 에 계획 생성을 더한다. **값만 늘리면 안 된다** — 대상 컬럼 CHECK 가
-- 2분기 OR 이라 session_id 조합이 거부된다(계획서 「구현 전 정정」). 두 CHECK 를 함께 갈아낸다.
-- partial unique uq_analysis_jobs_pending_session 은 001 이 (job_type, session_id) 로
-- 이미 만들어 뒀다 — **새 인덱스를 만들지 않는다.**
alter table analysis_jobs drop constraint analysis_jobs_job_type_check;
alter table analysis_jobs add constraint analysis_jobs_job_type_check
  check (job_type in ('analyze_utterance', 'summarize_session', 'plan_next_session'));

alter table analysis_jobs drop constraint analysis_jobs_target_matches_job_type;
alter table analysis_jobs add constraint analysis_jobs_target_matches_job_type
  check (
    (job_type = 'analyze_utterance' and utterance_id is not null and session_id is null)
    or (job_type = 'summarize_session' and session_id is not null and utterance_id is null)
    or (job_type = 'plan_next_session' and session_id is not null and utterance_id is null)
  );
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_schema.py -c pyproject.toml -v`
Expected: 전건 PASS. 이어서 전체 게이트: `.venv/bin/pytest -q` → **458 passed**(454 + 신규 4건.
표 목록 단정은 **기존 테스트 수정**이라 개수를 늘리지 않는다 — 2026-09-04 실측으로 확인),
`.venv/bin/ruff check . && .venv/bin/ruff format --check .` → exit 0, `ty check` → All checks passed.

⚠️ **위반을 기대하는 단정은 `async with db_conn.transaction():`으로 하나씩 감싼다.** `db_conn`
픽스처는 트랜잭션 **하나**로 돌기 때문에 CHECK·UNIQUE 위반이 나면 그 트랜잭션이 abort되고,
같은 테스트의 다음 문장이 전부 `InFailedSQLTransactionError`로 죽는다. 위 ⑭는 위반 3건과 성공 1건을
한 테스트에 담고 있어 이 격리 없이는 **항상 실패한다**(2026-09-04 실측). asyncpg의 중첩 트랜잭션이
savepoint로 동작해 위반 하나만 되돌린다.

- [ ] **Step 5: 커밋**

```bash
git add db/migrations/007_learning_coach_slice2.sql tests/unit/test_schema.py
git commit -m "feat: 007 마이그레이션 — session_plans·learner_notes + 계획 job 종류

- analysis_jobs 의 CHECK 2개를 재작성한다(값 3개 + 대상 3분기). 값만 늘리면
  session_id 조합이 기존 2분기 OR 에 거부된다
- partial unique 는 001 의 (job_type, session_id) 를 그대로 쓴다 — 새 인덱스 없음
- session_id 는 계획을 **만든** 세션이다: §8.1 의 not null+unique 와 §3.4 의
  '세션 시작은 조회 1회'가 이 읽기를 강제한다"
```

⚠️ **실물 dev DB 적용은 하지 않는다.** 이 태스크는 테스트 DB에서만 판정한다.
dev DB 적용은 **캡틴 승인 후** 실물 검증 L1에서 한다(아래 「실물 검증」).

---

### Task 2: 세션이 끝날 때 계획 job을 같은 트랜잭션에서 등록한다

**Files:**
- Modify: `app/backend/app/services/jobs.py`
- Modify: `app/backend/app/services/sessions.py:83-101` (`end_session`)
- Test: `tests/unit/test_jobs.py` (수정)

**Interfaces:**
- Consumes: Task 1의 `job_type = 'plan_next_session'` CHECK
- Produces: `JOB_TYPE_PLAN: str = "plan_next_session"` ·
  `async def enqueue_plan_next_session(conn: asyncpg.Connection, session_id: UUID) -> UUID | None`
  (등록했으면 job id, 이미 pending/running이면 `None`)

⚠️ **`end_session`의 호출자가 둘이고 둘 다 트랜잭션을 열어야 한다** (2026-09-04 리뷰에서 발견,
직접 확인). 정상 종료(`audio_gateway/session.py:164`)는 이미 `conn.transaction()`으로 감싸지만
**`mark_session_ended`(`sessions.py:190`)는 열지 않는다** — asyncpg는 명시적 블록이 없으면 문장마다
autocommit이라 그 경로가 비원자적이 된다. 이 태스크가 그 래퍼에도 트랜잭션을 넣는다.
`mark_session_ended`가 "묶을 것이 없는 호출자용"이라던 서술 **2곳**(`sessions.py:186` docstring ·
`pronunciation.py:321` 주석)은 이제 거짓이므로 함께 정정한다.

⚠️ **고아 리퍼가 닫은 세션은 계획 job을 받지 못한다 — 알고 받아들이는 축소다.**
`reap_orphan_sessions`는 `end_session`을 거치지 않고 대량 UPDATE로 닫는다(`sessions.py:63-74`).
그래서 **프로세스가 죽어 끝난 세션**은 다음 세션에서 폴백으로 시작한다 — 설계서 §3.3이 열거한
폴백 사유 3개(첫 세션·생성 실패·스키마 거부) 밖의 **4번째 사유**다. 리퍼 SQL에 등록을 붙이는 것은
별 태스크이고(대량 UPDATE에서 job을 걸면 오래된 고아가 쌓인 DB에서 한 번에 N건이 등록된다),
이 계획은 고치지 않는다. **Task 12가 설계서 §11 이월에 이 사유를 적는다.**
⚠️ **버그로 다시 조사하지 마라.**

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/unit/test_jobs.py 에 추가
from app.services.jobs import JOB_TYPE_PLAN, enqueue_plan_next_session
from app.services.sessions import end_session


@pytest.mark.asyncio
async def test_enqueue_plan_next_session_registers_one_job(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    job_id = await enqueue_plan_next_session(db_conn, session_id)

    assert job_id is not None
    row = await db_conn.fetchrow(
        "select job_type, session_id, utterance_id, status from analysis_jobs where id = $1",
        job_id,
    )
    assert row["job_type"] == JOB_TYPE_PLAN
    assert row["session_id"] == session_id
    assert row["utterance_id"] is None
    assert row["status"] == "pending"


@pytest.mark.asyncio
async def test_enqueue_plan_next_session_is_idempotent_while_pending(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    first = await enqueue_plan_next_session(db_conn, session_id)
    second = await enqueue_plan_next_session(db_conn, session_id)

    assert first is not None
    assert second is None
    assert await db_conn.fetchval(
        "select count(*) from analysis_jobs where job_type = $1", JOB_TYPE_PLAN
    ) == 1


# 설계서 §3.1: 종료 기록과 job 등록이 한 트랜잭션이다. 분리하면 그 사이 크래시에서
# 다음 계획이 영구히 만들어지지 않는다.
@pytest.mark.asyncio
async def test_end_session_enqueues_plan_job_in_same_transaction(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    await end_session(db_conn, session_id, "completed")

    assert await db_conn.fetchval(
        "select count(*) from analysis_jobs where job_type = $1 and session_id = $2",
        JOB_TYPE_PLAN,
        session_id,
    ) == 1


# 이미 닫힌 세션을 다시 닫으려 하면 job 이 늘지 않는다 — end_session 의 active 가드가
# 실제로 닫았는지(`closed`)를 보기 때문이다.
@pytest.mark.asyncio
async def test_end_session_does_not_enqueue_when_already_closed(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)

    await end_session(db_conn, session_id, "failed")
    await end_session(db_conn, session_id, "completed")

    assert await db_conn.fetchval(
        "select count(*) from analysis_jobs where session_id = $1", session_id
    ) == 1
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_jobs.py -c pyproject.toml -v -k "plan"`
Expected: **4건 FAIL** — 첫 두 건은 `ImportError: cannot import name 'enqueue_plan_next_session'`,
뒤 두 건은 job 수가 0이라 단정 실패.

- [ ] **Step 3: 최소 구현**

`app/backend/app/services/jobs.py` — 상수와 등록 함수를 더한다.

```python
JOB_TYPE_PLAN = "plan_next_session"

_ENQUEUE_PLAN_SQL = """
insert into analysis_jobs (job_type, session_id)
values ($1, $2)
on conflict do nothing
returning id
"""


async def enqueue_plan_next_session(
    conn: asyncpg.Connection, session_id: UUID
) -> UUID | None:
    """끝난 세션 하나를 근거로 **다음** 세션 계획을 만들 job을 건다 (설계서 §3.1).

    `None`은 실패가 아니라 **이미 걸려 있다**는 뜻이다 — partial unique
    `uq_analysis_jobs_pending_session`이 `(job_type, session_id)`를 pending/running
    동안 하나로 묶는다. 재시도되는 호출자가 중복을 만들지 않는다.

    ⚠️ 연결을 받는다(pool이 아니다). 세션 종료 기록과 **한 트랜잭션**이어야 하기 때문이다 —
    분리하면 그 사이 크래시에서 다음 계획이 영구히 만들어지지 않는다.
    """
    return await conn.fetchval(_ENQUEUE_PLAN_SQL, JOB_TYPE_PLAN, session_id)
```

`app/backend/app/services/sessions.py` — `end_session`의 `closed` 판정 뒤에 등록을 붙인다.
기존 `if closed is None:` 경고 분기는 그대로 두고, 닫힌 경우에만 등록한다.

```python
    closed = await conn.fetchval(_END_SESSION_SQL, session_id, status)
    if closed is None:
        # (기존 경고 분기 — 그대로 둔다)
        ...
        return
    # 설계서 §3.1: 같은 트랜잭션에서 다음 계획 job을 건다. `closed`가 있을 때만 거는 이유는
    # 이미 닫힌 세션 재호출(리퍼가 먼저 닫은 경우)에서 job이 중복되지 않게 하려는 것이다.
    await enqueue_plan_next_session(conn, session_id)
```

⚠️ **`import`는 모듈 최상단에 둔다.** `sessions.py`가 `jobs.py`를 부르는 방향이 새로 생기므로
순환 import가 없는지 확인한다 — `jobs.py`는 `sessions`를 import하지 않는다(직접 확인할 것).

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_jobs.py -c pyproject.toml -v`
Expected: 전건 PASS. 이어서 `.venv/bin/pytest -q`로 **무회귀**를 본다 —
세션 종료 경로를 건드렸으므로 `test_ws.py`·`test_sessions.py`·`test_pronunciation_service.py`가
함께 통과해야 한다. 실패하면 그 테스트가 job 수를 단정하고 있는지 먼저 본다(계획 job이 하나 늘었다).

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/services/jobs.py app/backend/app/services/sessions.py tests/unit/test_jobs.py
git commit -m "feat: 세션 종료와 같은 트랜잭션에서 계획 생성 job 을 건다

- end_session 이 실제로 닫았을 때만(closed is not None) 등록한다 — 리퍼가
  먼저 닫은 세션 재호출에서 중복되지 않는다
- 연결을 받는 함수로 두었다: 종료 기록과 분리하면 그 사이 크래시에서 다음
  계획이 영구히 만들어지지 않는다(설계서 §3.1)"
```

---

### Task 3: 워커가 job 종류를 구분한다

**Files:**
- Modify: `app/backend/app/services/jobs.py` (`ClaimedJob`, `claim_next`의 `returning`)
- Modify: `app/backend/app/workers/analysis_worker.py` (분기)
- Modify: `app/backend/app/services/analysis.py:489-494` (대상 판정)
- Test: `tests/unit/test_jobs.py`, `tests/unit/test_analysis.py` (수정)

**Interfaces:**
- Consumes: Task 2의 `JOB_TYPE_PLAN`
- Produces: `ClaimedJob(id: UUID, job_type: str, utterance_id: UUID | None, session_id: UUID | None, lease_token: str, attempts: int)`
  — **필드 2개가 늘었다.** `ClaimedJob`을 만드는 테스트가 있으면 함께 고쳐야 한다.

**왜 필요한가**: 오늘 계획 job을 넣으면 워커가 **그 자리에서 실패시킨다**. `claim_next`가 `job_type`을
돌려주지 않아 워커가 구분할 수 없고, `analysis.py`가 `utterance_id is None`을 곧 오류로 보기 때문이다.

⚠️ **이 태스크는 실제로 쌓이고 있는 쓰레기를 치운다.** Task 2가 끝난 시점부터 **세션 종료마다**
계획 job이 걸리고, 워커가 그것을 무대상 job으로 판정해 **5회 재시도 후 terminal `failed`로 쌓는다**
(2026-09-04 Task 2 리뷰에서 확인). 데이터 손실은 없지만 세션마다 실패 job 1건이 남는다 —
**게이트는 green이라 테스트로는 드러나지 않는다.** 이 태스크가 그 상태를 닫는다.

⚠️ **Task 2에서 넘어온 낡은 주석 1건을 함께 고친다.** `app/backend/app/services/analysis.py:490-492`가
"`summarize_session` job은 **이번 슬라이스에 등록되지 않지만** 타입상 가능하다"고 적었는데, 이제
세션마다 무대상 job(`plan_next_session`)이 **실제로 등록된다.** 이 태스크가 그 분기를 다시 쓰므로
여기서 참인 서술로 정정한다(Task 2에서 고치면 이 태스크가 같은 줄을 두 번 건드린다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/unit/test_jobs.py 에 추가
@pytest.mark.asyncio
async def test_claim_next_reports_job_type_and_session_target(db_conn: asyncpg.Connection):
    await _insert_user(db_conn)
    session_id = uuid4()
    await _insert_session(db_conn, session_id)
    await enqueue_plan_next_session(db_conn, session_id)

    claimed = await claim_next(db_conn)

    assert claimed is not None
    assert claimed.job_type == JOB_TYPE_PLAN
    assert claimed.session_id == session_id
    assert claimed.utterance_id is None
```

```python
# tests/unit/test_analysis.py 에 추가 — 분석 job 만 process_analysis 로 간다
@pytest.mark.asyncio
async def test_process_analysis_rejects_non_analyze_job(db_pool: asyncpg.Pool, fake_claude):
    job = ClaimedJob(
        id=uuid4(),
        job_type="plan_next_session",
        utterance_id=None,
        session_id=uuid4(),
        lease_token="t",
        attempts=1,
    )
    # 라우팅 실수를 조용히 삼키지 않는다 — 대상이 없다고 실패시키던 기존 문구가
    # 아니라 "종류가 다르다"로 실패해야 원인이 보인다.
    await process_analysis(db_pool, fake_claude(), job)
    # job 행이 없으므로 상태 갱신은 일어나지 않지만, 예외로 터지지 않는 것이 계약이다
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_jobs.py ../../tests/unit/test_analysis.py -c pyproject.toml -v -k "job_type or non_analyze"`
Expected: **2건 FAIL** — `AttributeError: 'ClaimedJob' object has no attribute 'job_type'`와
`TypeError: ClaimedJob.__init__() got an unexpected keyword argument 'job_type'`.

- [ ] **Step 3: 최소 구현**

`jobs.py` — `ClaimedJob`에 두 필드를 더하고 `returning`을 넓힌다.

```python
@dataclass(frozen=True, slots=True)
class ClaimedJob:
    """One successful claim. `lease_token` is only valid until `LEASE` elapses.

    `job_type`을 함께 돌려주는 이유: 큐 하나에 종류가 셋이고
    (`analyze_utterance`·`summarize_session`·`plan_next_session`) 대상 컬럼이
    상호배타적이라, **종류를 모르면 어느 대상을 읽어야 하는지 알 수 없다.**
    이전에는 `utterance_id`의 유무로 추측했는데 그러면 계획 job이 "대상 없음"으로
    실패했다(계획서 Task 3).
    """

    id: UUID
    job_type: str
    utterance_id: UUID | None
    session_id: UUID | None
    lease_token: str
    attempts: int
```

`claim_next`의 SQL 마지막 줄과 반환을 함께 고친다.

```python
        returning id, job_type, utterance_id, session_id, attempts
```

```python
    return ClaimedJob(
        id=row["id"],
        job_type=row["job_type"],
        utterance_id=row["utterance_id"],
        session_id=row["session_id"],
        lease_token=lease_token,
        attempts=row["attempts"],
    )
```

`analysis_worker.py`의 루프에서 종류로 분기한다. 기존 `await process_analysis(pool, claude, job)` 한 줄을
바꾼다.

```python
            if job.job_type == JOB_TYPE_PLAN:
                await process_plan(pool, claude, job)
            else:
                await process_analysis(pool, claude, job)
```

⚠️ **Task 7까지는 `process_plan`이 없다.** 이 태스크에서는 `services/plan.py`에 **호출 가능한 최소
형태**를 만들어 둔다 — 입력을 읽지 못하면 job을 실패로 종결시키는 것까지만. Task 4~7이 그 안을 채운다.

**먼저 실패 보고 헬퍼를 공용으로 옮긴다.** `_report_failure`는 지금 `analysis.py:473`의 **private
함수**여서 `plan.py`가 쓸 수 없다. 내용은 job 수명주기 로직뿐이고(`fail_or_retry` 한 줄) 분석에
고유한 것이 없으므로 `jobs.py`로 옮겨 공개한다 — 복제하지 않는다.

```python
# app/backend/app/services/jobs.py 로 옮긴다 (analysis.py 에서 삭제)
async def report_failure(pool: asyncpg.Pool, job: ClaimedJob, error: str) -> None:
    """실패를 큐에 보고한다 — 짧은 자기 트랜잭션(이 모듈의 호출 계약).

    `analysis.py`의 private 함수였는데 계획 생성 job 도 같은 보고가 필요해져 여기로 옮겼다.
    내용은 job 수명주기 로직뿐이라 이 모듈이 원래 자리다. 복제하면 두 경로의 보고 방식이
    조용히 갈라진다.
    """
    async with pool.acquire() as conn, conn.transaction():
        recorded = await fail_or_retry(conn, job.id, job.lease_token, error)
    if not recorded:
        logger.warning("job %s: failure report discarded (lease no longer ours)", job.id)
```

⚠️ **`jobs.py`에는 지금 logger가 없다** (2026-09-04 직접 확인: `import logging`·`getLogger` 각 0건).
옮기는 함수가 `logger.warning`을 쓰므로 `import logging`과 `logger = logging.getLogger(__name__)`을
함께 넣어야 한다. `analysis.py`의 logger 정의(`:27`·`:48`)는 다른 곳에서도 쓰이므로 **지우지 않는다.**

⚠️ **로그 이름이 바뀐다.** 그 경고는 이제 `app.services.analysis`가 아니라 `app.services.jobs`로 찍힌다.
레벨은 `warning` 그대로 둔다 — 문서가 지정한 실행에서 INFO는 보이지 않고(함정 H-Z), 이 로그가
lease 상실의 유일한 신호다.

`analysis.py`는 `_report_failure` 정의를 지우고 import를 정리한다. **`fail_or_retry`를 빼고
`report_failure`를 넣는다** — 직접 확인한 결과 `fail_or_retry`는 `_report_failure` 안에서만 쓰이므로
(`analysis.py:476` 한 곳) 남겨 두면 미사용 import가 되어 `ruff`가 게이트를 깬다. `complete`는
`:469`에서 계속 쓰이므로 **유지한다.** 최종 형태:

```python
from app.services.jobs import ClaimedJob, complete, report_failure
```

호출부 2곳(`analysis.py:493`과 이 태스크가 더하는 종류 판정)도 새 이름을 쓴다.
`_report_failure`를 쓰는 다른 모듈은 **없다**(앱·테스트·스크립트 전체 grep 0건) — 옮겨도 깨질 곳이 없다.

```python
# app/backend/app/services/plan.py (이 태스크가 만드는 최소 형태)
async def process_plan(pool: asyncpg.Pool, claude: ClaudeClient, job: ClaimedJob) -> None:
    """계획 생성 job 하나를 처리한다. Task 4~7이 이 함수의 안을 채운다.

    지금은 대상 검증만 한다 — 계약을 먼저 고정해 워커 분기가 이 태스크에서 완결되게 한다.
    """
    if job.session_id is None:
        await report_failure(pool, job, f"plan job {job.id} has no session target")
        return
    raise NotImplementedError("Task 7이 저장까지 채운다")
```

⚠️ **`NotImplementedError`를 남긴 채로 이 계획을 끝내지 않는다.** Task 7 완료 시점에 사라져야 하고,
Task 7의 Step 4가 그것을 확인한다. 완료 판정 전에 `grep -rn "NotImplementedError" app/backend/app/`이
**0건**이어야 한다.

`analysis.py:489-494`의 대상 판정을 종류 기준으로 바꾼다.

```python
    if job.job_type != JOB_TYPE_ANALYZE:
        await report_failure(pool, job, f"job {job.id} is not an analysis job: {job.job_type}")
        return
    if job.utterance_id is None:
        await report_failure(pool, job, f"job {job.id} has no utterance target")
        return
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -q`
Expected: 전건 PASS. `ClaimedJob`을 직접 만드는 기존 테스트가 있으면 **인자 2개를 더해** 고친다 —
`grep -rn "ClaimedJob(" ../../tests app`으로 전부 찾아 한 번에 고친다.
`ty check`도 함께 돌린다 — 데이터클래스 필드가 늘어 타입 오류가 나기 쉬운 자리다.

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/services/jobs.py app/backend/app/services/analysis.py \
        app/backend/app/services/plan.py app/backend/app/workers/analysis_worker.py \
        tests/unit/test_jobs.py tests/unit/test_analysis.py
git commit -m "feat: 워커가 job 종류로 분기한다

- claim_next 가 job_type·session_id 를 함께 돌려준다. 없으면 계획 job 이
  '대상 없음'으로 즉시 실패했다
- analysis.py 의 대상 판정을 utterance_id 유무에서 job_type 기준으로 바꿨다
- process_plan 은 대상 검증만 하는 최소 형태다 — Task 4~7 이 안을 채운다"
```

---

### Task 4: 계획 입력을 한 자료구조로 모은다

**Files:**
- Create: `app/backend/app/services/plan_input.py`
- Modify: `app/backend/app/services/review.py` (공개 함수 1개 추가)
- Test: `tests/unit/test_plan_input.py` (신규), `tests/unit/test_chronic.py` (수정 — 이연 LOW-12)

**Interfaces:**
- Consumes: `review.load_due_reviews(conn, user_id) -> list[DueReview]` ·
  `review.fold_stages(relapse_at, correct_times, scenario_context) -> ReviewState` ·
  `chronic.load_chronic_metrics(conn, user_id) -> list[ChronicMetric]`
- Produces:
  - `review.load_completed_then_relapsed(conn: asyncpg.Connection, user_id: UUID) -> set[UUID]`
  - `RecentUtterance(said_at: datetime, transcript: str, corrections: list[RecentCorrection])`
  - `RecentCorrection(pattern_key: str, category: str, original_span: str, correction: str, reason: str, severity: str, confidence: float)`
  - `PronunciationTally(target_sound: str, outcome: str, attempts: int, last_seen: datetime)`
  - `PlanInput(user_id: UUID, timezone: str, window_from: datetime, window_to: datetime, current_level: str, due_reviews: list[DueReview], chronic: list[ChronicMetric], chronic_pattern_ids: set[UUID], recent: list[RecentUtterance], pronunciation: list[PronunciationTally])`
  - `async def load_plan_input(conn: asyncpg.Connection, user_id: UUID) -> PlanInput`

**이 태스크가 닫는 이연 2건**: **LOW-12**(`chronic.py`의 SQL 세부 3개가 무보호) — 이 계획이
`chronic.py`의 첫 소비자이므로 여기서 테스트로 덮는다. **LOW-14**(`users.timezone`이 CHECK 없는
자유 텍스트라 무효값이면 예외가 그대로 나간다) — 조용히 UTC로 떨어지지 않고 **읽을 수 있는 오류로
job을 실패시킨다**(H-S가 걸린 자리라 조용한 폴백이 가장 위험하다).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/unit/test_plan_input.py (신규)
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import asyncpg
import pytest

from app.services.plan_input import InvalidTimezoneError, load_plan_input
from app.services.review import load_completed_then_relapsed

UTC = timezone.utc


# AS1 — 복습일이 지난 패턴이 여럿이면 **전부** 입력에 들어온다. 하나라도 빠지면 실패다.
@pytest.mark.asyncio
async def test_all_due_patterns_reach_the_input(db_conn: asyncpg.Connection, seed_due_patterns):
    user_id = await seed_due_patterns(db_conn, count=3)

    result = await load_plan_input(db_conn, user_id)

    assert len(result.due_reviews) == 3
    assert len({review.pattern_id for review in result.due_reviews}) == 3


# §4.2 — 최근 창은 14일이고 학습 발화만 본다(명령 발화는 학습 이력이 아니다).
@pytest.mark.asyncio
async def test_recent_window_is_14_days_and_learning_only(
    db_conn: asyncpg.Connection, seed_utterance_at
):
    user_id = await seed_utterance_at(db_conn, days_ago=1, transcript="inside", kind="learning")
    await seed_utterance_at(db_conn, days_ago=1, transcript="a command", kind="voice_command")
    await seed_utterance_at(db_conn, days_ago=20, transcript="too old", kind="learning")

    result = await load_plan_input(db_conn, user_id)

    transcripts = [item.transcript for item in result.recent]
    assert transcripts == ["inside"]
    assert result.window_to - result.window_from == timedelta(days=14)


# §4.4 주의 1 — pending 은 미판정이라 계획 근거로 쓰지 않는다.
@pytest.mark.asyncio
async def test_pronunciation_pending_is_excluded(db_conn: asyncpg.Connection, seed_pronunciation):
    user_id = await seed_pronunciation(
        db_conn, [("th_as_s", "incorrect"), ("th_as_s", "pending"), ("f_as_p", "correct")]
    )

    result = await load_plan_input(db_conn, user_id)

    outcomes = {(tally.target_sound, tally.outcome) for tally in result.pronunciation}
    assert ("th_as_s", "pending") not in outcomes
    assert ("th_as_s", "incorrect") in outcomes
    assert ("f_as_p", "correct") in outcomes


# §6.2 — 3단계를 완주한 뒤 다시 발생한 패턴은 그 사실 자체로 만성이다.
#   틀림(day0) → day1·day4·day11 정답(완주) → day20 다시 틀림  ⇒ 신호 ON
@pytest.mark.asyncio
async def test_completed_then_relapsed_is_detected(db_conn: asyncpg.Connection, seed_cycle):
    user_id, pattern_id = await seed_cycle(
        db_conn,
        relapses=[0, 20],
        corrects=[1, 4, 11],
    )

    flagged = await load_completed_then_relapsed(db_conn, user_id)

    assert pattern_id in flagged


# 완주하지 못한 채 재발한 패턴은 신호가 켜지지 않는다 — 임계값을 발명하지 않는다.
@pytest.mark.asyncio
async def test_relapse_without_completion_is_not_flagged(db_conn: asyncpg.Connection, seed_cycle):
    user_id, pattern_id = await seed_cycle(
        db_conn,
        relapses=[0, 20],
        corrects=[1, 4],  # 2단계까지만 — 7일 단계를 통과하지 못했다
    )

    flagged = await load_completed_then_relapsed(db_conn, user_id)

    assert pattern_id not in flagged


# LOW-14 — 타임존 값이 무효면 **조용히 UTC 로 떨어지지 않고** 읽을 수 있는 오류를 낸다.
@pytest.mark.asyncio
async def test_invalid_timezone_raises_readable_error(db_conn: asyncpg.Connection, seed_user):
    user_id = await seed_user(db_conn, tz="Not/AZone")

    with pytest.raises(InvalidTimezoneError) as excinfo:
        await load_plan_input(db_conn, user_id)

    assert "Not/AZone" in str(excinfo.value)
```

```python
# tests/unit/test_chronic.py 에 추가 — 이연 LOW-12 의 SQL 세부 3개를 덮는다
# ① 정렬이 pattern_key 순인지 (뮤테이션: order by 제거)
@pytest.mark.asyncio
async def test_chronic_metrics_are_ordered_by_pattern_key(db_conn, seed_two_patterns):
    user_id = await seed_two_patterns(db_conn, keys=["zebra_last", "alpha_first"])

    metrics = await load_chronic_metrics(db_conn, user_id)

    assert [metric.pattern_key for metric in metrics] == ["alpha_first", "zebra_last"]


# ② 최대 공백은 **인접 간격의 최대값**이다 (뮤테이션: lag 의 tie-break 변경)
@pytest.mark.asyncio
async def test_max_gap_is_largest_adjacent_interval(db_conn, seed_occurrences_on_days):
    user_id, _ = await seed_occurrences_on_days(db_conn, days=[0, 2, 42, 44])

    metrics = await load_chronic_metrics(db_conn, user_id)

    # 간격은 2, 40, 2 → 최대 40일
    assert metrics[0].max_gap == timedelta(days=40)


# ③ 발생이 1건이면 최대 공백이 없다 (뮤테이션: where prev_at is not null 제거)
@pytest.mark.asyncio
async def test_single_occurrence_has_no_max_gap(db_conn, seed_occurrences_on_days):
    user_id, _ = await seed_occurrences_on_days(db_conn, days=[0])

    metrics = await load_chronic_metrics(db_conn, user_id)

    assert metrics[0].max_gap is None
    assert metrics[0].span == timedelta(0)
```

⚠️ 위 테스트가 쓰는 픽스처(`seed_due_patterns`·`seed_utterance_at`·`seed_pronunciation`·`seed_cycle`·
`seed_user`·`seed_two_patterns`·`seed_occurrences_on_days`)는 **이 태스크가 `tests/conftest.py`에 만든다.**
시각은 전부 `datetime.now(UTC) - timedelta(days=N)`로 만들어 **naive datetime을 절대 만들지 않는다.**

**`conftest.py`에 이미 있는 것 (2026-09-04 직접 확인 — 이것들을 재사용하고 다시 만들지 않는다)**:
`test_database`(세션 스코프) · `db_conn`(트랜잭션 **하나**로 도는 연결) · `db_pool` ·
`committed_session` · `fake_claude` · 헬퍼 `default_finding` · `backdate_session(conn, session_id, *, by: timedelta)` ·
`job_row(conn, job_id)`. **위 7개와 겹치는 것은 없다** — 전부 새로 만드는 것이 맞다.
특히 `backdate_session`은 "N일 전" 픽스처를 만들 때 그대로 쓸 수 있다.

⚠️ **`db_conn`은 트랜잭션 하나로 돈다.** 위반을 기대하는 단정이 있으면 `async with db_conn.transaction():`으로
감싸야 한다(Task 1에서 실측한 함정 — 감싸지 않으면 뒤 문장이 `InFailedSQLTransactionError`로 죽는다).

✅ **이 태스크의 `InvalidTimezoneError` 테스트는 그 함정에 걸리지 않는다** (2026-09-04 실측으로 확정):
`load_plan_input`이 `pg_timezone_names`를 **평범한 SELECT로 먼저 조회**해 판정하므로 DB 오류가
아예 발생하지 않고, 던지는 것은 **앱 예외**라 트랜잭션이 abort되지 않는다. savepoint로 감쌀 필요가 없다.
확인한 값: `exists(select 1 from pg_timezone_names where name = 'Asia/Seoul')` → `true`,
`'Not/AZone'` → `false`. 그리고 무효값을 `at time zone`에 쓰면 DB가
`ERROR: time zone "Not/AZone" not recognized`로 거부한다 — **먼저 검증하는 이유가 이것이다.**
검증을 건너뛰고 변환을 시도하면 DB 오류가 나서 `db_conn` 트랜잭션이 abort되고, 그때는 원인이
"타임존이 무효하다"가 아니라 "뒤 문장이 다 죽었다"로 보인다.

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_plan_input.py ../../tests/unit/test_chronic.py -c pyproject.toml -v`
Expected: `test_plan_input.py` **6건 FAIL**(`ModuleNotFoundError: app.services.plan_input`),
`test_chronic.py`의 새 3건 FAIL(픽스처 없음). "9건 중 9건 red"를 출력으로 확인한다.

- [ ] **Step 3: 최소 구현**

`review.py`에 공개 함수를 더한다. **`_HISTORY_SQL`을 재사용할 수 없다** — 그 쿼리는 마지막 재발
**이후**의 정답만 모으므로(`u.created_at > r.at`) 완주 이력(재발 **이전**)이 보이지 않는다.

```python
# 완주 판정에는 **재발 이전** 정답까지 필요하다 — `_HISTORY_SQL`은 마지막 재발 이후만 보므로
# 이 판정에 쓸 수 없다. 그래서 전체 이력을 시각만 뽑아 온다(단일 사용자 규모라 전량이 싸다).
_FULL_HISTORY_SQL = """
select p.id as pattern_id,
       coalesce((
         select array_agg(t.at order by t.at)
           from (
                 select u.created_at as at
                   from error_occurrences eo
                   join utterances u on u.id = eo.utterance_id
                  where eo.pattern_id = p.id
                 union all
                 select u.created_at as at
                   from pattern_attempts pa
                   join utterances u on u.id = pa.utterance_id
                  where pa.pattern_id = p.id and pa.outcome = 'incorrect'
                ) t
       ), '{}'::timestamptz[]) as relapse_times,
       coalesce((
         select array_agg(u.created_at order by u.created_at, pa.id)
           from pattern_attempts pa
           join utterances u on u.id = pa.utterance_id
          where pa.pattern_id = p.id and pa.outcome = 'correct'
       ), '{}'::timestamptz[]) as correct_times
  from error_patterns p
 where p.user_id = $1
 order by p.pattern_key
"""


async def load_completed_then_relapsed(
    conn: asyncpg.Connection, user_id: UUID
) -> set[UUID]:
    """3단계(1·3·7일)를 완주한 **뒤에** 다시 발생한 패턴들 (설계서 §6.2).

    이것이 설계서가 허용한 **유일한 결정론적 만성 신호**다 — 임계값이 아니라 문서로 확정된
    1·3·7일에서 유도되기 때문이다(§3.2). 판정 자체는 `fold_stages`가 하고 이 함수는
    사이클을 잘라 넘기기만 한다. **복습 단계의 정의를 여기 복제하지 않는다.**

    한 번 완주한 뒤 재발했다면 그 사실은 이후에도 참이므로, 연속한 재발 쌍을 모두 본다.
    마지막 재발 이후의 열린 구간은 세지 않는다 — 아직 "재발이 뒤따랐다"가 성립하지 않는다.
    """
    flagged: set[UUID] = set()
    for record in await conn.fetch(_FULL_HISTORY_SQL, user_id):
        relapses = list(record["relapse_times"])
        corrects = list(record["correct_times"])
        for start, end in zip(relapses, relapses[1:], strict=False):
            within = [at for at in corrects if start < at < end]
            if fold_stages(start, within, "").completed:
                flagged.add(record["pattern_id"])
                break
    return flagged
```

`app/backend/app/services/plan_input.py` (신규) — 읽기만 한다. 쓰기 함수를 두지 않는다.

```python
"""계획 입력 3계층(설계서 §4)을 한 자료구조로 모은다. **읽기 전용 모듈이다.**

전체 이력을 매번 넣지 않는 이유는 §4가 정한 그대로다 — 비용과 지연을 무의미하게 늘린다.
여기서 하는 일은 **사실을 모으는 것**뿐이고 무엇이 약점인지·무엇을 연습할지는 Claude가
판단한다(§3.2의 승인된 경계). 그래서 이 모듈에는 점수식도 임계값도 없다.
"""

# §4.2: 복습 최장 간격 7일의 2배. 설계서가 **유도값**임을 명시했으므로 바꿀 때 설계서를 함께 고친다.
RECENT_WINDOW_DAYS = 14

_TIMEZONE_SQL = "select timezone, current_level from users where id = $1"

_VALID_TIMEZONE_SQL = "select exists (select 1 from pg_timezone_names where name = $1)"


class InvalidTimezoneError(ValueError):
    """`users.timezone`이 Postgres가 모르는 값이다 (이연 LOW-14).

    조용히 UTC로 떨어지지 않는 이유: 이 값은 달력 날짜 계산의 SoT이고, UTC로 흘리면
    재발 일수가 하루씩 어긋난 채 계획이 만들어진다(함정 H-S). 틀린 계획보다 실패가 낫다.
    """


async def load_plan_input(conn: asyncpg.Connection, user_id: UUID) -> PlanInput:
    row = await conn.fetchrow(_TIMEZONE_SQL, user_id)
    if row is None:
        raise LookupError(f"user {user_id} not found")
    tz = row["timezone"]
    if not await conn.fetchval(_VALID_TIMEZONE_SQL, tz):
        raise InvalidTimezoneError(f"users.timezone is not a known zone: {tz!r}")

    window_to = await conn.fetchval("select clock_timestamp()")
    window_from = window_to - timedelta(days=RECENT_WINDOW_DAYS)

    return PlanInput(
        user_id=user_id,
        timezone=tz,
        window_from=window_from,
        window_to=window_to,
        current_level=row["current_level"],
        due_reviews=await load_due_reviews(conn, user_id),
        chronic=await load_chronic_metrics(conn, user_id),
        chronic_pattern_ids=await load_completed_then_relapsed(conn, user_id),
        recent=await _load_recent(conn, user_id, window_from),
        pronunciation=await _load_pronunciation(conn, user_id, window_from),
    )
```

`_load_recent`의 SQL은 **학습 발화만** 본다(Phase 1 §6.2 D4 규약 계속) —
`where u.utterance_type = 'learning' and u.created_at >= $2`, 그 발화의 `error_occurrences`를
`original_span`·`correction`·`reason`·`severity`·`confidence`와 함께 붙인다.

`_load_pronunciation`의 SQL은 설계서 §4.4를 그대로 쓰되 **`outcome <> 'pending'`을 더한다**:

```sql
select a.target_sound, a.outcome, count(*) as attempts, max(a.created_at) as last_seen
  from pronunciation_attempts a
  join learning_sessions s on s.id = a.session_id
 where s.user_id = $1
   and a.created_at >= $2
   and a.outcome <> 'pending'
   and a.target_sound is not null
 group by a.target_sound, a.outcome
 order by a.target_sound, a.outcome
```

⚠️ **`target_sound is not null`을 함께 거르는 이유**: 003이 그 컬럼을 nullable로 두었고
(`outcome='incorrect'`이고 키가 있을 때만 채운다) 키 없는 행은 "어느 소리인지 모르는 시도"라
초점 패턴 후보가 될 수 없다. **발음 `frequency`는 시도 수 기준이고 문법의 occurrence 수 기준과
계산이 다르므로**(§4.4 주의 2) 두 값을 한 정렬에 섞지 않는다 — 카테고리별로 따로 제시한다.

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_plan_input.py ../../tests/unit/test_chronic.py -c pyproject.toml -v`
Expected: 전건 PASS. 이어서 전체 게이트(`pytest -q`·`ruff`·`ty check`).
⚠️ **`chronic.py`를 고치지 않았는지 확인한다** — LOW-12는 **테스트만** 더하는 것이다.
`git diff --name-only`에 `app/backend/app/services/chronic.py`가 없어야 한다.

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/services/plan_input.py app/backend/app/services/review.py \
        tests/unit/test_plan_input.py tests/unit/test_chronic.py tests/conftest.py
git commit -m "feat: 계획 입력을 모으는 읽기 전용 모듈

- 복습 목록·최근 14일 창·만성 지표·발음 시도를 한 자료구조로 모은다
- §6.2 의 결정론적 만성 신호(3단계 완주 후 재발)는 review.py 가 소유한다 —
  fold_stages 를 재사용하고 단계 정의를 복제하지 않는다
- _HISTORY_SQL 을 쓸 수 없는 이유: 그 쿼리는 마지막 재발 **이후** 정답만 본다
- 이연 LOW-12(chronic SQL 3개 무보호) 테스트로 덮음, LOW-14(타임존 무효값)는
  조용한 UTC 폴백 대신 읽을 수 있는 오류로 실패시킨다"
```

---

### Task 5: Claude 출력 계약과 거부 경계

**Files:**
- Create: `app/backend/app/models/plan.py`
- Test: `tests/unit/test_plan_models.py` (신규)

**Interfaces:**
- Consumes: 없음 (순수 모델)
- Produces:
  - `PlanValidationError(ValueError)`
  - `FocusPattern(pattern_id: UUID, pattern_key: str, target_form: str)`
  - `PlanQuestion(prompt: str, context: str)`
  - `SessionInstruction(target_level: str, focus: list[FocusPattern], sentence_length: str, hint_timing: str, contexts: list[str])`
  - `LevelDecision(action: Literal["keep", "up", "down"], target_level: str, reason: str)`
  - `PlanOutput(focus: list[FocusPattern], questions: list[PlanQuestion], target_level: str, reason: str, instruction: SessionInstruction, level: LevelDecision, notes: list[str])`
  - `def parse_plan(raw: str, *, current_level: str) -> PlanOutput`
  - `CEFR_LEVELS: tuple[str, ...]`

**AS5의 소유자다.** 잘못된 계획은 **저장 전에** 거부되고 job이 `last_error`와 함께 실패한다 —
반쯤 검증된 계획을 쓰지 않는다(설계서 §9 Failure).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/unit/test_plan_models.py (신규)
import json
from uuid import uuid4

import pytest

from app.models.plan import PlanValidationError, parse_plan


def _payload(**overrides: object) -> str:
    pattern_id = str(uuid4())
    body: dict[str, object] = {
        "focus": [{"pattern_id": pattern_id, "pattern_key": "article_missing", "target_form": "a/an/the"}],
        "questions": [
            {"prompt": "What did you do at work today?", "context": "work update"},
            {"prompt": "Tell me about your morning.", "context": "daily life"},
            {"prompt": "What will you do tomorrow?", "context": "plan"},
        ],
        "target_level": "A2",
        "reason": "관사를 계속 빼먹어서 오늘은 그것만 봅니다.",
        "instruction": {
            "target_level": "A2",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "two short clauses",
            "hint_timing": "offer a starter after one long pause",
            "contexts": ["work update", "daily life", "plan"],
        },
        "level": {"action": "keep", "target_level": "A2", "reason": "정답률이 아직 낮습니다."},
        "notes": ["짧은 문장에서는 관사를 붙이는데 길어지면 빼먹는다"],
    }
    body.update(overrides)
    return json.dumps(body, ensure_ascii=False)


def test_valid_plan_parses():
    result = parse_plan(_payload(), current_level="A2")

    assert len(result.focus) == 1
    assert len(result.questions) == 3
    assert result.reason.strip() != ""
    assert result.level.action == "keep"


# AS5 ① 추천 이유가 비어 있으면 거부한다 (PRD.md:189 R11-3 — 이유 없는 추천은 검증할 수 없다)
@pytest.mark.parametrize("blank", ["", "   ", "\n"])
def test_blank_reason_is_rejected(blank: str):
    with pytest.raises(PlanValidationError):
        parse_plan(_payload(reason=blank), current_level="A2")


# AS5 ② 질문 수가 3~5 밖이면 거부한다 (PRD.md:188 R11-2)
@pytest.mark.parametrize("count", [2, 6])
def test_question_count_outside_three_to_five_is_rejected(count: int):
    questions = [{"prompt": f"q{i}", "context": f"c{i}"} for i in range(count)]
    with pytest.raises(PlanValidationError):
        parse_plan(_payload(questions=questions), current_level="A2")


# 초점 패턴은 1~2개다 (PRD.md:188 · agent-system-prompt.md:19)
@pytest.mark.parametrize("count", [0, 3])
def test_focus_count_outside_one_to_two_is_rejected(count: int):
    focus = [
        {"pattern_id": str(uuid4()), "pattern_key": f"k{i}", "target_form": "f"} for i in range(count)
    ]
    with pytest.raises(PlanValidationError):
        parse_plan(_payload(focus=focus), current_level="A2")


# AS5 ③ CEFR 값역 밖이면 거부한다 (001 의 CHECK 와 같은 값역)
def test_unknown_level_is_rejected():
    with pytest.raises(PlanValidationError):
        parse_plan(_payload(target_level="Z9"), current_level="A2")


# AS7 — 두 단계 도약은 거부한다. h-doc 이 경고한 "목표 수준을 현재 수준으로 착각"을 구조로 막는다.
def test_two_step_jump_is_rejected():
    payload = _payload(
        target_level="B2",
        level={"action": "up", "target_level": "B2", "reason": "빠르게 좋아졌습니다."},
    )
    with pytest.raises(PlanValidationError):
        parse_plan(payload, current_level="A2")


# 한 단계 상향은 통과한다
def test_one_step_up_is_accepted():
    payload = _payload(
        target_level="B1",
        level={"action": "up", "target_level": "B1", "reason": "정답률이 꾸준합니다."},
        instruction={
            "target_level": "B1",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "two or three clauses",
            "hint_timing": "wait through one long pause",
            "contexts": ["work update", "daily life", "plan"],
        },
    )
    assert parse_plan(payload, current_level="A2").level.target_level == "B1"


# 하향도 허용한다 — 상향만 되면 잘못 올라간 수준이 영구히 굳는다 (설계서 §7)
def test_one_step_down_is_accepted():
    payload = _payload(
        target_level="A1",
        level={"action": "down", "target_level": "A1", "reason": "계속 막혔습니다."},
        instruction={
            "target_level": "A1",
            "focus": [{"pattern_key": "article_missing", "target_form": "a/an/the"}],
            "sentence_length": "one short clause",
            "hint_timing": "offer a starter early",
            "contexts": ["daily life", "morning", "evening"],
        },
    )
    assert parse_plan(payload, current_level="A2").level.action == "down"


# 계획의 난이도와 수준 판단이 어긋나면 거부한다 — 두 값이 다르면 어느 것이 오늘의 목표인지 모른다.
def test_target_level_must_match_level_decision():
    payload = _payload(
        target_level="A2",
        level={"action": "up", "target_level": "B1", "reason": "좋아졌습니다."},
    )
    with pytest.raises(PlanValidationError):
        parse_plan(payload, current_level="A2")


# 규격 밖 필드가 섞이면 거부한다 (슬라이스 1과 같은 extra="forbid" 규약)
def test_unknown_field_is_rejected():
    with pytest.raises(PlanValidationError):
        parse_plan(_payload(surprise="nope"), current_level="A2")


# 모델이 JSON 앞뒤에 말을 붙여도 파싱한다 (슬라이스 1의 _json_candidates 와 같은 관용)
def test_prose_wrapped_json_parses():
    raw = "여기 계획입니다:\n" + _payload() + "\n확인해 주세요."
    assert parse_plan(raw, current_level="A2").target_level == "A2"
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_plan_models.py -c pyproject.toml -v`
Expected: 전건 FAIL (`ModuleNotFoundError: app.models.plan`). "N건 중 N건 red"를 출력으로 센다.

- [ ] **Step 3: 최소 구현**

`app/backend/app/models/plan.py` — `models/analysis.py`의 관례를 그대로 따른다:
`pydantic.ConfigDict(extra="forbid", str_strip_whitespace=True)` · `Literal` 값역 ·
JSON 후보 추출 → `model_validate` → 실패를 도메인 예외로 감싼다.

```python
# 001 의 users.current_level / learning_scenarios.level CHECK 와 **같은 값역**이다.
# 여기서 값을 늘리면 DB CHECK 도 함께 고쳐야 한다(두 곳이 SoT를 나눠 갖지 않게).
CEFR_LEVELS: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

CefrLevel = Literal["A1", "A2", "B1", "B2", "C1", "C2"]


class PlanValidationError(ValueError):
    """Claude 계획 출력이 계약을 지키지 않았다.

    `AnalysisValidationError`와 같은 자리를 차지한다 — 워커가 이것을 잡아 job을
    `last_error`와 함께 실패시키고 **계획을 저장하지 않는다**(설계서 §9 Failure).
    """


def _one_step_or_same(current: str, target: str) -> bool:
    """수준 이동이 한 칸 이내인지. 두 칸 도약을 **구조로** 막는다 (설계서 §7).

    h-doc이 경고한 "목표 수준을 현재 수준으로 착각"이 이 자리에서 일어난다 —
    AWS 보고 수준 문형으로 예문을 만들면 첫 세션에서 얼어붙는다.
    """
    return abs(CEFR_LEVELS.index(target) - CEFR_LEVELS.index(current)) <= 1


def parse_plan(raw: str, *, current_level: str) -> PlanOutput:
    """모델 출력 문자열 → 검증된 계획. 실패는 전부 `PlanValidationError`다.

    `current_level`을 인자로 받는 이유: 두 단계 도약 여부는 **출력만으로는 판정할 수 없다.**
    """
```

⚠️ **`questions`·`focus` 길이와 `reason` 공백은 pydantic에서도 막고 DB CHECK에서도 막는다.**
이중 방어가 중복이 아닌 이유: pydantic은 **읽을 수 있는 오류**를 주고 DB CHECK는
**다른 경로로 들어온 쓰기**까지 막는다(백필 스크립트 등).

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_plan_models.py -c pyproject.toml -v`
Expected: 전건 PASS. `ty check`도 함께 — `Literal`과 `tuple[str, ...]`의 정합이 걸리는 자리다.

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/models/plan.py tests/unit/test_plan_models.py
git commit -m "feat: 계획 출력 계약과 거부 경계 (AS5)

- 이유 빈값·질문 수·초점 수·CEFR 값역·두 단계 도약을 저장 전에 거부한다
- 계획의 난이도와 수준 판단이 어긋나는 출력도 거부한다 — 두 값이 다르면
  어느 것이 오늘의 목표인지 알 수 없다
- 수준 이동 판정에 current_level 이 필요하다: 출력만으로는 도약을 알 수 없다"
```

---

### Task 6: 계획 프롬프트를 조립한다

**Files:**
- Modify: `app/backend/app/services/plan.py`
- Test: `tests/unit/test_plan.py` (신규)

**Interfaces:**
- Consumes: Task 4의 `PlanInput`
- Produces: `def build_plan_prompt(data: PlanInput) -> str`

**h-doc 프로필이 문구를 지배한다**: 단문·단일 절 기준 · 일상 → 업무 협업 순서 · 학습자용 설명은 한국어 ·
**목표 수준(AWS 보고) 문형으로 예문을 만들지 않는다.** 그리고 **발음을 채점하지 않는다** —
발음은 시도 사실만 넘기고 점수·등급을 요구하지 않는다(`docs/requirements-summary.md:120-121`).

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/unit/test_plan.py (신규)
from app.services.plan import build_plan_prompt


def test_prompt_lists_every_due_pattern(plan_input_factory):
    data = plan_input_factory(due_keys=["article_missing", "verb_tense_past", "preposition_at"])

    prompt = build_plan_prompt(data)

    # AS1 — 하나라도 빠지면 실패다.
    for key in ("article_missing", "verb_tense_past", "preposition_at"):
        assert key in prompt


def test_prompt_asks_for_the_output_contract(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 출력 계약(Task 5)과 같은 이름을 요구해야 파싱이 성립한다.
    for field in ("focus", "questions", "target_level", "reason", "instruction", "level", "notes"):
        assert field in prompt


def test_prompt_states_the_documented_counts_only(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    assert "1-2" in prompt or "one or two" in prompt   # 초점 패턴 (PRD.md:188)
    assert "3-5" in prompt or "three to five" in prompt  # 질문 (PRD.md:188)


def test_prompt_requires_korean_reason(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    assert "Korean" in prompt
    assert "reason" in prompt


def test_prompt_keeps_pronunciation_separate_from_grammar(plan_input_factory):
    data = plan_input_factory(
        due_keys=["article_missing"],
        pronunciation=[("th_as_s", "incorrect", 4)],
    )

    prompt = build_plan_prompt(data)

    # §4.4 주의 2 — 두 계산 기준을 한 정렬에 섞으면 발음이 부당하게 위/아래로 간다.
    assert "th_as_s" in prompt
    grammar_at = prompt.index("article_missing")
    pron_at = prompt.index("th_as_s")
    assert grammar_at != pron_at  # 서로 다른 절에 있다


def test_prompt_never_asks_for_a_pronunciation_score(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory(pronunciation=[("th_as_s", "incorrect", 4)]))

    # requirements-summary.md:120-121 — 점수·등급·유사도 지표는 하지 않는 것이다.
    lowered = prompt.lower()
    for banned in ("pronunciation score", "accent rating", "native-likeness", "how native"):
        assert banned not in lowered


def test_prompt_marks_the_chronic_signal_when_present(plan_input_factory):
    data = plan_input_factory(due_keys=["article_missing"], chronic_flagged=["article_missing"])

    prompt = build_plan_prompt(data)

    # §6.2 — 3단계를 소진한 뒤 재발한 것은 **사실**로 넘기고 만성 판정은 모델이 한다.
    assert "completed all three review stages" in prompt


def test_prompt_does_not_invent_a_size_limit(plan_input_factory):
    prompt = build_plan_prompt(plan_input_factory())

    # 설계서 §3.4 — 지시문 크기 상한의 구체 수치는 Nova 초기화 실측 후에 정한다.
    for banned in ("at most 500", "maximum 1000", "word limit"):
        assert banned not in prompt.lower()
```

⚠️ 픽스처 `plan_input_factory`는 이 태스크가 `tests/conftest.py`에 만든다 — `PlanInput`을
DB 없이 만들어 주는 순수 팩토리다(프롬프트 조립은 순수 함수라 DB가 필요 없다).

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_plan.py -c pyproject.toml -v`
Expected: **8건 FAIL** (`ImportError: cannot import name 'build_plan_prompt'`).

- [ ] **Step 3: 최소 구현**

`plan.py`에 프롬프트 조립을 더한다. 절 구성은 설계서 §4의 3계층 순서를 그대로 따른다:
① 오늘 다뤄야 하는 목록 → ② 최근 창 → ③ 만성 사실 → ④ 발음 시도(별도 절) → ⑤ 출력 규격.

```python
_PROMPT_HEADER = """\
You plan the next English speaking session for one Korean learner.

Learner profile: can handle greetings, small talk, and simple daily-life sentences; mostly uses
short patterns such as "I want to...", "I need to...", "I'd like to...". Long-term goal is to
join business meetings and report project status. Start from daily life and move toward work
topics — do not write examples at the long-term goal level.

You decide what the weakness really is, which situations to practise it in, and the difficulty.
The lists below are **facts**, already computed. Do not recompute them and do not drop any of them.
"""

_OUTPUT_SPEC = """\
Return one JSON object and nothing else. Keys:
- focus: one or two patterns, each {pattern_id, pattern_key, target_form}. Pick from the lists above.
- questions: three to five items, each {prompt, context}. Same target form, different situations.
- target_level: one CEFR code. It must equal level.target_level.
- reason: one short sentence **in Korean**, addressed to the learner, saying why today's practice
  is this. Never leave it empty.
- instruction: {target_level, focus:[{pattern_key, target_form}], sentence_length, hint_timing, contexts}
  — sentence_length and hint_timing are short English phrases that will be spliced into the tutor's
  instructions. contexts is the list of situations for today.
- level: {action: keep|up|down, target_level, reason}. Move at most one CEFR step from the current
  level, in either direction. Going down is allowed and is better than staying too hard.
- notes: observations worth keeping that numbers cannot hold — for example "adds articles in short
  sentences but drops them once the sentence gets longer". Empty list is fine.
"""
```

발음 절은 **문법 절과 분리해** 넣고, 시도 수 기준이 다르다는 것을 문장으로 알린다.

```python
_PRONUNCIATION_NOTE = """\
Pronunciation attempts (separate list — counted per attempt, not per error occurrence, so do not
rank these against the grammar counts above):
"""
```

만성 신호는 **사실 문장**으로만 넣는다.

```python
        if metric.pattern_id in data.chronic_pattern_ids:
            line += "  [completed all three review stages before, then came back]"
```

⚠️ **크기 상한을 넣지 않는다.** 설계서 §3.4가 "구체 수치는 Nova 초기화 시간을 실측해 정한다,
지금 발명하지 않는다"고 했다. 상한이 필요해지면 그때 초점 패턴 수와 상황 목록을 먼저 줄인다.

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_plan.py -c pyproject.toml -v`
Expected: 전건 PASS. 전체 게이트도 함께.

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/services/plan.py tests/unit/test_plan.py tests/conftest.py
git commit -m "feat: 계획 프롬프트 조립

- 설계서 §4 의 3계층 순서를 그대로 따른다. 목록은 사실로 넘기고 판단은 모델이 한다
- 발음은 별도 절이다: 시도 수 기준이라 문법의 발생 수 기준과 한 정렬에 섞으면
  발음이 부당하게 위/아래로 간다(§4.4 주의 2)
- 발음 점수·등급을 요구하지 않는다(requirements-summary.md:120-121)
- 지시문 크기 상한을 넣지 않는다 — 실측 전에 발명하지 않는다(§3.4)"
```

---

### Task 7: 계획·노트·수준을 한 트랜잭션에 저장한다

**Files:**
- Modify: `app/backend/app/services/plan.py` (`process_plan` 완성)
- Test: `tests/unit/test_plan.py` (수정), `tests/integration/test_plan_pipeline.py` (신규)

**Interfaces:**
- Consumes: Task 4 `load_plan_input` · Task 5 `parse_plan` · Task 6 `build_plan_prompt` ·
  기존 `jobs.complete(conn, job_id, lease_token)` · `jobs.fail_or_retry(conn, job_id, lease_token, error)`
- Produces: `async def process_plan(pool, claude, job) -> None` (완성형 — `NotImplementedError` 제거)

**설계서 §9 Contract의 소유자다**: 출력은 `session_plans` 1행 + `learner_notes` 1행 +
`users.current_level` 갱신이 **한 트랜잭션**. 부분 반영을 남기지 않는다.

**`source`에 대한 사실 기록**: 이 슬라이스는 `'agent'`만 쓴다. Claude가 실패하면 계획 행을
**만들지 않고**(§3.3이 "계획 미사용을 행 부재로 판별한다"고 정했다) 세션 시작이 시나리오 뱅크로
떨어진다. `'fallback'` 값은 설계서 §5.1이 정의한 값역이라 CHECK에 남기지만 **이 슬라이스에서
쓰이는 경로가 없다** — 나중에 "계획은 만들었으나 뱅크 내용을 썼다"가 생기면 그때 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/unit/test_plan.py 에 추가
# AS7 — 수준이 정확히 한 단계 올라가고 사유가 노트에 남는다.
@pytest.mark.asyncio
async def test_level_moves_exactly_one_step_and_reason_is_kept(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history
):
    session_id, user_id = await ended_session_with_history(db_pool)
    claude = fake_claude(response=plan_json(level_action="up", target_level="B1"))
    job = await claim_plan_job(db_pool, session_id)

    await process_plan(db_pool, claude, job)

    async with db_pool.acquire() as conn:
        assert await conn.fetchval(
            "select current_level from users where id = $1", user_id
        ) == "B1"
        note = await conn.fetchrow(
            "select note from learner_notes where user_id = $1 order by created_at desc limit 1",
            user_id,
        )
        assert "정답률" in note["note"]


# AS8 — 노트는 덧붙이기만 한다. 두 번 돌면 두 행이고 이전 행이 남는다.
@pytest.mark.asyncio
async def test_notes_are_append_only(db_pool, fake_claude, ended_session_with_history):
    session_id, user_id = await ended_session_with_history(db_pool)
    for note_text in ("첫 관찰", "둘째 관찰"):
        job = await claim_plan_job(db_pool, session_id, reset=True)
        await process_plan(db_pool, fake_claude(response=plan_json(note=note_text)), job)

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "select note from learner_notes where user_id = $1 order by created_at", user_id
        )
    assert len(rows) == 2
    assert "첫 관찰" in rows[0]["note"]


# 설계서 §9 Failure — 검증 거부는 계획을 **저장하지 않고** job 을 실패시킨다.
@pytest.mark.asyncio
async def test_rejected_plan_stores_nothing_and_records_error(
    db_pool, fake_claude, ended_session_with_history
):
    session_id, user_id = await ended_session_with_history(db_pool)
    job = await claim_plan_job(db_pool, session_id)

    await process_plan(db_pool, fake_claude(response=plan_json(reason="")), job)

    async with db_pool.acquire() as conn:
        assert await conn.fetchval("select count(*) from session_plans") == 0
        assert await conn.fetchval("select count(*) from learner_notes") == 0
        assert await conn.fetchval(
            "select current_level from users where id = $1", user_id
        ) == "A2"
        row = await conn.fetchrow("select status, last_error from analysis_jobs where id = $1", job.id)
    assert row["last_error"] is not None


# 부분 반영이 없다 — 수준 갱신이 실패하면 계획도 남지 않는다.
@pytest.mark.asyncio
async def test_no_partial_write_when_plan_insert_fails(
    db_pool: asyncpg.Pool, fake_claude, ended_session_with_history
):
    # 실패를 만드는 방법: 그 세션에 계획 행을 **미리** 넣어 unique(session_id)를 건드린다.
    # ⚠️ 사용자를 지우는 방법은 쓸 수 없다 — learning_sessions.user_id 가 cascade 라 세션까지
    # 사라지고, 그러면 process_plan 이 "세션 없음" 정상 실패 경로로 빠져 트랜잭션을 열지도 않는다.
    session_id, user_id = await ended_session_with_history(db_pool)
    questions = '[{"prompt":"q1","context":"c1"},{"prompt":"q2","context":"c2"},{"prompt":"q3","context":"c3"}]'
    async with db_pool.acquire() as conn:
        await conn.execute(
            "insert into session_plans "
            "(session_id, focus_pattern_ids, questions, target_level, reason, instruction, source) "
            "values ($1, $2, $3::jsonb, 'A2', '먼저 있던 계획', '{}'::jsonb, 'agent')",
            session_id,
            [uuid4()],
            questions,
        )
    job = await claim_plan_job(db_pool, session_id)
    claude = fake_claude(response=plan_json(level_action="up", target_level="B1"))

    with pytest.raises(asyncpg.UniqueViolationError):
        await process_plan(db_pool, claude, job)

    async with db_pool.acquire() as conn:
        # 노트와 수준 갱신이 같은 트랜잭션에 있었으므로 함께 되돌아간다
        assert await conn.fetchval("select count(*) from learner_notes") == 0
        assert await conn.fetchval("select current_level from users where id = $1", user_id) == "A2"
        assert await conn.fetchval(
            "select reason from session_plans where session_id = $1", session_id
        ) == "먼저 있던 계획"
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_plan.py -c pyproject.toml -v -k "level or append or rejected or partial"`
Expected: **4건 FAIL** — `NotImplementedError: Task 7이 저장까지 채운다`가 그대로 올라온다.

- [ ] **Step 3: 최소 구현**

```python
async def process_plan(pool: asyncpg.Pool, claude: ClaudeClient, job: ClaimedJob) -> None:
    """계획 생성 job 하나. 설계서 §3.1의 두 번째 화살표에 해당한다.

    **한 트랜잭션**에 계획·노트·수준 갱신·job 종결을 담는다(§9 Contract) — 절반만 반영된
    상태를 남기지 않는다. Claude 호출은 트랜잭션 **밖**에서 한다: 네트워크 대기 동안 행 잠금을
    들고 있으면 다른 job 이 막힌다.
    """
    if job.session_id is None:
        await report_failure(pool, job, f"plan job {job.id} has no session target")
        return

    async with pool.acquire() as conn:
        owner = await conn.fetchrow(
            "select user_id from learning_sessions where id = $1", job.session_id
        )
        if owner is None:
            await report_failure(pool, job, f"session {job.session_id} not found")
            return
        data = await load_plan_input(conn, owner["user_id"])

    raw = await claude.analyze(build_plan_prompt(data))

    try:
        plan = parse_plan(raw, current_level=data.current_level)
    except PlanValidationError as exc:
        # 예상된 결과다 — 반쯤 검증된 계획을 쓰지 않는다(§9 Failure).
        await report_failure(pool, job, f"plan contract violated: {exc}")
        return

    async with pool.acquire() as conn, conn.transaction():
        await conn.execute(
            _INSERT_PLAN_SQL,
            job.session_id,
            [item.pattern_id for item in plan.focus],
            json.dumps([q.model_dump() for q in plan.questions], ensure_ascii=False),
            plan.target_level,
            plan.reason,
            json.dumps(plan.instruction.model_dump(), ensure_ascii=False),
            "agent",
        )
        await conn.execute(
            _INSERT_NOTE_SQL,
            owner["user_id"],
            json.dumps(
                {"observations": plan.notes, "level_reason": plan.level.reason},
                ensure_ascii=False,
            ),
            data.window_from,
            data.window_to,
        )
        await conn.execute(
            "update users set current_level = $2 where id = $1",
            owner["user_id"],
            plan.level.target_level,
        )
        await complete(conn, job.id, job.lease_token)
```

⚠️ **jsonb 바인딩은 `str`이다.** asyncpg는 jsonb 컬럼에 파이썬 `list`/`dict`를 받지 않고
`DataError: expected str, got list`로 거부한다(슬라이스 1에서 실측). 쓸 때 `json.dumps(..., ensure_ascii=False)`,
읽을 때 `json.loads`. `ensure_ascii=False`가 한글을 그대로 보존한다.

⚠️ **`NotImplementedError`가 사라졌는지 확인한다** — Step 4에서 grep으로 본다.

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -q` → 전건 PASS.
Run: `grep -rn "NotImplementedError" app/` → **0건이어야 한다.**
Run: `.venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check` → 전부 exit 0.

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/services/plan.py tests/unit/test_plan.py tests/conftest.py
git commit -m "feat: 계획·관찰 노트·수준 갱신을 한 트랜잭션에 저장한다

- 부분 반영을 남기지 않는다(설계서 §9 Contract)
- Claude 호출은 트랜잭션 밖에서 한다 — 네트워크 대기 중 행 잠금을 들고 있으면
  다른 job 이 막힌다
- 계약 위반은 계획을 저장하지 않고 last_error 와 함께 실패시킨다
- 이 슬라이스는 source='agent' 만 쓴다: 실패하면 행을 만들지 않고 세션 시작이
  시나리오 뱅크로 떨어진다(§3.3)"
```

---

### Task 8: 세션 시작이 준비된 계획을 읽는다 (없으면 폴백)

**Files:**
- Modify: `app/backend/app/services/sessions.py`
- Test: `tests/unit/test_sessions.py` (수정), `tests/integration/test_plan_pipeline.py` (수정)

**Interfaces:**
- Consumes: Task 1의 `session_plans` · Task 5의 `SessionInstruction`
- Produces: `PreparedPlan(plan_id: UUID, reason: str, instruction: SessionInstruction)` ·
  `async def load_prepared_plan(conn: asyncpg.Connection, user_id: UUID) -> PreparedPlan | None`

**설계서 §3.4를 지킨다**: 세션 시작에 Claude 호출이 없고 **조회만** 한다. 쓰기를 넣지 않는다.
**§9 Contract**: 반환은 항상 성공한다 — 계획 부재가 세션 시작 실패로 번역되지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/unit/test_sessions.py 에 추가
# 직전 세션이 만든 계획을 읽는다 (계획 문서 「구현 전 정정」 — session_id 는 만든 세션이다).
@pytest.mark.asyncio
async def test_load_prepared_plan_returns_latest_plan(db_conn, seed_plan_for_session):
    user_id, _older = await seed_plan_for_session(db_conn, reason="오래된 이유", days_ago=3)
    await seed_plan_for_session(db_conn, user_id=user_id, reason="최신 이유", days_ago=0)

    prepared = await load_prepared_plan(db_conn, user_id)

    assert prepared is not None
    assert prepared.reason == "최신 이유"


# AS4 — 계획이 없으면 None 이고, 세션 시작은 그래도 성공한다.
@pytest.mark.asyncio
async def test_load_prepared_plan_returns_none_when_absent(db_conn, seed_user):
    user_id = await seed_user(db_conn)

    assert await load_prepared_plan(db_conn, user_id) is None


# 폴백은 수준이 맞는 시나리오를 고른다.
# ⚠️ `create_session`은 **pool** 을 받는다(`create_session(pool, user_id)`) — 그래서 이 두 테스트는
#    `db_conn`이 아니라 `db_pool` 픽스처를 쓴다. conn 을 pool 처럼 감싸는 헬퍼를 만들지 않는다.
@pytest.mark.asyncio
async def test_session_creation_prefers_scenario_matching_level(db_pool: asyncpg.Pool, seed_user):
    async with db_pool.acquire() as conn:
        user_id = await seed_user(conn, level="B1")
        await conn.execute(
            "insert into learning_scenarios (id, category, level, title, prompt_template) "
            "values ($1, 'work', 'B1', 'B1 scenario', 'Tell me about your project.')",
            uuid4(),
        )

    session_id = await create_session(db_pool, user_id)

    async with db_pool.acquire() as conn:
        level = await conn.fetchval(
            "select s.level from learning_scenarios s "
            "join learning_sessions ls on ls.scenario_id = s.id where ls.id = $1",
            session_id,
        )
    assert level == "B1"


# 수준에 맞는 시나리오가 없으면 시드된 첫 행으로 떨어지고, 시작이 실패하지 않는다.
# (시드는 A2 3행뿐이라 C2 사용자는 이 경로로 온다 — 계획 문서 「구현 전 정정」)
@pytest.mark.asyncio
async def test_session_creation_falls_back_when_no_level_match(db_pool: asyncpg.Pool, seed_user):
    async with db_pool.acquire() as conn:
        user_id = await seed_user(conn, level="C2")

    session_id = await create_session(db_pool, user_id)

    async with db_pool.acquire() as conn:
        has_scenario = await conn.fetchval(
            "select scenario_id is not null from learning_sessions where id = $1", session_id
        )
    assert has_scenario is True
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_sessions.py -c pyproject.toml -v -k "prepared or scenario"`
Expected: **4건 FAIL** — 앞 둘은 `ImportError: load_prepared_plan`, 뒤 둘은 현재 SQL이 수준을 보지 않아
`A2` 시나리오가 붙는다.

- [ ] **Step 3: 최소 구현**

```python
# 계획은 **직전 세션이 만든 것**이다(계획 문서 「구현 전 정정」). 소비 표시를 하지 않으므로
# 언제나 최신 1행을 읽는다 — 세션 시작을 조회 1회로 유지하기 위한 선택이다(§3.4).
_PREPARED_PLAN_SQL = """
select sp.id as plan_id, sp.reason, sp.instruction
  from session_plans sp
  join learning_sessions ls on ls.id = sp.session_id
 where ls.user_id = $1
 order by sp.created_at desc
 limit 1
"""
```

`_CREATE_SESSION_SQL`의 시나리오 서브쿼리를 수준 우선으로 바꾼다. **시드를 늘리지 않는다.**

```sql
insert into learning_sessions (user_id, scenario_id, mode)
values ($1,
        coalesce(
          -- 수준이 맞는 시나리오를 먼저 찾는다 (§3.3)
          (select s.id from learning_scenarios s
            where s.level = (select current_level from users where id = $1)
            order by s.created_at, s.id limit 1),
          -- 없으면 기존 동작 그대로. 시드가 A2 3행뿐이라 수준이 올라가면 이 경로로 온다 —
          -- 학습이 막히는 것보다 시나리오가 조금 쉬운 것이 낫다(§9 Failure).
          (select s.id from learning_scenarios s order by s.created_at, s.id limit 1)
        ),
        'speaking')
returning id
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -q` → 전건 PASS.
⚠️ **`create_session`은 기존 테스트가 여럿 쓴다** — 시나리오 id 를 단정하는 테스트가 있으면
수준 일치 결과로 바뀔 수 있다. `grep -rn "scenario_id" ../../tests`로 먼저 훑는다.

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/services/sessions.py tests/unit/test_sessions.py
git commit -m "feat: 세션 시작이 준비된 계획을 읽고 없으면 폴백한다

- 조회만 한다: 세션 시작에 쓰기를 넣지 않는다(설계서 §3.4 — 시작은 조회 1회)
- 계획 부재가 시작 실패로 번역되지 않는다(§9 Contract)
- 폴백은 수준 일치 우선, 없으면 기존 동작. 시드가 A2 3행뿐이라 수준이 올라가면
  일치가 0행이 된다 — 새 시나리오를 발명해 시드하지 않는다"
```

---

### Task 9: 가짜 대화 상대가 지시문을 받아 보관한다 (AS6의 검증 수단)

**Files:**
- Modify: `app/backend/app/audio_gateway/stub.py`
- Test: `tests/unit/test_stub_adapter.py` (신규 또는 기존 스텁 테스트 파일 수정)

**Interfaces:**
- Consumes: 없음
- Produces: `StubVoiceAdapter(mode: StubMode = "fixture", *, instructions: str | None = None)` ·
  읽기 전용 속성 `instructions: str | None`

**왜 이 태스크가 필수인가**: 2026-09-04 결정("실물 음성 확인은 나중, 스텁 관통으로 전달 경로를
검증한다")의 **유일한 검증 수단**이다. 지금 `stub.py:40`의 생성 함수는 지시문을 받는 인자가 없어
설계서 AS6("스텁이 기록한 지시문에 값이 들어 있다")을 **판정할 수 없다.**

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
from app.audio_gateway.stub import StubVoiceAdapter


def test_stub_keeps_the_instructions_it_was_given():
    adapter = StubVoiceAdapter("fixture", instructions="today: article_missing, A2")

    assert adapter.instructions == "today: article_missing, A2"


def test_stub_without_instructions_reports_none():
    assert StubVoiceAdapter("fixture").instructions is None


@pytest.mark.asyncio
async def test_stub_does_not_change_behaviour_because_of_instructions():
    # 설계서 §5.2 — 스텁은 지시문을 **받아서 기록만** 한다. 발화는 픽스처가 결정한다.
    plain = StubVoiceAdapter("fixture")
    with_instructions = StubVoiceAdapter("fixture", instructions="anything")

    await plain.start()
    await with_instructions.start()

    assert type(plain) is type(with_instructions)
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_stub_adapter.py -c pyproject.toml -v`
Expected: **3건 FAIL** — `TypeError: StubVoiceAdapter.__init__() got an unexpected keyword argument 'instructions'`.

- [ ] **Step 3: 최소 구현**

```python
    def __init__(self, mode: StubMode = "fixture", *, instructions: str | None = None) -> None:
        """`instructions`는 **받아서 보관만** 한다 — 발화는 픽스처가 결정한다(설계서 §5.2).

        스텁이 이 값을 쓰지 않는데도 받는 이유: 지시문이 조립 지점에서 어댑터까지
        실제로 도달했는지 **판정할 수단**이 이것뿐이다(AS6). 실물 Nova 응대가 달라지는지는
        별개 확인이고 이 슬라이스의 범위가 아니다.
        """
        self._mode = mode
        self._instructions = instructions

    @property
    def instructions(self) -> str | None:
        return self._instructions
```

⚠️ **키워드 전용 인자로 둔다**(`*` 뒤). 위치 인자로 두면 기존 `StubVoiceAdapter("fixture")` 호출과
`StubVoiceAdapter("unresponsive")`가 조용히 의미를 바꿀 수 있다.

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -q` → 전건 PASS. `ty check` 함께.

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/audio_gateway/stub.py tests/unit/test_stub_adapter.py
git commit -m "feat: 스텁 어댑터가 지시문을 받아 보관한다

- 설계서 AS6('스텁이 기록한 지시문에 값이 들어 있다')을 판정할 수단이 없었다
- 받아서 보관만 한다: 발화는 픽스처가 결정한다(§5.2). 동작은 바뀌지 않는다
- 키워드 전용 인자로 둔다 — 기존 위치 인자 호출의 의미가 바뀌지 않게"
```

---

### Task 10: 지시문에 계획을 얹는다 (+ 빠져 있던 65% 규칙을 넣는다)

**Files:**
- Modify: `app/backend/app/audio_gateway/nova.py` (`SYSTEM_PROMPT`, `build_system_prompt`)
- Modify: `app/backend/app/audio_gateway/factory.py` (`create_voice_adapter`)
- Modify: `app/backend/app/api/ws.py` (세션 시작이 계획을 읽어 넘긴다)
- Test: `tests/unit/test_nova.py`, `tests/integration/test_ws.py` (수정)

**Interfaces:**
- Consumes: Task 5 `SessionInstruction` · Task 8 `load_prepared_plan` · Task 9 스텁의 `instructions`
- Produces:
  - `def build_system_prompt(known_sounds: Sequence[str], plan: SessionInstruction | None = None) -> str`
  - `def create_voice_adapter(settings: Settings, *, known_sounds: Sequence[str] = (), plan: SessionInstruction | None = None) -> VoiceAdapter`

**포트를 건드리지 않는다.** `start()`는 계속 인자가 없다. 조립은 계속 `factory.py`가 소유한다 —
`factory.py:31-36`이 G-3 근거로 "소켓은 데이터만 넘기고 조립은 여기서 한다"를 못 박았고, 이 태스크는
그 규약을 **그대로 따른다**(계획도 데이터로 넘긴다).

**이 태스크가 닫는 어긋남 3건** (근거는 `docs/consistency-audit-2026-09-04.md`):
1. **65% 규칙이 실제 지시문에 없었다** — `docs/PRD.md:59`·R10-8이 요구하는데 대화 상대가 모르고 있었다.
2. **가변부의 "힌트를 얼마나 이르게 줄지"가 이미 고정돼 있었다**(`nova.py:116`·`:121`) — 계획이 그 두 줄을
   **대체한다**는 것을 문장으로 명시한다. 안 하면 모순된 지시가 함께 나간다.
3. **저장은 구조(jsonb), 문장 조립은 읽는 쪽** — 변환 규칙이 없던 자리를 여기서 정한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/unit/test_nova.py 에 추가
from app.audio_gateway.nova import SYSTEM_PROMPT, build_system_prompt
from app.models.plan import FocusPattern, SessionInstruction


def _instruction(**overrides: object) -> SessionInstruction:
    body: dict[str, object] = {
        "target_level": "B1",
        "focus": [FocusPattern(pattern_id=uuid4(), pattern_key="article_missing", target_form="a/an/the")],
        "sentence_length": "two or three short clauses",
        "hint_timing": "wait through one long pause before offering a starter",
        "contexts": ["work update", "daily life", "weekend plan"],
    }
    body.update(overrides)
    return SessionInstruction(**body)


# PRD.md:59 · R10-8 — 요구사항인데 실제 지시문에 없었다.
def test_fixed_prompt_states_the_65_percent_target():
    assert "65%" in SYSTEM_PROMPT


def test_plan_none_returns_prompt_unchanged_apart_from_sounds():
    assert build_system_prompt((), None) == SYSTEM_PROMPT


def test_plan_block_carries_level_focus_and_contexts():
    prompt = build_system_prompt((), _instruction())

    assert "B1" in prompt
    assert "a/an/the" in prompt
    assert "work update" in prompt
    assert "two or three short clauses" in prompt


# 어긋남 ② — 계획의 힌트 시점이 고정 규칙을 **대체한다**는 것이 문장으로 있어야 한다.
def test_plan_block_says_it_overrides_the_general_hint_rule():
    prompt = build_system_prompt((), _instruction())

    assert "instead of the general hint rule" in prompt
    assert "wait through one long pause before offering a starter" in prompt


# 발음 소리 목록과 계획이 함께 있어도 둘 다 실린다 (G-3 블록을 깨지 않는다).
def test_sounds_and_plan_can_coexist():
    prompt = build_system_prompt(("th_as_s",), _instruction())

    assert "th_as_s" in prompt
    assert "article_missing" in prompt or "a/an/the" in prompt


# 기존 tripwire 가 계속 산다 — 대기 규칙을 지우지 않았는지 본다.
def test_system_prompt_still_tells_the_tutor_to_wait_through_a_pause():
    assert "do not fill it with another question" in SYSTEM_PROMPT
```

```python
# tests/integration/test_ws.py 에 추가 — AS6 의 종단 판정
@pytest.mark.asyncio
async def test_session_start_passes_plan_instruction_to_the_adapter(
    db_pool, seed_plan_for_session, ws_client
):
    user_id, _ = await seed_plan_for_session(db_pool, target_level="B1", reason="관사를 봅니다")

    adapter = await ws_client.start_session_and_capture_adapter(user_id)

    # 스텁이 보관한 지시문에 계획 값이 들어 있다 (설계서 AS6)
    assert adapter.instructions is not None
    assert "B1" in adapter.instructions


@pytest.mark.asyncio
async def test_session_start_without_plan_uses_the_fixed_prompt_only(db_pool, seed_user, ws_client):
    user_id = await seed_user(db_pool)

    adapter = await ws_client.start_session_and_capture_adapter(user_id)

    # AS4 — 계획이 없어도 시작은 성공하고, 지시문은 고정부만이다.
    assert adapter.instructions == SYSTEM_PROMPT
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/unit/test_nova.py -c pyproject.toml -v -k "65 or plan_block or plan_none or coexist"`
Expected: **5건 FAIL** — `65%`가 상수에 없고 `build_system_prompt`가 두 번째 인자를 받지 않는다.
통합 2건은 픽스처가 없어 에러. **기존 tripwire 테스트는 이 시점에도 PASS여야 한다**(그것은 회귀 감시용이다).

- [ ] **Step 3: 최소 구현**

`SYSTEM_PROMPT`에 규칙 하나를 더한다. **기존 번호를 밀지 않도록 발음 절 앞, 규칙 6 다음에 넣는다.**

```python
# 규칙 번호를 매기는 문구라 삽입 위치가 중요하다 — 기존 7~10(발음)이 서로를 번호로
# 참조하므로(규칙 10이 규칙 4를 가리킨다) 그 앞에 넣고 이후 번호를 하나씩 올린다.
# 이 규칙은 PRD.md:59 · R10-8 이 요구하는데 지시문에 없던 것이다(2026-09-04 점검).
"""
7. Aim for the learner to speak at least 65% of the session. Keep your own turns short.
"""
```

⚠️ **발음 규칙의 번호가 7~10 → 8~11로 밀린다.** 규칙 10이 "규칙 4의 상한"을 번호로 참조하고
`test_nova.py`가 그 문구를 단정하므로, **번호를 옮긴 뒤 그 참조와 테스트 단정을 함께 고친다.**
`grep -n "규칙 [0-9]\|rule [0-9]" app/audio_gateway/nova.py ../../tests/unit/test_nova.py`로 전부 찾는다.

`build_system_prompt`에 계획 블록을 더한다.

```python
def build_system_prompt(
    known_sounds: Sequence[str], plan: SessionInstruction | None = None
) -> str:
    """세션용 지시문 = 기본 문구 + 놓친 소리 목록 + **오늘의 계획**.

    계획을 문장으로 바꾸는 것은 **읽는 쪽의 일이다** — `session_plans.instruction`은 구조로
    저장되고(jsonb) 여기서 문장이 된다. 설계서가 이 변환을 정하지 않아 이 계획이 정했다.

    ⚠️ 계획 블록은 위 고정 규칙 중 **힌트 시점만 대체한다**. 대체한다고 문장으로 쓰지 않으면
    "긴 침묵 뒤에만"(규칙 2)과 오늘의 지시가 함께 실려 모순된 지시문이 된다.
    """
    prompt = SYSTEM_PROMPT
    if known_sounds:
        prompt = f"{prompt}\n\n" + _sounds_block(known_sounds)
    if plan is None:
        return prompt
    forms = ", ".join(f"{item.pattern_key} ({item.target_form})" for item in plan.focus)
    contexts = ", ".join(plan.contexts)
    return (
        f"{prompt}\n\n"
        "Today's plan:\n"
        f"- Target level: {plan.target_level}\n"
        f"- Focus on: {forms}\n"
        f"- Aim for sentences of this shape: {plan.sentence_length}\n"
        f"- Situations to use today: {contexts}\n"
        f"- Hint timing for today, instead of the general hint rule above: {plan.hint_timing}\n"
    )
```

`factory.py` — 계획을 **데이터로** 받아 넘기고, **스텁에도 지시문을 준다**(Task 9가 만든 자리).

```python
def create_voice_adapter(
    settings: Settings,
    *,
    known_sounds: Sequence[str] = (),
    plan: SessionInstruction | None = None,
) -> VoiceAdapter:
    """`known_sounds`와 `plan`은 **데이터**다 — 조립된 지시문이 아니다 (G-3).

    (기존 docstring 유지) 계획도 같은 이유로 데이터로 받는다: 소켓 계층이 문장을 만들면
    `nova`를 import해야 하고 "어떤 구현이 붙는지 소켓은 모른다"는 이음매가 사라진다.

    스텁에도 지시문을 넘기는 이유: 전달 경로가 관통했는지 판정할 수단이 그것뿐이다(AS6).
    스텁은 값을 **보관만** 하고 발화에 쓰지 않는다.
    """
    instructions = build_system_prompt(known_sounds, plan)
    if settings.voice_adapter == STUB_ADAPTER:
        return StubVoiceAdapter("fixture", instructions=instructions)
    if settings.voice_adapter == STUB_UNRESPONSIVE_ADAPTER:
        return StubVoiceAdapter("unresponsive", instructions=instructions)
    if settings.voice_adapter == NOVA_ADAPTER:
        return NovaVoiceAdapter(settings, instructions=instructions)
    raise ValueError(f"알 수 없는 voice_adapter 설정: {settings.voice_adapter!r}")
```

`ws.py` — 이미 있는 `_load_known_sounds_or_empty` 옆에 같은 관례로 계획 조회를 둔다.
**조회 실패가 세션 시작을 막지 않는다**(§9 Contract · `ws.py:101-113`의 기존 규약과 같다).

```python
async def _load_prepared_plan_or_none(pool: asyncpg.Pool) -> SessionInstruction | None:
    """계획 조회 실패를 세션 시작 실패로 번역하지 않는다 — `_load_known_sounds_or_empty`와 같은 규약.

    계획이 없는 것과 조회가 실패한 것을 **여기서 구분하지 않는다**: 둘 다 "오늘은 고정 지시문으로
    시작한다"로 수렴하고, 그것이 §3.3이 정한 동작이다.
    """
```

그리고 어댑터 생성 호출을 고친다.

```python
            plan = await _load_prepared_plan_or_none(pool)
            adapter = create_voice_adapter(get_settings(), known_sounds=known_sounds, plan=plan)
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -q` → 전건 PASS.
⚠️ **번호 이동 때문에 `test_nova.py`가 여러 건 깨질 수 있다** — 규칙 번호를 단정하는 테스트를
전부 고친 뒤 다시 돌린다. 프론트는 아직 안 건드렸으므로 프론트 게이트는 이 태스크에서 불필요하다.

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/audio_gateway/nova.py app/backend/app/audio_gateway/factory.py \
        app/backend/app/api/ws.py tests/unit/test_nova.py tests/integration/test_ws.py
git commit -m "feat: 세션 지시문에 오늘의 계획을 얹는다 + 빠져 있던 65% 규칙을 넣는다

- 포트를 건드리지 않는다: 조립은 계속 factory 가 소유하고 계획도 데이터로 받는다(G-3)
- 계획의 힌트 시점이 고정 규칙을 **대체한다**고 문장으로 명시한다 — 안 하면
  '긴 침묵 뒤에만'과 오늘의 지시가 함께 실려 모순된다
- 65% 발화 목표는 PRD.md:59·R10-8 요구사항인데 실제 지시문에 없었다(2026-09-04 점검)
- 발음 규칙 번호가 7~10 에서 8~11 로 밀렸다: 규칙 간 상호 참조와 테스트를 함께 고쳤다
- 스텁에도 지시문을 넘긴다 — 전달 경로 관통을 판정할 수단이 그것뿐이다(AS6)"
```

---

### Task 11: 추천 이유를 화면에 한 줄로 보여준다

**Files:**
- Modify: `app/backend/app/api/results.py`
- Modify: `app/frontend/lib/api.ts`
- Modify: `app/frontend/app/page.tsx`
- Test: `tests/integration/test_plan_api.py` (신규)

**Interfaces:**
- Consumes: Task 8 `load_prepared_plan`
- Produces: `GET /api/sessions/next-plan` → `{"reason": str, "target_level": str}` 또는 `{"reason": null, "target_level": null}`

**캡틴 결정 2026-09-04**: 추천 이유를 **간략하게** 표시한다. 이 태스크가 읽는 방식:
**이유 한 문장 + 오늘의 난이도만.** 초점 패턴 목록·질문 목록은 **넣지 않는다** — 요구사항이 요구하는 것은
"왜 이 연습인지"(`docs/PRD.md:189`·`docs/requirements-summary.md:131`)이고 그 이상은 승인된 범위가 아니다.

⚠️ **이 태스크가 슬라이스 1의 "프론트 수정 0건" 제약을 끝낸다.** 그 제약은 슬라이스 1의 것이었다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

```python
# tests/integration/test_plan_api.py (신규)
@pytest.mark.asyncio
async def test_next_plan_returns_reason_and_level(api_client, db_pool, seed_plan_for_session):
    await seed_plan_for_session(db_pool, reason="관사를 계속 빼먹어서 오늘 그것만 봅니다", target_level="A2")

    response = await api_client.get("/api/sessions/next-plan")

    assert response.status_code == 200
    assert response.json() == {
        "reason": "관사를 계속 빼먹어서 오늘 그것만 봅니다",
        "target_level": "A2",
    }


@pytest.mark.asyncio
async def test_next_plan_returns_nulls_when_no_plan(api_client, db_pool, seed_user):
    await seed_user(db_pool)

    response = await api_client.get("/api/sessions/next-plan")

    # 404 가 아니다 — 계획 부재는 오류가 아니고 화면은 그 자리를 비운다(§9 Contract).
    assert response.status_code == 200
    assert response.json() == {"reason": None, "target_level": None}
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd app/backend && .venv/bin/pytest ../../tests/integration/test_plan_api.py -c pyproject.toml -v`
Expected: **2건 FAIL** — 404 (경로가 없다).

- [ ] **Step 3: 최소 구현**

`results.py`의 기존 라우터에 경로를 더한다(`router = APIRouter(prefix="/api/sessions", …)`).

⚠️ **사용자 id를 얻는 방법**: `results.py`는 지금 사용자 맥락이 **전혀 없다**(세션 id로만 조회한다 —
`user_id` 참조 0건). 그래서 `from app.api.ws import FIXED_USER_ID`로 가져온다 —
그 상수가 앱 전역의 단일 사용자 id이고, 이미 `tests/harness/inject_errors.py`가 같은 경로로
import하는 **선례가 있다**. 새 상수를 만들면 값이 두 곳에 생겨 갈라진다.

⚠️ **경로 충돌 없음을 확인했다**: `results.py`의 기존 경로는 `@router.get("/{session_id}/results")`
**하나뿐**이고 세그먼트 수가 달라 `/next-plan`을 가리지 않는다.

```python
@router.get("/next-plan")
async def next_plan(request: Request) -> dict[str, str | None]:
    """다음 세션에 쓸 계획의 **추천 이유만** 내려준다 (PRD.md:189 R11-3).

    계획이 없으면 404가 아니라 null이다 — 계획 부재는 오류가 아니고, 화면은 그 자리를
    비우기만 한다(설계서 §9 Contract: 계획 부재가 실패로 번역되지 않는다).

    초점 패턴·질문 목록을 내려주지 않는 이유: 캡틴 결정은 "간략하게 표시"였고,
    질문을 미리 보여주면 학습자가 답을 준비해 즉흥 발화 연습이 무의미해진다.
    """
```

`app/frontend/lib/api.ts` — 기존 관례(타입 + fetch 함수)를 따른다.

```typescript
/** 다음 세션 계획의 요약. 계획이 없으면 두 값이 모두 null 이다 (오류가 아니다). */
export interface NextPlanSummary {
  reason: string | null;
  target_level: string | null;
}

export async function fetchNextPlan(): Promise<NextPlanSummary> {
  const response = await fetch(`${API_BASE}/api/sessions/next-plan`);
  if (!response.ok) {
    // 계획 표시는 학습을 막지 않는다 — 실패하면 조용히 비운다.
    return { reason: null, target_level: null };
  }
  return (await response.json()) as NextPlanSummary;
}
```

`app/frontend/app/page.tsx` — 시작 화면에 **한 줄**. 이유가 없으면 아무것도 렌더하지 않는다.

```tsx
{nextPlan.reason ? (
  <p className="text-sm text-muted-foreground">
    오늘 이걸 연습해요: {nextPlan.reason}
    {nextPlan.target_level ? ` (${nextPlan.target_level})` : null}
  </p>
) : null}
```

⚠️ **실제 클래스 이름은 `page.tsx`의 기존 스타일 관례를 따른다.** 위 `className`은 그 파일에서
쓰는 토큰으로 바꿔라 — 새 색·새 토큰을 도입하지 않는다.

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd app/backend && .venv/bin/pytest -q` → 전건 PASS.
Run: `cd app/frontend && npx tsc --noEmit && npx eslint app lib` → **둘 다 exit 0.**
⚠️ **프론트 게이트는 이 태스크에서 처음 걸린다** — 슬라이스 1은 프론트를 건드리지 않았다.

- [ ] **Step 5: 커밋**

```bash
git add app/backend/app/api/results.py app/frontend/lib/api.ts app/frontend/app/page.tsx \
        tests/integration/test_plan_api.py
git commit -m "feat: 시작 화면에 추천 이유를 한 줄로 보여준다

- PRD.md:189 R11-3 · requirements-summary.md:131 이 '화면에서 볼 수 있어야 함'을
  요구하는데 담당이 없었다(2026-09-04 점검)
- 캡틴 결정대로 간략하게: 이유 한 문장 + 난이도만. 질문 목록은 내려주지 않는다 —
  미리 보면 답을 준비해 즉흥 발화 연습이 무의미해진다
- 계획 부재는 404 가 아니라 null 이다: 화면이 그 자리를 비우기만 한다"
```

---

### Task 12: 문서를 정본과 맞춘다 (+ 발음 확인 시나리오 AS11 신설)

**Files:**
- Modify: `docs/design/2026-08-25-learning-coach-agent-design.md`
- Modify: `docs/database-schema.md`
- Modify: `tests/harness/` 스모크 단정
- Modify: `TASKS.md` C절, `handoff/HANDOFF.md`

**Interfaces:** 없음 (문서 태스크)

**⚠️ 문서를 줄 번호로 인용하지 않는다**(함정 H-H). 절 제목으로 가리킨다.

- [ ] **Step 1: 설계서 6곳을 정정한다**

각 항목은 **한 줄 → 한 줄 교체**를 우선하고, `git diff -U0`로 밀린 줄이 없는지 확인한다.

1. **§5.2 전달 경로** — "`start(instruction)`으로 확장한다"를 "**팩토리 조립 경로를 확장한다**
   (`create_voice_adapter`가 계획을 데이터로 받아 `build_system_prompt`가 문장으로 만든다).
   포트는 무변경이다"로 바꾼다. 근거: 자매 설계(G-3)가 이미 그 경로를 만들었고, 포트를 확장하면
   지시문 통로가 둘이 된다. **캡틴 결정 2026-09-04.**
2. **§5.2 고정부 서술** — "고정부는 `agent-system-prompt.md`"에 한 문장을 덧붙인다:
   "⚠️ **실제 대화 상대가 받는 문구는 `audio_gateway/nova.py`의 상수다.** 이 문서는 목표 문구이고
   코드는 '대화 상대가 실제로 할 수 있는 부분'만 담는다 — 두 문서의 차이는
   `docs/consistency-audit-2026-09-04.md`가 표로 소유한다."
3. **§9 Dependency의 "`start(instruction)` 변경"** — 팩토리 경로로 고친다. 파급 제한 요건
   (세션 수명·저장·job 등록에 닿지 않는다)은 **그대로 유지한다** — 그 요건은 여전히 유효하고
   이번 구현이 실제로 지켰다.
4. **AS6** — "어댑터의 `start()`가 그 지시문을 받고"를 "**어댑터가 생성 시 그 지시문을 받고**"로 바꾼다.
5. **§10에 AS11을 신설한다** (AC11-6의 확인 시나리오 — 2026-09-04 점검에서 누락이 확인됐다):

```markdown
**AS11 — 발음이 초점 패턴에 들어올 수 있다** (요구사항 AC11-6)
Given 발음 재발화에 반복 실패한 소리가 최근 창 안에 있을 때, When 계획이 생성되면, Then 그 소리가
계획 입력의 발음 절에 **문법 목록과 분리되어** 들어오고, 초점 패턴 후보에서 배제되지 않는다.
⚠️ 발음 패턴의 `next_review_at`은 영구히 null이므로(§4.1 구현 공백 4) **복습 목록 경로로는
검증할 수 없다** — §4.4의 발음 시도 쿼리로 검증한다.
```

6. **§11 이월에 세 줄을 더한다.**

```markdown
| **고아 리퍼가 닫은 세션의 계획 생성** | 리퍼는 `end_session`을 거치지 않고 대량 UPDATE로 닫으므로(2026-09-04 리뷰에서 확인) **프로세스가 죽어 끝난 세션은 계획 job을 받지 못한다** — §3.3이 열거한 폴백 사유 3개 밖의 4번째 사유다. 대량 UPDATE에 등록을 붙이면 오래된 고아가 쌓인 DB에서 한 번에 N건이 등록되므로 별 판단이 필요하다. ⚠️ 버그로 재조사하지 말 것 |
```


```markdown
| **발음 성과를 난이도 단계 판단에 넣기** | 캡틴 결정 2026-09-04: **지금은 넣지 않고 MVP 이후 재검토한다.** 영구 제외가 아니다 — 이후 발음 교정을 따로 요청하면 그때 구체 요구사항을 정리한다. 근거: `requirements-summary.md`가 발음 점수·등급·유사도 지표를 "하지 않는 것"으로 정했고, 단계 판단에 넣으려면 없는 점수 기준을 발명해야 한다(§3.2 위반). 발음 자체는 실시간 교정과 계획 입력(§4.4)으로 살아 있다 |
| **AC11-5 — 두 세션 연속 틀린 패턴에서 대화가 구별된다** | **이 설계의 어느 시나리오에도 대응이 없었다**(2026-09-04 점검). 실제 음성 응대가 달라지는 것을 요구하므로 스텁으로는 판정할 수 없다 → 실물 Nova 확인과 함께 다룬다. **슬라이스 2 완료 후에도 미충족으로 남는다** |
```

- [ ] **Step 2: `database-schema.md`에 표 2개를 더한다**

`session_plans`·`learner_notes`의 컬럼·CHECK·unique·cascade와 **`session_id`가 계획을 만든 세션이라는 것**을
적는다. `### 아직 SQL에 없는 테이블` 절에서 이 둘을 지운다(있다면). 삽입 위치를 정하고
`git diff -U0`이 순수 삽입인지 확인한다 — 살아 있는 줄 인용이 밀리면 다른 문서가 깨진다.

- [ ] **Step 3: 스모크 단정을 더한다**

슬라이스 2 산출물을 실제로 보는 단정 4건을 스모크에 넣는다: ① 세션 종료 후 계획 job이 걸린다
② 계획 1행이 생긴다 ③ 관찰 노트 1행이 생긴다 ④ 다음 세션 시작 시 스텁 지시문에 `Today's plan:`이 있다.
⚠️ **하네스도 게이트 밖 자산이다**(함정 H-AA — 스모크가 이틀간 죽어 있었다). 손대기 전에
`git log -1 -- tests/harness/`와 최근 앱 변경 날짜를 대조한다.

- [ ] **Step 4: 원장과 handoff를 갱신한다**

`TASKS.md` C절의 "슬라이스 2 — 계획 생성·반영" 행을 완료로 바꾸고, 이연 처리 결과(LOW-12·LOW-14 닫힘,
MEDIUM-7·MEDIUM-8 유지)와 새 미결(AC11-5 미충족)을 적는다. `handoff/HANDOFF.md`의 "다음 한 걸음"을
다음 작업으로 바꾼다. **handoff가 이미 120줄 상한을 넘겼으므로**(2026-09-04 실측 196줄) 이때
발음 절·tmux 절을 영구 지식으로 내려 줄인다.

- [ ] **Step 5: 게이트 전체를 돌리고 커밋**

```bash
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && \
  .venv/bin/ruff format --check . && ty check
cd ../frontend && npx tsc --noEmit && npx eslint app lib
```

```bash
git add docs/ TASKS.md handoff/HANDOFF.md tests/harness/
git commit -m "docs: 슬라이스 2 문서 마감 — 설계서 6곳 정정 + AS11 신설 [skip ci]

- §5.2·§9·AS6 의 전달 경로를 팩토리 조립으로 정정(캡틴 결정 2026-09-04)
- §5.2 에 '실제 지시문은 nova.py 상수'라는 경고를 넣었다
- AC11-6 의 확인 시나리오 AS11 을 신설했다 — 누락이 2026-09-04 점검에서 확인됐다
- §11 이월 2건: 발음-단계 판단(MVP 이후 재검토) · AC11-5(미충족으로 남음)"
```

---

## 실물 검증 (자동 테스트로 판정 불가한 것)

⚠️ **둘 다 캡틴 승인 후에 한다.** 기록은 `tests/harness/runs/2026-09-XX-slice2-live.md`에 남긴다.

**L1 — 007을 실물 dev DB에 적용한다.** `scripts/migrate.py` 실행. 단정: `schema_migrations`가 **6행**이 되고
(`001`·`003`·`004`·`005`·`006`·`007`), `session_plans`·`learner_notes`가 실제로 생기고,
`analysis_jobs`의 CHECK 2개가 3값·3분기로 바뀐다. **되돌리기 어려운 조작이므로 승인 없이 하지 않는다.**

**L2 — 실물 Claude로 계획 생성 1회** (설계서 §10.1 AS-live). 판정은 사람이 한다:
① `reason`이 **한국어 한 문장**이고 학습자에게 말하는 어투인가 ② 질문 3~5개가 초점 패턴을 실제로
유발하는 형태인가 ③ 지시문의 목표 문장 길이대가 `target_level`과 모순되지 않는가
④ 노트가 숫자로 담을 수 없는 관찰인가(단순히 횟수를 되풀이한 것이 아닌가).
**비용이 든다** — 돌릴 때마다 실물 호출 1회다.

**하지 않는 것**: 실물 Nova에 지시문이 반영되어 응대가 달라지는지(AC11-5). **캡틴 결정 2026-09-04로
이월했다** — 스텁 관통(AS6)으로 전달 경로만 검증한다.

---

## 자체 점검 (이 계획을 쓴 뒤 사양과 대조했다)

**① 사양 커버리지.** 설계서 §12.1 결정표 2행의 5개 항목이 전부 태스크를 갖는다:
계획 생성 job(T1·T2·T3·T7) · `session_plans`(T1·T7) · `learner_notes`(T1·T7) ·
지시문 전달 §5.2(T9·T10) · 수준 갱신 §7(T5·T7).
수용 시나리오: AS1(T4·T6) · AS2(T4의 LOW-12 테스트) · AS3(T6) · AS4(T8) · AS5(T5) · AS6(T9·T10) ·
AS7(T5·T7) · AS8(T7) · **AS11 신설**(T12). AS9·AS10은 슬라이스 1이 이미 충족했다.
요구사항: R11-2(T5·T6) · R11-3(T5의 이유 검증 + **T11의 화면**) · R11-4(T2) · R11-5(T8) ·
R11-7(T5·T7) · R11-8(T4·T6) · R11-9(T4·T6·T12의 AS11) · R11-10(T7).
**AC11-5만 태스크가 없고, 그것이 의도된 것임을 T12가 문서에 적는다.**

**② 자리표시자 점검.** "TODO"·"적절히 처리"·"나머지는 비슷하게" 없음. Task 3이 남기는
`NotImplementedError`는 **유일한 의도적 임시물**이고 Task 7 Step 4가 grep으로 제거를 확인한다.

**③ 타입 정합.** `SessionInstruction`은 T5가 정의하고 T8(읽기)·T10(문장 조립)·T11(응답)이 쓴다 —
이름과 필드가 같다. `ClaimedJob`의 새 필드 2개는 T3이 정의하고 T7이 `job.session_id`로 읽는다.
`PlanInput.current_level`은 T4가 채우고 T7이 `parse_plan(current_level=…)`으로 넘긴다.
`build_system_prompt(known_sounds, plan)`의 인자 순서는 T10에서 한 번만 정의된다.

**남은 약점 1개 (정직하게 적는다)**: 연속 세션에서 계획이 아직 안 만들어졌으면 폴백으로 시작한다 —
느려지는 것이 아니라 **패턴 기반 선택이 조용히 꺼진다.** 설계서 §3.4가 이미 이월로 지정한 것이고
이 계획은 그것을 고치지 않는다. 후보 2개(직전 계획의 남은 질문 이어 쓰기 / job 등록을 마지막 발화
분석 완료 시점으로 앞당기기)가 §11 이월에 있다.

---

_계획 작성: 2026-09-04. 기준 커밋 `82203d1`. 실측 기준선 454 passed._
_사양: `docs/design/2026-08-25-learning-coach-agent-design.md` · 어긋남 점검: `docs/consistency-audit-2026-09-04.md`_

