# 첫 수직 슬라이스 설계서

- 작성: 2026-08-24
- 트랙: A (풀) — 새 프로젝트, 아키텍처 신설
- 상태: **캡틴 리뷰 대기**
- 선행: `handoff/HANDOFF.md` §다음 구현 작업 순서 1~2, `docs/nova-sonic-claude-architecture.md`

### 리뷰 이력

| 회차 | 리뷰어 | 판정 | 반영 |
|---|---|---|---|
| 1차 | Codex (DB 모델) | 결함 확정 8 / 조건부 7 / 반박 1, 신규 F1~F3 | §6 전체 |
| 2차 | Codex (설계서 전체) | **조건부 승인** — BLOCK 2건 | BLOCK 2건 해소(§5.1~5.3), SHOULD FIX 5건 반영(§5.4, §7 Boundary·Failure·Dependency, §8.1, §9) |
| 3차 | Codex (최종본) | **반려** — BLOCK 4건 | 멱등성을 replace 방식으로 재설계(§5.2), lease token 원자화(§5.4), 인증 모순 제거(§7), 결과 화면 조회 규칙 신설(§5.5), `analysis_jobs` 전체 명세(§6.1a), AC10~13 추가, 인용 3건 정정 |
| 4차 | Fable 5 critic (심층) | 대기 | — |
| 5차 | 캡틴 | 대기 | — |

이 문서는 구현 범위와 결정만 정의한다. 코드와 SQL은 이 설계가 승인된 뒤에 쓴다.

---

## 1. 범위

`HANDOFF.md §2`의 한 흐름을 끝까지 관통시킨다.

```text
브라우저 마이크 → FastAPI WebSocket → Nova 2 Sonic 양방향
  → 음성 응답 + 실시간 전사문 → (비동기) Claude Opus 5 분석
  → error_patterns 저장 → 학습 결과 화면
```

첫 시나리오는 일상 질문 3개로 고정한다.

1. `What do you usually do after work?`
2. `What do you usually do on weekends?`
3. `What do you need to do tonight?`

### 범위에 넣지 않는 것

음성 명령(3단계), 업무 역할극·보고(4단계), 쉐도잉, 주간 리포트, 복습 과제 생성, 인증, AWS 배포, 모바일 앱. 각각 이후 단계에서 다룬다.

---

## 2. 확정된 실행 환경

| 항목 | 결정 | 근거 |
|---|---|---|
| 배포 | localhost 단독 개인 도구 | 캡틴 결정 2026-08-24 |
| 인증 | 없음. 고정 `user_id` 1개를 시드 | 단일 사용자 |
| DB | PostgreSQL 컨테이너 (**podman**) | 로컬에 docker 없음, podman 5.8.0 |
| 비동기 처리 | PostgreSQL 큐 (`analysis_jobs`) | SQS/Redis는 과하다 — 캡틴 결정 |
| 클라이언트 | Next.js 웹만 | 모바일 앱 추후 |
| Slack 알림 | MVP 제외 | 필요해지면 나중에 |
| `infra/` | 미생성 | 배포는 동작 확인 후 |
| 자격증명 | **백엔드는 SigV4 전용, bearer token 금지** | Nova 양방향이 API Key를 거부 (§4.1) |

### Hermes 검토 결과 — MVP 미사용

Hermes Agent(v0.20.1)는 cron 스케줄러·Slack 게이트웨이·FTS5 기억을 갖췄지만 비동기 분석 워커로는 부적합하다.

- LLM agent loop이라 결정론적 변환(전사문 → `error_patterns` upsert)의 출력 스키마와 실행을 보장하기 어렵다.
- 코어 의존성이 `openai==2.24.0`이고 provider 교체 구조다. Bedrock 경유는 추가 작업이다.
- `requires-python >=3.11,<3.14`인데 로컬은 Python 3.14.3이다.
- FastAPI ↔ Hermes CLI 프로세스 간 결합이 늘어난다. "SQS/Redis는 과하다"는 단순화 취지에 역행한다.

**단 재사용처를 남긴다**: 주간 리포트를 cron으로 돌려 Slack DM으로 보내는 일. Hermes가 이미 둘 다 갖고 있어 그 시점에 재검토한다.

---

## 3. 저장소 구조

`app/`을 애플리케이션 코드의 정본으로 쓰고, 테스트는 최상위 `tests/`를 유지한다.

```text
app/frontend/                 # Next.js — 세션 화면, 전사문, 결과 화면
app/backend/app/
  ├── api/                    # HTTP + WebSocket endpoint
  ├── audio_gateway/          # Nova 2 Sonic 양방향 스트림
  ├── workers/                # Claude 분석 Worker
  ├── models/                 # DB model
  └── services/              # 학습·복습 domain service
tests/{unit,integration,e2e}/  # 최상위 유지
scripts/                      # 개발 보조
```

