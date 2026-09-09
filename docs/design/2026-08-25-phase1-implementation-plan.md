# OhMyEnglish 첫 수직 슬라이스 Phase 1 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스텁 음성 어댑터 기반으로 "세션 시작 → 전사문 저장 → 실제 Claude 비동기 분석 → error_patterns 저장 → 결과 화면"을 관통시킨다.

**Architecture:** FastAPI 백엔드가 WebSocket 세션과 PostgreSQL 큐(`analysis_jobs`, `FOR UPDATE SKIP LOCKED`)를 운영하고, asyncio 워커(동시성 1)가 Claude(`us.anthropic.claude-opus-5`)를 호출해 발화 단위 replace로 패턴을 저장한다. Nova는 포트(Protocol)로 격리하고 스텁이 공통 픽스처를 발행한다. Next.js 프론트가 세션·결과 화면을 제공한다.

**Tech Stack:** Python 3.13(uv 핀) · FastAPI + uvicorn · asyncpg(raw SQL, ORM 없음 — YAGNI) · pydantic v2(+pydantic-settings) · boto3(Claude invoke — bearer/SigV4를 자격증명 체인이 흡수해 F5 충족) · pytest + pytest-asyncio · ruff + ty · Next.js(App Router, TS) · podman(postgres:16-alpine)

**Spec:** `docs/design/2026-08-24-first-vertical-slice-design.md` (설계 정본) + `docs/design/2026-08-25-first-slice-acceptance-criteria.md` (완료 기준 — 이하 "AC 문서")

## Global Constraints

- 모델: `us.anthropic.claude-opus-5` / region `us-west-2`. **`[1m]` 접미사 금지** (Bedrock 프로필 아님 — 400)
- ~~Phase 1 자격증명: bearer(`AWS_BEARER_TOKEN_BEDROCK`) 임시 사용 (AC F5, 의도적 이탈 2)~~ → **해소 (2026-08-26).** SigV4 단일 경로로 전환 완료. `prepare_bedrock_credentials()`가 SigV4를 우선 쓰고(없으면 bearer 폴백 — 전환기 캡틴 지시) SigV4가 있으면 bearer를 프로세스 환경에서 제거한다. **AC F5의 "전환 = 설정 교체"가 실증됐다** — 격리 지점 `config.py` 한 곳만 고쳐 워커·클라이언트 코드는 무변경. 실측: Claude invoke HTTP 200, Nova 양방향 스파이크 PASS(설계서 §10-1 관문 통과)
- Nova 실연동 금지 — 포트+스텁만 (캡틴 결정 2026-08-25)
- 워커 동시성 1 / lease 5분 / attempts 상한 5 / 백오프 `attempts × 1분` / Gateway 연결 타임아웃 10초 (전부 설계 발명값 — 코드 상수로 두고 주석에 발명값 표기)
- `mastery_score`·`self_difficulty`·`review_tasks`는 스키마만 존재, 어떤 코드도 읽거나 쓰지 않는다 (⚠️ 2026-09-03 정정: `impact_score`는 **컬럼 자체가 없어** 이 목록에 있으면 안 된다. 같은 문서 뒤쪽 006 주석이 "만들지 않는다"로 옳게 적었다)
- 시간: 전부 `timestamptz`/aware datetime. naive datetime 금지 (SVG V3)
- 시간 의존 테스트는 실시간 대기 금지 — `locked_at`/`available_at`을 과거로 직접 세팅
- 테스트: `pytest` 전체 실패 0 + **skip/xfail 0**. 각 태스크는 red→green 증거(실패 출력 → 통과 출력)를 남긴다 (SVG T0)
- lint/type: `.venv/bin/ruff check` + `ruff format --check` + `ty check` 오류 0
- 커밋: conventional commits, 태스크당 1커밋

## 파일 구조 (전체 조감)

