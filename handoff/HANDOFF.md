# Handoff — OhMyEnglish

> **두 가지만 담는다: 다음 한 걸음 / 착수 전 필수.** 그 밖은 각 정본이 소유하고 여기서는
> **가리키기만** 함. 최종 갱신 **2026-09-09** · 브랜치 `design/first-vertical-slice`
> ⛔ **줄 수·개수를 적지 않는다** — 적는 순간 낡음(`H-O`).
> ⛔ **정리된 결정 이력을 이 파일에 옮기지 않는다** (2026-09-09 사용자 지시). 결정은 번호로만
> 가리킨다 — 본문은 `docs/ops/captain-instruction-register.md` 가 소유함.

## 다음 한 걸음 — **`TASK-64` 를 권함**(작고, `browser_leg.md` §11-9 를 막고 있음)

> ✅ **결과 화면 결함 셋이 닫혔음** — `TASK-55`·`56`·`57` 전부 `Done`. 수정 후 화면을 직접 열어
> 봤고 회차 기록이 값을 가짐(`tests/harness/runs/2026-09-09-task55-56-57-results-screen-fix.md`).
> ⛔ **상태 코드는 이제 분류용임** — `lib/api.ts` 의 `SessionResultsError.status` 가 문구가 아니라
> 「4xx 면 폴링을 멈춘다」의 입력임. 학습자 문구는 화면이 소유함(`failureNotice`).
> ⛔ **결과 화면의 인앱 출구에 밑줄을 직접 줬음** — `globals.css` 의 전역 `a` 가
> `text-decoration: none` 이라 링크가 본문 글자와 구별되지 않았음(화면으로 관측). 색 토큰이
> 4개뿐이어서 어포던스를 밑줄로 만들었고 **전역 `a` 규칙은 고치지 않았음.**
>
> ⚠️ **`TASK-59` 는 다른 세션(`ohmyenglish-15`)이 잡고 있음** — 2026-09-09 13:38 에 `In Progress` 로
> 바뀌었고 `tests/harness/fixtures/voice/p1q.wav` 등을 만들고 있음. **그 파일들과 그 태스크 md 를
> 건드리지 않음.** 세션 간 주소는 매번 `ListAgents` 로 확인함.
>
> ✅ **판별력 관측이 끝났음** — `TASK-30`·`TASK-49`·`TASK-52` 모두 `Done`. 단정 일곱 전부 무력화에서
> FAIL 을 관측했고 **`browser_leg.md` §11 의 미결 둘(§11-4·§11-9)이 닫혔음.** 회차 기록 넷이 값을
> 가짐(`runs/2026-09-09-task30-*.md`). **진행 상태를 여기 재서술하지 않음.**
> ⛔ **판별력이 게이트로 옮겨졌음** — 실행체 셋(`c1_session_walkthrough.py`·`c3_results_screen.py`·
> `c5_pronunciation_badge.py`)이 판정을 순수 함수로 분리해 브라우저 없이 변이를 잡음.
> **같은 관측을 다시 열 필요가 없음.**
>
> ⚠️ **백엔드 어댑터 상태를 알고 시작함**: pid **52228** · `VOICE_ADAPTER=stub_unresponsive` ·
> `WORKER_ENABLED=false`. **A1-4·A1-5 를 다시 재려면 `stub` 으로 재기동해야 함** — 어느 어댑터가
> 어느 단정을 뒷받침하는지는 `browser_leg.md` §5 의 C1 실행체 절이 소유함.
>
> ⛔ **워커를 켤 때 반드시 읽을 것: `H-AT`.** 2026-09-09 에 워커를 켜서 **보존 세션 2개를 두 번
> 파괴했고** 복구에 비용이 들었음. 경로 둘과 대응이 그 함정에 있음.
> ⚠️ **실물 호출·워커·재기동은 사전 승인임**(결정 40) — 묻지 않고 진행함.
> ⛔ **teardown 범위를 시각창으로 잡음 — 실패한 실행도 세션을 만듦.** 「성공한 실행」만 지우면
> 남고, 2026-09-09 에 실제로 1건을 빠뜨렸음. **공유 DB 에서 다른 세션의 회차가 겹치면 표 합계는
> 어느 쪽의 지표도 되지 못함** — 보존 세션 여섯과 `drift 0` 이 증거임.

