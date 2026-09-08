# 5차수 브라우저 다리 — `BLOCKED` (프리플라이트 P5 실패)

> 절차 정본: `tests/harness/browser_leg.md`. 회차 주체는 프론트엔드 검증자(에이전트)임.
> 리포 `/Users/redstar/MyProject/OhMyEnglish` · 브랜치 `design/first-vertical-slice` · HEAD `a82aa21`.
> 관측 일자 2026-09-09.

## 판정 요약

| 묶음 | 판정 | 근거 |
|---|---|---|
| C1 (A1-0~A1-8) | `BLOCKED` | 프리플라이트 P5 실패로 단정 평가에 넘어가지 않음 |
| C2 (A2-1~A2-3) | `BLOCKED` | 같음. 라이트·다크 두 모드 모두 미측정 |
| C3 (A3-1~A3-2) | `BLOCKED` | 같음 |
| C4 (A4-1~A4-2) | `BLOCKED` | 같음 |
| C5 (A5-1~A5-2) | `BLOCKED` | 같음 |

**단정 18건 전부 미평가임.** `browser_leg.md` §2 첫 줄이 「하나라도 어긋나면 단정 평가로
넘어가지 않는다」를 규정하므로 그것을 그대로 따랐음.

⛔ **이 `BLOCKED`는 화면 결함의 신호가 아님.** 백엔드 프로세스가 HEAD 코드를 실행하지 않고
있다는 환경 사실이고, 그 상태에서 관측한 화면은 어느 코드의 결과인지 특정할 수 없음.

## 막힌 것 — 캡틴·호출자 몫

**지금 `:8002`를 듣는 백엔드는 2026-09-06 23:59:26 에 뜬 pid 14879 이고, 그 이후 커밋 23건이
`app/backend/app/` 을 건드렸음.** `--reload` 가 없으므로 그 프로세스가 실행하는 코드는 HEAD
`a82aa21`(2026-09-09 03:40:01)의 코드가 아님. 절차 §2 는 이 경우 「소스를 고치는 것이 아니라
백엔드를 재기동한다」고 지시하지만, **검증자 역할은 프로세스 재기동을 금지함**(다른 작업이 그
프로세스를 쓰고 있을 수 있음) → 재기동 판단을 호출자에게 넘기고 멈췄음.

재기동 후 다시 부르면 회차를 열고 C1~C5 전부를 돈다. 회차를 아직 열지 않았으므로 DB 잔여물이 0임.

## 프리플라이트 P1~P9 — 아홉 건 전부 직접 돌림

| # | 판정 | 직접 돌린 출력 |
|---|---|---|
| P1 | 통과 | `{"status":"ok"}` — `version` 키 없음(StockAgent 아님) |
| P2 | 통과 | `NEXT_PUBLIC_API_BASE=http://localhost:8002` |
| P3 | 통과 | `app/frontend/.gitignore:34:.env*	app/frontend/.env.local` |
| P4 | 통과 | `postgresql@17 started         redstar ~/Library/LaunchAgents/homebrew.mxcl.postgresql@17.plist` |
| **P5** | **실패** | `P5: pid 14879 · 기동 02-03:42:34 전 · 소스 34건 → 실패 — 16건: [...]` · `AssertionError` · exit 1 |
| P6 | 통과 | `200` |
| P7 | 통과 | `2` |
| P8 | 통과 | `P8: pytest 0건` |
| P9 | 통과 | `/opt/homebrew/opt/postgresql@17/bin/psql` · `ohmyenglish` |

**P5 가 잡은 16건** (프로세스보다 새로운 백엔드 소스):
`config.py` · `audio_gateway/{session,factory,nova}.py` · `models/{analysis,scenario}.py` ·
`api/{results,ws,main}.py` · `workers/analysis_worker.py` ·
`services/{plan,recordings,sessions,pronunciation,results,review}.py`

**P5 의 판별력은 이 회차에서 실측으로 성립함** — 검사가 통과가 아니라 **실패**를 냈고, 그 실패가
독립 사실 셋과 맞음: ① `lsof -nP -iTCP:8002 -sTCP:LISTEN -t` → pid 하나(`14879`) ②
`ps -p 14879 -o lstart=` → `2026년 9월 6일 일요일 23시 59분 26초` ③
`git log --since='2026-09-06 23:59:26' -- app/backend/app/` → **커밋 23건**. 공허 통과가 아님
(검사한 소스 개수 34건을 함께 인쇄했고 0건이 아님).

**백엔드 환경변수는 회차 요구와 일치함**(`ps -p 14879 -Eww`): `VOICE_ADAPTER=stub` ·
`WORKER_ENABLED=false`. 즉 막은 것은 플래그가 아니라 **코드 판의 낡음** 하나임.

## 하지 않은 것 — 명시

- **§3 회차 개설을 하지 않았음.** `.harness/browser_run_id.txt` 를 쓰지 않았고 `harness_runs` 에
  행을 넣지 않았음. 단정 평가로 넘어가지 않는 회차가 회차 포인터를 남기면 다음 회차의
  teardown 범위가 흐려짐.
- **브라우저를 한 번도 열지 않았음.** 그래서 `use_browser` 자동 저장 산출물(`.png`·`.html`·
  `-console.txt`)이 이 회차에는 **0건**임. 스크린샷 `md5` 대조도 대상이 없어 미실시임.
- **백엔드·프론트를 건드리지 않았음.** 재기동·종료 0회. `app/backend/.env` 를 열지 않았음.
- **`pytest` 를 돌리지 않았음**(P8 이 그것을 검사하고 통과했음).
- **앱 코드·`tests/harness/**`·절차 문서를 수정하지 않았음.**

## DB — 읽기 전용 관측만. 잔여물 0

회차를 열지 않았으므로 **파괴적 조작이 0회**이고 teardown 이 필요 없음. 대신 다음 회차가 회차를
열 수 있는 상태인지를 §8-0 의 drift 검사로 확인했음(읽기 전용).

| 관측 | 값 |
|---|---|
| `harness_pattern_baseline` 존재 | `t` |
| **drift** (§8-0 · 0 이어야 함) | **0** — 앞 회차 teardown 이 정상 종료했음 |
| baseline 행 수 | 8 |
| 시드 사용자 `error_patterns` | 8 — baseline 과 일치 |

**§9 보존 세션 5개 전부 생존함** (`select count(*) ... where id in (5개)` → **5**):

| # | `session_id` | `learning_sessions.status` |
|---|---|---|
| C3b | `6225ddaf-90a8-43af-9aa8-e003921c75eb` | `completed` |
| C3a | `210233be-ecaa-4409-a1af-8b7016cfe7e9` | `completed` |
| C3c | `b2f0d169-3d90-431b-b842-cce21125052a` | `completed` |
| C3e | `d127dece-d1d1-4329-802d-9b8fd1067388` | `completed` |
| C3d | `76d9ef31-0d1b-4c50-b906-f16ee438080e` | `failed` |

시드 사용자 기준 현재 행 수 — `learning_sessions` 12 · `utterances` 114 · `analysis_jobs` 45 ·
`session_plans` 1 · `learner_notes` 1. ⚠️ **이 값을 다음 회차의 baseline 으로 베껴 쓰지 말 것** —
§10 이 「수치는 그 회차에 직접 돌린 출력만」을 요구하므로 다음 회차가 자기 시점에 다시 떠야 함.

## 절차 문서의 결함 1건 — 고치지 않고 보고함

**`browser_leg.md` §2 의 P5 실패 대응과 §8-⑤ 예외가 서로 어긋남.**

§2 는 「P5 가 실패하면 백엔드를 재기동한다」고 **회차 주체에게** 지시함. 그런데 같은 문서 §8-⑤ 의
예외(T5a D-5)는 이미 「백엔드를 호출자가 세웠으면 손대지 않고 **무변경을 증거로 보고한다**」를
인정하고 있음. 두 규약을 함께 적용하면 **호출자가 세운 백엔드가 낡았을 때 회차 주체가 할 수 있는
일이 문서 안에 없음** — 재기동은 §8-⑤ 가 금지한 「남의 세션이 세운 환경을 덮어쓰기」이고, 그대로
진행하는 것은 §2 가 금지함. 이 회차가 정확히 그 자리에 걸렸음.

**이것은 거짓 통과를 내는 결함이 아니라 절차 불능임.** 정직하게 그렇게 적음 — P5 자체는 제 몫을
했고(실패를 냈고 그 실패가 옳음) 뚫린 것이 아님. 필요한 것은 §2 에 **「백엔드가 호출자 소유이면
재기동하지 말고 `BLOCKED` 로 보고하고 멈춘다」**는 갈래를 넣는 것으로 보이나, **문서 수정은 하지
않았음** — 호출자가 판단할 몫임.

## 내가 확인하지 못한 것

- **단정 18건 전부.** 브라우저를 열지 않았으므로 C1~C5 의 어느 값도 관측하지 않았음.
- **C2 의 라이트·다크 두 모드.** `c2_render_hierarchy.py` 를 돌리지 않았음 → A2-3 은 미평가이고
  그것은 `PASS` 가 아님(§5 C2 표·§10).
- **음성 대조가 FAIL 을 내는지.** 어느 대조도 실행하지 않았음 → 이 회차는 어떤 단정도
  `PASS` 로 올리지 않음.
- **프론트엔드 소스와 실행 중 dev 서버의 일치.** 프리플라이트에 프론트용 P5 대응 항목이 없어
  재지 않았음(HMR 이 있는 dev 서버이므로 백엔드와 같은 부류의 위험은 아니라고 보나 **관측한
  것은 아님**).

## 호출자가 이 판정을 재현하는 방법

