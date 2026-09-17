---
id: TASK-159
title: '조사: 현재 앱 구조에서 영상 학습 메뉴가 붙을 자리 확정'
status: Done
assignee: []
created_date: '2026-09-17 16:54'
updated_date: '2026-09-17 17:07'
labels: []
dependencies: []
ordinal: 220000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
별도 메뉴로 분리하라는 지시를 이행하려면 기존 라우팅·메뉴·세션 생성 경로·쉐도잉 자산의 실제 구조를 먼저 읽어야 한다. 기존 패턴을 따르는 것이 목표다.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 프론트엔드 라우팅과 메뉴 정의 파일을 찾아 경로를 적었다
- [x] #2 기존 쉐도잉 기능의 데이터 흐름(표·API·화면)을 적었다
- [x] #3 추가 학습 진입점이 모드를 넘기는 방식을 확인했다
- [x] #4 영상 학습이 재사용할 자산과 새로 만들 자산을 갈랐다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## 내가 직접 조회한 것 (2026-09-18) — 코드 구조 조사와 별도로 얻은 사실

### 1. ⛔ PRD 가 이미 이 기능을 요구함 — 범위 확장이 아님

`docs/PRD.md` §10 `Shadowing & Content`:

- `30~90초의 짧은 오디오·영상 클립을 문장 단위로 제공한다.`
- `듣기, 따라 말하기, 녹음 비교, 본인 상황으로 바꿔 말하기 순서로 진행한다.`
- ⛔ `외부 영상은 메타데이터·링크만 보관하고 사용자가 선택한 콘텐츠만 과제로 사용한다.`

⇒ §5 의 비범위는 「**무제한** YouTube **자동** 수집 · 저작물 **전체** 저장」임. 사용자가 링크를 주고
우리가 메타데이터·링크만 보관하는 형태는 **§10 이 글자로 허용한 범위**임.
⚠️ 그래서 이 작업은 PRD 경계를 옮기지 않음 — 옮긴다고 적었던 초기 판정을 정정함.
⛔ **다만 「추천」은 갈라 봄**: 자동 수집·추천은 §5 가 막고, 사용자가 고른 것만 과제로 쓰는 것은
§10 이 허용함. MVP 는 후자만 함.

### 2. `shadowing_items` 표가 이미 「영상 구간 + 문장」을 담음 (직접 조회)

| 컬럼 | 형 | null |
|---|---|---|
| `id` | uuid (`gen_random_uuid()`) | NO |
| `source_title` | text | NO |
| `source_url` | text | YES |
| `transcript` | text | NO |
| `clip_start_sec` | numeric | NO |
| `clip_end_sec` | numeric | NO |
| `level` | text | NO |
| `created_at` | timestamptz (`now()`) | NO |
| `audio_filename` | text | YES |

제약 9개 (직접 조회):

| 제약 | 내용 |
|---|---|
| `shadowing_items_level_check` | `level in (A1,A2,B1,B2,C1,C2)` |
| `shadowing_items_span_within_limit` | `clip_end_sec - clip_start_sec <= 90` |
| `shadowing_items_span_ordered` | `clip_end_sec > clip_start_sec` |
| `shadowing_items_clip_start_sec_check` | `clip_start_sec >= 0` |
| `shadowing_items_audio_only_for_synthetic` | `audio_filename is null or source_url is null` |
| `shadowing_items_audio_filename_matches_id` | `audio_filename is null or audio_filename = id::text \|\| '.wav'` |
| `shadowing_items_source_title_check` | `length(btrim(source_title)) > 0` |
| `shadowing_items_transcript_check` | `length(btrim(transcript)) > 0` |
| `shadowing_items_pkey` | `PRIMARY KEY (id)` |

⛔ **`audio_only_for_synthetic` 가 이 설계의 방향을 이미 강제함** — `source_url` 이 있는 항목에는
오디오 파일을 붙일 수 없음. YouTube 에서 담은 문장은 `source_url` 을 가지므로 **오디오를 저장할
경로가 스키마 차원에서 막혀 있음.** 이것이 `TASK-158` 의 정책 조사(III.E.1 오디오 저장 금지)와
같은 방향임 — 우리가 새로 지킬 것이 아니라 **이미 지켜지고 있음.**

