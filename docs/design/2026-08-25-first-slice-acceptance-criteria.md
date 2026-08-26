# 첫 수직 슬라이스 — 개발 완료 기준 (Acceptance Criteria)

- 작성: 2026-08-25 / 개정 2회
- 상태: **확정** — critic 2회 검증(1차 CHALLENGE 필수 7건 → 전건 해소 확인, 2차 잔여 1건 반영으로 PASS 전환)
- 정본 관계: `2026-08-24-first-vertical-slice-design.md`(승인됨)의 §8 AC를 **개발 단계 기준으로 재구성**한 문서다. 설계 결정 자체는 설계서가 정본이고, 이 문서는 "무엇이 되면 개발 완료인가"를 정의한다. 설계서와의 의도적 이탈은 §범위 재정의와 §이월에 전부 기록한다.

## 범위 재정의 — Nova 연동 분리 (캡틴 결정 2026-08-25)

**Nova Sonic 실연동은 IAM(SigV4) 설정 이후 Phase 2로 분리한다.** 근거: 양방향 스트림은 bearer로 403(실측), SigV4 발급 방식은 미결. 반면 **Claude 분석 경로는 현재 bearer 자격증명으로 동작한다** (`/invoke` HTTP 200 실측) — 따라서 분석 워커는 실물로 만든다.

이 결정에 따른 설계서와의 의도적 이탈 2건 (캡틴 결정 2026-08-25 근거):

1. **§10-1 착수 게이트 오버라이드**: 설계서는 "SigV4 스파이크 통과 전 음성 경로·프론트엔드 착수 금지"였으나, 스텁 포트 도입으로 이 게이트를 대체한다 — 음성 경로는 스텁으로, 프론트엔드는 스텁 기반으로 착수한다.
2. **§2·§4.1 "bearer 금지"로부터의 임시 이탈**: Phase 1의 Claude 워커는 bearer로 호출한다. SigV4 전환은 Phase 2 이월표에 기록하며, **자격증명 획득을 설정 경계로 격리**해(bearer↔SigV4가 설정 교체로 끝나게) 전환 시 워커 코드를 손대지 않는다 (F5).

구조 원칙: **Nova 어댑터를 포트(인터페이스)로 격리**하고 스텁 구현으로 전체 흐름을 관통시킨다. 포트가 고정하는 것은 **데이터 경로**(오디오 프레임 입력, 부분/확정 전사문 이벤트·오디오 응답 출력)다. 롤오버 수명 이벤트와 barge-in 제어 연산은 Phase 2에서 인터페이스가 **확장**된다 — 이 경계의 목표는 "인터페이스 무변경"이 아니라 **그 확장이 Gateway 상위 로직(세션 수명·저장·job 등록)에 파급되지 않는 것**이다.

## 공통 픽스처 (AC3·AC4 대응 — 스텁·W-live·E2E-S가 공유)

스텁은 설계서 §1 질문 3개에 대해 고정 답변 3건을 발행하며, 그중 2건은 같은 `article` 오류를 포함한다:

| # | 질문 | 스텁 발화 | 기대 |
|---|---|---|---|
| 1 | What do you usually do after work? | `I usually go to gym after work.` | `article` 오류 검출, `target_form`에 `the` 삽입 |
| 2 | What do you usually do on weekends? | `I usually go to office by subway.` | 발화 1과 **같은 패턴으로 병합** |
| 3 | What do you need to do tonight? | `I need to finish my homework tonight.` | 오류 0건 허용 |

## Phase 1 완료 기준

각 AC는 자동 테스트 또는 명시된 검증 절차로 판정한다. 괄호는 설계서 §8 AC와의 대응.

### F — 기반