**P5 하나만 다시 돌리면 됨** — `browser_leg.md` §2 의 파이썬 덩이를 리포 루트에서 그대로 실행함
(`python3 - <<'PY' … PY`). 지금 상태에서 `실패 — 16건`과
`AssertionError`·exit 1 이 나옴. 백엔드를 재기동하면 같은 명령이 `통과`로 뒤집힘 — 그것이
이 `BLOCKED` 가 환경 사실이고 화면 판정이 아니라는 증거임.

보조 대조 셋(전부 읽기 전용):
`lsof -nP -iTCP:8002 -sTCP:LISTEN -t` · `ps -p <pid> -o lstart=,etime=` ·
`git log --oneline --since='<그 lstart>' -- app/backend/app/`.

DB 쪽은 `cd app/backend && .venv/bin/python -c "import sys; sys.path.insert(0,'../../tests/harness'); from psql_cli import psql; print(psql('<질의>'))"` 형태로 위 표의 질의를 그대로 다시 던지면 됨
(§7 규약 — `podman exec` 를 쓰지 않음).

## 재기동하는 주체에게 — 보존 세션을 파괴할 수 있는 조건 1개

⛔ **재기동 시 `WORKER_ENABLED=false` 를 반드시 함께 준다.** 절차 문서 §2 기동 명령의 **미커밋
작업본**이 그것을 새로 못 박아 뒀음(`git diff tests/harness/browser_leg.md` — 커밋본에는 없고
디스크 판에만 있음. 함정 `H-AS`): `config.py` 기본값이 `worker_enabled: bool = True` 이고 `.env` 에
그 키가 없으므로 **빼고 띄우면 워커가 켜지고 §9 보존 세션 C3a·C3e 가 파괴됨.**

현재 pid 14879 는 `VOICE_ADAPTER=stub` · `WORKER_ENABLED=false` 로 떠 있음(`ps -Eww` 로 확인) →
**재기동 후 같은 두 값이 되는지 `ps -p <새 pid> -Eww` 로 대조한 뒤** 이 다리를 다시 부를 것을 권함.

⚠️ **이 회차가 읽은 절차는 커밋본이 아니라 디스크 작업본임**(`browser_leg.md` 가 `M` 상태였음).
같은 시각 `docs/ops/pitfalls.md` · `tests/harness/README.md` · `runs/ROUNDS.md` 도 `M` 이었고
**이 회차는 그 넷 중 어느 것도 수정하지 않았음** — 다른 세션의 진행 중 작업으로 보임.

---

# 2차 시도 — 프리플라이트 통과 후 회차를 열어 C1~C5 전부 관측함

> 팀리드가 백엔드를 재기동해 P5 를 풀었음(pid 14879 → **26253**). HEAD **`5dd4fb8`**
> (1차 시도의 `a82aa21` 뒤에 문서 커밋 3건이 붙었음 — `browser_leg.md` 를 다시 읽고 시작했음).
> 회차 `run_id` **`8bc59725-7246-4957-b07d-ad66f9718d07`** · `WINDOW_START`
> **`2026-09-08 18:53:53.937015+00`**(UTC · KST 2026-09-09 03:53).

## 판정 요약 — 단정 18건

| 묶음 | 판정 | 한 줄 근거 |
|---|---|---|
| **C1** | **부분** — `PASS` 2건 · `BLOCKED` 7건 | 측정값은 A1-0~A1-6·A1-8 전부 기대와 일치했으나, 음성 대조가 **어댑터 전환(백엔드 재기동)** 을 요구하는 6건을 회차가 평가할 수 없었음 |
| **C2** | **`BLOCKED`** 3건 | 실행체가 「어댑터가 `stub_unresponsive` 가 아니다」로 진단하고 exit 1 을 냈음. 라이트에서 막혀 다크는 돌지 못했음 |
| **C3** | **`PASS`** 2건 | 실행체 `c3_results_screen.py` 가 **단정 57건 전건 통과**·exit 0 |
| **C4** | `PASS` 1건 · `BLOCKED` 1건 | A4-1 통과. A4-2 는 교정 2건 이상 세션이 없어 기대값 교차 대조 **미평가**(§11-9 가 예견한 그대로) |
| **C5** | **`BLOCKED`** 2건 | 세션이 `active` 에 머물지 않아 배지를 렌더할 화면이 없었음. 주입 4건은 오류 없이 들어갔고 배지는 0개 |

| # | 판정 | 기대 · 유도 | 관측 | 음성 대조가 FAIL 을 냈는가 |
|---|---|---|---|---|
| A1-0 | **`PASS`** | 1개 — ⓑ `next-plan` API 의 `reason` 이 null 아님 | 1개 | **예** — 클릭 후 **0개**(1 → 0 전이를 직접 관측) |
| A1-1 | `BLOCKED` | 6 — ⓐ | **6** | 아님 — `stub_unresponsive` 필요 |
| A1-2 | `BLOCKED` | 6 — ⓐ | **6** | 아님 — 같음 |
| A1-3 | `BLOCKED` | 3 — ⓐ | **3** | 아님 — 같음 |
| A1-4 | `BLOCKED` | 3 — ⓐ | **3** · `when`=[0,0.2,0.4] · `afterRecvAudio`=1/2/3 | 대조 ②③은 이 데이터에서 판별 조건으로 성립. 대조 ①은 어댑터 필요 → 미평가 |
| A1-5 | **`PASS`** | 6줄 · 내용 등호 — ⓐ | **`verdict: "PASS"`** (계측 값을 그대로 베낌) | **예** — 무력화 4종이 실제로 FAIL: 순서뒤바뀜·sentinel → `APP_CONTENT_MISMATCH` · 5줄축약 → `APP_EXCESS_RENDER` · `[]`·null·비배열 → 이름 있는 throw |
| A1-6 | `BLOCKED` | `/results/<session_id>` — ⓑ | `/results/0f2a66fc-…`(DB 행과 일치) | 아님 + **유도 경로가 없음**(아래 결함 2) |
| A1-7 | `BLOCKED` | `sent.audio > 0` · data 비지 않음 — ⓑ | audio **1** · bytes **1368** | 아님 — §10 갈래 2(세션이 너무 짧다) |
| A1-8 | `BLOCKED` | 6행 — ⓐ | **6행**(내용도 픽스처와 일치) | 아님 — `stub_unresponsive` 필요 |
| A2-1 | `BLOCKED` | ⓑ probe 유도 muted | 미측정 | 미평가 |
| A2-2 | `BLOCKED` | ⓑ probe 유도 foreground | 미측정 | 미평가 |
| A2-3 | `BLOCKED` | 라이트 muted ≠ 다크 muted — ⓑ | 미측정 (두 모드 **모두**) | 미평가 |
| A3-1 | **`PASS`** | ⓒ `STATUS_LABEL` · 요소 지목 + 등호 | 분석 중 / 확정 / 부분 실패 / 연결 실패 / 분석 대상 없음 | **예** — 같은 요소가 5상태 재방문에서 매번 다른 라벨 |
| A3-2 | **`PASS`** | ⓑ 없는 uuid → 라벨 5개 부재 + 오류 문구 | `결과 API가 404을 반환했습니다` · 라벨 잔존 `[]` | **예** — 실제 세션에서 그 오류 문구 부재(상호 대조) |
| A4-1 | **`PASS`** | N=1 — ⓑ API `corrections.length` | 원문/교정문 1/1 · 카드 1 · `pCount` 3 · 셋째 줄 비지 않음 | **예** — 빈 세션 2건에서 두 접두 **0개** |
| A4-2 | `BLOCKED` | ⓑ 카드별 `reason` 등호 | 등호 통과(카드 셋째 `<p>` == API `reason`) | 아님 — 교정 1건이라 기대값 교차 **평가 불가**(실행체가 「미확인」으로 냈고 PASS 로 세지 않았음) |
| A5-1 | `BLOCKED` | ⓒ `PRONUNCIATION_BADGE` · 요소 1개 + 등호 | 배지 **0개**(4 outcome 전부) | 대조 ①(주입 전 부재)만 성립. 본 단정 미측정 |
| A5-2 | `BLOCKED` | ⓑ sentinel 0건 | sentinel 0건 **이지만** outcome 문구도 0건 | **아님** — §5 A5-2 가 「둘 다 0이면 주입 실패」로 이 경우를 배제함 |

## 프리플라이트 P1~P9 — 아홉 건 전부 다시 돌려 전건 통과

| # | 판정 | 직접 돌린 출력 |
|---|---|---|
| P1 | 통과 | `{"status":"ok"}` (`version` 없음) |
| P2 | 통과 | `NEXT_PUBLIC_API_BASE=http://localhost:8002` |
| P3 | 통과 | `app/frontend/.gitignore:34:.env*	app/frontend/.env.local` |
| P4 | 통과 | `postgresql@17 started` |
| **P5** | **통과** | **`P5: pid 26253 · 기동 03:36 전 · 소스 34건 → 통과`** · exit 0 |
| P6 | 통과 | `200` |
| P7 | 통과 | `2` |
| P8 | 통과 | `P8: pytest 0건` |
| P9 | 통과 | `/opt/homebrew/opt/postgresql@17/bin/psql` · `ohmyenglish` |

백엔드 플래그를 프로세스에서 직접 확인했음(`ps -p 26253 -Eww`): `WORKER_ENABLED=false` ·
`VOICE_ADAPTER=stub`. 회차 중 워커를 켜지 않았고 실물 호출은 **0회**임.

## §4 계측 자기검사 — 통과. 손으로 옮기지 않았음

**계측을 eval 페이로드로 옮겨 적지 않았음** — §10-3 규약대로 임시 CORS 서버(`127.0.0.1:8899`,
`tests/harness/` 서빙, 회차 끝에 종료)로 페이지가 파일을 그대로 받아 페이지 안에서 sha256 을
계산해 대조했음. **전사 드리프트가 구조적으로 0임.**