```text
app/backend/
├── pyproject.toml                  # uv, py3.13 핀, deps
├── app/
│   ├── __init__.py
│   ├── config.py                   # Settings(pydantic-settings) — 자격증명 격리(F5)
│   ├── db.py                       # asyncpg pool + 트랜잭션 헬퍼
│   ├── models/
│   │   ├── __init__.py
│   │   └── analysis.py             # Claude 출력 스키마(W7) — pydantic
│   ├── services/
│   │   ├── __init__.py
│   │   ├── jobs.py                 # 큐: 등록/claim/완료/재큐/failed (W3~W5)
│   │   ├── utterances.py           # 전사문 저장+job 등록 트랜잭션 (W1,W6, seq 가드)
│   │   ├── analysis.py             # 프롬프트(§5.6)+replace 저장+frequency 재계산 (W2,W3)
│   │   └── results.py              # 결과 조회 (R1~R3)
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── claude_client.py        # Claude 포트+boto3 구현 (W7 경계)
│   │   └── analysis_worker.py      # asyncio 루프 (동시성 1)
│   ├── audio_gateway/
│   │   ├── __init__.py
│   │   ├── port.py                 # VoiceAdapter Protocol (G3)
│   │   ├── stub.py                 # 공통 픽스처 스텁 (+무응답 모드)
│   │   └── session.py              # 세션 수명주기 (G1,G2)
│   └── api/
│       ├── __init__.py
│       ├── main.py                 # FastAPI app + lifespan(pool, worker)
│       ├── ws.py                   # /ws/session WebSocket
│       └── results.py              # GET /api/sessions/{id}/results
app/frontend/                       # Next.js (T10)
db/migrations/001_initial_schema.sql  # 재작성 (T2)
scripts/
├── dev_db.sh                       # podman postgres 기동/중지
├── migrate.py                      # 001 적용 + 시드
└── smoke_analysis.py               # W-live (T11)
tests/
├── conftest.py                     # DB 픽스처(테스트 DB 재생성), fake Claude
├── unit/  (test_jobs.py, test_analysis.py, test_claude_schema.py, test_results.py)
└── integration/ (test_pipeline.py, test_gateway.py, test_ws.py)
```

핵심 인터페이스 (모든 태스크가 공유하는 계약):

```python
# audio_gateway/port.py — G3 포트. 데이터 경로만 고정 (수명·barge-in은 Phase 2 확장)
class TranscriptEvent(pydantic.BaseModel):
    kind: Literal["partial", "final"]
    text: str
    sequence_no: int | None = None   # final에만 부여(서버측), partial은 None

class VoiceAdapter(Protocol):
    async def start(self) -> None: ...                     # 연결 수립(스텁: 즉시/무응답 모드)
    async def send_audio(self, frame: bytes) -> None: ...
    def events(self) -> AsyncIterator[TranscriptEvent | bytes]: ...  # bytes = 오디오 응답 프레임
    async def close(self) -> None: ...

# workers/claude_client.py — Claude 포트. 테스트는 fake, 실물은 boto3
class ClaudeClient(Protocol):
    async def analyze(self, prompt: str) -> str: ...        # 원문 텍스트(JSON 문자열) 반환

# models/analysis.py — W7 검증 스키마 (Claude 출력)
class ErrorFinding(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")
    category: Literal["verb_tense","article","preposition","word_order",
                      "verb_form","business_expression","pronunciation_intonation"]
    pattern_key: str                     # 신규는 ^{category}_[a-z0-9_]+$ 검증
    target_form: str
    original_span: str
    correction: str
    severity: Literal["low","medium","high"]
    confidence: float = pydantic.Field(ge=0, le=1)

class AnalysisResult(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="forbid")
    findings: list[ErrorFinding]

# services/jobs.py — 큐 시그니처
async def enqueue_analyze(conn, utterance_id: UUID) -> UUID | None   # partial unique 충돌 시 None
async def claim_next(conn, *, now: datetime | None = None) -> ClaimedJob | None
async def complete(conn, job_id: UUID, lease_token: str) -> bool     # 0행 갱신이면 False
async def fail_or_retry(conn, job_id: UUID, lease_token: str, error: str) -> bool

# services/results.py — R2 상태
SessionResultStatus = Literal["analyzing", "final", "partial_failure",
                              "connection_failed", "no_utterances"]
```

공통 픽스처 (AC 문서 §공통 픽스처 — 스텁·W-live·E2E-S 공유, `tests/conftest.py`와 `audio_gateway/stub.py`가 동일 상수 참조):

