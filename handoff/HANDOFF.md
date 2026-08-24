# OhMyEnglish Handoff

## 현재 상태 (2026-08-25 갱신)

요구사항, 제품 설계, 데이터 모델, Agent 프롬프트, 학습 플로우, UI 스토리보드, 음성 아키텍처를 확정했고, **첫 수직 슬라이스 상세 설계서가 리뷰 5회(Codex 3회 + Fable critic 2회 + 캡틴)를 거쳐 승인됐다** — `docs/design/2026-08-24-first-vertical-slice-design.md` (구현 결정의 정본).

아직 실제 웹 애플리케이션, FastAPI 서버, 테스트 코드는 구현하지 않았다. 저장소는 git 초기화됐다(브랜치 `design/first-vertical-slice`).

### ⚠️ 구현 착수의 유일한 하드 블로커 — SigV4 자격증명

**Nova Sonic 양방향 스트림은 Bedrock API key(bearer)로 호출할 수 없다** — 실측 확정 (2026-08-25):

| 엔드포인트 | bearer token |
|---|---|
| `/invoke` | HTTP 200 |
| `/invoke-with-response-stream` | HTTP 200 |
| `/invoke-with-bidirectional-stream` | **HTTP 403 `This operation does not support API Keys`** |

서비스가 API Key를 특정해 거부하므로 SigV4 자격증명이 필수다. **발급 방식은 미결(캡틴 "나중에 결정") — 구현 착수 전 반드시 결정한다.** 권장안: Bedrock 권한만 가진 전용 IAM user access key → `.env`. 상세: 설계서 §4.1.

## 제품 한 줄 정의

OhMyEnglish는 사용자의 반복 영어 오류를 패턴으로 기억하고, 일상 질문·답변에서 IT 프로젝트 보고까지 말하기 중심으로 재훈련하는 개인화 영어 학습 Agent다.

## 확정된 사용자 수준과 목표

- 현재 수준
  - 일상적인 짧은 문장, 인사, small talk 가능
  - `I want to ~`, `I need to ~`, `I'd like ~` 등 단문 패턴 중심
  - 일상 단어 이해 가능
- 학습 방식
  - Speaking 중심
  - 반복 오류를 1일·3일·7일 간격으로 다른 문맥에서 재학습
  - 일상 Q&A, 업무 역할극, 쉐도잉, 추가 자유 학습 지원
- 장기 목표
  - 비즈니스 미팅 참여
  - IT 프로젝트 리딩과 설명
  - AWS Engage Manager 대상 프로젝트 상태 보고

## 확정된 기술 결정

| 영역 | 선택 |
|---|---|
| AWS Region | `us-west-2` |
| 실시간 음성 모델 | `amazon.nova-2-sonic-v1:0` |
| 학습 분석 모델 | `us.anthropic.claude-opus-5` |
| Backend | Python |
| API / Audio Gateway | FastAPI + `asyncio` |
| Frontend | Next.js / React 권장 |
| 데이터베이스 | PostgreSQL |
| 비동기 작업 | **PostgreSQL 큐** (`analysis_jobs` + `FOR UPDATE SKIP LOCKED`) — SQS/Redis는 과함 (캡틴 결정) |
| 로컬 DB 실행 | podman 컨테이너 (로컬에 docker 없음) |
| 백엔드 자격증명 | **SigV4 전용** — bearer token은 Nova 양방향에서 403 |

### 중요 주의사항

- 두 모델 ID 모두 us-west-2 실측 검증 완료 (2026-08-24): `us.anthropic.claude-opus-5` invoke HTTP 200, `amazon.nova-2-sonic-v1:0` 실존(`in=[SPEECH] → out=[SPEECH,TEXT]`).
- **`[1m]` 접미사를 모델 ID에 붙이지 않는다** — Bedrock 프로필이 아니며 400이다 (Claude Code 전용 표기). 1M 컨텍스트는 `anthropic_beta: ["context-1m-2025-08-07"]`로 켠다 (HTTP 200 확인).
- Hermes Agent는 MVP에서 쓰지 않는다 (LLM agent loop라 결정론적 워커 부적합, Python <3.14 제약). 주간 리포트 cron + Slack DM 시점에 재검토.
- Claude 호출은 `us.anthropic.claude-opus-5` US geographic 추론 프로필을 사용한다.
  - 요청은 `us-west-2`에서 시작하고, 추론은 미국 리전 안에서만 라우팅된다.
  - `global.anthropic.claude-opus-5`는 전 세계 리전으로 라우팅될 수 있으므로 사용하지 않는다.
  - 엄격히 `us-west-2` 단일 리전만 허용해야 하는 요구사항이 생기면, 구현 전 in-region 모델 가용성과 권한을 별도로 검증한다.