Python 툴체인은 `uv`(0.11.8) + `ruff` + `ty`(0.0.31)를 쓴다. `aws-sdk-bedrock-runtime`이 `requires-python >=3.12`이고 Hermes 사례처럼 3.14에서 Rust 휠 문제가 날 수 있어, **백엔드 인터프리터를 3.12 또는 3.13으로 핀한다**.

---

## 4. 모델 경로

| 역할 | 모델 | 검증 상태 |
|---|---|---|
| 실시간 음성 | `amazon.nova-2-sonic-v1:0` | 실존 확인 — `streaming=True`, `in=[SPEECH] → out=[SPEECH,TEXT]`. **양방향 호출은 SigV4 필수** (§4.1) |
| 학습 분석 | `us.anthropic.claude-opus-5` | ACTIVE 프로필, invoke HTTP 200 확인 |

- 두 모델 모두 `us-west-2`.
- 1M 컨텍스트가 필요하면 `anthropic_beta: ["context-1m-2025-08-07"]`를 쓴다 (HTTP 200 확인).
- **`[1m]` 접미사를 모델 ID에 붙이지 않는다.** Bedrock inference profile ID가 아니며 raw invoke는 HTTP 400이다. Claude Code 전용 표기다.
- Claude를 음성 턴의 동기 경로에 넣지 않는다 (`PRD.md:112`).

### 4.1 자격증명 — 검증 완료, 착수 차단 요인 확정

**결론: Nova Sonic 양방향 스트림은 Bedrock API key(bearer token)로 호출할 수 없다. SigV4 자격증명이 필수다.** 2026-08-25 스파이크로 확정했다.

서비스가 직접 거부한다 — SDK 한계가 아니다.

| 엔드포인트 | bearer token 결과 |
|---|---|
| `/invoke` | HTTP 200 |
| `/invoke-with-response-stream` | HTTP 200 (이벤트 스트림 청크 수신) |
| `/invoke-with-bidirectional-stream` | **HTTP 403 `This operation does not support API Keys`** |

대조군으로 인증 헤더를 아예 뺐을 때는 `Authorization header is missing`이 돌아왔다. 메시지가 다르므로 403은 인증 평가 단계에 도달한 뒤 **API Key를 특정해 거부한 것**이다.

SDK 쪽 증거도 일치한다. `aws-sdk-bedrock-runtime` 0.10.0의 `HTTPAuthSchemeResolver.resolve_auth_scheme`는 SigV4 옵션만 반환하고, `smithy_aws_core.auth`에는 `sigv4` 하위 모듈만 있다. 실제 실행 시 `IdentityChainError: No credential providers were configured to resolve an identity.`가 발생했다 — `AWS_BEARER_TOKEN_BEDROCK`이 설정돼 있어도 자격증명 체인이 인식하지 않는다.

**따라서 SigV4 자격증명 확보가 첫 슬라이스의 하드 블로커다.** 발급 전에는 음성 경로를 구현할 수 없다.

**자격증명 전략**: 백엔드는 **SigV4 단일 경로로 통일한다.** SigV4는 Nova Sonic 양방향과 Claude `/invoke` 양쪽에 모두 쓸 수 있어 경로를 두 개 유지할 이유가 없다. 현재의 `AWS_BEARER_TOKEN_BEDROCK`은 Claude Code 세션용으로만 남긴다. 로컬 단독 도구이므로 IAM user access key를 `.env`(gitignore 대상)에 두는 것으로 시작하고, 배포 시 IAM role로 교체한다.

### 4.2 SDK 오류 전파 특성 — 설계에 반영

스파이크에서 발견한 것: `invoke_model_with_bidirectional_stream`의 자격증명 실패가 **호출자에게 즉시 예외로 오지 않았다.** 내부 `RequestPipeline._execute_request` 태스크에서 발생하고 `Task exception was never retrieved`로 남았으며, 호출자 쪽에서는 30초 타임아웃으로 나타났다.

Audio Gateway는 이를 전제로 만든다 — **연결 실패를 예외 포착만으로 감지하지 말고 자체 연결 타임아웃을 둔다.** 그렇지 않으면 자격증명·권한 오류가 "응답 없음"으로 보여 원인을 찾기 어렵다.

---

## 5. 비동기 분석 — PostgreSQL 큐

새 인프라 컴포넌트를 만들지 않고 이미 확정된 PostgreSQL만 쓴다.

### 5.1 분석 단위 — job_type 2종

`nova-sonic-claude-architecture.md:98-99`가 분석 시점을 두 개로 정의하고 `PRD.md:112`도 "다음 턴·다음 세션에 반영"이라 명시한다. 따라서 작업 단위는 하나가 아니다.

| `job_type` | 등록 시점 | 대상 컬럼 | 산출 |
|---|---|---|---|
| `analyze_utterance` | 확정 전사문 저장 직후 (턴 단위) | `utterance_id` | 오류 카테고리·패턴 키·`error_patterns` upsert·`error_occurrences` insert |
| `summarize_session` | 세션 종료 기록 직후 (세션 단위) | `session_id` | 핵심 약점 1~2개, `learning_sessions.summary` |

