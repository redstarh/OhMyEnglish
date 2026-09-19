# 배치 B4 회차 결과 — TS-31 · TS-32 · TS-35

## 1. 회차 정보

| 항목 | 값 |
|---|---|
| 회차 | `2026-09-19-b4` |
| 측정 창 | 2026-09-19 06:18Z ~ 06:30Z (DB 시계로 확인: `select now()` → `06:30:29Z`) |
| 착수 시 HEAD | `997c728` |
| 종료 시 HEAD | `95d5dfe` |
| 범위 | 테스트 원장 시나리오 TS-31(A13 워커 큐) · TS-32(A14 복습 주기) · TS-35(A17 무대) |
| 실행 수단 | 큐·DB 층 드라이버 5종(내가 이 회차에 작성함) + 실제 WebSocket 1건 |

⚠️ **회차 도중 HEAD 가 움직였고 앱 소스는 무변경임.** `git diff --name-only 997c728 95d5dfe` 가
`tests/agent/backlog/tasks/ts-24 ...` 1파일만 냈음 — 배치 B3 의 테스트 원장 커밋임. 따라서 이 회차의
모든 측정이 **같은 앱 소스**에 대한 것임.

## 2. 환경 — 이 회차에 직접 재서 확인함

| 항목 | 측정값 |
|---|---|
| macOS | `27.0` |
| PostgreSQL | `17.9 (Homebrew)` · dev DB `ohmyenglish` (:5432) · 스키마 `ohmyenglish` |
| Python | `3.13.12` (`app/backend/.venv`) |
| 백엔드 | `:8002` 응답 `200` (`/health`) — 호출 세션 소유이고 내가 띄우지도 죽이지도 않았음 |
| 프런트 | `:3000` 기동 중 — 이 회차는 화면을 쓰지 않았음 |
| 유료 모델 호출 | **0건.** `select count(*) from llm_calls where called_at > '2026-09-19 06:15:00+00'` → `0` |
| job 집계 | 회차 전 `done 47 · failed 64 · pending 0` → 회차 후 **같은 값** (워커가 아무것도 처리하지 않았음) |

⛔ **워커 루프를 한 번도 켜지 않았음**(함정 `H-CD`). `claim_next` · `dispatch` · `complete` ·
`process_analysis` · `process_scenario` 를 드라이버가 **직접** 불렀고, `recover_while_idle` 은
부르지 않았음(§7 의 「계측하지 못한 것」이 그 근거를 가짐).

⚠️ **모델 호출만 스텁임.** TS-32 와 TS-35 AC#1 의 드라이버는 `ClaudeClient` 자리에 정해진 JSON 을
돌려주는 스텁을 넣었음 — 프롬프트 조립·파서·검증·저장·큐·복습 재계산은 **실제 코드**를 지나갔고
Bedrock 만 지나가지 않았음. 그래서 비용이 0 이고 `llm_calls` 도 늘지 않았음.

## 3. 공유 인스턴스 판정 — 공유임 (§2-6)

| 확인 | 결과 |
|---|---|
| `lsof -ti:8002` · `:3000` | 둘 다 선점됨(pid 2087 외) → 다른 주체가 소유함 |
| `git log` | 회차 중 커밋 1건이 늘었음(B3) → 공유 확정 |
| `find app -newermt '-40 minutes' -name '*.py'` | 0건 → 앱 소스를 고치는 주체는 없었음 |

공유이므로 규칙 셋을 적용했음.

1. **전역·공유 상태를 바꾸지 않았음** — 마이그레이션·`ALTER`·설정 표를 건드리지 않았음.
2. **내 자료를 별도 사용자 행으로 격리했음** — `users.display_name` 이 `b4-` 로 시작하는 사용자를
   드라이버마다 새로 만들고 끝에 지웠음. 픽스처 사용자(`Learner`)의 행은 **읽기만** 했음.
   예외 하나는 TS-35 AC#4 의 WebSocket 다리임 — 소켓이 `FIXED_USER_ID` 를 박아 넣어 격리할 수
   없었고, 그래서 세션 id 집합을 앞뒤로 떠서 **원래대로 돌아온 것을 읽어 확인**했음(§6).
