# 배치 B5 회차 결과 — TS-20 · TS-33 · TS-36

## 1. 회차 정보

| 항목 | 값 |
|---|---|
| 회차 | `2026-09-19-b5` |
| 측정 창 | 2026-09-19 06:38Z ~ 07:02Z (DB 시계로 확인: `select now()` → `06:38:29Z` 가 첫 값) |
| 착수 시 HEAD | `6f7583d` |
| 종료 시 HEAD | `78f7a6c` |
| 범위 | TS-20(A2 음성 세션 왕복 스텁) · TS-33(A15 음성 명령 제어) · TS-36(A18 추가 학습 진입) |
| 실행 수단 | `/ws/session` WebSocket 2종 · Orca 내장 브라우저 · 인프로세스 게이트웨이 드라이버 3종(내가 이 회차에 작성함) |

⚠️ **회차 도중 HEAD 가 움직였고 앱 소스는 무변경임.**
`git diff --name-only 6f7583d 78f7a6c` 가 `tests/agent/runs/2026-09-19-b4/result.md` 1파일만 냈음 —
배치 B4 의 회차 문서 커밋임. `find app -newermt '2026-09-19T06:00:00Z'` 가 0건이므로 이 회차의 모든
측정이 **같은 앱 소스**에 대한 것임.

⚠️ **이 회차는 전용 런처(`~/.claude/test-agent/run.sh`) 없이 리포 cwd 에서 돌았음** — 쓰기 경계를
OS 가 막는 보장이 없고 §1-1 의 규칙만 남았음. 그 규칙을 지켰음: 쓴 파일은 이 회차 디렉터리와
`/tmp` 뿐이고, 대상 소스·설정·`.env`·테스트 코드를 한 줄도 고치지 않았음(`git status` 가 근거).
예외 하나는 `tests/harness/ws_session.py` 가 **스스로** `.harness/evidence/` 에 프레임 JSON 을 쓰는
것임 — 그 도구의 기존 거동이고 내가 그 경로를 지정한 것이 아님. 판정에 쓴 사본은 이 디렉터리에 있음.

## 2. 환경 — 이 회차에 직접 재서 확인함

| 항목 | 측정값 |
|---|---|
| macOS | `27.0` |
| PostgreSQL | `17.9 (Homebrew)` · dev DB `ohmyenglish` (:5432) · `current_schema()` = `ohmyenglish` |
| Python | `3.13.12` (`app/backend/.venv`) |
| Orca | `ready` · appVersion `1.4.205` · runtime reachable |
| 백엔드 `:8002` | **이 회차가 띄우고 내렸음.** `/health` → `{"status":"ok"}` (`version` 키 없음 = StockAgent 아님) |
| 프런트 `:3000` | pid 98298 기동 중 — 호출 세션 소유이고 건드리지 않았음 · `curl` → `200` |
| `app/frontend/.env.local` | `NEXT_PUBLIC_API_BASE=http://localhost:8002` (프리플라이트 P2 통과) |
| 사용자 타임존 | `users.timezone` = `Asia/Seoul` |
| 유료 모델 호출 | **0건.** `llm_calls` 가 회차 전 `34` → 회차 후 `34` |

⛔ **워커를 한 번도 켜지 않았음**(함정 `H-CD`). 백엔드를 `WORKER_ENABLED=false` 로만 띄웠고
어댑터를 바꾸느라 세 번 재기동했음. 프로세스는 셸 `&` 가 아니라 `run_in_background` 로 띄우고
`TaskStop` 으로 내렸음 — 리스너 확인은 `lsof -nP -iTCP:8002 -sTCP:LISTEN -t` 로 함.

**어댑터를 바꾼 이력 셋** (`--reload` 가 없어 매번 내리고 다시 띄웠음):