```python
FIXTURE_TURNS = [
    ("What do you usually do after work?",  "I usually go to gym after work."),
    ("What do you usually do on weekends?", "I usually go to office by subway."),
    ("What do you need to do tonight?",     "I need to finish my homework tonight."),
]
```

---

### Task 1: 백엔드 스캐폴딩 + 툴체인 + 설정 격리 (AC F2 전반, F5 전반)

**Files:**
- Create: `app/backend/pyproject.toml`, `app/backend/app/{__init__,config,db}.py`, `app/backend/app/api/{__init__,main}.py`, `.env.example`, `scripts/dev_db.sh`, `tests/conftest.py`, `tests/unit/test_config.py`

**Interfaces:**
- Produces: `Settings`(env: `DATABASE_URL`, `AWS_REGION`, `AWS_BEARER_TOKEN_BEDROCK?`, `CLAUDE_MODEL_ID="us.anthropic.claude-opus-5"`), `db.pool()`/`db.tx()` 헬퍼, `create_app()`

- [ ] `cd app/backend && uv venv --python 3.13 && uv init` 상당의 pyproject 작성 — deps: `fastapi, uvicorn[standard], asyncpg, pydantic, pydantic-settings, boto3, aws-sdk-bedrock-runtime`(설치·import만 — F2), dev: `pytest, pytest-asyncio, ruff, httpx` (ty는 전역 CLI)
- [ ] `requires-python = ">=3.12,<3.14"` 핀 (설계서 §3 — 3.14 Rust 휠 회피)
- [ ] 실패 테스트: `test_config.py` — ① `Settings()`가 `.env`를 읽는다 ② `python -c "import aws_sdk_bedrock_runtime"` 성공 ③ **자격증명이 `config` 모듈 밖에서 import되지 않는다**(F5: `grep -r "AWS_BEARER" app/ | grep -v config.py` 0건을 테스트로)
- [ ] `config.py` 구현: pydantic-settings, `bedrock_client()` 팩토리 한 곳에서 boto3 client 생성(bearer는 env로 boto3가 흡수 — SigV4 전환 시 이 함수만 영향)
- [ ] `scripts/dev_db.sh`: `podman run -d --name ohmy-pg -p 5433:5432 -e POSTGRES_PASSWORD=... postgres:16-alpine` + stop/reset
- [ ] `conftest.py`: 세션 스코프 asyncpg 픽스처 — 테스트 시작 시 `ohmyenglish_test` DB drop/create 후 001 적용
- [ ] red→green 확인 후 검증: `.venv/bin/ruff check && .venv/bin/ruff format --check && ty check` 0 오류
- [ ] Commit: `feat: backend scaffolding with credential-isolated config`

### Task 2: 001 재작성 + 문서 정합화 + 시드 (AC F1, F4)

**Files:**
- Modify: `db/migrations/001_initial_schema.sql` (전면 재작성), `docs/database-schema.md` (정합화 + 도입 단계 표기)
- Create: `scripts/migrate.py`, `tests/unit/test_schema.py`

**Interfaces:**
- Produces: 설계서 §6 확정 스키마 전체. 고정 UUID: `USER_ID = 00000000-0000-0000-0000-000000000001`

001 재작성 요건 (설계서 §6.1·§6.1a 전건 — 누락 금지):

```sql
-- 요건 체크리스트 (SQL 전문은 구현 시 작성하되 아래를 전부 포함)
create extension if not exists pgcrypto;
-- 모든 PK: uuid primary key default gen_random_uuid()  (D2)
-- users.current_level / learning_scenarios.level: CHECK CEFR ('A1','A2','B1','B2','C1','C2') (D3)
-- learning_sessions: + status text not null default 'active'
--   check (status in ('active','completed','failed'))  (F2-ii)
-- utterances: unique (session_id, sequence_no) 유지 — Gateway 이중 commit 가드 (§7)
-- error_patterns: category CHECK 7코드 (D1), self_difficulty smallint check (1..5) null 허용 (B3)
--   impact_score 컬럼은 만들지 않는다 (4차 리뷰에서 3단계 연기)
-- error_occurrences: unique 없음(replace 방식) + 인덱스 (pattern_id, created_at desc), (utterance_id) (E1)
-- review_tasks: user_id 제거(F3), review_stage smallint check (1..3), unique(pattern_id, review_stage) (B1,F1)
-- analysis_jobs: §6.1a 명세 그대로 — job_type CHECK 2종, 대상 컬럼 상호배타 CHECK,
--   status CHECK 4종, partial unique 2개(where status in ('pending','running')), (status, available_at) 인덱스
-- shadowing_items / weekly_reports: 만들지 않는다 (002로 연기)
```

