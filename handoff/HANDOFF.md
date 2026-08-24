# OhMyEnglish Handoff

## 현재 상태 (2026-08-25 갱신 — Phase 1 구현 막바지)

**첫 수직 슬라이스(Phase 1)의 코드 태스크가 사실상 완료됐다.** 백엔드 전체(스키마·PG 큐·전사문·Claude 분석 파이프라인·워커·결과 API·Audio Gateway+스텁)와 프론트엔드(Next.js 세션·결과 화면)가 구현·리뷰 통과 상태다. 구현 커밋 17개, **테스트 188 passed (skip/xfail 0), ruff/format/ty 전부 clean**.

### 진행 중 / 남은 작업 (순서대로)

| # | 작업 | 상태 |
|---|---|---|
| 1 | T9 fix round 1 — Gateway Important 5건(비ASCII 프레임 세션 사망, 어댑터 실패 고아 세션, 종료 시 이벤트 유실, unresponsive 런타임 선택, 사인파 톤) + CORS(localhost:3000) | **진행 중** (구현 agent 작업 중) |
| 2 | T9 fix scoped re-review | 대기 |
| 3 | **W-live** — 실제 Claude 2발화 스모크 (`scripts/smoke_analysis.py` 작성+실행, 패턴 병합 실물 검증) | 대기 (T11) |
| 4 | **E2E-S** — 브라우저 6스텝 스모크 (AC 문서 §E2E-S — CORS 반영 후) | 대기 (T12) |
| 5 | `/simplify` → 재검증 → **최종 whole-branch 리뷰**(최상위 모델) → 완료 선언 6항목 대조 | 대기 |

완료 선언 기준은 `docs/design/2026-08-25-first-slice-acceptance-criteria.md` §완료 선언 규칙(6항목)이 정본이다 — 전 AC pass + W-live + E2E-S + red→green 증거 + /simplify + code-review Approve.

### ⚠️ 유일한 하드 블로커 (Phase 2 진입 조건) — SigV4 자격증명

**Nova Sonic 양방향 스트림은 Bedrock API key(bearer)로 호출할 수 없다** — 실측 확정 (2026-08-25):

| 엔드포인트 | bearer token |
|---|---|
| `/invoke` | HTTP 200 |
| `/invoke-with-response-stream` | HTTP 200 |
| `/invoke-with-bidirectional-stream` | **HTTP 403 `This operation does not support API Keys`** |