## 게이트 — 이 cwd 에서만 판정함 (`H-A`)

```bash
cd app/backend
.venv/bin/pytest -q                        # ⛔ 동시 실행 금지 (H-X) · 경로만 주면 async 가 죽음 (H-AJ)
.venv/bin/ruff check . && .venv/bin/ruff format --check .
/Users/redstar/.local/bin/ty check         # ⚠️ `.venv/bin/ty` 는 **없음** — pipx 전역임
.venv/bin/ruff check ../../tests ../../scripts    # 게이트 «밖» — 기준선 0
.venv/bin/ruff format --check ../../tests         # 게이트 «밖» — unformatted 0
```

⛔ **`tests/`·`scripts/` 를 건드렸으면 게이트 «밖»도 다시 잼.** 기준선은 **0** 이고 늘어나면 회귀임.
⛔ **`ruff check --fix` 를 디렉터리에 걸지 않음 — 내가 건드린 파일에만 검.**
⛔ **format 의 「N files」를 지표로 적지 않음** — `.md` 를 함께 세므로 문서를 추가하면 늘어남(`H-AR`).
⚠️ **수치가 0 인 것이 스크립트가 도는 증거가 아님** — import 를 바꿨으면 `--help` exit 0 을 확인함.
⚠️ 게이트 전에 `brew services list | grep postgresql@17` — 안 떠 있으면 대량 errors 가 나는데
**회귀가 아니라 연결 거부임**(`H-T`).

## 착수 전 필수

| # | 무엇 | 정본 |
|--:|---|---|
| 1 | **받은 캡틴 결정을 다시 묻지 않음.** 개수를 세지 않음 — register 가 열거함. 최근 것 중 판단을 바꾸는 것: **46**(⛔ **음성 제어에 참고할 구현체가 없음을 확인했음** — `realtime-meeting` 에 음성 명령 제어가 0건이고 `AllMyEnglish` 의 9건은 전부 문서임. `TASK-61` 은 **Nova tool 호출**로 만들고, 인식률이 낮은 것을 **관측한 뒤에만** 그 문서를 참고로 엶) · **43**(⛔ **태스크 경계에서 멈추지 않음** — 확인을 기다리는 것은 예의가 아니라 요청의 불이행임) · **44**(참고 프로젝트 적용은 이제 `TASK-60` **하나뿐** — ⛔ **`TASK-59` 의 Qwen3-TTS 가 2026-09-09 에 반증됐음**: `Sohee` 는 `lang_code` 를 `ko` 로 줘도 영어로 정확히 전사돼 발음 오류가 재현되지 않고 기존 `say -v Yuna` 가 이 목적에 나음 · prompt cache 와 BlackHole 은 **하지 않음**) · **45**(음성 제어·세션 총평을 요건으로 확정 · 튜터 목소리는 외부 합성으로 바꾸지 않음) · **40**(크리티컬 아닌 것은 사전 승인) · **41**(자격증명 회전 면제) · **42**(첫 푸시 완료) · **31**(스키마 이관은 전부 끝난 뒤) | `docs/ops/captain-instruction-register.md` |
| 2 | ⛔ **critic 재검증 루프를 다시 돌리지 않음.** 4회차까지 갔고 결정 22 가 설계·문서의 리뷰 게이트를 없앴음 | 결정 22 |
| 3 | **설계는 끝났음 — 다시 하지 않음.** 구현 소유자 `TASK-43`·`44`·`45` 전부 `Done`. 남은 UI 는 `TASK-10` 이 소유하고 그 노트에 선점 목록이 있음 | 원장 |
| 4 | ✅ **원격이 붙었고 푸시가 기본 리듬임.** `origin` = `github.com/redstarh/OhMyEnglish` · **PUBLIC** · 기본 브랜치 `main`. ⛔ **남은 잔여 위험**: DB 비밀번호가 **공개 이력에 있음**(결정 41 이 회전 면제). Postgres 가 `localhost` 전용 바인딩이라 한계 위험은 낮으나 0 은 아님. 없애는 선택지 셋은 **결정 42 가 소유함** — 다시 발명하지 않음 | 결정 42·41 |
| 5 | ⚠️ **`backlog task list --ready` 는 상태를 걸러내지 않음** — `Awaiting Decision`·`In Progress` 까지 「착수 가능」으로 뜸. **SessionStart 브리핑의 분류를 믿음** | 이 파일 |
| 6 | ⛔ **워커를 켜기 전에 `H-AT` 를 읽음.** `available_at` 비켜두기만으로는 부족함 — `flush_ended_sessions` 가 **job 을 새로 만듦** | `H-AT` |
| 7 | **함정을 안다** — `H-AV`(⛔ **`tests/` 아래 새 `.py` 는 `ty` 게이트 대상인데 `pytest` 는 수집하지 않음** — 그 틈에서 게이트가 조용히 깨짐. 하네스 파일을 건드렸으면 **게이트 넷을 모두** 다시 잼) · `H-AU`(⛔ **grep 「0건」이 거짓이 되는 기전 둘.** ① 제외 필터가 본문 언급을 버림 → 필터는 **경로에만** 걸음 ② **맨 `grep -r` 는 셰임이라 무시 대상을 빠뜨림** → 전수가 필요하면 **`command grep -r`**. ⚠️ `git ls-files` 는 **추적 밖을 빠뜨림**) · `H-AT`(워커가 보존 세션을 파괴함) · `H-AS`(문서 기동 명령이 워커를 켬 · 기본값 `True`) · `H-AR`(format 의 N files 가 `.md` 를 셈) · `H-AO`(위임 리뷰가 산출물만 잃고 죽음) · `H-AM`(병렬 dispatch → `git commit -- <path>`) · `H-AJ`(pytest 에 경로만 주면 async 가 죽음) · `H-AL`(완료 태스크의 낡은 노트) · `H-X`(⛔ 동시 `pytest` 금지) · `H-AP`(판별력 확인이 stale `__pycache__` 를 남김) | `docs/ops/pitfalls.md` |
| 8 | **DB 는 공유 인스턴스임**(`:5432`, StockAgent·En-Coach 와). 재시작·`ALTER SYSTEM`·`ALTER DATABASE … SET TimeZone` 금지 | `docs/ops/shared-database-guide.md` |
| 9 | ⚠️ **`.superpowers/**` 는 git 추적 밖임** — critic·리뷰 보고서 전부가 거기 있음. **지우지 않음** | `.superpowers/sdd/2026-09-07-…/` |