- [ ] 실패 테스트: `test_schema.py` — ① 001이 빈 DB에 오류 없이 적용 ② `analysis_jobs`에 pending 중복 insert가 unique 위반 ③ `error_patterns.category`에 `'noun'` insert가 CHECK 위반 ④ `learning_sessions.status='wrong'` 거부 ⑤ 시드 후 users 1행·scenarios 3행(질문 3개)
- [ ] 001 작성 → `scripts/migrate.py`(asyncpg로 SQL 파일 실행 + 시드: 고정 사용자, `daily_life` 시나리오 3행에 질문 텍스트)
- [ ] `database-schema.md` 정합화: 재작성된 001과 테이블·컬럼·제약 1:1 + 각 테이블에 "도입: Phase1 / 002(쉐도잉) / 002(주간리포트) / 3단계(복습)" 표기 + `:49`의 14일 → 1·3·7일 수정
- [ ] red→green + lint/ty → Commit: `feat: rewrite initial schema per approved design (001)`

### Task 3: analysis_jobs 큐 서비스 (AC W3 후반·W4·W5)

**Files:**
- Create: `app/backend/app/services/jobs.py`, `tests/unit/test_jobs.py`

**Interfaces:**
- Produces: 위 조감의 `enqueue_analyze / claim_next / complete / fail_or_retry`, `ClaimedJob(id, utterance_id, lease_token, attempts)`
- 상수: `LEASE = timedelta(minutes=5)`, `MAX_ATTEMPTS = 5`, `BACKOFF = attempts × timedelta(minutes=1)` — 주석에 "설계 발명값"

핵심 SQL 계약 (설계서 §5.4 — 구현은 이대로):

```sql
-- claim: 새 lease_token(uuid4 hex)을 이번 claim에 발급, attempts는 claim 시 +1
update analysis_jobs set status='running', locked_at=now(), locked_by=$token, attempts=attempts+1
where id = (
  select id from analysis_jobs
  where (status='pending' and available_at <= now())
     or (status='running' and locked_at < now() - interval '5 minutes')
  order by available_at limit 1 for update skip locked)
returning id, utterance_id, attempts;
-- complete/fail_or_retry/결과 저장: 전부 where status='running' and locked_by=$token (0행이면 False)
-- fail_or_retry: attempts >= 5 → status='failed', last_error=$e
--                 아니면 status='pending', available_at = now() + attempts * interval '1 minute'
```

- [ ] 실패 테스트 목록 (각각 red 확인): ① enqueue 후 같은 발화 재enqueue → None(partial unique) ② claim이 token 발급+attempts 증가 ③ `locked_at`을 과거로 세팅한 running job이 회수되고 **이전 token의 complete가 False** (W4) ④ attempts=5 실패 → `failed`+`last_error`, 재claim 안 됨 (W5) ⑤ 백오프: attempts=2 재큐 후 `available_at ≈ now()+2분` ⑥ done 후 같은 발화 재enqueue는 **허용** (partial unique는 pending/running만)
- [ ] 구현 → green → lint/ty → Commit: `feat: postgres-backed analysis job queue with lease tokens`

### Task 4: 전사문 저장 + job 등록 트랜잭션 (AC W1 전반·W3 추가거동·W6)

**Files:**
- Create: `app/backend/app/services/utterances.py`, `tests/unit/test_utterances.py`

