# OhMyEnglish Handoff

## 현재 상태 (2026-08-26)

**Phase 1 개발·검증 완료 + Phase 2 하드 블로커(SigV4) 해소.** 남은 것은 캡틴 게이트 1건뿐이다.

| 항목 | 상태 |
|---|---|
| Phase 1 (첫 수직 슬라이스) | ✅ 개발·검증 완료 — 태스크 12/12 |
| 테스트 | ✅ **206 passed** (skip/xfail 0) |
| 품질 게이트 | ✅ `ruff check` · `ruff format --check` · `ty check` 전부 clean |
| Phase 2 진입 (Nova SigV4) | ✅ **해소** — 스파이크 PASS, 설계서 §10-1 관문 통과 |
| Phase 1 완료 선언 | ⏸ **캡틴 게이트 1건** — 아래 참조 |
| 3단계 학습 코치 Agent | 📄 설계서 초안 작성 — 검토 전 |

브랜치: `design/first-vertical-slice` (git remote 없음 — 로컬 전용).

### ⏸ 완료 선언 전 캡틴 게이트 1건

**E2E-S 스텝 1의 "마이크 실프레임 전송"** — headless Chrome의 MediaRecorder 제약으로 자동 검증 불가(브라우저 레벨 오디오 셰임으로 대체 검증됨). **캡틴이 실물 마이크로 세션 1회**를 돌리거나 **이월 수용을 명시**하면 완료 선언 가능.

절차: `http://localhost:3000` → 학습 시작 → 마이크 허용 → 아무 말 → 종료 → 결과 확인.

> ⚠️ **선행 조건 (2026-08-26 수정)**: 프론트엔드가 잘못된 백엔드를 보고 있었다. §포트 함정 참조. `app/frontend/.env.local`을 만들어 뒀으니 **프론트 dev 서버를 재시작해야** 반영된다(Next.js는 `NEXT_PUBLIC_*`을 기동 시 읽는다).

---

## ⚠️ 포트 함정 — 저장소 문서의 8000은 틀렸다

**이 머신의 :8000은 다른 프로젝트(StockAgent)가 쓴다.** 2026-08-26 실측:

| 포트 | 서비스 | 근거 |
|---|---|---|
| **:8002** | **OhMyEnglish API** | `openapi.json` paths = `/api/sessions/{session_id}/results`, `/health` |
| :8000 | StockAgent (MOCK) | `openapi.json` title = `"StockAgent (MOCK)"`, paths = `/api/v1/account/*` |
| :3000 | OhMyEnglish 프론트 (Next.js) | — |
| :5433 | PostgreSQL (podman `ohmy-pg`) | — |

**발견한 결함**: `app/frontend/lib/config.ts:5`의 폴백이 `http://localhost:8000`인데 `app/frontend/.env.local`이 없어, **프론트가 StockAgent에 붙어 결과 조회가 조용히 실패하는 상태**였다. `.env.local`(gitignore 대상)을 `:8002`로 만들어 해소했고, 추적되는 `.env.example`에도 경고와 함께 기본값을 8002로 고쳤다.

**다음 세션 주의**: 백엔드는 **`--port 8002`**로 띄운다. 8000으로 띄우면 StockAgent와 충돌한다.

---

## 로컬 실행 방법

```bash
# DB (podman — docker 없음)
scripts/dev_db.sh start          # postgres:16-alpine, :5433, ohmy/ohmy/ohmyenglish
python3 scripts/migrate.py       # 001 적용 + 고정 사용자·시나리오 3행 시드 (멱등)
#   주의: 추적은 파일명 기준 — 001을 재작성했다면 재적용되지 않으니
#         dev DB를 drop/재생성해야 한다 (scripts/db_utils.recreate_database)

# 백엔드 (Python 3.13 venv — uv).  ⚠️ 포트 8002
cd app/backend && .venv/bin/uvicorn app.api.main:app --port 8002
#   WORKER_ENABLED=false          → 분석 워커 정지 (E2E-S 스텝 3용, 자격증명 없이 부팅)
#   voice_adapter=stub(기본) | stub_unresponsive(연결 실패 재현)

# 프론트 (Next.js 16)
cd app/frontend && npm run dev   # :3000. .env.local 이 :8002 를 가리켜야 한다

# 검증 게이트 (전부 통과 상태여야 정상)
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . \
  && .venv/bin/ruff format --check . && ty check
#   tests/ 와 scripts/ 는 위 `ruff check .` 범위 밖이다 — 따로 검사:
#   .venv/bin/ruff check ../../tests ../../scripts

# Nova 양방향 관문 (Phase 2 착수 조건)
cd app/backend && .venv/bin/python ../../scripts/spike_nova_bidirectional.py
#   불투명한 AccessDeniedException('') 이 나오면 본문 포착을 켠다:
#   OMY_SPIKE_CAPTURE_BODY=1 .venv/bin/python ../../scripts/spike_nova_bidirectional.py
```

