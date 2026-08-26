# OhMyEnglish Handoff

> 제품·구현 정본. 최종 갱신 2026-08-26 17:30 · 기준 커밋 **HEAD ≥ `5e3083f`** · **다음 할 일: 하네스 5차수**
> 이번 갱신은 캡틴 지시로 **테스트 세션(`claude_air_5-49`)이 수행**했다 — 원래 소유 관례상
> 다른 세션 파일이지만, 4차수 범위가 제품 요구(발음 교정·학습 반영)로 넓어져 정본을 함께 고쳤다.
> 하네스 절차는 `handoff/HANDOFF-test-harness.md`, 수정 세션 근거는 `handoff/HANDOFF-fix-session.md`.

## 현재 상태

| 항목 | 상태 |
|---|---|
| Phase 1 (첫 수직 슬라이스) | ✅ 개발 완료 — 태스크 12/12 |
| **Phase 2 Nova 2 Sonic 실연동** | ✅ **어댑터 구현 + 앱 경로 실음성 왕복(AC1) 실증** — 커밋 `37a2869`, 3차수 N5 |
| 테스트 | ✅ **241 passed** (skip/xfail 0, 기준선 206 → +35). **2026-08-26 17:2x 재실행 확인** |
| 품질 게이트 | ✅ **`app/backend`에서 실행할 때** `ruff check .` · `ruff format --check .`(25파일) · `ty check` 전부 clean. ⚠️ **"리포루트 양쪽 clean"은 틀렸다**(2026-08-26 재실측으로 정정) — 리포루트에 ruff 설정 파일이 **없어** 거기서 돌리면 ruff 기본 규칙이 적용돼 `check .` **56 errors** · `format --check .` **21 files**가 난다. 설정 SoT는 `app/backend/pyproject.toml`이므로 **게이트는 `app/backend` cwd로 정의된다**. `ty check`만 양쪽 clean |
| 하네스 테스트↔수정 루프 | **4/10 차수 사용.** 미해결 앱 결함 **0건**. 4차수 P·M 완료 → 5차수는 N·B·회귀 |
| Phase 1 완료 선언 | ⏸ **캡틴 게이트** — 아래 |
| 3단계 학습 코치 Agent | 📄 설계서 초안(2026-08-25 18:49) — **검토 전** |
| **발음 교정 루틴** | ❌ **없다 — 4차수 P계층에서 앱 경로로 확정.** 전사문 경로로는 원리적으로 불가. 개입 지점은 `nova.py:77` 프롬프트 한 곳. **캡틴 결정: 수정 보류, 기록만** |
| **오류 → 이후 학습 반영** | ⚠️ **저장은 되고 활용은 안 된다 — 4차수 M계층에서 확정.** 패턴 8개를 쌓아도 agent 응답이 3차수 N5 때와 글자까지 같았다. ⚠️ N5 시점 패턴 수를 "1개"라 적었던 것은 **오류** — Q1(E6 주입)이 N5보다 먼저 돌아 최소 2개였다(정확한 값 미기록). 대조 방향은 유지되나 **좌변 수치는 못 쓴다.** 결론의 근거는 코드 구조다 |

브랜치: `design/first-vertical-slice` (git remote 없음 — 로컬 전용).

### ⏸ 캡틴 게이트 3건

1. **E2E-S 스텝 1 "마이크 실프레임"** — 3차수 N5로 **거의 닫혔다**. 브라우저 캡처 경로가
   AudioWorklet raw PCM **806프레임 / 806KB**를 실제로 보내고 Nova ASR이 발화 내용을 맞췄다.
   남은 미검증분은 **물리 마이크 하드웨어 한 겹뿐**이다(N5는 `getUserMedia`를 합성 스트림으로
   대체). **캡틴 결정(2026-08-26): 캡틴이 직접 돌려야 하는 항목이라 이월한다** — 발음 픽스처
   보정(P계층 한계)도 같이 묶여 있으니 그 세션 한 번으로 둘을 함께 닫는다.
2. ~~**발음 교정의 범위**~~ → ✅ **결정됨(2026-08-26): 지금은 수정하지 않고 기록만.**
   4차수에서 부재가 확정됐지만 고장난 것이 아니라 없는 기능이고(P5 clean), 문법 교정은 이미
   작동한다(O-3). 상위 순서는 복습·학습 코치다. 재개 시 `scenarios-P-pronunciation.md` §5에서
   층(①결함/②프롬프트/③패턴기억)을 고른다.