3. **전체 행 수로 판정하지 않았음** — 내가 심은 행만 id 로 집어 셌음. 예외는 「생성 무대 수」이고
   그 표는 회차 전 0행이었음을 먼저 읽어 두고 썼음.

## 4. 착수 지시의 전제를 재검증한 결과 (§3)

| 지시가 준 전제 | 그 자리에서 잰 명령 | 결과 |
|---|---|---|
| dev DB 는 StockAgent 와 공유 | `psql ... select version()` | 참 — 같은 서버 :5432 |
| 우리 표는 스키마 `ohmyenglish` | `select current_schema()` → `ohmyenglish` | 참 |
| 워커가 꺼져 있음 | `analysis_jobs` 집계를 회차 전후로 비교 | 참 — `done` 이 47 에서 늘지 않았음 |
| 배치 B3 가 동시에 도는 중 | `git log` 회차 중 +1 커밋 | 참 |

⚠️ **`app/backend/.env` 에는 `WORKER_ENABLED` · `VOICE_ADAPTER` 줄이 없음.** 그 값은 호출 세션이
프로세스 환경으로 넘긴 것이므로 파일을 읽어서는 확인할 수 없었고, 대신 **집계로** 확인했음(위 표).

## 5. 착수 시 원장 상태 — 이 회차의 기준선

착수 시점에 `backlog task view` 로 직접 뜬 상태임.

| 시나리오 | 착수 상태 | 착수 시 체크된 AC |
|---|---|---|
| TS-31 | `In Progress` | 0 / 5 |
| TS-32 | `In Progress` | 0 / 4 |
| TS-35 | `In Progress` | 0 / 4 |

⛔ **세 시나리오 모두 이 회차가 첫 실행임** — 이전 회차의 판정이 없으므로 **회귀를 판정하지 않음.**
이 회차의 결과가 다음 회차의 기준선임.

## 6. 판정표

| 시나리오 | 판정 | AC | 근거 파일 |
|---|---|---|---|
| TS-31 · A13 분석 워커 큐 | **통과** | 5 / 5 | `evidence/TS-31-queue-layer.json` · `evidence/TS-31-part-sweep.json` |
| TS-32 · A14 오류 패턴과 복습 주기 | **통과** | 4 / 4 | `evidence/TS-32-review-cycle.json` |
| TS-35 · A17 시나리오(무대) | **통과** | 4 / 4 | `evidence/TS-35-scenario.json` · `TS-35-rotation-app-path.json` · `TS-35-ws-intake.json` |

- 새로 실패: **0건**
- 차단: **0건**
- 등록한 결함: **`TASK-232`** 1건 — TS-35 AC#2 는 통과이고 그 옆에서 관측된 별건임(§9).
- 모든 판정을 **2회 돌려 같은 값**을 얻었음(§7-3). 드라이버 5종을 각각 두 번 실행했고 판정 키의
  값이 전부 일치했음.

## 7. TS-31 · A13 분석 워커 큐 — AC 별 측정

드라이버: `evidence/d1_queue.py`(큐 층) · `evidence/d2_part_sweep.py`(고아 스윕).
⛔ claim 을 부르는 자리는 **전부 롤백되는 트랜잭션** 안임 — `claim_next` 가 전역 최소
`available_at` 을 집으므로 그러지 않으면 남의 job 을 집을 수 있음(`H-AT` 경로 ①).

### AC#1 · 표에 없는 job 종류가 큐에 사유를 남김 (TASK-225) — 통과

- 내 발화에 `analyze_utterance` job 1건을 심고 `available_at` 을 `1970-01-02` 로 당겨 **내 것이
  집히는 것을 먼저 확인**했음(`B_claimed_is_mine: true`).
- 그 claim 의 `job_type` 만 `b4_bogus_job_type` 으로 바꿔 `dispatch` 에 넘겼음.
- 결과: `last_error` = `no handler for job type: b4_bogus_job_type` · `status` = `pending` ·
  `attempts` = 1 · `available_at` 이 백오프만큼 밀렸음.
- **관측력**: 같은 수단으로 읽은 before 값이 `last_error: null` 이었음 — 내 판독이 이 칸의 변화를
  실제로 본다는 뜻임.

### AC#2 · lease 를 잃은 뒤에는 결과를 커밋하지 않음 (TASK-224) — 통과

