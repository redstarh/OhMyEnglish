# Handoff — OhMyEnglish

> **두 가지만 담는다: 다음 한 걸음 / 착수 전 필수.** 그 밖은 각 정본이 소유하고 여기서는
> **가리키기만** 함. 최종 갱신 **2026-09-09** · 브랜치 `design/first-vertical-slice`
> ⛔ **줄 수·개수를 적지 않는다** — 적는 순간 낡음(`H-O`).
> ⛔ **정리된 결정 이력을 이 파일에 옮기지 않는다** (2026-09-09 사용자 지시). 결정은 번호로만
> 가리킨다 — 본문은 `docs/ops/captain-instruction-register.md` 가 소유함.

## 다음 한 걸음 — `TASK-37`(하네스 5차수) `In Progress`

> 회차 정본은 **`tests/harness/runs/2026-09-09-run-5.md`**(요약) 와 `…-run-5-browser.md`(상세).
> **진행 상태를 여기 재서술하지 않음** — 그 둘과 원장이 가짐.
>
> **남은 것**: `AC#1`(N6·N12·N13 실물) · `AC#3` 의 E4~E6 · `AC#4`(P8·P7 재캡처) ·
> `AC#5` 실행(P9~P12) · `AC#8`·`AC#9`. 끝난 것은 `AC#2`·`AC#6`·`AC#7`.
>
> ⛔ **워커를 켤 때 반드시 읽을 것: `H-AT`.** 2026-09-09 에 워커를 켜서 **보존 세션 2개를
> 파괴했고** 복구에 비용이 들었음. 막는 방법이 그 함정에 있음.
> ⚠️ **실물 호출·워커·재기동은 이제 사전 승인임**(결정 40) — 묻지 않고 진행함.

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
| 1 | **받은 캡틴 결정을 다시 묻지 않음.** 개수를 세지 않음 — register 가 열거함. 최근 것 중 판단을 바꾸는 것: **40**(크리티컬 아닌 것은 사전 승인) · **41**(자격증명 회전 면제) · **42**(첫 푸시 완료) · **27**(008·002 영구 결번) · **31**(스키마 이관은 전부 끝난 뒤) | `docs/ops/captain-instruction-register.md` |
| 2 | ⛔ **critic 재검증 루프를 다시 돌리지 않음.** 4회차까지 갔고 결정 22 가 설계·문서의 리뷰 게이트를 없앴음 | 결정 22 |
| 3 | **설계는 끝났음 — 다시 하지 않음.** 구현 소유자 `TASK-43`·`44`·`45` 전부 `Done`. 남은 UI 는 `TASK-10` 이 소유하고 그 노트에 선점 목록이 있음 | 원장 |
| 4 | ✅ **원격이 붙었고 푸시가 기본 리듬임.** `origin` = `github.com/redstarh/OhMyEnglish` · **PUBLIC** · 기본 브랜치 `main`. ⛔ **남은 잔여 위험**: DB 비밀번호가 **공개 이력에 있음**(결정 41 이 회전 면제). Postgres 가 `localhost` 전용 바인딩이라 한계 위험은 낮으나 0 은 아님. 없애는 선택지 셋은 **결정 42 가 소유함** — 다시 발명하지 않음 | 결정 42·41 |
| 5 | ⚠️ **`backlog task list --ready` 는 상태를 걸러내지 않음** — `Awaiting Decision`·`In Progress` 까지 「착수 가능」으로 뜸. **SessionStart 브리핑의 분류를 믿음** | 이 파일 |
| 6 | ⛔ **워커를 켜기 전에 `H-AT` 를 읽음.** `available_at` 비켜두기만으로는 부족함 — `flush_ended_sessions` 가 **job 을 새로 만듦** | `H-AT` |
| 7 | **함정을 안다** — `H-AT`(워커가 보존 세션을 파괴함) · `H-AS`(문서 기동 명령이 워커를 켬 · 기본값 `True`) · `H-AR`(format 의 N files 가 `.md` 를 셈) · `H-AO`(위임 리뷰가 산출물만 잃고 죽음) · `H-AM`(병렬 dispatch → `git commit -- <path>`) · `H-AJ`(pytest 에 경로만 주면 async 가 죽음) · `H-AL`(완료 태스크의 낡은 노트) · `H-X`(⛔ 동시 `pytest` 금지) · `H-AP`(판별력 확인이 stale `__pycache__` 를 남김) | `docs/ops/pitfalls.md` |
| 8 | **DB 는 공유 인스턴스임**(`:5432`, StockAgent·En-Coach 와). 재시작·`ALTER SYSTEM`·`ALTER DATABASE … SET TimeZone` 금지 | `docs/ops/shared-database-guide.md` |
| 9 | ⚠️ **`.superpowers/**` 는 git 추적 밖임** — critic·리뷰 보고서 전부가 거기 있음. **지우지 않음** | `.superpowers/sdd/2026-09-07-…/` |

## 인계 지표 — **직접 돌려** 얻고 대조함

| # | 지표 | 기준값 (마감 시점에 직접 돌려 얻었음) |
|--:|---|---|
| 1 | `git rev-parse --short HEAD` · `git status` | **`744bb07` 이상**(등호를 요구하지 않음 — `H-P`) · 추적 미커밋 **0건** · `origin` 과 동기 |
| 2 | 원장 — `grep -h "^status:" backlog/tasks/*.md \| sort \| uniq -c` | 전체 **52** · Done **35** · To Do **16** · In Progress **1**(`TASK-37`) · Awaiting Decision **0**. ⛔ `backlog task list --plain \| grep -c "^  TASK-"` 로 세지 않음 — 우선순위 라벨이 붙으면 빠짐 |
| 3 | 게이트 (`app/backend` cwd) | **843 passed** · `ruff check` exit 0 · format **unformatted 0** · `ty check` exit 0 · 게이트 **밖** `ruff check` **0 errors** · format **unformatted 0** · 프론트 `npx tsc --noEmit`·`npx eslint app lib` exit 0 |
| 4 | DB (읽기만) | `schema_migrations` **9건**(`001·003~007·009·010·011`) · `error_patterns` **9** · `error_occurrences` **24** · `utterances` **120** · `review_tasks` **13** · `pronunciation_attempts` **4** · `shadowing_items` **1** · **§8 drift 0** · **보존 세션 6개** 생존. ⚠️ **수치에 표 이름을 붙여 적음** — 이름 없는 묶음은 읽는 사람이 엉뚱한 표에 대응시킴(2026-09-09 실측) |
| 5 | 결과 API 상태 6개 | `210233be` `analyzing` · `6225ddaf` `final`(교정 1) · `b2f0d169` `partial_failure` · `76d9ef31` `connection_failed` · `d127dece` `no_utterances` · **`e0c5e580` `final`(교정 2 — A4-2 표본)**. ⛔ **이 여섯이 `browser_leg.md` §9 의 자산임 — 지우지 않음** |

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
