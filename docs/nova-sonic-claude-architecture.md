# Nova Sonic + Claude 아키텍처 정의

## 1. 결정

OhMyEnglish의 실시간 음성 학습은 **Amazon Nova 2 Sonic**이 담당하고, 개인화 학습 판단과 장기 분석은 **Claude Opus 5 on Amazon Bedrock**이 담당한다.

## 확정된 기술 결정

- AWS Region: `us-west-2`
- 실시간 음성 모델: `amazon.nova-2-sonic-v1:0`
- 학습 분석 모델: `us.anthropic.claude-opus-5`
- Backend / Audio Gateway: Python
- Python 웹 프레임워크: FastAPI + `asyncio`

> Claude 호출은 US geographic profile인 `us.anthropic.claude-opus-5`를 사용한다. 요청은 `us-west-2`에서 시작하며 추론은 미국 리전 안에서만 라우팅된다. 전 세계 상용 리전으로 라우팅될 수 있는 `global.anthropic.claude-opus-5`는 사용하지 않는다. 단일 `us-west-2` 상주가 필수라면 배포 전에 in-region 가용성과 권한을 검증한다.

| 역할 | 담당 모델/컴포넌트 | 이유 |
|---|---|---|
| 실시간 듣기·말하기·끊김 없는 대화 | Nova 2 Sonic | 음성 입력과 음성 출력을 하나의 양방향 스트림에서 처리 |
| 일상 대화, 반복 Q&A, 즉시 짧은 교정 | Nova 2 Sonic + 학습 컨텍스트 | 사용자 응답 지연을 최소화 |
| 오류 패턴 추출·숙련도 계산 | Claude Opus 5 | 문법·업무 표현의 깊이 있는 텍스트 분석 |
| 주간/월간 분석·다음 커리큘럼 | Claude Opus 5 | 긴 학습 이력에서의 추론과 계획 |
| 복습 큐·사용자 데이터·권한 | 애플리케이션 서버 + PostgreSQL | 모델과 비즈니스 상태를 분리 |

## 2. OpenClaw 사용 결정

**MVP에서는 사용하지 않는다.**

OpenClaw는 여러 메신저·채널을 AI Agent에 연결하는 self-hosted gateway다. OhMyEnglish는 전용 웹/모바일 학습 앱에서 실시간 음성, 전사문, 복습 UI를 일관되게 제공해야 하므로 OpenClaw를 실시간 경로에 두지 않는다.

OpenClaw가 유용해지는 선택적 시점은 다음과 같다.

- Telegram/Slack/WhatsApp으로 “오늘 질문 3개” 같은 텍스트 복습을 발송할 때
- 사용자가 메신저에서 음성이 아닌 짧은 텍스트 드릴을 할 때
- 개인 일정·메신저 알림을 학습 리마인더와 연결할 때

이 경우에도 OpenClaw는 **별도 채널 어댑터**로 두고, 학습 데이터와 음성 세션의 기준 시스템은 OhMyEnglish 서버로 유지한다.

## 3. 목표 아키텍처

```text
┌────────────────────────── Browser / Mobile App ──────────────────────────┐
│ UI controls · mic · speaker · live transcript · command button           │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ Secure WebSocket
┌──────────────────────────────▼───────────────────────────────────────────┐
│ OhMyEnglish Audio Gateway                                                  │
│ - user authentication / session authorization                              │
│ - audio frame relay / session rollover                                     │
│ - voice command router                                                     │
│ - tool execution and event publishing                                      │
└───────────────┬────────────────────────────┬──────────────────────────────┘
                │ bidirectional audio        │ finalized learning events
                ▼                            ▼
┌─────────────────────────┐       ┌───────────────────────────────────────┐
│ Amazon Nova 2 Sonic     │       │ Claude Opus 5 Worker                   │
│ - speech-to-speech      │       │ - error pattern extraction             │
│ - VAD / interruption    │       │ - correction quality check             │
│ - short live coaching   │       │ - review plan / weekly report          │
│ - tool calls            │       └──────────────────┬────────────────────┘
└─────────────┬───────────┘                          │
              │ transcripts / tools                  ▼
              └───────────────────────┌───────────────────────────────────┐
                                      │ PostgreSQL + Queue + Object Store  │
                                      │ profile · patterns · tasks · logs  │
                                      └───────────────────────────────────┘
```

## 4. 실시간 음성 세션 흐름

### 4.1 세션 시작

1. 사용자가 UI에서 `오늘 학습 시작` 또는 음성으로 “학습 시작”을 요청한다.
2. 앱은 OhMyEnglish 서버에 인증된 WebSocket 세션을 연다.
3. 서버는 사용자 프로필, 오늘의 목표, 상위 오류 1~2개, 현재 시나리오를 조회한다.
4. 서버는 이 정보를 Nova 2 Sonic의 세션 지시문과 도구 컨텍스트로 제공한다.
5. 브라우저는 마이크 오디오 프레임을 Audio Gateway로 전송하고, Gateway는 Nova 2 Sonic 양방향 스트림으로 전달한다.

### 4.2 한 번의 학습 턴