**Interfaces:**
- Produces: `save_final_transcript(conn, session_id, text, speaker="user") -> UtteranceRow` — 세션 내 `sequence_no` 단조 증가 부여, `utterance_type='learning'`이면 같은 트랜잭션에서 `enqueue_analyze`. `save_final_transcript`는 agent 발화(`speaker='agent'`)도 저장하되 job은 사용자 learning 발화만
- Produces: ~~`pending_learning_utterances(conn)`~~ — 분석 입력 선택 쿼리 (W6의 검증 대상은 enqueue 조건). ⚠️ **2026-09-03 G-7로 삭제했다** — 앱 호출처가 0곳이었다(캡틴 결정 B-8 "죽은 코드는 삭제"). W6 증거는 이 줄이 이미 말한 대로 enqueue 조건 쪽에 있으므로 잃은 것이 없다.

- [ ] 실패 테스트: ① 사용자 learning 발화 저장 → utterances 1행 + analysis_jobs 1행, **같은 트랜잭션**(중간 실패 주입 시 둘 다 롤백) ② `voice_command` 발화 저장 → job 0건 (W6) ③ agent 발화 → job 0건 ④ 같은 `(session_id, sequence_no)` 강제 재insert → unique 위반 (W3 가드) ⑤ sequence_no가 1,2,3 단조 증가
- [ ] 구현 → green → lint/ty → Commit: `feat: transcript persistence with atomic job enqueue`

### Task 5: Claude 클라이언트 포트 + 출력 경계 검증 (AC W7)

**Files:**
- Create: `app/backend/app/models/analysis.py`, `app/backend/app/workers/claude_client.py`, `tests/unit/test_claude_schema.py`

**Interfaces:**
- Produces: `ErrorFinding`/`AnalysisResult`(위 조감 그대로), `parse_analysis(raw: str) -> AnalysisResult`(JSON 파싱+검증 — 실패 시 `AnalysisValidationError`), `BedrockClaudeClient(settings)`(boto3 `invoke_model`, thread executor로 async 래핑), `FakeClaudeClient(responses)`(테스트용)

- [ ] 실패 테스트: ① 정상 JSON → AnalysisResult ② 필수 필드 누락 → 거부 ③ `severity:"critical"` → 거부 ④ `confidence:1.5` → 거부 ⑤ `category:"noun"` → 거부 ⑥ 미지 필드 → 거부(extra=forbid) ⑦ JSON 아님(마크다운 감싼 텍스트) → 코드펜스 제거 후 재시도, 그래도 실패면 거부
- [ ] 구현 → green → lint/ty → Commit: `feat: claude client port with strict output schema validation`

### Task 6: 분석 파이프라인 — 프롬프트 + replace 저장 (AC W1 후반·W2·W3)

**Files:**
- Create: `app/backend/app/services/analysis.py`, `tests/unit/test_analysis.py`, `tests/integration/test_pipeline.py`

**Interfaces:**
- Consumes: `ClaudeClient`, `parse_analysis`, jobs의 `complete/fail_or_retry`
- Produces: `build_prompt(transcript, existing_patterns: list[PatternRow]) -> str` (§5.6: 기존 key 목록+category+target_form 주입, 재사용 우선 지시, 신규 형식 규칙, 학습자 수준은 h-doc 기준 단문 교정 톤, 세션당 상한 없이 검출은 전부 — 상위 2개 선정은 R1의 몫), `process_analysis(pool, claude, job) -> None`

process_analysis 계약 (설계서 §5.2·§5.3):
1. 짧은 트랜잭션 밖에서 Claude 호출 → `parse_analysis`
2. 한 트랜잭션에서: `delete from error_occurrences where utterance_id=...` → findings insert → 패턴 upsert(`unique(user_id, pattern_key)`) → `frequency = (select count(*) ...)` 재계산, `last_seen_at = utterances.created_at` → `complete(job, token)` — **complete가 False면 전체 롤백**(lease 상실)
3. 검증 실패/호출 실패 → `fail_or_retry`

- [ ] 실패 테스트: ① fake Claude(픽스처 발화 1·2에 같은 pattern_key 반환)로 두 발화 처리 → patterns 1행·occurrences 2행·frequency=2 (W2) ② 같은 job을 결과 저장 후 status 갱신 전 죽인 척 재실행 → occurrences 그대로 2행, frequency 2, **last_seen_at 불변**(발화 시각 기준) (W3) ③ 프롬프트에 기존 pattern_key가 포함됨 ④ 검증 실패 응답 → job이 fail_or_retry 경로 (W7 연동) ⑤ 한 발화에 같은 패턴 2 findings → occurrences 2행 보존(replace가 복수 발생 유지)
- [ ] 구현 → green → lint/ty → Commit: `feat: analysis pipeline with replace idempotency and pattern-key contract`