- **F1. 스키마 적용**: 재작성된 `001_initial_schema.sql`이 podman PostgreSQL에 오류 없이 적용되고, 고정 사용자 1명과 시나리오(일상 질문 3개)가 시드된다. 검증: 마이그레이션 + 시드 스크립트 실행 출력.
- **F2. 툴체인·품질 게이트**: 백엔드 venv가 Python 3.12/3.13으로 핀되고 `aws-sdk-bedrock-runtime` 0.10.0이 설치·import된다(§3 — 3.14 Rust 휠 문제를 지금 검출). `ruff check`·`ruff format --check` 통과, `ty check` 오류 0. 검증: 명령 출력 (SVG V3·V5).
- **F3. 테스트 건전성**: 전체 pytest 실패 0 **+ skip/xfail 0** (stub 테스트 금지 — `<failure_mode_guards>`). 무회귀(T4)는 기준선이 생기는 Phase 2부터 적용.
- **F4. 스키마 문서 정합화**: `database-schema.md`가 재작성된 001과 컬럼·제약 단위로 일치하고, 각 테이블의 도입 단계가 표기된다 (설계서 §6 산출물 — 문서-SQL 불일치 재발 방지).
- **F5. 자격증명 격리·비노출**: Bedrock 자격증명 획득이 설정 모듈 한 곳에 격리된다(bearer↔SigV4 전환 = 설정 교체). `.env`는 gitignore되고, 프론트엔드 번들·API 응답에 자격증명이 포함되지 않는다 (`HANDOFF.md` 보안 원칙).

### W — 분석 워커 + PG 큐

시간 의존 항목(W4·W5)은 **실시간 대기 금지** — `locked_at`/`available_at`을 과거 시각으로 직접 세팅(또는 시각 주입)해 판정한다.

- **W1. 턴 단위 비동기 분석** (≙AC3): 확정 전사문 저장과 `analyze_utterance` 등록이 한 트랜잭션이고, 워커가 claim해 분석한 뒤 `error_patterns` upsert + `error_occurrences` insert + job 완료를 한 트랜잭션으로 커밋한다. **세션이 `status='active'`인 동안 해당 job이 `done`에 도달할 수 있다** (세션 종료 대기 없음의 관측형). **오류 0건 결과(픽스처 발화 3)도 occurrence 0행·패턴 미생성으로 정상 `done` 처리된다** — W7의 스키마 거부 대상과 구분한다 (SVG T2 empty).
- **W2. 패턴 병합 + 정규화 계약** (≙AC4, §5.6): 같은 오류 유형이 다른 문장에서 나와도 `error_patterns` 행이 늘지 않고 `error_occurrences`만 추가되며 `frequency`가 실제 행 수로 재계산된다. 분석 프롬프트에 기존 `pattern_key` 목록이 주입되고, 신규 key는 `{category}_{snake}` 형식이다.
- **W3. 재시도 멱등성** (≙AC7): "결과 저장 후 status 갱신 전 크래시"를 재현해 같은 작업을 재실행해도 발화 단위 replace로 최신 결과 집합 하나만 남고 `frequency`가 부풀지 않으며, **`last_seen_at`(발화 시각 `utterances.created_at` 기준)도 재시도 후 변하지 않는다** (§6.5). 추가 거동 2건: 같은 발화의 두 번째 `pending` job 등록이 partial unique로 거부된다(§5.2), 같은 `(session_id, sequence_no)` 재commit이 거부된다(§7 무결성 가드).
- **W4. lease 회수 + 소유자 검증** (≙AC8): lease 기간(5분 — 설계 발명값, 조정 시 이 AC 수치도 갱신) 초과 `running` 작업이 회수 가능하고, 회수당한 이전 claim의 lease token으로는 결과 쓰기·상태 전이가 전부 거부된다(0행 갱신).
- **W5. 재시도 상한** (≙AC9): 호출이 계속 실패하면 `attempts` 5회에서 terminal `failed` + `last_error`가 남고 재시도가 멈춘다. 백오프 `attempts × 1분` (둘 다 설계 발명값 — 조정 시 이 AC 수치도 갱신).
- **W6. 학습 발화만 분석**: 분석 입력 선택 쿼리가 `utterance_type='learning'`만 반환한다 — `voice_command` 행을 넣어도 job이 생성되지 않는다 (`tests/README.md:14` 선행 대응, §6.2 D4 규약의 테스트 강제).
- **W7. Claude 출력 경계 검증** (§7 Boundary): Claude 출력을 신뢰할 수 없는 외부 데이터로 취급한다 — 필수 필드 누락 / `severity` 미정의값 / `confidence` 범위(0~1) 초과 / 카테고리 CHECK 밖 값을 담은 가짜 응답이 **저장 전에 스키마 검증에서 거부**되고, job이 `last_error`와 함께 실패 처리된다 (SVG V2).
- **W1~W7 검증 방식**: Claude 호출은 테스트에서 가짜 클라이언트로 대체한 단위·통합 테스트로 판정한다. 단, **패턴 병합의 실물 검증은 W-live가 담당한다** — 가짜 클라이언트로는 §5.6 계약(실제 Claude가 주입된 목록에서 기존 key를 재사용하는가)이 동어반복이 되기 때문이다.