```text
사용자 음성
 → Nova 2 Sonic 전사·의도 판단
 → (필요 시) get_learning_context 도구 호출
 → Nova 2 Sonic의 짧은 음성 응답
 → 브라우저 재생 + 전사문 표시
 → 확정 전사문 이벤트 저장
 → Claude 분석 작업 큐 등록
```

정상 대화에서 Claude Opus 5는 **매 턴의 음성 응답 경로에 넣지 않는다.** 매 턴 Claude를 기다리면 실시간 대화의 반응성이 떨어진다. 대신 Nova 2 Sonic은 현재 집중 패턴과 간단한 코칭 규칙을 받으며, Claude는 확정된 턴을 비동기로 분석한다.

### 4.3 즉시 교정과 깊은 분석의 분리

| 시점 | 처리 | 사용자 경험 |
|---|---|---|
| 발화 직후 | Nova 2 Sonic | “Try: I worked on the API.”처럼 짧게 수정하고 재발화 요청 |
| 턴 확정 후 | Claude Opus 5 Worker | 오류 카테고리, 반복 여부, 패턴 키, 다음 복습일 계산 |
| 세션 종료 후 | Claude Opus 5 Worker | 잘한 점, 핵심 약점 1~2개, 다음 세션 계획 생성 |
| 주간 배치 | Claude Opus 5 Worker | 상위 오류, 개선도, 일상/업무 학습 비중 분석 |

## 5. 음성 명령 설계

Nova 2 Sonic은 대화 흐름에서 음성 명령을 감지하고, 허용된 tool만 호출한다.

| 명령 | tool | 결과 |
|---|---|---|
| “추가 연습 시작” | `start_extra_practice` | 추가 학습 선택 화면과 음성 안내 |
| “질문 다섯 개 더” | `start_qa_drill` | 같은 문형의 Q&A 5개 생성 |
| “이 문법으로 연습 만들기” | `practice_current_pattern` | 현재 오류 패턴 기반 드릴 생성 |
| “천천히 다시 말해줘” | `repeat_last_reply` | 마지막 응답을 느리게 재생 |
| “힌트 줘” | `get_hint` | 문장 시작어와 선택지 제공 |
| “다음 문제” | `skip_item` | 항목 건너뛰기 기록 |
| “일시 정지” | `pause_session` | 오디오·타이머 정지 |
| “학습 끝낼게” | `request_end_session` | 반드시 종료 확인 질문 |

일반 영어 답변은 명령으로 취급하지 않는다. 명령 버튼을 누르거나 “Oh My English, …” 호출어를 사용하면 명령 우선 모드로 처리한다.

## 6. 세션 길이와 연결 관리

Audio Gateway는 Nova 2 Sonic 세션의 서비스 제한·연결 종료 이벤트를 감시한다. 세션을 교체해야 할 때는 다음 절차로 컨텍스트를 보존한다.

1. 현재 대화의 확정 전사문과 현재 목표를 요약한다.
2. 새 Nova 2 Sonic 스트림을 연다.
3. 요약, 현재 질문, 오늘 집중 패턴을 새 세션 컨텍스트로 전달한다.
4. 사용자에게 끊김이 느껴지지 않게 재개한다.

## 7. 기술 선택

| 영역 | MVP 선택 | 이유 |
|---|---|---|
| 웹 클라이언트 | Next.js/React | 대시보드, 전사문, 음성 UI 구성 |
| 브라우저-서버 | Secure WebSocket | 오디오 프레임·이벤트 양방향 전달 |
| 음성 Gateway | Python, FastAPI + asyncio | Bedrock 스트리밍 연결과 인증 격리 |
| 실시간 음성 | Amazon Nova 2 Sonic (`amazon.nova-2-sonic-v1:0`) | 양방향 speech-to-speech |
| 학습 분석 | Claude Opus 5 (`us.anthropic.claude-opus-5`) | 오류 패턴·보고 영어·장기 계획 |
| 비동기 처리 | SQS + Worker 또는 Redis Queue | 음성 응답과 분석 분리 |
| 데이터 | PostgreSQL | 학습 이력·오류 패턴·복습 큐 |
| 음성 파일 | S3, opt-in | 필요 시에만 녹음 보관 |

## 8. 개발 단계

### Phase 1 — 음성 MVP

- Python/FastAPI Nova 2 Sonic 오디오 Gateway
- 일상 질문·답변 3개
- 실시간 전사문과 음성 응답
- UI 기반 시작/종료/반복

### Phase 2 — 개인화

- Claude Opus 5 오류 분석 Worker
- `error_patterns`, `review_tasks` 저장
- 현재 집중 패턴을 Nova 2 Sonic 컨텍스트에 주입
- 추가 학습과 음성 명령

### Phase 3 — 업무 영어

- daily update, blocker, risk 보고
- Status / Change / Risk / Ask / Next step 역할극
- 주간·월간 분석

### Phase 4 — 선택적 채널 확장

- 메신저 텍스트 복습이 필요할 때만 OpenClaw 또는 자체 채널 어댑터 검토
- 음성 핵심 경로는 계속 OhMyEnglish Audio Gateway가 담당