### Task 7: 워커 루프 (AC W1 전체 연결)

**Files:**
- Create: `app/backend/app/workers/analysis_worker.py`, `tests/integration/test_worker.py` (테스트는 `tests/integration/test_pipeline.py`에 합쳐도 무방 — 파일 분리는 구현자 판단)

**Interfaces:**
- Produces: `run_worker(pool, claude, *, stop: asyncio.Event, poll_interval=1.0)` — 동시성 1 단일 루프: claim → process_analysis → 반복. `create_app()` lifespan에서 기동/정지. 기동 플래그(`WORKER_ENABLED`, 기본 true) — E2E-S 스텝 3용

- [ ] 실패 테스트: ① 세션 `active` 상태에서 enqueue된 job이 워커 1사이클 후 `done` (W1 관측형) ② stop 이벤트로 루프가 1초 내 종료 ③ `WORKER_ENABLED=false`면 루프가 뜨지 않는다
- [ ] 구현 → green → lint/ty → Commit: `feat: single-concurrency analysis worker loop`

### Task 8: 결과 API (AC R1·R2·R3)

**Files:**
- Create: `app/backend/app/services/results.py`, `app/backend/app/api/results.py`, `tests/unit/test_results.py`

**Interfaces:**
- Produces: `GET /api/sessions/{id}/results` → `{"status": SessionResultStatus, "corrections": [{pattern_key, category, original_span, correction, target_form, reason?, occurrences:int}] (최대 2, status=="final"|"partial_failure"일 때만), "partial_failure": bool}`
- 정렬: `case severity when 'high' then 3 when 'medium' then 2 else 1 end desc, confidence desc, count desc` — **텍스트 desc 금지** (§5.5 함정)

- [ ] 실패 테스트: ① 3패턴 검출 세션 → 정확히 2개, high가 medium보다 먼저 (R1 ordinal) ② non-terminal job 존재 → `analyzing` + corrections **키 자체 없음** (R2) ③ job 0건 세션 → `no_utterances` ④ `status='failed'` 세션 → `connection_failed` ⑤ failed job 1 + done 2 → `partial_failure` + 성공분 교정 포함 (R3)
- [ ] 구현 → green → lint/ty → Commit: `feat: session results API with ordinal severity ranking`

### Task 9: Nova 포트 + 스텁 + Gateway + WebSocket (AC G1~G4)

**Files:**
- Create: `app/backend/app/audio_gateway/{port,stub,session}.py`, `app/backend/app/api/ws.py`, `tests/integration/test_gateway.py`, `tests/integration/test_ws.py`

**Interfaces:**
- Consumes: `save_final_transcript`, `VoiceAdapter`/`TranscriptEvent`(위 조감)
- Produces: `SessionRunner(adapter, pool, session_id)` — 어댑터 이벤트를 소비해 partial은 브로드캐스트만, final은 저장+브로드캐스트, 오디오 프레임은 클라이언트로 릴레이. `CONNECT_TIMEOUT = 10`초(발명값). 종료 시 **adapter.close() → 세션 종료 기록** 순서(G1). start()가 10초 내 안 되면 `status='failed'` + 실패 이벤트(G2)
- Produces: `StubVoiceAdapter(mode="fixture"|"unresponsive")` — FIXTURE_TURNS 재생: 질문(agent final) → 사용자 partial 1~2개 → 사용자 final → 고정 오디오 프레임(짧은 무음 WAV bytes). 수신 프레임 카운트 노출
- WS 프로토콜(JSON): `{"type":"partial"|"final"|"audio"|"session_started"|"session_failed"|"session_ended", ...}` — 오디오는 base64