## 인계 지표 — **직접 돌려** 얻고 대조함

| # | 지표 | 기준값 (마감 시점에 직접 돌려 얻었음) |
|--:|---|---|
| 1 | `git rev-parse --short HEAD` · `git status` | **`dac604d` 이상**(등호를 요구하지 않음 — `H-P`) · 추적 미커밋 **0건** · `origin` 과 동기. ⚠️ **다른 세션이 동시에 원장을 쓰고 있으면 미커밋 0건이 아닐 수 있음** — 그 세션의 파일인지 먼저 보고 내 것만 커밋함(`H-AM`) |
| 2 | 원장 — `grep -h "^status:" backlog/tasks/*.md \| sort \| uniq -c` | 전체 **67** · Done **48** · To Do **18** · In Progress **1**(`TASK-59` — **다른 세션 소유**) · Awaiting Decision **0**. ⛔ `backlog task list --plain \| grep -c "^  TASK-"` 로 세지 않음 — 우선순위 라벨이 붙으면 빠짐 |
| 3 | 게이트 (`app/backend` cwd) | **871 passed** · `ruff check` exit 0 · format **unformatted 0** · `ty check` exit 0 · 게이트 **밖** `ruff check` **0 errors** · format **unformatted 0** · 프론트 `npx tsc --noEmit`·`npx eslint app lib` exit 0. ⚠️ **843 → 854 → 869 → 871 은 게이트 테스트가 는 것**(`test_c5_gates.py` 11건 · `test_c1_gates.py` 15건 · `test_c3_gates.py` 에 TASK-55 판별력 2건) — 회귀가 아님. **그것들이 판별력을 브라우저 없이 지킴.** ⛔ **`ty check` 는 `tests/harness/**` 까지 본다** — 2026-09-09 에 그 사실을 모르고 새 하네스 파일을 넣어 진단 4건이 났고(다른 세션이 찾음) **`TASK-49` 를 닫을 때 이 항목을 다시 재지 않은 것이 그 누락의 원인임.** 하네스 파일을 추가했으면 `ty check` 도 다시 잼 |
| 4 | DB (읽기만) | `schema_migrations` **9건**(`001·003~007·009·010·011`) · `learning_sessions` **13** · `error_patterns` **9** · `error_occurrences` **24** · `utterances` **120** · `session_plans` **2** · `review_tasks` **15** · `pronunciation_attempts` **4** · **§8 drift 0** · **보존 세션 6개** 생존. ⚠️ **수치에 표 이름을 붙여 적음** — 이름 없는 묶음은 읽는 사람이 엉뚱한 표에 대응시킴(2026-09-09 실측) |
| 5 | 결과 API 상태 6개 | `210233be` `analyzing` · `6225ddaf` `final`(교정 1) · `b2f0d169` `partial_failure` · `76d9ef31` `connection_failed` · `d127dece` `no_utterances` · **`e0c5e580` `final`(교정 2 — A4-2 표본)**. ⛔ **이 여섯이 `browser_leg.md` §9 의 자산임 — 지우지 않음.** ⚠️ **C3 회차에는 앞의 다섯만 넣음(상태당 1건)** — `e0c5e580` 을 여섯째로 넣으면 `final` 이 둘이 되어 A3-1 음성 대조가 오탐함. 그것이 `TASK-64` 임 |