| 검사 | 관측 |
|---|---|
| `eval` 반환값 | **`"instrumented"`** (§4-1) |
| sha256 (페이지 계산) | **`846f130f2cf73365ae00765b37300e00e3c1c5b1cb1ae6152f9a02b7fc16ae93`** · 43,119 B |
| 파일 해시 (`shasum -a 256`) | 같은 값 — 일치 |
| 후킹 소유자 (§11-2 재확인) | `onmessage`=**WebSocket** · `send`=**WebSocket** · `start`=**AudioBufferSourceNode** · `createBufferSource`=**BaseAudioContext** |
| 필수 키 8건 | `recv`·`sent`·`started`·`snapshots`·`finalLinesAtTerminal`·`judgeFinalLines`·`inject`·`probeColor` 전부 존재 |
| `finalLines`(있으면 낡음) | **ABSENT** — §4 의 정정대로 요구하지 않았음 |
| `judgeFinalLines` 반환 키 | `verdict`·`judgeable`·`reachedExpected`·`terminalIsPrefix`·`exactStateSeen`·`noExcess`·`terminalMatches`·`nonDecreasing`·`atMaxDiagnostic` 전부 존재 |

⚠️ **`judgeFinalLines` 가 순수 함수임을 확인했음** — 같은 `expected` 로 두 번 불러 반환이 동일했음.
그것이 없으면 뒤이은 무력화 호출이 앞 호출의 상태를 오염시켰을 수 있음.

## C1 — 세션 두 번 관통. 같은 값을 재현했음

**세션 2건을 각각 새 문서에서 돌렸음**(§5 A1-5 의 「한 문서에 세션 하나」 규약).
① 톤(`silentMic:false`) → `0f2a66fc-427a-416d-825e-51cb394c2f7e`
② 무음(`silentMic:true`) → `431f25f3-f6f8-4d70-8ddb-a6bb6294ae31`

두 회차가 **`recv`·`started`·`finalLinesAtTerminal` 을 완전히 재현했음**:
`recv={session_started:1, partial:6, final:6, audio:3, session_ended:1, session_failed:0}` ·
`started={count:3, when:[0,0.2,0.4]}` · 종단 6줄이 픽스처와 축자 일치.

**A1-4 의 대조 ②③이 이 데이터에서 실제 판별 조건으로 작동했음**: `when` 이 [0, 0.2, 0.4] 로
비감소이고 첫째(0) < 셋째(0.4) — 세 값이 같으면 어긋났을 것임. `afterRecvAudio` 태그가 1/2/3 으로
갈려 **어느 수신 프레임에서 났는지**가 확정됨. 다만 대조 ①(어댑터 전환 → 0)은 평가하지 못했음.

**A1-8 은 행 수와 내용을 함께 확인했음** — `utterances` **6행**이고 `sequence_no` 1~6 이
`agent`/`user` 교대로 픽스처 문장을 담았음. partial 12건은 저장되지 않았음(6행이 그 증거임).

### A1-5 — `PASS`. 판별력을 이 회차에서 실측했음

기대값은 `fixtures.py:FIXTURE_TURNS` 3턴에서 연역했음(ⓐ). 계측이 낸 값을 **해석하지 않고 베낌**:
`verdict: "PASS"` · `maxCount 6` · `expectedCount 6` · `noExcess true` · `reachedExpected true` ·
`terminalMatches true` · `nonDecreasing true` · `judgeable true` · `terminalIsPrefix false` ·
`snapshotCount 11` · `snapshotCounts=[0,1,2,2,3,4,4,5,6,6,0]`.

**무력화 입력 6종을 같은 회차 데이터에 얹어 FAIL 을 실제로 관측했음**(앱 소스를 고치지 않고
기대값만 바꿨음):

| 무력화 | 결과 |
|---|---|
| 1·3번째 줄 순서 뒤바꿈 | `terminalMatches false` → **`APP_CONTENT_MISMATCH`** |
| 마지막 줄에 sentinel 덧붙임 | `terminalMatches false` → **`APP_CONTENT_MISMATCH`** |
| 5줄로 축약 | `noExcess false` → **`APP_EXCESS_RENDER`** |
| `expected = []` | **throw** — `expected 가 비었다 — 빈 기대값은 공허 통과다 (A1-5)` |
| `expected = null` · `"nope"` | **throw** — `expected 가 배열이 아니다` |

⚠️ **§5 의 정정 2가 이 회차에서 재현됐음** — `atMaxDiagnostic.texts` 의 마지막 줄이
**`답변: I need to finish`**(partial)였음. 이전 판정식(최대 지점의 `texts` 를 본다)이면 **정상
회차가 FAIL** 이었을 것임. 지금 판정은 종단 동기 스냅샷을 보므로 영향받지 않았음.

또 A1-5 ④를 재확인했음: 기대 문장 6개 길이 `[38,35,39,37,35,41]` — 전부 20자 이상이고
sentinel 변형이 DOM 의 어떤 `<p>` 와도 같지 않았음(0건).

### A1-7 — `BLOCKED`. §10 갈래 2 에 정확히 걸렸음

| 회차 | `sent.audio` | `sentAudioBytes` | `sentAudioNonZeroFrames` | `sent.end_session` |
|---|--:|--:|--:|--:|
| 톤 (`silentMic:false`) | **1** | 1368 | **0** | 0 |
| 무음 (`silentMic:true`) | **0** | 0 | 0 | 0 |

**후킹은 살아 있음**(§10 갈래 1): 톤 회차 `sent.foreign=1` · `socketUrls` 에
`ws://localhost:8002/ws/session` 실재. 무음 회차도 `foreign=1`·`appHandlerAttached=true`.
**갈래 2 가 성립함**: `recv.session_started === 1` 인데 `sent.audio` 가 0~1 로 흔들림 →
**세션이 너무 짧음**(캡처 프레임 1건 = 512샘플@16kHz = 32 ms). 화면 결함이 아니므로 `BLOCKED` 임.

**대조 ① `end_session` 1건은 구조적으로 평가 불가임** — 스텁 세션이 스스로 종료해
`학습 종료` 버튼에 도달할 수 없음(두 회차 모두 클릭 후 결과 화면으로 이동했음).

⚠️ **§11-4 의 미결이 닫히지 않았고 반대 방향의 새 사실이 늘었음** — 대조 ③은 *"`silentMic=true`
에서 `audio > 0` 이면서 `nonZeroFrames === 0`, 톤에서는 둘이 같다"* 를 요구하는데 이 회차는
**무음에서 `audio` 가 0**(전제 불성립)이고 **톤에서 `nonZeroFrames` 가 0**(요구 불성립)이었음.
즉 대조 ③도 세션 길이에 걸림. `oscillator` 는 계측 시점에 `start()` 되지만 컨텍스트가 그때
`suspended` 였으므로(관측: `audioContextState` 가 클릭 전 `suspended` → 후 `running`) 첫 32 ms 가
램프업 구간일 가능성이 있으나 **이 회차 데이터로는 그것과 「톤 경로 고장」을 가르지 못했음.**

## C2 — `BLOCKED` 3건. 실행체가 원인을 정확히 지목했음

`cd app/backend && .venv/bin/python ../../tests/harness/c2_render_hierarchy.py` (기본
`--schemes light,dark --phase both`) → **exit 1**. 라이트에서 막혀 다크는 돌지 못했으므로
**두 모드 모두 미측정**이고 A2-3 은 그래서 미평가임.

```
=== light ===
페이지 예외: Error: 시간초과(3000ms): partial 줄 렌더
판별: 세션이 이미 **정상 종료**했다(`session_ended`) → … 주입 회차라면
      **어댑터가 `stub_unresponsive` 가 아니다** (§6 주입 창은 그 모드에서만 열린다).
      `recv.partial`·`recv.final` 이 0이 아닌 것이 증거다
```

진단 근거가 모두 살아 있었음: `socketUrls` 2건 · `resumeLog` 2건 ·
`appHandlerAttached=True` · `userActivation={hasBeenActive:True, isActive:True}` ·
`recv={session_started:1, partial:6, final:6, audio:3, session_ended:1}` ·
`contextState={state:running, currentTime:3.05}`. 즉 `H-AE`(배경 탭·클릭 미도달)도
`H-AH`(후킹 고장)도 **아님** — 어댑터 하나가 원인임. `classify_failure` 의 판별력이 이 회차에서
실물로 확인됐음.

## C5 — `BLOCKED` 2건. 주입은 됐고 화면이 없었음

§6 ⛔ 대로 **클릭·주입·판독을 한 `eval` 에** 넣었음(합성 클릭 → active 대기 → 4 outcome 순차
주입 → 판독). 합성 클릭이 세션을 실제로 열었음(`appHandlerAttached=true` · `recv` 전건 정상 ·
`session_ended 1`) — 그러나 **`activeReached: false`**(4,003 ms 대기 후에도 `학습 종료` 버튼 부재)
였고 판독 시점의 `main` 이 `<h1>학습 결과</h1>` 였음. 즉 **세션이 이미 결과 화면으로 넘어가
배지를 렌더할 컨테이너가 언마운트됐음**(`page.tsx` 가 그 컨테이너를 `active`/`ending` 으로 가둠).

주입 4건은 **오류 없이 들어갔음**(`injected: 4` · `injectErr: null` 전건) 그리고
**`recv` 를 오염시키지 않았음**(주입 후에도 `recv` 에 `pronunciation` 키가 없음) — `inject()` 의
설계 주장이 이 회차에서도 유지됐음. 배지는 4회 모두 **0개**.

A5-1 의 대조 ①(주입 전 배지 부재)은 성립했음(`badgeBeforeClick: 0` · `badgeAtActive: 0`).
A5-2 는 sentinel `ZZ_TARGET_SOUND_SENTINEL_9931` 이 DOM 0건이었으나 **outcome 문구도 0건**이라
§5 A5-2 의 대조 규정(둘 다 0이면 주입 실패)에 따라 **평가 불가**임.