### W-live — 실제 Claude 스모크 (공통 픽스처 2발화, 실행 출력 증빙)

`scripts/`의 스모크 스크립트가 공통 픽스처 발화 1·2를 **순서대로** 실제 분석한다. 단정:

- `error_patterns` 1행 · `error_occurrences` 2행 · `frequency=2` (필수 케이스 1 = `tests/README.md:9`의 실물 검증)
- category=`article`, `target_form`에 `the` 삽입 (≙AC3의 구체 단정)
- 두 번째 분석의 프롬프트에 첫 번째 `pattern_key`가 포함되고, 신규 key는 `{category}_{snake}` 형식 (§5.6 계약)

### R — 결과 API/화면 규칙 (≙§5.5)

- **R1. 상위 2개 선정** (≙AC5): 결과 API가 세션의 occurrence를 조인해 severity(**ordinal: high>medium>low**) → confidence desc → 발생 수 desc 순 **패턴 단위** 상위 2개를 반환한다. 3개 이상 검출된 세션에서 정확히 2개만 반환됨을 테스트.
- **R2. 상태 판정** (≙AC6): 결과 API의 상태는 아래 우선순위로 **정확히 하나**를 반환한다 (위에서 처음 매칭되는 것):
  1. `learning_sessions.status='failed'` → `connection_failed`
  2. job 0건 → `no_utterances` (빈 결과를 확정처럼 주는 경로 차단, SVG T2)
  3. non-terminal job 존재 → `analyzing` — 교정 목록을 **응답에 포함하지 않는다** (잠정 노출 금지, §5.5)
  4. `failed` job 존재 → `partial_failure` — **성공분(`done`) 교정은 포함**한다
  5. 그 외(1건 이상 전부 `done`) → `final` (교정 목록 포함)

  **R2↔U2 상태 매핑 (단일 계약)**:

  | API status | U2 화면 상태 | 교정 카드 |
  |---|---|---|
  | `analyzing` | 분석 중 | 없음 |
  | `final` | 확정 | 최대 2개 |
  | `partial_failure` | 부분 실패 문구 **+ 성공분 교정 병존** | 최대 2개 |
  | `connection_failed` | 연결 실패 | 없음 |
  | `no_utterances` | 분석 대상 없음 | 없음 |
- **R3. 부분 실패 표시** (≙AC13): `failed` job이 있는 세션의 결과에 부분 실패 플래그가 포함된다. 화면 문구는 U2가 담당.

### G — Audio Gateway (Nova 포트 + 스텁)

- **G1. 세션 수명주기**: WebSocket 연결 수립 시 고정 사용자에 바인딩된 `learning_sessions` 행이 생기고, 종료 시 `ended_at`과 `status='completed'`가 한 번에 기록된다. **어댑터 close가 세션 종료 기록보다 먼저 호출된다** (§7 Dependency 정리 순서).
- **G2. 연결 실패 가시화** (≙AC10 전반부): 스텁 어댑터가 무응답을 시뮬레이션하면 Gateway 자체 연결 타임아웃(**10초 — 설계 발명값, 근거 문서 없음**)이 발동해 세션이 `status='failed'`로 닫히고 클라이언트에 실패 이벤트가 전달된다. 무한 대기가 없다. 화면 표시(AC10 후반부)는 **U2의 `연결 실패` 상태**가 담당한다.
- **G3. Nova 포트 계약**: 음성 어댑터 인터페이스가 정의된다 — 입력: 오디오 프레임 / 출력: **부분 전사문 이벤트**, 확정 전사문 이벤트, 오디오 응답 프레임. 스텁 구현은: 확정 전사문을 `(session_id, sequence_no)` 단조 증가로 발행하고, 확정 직전에 부분 전사문 1~2개를 발행하며(U1 검증용), 고정 오디오 프레임(사전 생성 톤/TTS)을 응답으로 발행하고, 수신한 입력 프레임 수를 카운트한다. 검증: **Gateway 모듈이 스텁 구현을 import하지 않고 주입만 받는다** (import 그래프 확인 — 가짜↔가짜 교체 테스트는 동어반복이라 쓰지 않는다).
- **G4. 시나리오 완주** (≙AC12 스텁판): 공통 픽스처로 고정 질문 3개 플로우를 완주하면 사용자 발화 3건이 각각 `utterances`에 저장되고 각각 `analyze_utterance`가 등록된다.