⚠️ `shadowing_items` 에 사용자 FK 가 없음 — 단일 사용자 전제를 그대로 따름.
⚠️ 구간 상한 90초가 이미 스키마에 있어 「긴 영상에서 한 조각만 담는다」가 강제됨.

### 3. `ohmyenglish` 스키마의 기본 표 21개 (직접 조회)

`analysis_jobs` · `daily_error_summary` · `error_occurrences` · `error_patterns` ·
`harness_pattern_baseline` · `harness_review_task_baseline` · `harness_runs` · `harness_sessions` ·
`learner_notes` · `learning_scenarios` · `learning_sessions` · `llm_calls` · `pattern_attempts` ·
`pronunciation_attempts` · `review_tasks` · `schema_migrations` · `session_plans` ·
`shadowing_items` · `users` · `utterances` · `weekly_reports`

⇒ 영상 메타데이터를 담을 표가 **없음** — 새로 만들 것은 그것 하나임.

### 4. 추가 학습 진입점의 구조 (설계서 `2026-09-12-additional-learning-entry-design.md`)

- **문은 하나**(대시보드 `추가 학습`)이고 **표면은 셋**임: 모드 없음 · `?mode=pronunciation` ·
  `?mode=shadowing`.
- 항목은 여섯임: `자유 대화` · `약점 패턴 집중` · `질문 답변 5개` · `발음 집중` · `쉐도잉` ·
  `업무 역할극`(비어 있는 칸).
- 표면이 갈리는 기준은 **조립되는 지시문이 실제로 달라지는가**임.

⇒ 영상 학습이 새 표면을 가질지 판단할 기준이 이것임. 영상 학습은 **세션 지시문이 아니라 화면과
자산 관리**가 다르므로, 세션 모드를 새로 만들기보다 **별도 화면**을 두고 담은 문장을 기존
`?mode=shadowing` 으로 흘려보내는 쪽이 이 구조와 맞음.

## 코드 구조 조사 결과 — 붙이는 자리 (위임 조사 · 2026-09-18)

### 새 갈래를 「세션 모드」로 붙일 때 손대는 자리 아홉

1. `app/frontend/lib/config.ts` — `SessionEntry.mode` 리터럴 유니온에 값을 더함
2. `app/frontend/lib/api.ts` — 조회 함수와 응답 인터페이스를 더함
   (⚠️ 관례: **전용 화면은 실패를 `null` 로**, 곁가지는 조용히 빈 값으로)
3. `app/backend/app/models/session.py` — `SessionMode` 리터럴과 상수
4. `db/migrations/027_*.sql` — `learning_sessions_mode_check` 를 018 처럼 **`drop`+`add`** 로 대체
5. `app/backend/app/services/session_modes.py` — `SessionModePolicy` 인스턴스 한 줄과 `_POLICIES` 튜플
   (그 표의 존재 이유가 「모드를 하나 더 붙이는 비용을 한 줄로 만드는 것」임)
6. `app/backend/app/api/<자원>.py` 신설 + `app/backend/app/api/main.py` 의 `create_app()` 에
   `include_router` 한 줄
7. `app/backend/app/services/<도메인>.py` — `conn` 을 첫 인자로 받는 raw SQL 함수들
8. 테스트: `tests/unit/test_<모듈>.py` · `tests/integration/test_ws.py` 의
   `query_string=b"mode=..."` 패턴
9. 값역 대조는 `tests/unit/test_schema.py` 에 `pg_get_constraintdef` 단정을 더함

### ⛔ 갈림길 하나 — 조사가 지목한 더 싼 경로

**「세션 모드」가 아니라 「별도 화면 갈래」로 붙이면 3·4·5 가 필요 없음.**
쉐도잉이 모드로 붙은 이유는 「Nova 대화 세션 안에서 진행된다」였음(`?mode=shadowing` →
`SessionRunner`). 영상 학습이 대화 세션을 쓰지 않으면 `/api/shadowing` + `ShadowingPanel` 계보
(**자원 라우터 + 화면**)만 베끼는 것이 싸다는 판정임.