## C3·C4 — 실행체가 단정 57건 전건 통과. exit 0

`c3_results_screen.py` 를 §9 의 보존 세션 5개로 돌렸음(세션을 **새로 만들지 않았음** — 재방문).

```
세션 5건 · API 상태: analyzing=analyzing · final=final · partial_failure=partial_failure
                     · connection_failed=connection_failed · no_utterances=no_utterances
  analyzing          첫 직계 <p> = '분석 중'      · 원문/교정문 = 0/0 · 카드 0
  final              첫 직계 <p> = '확정'        · 원문/교정문 = 1/1 · 카드 1
  partial_failure    첫 직계 <p> = '부분 실패'    · 원문/교정문 = 0/0 · 카드 0
  connection_failed  첫 직계 <p> = '연결 실패'    · 원문/교정문 = 0/0 · 카드 0
  no_utterances      첫 직계 <p> = '분석 대상 없음' · 원문/교정문 = 0/0 · 카드 0
  missing-uuid       첫 직계 <p> = '결과 API가 404을 반환했습니다' · 라벨 잔존 []
--- 판정 (단정 57건 검사) ---
  미확인   A4-2 기대값 교차 대조: 교정 **2건 이상**인 세션이 없어 평가할 수 없다 → 판별력 미확인
  PASS  57건 전건 통과 · 미확인 1건은 통과로 세지 않았다
```

**A3-1 의 음성 대조가 실제로 성립했음** — 같은 요소(`main` 첫 직계 `<p>`)의 `textContent` 가
5상태 재방문에서 **매번 다른 라벨**로 바뀌었음. 상수를 렌더하고 있으면 바뀌지 않았을 것임.

**A4-1·A4-2 의 근거를 raw 증거에서 직접 읽었음**(`.harness/evidence/c3-results-screen.json`):
API `corrections` 1건(`original_span: "go to gym"` · `correction: "go to the gym"` ·
`reason: "gym처럼 늘 다니는 장소를 …"`)이고 DOM 카드가 `pCount: 3` ·
`strongs: ["원문:","교정문:",null]` 이며 라벨 없는 셋째 `<p>` 가 그 `reason` 과 **문자열 등호**로
일치했음(비어 있지 않음). **`c3-final.png` 를 직접 열어 눈으로 확인했음** — 다크 배경에 `확정`
라벨과 교정 카드 1개가 렌더되고 이유 줄이 muted 로 나왔음.

## DB — 3열 대조 (§10 규약)

| 표 | baseline | 회차 후 | teardown 후 |
|---|--:|--:|--:|
| `learning_sessions` (시드 사용자) | 12 | **16** | **12** |
| `analysis_jobs` | 45 | **61** | **45** |
| `utterances` | 114 | **138** | **114** |
| `error_patterns` (시드 사용자) | 8 | 8 | 8 |
| `session_plans` | 1 | 1 | 1 |
| `learner_notes` | 1 | 1 | 1 |

세션 4건 × (utterances 6 + jobs 4) = 24·16 이 그대로 늘고 그대로 걷혔음. `error_patterns` 는
회차 중 **한 번도 바뀌지 않았음**(워커가 꺼져 있어 분석이 돌지 않았음 → drift 0).

**회차가 만든 세션 4건** (전부 `harness_sessions` 에 `run_id` 로 등록한 뒤 삭제):
`0f2a66fc-…`(C1 톤) · `431f25f3-…`(C1 무음) · `93dbe6cd-…`(C2 실행체) · `c1e3075c-…`(C5 시도).

### teardown — drift 0 · 보존 5건 생존

| 단계 | 출력 |
|---|---|
| §8-0 drift (회차 **전**) | **0** → 재스냅샷 진행. baseline **8행** |
| ①-a 스윕 등록 | `INSERT 0 4` |
| ① 세션 삭제 | `DELETE 4` (보존 5개는 `not in` 으로 제외) |
| ② `frequency`·`last_seen_at` 복원 | `UPDATE 0` — 바뀐 값이 없었으므로 만질 행이 없음(**재계산하지 않았음**) |
| ③ baseline 밖 0-occurrence 패턴 삭제 | `DELETE 0` |
| ④-1 `error_patterns` 행 수 | **8** = baseline 8 |
| ④-2 **drift** | **0** |
| ④-3 이 회차 등록 세션 중 생존 | **0** |
| 보존 세션 5개 | **5 생존** |

**보존 세션 5개가 회차 전후로 온전함을 job 단위까지 확인했음**:
C3a `analyze_utterance:pending×3` · C3b `done×1` · C3c `done×2,failed×1` ·
C3d `analyze_utterance 0건`(utterances 0) · C3e `analyze_utterance 0건`. 팀리드가 재기동 전후로
보고한 값과 **일치함.**

⚠️ **내 첫 집계 쿼리가 틀렸고 그것을 정정했음** — `analysis_jobs` 를 `session_id` 로만 조인하면
`analyze_utterance` 가 전부 빠짐(그 job 의 `session_id` 는 **NULL** 이고 `utterance_id` 로 연결됨 —
직접 확인: `analyze_utterance` 40건 전건 `session_id is null`). 첫 출력이 「C3b job 0건」처럼 보여
팀리드 보고와 어긋났으나 **쿼리 결함이었고 데이터는 온전했음.** 다음 회차가 같은 함정을 밟지
않도록 적어 둠: **보존 세션 무결성 확인은 `utterances` 경유 조인을 함께 해야 함.**

### ⑤ 프로세스·환경 — §8-⑤ 예외 적용(무변경)

백엔드를 호출자(팀리드)가 세웠으므로 **손대지 않았음.** 증거 3개:
`lsof -nP -iTCP:8002 -sTCP:LISTEN -t` → **26253**(회차 시작과 같음) ·
`ps -p 26253 -Eww` → `WORKER_ENABLED=false`·`VOICE_ADAPTER=stub`(회차 시작과 같음) ·
`/health` → `{"status":"ok"}`. **`app/backend/.env` 를 열지 않았음.**
회차가 띄운 임시 CORS 서버(`127.0.0.1:8899`)는 종료하고 `/tmp` 의 스크립트·로그를 지웠음
(재확인: 8899 응답 `000`).

## 증거 파일 — 이 회차가 만든 것만. md5 로 서로 다름을 확인함

`.harness/evidence/` (타임스탬프 `09-09 04:02`):

| 파일 | md5 |
|---|---|
| `c2-light-failure.png` | `e597fcd079fc754bf1385b1f1f30d2e4` |
| `c2-light-failure.json` | (계측 덤프 1.4 kB) |
| `c3-analyzing.png` | `b26969b71905a56f483fd65f23408a7a` |
| `c3-final.png` | `e91117203e7f9aaee5d5fa4c543535f6` |
| `c3-partial_failure.png` | `bc72f78587511a065b58acb677a5bd1b` |
| `c3-connection_failed.png` | `b8d86abcfb786275dd828d8ee2cd9a53` |
| `c3-no_utterances.png` | `1544fd0d1f420438c184302dcf06d359` |
| `c3-missing.png` | `631d043a8bcad9b81b68b2d8b3906a6b` |
| `c3-results-screen.json` | (API·DOM raw 7.2 kB) |

**7장 전부 서로 다른 해시임** — 「같은 캡처를 두 이름으로 저장」이 아님을 이 값으로 배제함.

⚠️ **이 회차 밖에서 바이트 동일 3건을 발견했음(고치지 않고 적어 둠)**: `c2-dark.png`(09-06 23:58) ·
`c2-selftest-failure.png`(09-06 22:41) · `c2-selftest2-failure.png`(09-06 22:42)가 md5
`b2c5daa57c8fceb46eeedd30f4a137fa` 로 **셋 다 같음.** 4차수의 그 사고와 같은 부류로 보이나
**이 회차가 만든 파일이 아니므로 원인을 조사하지 않았음.**

`use_browser` 자동 저장분: `~/Library/Caches/superpowers/browser/2026-09-08/session-1788871212847/`
의 `001`~`012`(`.png`·`.html`·`.md`·`-console.txt`). ⚠️ **§10 이 이미 규정한 대로 창 안 관측의
증거로 쓰지 않았음** — 판정 근거는 전부 `eval` 반환 JSON 이고 그것을 이 기록에 옮겼음.
`-console.txt` 는 이 회차에서도 **빈 스텁**이었음(내용 미구현).

## 절차 문서의 결함 — 신규 2건. 고치지 않고 보고함

**결함 1 — 한 회차로 C1 과 C2·C5 를 동시에 판정할 수 없음. 그 사실이 절차에 적혀 있지 않음.**
§5 C1 의 음성 대조 6건(A1-1·A1-2·A1-3·A1-4①·A1-6·A1-8)은 `VOICE_ADAPTER=stub_unresponsive` 를
요구하고, §6 의 주입 창(C2·C5)도 같은 모드를 요구함. 그런데 **A1-4 본 단정은 `stub` 에서만
측정 가능**하다고 §5 가 못 박음. 어댑터는 프로세스 환경변수이고 CORS 가 `:3000` 하드코딩이라
두 번째 백엔드를 띄울 수 없음 → **두 모드는 재기동으로만 갈림.** 그리고 2026-09-09 커밋
`5dd4fb8` 이 재기동 주체를 **호출자**로 정했으므로, 검증자가 한 번 불려서 낼 수 있는 최대치는
**어느 한 모드의 단정뿐**임. 이 회차가 그 자리에 걸려 `BLOCKED` 12건을 냈음.
→ 필요한 것은 §5·§6 에 **「모드가 갈리는 두 묶음이고 회차를 둘로 나눈다」**를 명시하고 브리프가
모드를 지정하는 것으로 보임. **문서를 고치지 않았음** — 호출자 판단 몫임.

