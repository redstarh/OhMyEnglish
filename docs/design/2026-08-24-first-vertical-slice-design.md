# 첫 수직 슬라이스 설계서

- 작성: 2026-08-24
- 트랙: A (풀) — 새 프로젝트, 아키텍처 신설
- 상태: **리뷰 대기** (Codex DB 리뷰 반영 완료 / 캡틴 리뷰 전)
- 선행: `handoff/HANDOFF.md` §다음 구현 작업 순서 1~2, `docs/nova-sonic-claude-architecture.md`

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
| 실시간 음성 | `amazon.nova-2-sonic-v1:0` | 실존 확인 — `streaming=True`, `in=[SPEECH] → out=[SPEECH,TEXT]` |
| 학습 분석 | `us.anthropic.claude-opus-5` | ACTIVE 프로필, invoke HTTP 200 확인 |

- 두 모델 모두 `us-west-2`.
- 1M 컨텍스트가 필요하면 `anthropic_beta: ["context-1m-2025-08-07"]`를 쓴다 (HTTP 200 확인).
- **`[1m]` 접미사를 모델 ID에 붙이지 않는다.** Bedrock inference profile ID가 아니며 raw invoke는 HTTP 400이다. Claude Code 전용 표기다.
- Claude를 음성 턴의 동기 경로에 넣지 않는다 (`PRD.md:112`).

### 최대 리스크 — 착수 전 스파이크 필요

Nova Sonic 양방향 스트림(`InvokeModelWithBidirectionalStream`)이 **현재 로컬 자격증명으로 되는지 미검증**이다. 로컬에는 `AWS_BEARER_TOKEN_BEDROCK`만 있고 SigV4 자격증명이 없다(`aws sts get-caller-identity` 실패). 양방향 스트림이 SigV4를 요구하면 자격증명 확보가 선행 조건이 된다.

**조치**: `aws-sdk-bedrock-runtime` 0.10.0으로 최소 스트림 1회 왕복을 먼저 뚫는다. 실패하면 SigV4 자격증명을 발급한 뒤 재시도한다. 이 스파이크가 통과하기 전에는 프론트엔드에 착수하지 않는다.

---

## 5. 비동기 분석 — PostgreSQL 큐

새 인프라 컴포넌트를 만들지 않고 이미 확정된 PostgreSQL만 쓴다.

- `analysis_jobs` 테이블: `job_type`, `session_id`/`utterance_id`, `status`, `available_at`, `attempts`, `locked_at`, `locked_by`, `last_error`, `payload`, `created_at`
- 인덱스 `(status, available_at)`, 분석 대상별 중복 방지 unique
- 워커는 FastAPI 기동 시 `asyncio` 루프로 뜬다
- **짧은 트랜잭션에서 `FOR UPDATE SKIP LOCKED`로 claim → 트랜잭션을 닫고 Claude 호출 → 별도 트랜잭션에서 완료 처리.** Claude 호출을 트랜잭션 안에 두면 커넥션을 수십 초 잡는다
- 프로세스가 죽어도 작업이 테이블에 남아 재기동 후 이어진다

`BackgroundTasks`만 쓰는 더 단순한 안은 버렸다. 프로세스가 죽으면 그 세션의 학습 데이터가 통째로 사라지는데, 이 앱에서 세션 분석은 유일한 산출물이다.

---

## 6. DB 스키마 결정

`001_initial_schema.sql`은 아직 어떤 DB에도 적용된 적이 없다. **002를 쌓지 않고 001을 직접 재작성한다.** 동시에 `database-schema.md`를 정합화한다.

### 6.1 반영할 결함 (Codex 리뷰 확정)

