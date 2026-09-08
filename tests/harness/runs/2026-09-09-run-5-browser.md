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