**결함 2 — A1-6 의 유도 방식이 계측에 없음.** §5 A1-6 은 기대값을 *"ⓑ `session_started` 프레임의
`session_id` 를 **계측이 기록해** 대조"* 로 정의하는데 **`instrument.js` 에 그 기록이 없음**
(`grep -n 'session_id\|sessionId' instrument.js` → 주석 1줄뿐. §4 의 필수 키 목록에도 없음).
그래서 이 회차는 URL 의 uuid 를 **DB 세션 행과** 대조했음(상류라 순환은 아니나 문서가 지정한
경로가 아님). **문서가 요구하는 대조를 계측이 제공하지 않으므로 A1-6 은 지금 형태로는
누가 돌려도 그대로 잴 수 없음.**

## 내가 확인하지 못한 것

- **C2 의 색 위계 전부**(A2-1·A2-2·A2-3). probe 유도값을 **한 번도 읽지 못했음** — 라이트·다크
  두 모드 모두 미측정이고 A2-3 은 그래서 미평가임(§10: 미평가는 `PASS` 가 아님).
- **A5-1 의 배지 문구 등호**(4 outcome). 배지 요소를 한 번도 렌더시키지 못했음.
- **A1-7 의 대조 ①③.** 위 A1-7 절에 이유를 적었음. §11-4 는 여전히 열려 있음.
- **A4-2 의 기대값 교차 대조.** 교정 2건 이상 세션이 없음 — §11-9 가 「캡틴 결정 사안」으로
  남긴 그대로임. 실행체가 「미확인」으로 냈고 통과로 세지 않았음.
- **A1-4 의 대조 ①**(어댑터 전환 → 0).
- **바이트 동일 스크린샷 3건의 원인**(이 회차 밖 파일이라 조사하지 않았음).
- **프론트 dev 서버가 HEAD 소스를 실행하는지.** 프리플라이트에 프론트용 대응 항목이 없어
  재지 않았음(HMR 이 있어 백엔드와 같은 부류의 위험은 아니라고 보나 **관측한 것은 아님**).

## 호출자가 재현하는 방법 — 무엇을 어떤 선택자로 쟀는가

**가장 싼 재현은 C3·C4 임**(어댑터 무관 · 세션을 만들지 않음 · 실물 호출 0회):

```bash
cd app/backend && .venv/bin/python ../../tests/harness/c3_results_screen.py \
  --session analyzing=210233be-ecaa-4409-a1af-8b7016cfe7e9 \
  --session final=6225ddaf-90a8-43af-9aa8-e003921c75eb \
  --session partial_failure=b2f0d169-3d90-431b-b842-cce21125052a \
  --session connection_failed=76d9ef31-0d1b-4c50-b906-f16ee438080e \
  --session no_utterances=d127dece-d1d1-4329-802d-9b8fd1067388
```
→ `단정 57건 검사` · `PASS 57건 전건 통과` · exit 0. raw 는 `.harness/evidence/c3-results-screen.json`.

**C2 의 `BLOCKED` 재현**: `cd app/backend && .venv/bin/python ../../tests/harness/c2_render_hierarchy.py`
→ exit 1 · `판별: … 어댑터가 stub_unresponsive 가 아니다`. 어댑터를 바꾸면 뒤집힘 — 그것이 이
`BLOCKED` 가 환경 사실이고 화면 결함이 아니라는 증거임.

**C1 재현** — 브라우저 액션 4개:
① `navigate http://localhost:3000/`
② `eval` 로 `fetch('http://127.0.0.1:8899/instrument.js')` → 페이지 안 sha256 대조 → `eval(text)`
  (임시 CORS 서버: `python3 -m http.server` 에 `Access-Control-Allow-Origin: *` 를 얹어
  `tests/harness/` 를 서빙. **파일 내용을 페이로드로 옮겨 적지 않음**)
③ `click` **selector `button`** (CDP 클릭이어야 함 — 합성 클릭도 세션은 열리나 `H-AE` 위험)
④ `eval` 로 `window.__omy` 판독.

**선택자 정본** — 이 회차가 쓴 것 그대로:
- 확정/partial 줄: `p` 중 `querySelector('strong').textContent` 가 `"질문: "`·`"답변: "` 인 것
  (**색으로 고르지 않음** — §6)
- A1-0: `p` 중 `textContent.startsWith("오늘 이걸 연습해요:")` (`page.tsx:NEXT_PLAN_PREFIX`)
- 배지: `p[aria-live="polite"]`
- 상태 라벨: `main` 의 첫 직계 `<p>` (실행체가 지목)

**A1-5 판별력 재현**: 위 ④의 `eval` 안에서 `omy.judgeFinalLines(expected)` 를 정상 기대값과
무력화 5종(순서 뒤바꿈 · sentinel 덧붙임 · 5줄 축약 · `[]` · `null`)으로 각각 부르고 `verdict` 를
읽음. 앱 소스를 고치지 않음.

**DB 대조**: `cd app/backend && .venv/bin/python -c "import sys; sys.path.insert(0,'../../tests/harness');
from psql_cli import psql; print(psql('<질의>'))"` — §7 헬퍼만 씀(`podman exec` 를 쓰지 않음).
보존 세션 무결성은 **`utterances` 경유 조인**으로 물어야 함(위 teardown 절의 ⚠️).

---

# 3차 시도 — `stub_unresponsive`. 이 모드가 뒷받침하는 단정을 전부 판정함

> 호출자가 어댑터를 전환했음(pid 26253 → **56138** · `VOICE_ADAPTER=stub_unresponsive` ·
> `WORKER_ENABLED=false`). HEAD **`2668ca1`** · 회차 `run_id`
> **`bcafc8ba-1c8e-43f9-afad-d7181dfccb3b`** · `WINDOW_START`
> **`2026-09-08 19:19:01.108513+00`**(UTC).
> `browser_leg.md`·`instrument.js` 를 둘 다 다시 읽고 시작했음(diff 확인: §2 어댑터 모드 규약 ·
> A1-6 칸 · `startedSessionId`).

## 판정 요약 — 이 회차가 평가한 11건

| # | 판정 | 관측 | 음성 대조가 FAIL 을 냈는가 |
|---|---|---|---|
| A1-1 대조 | **`PASS`** | `recv.final` = **0** | **예** — 2차의 6 에서 0 으로 떨어졌음 |
| A1-2 대조 | **`PASS`** | `recv.partial` = **0** | **예** — 2차의 6 → 0 |
| A1-3 대조 | **`PASS`** | `recv.audio` = **0** | **예** — 2차의 3 → 0 |
| A1-4 대조 ① | **`PASS`** | `started` = `{count:0, when:[], calls:[]}` | **예** — 2차의 3 → 0 |
| A1-6 대조 | **`PASS`** | URL 이 **`http://localhost:3000/`** 에 남고 `사유: voice_adapter_connect_timeout` `<p>` **1개** | **예** — 2차의 `/results/<uuid>` 가 나오지 않았음 |
| A1-8 대조 | **`PASS`** | 그 세션 `utterances` **0행**. 창 안 세션 **5건 전부 0행**이고 전체 `utterances` 가 **114 → 114**(불변) | **예** — 2차의 6행 → 0행 |
| A2-1 | **`PASS`** | partial 줄 1개 · color == probe muted (라이트 `rgb(89,89,89)` · 다크 `rgb(154,154,154)`) | **예** — 주입 전(`active` 도달 후) 접두 `<p>` **0개**를 두 모드에서 관측 |
| A2-2 | **`PASS`** | 확정 줄 1개 · color == probe fg (라이트 `rgb(23,23,23)` · 다크 `rgb(237,237,237)`) · partial 문구 잔존 **False** | **예** — ① 주입 전 0개 ② probe 두 값이 서로 다름(89≠23 · 154≠237) |
| A2-3 | **`PASS`** | 라이트 muted `rgb(89,89,89)` ≠ 다크 muted `rgb(154,154,154)` | **예** — **두 모드를 다 돌렸음**(한 모드면 `A2-3 미평가`·FAIL). 페이지가 보고한 스킴이 요청과 일치(`page reports light`/`dark`) |
| A5-1 | **`PASS`** | 4 outcome 전부 배지 **정확히 1개** + `textContent` 가 `PRONUNCIATION_BADGE` 와 등호 일치 | **예(대조 ②)** — 같은 요소가 매번 바뀜. ⚠️ 대조 ①은 이 문서에서 오염됨(아래) |
| A5-2 | **`PASS`** | sentinel `ZZ_TARGET_SOUND_SENTINEL_9931` 이 leaf 0건 · 전체 `innerHTML` 검색 **false**(4회 전부) | **예** — 짝 대조 성립: 같은 프레임의 outcome 문구는 **있었음** |

**A1-6 본 단정의 유도 경로가 실재함을 확인했음** — 새 계측 키 `startedSessionId` 가
**`db1e7af0-1146-4a0a-a8e8-84f98072e09a`** 로 채워졌고 `recv.session_started === 1` 이므로
「세션이 시작되지 않았다」가 아님. 그 uuid 가 DB `learning_sessions` 에 `failed` 로 실재함을
확인했음. ⚠️ **본 단정 자체(URL 이 `/results/<그 id>`)는 이 모드에서 성립할 수 없음** — 그것이
바로 이 모드의 음성 대조이기 때문임. 두 회차를 합쳐야 A1-6 이 완결되고 그 판단은 호출자 몫임.

⛔ **이 모드가 뒷받침하지 않는 것을 다시 재지 않았음**: A1-0·A1-5·A1-7·A1-4 본 단정·C3·C4.
A4-2 도 지시대로 평가하지 않았음.

## 프리플라이트 P1~P9 — 전건 통과