`analyze_utterance`가 턴마다 도는 것이 채택 아키텍처(`nova-sonic-claude-architecture.md:87-88`)다. 세션 종료를 기다리지 않는다. 두 컬럼은 nullable이며 `job_type`에 따라 정확히 하나만 채워진다는 CHECK를 둔다.

### 5.2 멱등성 — 재시도가 안전해야 한다

크래시가 "결과 저장 완료 후 `status` 갱신 전"에 발생하면 같은 작업이 다시 실행된다. 따라서 재실행이 중복을 만들지 않아야 한다.

- **occurrence는 발화 단위 replace다.** `analyze_utterance` 결과 저장은 한 트랜잭션에서 `delete from error_occurrences where utterance_id = :id` 후 새 결과 집합을 insert한다. 재시도하면 같은 집합으로 교체될 뿐 중복이 생기지 않고, 재분석 결과가 이전과 달라져도 최신 결과만 남는다.
  - 초안은 `unique (utterance_id, pattern_id)`로 막으려 했으나 **철회했다** — 한 발화에 같은 패턴이 두 곳 나오는 정상 데이터(예: 한 문장에 관사 누락 2곳)를 잃는다. replace 방식은 복수 occurrence를 보존하면서 멱등하다.
- `error_occurrences`에 `span_start`/`span_end`(발화 내 문자 오프셋)를 저장해 같은 패턴의 복수 발생을 구분하고 결과 화면에서 위치를 표시한다.
- `analysis_jobs`에 **partial unique** — `(job_type, utterance_id)` / `(job_type, session_id)`가 `status in ('pending','running')`인 동안 중복 등록 차단
- `error_patterns`는 `unique(user_id, pattern_key)` upsert이므로 이미 멱등
- `frequency`는 `error_occurrences`의 실제 행 수에서 재계산한다. 무조건 `+1`로 올리면 재시도마다 부풀어 오른다

### 5.3 작업 등록의 원자성

**세션 종료 기록과 `summarize_session` 등록은 한 트랜잭션이다.** 확정 전사문 저장과 `analyze_utterance` 등록도 한 트랜잭션이다. 분리하면 그 사이 크래시에서 분석 없는 발화·세션이 영구히 남는다.

### 5.4 claim과 lease

- 워커는 FastAPI 기동 시 `asyncio` 루프로 뜬다
- 인덱스 `(status, available_at)`
- **짧은 트랜잭션에서 `FOR UPDATE SKIP LOCKED`로 claim → 트랜잭션을 닫고 Claude 호출 → 별도 트랜잭션에서 완료 처리.** Claude 호출을 트랜잭션 안에 두면 커넥션을 수십 초 잡는다
- **lease 기간 5분.** claim 조건은 `status='pending' and available_at <= now()` 또는 `status='running' and locked_at < now() - interval '5 minutes'`(회수). 이 규칙이 없으면 오래 걸리는 정상 호출을 다른 워커가 중복 claim한다
- **claim마다 새 lease token을 발급해 `locked_by`에 기록한다** (워커 ID가 아니라 claim 1회당 고유값). 같은 워커가 재claim해도 token이 달라져 이전 시도의 늦은 쓰기를 구분할 수 있다
- **결과 저장·`done`·재큐·`failed` 등 모든 상태 전이와 결과 DB 쓰기를 같은 트랜잭션에서 `where status='running' and locked_by=:token` 조건으로 원자화한다.** 완료 처리만 검증하면 부족하다 — lease를 잃은 워커 A가 결과 쓰기나 재큐를 먼저 수행해 워커 B의 새 claim 이후 상태를 오염시킬 수 있다. 조건이 0행이면 그 시도의 결과를 통째로 버린다
- **`attempts`는 claim 시점에 증가한다** — 즉 상한 5는 "최대 5번 호출"이다. lease 만료 회수도 재claim이므로 attempt를 소비한다
- **`attempts >= 5`면 terminal `failed`로 보내고 재시도를 멈춘다.** `last_error`를 남긴다. 상한이 없으면 영구 재시도한다
- 상태 전이: `pending → running → done` / `running → pending`(백오프 재시도) / `running → failed`(상한 초과)
- 프로세스가 죽어도 작업이 테이블에 남아 재기동 후 이어진다

`BackgroundTasks`만 쓰는 더 단순한 안은 버렸다. 프로세스가 죽으면 그 세션의 학습 데이터가 통째로 사라지는데, 이 앱에서 세션 분석은 유일한 산출물이다.

단일 로컬 워커에 `SKIP LOCKED`가 과한지 검토했으나 유지한다. 개발 중 워커를 두 번 띄우는 일이 흔하고, 그때 중복 claim으로 생기는 데이터 오염이 이 제약을 넣는 비용보다 크다.