| # | 결정 |
|---|---|
| F2 | `analysis_jobs` 테이블 신설 (§5) |
| D1 | `error_patterns.category`에 CHECK 추가. 코드값 확정: `verb_tense`, `article`, `preposition`, `word_order`, `verb_form`, `business_expression`, `pronunciation_intonation`. `PRD.md:89`의 한국어 표시명과의 매핑을 문서화 |
| D2 | `create extension if not exists pgcrypto` + 모든 PK에 `default gen_random_uuid()`. 고정 단일 사용자는 결정적 UUID를 설정값으로 시드 |
| E1 | `error_occurrences (pattern_id, created_at desc)`, `(utterance_id)` 인덱스 추가 |
| C1 | 복습 간격을 **1·3·7일 3단계로 확정**하고 `database-schema.md:49`의 14일을 삭제 |
| B1 | 단계는 패턴이 아니라 과제에 둔다 — `review_tasks.review_stage smallint check (between 1 and 3)` |
| F1 | `unique(pattern_id, review_stage)`로 복습 과제 중복 생성 차단 (`tests/README.md:12`) |
| B3 | `error_patterns.self_difficulty smallint check (between 1 and 5)` |
| F3 | `review_tasks.user_id`를 제거하고 소유자를 `pattern_id`로 유도 — 단일 사용자 범위에서 불일치 가능성을 원천 제거 |

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

- **Audio Gateway**: WebSocket 연결 성립 = 인증된 세션 1개 + Nova 스트림 1개. 호출자(브라우저)는 합의된 샘플레이트·인코딩의 프레임만 보낸다. 세션 종료 시 `learning_sessions.ended_at`이 반드시 채워진다.
- **분석 Worker**: 입력은 `utterance_type='learning'`인 확정 전사문만. 출력은 `error_patterns` upsert + `error_occurrences` insert가 **한 트랜잭션**. 부분 반영을 남기지 않는다.
- **`error_patterns` 불변조건**: `unique(user_id, pattern_key)` — 같은 오류는 문장이 달라도 한 패턴으로 병합된다 (`tests/README.md:9`). `mastery_score` 0~100.

### Boundary

- **타입 경계**: Nova 오디오 프레임(바이너리) ↔ 전사문(텍스트) ↔ Claude JSON 출력 ↔ DB 행. Claude 출력은 신뢰할 수 없는 외부 데이터로 취급해 스키마 검증 후 저장한다. `confidence`·`severity`는 CHECK 범위를 넘으면 거부한다.
- **시간 경계**: 모든 시각을 `timestamptz`로 저장하고 naive datetime을 만들지 않는다. 복습 기준일은 `users.timezone`(`Asia/Seoul`)의 날짜 경계로 계산한다 — UTC 자정으로 계산하면 하루가 밀린다.
- **프로세스 경계**: 부분 전사문은 화면 표시용으로만 쓰고 저장하지 않는다. 확정 전사문만 `utterances`에 남긴다 (`voice-architecture.md:45`).
- **학습/명령 경계**: `utterance_type`이 이 경계다. 첫 슬라이스에는 명령이 없지만 컬럼과 규약을 미리 지킨다.

### Failure

- **Nova 스트림 끊김**: 확정 전사문과 현재 목표를 요약해 새 스트림에 넘긴다 (`nova-sonic-claude-architecture.md §6`). 재연결 실패 시 세션을 `ended_at`으로 닫고 그때까지의 전사문을 보존한다.
- **Claude 호출 실패**: `analysis_jobs.attempts` 증가 + `available_at` 백오프. 재시도가 안전해야 하므로 upsert는 **멱등**이어야 한다 — 같은 발화를 두 번 분석해도 `error_occurrences`가 중복되지 않게 대상별 unique를 둔다.
- **워커 프로세스 사망**: `locked_at` 타임아웃을 넘긴 작업은 다시 claim 가능하게 한다. 그렇지 않으면 작업이 영구 잠긴다.
- **부분 실행**: 분석 결과 저장이 한 트랜잭션이므로 절반만 반영되는 상태가 없다.

### Dependency

- **초기화 순서**: DB 마이그레이션 → 고정 사용자·시나리오 시드 → FastAPI 기동 → 워커 루프 → WebSocket 수신. 시드 전에 세션을 만들면 FK가 깨진다.
- **읽기 전 갱신 보장**: 결과 화면은 분석 완료 후의 `error_patterns`를 읽는다. 분석이 비동기이므로 **화면은 `analysis_jobs.status`를 근거로 "분석 중" 상태를 표시**해야 한다. 완료를 가정하고 읽으면 빈 결과를 보여준다.
- **정리 순서**: WebSocket 종료 → Nova 스트림 종료 → 세션 종료 기록 → 분석 작업 등록. 순서가 뒤바뀌면 종료 시각이 없는 세션이 분석 대상이 된다.
- **단독 테스트 가능성**: 분석 Worker는 전사문 입력만 받으므로 Nova 없이 단위 테스트할 수 있다. Audio Gateway는 Nova 스트림을 가짜로 대체해 테스트한다.