3. **M계층 반영 단위** — 오류가 대화에 닿는 경로가 지금 0개다(`sessions.py:29`가 고정 시나리오,
   `nova.py:77`이 정적 지시문). 두 갈래가 있고 배타적이지 않다:
   - **A 시나리오 선택** — 약점 패턴에 맞는 질문 세트를 `learning_scenarios`에서 고른다.
     `limit 1`을 "추천 한 건"으로 바꾸는 작은 변경이지만, 반영이 시나리오 문구 수준으로 거칠다.
   - **B 지시문 주입** — "관사를 5번 틀렸다, 그 문형을 유도해라"를 Nova 지시문에 넣는다.
     `port.start()`에 인자 추가가 필요하나(AC 허용 확장) **agent 발화가 실제로 달라지는 유일한
     길**이고 M2·M3 판정이 여기에 달려 있다.
   - A가 "무슨 주제로", B가 "어떻게 굴릴지"를 담당해 **함께 쓰는 것이 자연스럽다.**
   나머지 미결은 `scenarios-E-agent-learning.md` M계층 §캡틴 결정(반영 시점·판정 기준).

---

## 4차수 범위 — 캡틴 지시(2026-08-26)로 확장됨

원래 4차수는 "미실행 Nova 시나리오 + 회귀"였다. 캡틴이 4건을 추가해 아래가 됐다.
절차·명령은 `handoff/HANDOFF-test-harness.md` §3·§5가 정본이다.

| 묶음 | 내용 | 정본 문서 |
|:--:|---|---|
| **P** | ✅ **완료(4차수)** — 발음 교정 루틴 검증. P1~P7 실행, P5(최우선 위험) **clean**. 이월은 P8 + **`p2` 쌍**(4차수는 `p1` 쌍만 돌렸다) | `tests/harness/scenarios-P-pronunciation.md` |
| **M** | ✅ **완료(4차수)** — M0·M1로 반영 부재를 통제된 대조로 고정. 통합테스트 회귀 기준선 | `tests/harness/scenarios-E-agent-learning.md` M계층 |
| ① | ⏭ **5차수** — 미실행 Nova 시나리오 N6(barge-in)·N7(3턴)·N8(실발화 병합)·N11(권한거부)·N12(포맷불일치)·N13(endpointing) | `tests/harness/scenarios-N-real-voice.md` §4 |
| ② | ⏭ **5차수** — 3차수가 대체 커버한 B1~B4 전량 재확인 + 라이트/다크 5상태 (**이 판단은 아직 미검증**) | `runs/2026-08-26-run-3.md` §회귀 |
| ③ | ⏭ **5차수** — 회귀 A1·A2·E4·E5·E6·D1·D2 + 프론트 `npx tsc --noEmit` | — |
| ④ | 4차수 신규 결함 **0건** → 수정 왕복 열지 않았다. O-1 단독으로는 열지 않는다 | `runs/2026-08-26-run-4.md` |

**일부러 빼는 것**: N9(세션 롤오버 — Nova 스트림 상한이 `nova.py:61` `STREAM_LIMIT_SECONDS = 8*60`
이라 8분 이상 실음성 유지가 필요, 시간·비용), N10(무응답형 자격증명 실패 — `.env` 편집 금지 제약).

### 기록 규약 (캡틴 요구: "테스트 내용과 결과를 계속 기록, 향후 통합테스트에 반영")

| 무엇 | 어디 |
|---|---|
| 차수별 진행·상한 | `tests/harness/runs/ROUNDS.md` (원장) |
| 차수별 결과 | `tests/harness/runs/2026-08-26-run-N.md` + `runs/2026-08-26-run-N/` 원자료 |
| 시나리오 정본(계층별) | `scenarios-N-real-voice.md` · `scenarios-E-agent-learning.md` · `scenarios-P-pronunciation.md` |
| 절차 정본 | `docs/ops/2026-08-26-test-harness.html` (12절) |

---

## 발음 교정 — 4차수 개시 전 확보한 실측 (핵심 발견)

`spike_nova_protocol.py`로 Nova에 직접 왕복. 같은 문장을 발음만 바꿔 넣었다.