두 층에서 쟀음.

1. **큐 함수 층** — `locked_by` 를 다른 토큰으로 바꾼 뒤 `complete` 를 부르면 `LeaseLost` 가 올라옴
   (`E_lease_lost_raised: true`). `fail_or_retry` 는 `False` 를 돌려줌
   (`E_fail_or_retry_lost_lease: true`).
   **양성 대조**: 같은 함수가 **올바른 토큰**에서는 `done` 으로 통과함
   (`E_owner_token_completes: "done"`) — 「아무것도 못 하는 함수」와 구별됨.
2. **실제 호출자 층** — `process_scenario` 가 claim 한 뒤 그 job 의 `locked_by` 를 다른 토큰으로
   바꿔 임대를 잃은 상태를 만들고 끝까지 처리시켰음.
   모델 스텁은 호출됐고(`lease_lost_model_was_called: true`) **무대 행은 0건 그대로**였음
   (`lease_lost_generated_before/after` 둘 다 0). job 은 `running` 이고 `locked_by` 가 바뀐 값
   그대로이며 `last_error` 가 `null` — 「내 것이 아닌 job 에 실패를 보고하지 않는다」도 함께
   성립함.
3. **코드 확인** — `LeaseLost` 를 잡는 자리가 다섯 개(`plan`·`session_summary`·`weekly_report`·
   `analysis`·`scenario_generator`)이고 모두 **broad `except Exception` 바로 앞**이며 결과 쓰기와
   `complete` 가 한 `conn.transaction()` 안에 있음.

### AC#3 · 고아 스윕이 정지 중 세션의 `.part` 를 지우지 않음 (TASK-223) — 통과

- 임시 뿌리에 `active` · `paused` · `completed` 세션 디렉터리를 만들고 각각 `.pcm.part` 1개를 둠.
  `completed` 에는 포인터 없는 `.pcm` 1개를 더 둠(양성 대조).
- `sweep_orphan_recording_files` 결과: **2건 삭제** — `completed` 디렉터리가 비어 지워졌고
  `active` · `paused` 의 `.part` 는 **그대로 남았음**.
- 값역의 정본이 `sessions.LIVE_SESSION_STATUSES` = `('active', 'paused')` 이고 스윕이 그것을 읽음
  (측정값 `live_statuses_const`).
- **관측력**: 끝난 세션 쪽이 실제로 지워졌으므로 이 계측은 「아무것도 지우지 않는 스윕」을
  통과시키지 않음.

### AC#4 · 회복 스윕이 running 상태로 시한을 넘긴 job 을 되돌림 — 통과

| 팔 | 조건 | 결과 |
|---|---|---|
| 만료 | `running` · `locked_at` = now − 6분 · `attempts` 1 | 내 job 이 다시 집혔고 `attempts` 2 · lease 토큰이 새로 발급됨 |
| 생존 | `running` · `locked_at` = now − 1분 | 집히지 않았음 (음성 대조) |
| 소진 | `running` · `attempts` 5 · 만료 | reaper 가 terminal `failed` 로 닫고 사유 `max attempts exceeded (lease expired without report)` 를 남김 |

시각은 `claim_next(now=)` 로 주입했음 — 기다리지 않고 경계를 만드는 방법임.

### AC#5 · job 5종이 전부 표에 있고 claim 쿼리가 failed 를 집지 않음 — 통과

- **값역 대조**: DB CHECK `analysis_jobs_job_type_check` 의 5값과 `_HANDLERS` 의 키 5개가
  **정렬해서 동일**(`A_match: true`). 값역 정본이 DB 이고 표가 그것을 따름.
- **claim 술어**: 내 job 을 `status='failed'` · `available_at='1970-01-01'`(전역 최소)로 두고
  `claim_next` 를 부르면 내 것이 집히지 않았음(`C_failed_claimed_mine: false`). 그 순간 dev DB 에
  claim 가능한 다른 job 도 없어 반환은 `null` 이었음.
- **관측력(§7-7)**: 같은 행을 `pending` 으로만 바꿔 같은 수단으로 부르면 **집혔음**
  (`C_pending_claimed_mine: true`). 즉 「0건 관측」이 내 드라이버의 눈이 먼 것이 아님을 증명함.
  이 두 팔은 각각 롤백했으므로 DB 상태는 `failed` 그대로였음(`C_status_after_rollback: "failed"`).