- OpenClaw는 현재 사용하지 않는다.
  - 실시간 음성 및 학습 기능은 OhMyEnglish 웹/모바일 앱과 Audio Gateway가 직접 담당한다.
  - Telegram, Slack, WhatsApp 같은 외부 메신저 학습 알림이 필요할 때만 선택적으로 검토한다.
- 음성 녹음은 기본 저장하지 않고 opt-in으로 설계한다.
- API 키와 AWS 자격 증명은 브라우저에 노출하지 않는다.

## 핵심 아키텍처

```text
Browser / Mobile
  - microphone, speaker, live transcript, UI controls
  - voice command button
        │ Secure WebSocket
        ▼
Python FastAPI Audio Gateway
  - authentication
  - audio frame relay
  - session state
  - command router
        │ bidirectional stream
        ▼
Amazon Nova 2 Sonic
  - real-time speech-to-speech
  - daily conversation, Q&A drills
  - short correction, interruption, voice commands
        │ finalized transcript events
        ▼
Claude Opus 5 Worker
  - error pattern extraction
  - review scheduling
  - session feedback
  - weekly/monthly analysis
        ▼
PostgreSQL
  - users, sessions, utterances, error patterns, review tasks
```

## 모델 역할 분리

- **Nova 2 Sonic (실시간 경로)**
  - 음성 입력과 음성 응답
  - 일상 대화와 질문·답변 드릴
  - 짧은 즉시 교정
  - 음성 명령 처리
  - 사용자가 끼어들면 Agent 음성을 멈추고 다시 듣기

- **Claude Opus 5 (비동기 분석 경로)**
  - 전사문에서 반복 문법/구문 오류 추출
  - `error_patterns` 업데이트
  - 1일·3일·7일 복습 과제 생성
  - 세션 종료 피드백
  - 주간·월간 학습 리포트
  - IT 프로젝트 보고 학습 계획

Claude를 매 음성 턴의 실시간 응답 경로에 넣지 않는다. 응답 지연을 줄이기 위해 Nova 2 Sonic이 대화를 담당하고, Claude는 확정 전사문을 비동기로 분석한다.

## 주요 기능 요구사항

- 매일 10~15분 Speaking 중심 학습
- 일상 대화와 동일 문형 반복 Q&A
- 세션당 고영향 오류 최대 1~2개만 교정
- 오류 패턴별 다른 문맥 재학습
- 일일 목표 완료 뒤에도 추가 학습 제한 없음
  - 자유 대화
  - 질문 다섯 개 더
  - 약점 패턴 집중
  - 업무 역할극
  - 쉐도잉
- UI와 음성 명령 모두 지원
  - “추가 연습 시작”
  - “질문 다섯 개 더”
  - “천천히 다시 말해줘”
  - “힌트 줘”
  - “다음 문제”
  - “오늘 학습 끝낼게”
- 종료·삭제 등 영향이 큰 음성 명령은 한 번 더 확인

## 핵심 데이터 규칙

- 오류는 개별 틀린 문장이 아니라 재사용 가능한 패턴으로 저장한다.

```text
pattern_key: past_tense_in_work_update
original: Yesterday I work on the API.
target: Yesterday, I worked on the API.
review: 1d → 3d → 7d
```

- `learning_sessions.learning_source`
  - `recommended`: 오늘의 권장 학습
  - `additional`: 권장량 완료 뒤의 추가 학습
  - `user_requested`: 사용자가 직접 특정 패턴으로 요청한 학습
- `utterances.utterance_type`
  - `learning`: 영어 학습 발화
  - `voice_command`: UI/세션 제어 명령
  - `command_confirmation`: 종료·삭제 등의 확인 발화
- `voice_command`는 오류 분석 대상에서 제외한다.

## 생성된 주요 문서