⇒ 판단 기준의 선례는 `docs/design/2026-09-12-additional-learning-entry-design.md` §2 임:
**「표면이 갈리는 기준은 지시문이 실제로 달라지는가」.** 영상 학습은 **지시문이 아니라 화면과 자산
관리**가 다르므로 이 기준에 따르면 **세션 모드를 새로 만들지 않음.**

### ⛔ 재사용 금지 하나

**「업무 역할극」 칸을 영상 학습으로 재사용하지 않음.** 그 칸은 무대 선택 화면의 부재를 가리키는
표식이고(`entry: null` + `note`), 소유는 `TASK-102`·`TASK-5` 임. `page.tsx` 주석이 「지우면 다음
사람이 원래 다섯이었다로 읽는다」로 못박았음.
⇒ 새 갈래는 **항목 일곱째** 또는 **별도 섹션**으로 붙음.

### 자산 저장 자리 — 뿌리 둘이 이미 갈려 있음

| 뿌리 | 설정 키 | 성질 |
|---|---|---|
| `assets/clips/` | `shadowing_clip_audio_root` | 제품 자산 · git 추적 |
| `assets/audio/` | `shadowing_audio_root` | 개인 녹음 · 워커의 `sweep_recordings` 가 순회해 지움 |

⛔ **같은 뿌리를 재사용하면 제품 자산이 스윕됨** — 근거가 `config.py` 의 해당 필드 주석에 있음.
⇒ 영상 학습은 **미디어를 저장하지 않으므로 이 갈림에 걸리지 않음**(정책상 저장 금지 · `TASK-158`).
이것이 「저장하지 않는다」의 부수 이득임.

### 백그라운드 처리 관례

새 큐를 만들지 않고 `analysis_jobs` 에 `job_type` 을 하나 더 여는 것이 관례임 —
`db/migrations/018` 의 `analysis_jobs_job_type_check` 값역 확장 + `services/jobs.py` 의
`JOB_TYPE_*` 상수와 `_ENQUEUE_PLAN_SQL` 재사용 + `workers/analysis_worker.py` 의 `job.job_type`
분기 한 줄.
⇒ MVP 에 백그라운드 작업이 필요한지는 설계서가 판단함. oEmbed 호출은 동기로 충분함(1회·짧음).

### 마이그레이션 실측 (내가 직접 조회)

`db/migrations/` 최대는 `026_dedicated_schema.sql` 이고 `schema_migrations` 의 마지막 적용도
`026_dedicated_schema.sql`(2026-09-17 00:37 UTC)임. ⇒ **새 파일 번호는 `027` 임.**

`shadowing_items` 현재 행은 **1건**이고 합성 클립임(`source_url` 없음 ·
`audio_filename` = `00000000-0000-0000-0000-000000000201.wav` · `A2` · 0.00~17.36초).
⇒ **`source_url` 이 있는 행은 아직 0건임** — 영상에서 담은 문장이 그 첫 사례가 됨.

## 구조 조사 2차 — 항목별 사실 (위임 조사 · 2026-09-18)

### 1. 프론트엔드

- **Next.js 16.3.2 App Router** · React 19.2.8 · TypeScript 5. `src/` 없음. 뿌리는 `app/frontend/app/`.
- ⛔ **라우터 정의 파일이 없음**(파일시스템 라우팅) · **전역 네비게이션 바가 없음**
  (`layout.tsx` 의 `RootLayout` 은 `<body>{children}</body>` 뿐).
- 화면 넷: `/`(`app/page.tsx` · `SessionPage` — 대시보드와 세션 겸용) ·
  `/results/[sessionId]` · `/history` · `/history/weekly`.
- 라우트가 아닌 패널이 `app/` 에 나란히 있음: `app/ShadowingPanel.tsx` · `app/WeeklyReportPanel.tsx`.
  ⇒ **컴포넌트 디렉터리를 새로 만들지 않고 이 관례를 따름.**
- 화면 간 이동은 각 페이지가 `next/link` 로 직접 이음(`HOME_LINK_LABEL`·`HISTORY_LINK_LABEL`·
  `WEEKLY_LINK_LABEL` 상수).