### 5.5 결과 화면 조회 규칙

결과 화면은 전역 `error_patterns`가 아니라 **그 세션의 occurrence**를 읽는다.

- 조회: `error_occurrences` ⨝ `utterances`(`utterance_id`)를 `utterances.session_id = :session`으로 좁히고 패턴을 조인
- **상위 2개 선정** (`PRD.md:29` "세션당 핵심 오류 1~2개 교정"): `severity desc → confidence desc → 발생 수 desc` 순으로 정렬해 **패턴 단위** 상위 2개. 같은 패턴의 복수 occurrence는 한 항목으로 묶고 위치(`span_start`)를 함께 표시
- `summarize_session`의 `learning_sessions.summary`는 이 2개와 별개의 세션 총평이다. summary가 아직 없으면 총평 영역만 "분석 중"으로 두고 교정 2개는 준비되는 대로 표시
- **부분/실패 표시**: 세션의 `analysis_jobs` 중 `failed`가 있으면 "일부 발화는 분석하지 못했다"를 명시하고 재시도 불가임을 알린다. `failed`를 숨기고 성공분만 보여주면 사용자는 완전한 결과로 오해한다

---

## 6. DB 스키마 결정

`001_initial_schema.sql`은 아직 어떤 DB에도 적용된 적이 없다. **002를 쌓지 않고 001을 직접 재작성한다.** 동시에 `database-schema.md`를 정합화한다.

### 6.1 반영할 결함 (Codex 리뷰 확정)

| # | 결정 |
|---|---|
| F2 | `analysis_jobs` 테이블 신설 (§5). `job_type` 2종 + 대상 컬럼 CHECK + `(status, available_at)` 인덱스 + partial unique |
| F2-i | `error_occurrences`는 **발화 단위 replace**로 멱등 처리 (§5.2). `unique(utterance_id, pattern_id)` 초안은 복수 occurrence를 잃어 철회. `span_start`/`span_end` 컬럼 추가 |
| F2-ii | `learning_sessions.status` 추가 — `active`/`completed`/`failed` CHECK. Nova 연결 실패로 닫힌 세션(§7 Failure)을 정상 종료와 구분 |
| D1 | `error_patterns.category`에 CHECK 추가. 코드값 확정: `verb_tense`, `article`, `preposition`, `word_order`, `verb_form`, `business_expression`, `pronunciation_intonation`. `PRD.md:89`의 한국어 표시명과의 매핑을 문서화 |
| D2 | `create extension if not exists pgcrypto` + 모든 PK에 `default gen_random_uuid()`. 고정 단일 사용자는 결정적 UUID를 설정값으로 시드 |
| E1 | `error_occurrences (pattern_id, created_at desc)`, `(utterance_id)` 인덱스 추가 |
| C1 | 복습 간격을 **1·3·7일 3단계로 확정**하고 `database-schema.md:49`의 14일을 삭제 |
| B1 | 단계는 패턴이 아니라 과제에 둔다 — `review_tasks.review_stage smallint check (between 1 and 3)` |
| F1 | `unique(pattern_id, review_stage)`로 복습 과제 중복 생성 차단 (`tests/README.md:12`) |
| B3 | `error_patterns.self_difficulty smallint check (between 1 and 5)` |
| F3 | `review_tasks.user_id`를 제거하고 소유자를 `pattern_id`로 유도 — 단일 사용자 범위에서 불일치 가능성을 원천 제거 |

### 6.1a `analysis_jobs` 최종 명세

구현자 선택 여지를 없애기 위해 컬럼을 확정한다.

| 컬럼 | 타입 | NULL | 제약 |
|---|---|---|---|
| `id` | uuid | X | PK, `default gen_random_uuid()` |
| `job_type` | text | X | CHECK `in ('analyze_utterance','summarize_session')` |
| `utterance_id` | uuid | O | FK → `utterances`. `analyze_utterance`일 때만 NOT NULL |
| `session_id` | uuid | O | FK → `learning_sessions`. `summarize_session`일 때만 NOT NULL |
| `status` | text | X | CHECK `in ('pending','running','done','failed')`, default `'pending'` |
| `available_at` | timestamptz | X | default `now()` |
| `attempts` | smallint | X | default 0 |
| `locked_at` | timestamptz | O | claim 시각 |
| `locked_by` | text | O | claim별 고유 lease token (§5.4) |
| `last_error` | text | O | 마지막 실패 메시지 |
| `created_at` | timestamptz | X | default `now()` |

- 테이블 CHECK: `(job_type='analyze_utterance' and utterance_id is not null and session_id is null) or (job_type='summarize_session' and session_id is not null and utterance_id is null)`
- partial unique: `(job_type, utterance_id) where status in ('pending','running')`, `(job_type, session_id) where status in ('pending','running')`
- 인덱스: `(status, available_at)`
- `payload` 컬럼은 두지 않는다 — 입력은 FK로 참조하는 원본 행에서 읽는다 (YAGNI)