## 8. TS-32 · A14 오류 패턴과 복습 주기 — AC 별 측정

드라이버: `evidence/d4_review.py`. `process_analysis` 를 실제로 부르므로 패턴 upsert · 발생 저장 ·
`store_attempts` · `review.recompute` · `review_tasks` 사다리 · 일일 요약이 모두 실제 경로임.
발화 시각은 내가 행을 만들 때 박았음 — **저장된 `timestamptz` 를 나중에 변환·UPDATE 하지 않았음**
(전역 시각 규약 4항).

### AC#1 · 복습 1일·3일·7일 주기가 실제로 돌아감 — 통과

기준 시각 `t0` = 측정 시점 − 20일. 상수 `STAGE_DAYS` = `(1, 3, 7)`.

| 단계 | 입력 | `next_review_at` 기대 | 실제 |
|---|---|---|---|
| ① 첫 오류 | 발화 `t0` 에 `article` 오류 1건 | `t0 + 1일` | 일치 (`cycle_1_day: true`) |
| ② 정답 | 발화 `t0+1일 1분` 에 `correct` | 그 발화 `+ 3일` | 일치 (`cycle_3_day: true`) |
| ③ 정답 | 발화 `t0+4일 5분` 에 `correct` | 그 발화 `+ 7일` | 일치 (`cycle_7_day: true`) |
| ④ 정답 | 발화 `t0+11일 10분` 에 `correct` | 완주 — 예정일 없음 | `next_review_at` 이 `null` · `mastery_score` `100.00` |

`review_tasks` 에 단계 1·2·3 행이 `done` 으로 남고 각 행의 `due_at` 이 **이동 전 앵커**에서 계산된
값임을 함께 읽었음(`ladder_stages_recorded: [1, 2, 3]`).

### AC#2 · 또 틀린 패턴의 주기가 1일로 되돌려짐 (PRD R11-6) — 통과

- 완주 뒤 `t0+12일` 발화에서 같은 패턴이 재발함.
- `next_review_at` = **재발 발화 시각 + 1일** (`relapse_back_to_1_day: true`) ·
  `mastery_score` 가 `100.00` → `0.00` 으로 내려감.
- `review_tasks` 에 `cycle_started_at` 이 재발 시각인 **새 사이클의 단계 1 행**이 `pending` 으로
  생겼고, 완주한 이전 사이클 행 셋은 지워지지 않고 남았음.

### AC#3 · 난이도가 한 번에 한 단계씩만 오르고 내려가는 것도 허용됨 — 통과

이 구현에서 「난이도」는 **CEFR 목표 수준**임(PRD R11-7 · AC11-4 의 「난이도 두 단계 도약」).
`parse_plan(current_level='B1', ...)` 을 다섯 팔로 불렀음.

| 팔 | 결과 |
|---|---|
| `B1 → B1` (유지) | 통과 |
| `B1 → B2` (한 단계 상향) | 통과 |
| `B1 → A2` (한 단계 하향) | **통과** — 하향이 허용됨 |
| `B1 → C1` (두 단계 상향) | 거부: `level jump from 'B1' to 'C1' skips more than one CEFR step` |
| `B1 → A1` (두 단계 하향) | 거부: 같은 사유 |

⚠️ `error_patterns.self_difficulty`(1~5) 는 **학습자 자기 평가 칸**이고 복습 시계와 무관함 —
이 AC 의 판정 대상이 아님을 적어 둠.

### AC#4 · 틀린 문장이 재사용할 수 있는 패턴 이름으로 저장됨 — 통과

- 틀린 구간과 교정이 그대로 저장됨: `original_span` `go to gym` · `correction` `go to the gym` ·
  `pattern_key` `article_b4_marker_stage`(형식 `^{category}_[a-z0-9_]+$`).
- **재사용 확인**: 재발 단계에서 **표기만 다른 key**(`Article_B4_Marker_Stage`)를 넣었더니
  패턴 행이 **1행 그대로**이고 저장된 이름은 기존 표기였으며 `frequency` 가 2 로 다시 세어졌음
  (`pattern_row_count_after_recased_key: 1`). 쌍둥이 패턴이 생기지 않음.