| 순서 | 어댑터 | 쓴 곳 |
|---|---|---|
| 1 | `VOICE_ADAPTER=stub` | TS-20 AC#1~#3 |
| 2 | `VOICE_ADAPTER=stub_unresponsive` | TS-20 AC#4 |
| 3 | `VOICE_ADAPTER=stub` | TS-36 브라우저 레그 · TS-33 브라우저 레그 · TS-33 종료 경로 대조 |

⛔ **회차 끝에 `VOICE_ADAPTER=stub` 으로 떠 있음** — 다음 배치가 그 상태를 전제함.

## 3. 착수 지시의 전제를 재검증한 결과 (§3)

| 지시가 준 전제 | 그 자리에서 잰 명령 | 결과 |
|---|---|---|
| `:8002` 는 비어 있음 | `lsof -nP -iTCP:8002 -sTCP:LISTEN -t` | 참 — 빈 출력 |
| 프런트 `:3000` 은 호출 세션 소유 | 같은 명령 `-iTCP:3000` | 참 — pid 98298 |
| dev DB 는 StockAgent 와 공유 | `select version()` · `psql_cli` 가 따라가는 DSN | 참 — 같은 서버 `:5432` |
| 스키마는 `ohmyenglish` 이고 `public` 에 호환 뷰가 있음 | `current_schema()` 를 건 introspection | 참 — 표 이름을 `information_schema` 에서 스키마 한정으로 읽었음 |
| Orca 가 브라우저를 줌 | `orca status --json` | 참 — `state: ready` |
| ⚠️ **틀린 전제 1건** | — | **아래** |

⚠️ **착수 지시는 `jobs` 표를 전제한 듯한 이름을 쓰지 않았으나, 내가 처음 던진 집계 질의가 `jobs`
표를 찾아 실패했음** — 이 리포의 큐 표 이름은 `analysis_jobs` 임(`information_schema` 로 확인).
전제 자체의 오류가 아니라 내 질의의 오류였고, 그 사실을 남기는 이유는 다음 회차가 같은 이름으로
집계를 시도하기 때문임.

## 4. 공유 인스턴스 판정 — 공유임 (§2-6)

| 확인 | 결과 |
|---|---|
| `lsof` `:8002` | 회차 시작 시 비어 있었음 → **백엔드는 이 회차 전용** |
| `lsof` `:3000` | 선점됨(pid 98298) → 프런트는 공유 |
| `git log` | 회차 중 커밋 1건이 늘었음(B4 문서) → 리포는 공유 확정 |
| `find app -newermt '2026-09-19T06:00:00Z'` | 0건 → 앱 소스를 고치는 주체는 없었음 |
| dev DB | StockAgent 와 공유 · 다른 테스트 배치는 돌지 않았음 |

공유이므로 규칙 셋을 적용했음.

1. **전역·공유 상태를 바꾸지 않았음** — 마이그레이션·`ALTER SYSTEM`·`ALTER DATABASE`·`ALTER ROLE`
   을 부르지 않았고 `users.timezone` 을 **읽기만** 했음.
2. **내가 만든 행만 지웠음** — 회차가 만든 세션 **20개**를 `teardown_session.py --session-id` 로
   하나씩 걷었고, **기존 행은 하나도 지우지 않았음**. `error_patterns`·`review_tasks` 는 손대지
   않았음(그 표는 이 회차가 갱신하지 않았음 — 워커를 켜지 않았으므로).
3. **전체 행 수로 판정하지 않고 세션 id 로 집어 셌음.** 그래도 복원 확인은 전체 수로 했음 —
   그 수가 회차 전과 **정확히 같아야** 남의 행을 건드리지 않았다는 뜻이기 때문임.

**복원 확인 — 회차 전과 후를 직접 읽었음** (`evidence/00-baseline-db.txt` · `evidence/41-db-restored.txt`):

| 표 | 회차 전 | 회차 후 |
|---|---|---|
| `learning_sessions` | 27 | **27** |
| `utterances` | 175 | **175** |
| `llm_calls` | 34 | **34** |
| `session_plans` | 6 | **6** |
| `weekly_reports` | 0 | **0** |
| `analysis_jobs` (전체) | `analyze_utterance` done 41 · failed 30 / `plan_next_session` done 6 · failed 14 / `summarize_session` failed 10 / `summarize_week` failed 10 · **pending 0** | **같은 값 · pending 0** |