- ⛔ **상태 관리 라이브러리가 없음**(Redux·Zustand·Context 0곳). `useState`·`useRef` 만 씀.
  서버 조회는 `lib/api.ts` 의 `fetch` 직접 호출(`cache: "no-store"`).

### 2. 추가 학습 진입점

- 항목 여섯의 정의: `app/page.tsx` 의 모듈 상수 **`ADDITIONAL_LEARNING`**
  (`ReadonlyArray<{label, entry, target?, note?}>`). 마지막 원소가 `업무 역할극` 이고
  `entry: null` · `note: "무대를 고르는 화면이 아직 없어요"` · 렌더가 `disabled={item.entry === null}`.
- 경로: 버튼 → `startSession(item.entry)` → `SessionSocket`(`lib/ws.ts`) →
  `sessionSocketUrl(entry)`(`lib/config.ts`)가 `mode`·`source` 를 쿼리로 실음 →
  `api/ws.py` 의 `session_socket` 이 `query_params.get("mode")` → `policy_for(...)`.
- 모드 열거형: 프론트 `lib/config.ts` 의 `SessionEntry.mode`
  (`"pronunciation"|"shadowing"|"scenario_intake"`) · 백엔드 `models/session.py` 의
  `SessionMode`·`SESSION_MODES`·`SPEAKING_MODE`·`SHADOWING_MODE`·`PRONUNCIATION_MODE`·
  `SCENARIO_INTAKE_MODE`.
- DB 값역 정본: `db/migrations/018_*.sql` 의 `learning_sessions_mode_check` ·
  대조 단정은 `tests/unit/test_schema.py`.
- 음성 명령: 프론트 `lib/ws.ts` 의 `AdditionalTarget` · 백엔드 `models/voice_command.py` 의
  `AdditionalTarget`·`ADDITIONAL_TARGETS`·`parse_control_payload`.

### 3. 기존 쉐도잉 흐름

- 라우터 `api/shadowing.py` — `APIRouter(prefix="/api/shadowing")` ·
  `get_clip_audio`(`GET /clips/{item_id}/audio`). `StaticFiles` 마운트는 리포에 0곳.
- 서비스 `services/clip_audio.py`(`clip_audio_path`·`load_clip_audio`) ·
  `services/sessions.py`(`start_shadowing_session`·`_ATTACH_SHADOWING_CLIP_SQL`) ·
  `services/recordings.py`(`ShadowingClip`·`ShadowingTurns`·`load_session_clip`).
- ⛔ **클립 선택이 자동임** — `_ATTACH_SHADOWING_CLIP_SQL` 이 `coalesce(수준 일치 첫 행, 전체 첫 행)`
  로 고름. **사용자가 클립을 고를 경로가 없음.** 이것이 영상 학습에서 반드시 열어야 하는 자리임.
- 프론트 `app/ShadowingPanel.tsx` — `new Audio()` + `playbackRate` + `ended` 반복.
  진입은 `page.tsx` 의 `shadowing` 상태(← `session_started` 의 `event.shadowing`).
- 클립 자산은 `assets/clips/00000000-...-201.wav` **1개뿐**(560KB · WAV PCM 16bit mono 16kHz ·
  17.36초 · TTS 합성 · git 추적). 시드는 `scripts/migrate.py` 의 `SEED_SHADOWING_ITEMS`.

### 4. 백엔드

- `create_app()`·`lifespan()` 은 `api/main.py`(모듈 끝에 `app = create_app()`).
  `FRONTEND_ORIGIN="http://localhost:3000"`.
- 등록된 라우터 넷: `results_router` · `daily_router` · `shadowing_router` · `ws_router` (+`/health`).
- 서비스 관례(정본은 `services/__init__.py` docstring): **raw SQL** · `conn` 을 **첫 인자**로 ·
  트랜잭션 경계는 호출자 소유 · 공용 헬퍼 금지 · 값역과 DTO 는 `models/` 로 분리.
- `Settings` 는 `app/config.py`(`get_settings()` = `@lru_cache`). 값역은 `Field(ge=,le=)` 로
  기동 시점에 거부.