- [ ] 실패 테스트: ① 픽스처 완주 → utterances에 사용자 final 3행 + jobs 3건 (G4) ② unresponsive 모드 → (타임아웃을 0.1초로 주입해) `status='failed'` + 실패 이벤트, 무한 대기 없음 (G2) ③ 정상 종료 → close가 종료 기록보다 먼저(호출 순서 기록 스파이로 단정) + `ended_at`·`completed` (G1) ④ **import 그래프**: `audio_gateway/session.py`·`api/ws.py` 소스에 `stub` import 부재 (G3 — AST/텍스트 검사 테스트) ⑤ WS 연결 → `learning_sessions` 행 생성(고정 user)
- [ ] 구현 → green → lint/ty → Commit: `feat: audio gateway with voice-adapter port and fixture stub`

### Task 10: 프론트엔드 (AC U1·U2)

**Files:**
- Create: `app/frontend/` Next.js 프로젝트 (`npx create-next-app@latest --ts --app --no-tailwind` 상당, 최소 구성) — `app/page.tsx`(세션 화면), `app/results/[sessionId]/page.tsx`(결과 화면), `lib/ws.ts`

**Interfaces:**
- Consumes: WS 프로토콜(T9), 결과 API(T8)

- [ ] 세션 화면: 시작 버튼 → `getUserMedia`(마이크 권한) → WS 연결 → 오디오 프레임 전송(MediaRecorder chunk) → partial=회색/final=검정 전사문 렌더 → 스텁 오디오 재생(`Audio` API) → 종료 버튼 → 결과 화면 이동. 연결 실패 이벤트 시 실패 UI
- [ ] 결과 화면: 결과 API 폴링(2초) — `analyzing`("분석 중"), `final`(교정 카드 최대 2: 원문→교정문→한 줄 이유), `partial_failure`(성공분 + "분석하지 못한 발화가 있습니다 — 재시도되지 않습니다" · 문구는 `TASK-57`이 고쳤다), `connection_failed`/`no_utterances` 각 문구
- [ ] 검증: `npm run build` 성공 + `npm run lint` 통과 (프론트 자동 테스트 없음 — AC U-검증, E2E-S가 판정)
- [ ] Commit: `feat: session and results screens (Next.js)`

### Task 11: W-live 스모크 (AC W-live)

**Files:**
- Create: `scripts/smoke_analysis.py`

- [ ] 스크립트: 실제 `BedrockClaudeClient`로 픽스처 발화 1·2를 순서대로 처리(세션·발화를 임시 생성) → 단정 출력: patterns 1행/occurrences 2행/frequency=2/category=article/`the` 삽입/두 번째 프롬프트에 첫 key 포함/신규 key 형식 `^article_[a-z0-9_]+$`
- [ ] **실행하고 출력 저장** (완료 보고 증거) → Commit: `feat: live claude smoke script (W-live)`

### Task 12: E2E-S + 마무리 게이트

- [ ] `scripts/dev_db.sh` + 백엔드 + 프론트 기동 → AC 문서 E2E-S 6스텝 수행 (브라우저 자동화로 가능한 데까지 — superpowers-chrome. 마이크 권한은 CDP `Browser.grantPermissions`로 시도, 불가 시 해당 스텝만 캡틴 수동 확인으로 이월 기록)
- [ ] `/simplify` 실행 → 수정 있으면 7단계(전체 테스트) 재실행
- [ ] code-reviewer(opus) 리뷰 → Approve까지 반복
- [ ] 완료 보고: AC 문서 완료 선언 6항목 대조 + 증거 첨부

## Self-Review 결과

- 커버리지: F1(T2) F2(T1·게이트) F3(전 태스크) F4(T2) F5(T1) / W1(T4·T6·T7) W2(T6) W3(T3·T4·T6) W4(T3) W5(T3) W6(T4) W7(T5·T6) W-live(T11) / R1~R3(T8) / G1~G4(T9) / U1·U2(T10) / E2E-S(T12) — 전 AC에 태스크 존재
- 타입 일관성: `VoiceAdapter`/`ClaudeClient`/`SessionResultStatus`/큐 시그니처는 조감 블록이 단일 정의처이고 각 태스크가 이를 인용 — 상충 없음
- 플레이스홀더: 코드 전문 대신 "계약+테스트 목록" 형식을 쓴 곳(T2 SQL, T6 프롬프트)은 요건 체크리스트를 전부 명기했으므로 구현 재량이 아니라 검증 가능한 명세다