⚠️ **되돌리지 못한 것 하나를 적음**: `harness_sessions` 에는 이 회차가 등록한 행 2건이 남아 있음
(`ws_session.py` 의 `register()` 가 자동으로 넣음). 그 표는 하네스 전용 기록이고 앱이 읽지 않으므로
지우지 않았음 — 회차 이력이 그 표의 값이기 때문임.

## 5. 판정표

| 시나리오 | AC | 판정 | 원장 상태 |
|---|---|---|---|
| TS-20 · A2 음성 세션 왕복(스텁) | 5/5 확인됨 | **통과** | `Done` |
| TS-33 · A15 음성 명령 제어 | 3/3 확인됨 | **통과** | `Done` |
| TS-36 · A18 추가 학습 진입과 즉시 드릴 | 2/3 확인됨 (#3 미확인) | **부분** | `Blocked` |

**새로 실패**: 없음 — 세 시나리오 모두 이 회차가 처음 돌린 것이고 착수 시 상태가 전부
`In Progress`(AC 0건 체크)였음. 따라서 회귀 비교의 기준선이 이 회차임.

**차단 목록**: TS-36 AC#3 하나.
⚠️ **그것은 「관측 차단」이 아니라 「기능 부재로 인한 실패」임**(§7-4 의 구분). 원장 상태를
`Blocked` 로 둔 것은 착수 지시의 절대 조건 2(「AC 하나라도 미확인이면 `Blocked`」)를 따른 것이고,
성질은 실패이므로 결함 `TASK-233` 을 등록했음.

**등록한 결함**: `TASK-233` · `TASK-234` (§7).

## 6. 시나리오별 판정 근거

### TS-20 · A2 음성 세션 왕복 (스텁) — 전건 통과

| AC | 판정 | 근거 |
|---|---|---|
| #1 stub 어댑터로 세션이 열려 픽스처 턴이 흐르고 세션이 닫힘 | ✅ | 프레임 17개가 `session_started` → (agent final · user partial 2 · user final · audio) ×3 → `session_ended` 순서로 왔음. 세션 `54ce134a` · elapsed `0.045s` · DB `status=completed` |
| #2 그 세션의 발화 전사가 DB 에 남음 | ✅ | `utterances` 6행 — `sequence_no` 1~6 이 agent·user 교대이고 전사문이 픽스처와 일치함. **partial 은 저장되지 않았음**(프레임에 partial 6건, 저장 0건) |
| #3 세션 종료가 job 셋을 그 자리에서 등록함 | ✅ | 워커가 꺼진 채 `plan_next_session` · `summarize_session` · `summarize_week` 가 각 1건 `pending` 으로 생겼음. `analyze_utterance` 3건(user final 수와 같음)이 함께 생겼고 그것은 저장 시점의 등록임 |
| #4 `stub_unresponsive` 에서 `voice_adapter_connect_timeout` 사유로 닫힘 | ✅ | 세션 `ddf4913d` — 프레임 2개(`session_started` · `session_failed`) · `reason='voice_adapter_connect_timeout'` · `t=10.033s`(`CONNECT_TIMEOUT=10.0` 과 일치) · DB `status=failed` |
| #5 회차가 만든 세션이 `teardown_session.py` 로 걷혔음 | ✅ | 두 세션 모두 `session_deleted: 1` · 회차 전체 복원표가 §4 |

**함께 관측한 사실 하나** — `stub_unresponsive` 로 **발화 0건에 실패한 세션에도 job 셋이 걸림**
(`plan_next_session`·`summarize_session`·`summarize_week` 각 1건). 결함으로 올리지 않음: 구현이
그것을 의도로 적어 두었음 — `end_session` 은 `closed` 가 있을 때만 걸고 모드 조건을 두지 않으며
(`services/sessions.py:647-671`), `session_summary.process_summary` 가 발화 0건을 「담을 것이
없었다」로 기록하는 판단을 가짐.

### TS-33 · A15 음성 명령 제어 — 전건 통과

⛔ **먼저 계측 수단을 밝힘.** `/ws/session` + `VOICE_ADAPTER=stub` 으로는 이 시나리오를 관측할 수
없음. 음성 명령은 `SessionCommandEvent` 로만 들어오고 그 이벤트를 만드는 것은 **어댑터**인데
(`audio_gateway/port.py` — *"어댑터만 만들 수 있다"*) `StubVoiceAdapter.events()` 는 전사문과 오디오
프레임만 흘림(직접 읽어 확인). 실물 Nova 는 이 배치에서 금지됨. ⇒ **제어 이벤트를 흘리는 어댑터
대역을 드라이버가 넣고 `SessionRunner` 를 그대로 돌렸음**
(`ts33_voice_command_driver.py` · `ts33_end_paths_compare.py`).

**지나간 것(실제 앱 코드)**: `_pump_adapter_events` → `_handle_command` → `_decide_command` →
표지 검사(`is_wake_command`) · 확인 절차 · `_apply_pause`(DB 쓰기) · `closes_session` ·
`_classify_user_final` · 종료 경로 · 실제 dev DB.
**지나가지 않은 것**: ⑴ Nova 의 `toolUse` → `SessionCommandEvent` 번역 ⑵ `/ws/session` 소켓 층
(AC#3 의 브라우저 다리는 이 층을 지나감 — 아래).

| AC | 판정 | 근거 |
|---|---|---|
| #1 명령 여섯 가운데 최소 넷이 세션 안에서 실제로 동작함 | ✅ | **여섯 전부 동작했음.** `next_question`·`show_report` → `voice_command` 프레임 방송 + `executed=True` 보고, 세션 안 닫힘 · `pause`→`resume` → **정지 중 발화가 저장되지 않았고**(로그 `정지 중 학습 발화를 저장하지 않았다 … 33자`, 그 발화가 `utterances` 에 없음) 재개 뒤 발화가 다시 `learning` 으로 저장됨 · `end`(confirmed) → 세션 닫힘, 뒤에 온 발화 미저장 · `start_additional`(confirmed) → 세션 닫힘 + `target` 전달 |
| #2 학습 답변이 음성 명령으로 오인되지 않는 경계가 성립함 | ✅ | 경계 셋을 각각 돌렸음. ⑴ 표지 없는 학습 발화 뒤의 `end` → 실행되지 않고 `voice_command_ignored` 프레임 + `executed=False, reason='no_wake_word'`, 그 발화는 `learning` 으로 저장됨 ⑵ **문장 가운데의 앱 이름**(`I told my friend about Oh My English yesterday.`) → 표지로 인정되지 않음(포함 검사가 아니라 접두 검사임) ⑶ `cancelled` → 세션이 닫히지 않고 대화가 이어져 뒤 발화가 `learning` 으로 저장됨 |
| #3 화면 버튼과 음성 명령이 같은 기능에 닿음 | ✅ | **버튼이 있는 명령 둘 다 같은 자리에 닿았음.** 아래 두 대조 |

**AC#3 대조 ① `start_additional` ↔ 추가 학습 버튼 (브라우저 · 실시간)**

브라우저에서 세션을 열고 소켓 경계에 서버 프레임
`{"type":"voice_command","command":"start_additional","stage":"confirmed","target":"shadowing"}` 와
`session_ended` 를 흘렸음. 화면이 **새 쉐도잉 세션**을 열었고 클립까지 붙었음(페이지 본문에
`A morning routine before work` 와 버튼 `클립 듣기`·`따라 읽기`). DB 행이 버튼으로 연 세션과
**완전히 같음**:

| | `mode` | `learning_source` | `started_via` | 클립 |
|---|---|---|---|---|
| 버튼(`쉐도잉`) `f2b9d9fb` | `shadowing` | `additional` | `ui` | 있음 |
| 음성(`start_additional`) `f5f832a5` | `shadowing` | `additional` | `ui` | 있음 |

코드도 같은 자리를 가리킴 — 버튼은 `startSession(item.entry)`, 음성은
`entryForTarget(event.target)` 가 **같은 `ADDITIONAL_LEARNING` 항목의 `entry`** 를 돌려주고 그것을
같은 `startSession` 에 넘김(`app/frontend/app/page.tsx:100·327·386·623`).
⚠️ 두 행이 `started_via` 까지 같은 것은 **결함임** → `TASK-234`.

**AC#3 대조 ② `end` ↔ 「학습 종료」 버튼 (인프로세스 · 같은 조건)**

⚠️ **첫 시도는 판별력이 없었음.** `/ws/session` 에 `end_session` 프레임만 보냈더니 픽스처
스트림이 45ms 안에 소진되어 **종료의 원인이 언제나 어댑터 소진**이었음
(`evidence/33-ts33-end-button-leg.txt` 의 order 가 픽스처 세 턴을 전부 담았음). ⇒ 어댑터를 0.4초
간격으로 천천히 흘려 두 경로가 각자 종료의 원인이 되게 다시 잼:

| 팔 | 종료의 원인 | `status` | `ended_at` | 어댑터 닫힘 | 마지막 프레임 |
|---|---|---|---|---|---|
| A · 버튼 `{"type":"end_session"}` (t=0.6s, 어댑터는 아직 말하는 중) | 클라이언트 | `completed` | 있음 | 참 | `session_ended` |
| B · 음성 `end`/`confirmed` | 어댑터 이벤트 | `completed` | 있음 | 참 | `session_ended` |

두 팔의 종료 계약이 같음. `session.py` 가 *"클라이언트의 `end_session` 과 같은 길이므로 종료
상태·프레임 순서가 갈리지 않는다"* 로 적은 것과 일치함.

**AC 로는 재지 않았으나 적어 둘 관측 둘**

1. **세션 중 화면 버튼은 하나뿐임** — 브라우저에서 활성 세션의 `document.querySelectorAll('button')`
   가 `["학습 종료"]` 였음(쉐도잉 모드에서는 `클립 듣기`·`따라 읽기` 가 더해짐). 즉
   `show_report`·`next_question`·`pause`·`resume` 넷은 **음성 전용**임. ⛔ **결함으로 올리지
   않았음**: `PRD.md:80` 이 요구하는 방향은 「UI 버튼과 동일한 행동을 음성으로」(음성 ⊇ 버튼)이고
   그 반대가 아님. 또 `PRD.md:85` 의 「명령 모드 버튼」은 **명시로 기각된 결정**임 —
   `TASK-61` 이 *"① 명령 표지는 「Oh My English」 접두어 하나(명령 버튼·둘 다 기각)"* 로 적었고
   TS-33 의 시나리오 본문도 「명령 버튼 **또는** Oh My English 호출어」로 둘 중 하나를 허용함.
2. **`show_report` 는 실시간으로 동작함** — 주입 뒤 화면에 `주간 리포트` 패널과
   `아직 주간 리포트가 만들어지지 않았어요` 가 떴음. 그 패널을 여는 다른 호출자는 0곳임
   (`setReportOpen(true)` 의 유일한 호출자가 음성 명령 처리부임).

### TS-36 · A18 추가 학습 진입과 즉시 드릴 — AC#3 미확인

⛔ **세션 화면을 `?mode=…` 로 열지 않았음**(함정 `H-CC`). 쿼리 없이 `http://localhost:3000/` 로 열어
(`H-CA` — `127.0.0.1` 을 쓰지 않았음) 마이크 대체본을 먼저 심고 화면의 진입 버튼을 눌렀음.
대체본은 `tests/harness/instrument.js` 가 쓰는 것과 같은 형태임(`createMediaStreamDestination` +
220Hz 오실레이터). 대체본이 실제로 불린 것을 `__b5.gum` 계수로 확인했음(진입마다 `1`).

| AC | 판정 | 근거 |
|---|---|---|
| #1 하루 학습량을 채운 뒤에도 추가 학습을 시작할 수 있음 | ✅ | 아래 |
| #2 추가 학습 종류 가운데 최소 셋이 진입됨 | ✅ | 아래 |
| #3 자주 틀리는 패턴에서 즉시 드릴을 만드는 경로가 성립함 | ⛔ **미확인 — 기능 부재** | 아래 · `TASK-233` |

**AC#1** — 회차 시작 시 오늘(KST) 완료 세션은 **0건**이었음(teardown 뒤 같은 값으로 돌아온 것이
그 근거임). 그래서 **앱 경로로 먼저 채웠음**: TS-20 의 스텁 세션이 `completed` 로 닫히자
`GET /api/daily-summary` 가 `completed_today: true · completed_scenarios: 1` 을 냈음. **그 상태에서**
추가 학습 버튼 다섯이 모두 세션을 열었고, 결과 화면의 집계가 `시나리오 2개` → `3개` → `4개` →
`5개` → `6개` 로 늘었음. 즉 권장량 충족이 이 문을 닫지 않음(`PRD.md:73`).
⚠️ **화면에 권장량 게이트가 애초에 없음** — 대시보드의 추가 학습 절은 조건 없이 렌더됨. 그래서 이
AC 는 「게이트가 열렸다」가 아니라 「게이트가 없고 채운 뒤에도 실제로 열렸다」로 확인됨.

**AC#2** — 다섯이 진입됐음(최소 셋 요구). 다섯 모두 `learning_source=additional` · `started_via=ui` ·
발화 6행 저장 · `completed` 로 닫힘:

| 버튼 | 세션 | `mode` | job |
|---|---|---|---|
| `자유 대화` | `e7eb8948` | `speaking` | 3 |
| `약점 패턴 집중` | `7523a66f` | `speaking` | 3 |
| `질문 답변 5개` | `5eb0702e` | `scenario_intake` | **4** (`generate_scenario` 가 더 걸림) |
| `발음 집중` | `072f8489` | `pronunciation` | 3 |
| `쉐도잉` | `f2b9d9fb` | `shadowing` | 3 |

AC 문면이 든 다섯 가운데 넷이 여기 대응함 — `자유 대화` · `질문 다섯 개 더`(=`질문 답변 5개`) ·
`자주 틀리는 패턴`(=`약점 패턴 집중`) · `쉐도잉`. 다섯째 `업무 역할극` 은 **비활성**이었고
(`disabled: true` · 제목 `무대를 고르는 화면이 아직 없어요`) 그것은 설계가 정한 **빈 칸**임
(진입점 설계서 §2 — *"«비어 있는 칸»으로 둔다 … 항목을 지우면 다음 사람이 「원래 다섯이었다」로
읽는다"*). ⇒ 결함으로 올리지 않음.

⚠️ **`자유 대화` 와 `약점 패턴 집중` 의 세션 행이 서로 구별되지 않음**(둘 다 `speaking`/`additional`).
결함으로 올리지 않음 — 진입점 설계서 §2 가 *"그 셋의 차이는 지시문이 아니라 계획 데이터에 있다 …
갈라 두면 값역만 늘고 거동은 같다"* 로 그것을 의도로 적어 두었음.

**AC#3 — 미확인.** 넷을 직접 확인했음:

1. 결과 화면은 그날의 오류 패턴을 **보여 주기만** 함 — `app/frontend/app/results/[sessionId]/page.tsx:473-495`
   가 원문·교정문·이유·반복 횟수를 렌더하고 **동작이 붙은 요소가 없음**.
2. `app/frontend` 전체에서 `pattern_key` 는 **React `key` 로만** 쓰임(히트 6곳 전부).
3. 세션 생성에 패턴을 실을 자리가 없음 — `SessionEntry` 는 `mode`·`source`·`itemId` 셋뿐이고
   (`app/frontend/lib/config.ts:24-31`) `entryQuery` 가 그 셋만 쿼리로 싣음.
4. `practice_current_pattern`(아키텍처 문서가 이 요청에 배정한 tool)은 `docs/` 에만 있고
   `app/` 안 히트가 **0건**임.

⇒ 「패턴을 보는 것」까지는 되고 「그 패턴으로 즉시 드릴을 만드는 것」이 없음.
⚠️ **이것이 AC 문면의 오류가 아닌 이유**: `PRD.md:70` 이 *"사용자는 「질문 더 주세요」, 「이 패턴으로
연습 만들어줘」라고 요청해 즉시 드릴을 생성할 수 있다"* 로 글자로 요구하고,
`docs/design/2026-09-08-immediate-drill-entry-design.md` §6 과 `TASK-7` 의 노트가 그 경로(경로 A)를
**범위 밖 발견 · 소유자 없음**으로 적어 두었으며 `TASK-7` 은 `Done` 임. 즉 요구가 살아 있고 소유자만
없는 상태임 ⇒ 결함 `TASK-233` 으로 등록해 사람이 소유자를 정하게 함.

## 7. 등록한 결함

| ID | 현상 | 나온 자리 |
|---|---|---|
| `TASK-233` | 자주 틀리는 패턴을 골라 즉시 드릴을 만드는 경로가 0곳이고 소유자도 없다 | TS-36 AC#3 |
| `TASK-234` | 음성 명령으로 연 세션도 `started_via='ui'` 로 기록되어 두 진입을 가릴 수 없다 | TS-33 AC#3 관측에서 파생 |

⛔ **둘 다 고치지 않았음.** 이 회차는 관측만 했고 수정 제안은 각 결함 본문 끝에 「제안」으로 적었음.
이미 등록된 `TASK-230`·`TASK-231`·`TASK-232` 와 뿌리가 다름(각각 픽스처 세션 상태 · AC 문면과 계약의
갈림 · 무대 후보 좁힘).

## 8. 계측하지 못한 것 — 다음 배치를 위해

1. **Nova 의 `toolUse` → `SessionCommandEvent` 번역**(TS-33). 스텁에 그 경로가 없어 어댑터 대역으로
   갈아 끼웠음. 표지의 ASR 신뢰도(이전 회차가 2회 중 1회 실패로 관측한 것)도 실물이 있어야 잼.
2. **`speech_start`/`speech_end` 와 시각적 마이크 상태**. 스텁이 그 이벤트를 만들지 않아
   화면의 `listening` 표시가 한 번도 뜨지 않았음.
3. **오류 패턴 카드의 실제 렌더**(TS-36 AC#3 의 앞 절반). 분석 워커를 켜지 않았으므로
   `daily-summary` 가 `analyzed: false` 였고 패턴 목록이 빈 배열이었음 — 카드 자체는 코드로만 확인함.
4. **스크린샷**. `orca screenshot` 이 `Screenshot timed out — the browser tab may not be visible`
   으로 실패했음. 판정은 `eval` 로 읽은 DOM 텍스트와 DB 로 했으므로(스크린샷은 보조 증거) 판정에는
   영향이 없음. 페이지 본문 사본은 `evidence/32-ts33-ac3-page-text.txt` 에 있음.

## 9. 이 회차가 쓴 드라이버

| 파일 | 무엇 |
|---|---|
| `ts33_voice_command_driver.py` | 명령 여섯 + 경계 셋을 세션 8개로 흘림 |
| `ts33_end_paths_compare.py` | 버튼 프레임과 음성 `end` 를 같은 조건에서 견줌 |
| `ts33_end_button_leg.py` | `/ws/session` 에 `end_session` 만 보내는 다리 — **판별력이 없었음**(§6 AC#3 대조 ②). 지우지 않고 남기는 이유는 그 실패가 다음 회차의 값이기 때문임 |