- **음성 대조**: 규격 밖 **신규** key(`Bad Key With Spaces`)는 저장되지 않고 그 발화의 분석이
  거부됐음 — `new pattern_key 'Bad Key With Spaces' does not match ^article_[a-z0-9_]+$` ·
  패턴 행 수는 1 그대로. 즉 「이름이 재사용 가능한 형태인지」를 실제로 강제함.

## 9. TS-35 · A17 시나리오(무대) — AC 별 측정

드라이버: `evidence/d3_scenario.py` · `d3b_rotation_app_path.py` · `d5_ws_intake.py` ·
`d6_pool_boundary.py`.

### AC#1 · 시나리오가 생성돼 세션에 붙음 — 통과

- `enqueue_generate_scenario` → `claim_next` → `process_scenario` 를 실제로 지나갔고 job 이
  `done` 으로 닫혔음.
- `learning_scenarios` 에 `source='generated'` 행 1건이 생겼고 `level` 이 **모델이 아니라 앱이 넣은
  값**(사용자의 `current_level` = `B1`)이었음. 프롬프트에 다섯 축 블록이 실려 있었음.
- **세션에 붙는 것**: 그 사용자로 다음 세션을 열었더니 `scenario_id` 가 **그 생성 무대**였고
  `scenario_pick` 이 `new` 였음(결정 80 — 생성 무대가 신규 차례에서 시드보다 먼저 집힘).
- ⚠️ **모델 호출은 스텁임.** 남는 것 하나: 실물 Claude 응답이 파서 계약(제목 언어 · 값역 안 category)
  을 지키는지는 이 회차가 재지 않았음. 그 다리는 유료 호출이라 이 배치의 허용 범위 밖임(§11).

### AC#2 · 회전 비율 70대 30 규약이 성립함 — 통과

두 절로 쟀음.

1. **순수 함수 절** — 후보 10건 · 빈 이력에서 `pick_scenario` 를 30회 연속으로 돌렸음. 결과
   `NNNRRRRRRRRNNNRRRRRRRRNNNRRRRR` = **신규 9 · 반복 21**, 창(10회)마다 신규 `[3, 3, 3]`.
   설계서 `2026-09-12-scenario-rotation-70-30-design.md` 의 표가 적어 둔 기대값(**30회에 9**)과
   **정확히 일치**함.
2. **앱 경로 절** — 시드와 같은 수준(`A2`)의 새 사용자로 `create_session` 을 12회 불렀음. 결과
   `NNNRRRRRRRRN` · 서로 다른 무대 4종(`0101`·`0102`·`0103` 다음에 `0110`). 창 안 신규가 3 을
   넘지 않았고, 12회째에 다시 신규가 나온 것은 첫 신규가 창 밖으로 빠졌기 때문임.

### AC#3 · 시나리오 진행 상태가 턴을 넘어 이어짐 — 통과

- 세션 도중 발화를 넣어 턴을 넘긴 뒤 `load_session_scenario` 를 두 번 읽었고 **같은 무대**가
  나왔음(세션 행의 `scenario_id` 도 그대로). 무대는 세션 생성 시점에 박히고 수준으로 다시
  고르지 않음.
- `load_scenario_progress` 로 읽은 그 무대의 행: `sessions` 1 · `new_picks` 1 ·
  `last_studied_on` `2026-09-19`(사용자 타임존 `Asia/Seoul` 기준 달력 날짜 — `current_date` 가
  아님). 한 번도 안 한 무대도 목록에 함께 나왔음(전체 31행).

### AC#4 · `mode=scenario_intake` 진입이 성립함 — 통과

실제 소켓 `ws://localhost:8002/ws/session?mode=scenario_intake` 로 붙었음(스텁 음성 어댑터).

- `session_started` 프레임이 왔고 이어서 `partial`·`final`·`audio` 프레임이 흘렀음.
- 세션 행: `mode` = `scenario_intake` · `status` = `completed` · `drill_turns_expected` = 20 ·
  발화 6건.