### 6.2 조건부 — 규약으로 처리

| # | 결정 |
|---|---|
| B2 | `error_patterns.impact_score`를 저장하고 `error_occurrences.severity` 집계 규칙을 문서에 명문화. 추천 근거를 재현 가능하게 만드는 것이 목적 |
| D4 | 일반 CHECK로 다른 테이블 값을 검사할 수 없다. **분석 입력 쿼리는 `utterance_type = 'learning'`만 선택하는 것을 규약으로 하고 통합 테스트로 강제한다** (`tests/README.md:14`). DB 보장이 필요해지면 트리거를 추가 |
| D3 | `users.current_level`·`learning_scenarios.level`에 CEFR 공유 CHECK를 적용 |

### 6.3 반박 수용

**D5(녹음 삭제 이력) — 결함 아님.** `tests/README.md:11`은 URL 노출 여부만 검사하고 `database-schema.md:59`도 "즉시 접근 불가"만 요구한다. 객체 스토리지를 삭제하고 `audio_url = NULL`로 갱신하면 충족된다. 감사 이력이 필요해질 때 `audio_deleted_at`을 추가한다.

### 6.4 이번 재작성에 넣지 않는 것

- `shadowing_items` (A1) — 쉐도잉 착수 시 002
- `weekly_reports` (A2) — `PRD.md:31` MVP 범위이지만 첫 슬라이스 밖. 주간 리포트 착수 시 002
- `users.daily_goal_minutes` (E2) — 단일 사용자이므로 앱 상수로 두고 문서에 명시

`database-schema.md`에 각 테이블이 **어느 단계에서 생기는지** 명시해 문서-SQL 불일치가 재발하지 않게 한다.

### 6.5 유지 확인

`error_patterns` / `error_occurrences` 분리는 적절한 정규화다. 재사용 단위(`pattern_key`, `target_form`)는 패턴에, 원문 조각과 실제 교정(`original_span`, `correction`)은 발생에 둔다. `frequency`·`last_seen_at`은 발생에서 파생되는 캐시이므로 **분석 완료 트랜잭션에서 원자적으로 갱신하는 것을 규약으로 한다.**

---

## 7. 4 Lenses 검증

### Contract

- **Audio Gateway**: WebSocket 연결 성립 = **고정 사용자에 바인딩된 localhost 세션** 1개 + Nova 스트림 1개 (§2 인증 없음과 일치 — 인증은 이후 단계). 호출자(브라우저)는 합의된 샘플레이트·인코딩의 프레임만 보낸다. 세션 종료 시 `learning_sessions.ended_at`이 반드시 채워진다.
- **분석 Worker**: 입력은 `utterance_type='learning'`인 확정 전사문만. 출력은 `error_patterns` upsert + `error_occurrences` insert가 **한 트랜잭션**. 부분 반영을 남기지 않는다.
- **`error_patterns` 불변조건**: `unique(user_id, pattern_key)` — 같은 오류는 문장이 달라도 한 패턴으로 병합된다 (`tests/README.md:9`). `mastery_score` 0~100.

### Boundary

- **타입 경계**: Nova 오디오 프레임(바이너리) ↔ 전사문(텍스트) ↔ Claude JSON 출력 ↔ DB 행. Claude 출력은 신뢰할 수 없는 외부 데이터로 취급해 스키마 검증 후 저장한다. `confidence`·`severity`는 CHECK 범위를 넘으면 거부한다.
- **시간 경계**: 모든 시각을 `timestamptz`로 저장하고 naive datetime을 만들지 않는다. `due_at` 계산은 **경과 시간이 아니라 현지 날짜 기준**이다: `last_seen_at`을 `users.timezone`(`Asia/Seoul`)의 현지 날짜로 변환 → N일(1·3·7) 더함 → 그 날짜의 고정 현지 시각(`09:00`)을 `timestamptz`로 환산. 경과 시간(`+24h`)으로 계산하면 밤 11시 학습이 다음날 밤 11시로 밀려 "1일 뒤"가 아니게 된다. UTC 자정 기준으로 계산하면 하루가 밀린다. **DST는 이 설계에서 해당 없다** — `Asia/Seoul`은 DST를 쓰지 않고 단일 사용자 고정 timezone이다. 다중 timezone을 지원하게 되면 이 계산을 재검토한다.
- **프로세스 경계**: 부분 전사문은 화면 표시용으로만 쓰고 저장하지 않는다. 확정 전사문만 `utterances`에 남긴다 (`voice-architecture.md:42-43`).
- **Nova 이벤트 경계**: 확정 전사문 이벤트는 **수신 즉시 `(session_id, sequence_no)`로 commit한다.** 세션 롤오버(`nova-sonic-claude-architecture.md:121-126`)나 barge-in 중 연결이 끊기면 이미 확정된 이벤트가 유실될 수 있으므로 버퍼에 모아두지 않는다. `utterances`의 `unique (session_id, sequence_no)`가 재수신 시 중복 제거 지점이다 — 롤오버 후 Nova가 같은 턴을 다시 보내도 행이 늘지 않는다. `sequence_no`는 Nova가 아니라 서버가 세션 내에서 단조 증가로 부여한다.
- **학습/명령 경계**: `utterance_type`이 이 경계다. 첫 슬라이스에는 명령이 없지만 컬럼과 규약을 미리 지킨다.