| 픽스처 | 실제 발음 | Nova ASR 전사문 | agent 응답 |
|---|---|---|---|
| `p1a.wav` | 정확 | `i think i found three very useful videos.` | 정상 대화 |
| `p1m.wav` | `sink / pound / sree / bery / bideos` (음소 치환) | **`i think i found three very useful videos.`** — 원문 복원 | **p1a와 한 글자도 다르지 않다** |
| `p1k.wav` | 같은 문장, 한국어 음성(강한 억양) | **`아이싱크 아이파운드 쓰리 베리 유스풀 비디오즈`** — 한글 전사 | `Sorry, that part sounds a bit unclear. Could you please repeat…` |

**확정된 것**: ① 약한 발음 오류는 **전사문 경로에서 완전히 소실**된다(ASR 언어모델이 복원) →
전사문만 받는 분석 워커는 **원리적으로** 발음을 판정할 수 없고, `analysis.py:48`이 
`pronunciation_intonation`을 금지 카테고리로 둔 것은 실측으로도 옳다. ② speech-to-speech 모델인
Nova도 **발음을 지적하지 않았다** — `nova.py:77` `SYSTEM_PROMPT`에 발음 지시가 없다(rule 4는
"한 턴 1회 교정"이지만 발음 특화가 아니다). ③ 강한 억양은 **ASR 언어 판별을 뒤집는다** — 이
한글 전사문이 워커에 들어가면 어떻게 되는지가 미검증이고 **결함 후보**다(P5).

한계: `p1m`은 원어민이 다른 단어를 정확히 발음한 것, `p1k`는 한국어 TTS가 영문자를 읽은 것이다.
실제 캡틴 육성은 이 둘 사이에 있으므로 **실물 마이크 1회 보정이 필요하다**(게이트 1과 함께 처리 가능).

---

## ⚠️ 포트 함정 — 저장소 문서의 8000은 틀렸다

**이 머신의 :8000은 StockAgent가 쓴다.**

| 포트 | 서비스 |
|---|---|
| **:8002** | **OhMyEnglish API** (`/health` → `{"status":"ok"}`) |
| :8000 | StockAgent (MOCK) — `openapi.json` title로 식별 |
| :3000 | OhMyEnglish 프론트 (Next.js 16) |
| :5433 | PostgreSQL (podman `ohmy-pg`) |

`app/frontend/lib/config.ts:5` 폴백이 `:8000`이라 `.env.local`이 없으면 프론트가 StockAgent에
붙어 **결과 조회가 조용히 실패한다**. 현재 `app/frontend/.env.local`에
`NEXT_PUBLIC_API_BASE=http://localhost:8002`가 있고 dev 서버 번들에 반영된 것을 확인했다
(`.next/dev/**`에 `localhost:8002`). 백엔드는 **반드시 `--port 8002`**로 띄운다.

---

## 로컬 실행 방법

```bash
# DB (podman — docker 없음)
scripts/dev_db.sh start          # postgres:16-alpine, :5433, ohmy/ohmy/ohmyenglish
python3 scripts/migrate.py       # 001 적용 + 고정 사용자·시나리오 3행 시드 (멱등)
#   추적은 파일명 기준 — 001을 재작성했다면 dev DB를 drop/재생성해야 한다

# 백엔드 (Python 3.13 venv — uv).  ⚠️ 포트 8002 · --reload 없음(소스 바뀌면 재기동)
cd app/backend && .venv/bin/uvicorn app.api.main:app --port 8002
#   VOICE_ADAPTER=stub(기본) | stub_unresponsive(연결 실패 재현) | nova(실연동)
#   NOVA_ENDPOINTING_SENSITIVITY=HIGH|MEDIUM(기본)|LOW      (config.py:66,73)
#   WORKER_ENABLED=false  → 분석 워커 정지 (자격증명 없이 부팅)

# 프론트 (Next.js 16)
cd app/frontend && npm run dev   # :3000. .env.local 이 :8002 를 가리켜야 한다

# 검증 게이트 (전부 통과 상태여야 정상)
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . \
  && .venv/bin/ruff format --check . && ty check
#   ⚠️ cwd가 게이트의 일부다. ruff 설정은 app/backend/pyproject.toml 하나뿐이고
#      리포루트에는 없다 → 리포루트에서 돌리면 ruff 기본 규칙이 적용돼 56 errors가 난다.
#      그건 회귀가 아니라 다른 규칙셋이다. 반드시 app/backend cwd에서 판정한다.
#   tests/ 와 scripts/ 는 위 `ruff check .` 범위 밖 → 따로: ruff check ../../tests ../../scripts
#      (이때도 cwd는 app/backend. 현재 6건 잔존 — 5차수 정리 대상)

# Nova 직접 왕복 (자격증명·모델 생존 확인 + 발음 픽스처 ASR 확인)
cd app/backend && .venv/bin/python ../../tests/harness/spike_nova_protocol.py --wav p1a.wav
#   불투명한 AccessDeniedException('') → OMY_SPIKE_CAPTURE_BODY=1 로 본문 포착
```