- **종료가 그 모드를 읽어 `generate_scenario` job 을 걸었음**(설계서 §5 흐름 3). 같은 종료가
  `plan_next_session` · `summarize_session` · `summarize_week` 도 걸어 **job 4건**이 남았음 —
  착수 지시가 예고한 그 넷임.
- 되돌림: 내가 만든 세션 1행만 지웠고 픽스처 사용자의 세션 id 집합이 **앞뒤로 동일**
  (27 → 27 · `session_set_restored: true`). job 4건은 cascade 로 걷혔음.

### 그 옆에서 관측한 결함 — `TASK-232`

`AC#2` 의 앱 경로 절을 재다 후보 풀의 경계를 만났고, 가설을 세운 뒤 **반증을 시도해** 경계를
갈랐음(§7-9).

| 팔 | 조건 | 결과 |
|---|---|---|
| A | `current_level='B1'` · B1 무대 **0행** | 폴백이 돌아 시드 30행이 후보 → `NNNRRR` · 무대 3종 |
| B | `current_level='B1'` · B1 무대 **1행** | 폴백이 꺼짐 → `NRRRRR` · **무대 1종** |

즉 결함의 조건은 「후보가 적다」가 아니라 **「그 수준에 1행이라도 있으면 폴백이 꺼진다」** 임.
시드 30행이 dev DB 에서 전부 `A2` 이므로, 수준이 한 단계라도 오른 학습자는 자기 생성 무대만
후보로 갖게 됨. 회전 규칙 자체는 어긋나지 않았으므로 **AC#2 는 통과로 두고** 결함을 따로 올렸음.

## 10. 남긴 자취와 되돌림 — 전부 읽어서 확인함

| 드라이버가 만든 것 | 되돌린 방법 | 되돌림을 읽어 확인한 값 |
|---|---|---|
| 사용자 6행(`display_name` 이 `b4-` 로 시작) + 그 cascade(세션·발화·job·패턴·발생·복습 과제·일일 요약) | 사용자 행 삭제 | `cleanup_users_left: 0` (드라이버마다) |
| 생성 무대 2행(`b4` 표지 제목) | 세션 삭제 뒤 무대 삭제 | `cleanup_generated_left: 0` · 회차 전에도 0행이었음을 먼저 읽어 둠 |
| 라우팅 측정이 남긴 job 1행 | 사용자 cascade | `cleanup_jobs_left: 0` |
| 픽스처 사용자의 WebSocket 세션 1행 + job 4건 | 세션 행 삭제(cascade) | 세션 id 집합이 앞뒤로 동일 (27 → 27) |
| 임시 녹음 뿌리(`/tmp/b4-recordings-*`) | `rmtree` | `temp_root_removed: true` |
| 복습 측정의 DB 변경 | 사용자 cascade | `cleanup_patterns_left: 0` |

⛔ **회차가 만들지 않은 행을 지우거나 고치지 않았음.** claim 술어·회복·lease 측정은 전부 롤백되는
트랜잭션 안에서 했고, 롤백 뒤 내 job 행의 상태를 다시 읽어 원래 값임을 확인했음.

⛔ **대상 소스·설정·마이그레이션·`.env` 를 건드리지 않았음.** 드라이버는 전부 `/tmp/b4/` 에 쓰고
증거 사본만 이 회차 디렉터리에 두었음.

## 11. 계측하지 못한 것 — 덮지 않고 적음

1. **실물 모델 호출 0건.** TS-32 와 TS-35 AC#1 은 `ClaudeClient` 를 스텁으로 갈아 쟀음. 남는 것은
   「실물 Claude 응답이 파서 계약을 지키는가」이고, 그 다리는 유료 호출이라 이 배치의 허용 범위에
   없었음. ⇒ **승인이 필요한 잔여 항목**으로 호출 세션에 돌려줌.
2. **`recover_while_idle` · `flush_ended_sessions` 를 부르지 않았음.** 그 경로는 끝난 세션에서 job
   없는 발화 묶음을 찾아 **새 job 을 등록**하므로 dev DB 의 보존 회귀 픽스처 세션을 파괴함
   (`H-AT` 경로 ② · `tests/harness/p5_worker_leg.py` 머리말이 그 사고를 기록함). TS-31 의 AC 넷은
   그 함수를 지나지 않고 성립하므로 **판정에 구멍이 없음** — AC#3 은 스윕 함수를 직접 부르고 AC#4 는
   `claim_next` 의 회복 갈래임. `TASK-227` 이 고친 「연결 1건으로 회복 셋을 돌린다」는 이 회차가
   재지 않았음.