⚠️ **3번과 5번이 핵심임** — 읽기는 전달을 증명하지 못하고 **직접 돌린 출력**만 데이터임.

## 이 리포의 지배 실패 모드

**"본문을 고치고 그것을 설명하는 문장을 안 고친다."** 판별법: **본문을 고쳤으면 그것을 설명하는
문장·개수·방향·시그니처를 같은 커밋에서 함께 고침.** 개수를 말하는 문장은 **아예 세지 않는
서술로 바꾸는 것**이 실제로 통한 유일한 구조적 해법임.

⛔ **파생 규칙 4개** (전부 실측):
- **설계서·원장의 「~하지 않는다/없다」를 근거로 쓸 때 지금도 참인지 코드로 확인함**(`H-AL`).
- **subagent·다른 세션이 「돌렸다」고 적은 수치는 내 증거가 아님** — 최소 1건을 직접 검증함.
  ⚠️ **판정의 정의에 맞는 쿼리를 내가 돌려야 함**(2026-09-09: 남의 6수치를 엉뚱한 표에 대응시켜
  틀린 정정을 냈음).
- **수치에 도구·표 이름을 붙임** — "게이트 밖 6 errors" 가 아니라 "게이트 밖 `ruff` 6건"(`H-AN`).
- **한 명령에 여러 단계를 묶지 않음** — 앞 단계 실패를 확인하지 않고 다음을 실행하는 것이
  2026-09-09 에 보존 세션을 파괴했음(`H-AT`).

## 진입 절차

1. **원장을 조회해 태스크 ID 를 말한 뒤 착수함.** 태스크가 없는 일이면 **먼저 등록함.**
2. 게이트를 `app/backend` cwd 에서 돌려 지표 3 과 대조함. **다르면 그 차이를 먼저 설명함.**
3. **태스크 상태는 원장을, 다음 걸음이 바뀌면 이 파일을** 갱신함. 커밋 뒤 **푸시함.**
4. ⛔ **태스크를 `Done` 으로 올린 같은 턴에 다음 태스크를 조회해 착수함 — 보고로 턴을 끝내지 않음.**
   2026-09-09 에 세 번 어겼고 사용자가 지적함(*"난 계속 작업을 하라고 햇는데"*). 원인은 승인 범위
   오해가 아니라 **태스크 경계에서 확인을 기다리는 습관**이었음. **훅이 이것을 막지 못함** —
   `task-management.md` §9 가 잔여 태스크를 차단 조건에서 **의도적으로 뺐음**(완주를 강제하면 8회
   cap 에 걸려 G1~G5 누락 방지까지 죽음). **멈추는 조건은 셋뿐임**: 승인 밖 항목(결정 40 의 경계) ·
   인계 트리거(≲35%·compact 경고 — 이때는 멈추는 것이 아니라 **마감**) · 사용자가 멈추라고 함.
   ⚠️ **위임해 두고 대기하는 시간에 턴을 끝내지 않음** — 기대값 확보·문서 정정·baseline 스냅샷 같은
   준비 작업이 거의 항상 있음.