### Failure

- **Nova 스트림 연결 실패**: 자격증명·권한 오류가 즉시 예외로 오지 않고 무응답으로 나타난다 (§4.2). Audio Gateway는 자체 연결 타임아웃을 두고, 초과 시 세션을 실패로 닫고 사용자에게 알린다. 예외 포착만 믿으면 원인 불명의 무한 대기가 된다.
- **Nova 스트림 끊김**: 확정 전사문과 현재 목표를 요약해 새 스트림에 넘긴다 (`nova-sonic-claude-architecture.md §6`). 재연결 실패 시 세션을 `ended_at`으로 닫고 그때까지의 전사문을 보존한다.
- **Claude 호출 실패**: `analysis_jobs.attempts` 증가 + `available_at` 백오프. `attempts >= 5`면 terminal `failed` (§5.4).
- **결과 저장 후 status 갱신 전 크래시**: 가장 까다로운 실패다. 같은 작업이 재실행되므로 `error_occurrences`의 `unique (utterance_id, pattern_id)`와 `frequency` 재계산 규약이 중복을 막는다 (§5.2). 이 두 장치가 없으면 재시도가 데이터를 오염시킨다.
- **워커 프로세스 사망**: lease 5분을 넘긴 `running` 작업은 다시 claim 가능하다. 회수당한 워커는 `locked_by` 검증에서 완료 처리를 거부당한다 (§5.4). 그렇지 않으면 작업이 영구 잠기거나 남의 작업을 덮어쓴다.
- **작업 등록 누락**: 확정 전사문 저장 ↔ `analyze_utterance` 등록, 세션 종료 기록 ↔ `summarize_session` 등록이 각각 한 트랜잭션이다 (§5.3). 분리하면 그 사이 크래시에서 분석되지 않는 발화·세션이 영구히 남는다.
- **부분 실행**: 분석 결과 저장(`error_patterns` upsert + `error_occurrences` insert + job 완료)이 한 트랜잭션이므로 절반만 반영되는 상태가 없다.

### Dependency

- **초기화 순서**: DB 마이그레이션 → 고정 사용자·시나리오 시드 → FastAPI 기동 → 워커 루프 → WebSocket 수신. 시드 전에 세션을 만들면 FK가 깨진다.
- **읽기 전 갱신 보장**: 결과 화면은 분석 완료 후의 `error_patterns`를 읽는다. 분석이 비동기이므로 **화면은 그 세션에 속한 `analysis_jobs`가 모두 terminal(`done`/`failed`)인지를 근거로 "분석 중" 상태를 표시**해야 한다. 세션의 발화 수만큼 `analyze_utterance` 작업이 있으므로 하나만 보고 판단하면 안 된다. 완료를 가정하고 읽으면 빈 결과를 확정 결과처럼 보여준다.
- **작업 등록 순서**: `analyze_utterance`는 턴마다 확정 전사문 저장과 함께 등록된다 — 세션 종료를 기다리지 않는다 (`nova-sonic-claude-architecture.md:87-88`). `summarize_session`은 세션 종료 기록과 함께 등록된다. 두 번째는 첫 번째들의 결과에 의존하므로, 워커가 `summarize_session`을 집을 때 같은 세션의 `analyze_utterance`가 아직 남아 있으면 `available_at`을 미뤄 재큐한다.
- **정리 순서**: WebSocket 종료 → Nova 스트림 종료 → (세션 종료 기록 + `summarize_session` 등록, 한 트랜잭션). 순서가 뒤바뀌면 종료 시각이 없는 세션이 요약 대상이 된다.
- **단독 테스트 가능성**: 분석 Worker는 전사문 입력만 받으므로 Nova 없이 단위 테스트할 수 있다. Audio Gateway는 Nova 스트림을 가짜로 대체해 테스트한다.

---

## 8. 수용 시나리오

**AC1 — 음성 왕복**
Given 세션이 시작되고 마이크 권한이 허용되었을 때, When 사용자가 `What do you usually do after work?`에 영어로 답하면, Then Agent의 음성 응답이 재생되고 확정 전사문이 화면에 표시되며 `utterances`에 `utterance_type='learning'`으로 저장된다.