| 문서 | 용도 |
|---|---|
| `README.md` | 프로젝트 구조와 문서 진입점 |
| `docs/requirements-summary.html` | 사용자 작성 스타일의 핵심 요구사항 HTML |
| `docs/requirements-summary.md` | 핵심 요구사항 Markdown |
| `docs/PRD.md` | 제품 요구사항과 수용 기준 |
| `docs/database-schema.md` | 데이터 모델 설명 |
| `db/migrations/001_initial_schema.sql` | PostgreSQL 초기 스키마 |
| `docs/agent-system-prompt.md` | 영어 코치 Agent 시스템 프롬프트 |
| `docs/first-4-weeks.md` | 첫 4주 학습 플로우 |
| `docs/storyboard.html` | UI 스토리보드 |
| `docs/voice-architecture.md` | 음성 인식·발화·제어 설계 |
| `docs/nova-sonic-claude-architecture.md` | Nova 2 Sonic + Claude 상세 아키텍처 |
| `tests/README.md` | 테스트 전략 |
| `docs/design/2026-08-24-first-vertical-slice-design.md` | **첫 수직 슬라이스 설계서 (승인됨 — 구현 결정의 정본)** |

## 다음 구현 작업 순서

### 1. 코드 프로젝트 초기화

기존 최상위 `app/` 디렉터리를 애플리케이션 코드의 정본으로 사용한다. 테스트는 스택 안으로 넣지 않고 최상위 `tests/`를 그대로 유지한다 (`README.md` 프로젝트 구조와 `tests/README.md` 기준).

```text
app/
├── frontend/                    # Next.js / React
└── backend/                     # FastAPI
    └── app/
        ├── api/                 # HTTP, WebSocket endpoint
        ├── audio_gateway/       # Nova 2 Sonic 양방향 스트림
        ├── workers/             # Claude 분석 Worker
        ├── models/              # DB model
        └── services/            # 학습·복습 domain service
tests/                           # unit, integration, e2e (최상위 유지)
scripts/                         # 개발/운영 보조 스크립트
infra/                           # AWS 배포 환경
```

### 2. 첫 번째 수직 기능 (Vertical Slice)

> **구현 순서·상세 결정은 설계서 §10이 정본이다**: ① SigV4 자격증명 확보(하드 블로커) → ② `001_initial_schema.sql` 재작성 + `database-schema.md` 정합화 → ③ 백엔드 + 분석 Worker(TDD, Nova 없이 테스트 가능한 부분 먼저) → ④ Audio Gateway 최소 왕복 → ⑤ 프론트엔드 → ⑥ barge-in·롤오버 → ⑦ 통합·E2E.
> 주요 확정: `analyze_utterance` 단일 job(세션 총평은 다음 슬라이스), pattern_key 정규화 계약(§5.6), 복습 1·3·7일, 오류 카테고리 영문 코드 7종.

다음 한 흐름을 먼저 완성한다.

```text
브라우저 마이크
 → FastAPI WebSocket
 → Nova 2 Sonic
 → 음성 응답 + 실시간 전사문
 → Claude Opus 5 분석
 → error_patterns 저장
 → 학습 결과 화면
```

첫 시나리오는 일상 질문·답변 3개로 제한한다.

```text
What do you usually do after work?
What do you usually do on weekends?
What do you need to do tonight?
```

### 3. 추가 학습과 음성 명령

- UI `질문 다섯 개 더`
- UI `약점 패턴으로 연습`
- 음성 `추가 연습 시작`
- 음성 `천천히 다시 말해줘`
- 음성 `힌트 줘`
- 음성 `오늘 학습 끝낼게` + 종료 확인

### 4. 업무 영어와 리포트

- daily update
- blocker 공유
- 일정 변경
- Status / Change / Risk / Decision needed / Next steps 보고 역할극

### 5. 테스트

- 단위: 오류 패턴 정규화, 복습 우선순위, 음성 명령 Intent
- 통합: 전사문 → Claude 분석 → 패턴 저장 → 복습 과제 생성
- E2E: 학습 시작 → 대화 → 교정 → 결과 → 추가 학습

## 구현 시작 전 확인할 항목

- [x] `amazon.nova-2-sonic-v1:0` 접근 — 실존·streaming 확인 (2026-08-24)
- [x] `us.anthropic.claude-opus-5` 호출 권한 — invoke HTTP 200 (2026-08-24)
- [x] 오디오 녹음 보관 — 첫 슬라이스에서 켜지 않음 (기본 미저장 opt-in, 캡틴 승인)
- [ ] **SigV4 자격증명 발급 방식 결정 + 발급** — 유일한 하드 블로커. 발급 후 양방향 스트림 스파이크 재실행으로 1회 왕복 확인
- [ ] PostgreSQL 컨테이너(podman) 기동 및 연결 정보 확정