- `.env.example` 은 리포 루트 → `app/backend/.env` 로 복사. 프론트는
  `app/frontend/.env.example` → `.env.local`(`NEXT_PUBLIC_API_BASE=http://localhost:8002`).
- 워커는 별 프로세스가 아니라 **API lifespan 에 붙음**(`workers/analysis_worker.py` 의 `run_worker`).
  큐는 `analysis_jobs` 표 · `services/jobs.py`(`MAX_ATTEMPTS=5` · `JOB_TYPE_*`).

### 5. 마이그레이션

- `db/migrations/NNN_snake_case.sql` 평면 배치 · Alembic 없음 · **002·008 은 영구 결번**.
- ⛔ **번호를 미리 예약하지 않고 파일을 쓰는 턴에 최대값을 다시 확인해 받음**(결정 27).
- 파일 머리에 `설계:`·`캡틴 결정:`·`소유 태스크:`·`번호:`·`되돌리기:` 주석 블록을 붙임.
- 실행은 `app/backend/.venv/bin/python scripts/migrate.py` — 단독 스크립트이고 `seed()` 를 함께 가짐.
- ⛔ **우리 SQL 은 전부 비수식** — 전수 882건 중 `public.` 한정 0건임. 새 SQL 에도 붙이지 않음.

### 6. 테스트

- `tests/` 에 `conftest.py` · `unit/` · `integration/` · `e2e/`(비어 있음) · `harness/` · `agent/`.
- 실행은 `cd app/backend && ./.venv/bin/pytest -q` · 설정은 `pyproject.toml` 의
  `[tool.pytest.ini_options]`(`asyncio_mode="auto"` · `testpaths=["../../tests"]`).
- 타입 검사 스코프가 루트 `ty.toml` 의 `include=["app/backend/app","tests"]` 임 ⇒
  **새 테스트 파일도 `ty check` 대상임.**
- 테스트 함수 이름은 **영어 문장형**(예: `test_ws_opens_a_shadowing_session_and_hands_over_the_clip`).
- **DB 픽스처**: `test_database`(session scope) · **`db_conn`**(기본 · 테스트마다 롤백 트랜잭션) ·
  **`db_pool`**(스스로 커밋하는 코드용 · 정리 책임이 테스트에 있음) · `committed_session` ·
  `api_client`(httpx AsyncClient) · `fake_claude`.
- 시드 팩토리에 **`seed_shadowing_clips`** 가 이미 있음 ⇒ 영상 항목 테스트가 그것을 베낌.
- ⛔ **프론트 테스트 러너가 없음** — 게이트는 `npx tsc --noEmit` + `npx eslint .` 이고 화면 검증은
  `tests/harness/` 가 대신함. ⇒ **프론트에 논리를 두면 단위 테스트로 덮을 수 없음.**

### 7. 외부 API 관례

- 음성은 어댑터 패턴임 — 포트 `audio_gateway/port.py` 의 `VoiceAdapter(Protocol)` · 유일한 분기점
  `audio_gateway/factory.py` 의 `create_voice_adapter()`(알 수 없는 값은 `ValueError`).
- stub 설정 키는 `Settings.voice_adapter`(env `VOICE_ADAPTER`) 이고 **기본값이 `"stub"`** 임.
- ⛔ **런타임 HTTP 클라이언트가 없음** — 런타임 의존성은 `fastapi`·`uvicorn`·`asyncpg`·`pydantic`·
  `pydantic-settings`·`boto3`·`aws-sdk-bedrock-runtime` 뿐임. `httpx` 는 `[dependency-groups] dev`
  에만 있고 유일한 예외가 `claude_client.py` 의 `_http_post` 임.
  ⇒ **백엔드에서 REST API 를 부르려면 런타임 의존성 추가가 새 결정임.**
- 타임아웃·재시도 정본은 `config.py` 의 `bedrock_boto_config()` 하나임.
- 실패 관례: **외부·조회 실패를 세션 실패로 번역하지 않음** — `api/ws.py` 의 `_load_*_or_none` 들이
  `logger.exception` 뒤 그대로 진행함.