**AC2 — 끼어들기**
Given Agent가 말하고 있을 때, When 사용자가 말을 시작하면, Then 사용자 발화 시작 감지 후 **1초 이내**에 Agent 오디오 송출이 중단되고 사용자 발화를 받는다 (`voice-architecture.md:63`). 1초는 수용 상한이며 체감 목표는 즉시다.

**AC3 — 턴 단위 비동기 분석**
Given 사용자가 `What do you usually do after work?`에 `I usually go to gym after work.`라고 답할 때, When 확정 전사문이 저장되면, Then 같은 트랜잭션에서 `analyze_utterance` 작업이 등록되고(§5.3) **세션 종료를 기다리지 않고** 처리되어 `article` 카테고리의 `missing_article_before_place` 패턴이 저장되며 `target_form`이 `I usually go to the gym after work.`가 된다. 음성 응답 경로는 이 분석을 기다리지 않는다.

> `PRD.md:116`의 과거시제 사례(`Yesterday I work on the API`)는 업무 문맥이라 이번 일상 질문 3개의 전형적 답변이 아니다. 4단계(업무 영어) 검증용 독립 fixture로 둔다.

**AC4 — 패턴 병합**
Given 같은 관사 누락이 `I usually go to office by subway.`처럼 다른 문장에서 다시 나올 때, When 분석이 완료되면, Then `error_patterns` 행은 늘지 않고 `error_occurrences`가 한 건 추가되며 `frequency`가 그 실제 행 수로 재계산된다 (`tests/README.md:9`, §5.2).

**AC5 — 교정 개수 상한**
Given 한 세션에 오류가 여러 개 검출될 때, When 결과 화면을 보면, Then 고영향 오류 최대 2개만 제시된다 (`tests/README.md:10`).

**AC6 — 분석 중 상태**
Given 세션이 막 끝나 그 세션의 `analysis_jobs` 중 일부가 아직 `pending`/`running`일 때, When 결과 화면에 진입하면, Then "분석 중"으로 표시한다. **세션에 속한 모든 작업이 terminal(`done`/`failed`)이 된 뒤에만 확정 결과로 표시한다.** 빈 결과를 확정 결과처럼 보여주지 않는다.

**AC7 — 재시도 멱등성**
Given 결과 저장은 끝났지만 `status` 갱신 전에 워커가 죽어 같은 작업이 재실행될 때, When 재분석이 완료되면, Then `error_occurrences`에 중복 행이 생기지 않고(`unique (utterance_id, pattern_id)`) `frequency`가 부풀지 않는다 (§5.2).

**AC8 — lease 회수와 소유자 검증**
Given 워커 A가 작업을 claim한 뒤 lease 5분을 넘겨 워커 B가 회수했을 때, When 워커 A가 늦게 돌아와 완료 처리를 시도하면, Then `locked_by` 검증에서 거부되어 B의 결과를 덮어쓰지 못한다 (§5.4).

**AC9 — 재시도 상한**
Given Claude 호출이 계속 실패할 때, When `attempts`가 5에 도달하면, Then 작업이 terminal `failed`로 전이하고 `last_error`가 남으며 더 이상 재시도하지 않는다 (§5.4).

**AC10 — Nova 연결 실패 가시화**
Given 자격증명·권한 문제로 Nova 스트림이 열리지 않을 때, When 연결 타임아웃(§4.2)이 초과되면, Then 세션이 `status='failed'`로 닫히고 화면에 연결 실패가 표시된다. 무한 대기 상태가 되지 않는다.

**AC11 — 세션 요약**
Given 세션이 정상 종료되고 모든 `analyze_utterance`가 terminal일 때, When `summarize_session`이 완료되면, Then `learning_sessions.summary`에 핵심 약점 1~2개가 저장되고 결과 화면 총평 영역에 표시된다.

**AC12 — 시나리오 3문항 완주**
Given 세션이 시작되면, When 사용자가 고정 질문 3개(§1)에 차례로 답하면, Then 각 질문마다 AC1의 왕복이 성립하고 세 발화 모두 `utterances`에 저장되며 각각 `analyze_utterance` 작업이 등록된다.

**AC13 — 부분 실패 표시**
Given 세션의 `analyze_utterance` 중 하나가 `failed`일 때, When 결과 화면을 보면, Then 성공한 발화의 교정과 함께 "일부 발화는 분석하지 못했다"가 표시된다 (§5.5). 실패를 숨기지 않는다.

### 8.1 `tests/README.md` 필수 케이스 대응