3. **리포의 `pytest` 를 돌리지 않았음.** DB 픽스처가 `ohmyenglish_test` 를 **drop/create** 하므로
   같은 시각에 도는 다른 배치의 실행을 깨뜨릴 수 있음(공유 판정 §3). 그래서 기준선을 남의 테스트에
   의존하지 않고 이 회차의 드라이버로 직접 세웠음. ⚠️ 그 대가: 이 회차는 「기존 단위 테스트가
   지금도 초록인가」에 답하지 않음.
4. **성능·계획을 판정하지 않았음.** dev DB 의 행 수가 작아 실행 계획이 Seq Scan 으로 나오는 것이
   정상이므로 그것을 근거로 쓰지 않았음(`jobs.claim_next` docstring 이 같은 경고를 가짐).

## 12. 회귀 판정

세 시나리오 모두 **이 회차가 첫 실행**이므로 회귀를 판정할 이전 값이 없음. 분류는 「새 시나리오」
3건이고 이 회차의 결과가 다음 회차의 기준선임.

⚠️ 이 회차가 확인한 것은 `TASK-223`(정지 중 세션의 `.part`) · `TASK-224`(LeaseLost) ·
`TASK-225`(라우팅 표)가 고친 자리가 **지금도 고쳐진 상태**라는 것임. 그 셋은 회귀가 아니라
현재 상태의 확인임.

## 13. 원장 갱신

| 원장 | 대상 | 조작 |
|---|---|---|
| 테스트 원장 (`tests/agent`) | TS-31 · TS-32 · TS-35 | AC 전건 체크 후 `Done` |
| 작업 원장 (리포 루트) | `TASK-232` | 결함 신규 등록(`To Do`) · 본문에 시나리오 `TS-35` 를 적음 |

기존 결함 `TASK-230` · `TASK-231` 과 같은 뿌리를 다시 등록하지 않았음 — `TASK-232` 는 제품 동작의
결함이고 그 둘과 뿌리가 다름(`TASK-231` 은 AC 문면과 계약의 갈림임).

## 14. 회차 끝에 관측한 환경 변화 — 백엔드 `:8002` 가 내려가 있음

⚠️ **내가 내린 것이 아님.** 이 회차는 그 프로세스를 죽이거나 다시 띄우지 않았음 — 호출 세션이
소유한 것이라 만지지 않는 것이 지시였고, 쓴 것은 WebSocket 클라이언트 1건(정상 종료)과 DB 질의뿐임.

| 시각(KST) | 관측 |
|---|---|
| 15:18 | `curl /health` → `200` (회차 착수 확인) |
| 15:27 | WebSocket 다리 2회째 성공 — `session_started` 수신 · 세션 행 기록 확인 |
| 15:32 | `curl /health` → 연결 거부. `lsof -nP -iTCP:8002 -sTCP:LISTEN` 이 **0행** |
| 15:32 | 프런트(`node`, pid 98298)는 `:3000` 에서 그대로 LISTEN 중 |
| 15:32 | `/tmp/omy-backend.log` 의 마지막 기록이 **14:52** — 종료 흔적·트레이스백이 없음 |

⛔ **누가 내렸는지 이 세션은 가릴 수 없음** — 샌드박스에서 `ps`·`pgrep` 이 막혀 프로세스 이력을 볼
수 없고 로그에도 남지 않았음(신호로 죽으면 그렇게 됨). 다른 배치나 호출 세션이 재기동했을
가능성이 가장 높지만 **단정하지 않음.**

⚠️ **이 회차의 판정은 영향을 받지 않음.** 백엔드가 필요했던 다리는 TS-35 AC#4 하나이고 그 측정은
15:27 에 끝나 증거가 `evidence/TS-35-ws-intake.json` 에 있음. 나머지 드라이버는 DB 층이라 백엔드를
쓰지 않음.

⇒ **다른 배치가 `:8002` 를 쓰려면 호출 세션이 다시 띄워야 함.**