### `.env` (app/backend, gitignore 대상)

`config.py`의 `prepare_bedrock_credentials()` 우선순위:

1. `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (+임시면 `AWS_SESSION_TOKEN`) → **SigV4**.
   이때 `AWS_BEARER_TOKEN_BEDROCK`을 프로세스 환경에서 **제거**해 단일 경로를 강제한다.
   **Nova 양방향은 이 경로만 가능하다.**
2. 없으면 `AWS_BEARER_TOKEN_BEDROCK` 폴백 — Claude invoke는 되지만 Nova는 403.
3. 둘 다 없으면 워커 기동 시 `RuntimeError`.

현재 `.env`는 ①번으로 동작한다. ⚠️ **이 access key는 대화 기록을 경유했다 — 로테이션 권장**
(`docs/ops/iam-setup-nova-sigv4.md` §6).

---

## 현재 스택·DB 상태 (**2026-08-26 17:2x 재실측 — 4차수 teardown 이후 값**)

| 항목 | 값 |
|---|---|
| 백엔드 | `:8002` **스텁 모드** baseline (`--log-level warning`), **09:59:30 기동**(4차수 teardown 시 재기동). 이후 변경된 `.py` **없음** → 최신. 프로세스 env에 `VOICE_ADAPTER` **잔류 없음** |
| 프론트 | `:3000`, 08-25 09:45 기동. 소스는 그보다 새롭지만 **dev 서버가 재컴파일해 최신**이다 |
| DB baseline | `learning_sessions` 2 · `utterances` 6 · `error_patterns` 1 · `error_occurrences` 2 · `frequency` 합 2 · `analysis_jobs` 3 — **4차수 teardown 후 재실측으로 일치 확인** |
| 하네스 부기 | `harness_runs` **5행**(4차수가 5번째 회차 `8e49d45a…`, `git_commit=4588b50`, note `round#4 P+M only`) · `harness_sessions` **35행** · `harness_pattern_baseline` 1행 — **4차수 개시 시 재생성된 것으로 확정**(`xmin` **51149**가 3차수 마지막 세션 `50579`와 4차수 첫 세션 `51177` **사이**다. 테이블에 생성 시각 컬럼이 없어 `xmin`으로 판별한다). **5차수 개시 때 또 새로 뜬다** |
| 음성 픽스처 9개 | `u1~u3`(문법 오류용) + `p1a/p1m/p1k/p2a/p2m/p2k`(발음 쌍, 신규) |

> ⚠️ 하네스 §5의 "낡은 프로세스" mtime 검사는 **프론트에 오탐을 낸다** — Next dev는 HMR로
> 재컴파일하므로 소스가 프로세스보다 새로워도 최신일 수 있다. mtime 검사는 **백엔드에만**
> 의미가 있다(`--reload` 없음). 프론트는 번들(`.next/dev/**`) 또는 화면으로 확인한다.

---

## HANDOFF 이전 판 `c55fbc4` 이후의 커밋

> 개수·최신 해시를 이 제목에 박지 않는다 — 박으면 갱신할 때마다 낡는다(실제로 2회 낡았다).
> **`git log --oneline c55fbc4..HEAD`로 확인하라.** 아래 표는 `5e3083f`까지(16건) 열거한 것이고,
> 그보다 많으면 그 차이가 이 파일 갱신 이후에 생긴 커밋이다.