| # | 필수 케이스 | 첫 슬라이스 | 대응 |
|---|---|---|---|
| 1 | 같은 오류가 다른 문장에 나타나도 하나의 패턴으로 병합 | ✅ 범위 | **AC4** |
| 2 | 세션 피드백이 최대 두 개의 핵심 오류만 선택 | ✅ 범위 | **AC5** |
| 3 | 녹음 삭제 시 음성 URL 미노출 | ❌ 제외 | 녹음이 기본 미저장 opt-in이고(`HANDOFF.md:50`) 첫 슬라이스에 녹음 보관을 켜지 않는다. 녹음 기능 착수 시 AC 추가 |
| 4 | 1·3·7일 복습 일정이 중복 없이 생성 | ❌ 제외 | 복습 과제 생성은 3단계다(§1 범위 밖). 스키마 제약(`unique(pattern_id, review_stage)`)은 §6.1에서 미리 넣되 AC는 그 단계에서 추가 |
| 5 | 일일 목표 완료 후에도 `additional` 세션 제한 없이 시작 | ❌ 제외 | 추가 학습은 3단계 |
| 6 | 음성 명령은 오류 분석에 미포함 | ❌ 제외 | 음성 명령은 3단계. 단 §6.2 D4의 쿼리 규약과 `utterance_type` 컬럼은 지금부터 지킨다 |
| 7 | 종료 명령은 확인 단계를 거침 | ❌ 제외 | 음성 명령은 3단계 |

첫 슬라이스가 덮는 필수 케이스는 1·2뿐이다. 나머지 5건은 해당 기능이 범위에 들어오는 단계에서 AC를 추가한다.

---

## 9. 미결 사항 — 캡틴 확인 필요

1. **h-doc의 SoT 포인터 수정**: h-doc이 `구현 범위의 SoT는 ~/MyProject/AllMyEnglish/spec/...다`라고 명시해 다음 세션을 폐기된 프로젝트로 유도한다. **사용자 개인 skill 파일이므로 설계자가 임의로 고치지 않는다.**
2. ~~h-doc이 ❌로 판정한 3건의 재판정~~ → **문서 정리 작업으로 재분류.** 월간 분석(`HANDOFF.md:98`)·YouTube 추천(`docs/requirements-summary.md:99`)·요청형 학습(`HANDOFF.md:138`) 모두 OhMyEnglish 문서가 이미 범위 근거를 제공한다. h-doc의 ❌ 판정은 폐기된 AllMyEnglish 스펙 기준이므로, 캡틴 sign-off 대기가 아니라 h-doc 스펙 대조표를 손볼 때 함께 정정하면 된다(위 1번과 같은 작업). 첫 슬라이스와 무관하다.

### 9.1 문서 근거로 확정한 사항 — 참고용

Codex 리뷰 지적에 따라, 근거가 문서에 이미 있는 것은 미결로 남기지 않고 확정했다.

| 사항 | 결정 | 근거 |
|---|---|---|
| 복습 간격 | **1·3·7일 3단계.** `database-schema.md:49`의 14일을 삭제 | `HANDOFF.md:21`, `requirements-summary.md:52`, `tests/README.md:12` 3곳이 3단계이고 14일은 1곳뿐. ~~PRD~~ — PRD에는 간격 수치가 없다 (인용 정정) |
| 오류 카테고리 코드 | §6.1 D1의 영문 7개 코드 | `PRD.md:89`의 7분류와 1:1, `database-schema.md:35`가 이미 영문 `verb_tense`를 씀 |
| 음성 녹음 보관 | **첫 슬라이스에서 켜지 않음** (기본 미저장) | `HANDOFF.md:50` "음성 녹음은 기본 저장하지 않고 opt-in으로 설계한다" |
| 일일 목표 수치 | 앱 상수 10~15분, 컬럼 미추가 | `PRD.md:63` 권장량이고 단일 사용자 |

복습 간격은 h-doc이 "복습 간격 N일 같은 수치는 철회된 거짓 정밀도 유형"이라 경고한 항목이라 캡틴에게 알린다. 다만 이 수치는 이 프로젝트 문서 4곳이 이미 확정한 값이므로 새로 발명한 숫자가 아니다.

---

## 10. 다음 단계

1. **SigV4 자격증명 확보 (하드 블로커, §4.1)** — bearer token으로는 양방향 스트림이 403이다. 발급 후 `aws-sdk-bedrock-runtime` 0.10.0으로 최소 스트림 1회 왕복을 확인한다. 통과 전 음성 경로·프론트엔드 착수 금지
2. `001_initial_schema.sql` 재작성 + `database-schema.md` 정합화 (§6). 문서에는 각 테이블의 도입 단계를 표기
3. 백엔드 스캐폴딩 + 분석 Worker (Nova 없이 단독 테스트 가능한 부분 먼저 — TDD)
4. Audio Gateway 최소 왕복 (텍스트/고정 오디오로 Nova 왕복 확인, barge-in·롤오버는 이후)
5. 프론트엔드 세션·결과 화면
6. barge-in(AC2)·세션 롤오버 등 스트림 견고성
7. `tests/` 통합·E2E (필수 케이스 1·2 = AC4·AC5)

구현 규모가 커 보이지만 순서가 위와 같으므로 각 단계가 독립적으로 검증된다. 한 번에 전부 만들지 않는다.