P1 `{"status":"ok"}` · P2 `NEXT_PUBLIC_API_BASE=http://localhost:8002` ·
P3 `app/frontend/.gitignore:34:.env*` · P4 `postgresql@17 started` ·
**P5 `pid 56138 · 기동 01:43 전 · 소스 34건 → 통과`(exit 0)** · P6 `200` · P7 `2` ·
P8 `pytest 0건` · P9 `/opt/homebrew/opt/postgresql@17/bin/psql` · `ohmyenglish`.
플래그를 프로세스에서 확인: `WORKER_ENABLED=false` · `VOICE_ADAPTER=stub_unresponsive`.

## §4 계측 자기검사 — 통과. ⚠️ **sha256 대조가 캐시된 낡은 판을 잡아냈음**

**이 회차의 가장 값어치 있는 계측 사건임.** 첫 시도에서 페이지가 계산한 sha256 이
**`846f130f…`**(2차 회차의 판)였고 파일 해시는 **`cbc19fb6…`**(새 판)였음. 같은 시점에
`'startedSessionId' in omy` 가 **`false`** 로 나와 그 진단이 교차 확인됐음.

원인은 **HTTP 캐시**임 — 같은 URL(`http://127.0.0.1:8899/instrument.js`)을 2차 회차에서 이미
받았고 브라우저가 그 응답을 재사용했음. `fetch(url + '?v=' + Date.now(), {cache:'no-store'})`
로 다시 받아 **`cbc19fb69a89eb7868420a9ea1b9245103518dfeaebddec29fcfea3ee19b55ac`**(44,552 B)
· 파일 해시와 일치를 확인한 뒤 진행했음.

⛔ **§10-3 의 sha256 규약이 「전사 드리프트」만 막는 것이 아님을 실측으로 보여줌** —
**캐시 드리프트**도 잡음. 그 대조가 없었으면 이 회차가 **낡은 계측으로 A1-6 을 재고
`startedSessionId` 부재를 「계측 결함 미해결」로 오보했을 것임.** 다음 회차는 처음부터
`cache:'no-store'` + 캐시 무력화 쿼리를 붙이는 편이 낫음.

| 검사 | 관측 |
|---|---|
| `eval` 반환값 | `"instrumented"` |
| sha256 (페이지) == 파일 | **일치** (`cbc19fb6…` · 44,552 B) |
| 필수 키 9건 (`startedSessionId` 포함) | 전부 존재 · `startedSessionId` 초기값 `null` |
| `finalLines`(있으면 낡음) | **ABSENT** |
| 후킹 소유자 | `onmessage`=WebSocket · `send`=WebSocket · `start`=AudioBufferSourceNode · `createBufferSource`=BaseAudioContext |

## C2 — 실행체 출력 그대로. 단정 56건 전건 통과 · exit 0

```
instrument.js sha256(file): cbc19fb69a89eb7868420a9ea1b9245103518dfeaebddec29fcfea3ee19b55ac  (44552B)
--- emulated=light (page reports light) ---
  주입 전(active 도달 후) 접두 <p>: 0 · 사유 <p>: 0 · 대기문구: True
  probe  muted=rgb(89, 89, 89) (재판독 rgb(89, 89, 89))
  probe  fg   =rgb(23, 23, 23) (재판독 rgb(23, 23, 23))
  partial 줄  count=1 color=rgb(89, 89, 89) → muted 일치: True
  확정   줄  count=1 color=rgb(23, 23, 23) → fg 일치: True · partial 문구 잔존: False
  timing active=18ms partial+19ms final+37ms total=55ms · 클릭→eval반환 68ms · 클릭→스크린샷 130ms
  recv={'session_started': 1, 'partial': 0, 'final': 0, 'audio': 0, ...} injected=2 snapshotCounts=[0, 1, 1]
--- emulated=dark (page reports dark) ---
  주입 전(active 도달 후) 접두 <p>: 0 · 사유 <p>: 0 · 대기문구: True
  probe  muted=rgb(154, 154, 154) (재판독 rgb(154, 154, 154))
  probe  fg   =rgb(237, 237, 237) (재판독 rgb(237, 237, 237))
  partial 줄  count=1 color=rgb(154, 154, 154) → muted 일치: True
  확정   줄  count=1 color=rgb(237, 237, 237) → fg 일치: True · partial 문구 잔존: False
  timing active=17ms partial+18ms final+35ms total=53ms · 클릭→eval반환 64ms · 클릭→스크린샷 132ms
--- A2-3 모드 대조 ---
  light muted=rgb(89, 89, 89) · dark muted=rgb(154, 154, 154) → 서로 다름: True
  light fg=rgb(23, 23, 23) · dark fg=rgb(237, 237, 237) → 서로 다름: True
--- 판정 (단정 56건 검사) ---
  PASS  56건 전건 통과
```

`recv.partial`·`recv.final` 이 **0**인 것이 주입 창이 실제로 열렸다는 증거임(경쟁 프레임 0).
`injected=2` 가 partial·final 두 프레임임. **`c2-light.png` 를 직접 열어 눈으로 확인했음** —
흰 배경에 확정 줄 `질문: FINAL_PROBE_BETA 확정 전사문 표본`이 진한 색으로 렌더되고 partial 줄이
사라져 있었음.

## C1 음성 대조 — 창을 넘긴 뒤의 판독이 그대로 대조가 됨

CDP 클릭(`use_browser` `click`) 후 `eval` 로 판독했음. **마커를 심어 라운드트립을 실측했음**:
`sinceMarkerMs` **20,635**(wall clock 20,634) — 창(`CONNECT_TIMEOUT = 10.0`)의 **2배**임.
그래서 판독 시점은 이미 창 밖이고 **C1 대조에는 그것이 유리함**(`session_failed` 후 상태를 봄).

```
recv    = {session_started:1, partial:0, final:0, audio:0, session_ended:0, session_failed:1}
sent    = {audio:313, end_session:0, unparsed:0, other:0, foreign:0}
started = {count:0, when:[], calls:[]}
url     = "http://localhost:3000/"        · reasonPCount = 1
reason  = "사유: voice_adapter_connect_timeout"
startedSessionId = "db1e7af0-1146-4a0a-a8e8-84f98072e09a"
userActivation = {hasBeenActive:true, isActive:false}
resumeLog[*].afterAwait = "running", "running"   · contextState = "running"
socketUrls = ["ws://localhost:8002/ws/session"] · appHandlerAttached = true
mainHTML = <h1>…</h1><div><p>연결에 실패했습니다.</p><p …>사유: voice_adapter_connect_timeout</p>
           <button>다시 시도</button></div>
```

⚠️ **`sent.audio` 가 313 건임** — 2차 회차(`stub`)의 0~1 과 대비됨. 세션이 20초 유지되니
캡처 프레임이 쌓임. **A1-7 의 「세션이 너무 짧다」 진단이 이 대비로 뒷받침됨**(2차의 `BLOCKED`
사유가 옳았음). ⛔ 다만 **A1-7 본 단정을 이 모드에서 `PASS` 로 올리지 않았음** — 이 모드는
`audio` 응답 프레임이 0이라 §5 가 A1-4 를 그렇게 가둔 것과 같은 이유로 구성이 다름. 호출자가
범위를 정하지 않은 것을 스스로 넓히지 않았음.

**H-AE 판별이 이 회차에서 양쪽으로 갈렸음** — 같은 코드에서 두 클릭 방식이 다른 결과를 냈음:

| 클릭 방식 | `userActivation.hasBeenActive` | `resumeLog[*].afterAwait` | `active` 도달 |
|---|---|---|---|
| 합성 `element.click()` | **false** | **null**(영원히 pending) | **실패**(6,000 ms 초과) · 화면이 `마이크 권한을 요청하는 중입니다...` 에 머묾 |
| CDP 클릭 | **true** | `"running"` | 성공 |

**즉 `H-AE` 가 이 회차에서 실물로 재현됐고 그 signature 가 확정됨.** 합성 클릭 회차도 소켓은
열렸음(`appHandlerAttached: true` · `recv.session_started: 1`) — **소켓이 열린 것과 `active`
도달은 다른 사건**이고, 그 구별이 없으면 「후킹 고장」으로 오진할 자리임.

## C5 — 창 안 주입에 성공했음. 우회 경로를 실측으로 찾음

⛔ **두 경로가 먼저 막혔고 그것을 각각 관측했음**:
① **합성 클릭** → `H-AE` 로 `active` 미도달(위 표) → 주입 4건이 오류 없이 들어갔으나 배지 0개.
② **CDP 클릭 + 별도 `eval`** → 라운드트립 **20,635 ms** > 창 **10,000 ms** → §6 의 판별대로
   **기대 개수가 나오지 않고 `사유:` `<p>` 가 1개** = 창 이탈. §6·§10 규약상 **`ERROR`** 이고
   재시도 대상임.

✅ **성립한 경로 — 같은 문서에서 `다시 시도` 를 합성 클릭했음.** 근거: 앞선 CDP 클릭이
`userActivation.hasBeenActive = true` 를 이미 만들었고 **AudioContext 가 이미 `running`** 이라
`tryResume()` 이 즉시 끝남(`resumeLog[2]` = `{before:"running", afterSync:"running",
afterAwait:"running"}`). 실측: **`active` 도달 20 ms** · 주입·판독까지 **전체 243 ms**(창의
2.4 %) · 판독 시점 `reasonPCount` **0**(창 안).

| 주입 outcome | 배지 개수 | `textContent` | `outerHTML` 의 색 |
|---|--:|---|---|
| `pending` | **1** | `🔊 발음 교정 중` | `var(--foreground-muted)` |
| `correct` | **1** | `✓ 좋아요` | `var(--foreground)` |
| `incorrect` | **1** | `다시 연습해요` | `var(--danger)` |
| `unclear` | **1** | `잘 안 들렸어요` | `var(--foreground-muted)` |