| 커밋 | 내용 |
|---|---|
| `3c62770` | `fix:` 전사문·보조 문구 색을 테마 토큰으로 (**F-1** HIGH, 1차수 발견) |
| `9935715` | `test:` 자동 테스트 하네스 + 1·2차수 기록 (절차 HTML 2개 포함 — 이전 판이 "미추적"이라 한 것은 **해소됨**) |
| `832b258` | `test:` Nova 실음성 왕복 실증(N-0·N-1) + 2차수 회귀 |
| `dae398e` `589950a` | `docs:` 3차수 수정 지시 + 개시 근거(ROUNDS 원장) |
| `3bde54f` | `fix:` **F-2** `target_form`을 패턴 수준 일반형으로 (캡틴 선택지 B) |
| `37a2869` | `feat:` **Nova 2 Sonic 실연동** (포트 확장·어댑터·프론트 입출력 교체·테스트 28건) |
| `486c302` `6e0ba96` | `docs:`/`test:` 수정 세션 handoff 신설 + 3차수 회귀 기록(F-2 검증·N5) |
| `c1d34ef` `32a6c22` | `docs:` 하네스 handoff 4차수 진입용 재작성 + "미수행"의 의미 명확화 |
| `204d8a1` | `test:` **4차수 준비** — P계층(발음)·M계층(학습 반영) 신설, 발음 픽스처 6개, 사전 실측, 이 파일 갱신 |
| `4588b50` | `docs:` handoff의 커밋 참조를 "≥ 204d8a1" 형태로 고정 (4차수 회차가 DB에 이 커밋으로 기록됐다) |
| `61fc7ca` | `test:` **4차수 P·M 실행** — 발음 교정 부재 확정, 학습 반영 부재 확정, **신규 결함 0건**, 스크린샷 3장 |
| `5ee59f8` `5e3083f` | `docs:` 캡틴 결정(발음 교정 수정 보류·기록만) + 게이트 정리(실물 마이크 이월, M계층 반영 단위 2갈래) |

---

## 제품 정의·설계 정본

- 제품: 반복 영어 오류를 패턴으로 기억해 말하기 중심으로 재훈련하는 개인화 학습 Agent
  (일상 Q&A → IT 업무 → AWS Engage Manager 보고)
- 요구·설계
  - `docs/PRD.md` / `docs/requirements-summary.md` / `docs/agent-system-prompt.md`(지시문 고정부) /
    `docs/first-4-weeks.md`(손으로 쓴 시나리오 뱅크)
  - `docs/design/2026-08-24-first-vertical-slice-design.md` (리뷰 5회 승인)
  - `docs/design/2026-08-25-first-slice-acceptance-criteria.md` (완료 선언 규칙 6항목 §145)
  - `docs/design/2026-08-25-phase1-implementation-plan.md` (12태스크)
  - `docs/design/2026-08-25-learning-coach-agent-design.md` (3단계, **검토 전 초안**)
  - `docs/ops/iam-setup-nova-sigv4.md` (IAM 절차 + SDK 함정 §5.1)
  - `docs/database-schema.md` / `docs/nova-sonic-claude-architecture.md` / `docs/voice-architecture.md`
- 테스트 하네스: `tests/harness/README.md` + 위 §기록 규약의 5개 문서
- 기술: us-west-2 / `amazon.nova-2-sonic-v1:0` / `us.anthropic.claude-opus-5`
  (**`[1m]` 접미사 금지** — Bedrock 프로필 아님) / FastAPI+asyncpg / PG 큐(SQS·Redis 배제, 근거 §5.0) /
  Next.js 16 / podman / 인증 없음·고정 사용자 1명·localhost 전용
- 데이터 규칙: 오류는 재사용 가능한 패턴 단위(`unique(user_id, pattern_key)`), 복습 1·3·7일
  (**스키마만**), `voice_command` 발화는 분석 제외, 음성 녹음 기본 미저장(opt-in)