### U — 프론트엔드 (Next.js)

- **U1. 세션 화면**: 학습 시작/종료, 질문 3개 진행, 전사문 표시 — 부분=회색·확정=일반 (`docs/backup/superseded/voice-architecture.md:41` — 2026-08-27 폐기 이관, 줄 번호 유효). 부분 전사문의 발생원은 G3 스텁이다.
- **U2. 결과 화면 — 5상태** (R2 매핑 표가 단일 계약): `분석 중` / `확정`(교정 최대 2개: 원문 → 교정문 → 한 줄 이유) / `부분 실패`("일부 발화는 분석하지 못했다" + 재시도 불가 안내 **+ 성공분 교정 병존**, §5.5) / `연결 실패`(G2 연동, ≙AC10 후반부) / `분석 대상 없음`.
- **U-검증**: 프론트는 자동 E2E를 만들지 않는다(MVP). E2E-S 스모크로 판정한다.

### E2E-S — 스텁 종단 스모크 (수동 1회, 증거 첨부)

podman PG + 백엔드 + 프론트를 실제 기동하고 브라우저에서 다음을 **순서대로** 수행·기록한다:

1. 학습 시작 → **마이크 권한 허용 → 오디오 프레임 전송 확인(스텁 카운트) → 스텁 오디오 응답 재생 확인** (출력 경로 관통)
2. 공통 픽스처로 3문항 완주 — 부분 전사문(회색)→확정 전사문(일반) 전환 확인 (U1). ※ 스텁 모드라 실제 발화 내용과 무관하게 전사문은 픽스처가 결정한다 — 버그 아님
3. **`WORKER_ENABLED=false`로 백엔드를 기동**한 상태에서 스텝 1~2 수행 후 세션 종료 → 결과 화면 진입 → `분석 중` 확인 (결정적 절차 — 경합 회피) → 플래그를 켜고 재기동 (job은 PG에 남아 이어짐, §5.4)
4. 실제 Claude 분석 완료 후 `확정` 상태에서 **교정 카드 정확히 1개**(`article` 패턴, `the` 삽입 — 픽스처상 패턴이 1개뿐) 확인
5. **job 1건을 강제 실패**(DB에서 `failed`로 직접 갱신) → 결과 화면에서 `부분 실패` 문구 **와 성공분 교정 카드가 병존**함을 확인 (U2·R3, R2 매핑 표)
6. 스텁을 무응답 모드로 새 세션 시작 → 10초 내 `연결 실패` 화면 확인 (G2·U2)

## Phase 1에서 쓰지 않는 것 (명시)

`mastery_score`·`self_difficulty`·`review_tasks`·`impact_score`는 **컬럼/테이블만 존재하고 어떤 코드도 읽거나 갱신하지 않는다** (복습 스케줄링은 3단계). `pronunciation_intonation` 카테고리는 CHECK에만 있고 산출되지 않는다(§6.1 D1 참고). ⚠️ **이 문단은 Phase 1 범위에 대한 진술이고 당시로서 옳았다. 2026-08-27에 범위가 넓어졌다** — `review_tasks`·복습 스케줄은 `2026-08-25-learning-coach-agent-design.md`(정본 승격), 발음 산출은 `2026-08-27-pronunciation-echo-design.md`, `impact_score`는 **영구 제외**로 결정됐다(학습 코치 설계서 §11 미결 3 종결).

## 이월 — 이 개발의 완료 기준이 아님

### Phase 2 (IAM/SigV4 후)