### `.env` (app/backend, gitignore 대상)

자격증명 우선순위 — `config.py`의 `prepare_bedrock_credentials()`:

1. `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (+임시면 `AWS_SESSION_TOKEN`) → **SigV4 사용**. 이때 `AWS_BEARER_TOKEN_BEDROCK`을 프로세스 환경에서 **제거**해 단일 경로를 강제한다(§4.1). Nova 양방향은 이 경로만 가능.
2. 없으면 `AWS_BEARER_TOKEN_BEDROCK` 폴백 — Claude invoke는 되지만 Nova는 403.
3. 둘 다 없으면 워커 기동 시 즉시 `RuntimeError`. `WORKER_ENABLED=false`로는 부팅됨.

현재 `.env`에는 SigV4 키가 들어 있어 **①번 경로로 동작한다**.

> ⚠️ **보안 후속**: 이 access key는 대화 기록을 경유했다 — **로테이션 권장** (`docs/ops/iam-setup-nova-sigv4.md` §6).

---

## 이번 세션(2026-08-25~26)에 한 일

커밋 5건, 모두 `design/first-vertical-slice`:

| 커밋 | 내용 |
|---|---|
| `954e581` | `feat:` SigV4 전환 (config·테스트·스모크) |
| `390c7cc` | `feat:` Nova 양방향 스파이크 + IAM 가이드 정책 정정 |
| `0e07aad` | `docs:` 학습 코치 Agent 설계서 · PG 큐 근거(§5.0) · 이월 항목 |
| `1bb0a9a` | `docs:` HTML 보고서 3부 + 갱신 전 백업 |
| `57b2400` | `docs:` HANDOFF — 하드 블로커 해소 |

### SigV4 전환 — 해소 경로 (전부 실측)

| 단계 | 결과 |
|---|---|
| IAM user `ohmyenglish-local` + 최소권한 인라인 정책 | 발급 (account `783504293555`) |
| `sts get-caller-identity` | `arn:aws:iam::783504293555:user/ohmyenglish-local` |
| Claude invoke via SigV4 (앱 `config` 경유) | HTTP 200, `claude-opus-5` |
| **Nova 양방향 스트림** | **PASS** — 요청 수락·스트림 유지·4xx 없음 |

**정책 결함 1건 발견·수정**: 가이드가 `NovaSonicBidirectional`에 `bedrock:InvokeModelWithBidirectionalStream`만 줬는데 HTTP 403이 났다. **양방향 연산도 `bedrock:InvokeModel`을 함께 요구한다** — 서비스가 403 본문에 정확히 그렇게 답했다. IAM 정책(`kjihoon-bedrock` admin 프로필로 직접 수정)과 가이드를 모두 고쳤다.

**AC F5의 "전환 = 설정 교체"가 실증됐다** — 격리 지점 `config.py` 한 곳만 고쳐 워커·Claude 클라이언트 코드는 무변경.

### 실측으로 밝힌 SDK 함정 3개 (`docs/ops/iam-setup-nova-sigv4.md` §5.1에 기록)

1. **SDK가 4xx 응답 본문을 버린다.** 403 + 271바이트 JSON에 정확한 이유가 있는데 `AccessDeniedException('')`만 남는다. 빈 메시지로는 "정책 누락"과 "모델 접근 미승인"을 구분할 수 없다 → `DiagnosticTransport`로 해결.
2. **본문 포착이 진단을 가린다.** 본문은 한 번만 읽을 수 있고 `response.body`가 읽기 전용이라 되돌릴 수 없어, 켜면 SDK 예외 타입이 `SmithyError: premature EOF`로 바뀐다 → 기본 꺼짐 + 플래그.
3. **Nova는 초기화 시퀀스 전엔 침묵한다.** `sessionStart`만 보내고 25초 기다려도 응답이 없다. 그래서 스파이크의 판정 기준은 "출력이 온다"가 아니라 **"요청이 수락되고 4xx가 없다"**이고, "조용함 = 성공"이 위험하므로 음성 대조군(존재하지 않는 모델)으로 하네스가 실패를 잡는지 먼저 확인한다.

**모델 ID 확정**: `amazon.nova-2-sonic-v1:0`이 맞다. `amazon.nova-sonic-v1:0`·`us.amazon.nova-sonic-v1:0`은 ValidationException(존재하지 않음). SDK docstring의 "only `amazon.nova-sonic-v1:0` supported"는 구버전 서술이다.

### PostgreSQL 큐 선택 근거를 §5.0으로 신설

기존 근거는 "SQS/Redis는 과하다"(단순화) 한 줄이었는데, **실제로는 §5.3의 원자성 요구가 외부 큐를 배제한다.** 확정 전사문 저장과 job 등록이 한 트랜잭션이어야 하는데 DB insert와 외부 큐 전송은 원자적으로 묶을 수 없다(dual-write). 해결하려면 PostgreSQL outbox 테이블 + 릴레이가 필요하므로 **외부 큐 쪽이 엄격히 더 복잡하다.** 이 근거는 사용자 수와 무관해 다중 사용자로 확장해도 뒤집히지 않는다.

문서 불일치 1건도 고쳤다 — `nova-sonic-claude-architecture.md:137`이 아직 "SQS + Worker 또는 Redis Queue"로 남아 있었다.

### 학습 코치 Agent 설계서 (신규, 3단계)

`docs/design/2026-08-25-learning-coach-agent-design.md` (410줄, **검토 전 초안**).

고정 시나리오 1개(`app/services/sessions.py:29`의 `limit 1`)를 대체해, 학습자가 실제로 틀린 것에서 오늘의 연습을 정한다. 캡틴 승인 3건: Agent 성질(LLM 판단 + 쿼리 장부), 만성 기록 방식(숫자 계산 + Claude 노트), 수준 적응 지시문 포함.

- 계획을 **앞선 세션 종료 시** 미리 만든다 → 사용자 대기 경로에 Claude 호출 0개
- 쿼리는 사실만 제공하고 만성 판정·우선순위는 Claude가 한다 (임계값 발명 금지)
- 만성 지표는 **새 컬럼 없이 계산된다**(라이브 DB로 확인). 단 지속 기간을 `error_patterns.created_at` 기준으로 재면 **음수가 나온다**(실측 −3.8초) — 발화 시각의 min/max를 써야 한다
- 자체 검토에서 구멍 1건 발견: `next_review_at`을 쓰는 주체가 어디에도 없어 "오늘 복습할 목록"이 항상 빈다 → §4.1에서 갱신 주체를 확정
- 새 테이블 3개(`session_plans`·`learner_notes`·`pattern_attempts`) + 컬럼 1개(`suggested_contexts`) + CHECK 확장 1개, `002` 마이그레이션
- 4 Lenses 검증 + 수용 시나리오 10건 + 실물 검증 1건

---

## 제품 정의·설계 정본

- 제품: 반복 영어 오류를 패턴으로 기억해 말하기 중심으로 재훈련하는 개인화 학습 Agent (일상 Q&A → IT 업무 → AWS Engage Manager 보고)
- 정본 문서
  - `docs/PRD.md` / `docs/requirements-summary.md` / `docs/agent-system-prompt.md`(지시문 고정부) / `docs/first-4-weeks.md`(손으로 쓴 시나리오 뱅크)
  - `docs/design/2026-08-24-first-vertical-slice-design.md` (리뷰 5회 승인, §5.0 신설)
  - `docs/design/2026-08-25-first-slice-acceptance-criteria.md` (critic 2회 PASS, 이월표 갱신)
  - `docs/design/2026-08-25-phase1-implementation-plan.md` (12태스크)
  - `docs/design/2026-08-25-learning-coach-agent-design.md` (3단계, **검토 전**)
  - `docs/ops/iam-setup-nova-sigv4.md` (IAM 절차 + SDK 함정 §5.1)
  - `docs/database-schema.md` / `docs/nova-sonic-claude-architecture.md` / `docs/voice-architecture.md`
- 기술: us-west-2 / `amazon.nova-2-sonic-v1:0` / `us.anthropic.claude-opus-5` (**`[1m]` 접미사 금지** — Bedrock 프로필 아님, 1M은 `context-1m-2025-08-07` 베타 플래그) / FastAPI+asyncpg / PG 큐(SQS·Redis 배제, 근거 §5.0) / Next.js 16 / podman / 인증 없음·고정 사용자 1명·localhost 전용
- 데이터 규칙: 오류는 재사용 가능한 패턴 단위(`unique(user_id, pattern_key)`), 복습 1·3·7일(로직 미구현 — 스키마만), `voice_command` 발화는 분석 제외, 음성 녹음 기본 미저장(opt-in)
- HTML 현황 보고서 3부: `docs/status-report-2026-08-25*.html` (Slack #clawair 전송 완료). 갱신 전 버전은 `docs/backup/`

## 구현 중 확정된 주요 판단 (요약)

- **큐 의미론**: claim당 고유 lease token / `attempts`는 claim 시 +1(상한 5 = 최대 5회 호출) / claim 내장 reaper가 lease 만료+상한 도달 좀비를 `failed`로 수렴 / 모든 상태 전이·결과 쓰기는 `status='running' and locked_by=token` 조건 원자화 / 시계는 `clock_timestamp()` (Postgres `now()`는 트랜잭션 고정이라 백오프 무력화 — 실측)
- **멱등성**: 분석 결과는 발화 단위 replace(delete+insert 한 트랜잭션). `frequency`는 행 수 재계산, `last_seen_at`은 **발화 시각** 기준
- **pattern_key 계약(§5.6)**: 기존 key 목록 프롬프트 주입 + 재사용 우선 + 신규만 `{category}_{snake}` + 표기 정규화
- **빈/공백 전사문** = findings 0건 done (재시도 소진 금지) + Gateway 미저장 이중 방어
- **Nova 포트**: 데이터 경로만 고정, 수명·barge-in은 Phase 2 확장. import 격리(AST 검사) — factory만 스텁을 안다
- **결과 API**: R2 5분기 우선순위(failed→no_utterances→analyzing→partial_failure→final), severity는 CASE ordinal, 대표 문구는 `eo.id` tertiary key로 결정화
- **agent 발화도 `utterances`에 저장**(job은 user learning만 — W6), 릴레이 예외 세션은 `completed`(`failed`는 연결 실패 전용)

## 후속(비차단) 항목

- `pending_learning_utterances` 함수가 앱에서 미사용 (AC W6 대응물로 유지 중 — 삭제 여부 캡틴 판단)
- WS 엔드포인트 origin 미검증 (localhost 단일 사용자라 수용 — 인증 도입 시 처리)
- `botocore` 재시도 미설정(스로틀 중복 과금) — Phase 2 첫 운영 관찰 대상
- `tests/`·`scripts/`가 문서화된 lint 게이트(`cd app/backend && ruff check .`) **범위 밖**이다 — 별도 실행 필요
- 이연 minor 33건 전건 "병합 전 필수 아님" triage 완료 — 목록·근거는 ledger
- **미추적 파일 2개**: `docs/ops/2026-08-26-test-harness.html`, `docs/ops/2026-08-26-test-harness-report.html` — 이번 세션에서 만든 것이 아니라 출처 미확인. 커밋하지 않았다

## 다음 작업 후보

우선순위는 캡틴 결정 사항이다.

1. **Phase 1 완료 선언** — 캡틴 마이크 세션 1회 (프론트 dev 서버 재시작 후) 또는 이월 수용 명시
2. **학습 코치 Agent 구현 계획** — 설계서 검토 → `superpowers:writing-plans`. 설계서 §12.1의 **분해 여부**(기록·계산 / 판단·적용 2슬라이스)와 §11 미결 3건(최근 창 14일 / 정답 판정 주체 / `impact_score`)이 선행 결정
3. **Phase 2 Nova 실연동** — 관문은 통과했다. 어댑터 구현은 아직 없고, 포트 `start()`에 세션 지시문 인자 추가가 필요하다 (AC가 허용한 확장)
4. **보안** — access key 로테이션

## 다음 세션 진입 절차

1. `git log --oneline -6`으로 위 커밋 5건이 있는지 확인 (HEAD = `57b2400` 이후)
2. **포트 함정 절을 먼저 읽어라** — 백엔드는 `--port 8002`, 프론트 `.env.local`은 `:8002`
3. 검증 게이트 4개를 돌려 현재 상태를 실측으로 확인 (206 passed / ruff · format · ty clean)
4. Phase 2를 건드리면 `spike_nova_bidirectional.py`로 자격증명이 여전히 유효한지 먼저 확인 (키 로테이션 시 여기서 먼저 깨진다)
5. 완료 선언은 AC 문서 §완료 선언 규칙 6항목 전건 충족 시에만 — 미충족이면 완료라 부르지 않는다
6. 프로세스 상세(모든 ruling·이연 minor·red→green 증거 위치)는 `.superpowers/sdd/2026-08-25-phase1-implementation-plan/progress.md` (ledger, git 미추적)

## 구현 시작 전 확인 항목 (이력)

- [x] `amazon.nova-2-sonic-v1:0` 실존·streaming 확인 (2026-08-24)
- [x] `us.anthropic.claude-opus-5` 호출 권한 — invoke HTTP 200 (2026-08-24)
- [x] 오디오 녹음 보관 — 첫 슬라이스에서 켜지 않음 (기본 미저장 opt-in, 캡틴 승인)
- [x] PostgreSQL 컨테이너(podman) — 기동·마이그레이션·시드 확인
- [x] **SigV4 자격증명 발급 + Nova 양방향 왕복 확인 (2026-08-26)** — Phase 2 진입 조건 충족
- [ ] Phase 1 완료 선언 — 캡틴 게이트 1건 대기