네 문구가 `app/page.tsx:PRONUNCIATION_BADGE` 의 값과 **등호로 일치**하고 요소는 매번
`p[aria-live="polite"]` **정확히 1개**임. **같은 요소가 4회 모두 바뀌었으므로 대조 ②가
성립함**(상수를 렌더하면 바뀌지 않음). `inject()` 가 `recv` 를 오염시키지 않은 것도 재확인됐음
(`recvAfterInject` 가 주입 전과 동일 · `injected` 5→8).
**`019-eval.png` 를 직접 열어 확인했음** — 다크 화면에 `대화를 기다리는 중...` 아래 배지
`잘 안 들렸어요` 가 굵게 렌더됐고 `target_sound` 는 화면에 없었음.

⚠️ **A5-1 대조 ①의 한계를 정직하게 적음.** 이 문서에서는 `active` 도달 시점에 배지가 이미
**1개**였음(`badgeAtActive: 1`) — 앞선 창 이탈 회차의 주입이 React 상태에 남아 컨테이너가 다시
마운트되자 렌더된 것임. 그래서 **「컨테이너가 마운트된 상태에서 주입 전 배지 부재」를 이 문서에서
깨끗하게 재지 못했음.** 관측한 것은 `badgeBefore: 0`(재시도 클릭 전)과 앞선 회차의
`badgeBeforeClick: 0` 이고 **그때는 컨테이너가 없었음.** 판정을 `PASS` 로 올린 근거는 **대조 ②**임
(실제로 판별력을 냈음). 대조 ①을 깨끗하게 재려면 **한 문서에서 주입을 한 번만** 해야 하고
그것은 창 안 진입이 첫 시도에 성공해야 가능함 → **C5 전용 실행체가 있으면 닫힘.**

## DB — 3열 대조. **쿼리를 표에 명시함**

⚠️ **2차 보고의 수치 하나가 다른 표로 오독됐으므로 이번에는 각 행에 쿼리를 붙임.**
2차의 `45` 는 **`select count(*) from analysis_jobs`** 의 출력이었고 `error_occurrences` 가 아님.
이번 회차에 두 표를 나란히 재서 확정했음: `analysis_jobs` **45** · `error_occurrences` **18**
— **서로 다른 표임.** ⛔ **§8 의 drift 정의는 그 어느 쪽도 아님** — `error_patterns` 의
`frequency`·`last_seen_at` 을 `harness_pattern_baseline` 과 대조하는 것임(아래 쿼리 그대로).

| 표 (쿼리) | baseline | 회차 후 | teardown 후 |
|---|--:|--:|--:|
| `learning_sessions` (`where user_id='0…001'`) | 12 | **17** | **12** |
| `analysis_jobs` (전체) | 45 | **50** | **45** |
| `utterances` (전체) | 114 | **114** | **114** |
| `error_patterns` (`where user_id='0…001'`) | 8 | 8 | 8 |
| `session_plans` (전체) | 1 | 1 | 1 |
| `learner_notes` (전체) | 1 | 1 | 1 |
| `error_occurrences` (전체) | 18 | 18 | 18 |

⚠️ **`utterances` 가 세 시점 모두 114 로 불변인 것이 A1-8 대조의 독립 증거임** — 이 모드는
세션 5건을 열었지만 발화를 한 건도 저장하지 않았음.

### teardown — §8 정의 그대로

```sql
-- ④-2 에 쓴 쿼리 (§8 정의)
select count(*) from harness_pattern_baseline b join error_patterns p on p.id = b.id
 where p.frequency <> b.frequency or p.last_seen_at is distinct from b.last_seen_at;
```

| 단계 | 출력 |
|---|---|
| §8-0 drift (회차 **전**) | **0** → 재스냅샷. baseline **8행** |
| ①-a 스윕 등록 | `INSERT 0 5` |
| ① 세션 삭제 | `DELETE 5` (보존 5개는 `not in` 제외) |
| ② 복원 | `UPDATE 0` — 바뀐 값이 없어 만질 행이 없음(**재계산하지 않았음**) |
| ③ 0-occurrence 패턴 삭제 | `DELETE 0` |
| ④-1 `error_patterns` | **8** = baseline 8 |
| **④-2 drift** | **0** |
| ④-3 이 회차 등록 세션 중 생존 | **0** |
| 보존 세션 | **5 생존** |

**보존 세션 5개가 job 단위까지 2차 회차와 동일함**(2차의 정정을 적용해 `utterances` 경유로 조인):
C3a `analyze_utterance:pending×3` · C3b `done×1` · C3c `done×2,failed×1` ·
C3d `analyze_utterance 0건`(발화 0) · C3e `analyze_utterance 0건`(발화 6).

**회차가 만든 세션 5건** (전부 등록 후 삭제 · 전부 `failed`·발화 0):
`f8efef13-…`(C2 라이트) · `29680903-…`(C2 다크) · `9943e2f8-…`(합성 클릭) ·
`db1e7af0-…`(CDP 클릭) · `c33f8614-…`(C5 재시도).

### ⑤ 프로세스·환경 — §8-⑤ 예외(무변경)

`lsof -nP -iTCP:8002 -sTCP:LISTEN -t` → **56138**(회차 시작과 같음) ·
`ps -p 56138 -Eww` → `WORKER_ENABLED=false`·`VOICE_ADAPTER=stub_unresponsive`(회차 시작과 같음) ·
`/health` → `{"status":"ok"}`. **`app/backend/.env` 를 열지 않았고 워커를 켜지 않았음.**
임시 CORS 서버는 종료했음(8899 응답 `000`) 그리고 `/tmp` 스크립트·로그를 지웠음.

## 증거 파일 — 이 회차 것. 해시로 구별을 증명함

| 파일 | md5 · 크기 |
|---|---|
| `.harness/evidence/c2-light.png` | `a4e400b6446201f87973f5855775495f` · 43,856 B |
| `.harness/evidence/c2-dark.png` | `856ad715b1581515db995730d0a288f8` · 41,479 B |
| `.harness/evidence/c2-render-hierarchy.json` | 3,799 B (probe·색·타이밍 raw) |

**두 png 이 서로 다른 해시임** — 「같은 캡처를 두 이름으로 저장」을 배제함.
C5 는 `use_browser` 자동 저장분 `019-eval.png` 를 눈으로 확인했고 **판정 근거는 `eval` 반환
JSON**임(§10-1 — 위 표에 옮겼음).

## 절차·계측 결함 — 신규 2건. 고치지 않고 보고함

**결함 3 — 계측을 fetch 로 받으면 HTTP 캐시가 낡은 판을 먹임.** 이 회차가 실제로 걸렸고
**sha256 대조가 잡았음**(위 §4 절). `browser_leg.md` §10-3 은 「임시 CORS 서버로 파일을 그대로
받아 sha256 을 대조한다」만 적고 **캐시 무력화를 적지 않음.** 대조가 있어 사고로 이어지지는
않았으나, **대조를 뺀 회차는 낡은 계측으로 새 키를 「부재」로 오보함.** →
§10-3 에 `{cache:'no-store'}` + 쿼리 무력화를 명시하는 편이 좋아 보임.

**결함 4 — C5 에 실행체가 없어 창 안 진입이 우연에 걸림.** C2 는 `c2_render_hierarchy.py` 가
CDP 클릭 + 한 왕복(68 ms)으로 창을 0.65 % 만 쓰지만, **C5 는 같은 수단이 없어** 에이전트
라운드트립(**이 환경 실측 20,635 ms**)이 창(10,000 ms)을 반드시 넘김. 이 회차는
**「CDP 클릭으로 activation 을 만든 뒤 같은 문서에서 `다시 시도` 를 합성 클릭」**이라는 우회로
성립시켰으나, 그 결과 **A5-1 대조 ①이 오염됐음**(위 C5 절). → C5 를 C2 실행체에 `--phase
pronunciation` 으로 넣거나 전용 실행체를 두면 닫힘. **`tests/harness/**` 를 수정하지 않았음.**

⚠️ **§6 의 「라운드트립 약 30 s」를 이 환경에서 다시 재서 20,635 ms 를 얻었음** — 결론(창보다
길다)은 같으나 수치가 다름. 그 문장을 고치지 않았음(호출자 몫).

## 내가 확인하지 못한 것

- **A5-1 대조 ①을 깨끗한 조건에서**(컨테이너 마운트 + 주입 0회). 위 결함 4 가 원인임.
- **A1-7 본 단정을 이 모드에서** — 범위 밖이라 재지 않았음. §11-4 는 여전히 열려 있음.
- **A1-6 본 단정** — 이 모드에서 구조적으로 불가(그것이 이 모드의 대조임). `startedSessionId` 가
  채워지는 것과 그 uuid 가 DB 에 실재하는 것까지만 확인했음.
- **A4-2 기대값 교차 대조** — 지시대로 평가하지 않았음.
- **C2 다크 스크린샷을 눈으로** — 라이트만 열어 봤음(해시로 라이트와 다름은 확인했음).
- **`instrument.js` 새 판의 게이트 무회귀** — 호출자가 71 passed 로 확인했다고 했고 **나는 직접
  돌리지 않았음**(`pytest` 금지).

## 호출자가 3차 판정을 재현하는 방법

**C2 가 가장 싸고 강함** (`stub_unresponsive` 에서):
```bash
cd app/backend && .venv/bin/python ../../tests/harness/c2_render_hierarchy.py
```
→ `단정 56건 검사 · PASS` · exit 0. 한 모드만 돌리려면 `--schemes light` → **`A2-3 미평가`로
FAIL·exit 1** 이 나는 것으로 그 게이트의 판별력을 확인할 수 있음.