| 이월 항목 | 근거 |
|---|---|
| AC1 실음성 왕복, AC2 barge-in(1초), AC12 실음성 완주 | Nova 양방향 스트림 필요 |
| 세션 롤오버(§7 Boundary) + 포트 수명 이벤트·barge-in 제어 연산 확장 | Nova 스트림 수명 이벤트 필요 (§범위 재정의의 포트 확장 원칙) |
| §4.2 무응답형 자격증명 오류의 실계측 | G2가 스텁으로 메커니즘은 검증, 실제 SDK 거동은 스파이크 재실행 |
| ~~**Claude 클라이언트 자격증명 SigV4 전환**~~ | **해소 (2026-08-26).** `prepare_bedrock_credentials()`가 SigV4 우선·bearer 폴백으로 동작하고, SigV4가 채워진 지금은 bearer를 프로세스 환경에서 제거해 단일 경로를 강제한다(셸 export 상속 차단). 실측 증거: `sts get-caller-identity` = `user/ohmyenglish-local`, Claude invoke via SigV4 HTTP 200, Nova 양방향 스파이크 PASS. F5의 "전환 = 설정 교체"대로 워커·클라이언트 코드는 무변경. 폴백을 남긴 것은 캡틴 지시다(발급 전 동작 경로 보호) — 이제는 SigV4가 항상 이긴다 |
| ~~AC1·AC2·AC12 실음성 / 세션 롤오버 / §4.2 실계측~~ 의 **선행 조건** | **해소 (2026-08-26)** — Nova 양방향 스트림 착수 조건(설계서 §10-1 관문) 충족. 이 항목들 자체는 여전히 Phase 2 작업이다 |

### 다음 슬라이스 (IAM과 무관)

| 이월 항목 | 근거 |
|---|---|
| AC11 세션 총평(`summarize_session`) | 설계서 §5.1에서 이미 다음 슬라이스로 연기 |

### 다중 사용자 전환 (별도 Phase — 캡틴 결정 2026-08-25)

현재는 **개인 학습 용도이고 다중 사용자를 고려하지 않는다.** 아래는 다중 사용자로 전환할 때의 과제이며 **Phase 1·2의 완료 기준이 아니다.** 큐 선택 자체(PostgreSQL 큐 유지)는 사용자 수와 무관하게 유효하다 — 근거는 설계서 §5.0.

**이미 안전한 것** — claim의 `FOR UPDATE SKIP LOCKED` + claim당 고유 lease token + 모든 쓰기의 `locked_by=:token` 조건(설계서 §5.4) 덕에 **워커 동시성을 1에서 올리는 것 자체는 코드 변경 없이 안전하다.** 설계 시점에 의도한 방어다.

| 이월 항목 | 근거 |
|---|---|
| 공정성(fairness) — per-user 라운드로빈 또는 사용자별 동시 실행 상한 | claim이 `available_at` 단일 FIFO라 한 사용자의 발화 폭주가 다른 사용자를 기아 상태로 만든다 |
| 폴링 → 푸시 (`LISTEN/NOTIFY` 또는 폴링 백오프) | 워커 N개 × `poll_interval=1.0s`가 DB 부하가 된다. 단일 워커에서는 무해하다 |
| `analysis_jobs` 보존 정책 — terminal job 아카이빙·파티셔닝, vacuum 관찰 | 현재 정리 코드가 없다. 개인 사용량에서는 무해하나 고빈도 UPDATE 테이블이다 |
| 워커 프로세스를 API에서 분리 | 현재 FastAPI 기동 시 `asyncio` 루프로 뜬다 — API 재시작이 분석을 멈춘다(작업은 PG에 남아 이어지므로 데이터 손실은 없다) |
| 큐 관측성 — 큐 깊이·실패율·lease 회수 횟수 | 외부 큐의 콘솔·DLQ 대응물이 없어 지금은 직접 쿼리한다 |
| 사용자별 인증 + WebSocket 엔드포인트 origin 검증 | 현재 인증 없음·고정 사용자 1명이고 origin 미검증을 수용 중(localhost 단일 사용자) |

**외부 큐(SQS 등) 재검토 시점**: 위 항목을 PostgreSQL로 해결하는 비용이 outbox + 외부 큐 비용을 넘을 때다 — 처리량 상한이 아니라 이 비용 비교가 판정 기준이다. 판단 근거는 설계서 §5.0.

## 완료 선언 규칙

Phase 1 완료 = 아래 6개 전부. 어느 항목이든 미충족이면 완료라 부르지 않는다.

1. **F·W·R·G·U 전 항목 pass** (증거: 테스트·명령 출력)
2. **W-live 1회** (실행 출력 첨부)
3. **E2E-S 1회** (6스텝 실행 기록 첨부)
4. **각 W/R/G AC 테스트의 red→green 증거** — 구현 전 실패 확인 (SVG T0, A트랙 TDD)
5. **`/simplify` 실행 후 7단계 재검증** (§0 9단계)
6. **code-reviewer Approve** (SVG DEVELOPMENT gate — Approve 전 Done 전환 금지)