## AC 4 — 재사용할 자산과 새로 만들 자산

### 그대로 재사용 (코드를 새로 쓰지 않음)

| 자산 | 자리 | 왜 그대로 쓰는가 |
|---|---|---|
| `shadowing_items` 표 | `db/migrations/011`·`022` | `source_url`·`transcript`·`clip_start_sec`·`clip_end_sec`·`level` 이 이미 「영상 구간 + 문장」임 |
| 쉐도잉 세션 | `start_shadowing_session` · `?mode=shadowing` | 연습·녹음·발음 판정 경로가 이미 돎 |
| 발음 판정·오류 패턴 | `pronunciation_attempts` · `error_patterns` | 영상에서 담은 문장도 같은 경로를 탐 |
| 복습 큐 | `review_tasks` | 새 복습 계산을 만들지 않음 |
| `ShadowingPanel.tsx` | `app/ShadowingPanel.tsx` | 문장·재생을 이미 렌더함 |
| `assets/clips/` 스윕 회피 | `shadowing_clip_audio_root` | 영상은 **미디어를 저장하지 않아** 이 갈림에 걸리지 않음 |

### 새로 만드는 것 — 넷뿐

1. **영상 표 하나** (`027` 마이그레이션) — `youtube_videos`. `shadowing_items` 는 문장이고 영상은
   그 문장들의 출처이므로 1:N 임. 기존 21개 표에 영상 메타데이터를 담을 자리가 없음.
2. **자원 라우터 하나** — `api/videos.py`(`APIRouter(prefix="/api/videos")`). `api/shadowing.py` 의
   계보를 그대로 베낌.
3. **서비스 하나** — `services/videos.py`. `conn` 을 첫 인자로 받는 raw SQL 함수들.
4. **화면 하나** — `app/videos/page.tsx`(라우트). 목록·재생·문장 담기를 한 화면에 둠.

### ⛔ 새로 만들지 않는 것 셋 — 그 근거

| 안 만드는 것 | 근거 |
|---|---|
| **새 세션 모드** | 영상 학습은 **지시문이 달라지지 않음**. 판정 기준의 선례가 `2026-09-12-additional-learning-entry-design.md` §2 임. ⇒ `models/session.py`·`session_modes.py`·`018` 값역을 건드리지 않음 |
| **백엔드 HTTP 클라이언트 의존성** | oEmbed 가 **CORS 를 허용함**(실측: `access-control-allow-origin` 이 요청 Origin 을 반영) ⇒ 브라우저가 직접 부름. `pyproject.toml` 의 런타임 의존성을 건드리지 않음 |
| **새 백그라운드 job 종류** | oEmbed 는 1회·짧은 호출이라 동기로 충분함. `analysis_jobs` 값역을 건드리지 않음 |

### ⛔ 배치 결정 하나와 그 대가

**URL 파싱·검증은 백엔드에 두고, oEmbed 호출은 프론트에 둠.**

- 근거: 프론트에 **테스트 러너가 없음**(6항) ⇒ 논리를 프론트에 두면 단위 테스트로 덮을 수 없음.
  videoId 추출은 형태 넷(`watch?v=`·`youtu.be/`·`shorts/`·`embed/`)을 다루는 **논리**이므로 서버가 가짐.
- oEmbed 호출은 **논리가 아니라 전송**이므로 프론트가 가짐. 그러면 백엔드 런타임 의존성이 늘지 않고
  백엔드 테스트가 밖으로 나가지 않음.
- ⚠️ **대가**: 백엔드가 프론트가 준 제목·채널을 그대로 믿음. 단일 사용자 앱이고 그 값이 표시용
  라벨이라 받아들임. 다만 **길이 상한과 공백 거부는 서버가 검사함**(값역을 서버가 소유하는 관례).

### ⛔ 재사용 금지 하나 (다시 못박음)

`업무 역할극` 칸을 쓰지 않음. 새 항목은 **`ADDITIONAL_LEARNING` 의 일곱째** 로 붙이거나 별도 링크로 둠.
그 칸의 소유는 `TASK-102`·`TASK-5` 임.
<!-- SECTION:NOTES:END -->