- HTML 현황 보고서 3부: `docs/status-report-2026-08-25*.html` (Slack #clawair 전송 완료)

## 구현 중 확정된 주요 판단 (요약)

- **큐 의미론**: claim당 고유 lease token / `attempts`는 claim 시 +1(상한 5) / claim 내장 reaper가
  좀비를 `failed`로 수렴 / 모든 전이는 `status='running' and locked_by=token` 조건 원자화 /
  시계는 `clock_timestamp()` (`now()`는 트랜잭션 고정이라 백오프 무력화 — 실측)
- **멱등성**: 분석 결과는 발화 단위 replace(delete+insert 한 트랜잭션). `frequency`는 행 수 재계산,
  `last_seen_at`은 **발화 시각** 기준
- **pattern_key 계약(§5.6)**: 기존 key 목록 프롬프트 주입 + 재사용 우선 + 신규만 `{category}_{snake}`
- **`target_form`은 패턴 수준 일반형**(F-2, 캡틴 선택지 B). 코드로 강제하지 않고 프롬프트로 만든다 —
  엄격 검증은 W7 경로로 job을 `failed`로 만들기 때문(수정 세션 근거, 3차수 Q1 검증)
- **빈/공백 전사문** = findings 0건 done + Gateway 미저장 이중 방어
- **Nova**: `SPECULATIVE`→`partial`, ASSISTANT 텍스트는 `completionEnd`에서 확정 승격(없으면 agent
  발화가 저장되지 않는다), 스트림 상한 8분, 스텁은 새 이벤트를 흘리지 않는다(모드 격리)
- **결과 API**: R2 5분기 우선순위(failed→no_utterances→analyzing→partial_failure→final)
- **agent 발화도 `utterances`에 저장**(job은 user learning만 — W6)

## 후속(비차단) 항목

- **`tests/harness/**`에 ruff 6건** — `inject_errors.py`(I001·E501) · `measure_contrast.py`(E501) ·
  `spike_nova_protocol.py`(I001) · `ws_session.py`(E501·UP041). 문서화된 게이트 범위 밖이지만
  **테스트 세션 소유 파일이라 4차수에 정리한다**
- `pending_learning_utterances`(`services/utterances.py:145`)가 앱에서 미사용 — AC W6 대응물로
  유지 중, 삭제 여부 캡틴 판단
- WS 엔드포인트 **origin 미검증**(`api/ws.py`에 origin 참조 0건) — localhost 단일 사용자라 수용
- `botocore` 재시도 미설정(스로틀 중복 과금) — Phase 2 운영 관찰 대상
- **`.claude/settings.json` 미커밋(untracked, gitignore 대상 아님)** — `worktree.bgIsolation="none"`.
  하네스의 "워크트리 금지" 제약이 이것에 의존한다. **지우지 마라.** 커밋 여부는 캡틴 판단
- 이연 minor 33건 전건 "병합 전 필수 아님" triage 완료 — 목록·근거는 ledger

## 다음 작업 후보 (우선순위는 캡틴 결정)

1. **하네스 5차수 실행** — 4차수에서 미실행한 묶음 ①②③ + P8 + **P계층 `p2` 쌍** +
   `tests/harness/**` ruff 6건
2. **캡틴 게이트 3건 처리** — 실물 마이크 1회(게이트 1·발음 보정을 한 번에) / 발음 교정 범위 / M계층 단위
3. **학습 코치 Agent 구현 계획** — 설계서 검토 → `superpowers:writing-plans`. §12.1 분해 여부와
   §11 미결 3건(최근 창 14일 / 정답 판정 주체 / `impact_score`)이 선행 결정
4. **보안** — access key 로테이션

## 다음 세션 진입 절차

1. `git log --oneline c55fbc4..HEAD`로 위 커밋 표를 대조 (**HEAD ≥ `5e3083f`**).
   표보다 커밋이 많은 것은 정상 — 그 차이가 이 파일 갱신 이후의 작업이다
2. **포트 함정 절을 먼저 읽어라** — 백엔드 `--port 8002`, 프론트 `.env.local` `:8002`
3. 게이트 4개를 돌려 실측 확인 (241 passed / ruff · format · ty clean)
4. Nova를 건드리면 `spike_nova_protocol.py --wav p1a.wav`로 자격증명 생존을 먼저 확인
   (키 로테이션 시 여기서 먼저 깨진다)
5. 5차수를 시작하면 `handoff/HANDOFF-test-harness.md` §5 개시 절차를 그대로 실행 —
   `run_id.txt` 오염 방지 `grep` 고정과 `harness_pattern_baseline` 재생성이 포함돼 있다
6. 완료 선언은 AC 문서 §완료 선언 규칙 6항목 전건 충족 시에만 — 미충족이면 완료라 부르지 않는다
7. 프로세스 상세(모든 ruling·이연 minor·red→green 증거 위치)는
   `.superpowers/sdd/2026-08-25-phase1-implementation-plan/progress.md` (ledger, git 미추적)

## 구현 시작 전 확인 항목 (이력)

- [x] `amazon.nova-2-sonic-v1:0` 실존·streaming 확인 (2026-08-24)
- [x] `us.anthropic.claude-opus-5` 호출 권한 — invoke HTTP 200 (2026-08-24)
- [x] 오디오 녹음 보관 — 첫 슬라이스에서 켜지 않음 (기본 미저장 opt-in, 캡틴 승인)
- [x] PostgreSQL 컨테이너(podman) — 기동·마이그레이션·시드 확인
- [x] SigV4 자격증명 + Nova 양방향 왕복 (2026-08-26) — Phase 2 진입 조건 충족
- [x] **Nova 실연동 앱 경로 관통 (2026-08-26, 3차수 N5)** — AC1 충족
- [ ] Phase 1 완료 선언 — 캡틴 게이트 3건 대기