---

## 8. 수용 시나리오

**AC1 — 음성 왕복**
Given 세션이 시작되고 마이크 권한이 허용되었을 때, When 사용자가 `What do you usually do after work?`에 영어로 답하면, Then Agent의 음성 응답이 재생되고 확정 전사문이 화면에 표시되며 `utterances`에 `utterance_type='learning'`으로 저장된다.

**AC2 — 끼어들기**
Given Agent가 말하고 있을 때, When 사용자가 말을 시작하면, Then Agent 음성 재생이 즉시 멈추고 사용자 발화를 받는다 (`voice-architecture.md:63`).

**AC3 — 비동기 분석**
Given 세션이 종료되었을 때, When 분석 작업이 처리되면, Then `PRD.md:116`의 사례대로 `Yesterday I work on the API`가 `past_tense_in_work_update` 패턴으로 저장되고 `target_form`이 `Yesterday, I worked on the API.`가 된다. 음성 응답 경로는 이 분석을 기다리지 않는다.

**AC4 — 패턴 병합**
Given 같은 시제 오류가 다른 문장에서 다시 나올 때, When 분석이 완료되면, Then `error_patterns` 행은 늘지 않고 `frequency`가 증가하며 `error_occurrences`가 한 건 추가된다 (`tests/README.md:9`).

**AC5 — 교정 개수 상한**
Given 한 세션에 오류가 여러 개 검출될 때, When 결과 화면을 보면, Then 고영향 오류 최대 2개만 제시된다 (`tests/README.md:10`).

**AC6 — 분석 중 상태**
Given 세션이 막 끝났을 때, When 결과 화면에 진입하면, Then 분석이 끝나지 않았다면 "분석 중"으로 표시하고, 빈 결과를 확정 결과처럼 보여주지 않는다.

**AC7 — 재시도 멱등성**
Given 분석이 실패해 재시도될 때, When 같은 발화가 다시 분석되면, Then `error_occurrences`에 중복 행이 생기지 않는다.

---

## 9. 미결 사항 — 캡틴 확인 필요

1. **복습 간격 1·3·7일 확정**: 문서 3개(`HANDOFF.md:21`, PRD, requirements-summary)가 3단계이고 `database-schema.md:49`만 14일을 더한다. 다수를 따라 3단계로 정했으나 확인이 필요하다. h-doc이 "복습 간격 N일 같은 수치는 철회된 거짓 정밀도 유형"이라 경고한 항목이다.
2. **오류 카테고리 영문 코드값**: §6.1 D1의 7개 코드를 확정할지.
3. **h-doc의 SoT 포인터**: 현재 `~/MyProject/AllMyEnglish/spec/...`을 가리켜 다음 세션을 오도한다. skill 본문을 고칠지.
4. **h-doc이 ❌로 판정한 3건**: 월간 분석·YouTube 수집·요청형 학습 생성. 그 판정 근거가 AllMyEnglish 스펙이었으므로 OhMyEnglish `PRD.md` 기준 재판정 대상이다. 세 건 모두 현재 OhMyEnglish 범위에 들어 있다.
5. **음성 녹음 보관**: 첫 MVP에서 비활성화할지 (`HANDOFF.md:233`).

---

## 10. 다음 단계

1. Nova Sonic 양방향 스트림 스파이크 (§4) — 통과 전 프론트엔드 착수 금지
2. `001_initial_schema.sql` 재작성 + `database-schema.md` 정합화 (§6)
3. 백엔드 스캐폴딩 → 분석 Worker → Audio Gateway
4. 프론트엔드 세션·결과 화면
5. `tests/` 단위·통합 테스트 (TDD — 실패하는 테스트 먼저)