**발급 방식은 미결(캡틴 "나중에 결정")** — Phase 2(Nova 실연동) 착수 전 반드시 결정. 절차 가이드: `docs/ops/iam-setup-nova-sigv4.md` (Slack #clawair 전송 완료). Phase 1은 이 블로커와 무관하게 완주 가능 — Nova는 포트+스텁으로 격리했고 Claude 분석은 bearer로 동작한다(실측 200).

## 구현 완료 내역 (태스크 → 커밋)

| 태스크 | 커밋 | 리뷰 결과 |
|---|---|---|
| T1 스캐폴딩+자격증명 격리(config 단일점) | `de61434`, fix `3d823ae` | Approve (fix: pool 경쟁 조건) |
| T2 001 스키마 재작성+문서 정합화+시드 | `b0b2323` | Approve — 라이브 DB로 요건 전건 대조 |
| T3 PG 큐(lease token·reaper·백오프) | `1351c0b`, fix `e002f79`·`fb3754d` | Approve — 구현자가 계획 결함(poison-pill 영구 루프) 발견, reaper ruling으로 해소. 리뷰 Important 3건(원자성·clock_timestamp·동시쓰기) 전건 해소 |
| T4 전사문 저장+원자적 job 등록 | `e6f58a7` (fix는 T3와 공유) | Approve |
| T5 Claude 클라이언트+W7 출력 경계 | `fb1839b` | Approve (배치 리뷰) |
| T6 분석 파이프라인(replace 멱등·§5.6 key 계약) | `e96ab01` | Approve — 뮤테이션 테스트로 트랜잭션 경계 가드 실증 |
| T7 워커 루프(동시성 1, WORKER_ENABLED) | `086a42e`, fix `010c90c`+chore `f315fa5` | Approve — Important 5건(MAX_TOKENS 16000, tx-밖 호출 가드, 빈 전사문 0건 done, 종료 상한 15s, key 정규화) 해소 |
| T8 결과 API(R2 5분기·severity ordinal) | `7d453e4`, fix `f183249` | Approve (fix: 대표 문구 tie-break 결정화) |
| explanation wave (U2 "한 줄 이유" 관통 — 계획 결함 수정) | `79ce9e2` | Approve 이슈 0건 |
| T9 Gateway+Nova 포트+스텁+WS | `bac4144` | 스펙 ✅ / **fix round 1 진행 중** (Important 5 + CORS) |
| T10 프론트엔드(Next.js 16, U1·U2 5상태) | `346bf23` | build+lint 통과. 실질 판정은 E2E-S (AC U-검증 원칙) |

프로세스 상세(모든 ruling·이연 minor·red→green 증거 위치)는 `.superpowers/sdd/2026-08-25-phase1-implementation-plan/progress.md`(ledger, git 미추적)에 있다.

## 로컬 실행 방법

```bash
# DB (podman — docker 없음)
scripts/dev_db.sh start          # postgres:16-alpine, port 5433, ohmy/ohmy/ohmyenglish
python3 scripts/migrate.py       # 001 적용 + 고정 사용자·시나리오 3행 시드 (멱등)

# 백엔드 (app/backend, Python 3.13 venv — uv)
cd app/backend && .venv/bin/uvicorn app.api.main:app --port 8000
#   .env: DATABASE_URL, AWS_REGION=us-west-2, AWS_BEARER_TOKEN_BEDROCK(Claude용)
#   WORKER_ENABLED=false 로 기동하면 분석 워커 정지 (E2E-S 스텝 3용)
#   voice_adapter=stub(기본) | stub_unresponsive(연결 실패 재현 — T9 fix 후)

# 프론트 (app/frontend, Next.js 16)
cd app/frontend && npm run dev   # localhost:3000, NEXT_PUBLIC_API_BASE 기본 localhost:8000

# 검증 게이트 (전부 통과 상태여야 정상)
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . && .venv/bin/ruff format --check . && ty check
```

## 구현 중 확정된 주요 판단 (요약 — 전문은 ledger)

- **큐 의미론**: claim당 고유 lease token / attempts는 claim 시 +1(상한 5 = 최대 5회 호출) / claim 내장 reaper가 lease 만료+상한 도달 좀비를 `failed`로 수렴 / 모든 상태 전이·결과 쓰기는 `status='running' and locked_by=token` 조건 원자화 / 시계는 `clock_timestamp()`(Postgres `now()`는 트랜잭션 고정이라 백오프 무력화 — 실측)
- **멱등성**: 분석 결과는 발화 단위 replace(delete+insert 한 트랜잭션) — 재시도·재분석 안전, 복수 occurrence 보존. `frequency`는 행 수 재계산, `last_seen_at`은 발화 시각 기준
- **pattern_key 계약(§5.6)**: 기존 key 목록 프롬프트 주입 + 재사용 우선 + 신규만 `{category}_{snake}` + 공백/대소문자 변형은 기존 표기로 정규화
- **빈/공백 전사문** = findings 0건 done (재시도 소진 금지) + Gateway 미저장 이중 방어
- **Claude 클라이언트**: legacy InvokeModel + bearer (Phase 1 임시 이탈 — 설계서 §4.1의 "bearer 금지"는 Phase 2 SigV4 전환으로 해소, config.bedrock_client() 한 곳 격리라 전환 = 설정 교체). MAX_TOKENS 16000(thinking 예산 고려), stop_reason 관측
- **Nova 포트**: 데이터 경로만 고정(부분/확정 전사문·오디오), 수명·barge-in은 Phase 2 확장. import 격리(AST 검사) — factory만 스텁을 안다
- **결과 API**: R2 5분기 우선순위(failed→no_utterances→analyzing→partial_failure→final), severity는 CASE ordinal, 대표 문구는 eo.id tertiary key로 결정화
- **agent 발화도 utterances에 저장**(job은 user learning만 — W6), 릴레이 예외 세션은 completed(failed는 연결 실패 전용)

## 제품 정의·설계 정본 (변경 없음)

- 제품: 반복 영어 오류를 패턴으로 기억해 말하기 중심으로 재훈련하는 개인화 학습 Agent (일상 Q&A → IT 업무 → AWS Engage Manager 보고)
- 설계 정본: `docs/design/2026-08-24-first-vertical-slice-design.md` (리뷰 5회 승인) / 완료 기준: `docs/design/2026-08-25-first-slice-acceptance-criteria.md` (critic 2회 PASS) / 구현 계획: `docs/design/2026-08-25-phase1-implementation-plan.md` (12태스크)
- 기술: us-west-2 / `amazon.nova-2-sonic-v1:0`(Phase 2) / `us.anthropic.claude-opus-5`(**`[1m]` 접미사 금지** — Bedrock 프로필 아님, 1M은 `context-1m-2025-08-07` 베타 플래그) / FastAPI+asyncpg / PG 큐(SQS·Redis 배제) / Next.js / podman / 인증 없음·고정 사용자 1명·localhost 전용
- 데이터 규칙: 오류는 재사용 가능한 패턴 단위(`unique(user_id, pattern_key)`), 복습 1·3·7일(3단계 로직은 미구현 — 스키마만), `voice_command` 발화는 분석 제외, 음성 녹음 기본 미저장(opt-in)
- Hermes는 MVP 미사용(비결정론 agent loop·Python <3.14 제약) — 주간 리포트 cron+Slack 시점에 재검토. 세션 총평(`summarize_session`)은 다음 슬라이스(스키마는 준비됨)

## 다음 세션 진입 절차

1. `git log --oneline`과 ledger(`.superpowers/sdd/2026-08-25-phase1-implementation-plan/progress.md`)로 현재 위치 확인 — ledger의 `Task <N>: complete` 줄이 완료 태스크
2. 위 "남은 작업" 표의 첫 미완 항목부터 재개 (T9 fix가 커밋됐는지 `git log`로 확인)
3. E2E-S 6스텝은 AC 문서 §E2E-S가 정본 — 실행 기록을 완료 보고에 첨부
4. 완료 선언은 AC 문서 6항목 전건 충족 시에만 — 미충족이면 완료라 부르지 않는다 (캡틴 최종 승인 필요)

## 구현 시작 전 확인 항목 (이력)

- [x] `amazon.nova-2-sonic-v1:0` 접근 — 실존·streaming 확인 (2026-08-24)
- [x] `us.anthropic.claude-opus-5` 호출 권한 — invoke HTTP 200 (2026-08-24)
- [x] 오디오 녹음 보관 — 첫 슬라이스에서 켜지 않음 (기본 미저장 opt-in, 캡틴 승인)
- [x] PostgreSQL 컨테이너(podman) — 기동·마이그레이션·시드 동작 확인 (테스트 188건이 실DB로 검증)
- [ ] **SigV4 자격증명 발급 방식 결정 + 발급** — Phase 2 하드 블로커 (가이드: `docs/ops/iam-setup-nova-sigv4.md`)