**C1 대조**: `navigate http://localhost:3000/` → `eval` 로 계측 걸기(⚠️ **`{cache:'no-store'}` +
`?v=<epoch>`** — 없으면 낡은 판이 걸림) → `click` selector **`button`** → 20초쯤 뒤 `eval` 로
`window.__omy` 판독. `recv.final`·`partial`·`audio` 와 `started.count` 가 **전부 0** 이고
`location.href` 가 `http://localhost:3000/` 이며 `사유: ` 로 시작하는 `<p>` 가 1개면 재현됨.

**C5**: 위 C1 판독까지 온 **같은 문서에서** `eval` 하나로
`다시 시도` 버튼을 합성 클릭 → `학습 종료` 버튼 출현 대기 → `omy.inject({type:'pronunciation',
outcome, target_form:'…', target_sound:'<sentinel>'})` 를 4 outcome 순차 호출하며 매번
`document.querySelectorAll('p[aria-live="polite"]')` 의 개수·`textContent`·`outerHTML` 을 읽음.
⚠️ **CDP 클릭이 먼저 있어야 함**(합성 클릭만으로는 `H-AE` 로 `active` 에 도달하지 못함).

**DB 대조**: §7 헬퍼로 위 표의 쿼리를 그대로 던짐. drift 는 **§8 정의 쿼리**를 씀
(`error_occurrences` 총계가 아님).

---

# 4차 시도 — A1-6 본 단정 하나. 지정된 유도로 재서 `PASS`

> 호출자가 어댑터를 baseline 으로 되돌렸음(pid 56138 → **72290** · `VOICE_ADAPTER=stub` ·
> `WORKER_ENABLED=false`). HEAD **`23aed48`** · 회차 `run_id`
> **`3d7ddd94-d7a6-4524-8e36-28ac82266a0a`** · `WINDOW_START` **`2026-09-08 19:32:33.018671+00`**.
> ⚠️ `browser_leg.md` §10-3 의 캐시 규약은 **미커밋 상태로 디스크에 있었고 그것을 정본으로 읽었음**
> (`grep no-store` 로 확인: `⛔ 취득은 반드시 fetch(url, {cache:'no-store'}) 로 한다`).

**프리플라이트 P1~P9 전건 통과** — P5 `pid 72290 · 기동 01:15 전 · 소스 34건 → 통과`(exit 0) ·
P1 `{"status":"ok"}` · P4 `postgresql@17 started` · P6 `200` · P7 `2` · P8 `pytest 0건` ·
P9 `ohmyenglish`. 플래그를 프로세스에서 확인: `WORKER_ENABLED=false`·`VOICE_ADAPTER=stub`.

**계측** — §10-3 의 새 규약대로 `fetch(url + '?v=' + Date.now(), {cache:'no-store'})` 로 받았고
페이지 계산 sha256 이 **`cbc19fb69a89eb7868420a9ea1b9245103518dfeaebddec29fcfea3ee19b55ac`**
(44,552 B) 로 파일 해시와 일치했음. `evalReturn` `"instrumented"` ·
`startedSessionIdKeyPresent` **true** · 초기값 **`null`** · `recv` 전건 0(클릭 전).

## A1-6 — `PASS`. 기대값·관측값이 같은 `eval` 반환 JSON 안에 있음

```json
{"startedSessionId":"d08d470a-9347-407d-b2ca-68b7f73fd4ad",
 "recv_session_started":1,
 "nullMeaning":"N/A — 값이 있음",
 "expectedPath":"/results/d08d470a-9347-407d-b2ca-68b7f73fd4ad",
 "actualPath" :"/results/d08d470a-9347-407d-b2ca-68b7f73fd4ad",
 "actualHref" :"http://localhost:3000/results/d08d470a-9347-407d-b2ca-68b7f73fd4ad",
 "A1_6_pathEquals":true,
 "negControl_sentinelPathEquals":false, "negControl_rootEquals":false,
 "recv":{"session_started":1,"partial":6,"final":6,"audio":3,"session_ended":1,"session_failed":0},
 "h1":"학습 결과","firstDirectP":"분석 중",
 "mainOuterHTML":"<main …><h1>학습 결과</h1><p style=\"font-size: 1.25rem; font-weight: bold;\">분석 중</p></main>"}
```

**기대값의 출처가 계측이고 DB 가 아님** — `startedSessionId` 는 `session_started` 프레임이 실어 온
값이고, `recv.session_started === 1` 이므로 `null` 의 두 뜻(세션 미시작 / 키 부재)은 발생하지
않았음. **DB 로 대신하지 않았음**(4차에서는 그 조회를 아예 하지 않았고, teardown 의 잔여물 관리만
DB 를 만졌음).

**음성 대조는 3차 회차가 냈음** — 같은 단정을 `stub_unresponsive` 에서 재서
`actualPath` 가 **`/`** 였고 `사유: voice_adapter_connect_timeout` 이 떴음. 이번 회차의
`negControl_rootEquals: false` 가 그 반대편이므로 **두 모드가 실제로 갈렸음.**

⚠️ **`negControl_sentinelPathEquals` 는 판별력이 0임을 밝혀 둠.** 본 단정이 이미
`actualPath === expectedPath` 를 등호로 요구하므로 sentinel 을 덧붙인 부등호는 **필연적으로 참**임.
`browser_leg.md` §5 가 A4-2 대조 ①을 철회한 것과 **같은 형태**임 — 검사 수를 부풀리는 줄이므로
근거로 세지 않았음. **A1-6 을 받치는 대조는 3차의 모드 대조 하나임.**

## DB — 3열. 각 행에 쿼리를 붙임(3차의 형식 유지)

| 표 (쿼리) | baseline | 회차 후 | teardown 후 |
|---|--:|--:|--:|
| `learning_sessions` (`where user_id='0…001'`) | 12 | **13** | **12** |
| `analysis_jobs` (전체) | 45 | **49** | **45** |
| `utterances` (전체) | 114 | **120** | **114** |
| `error_patterns` (`where user_id='0…001'`) | 8 | 8 | 8 |
| `session_plans` (전체) | 1 | 1 | 1 |
| `learner_notes` (전체) | 1 | 1 | 1 |
| `error_occurrences` (전체) | 18 | 18 | 18 |

회차가 만든 세션 **1건** — `d08d470a-…` (`completed` · 발화 6). teardown:
§8-0 drift(회차 전) **0** → `①-a INSERT 0 1` · `① DELETE 1` · `② UPDATE 0`(재계산하지 않았음) ·
`③ DELETE 0` · `④-1` **8** = baseline 8 · **`④-2` drift(§8 정의) 0** · `④-3` 생존 **0** ·
**보존 세션 5개 생존**. ⑤는 §8-⑤ 예외(무변경): pid **72290** 동일 · 플래그 동일 ·
`/health` `{"status":"ok"}` · 임시 CORS 서버 종료(8899 `000`).

## A1-0~A1-8 — 세 회차 합산. 각 칸에 어느 회차에서 얻었는지 표시함

| # | 본 단정 | 어느 회차 | 음성 대조가 FAIL 을 냈는가 | 어느 회차 | 종합 |
|---|---|---|---|---|---|
| A1-0 | 접두 `<p>` **1개**(ⓑ API `reason`≠null) | 2차 | **예** — 클릭 후 **0개** | 2차 | **`PASS`** |
| A1-1 | `recv.final` **6** | 2차 | **예** — **0** | 3차 | **`PASS`** |
| A1-2 | `recv.partial` **6** | 2차 | **예** — **0** | 3차 | **`PASS`** |
| A1-3 | `recv.audio` **3** | 2차 | **예** — **0** | 3차 | **`PASS`** |
| A1-4 | `started.count` **3** · `when`=[0,0.2,0.4] · `afterRecvAudio`=1/2/3 | 2차 | **예** — 대조 ① `count` **0** | 3차 | **`PASS`** |
| A1-5 | `verdict: "PASS"`(계측 값을 베낌) | 2차 | **예** — 무력화 6종 중 5종이 `APP_CONTENT_MISMATCH`·`APP_EXCESS_RENDER`·이름 있는 throw | 2차 | **`PASS`** |
| A1-6 | `actualPath === '/results/' + startedSessionId` (ⓑ **계측 유도**) | **4차** | **예** — 같은 단정이 `stub_unresponsive` 에서 `actualPath` **`/`** + `사유: voice_adapter_connect_timeout` | 3차 | **`PASS`** |
| A1-7 | `sent.audio` **1** · `sentAudioBytes` **1368** | 2차 | **아님** — 대조 ①(`end_session` 1건)은 스텁이 자기종료해 구조적 불가 · 대조 ③은 톤에서도 `nonZeroFrames` 0(§11-4 미결) | — | **`BLOCKED`** |
| A1-8 | `utterances` **6행**(내용도 픽스처와 일치) | 2차 | **예** — `stub_unresponsive` 세션 **0행**이고 전체 `utterances` **114 불변** | 3차 | **`PASS`** |

⛔ **A1-7 하나만 남았음.** 그 사유는 화면 결함이 아니라 **표본 구성**임(§10 갈래 2 —
스텁 세션이 32 ms 캡처 프레임 1건을 만들기도 전에 끝남). 3차의 `stub_unresponsive` 회차가
`sent.audio` **313** 을 낸 것이 그 진단을 뒷받침함 — 세션이 20초 유지되면 프레임이 쌓임.
**닫으려면 「응답 프레임이 오면서 세션이 길게 유지되는」 구성이 필요하고 그것은 이 회차가
만들 수 있는 것이 아님**(호출자 판단 몫).

⚠️ **재검증 불가를 명시함**: 4차의 `d08d470a-…` 도 teardown 이 지웠음(`learning_sessions` 12 =
baseline). 그래서 A1-6 의 증거는 **위 `eval` 반환 JSON 하나**이고, 그 안에 기대값·관측값·
`recv` 가 함께 들어 있어 회차 밖에서도 대조 가능함(호출자 요구를 그렇게 반영했음).
