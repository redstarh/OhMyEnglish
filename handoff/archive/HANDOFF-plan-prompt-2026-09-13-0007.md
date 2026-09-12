# Handoff — 계획 프롬프트·배치·시나리오 생성 갈래 · 세션 `ohmyenglish-f4` (마감)

> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 짧게 씀 — 판정 근거를 옮기지 않고
> 태스크 조회와 설계서를 가리킴(`backlog task view <ID> --plain`).
>
> 이전 판은 `handoff/archive/HANDOFF-plan-prompt-2026-09-12-2257.md` 임.
> ⛔ 다른 갈래의 handoff 를 건드리지 않았음 — `HANDOFF-pronunciation.md` 는 발음 축 소유임
> (지금 세션 `ohmyenglish-d9` 가 `TASK-128.1`·`.2` 진행 중).

최종 갱신 2026-09-12 · 브랜치 `design/first-vertical-slice`

---

## ① 이 세션이 한 것

**닫은 태스크**: `TASK-4`(AC 4/4) · `TASK-102` AC#3·#4.
**받은 사용자 결정 여섯**: 73(배치 단위는 대화 상황) · 74(신규는 최근 10회 안에 안 나온 상황 ·
창 10 은 유도값) · 75(업무 6종을 처음부터 · `level` 은 `A2`) · 76(시드 배열 순서가 노출 순서) ·
77(분야는 기존 `category` 값역을 늘려 담음) · 78(상황 30개가 돼도 비율은 그대로) ·
79(5회 질문은 음성 대화 · 생성은 세션 뒤 job) · 80(사용자가 만든 상황은 신규 차례 맨 앞).
정본은 `docs/ops/captain-instruction-register.md` 임.

**제품에 들어간 것**: 대화 상황 시드 **3 → 30행**(일상 9 · 업무 9 · 여행 6 · 쇼핑 3 · 진료 3) ·
배치 규칙 `services/scenario_rotation.py`(DB 를 모르는 순수 함수) · `sessions.py` 의 시나리오
서브쿼리를 걷고 `_pick_scenario_for_user` 로 옮김 · 학습 현황 집계와 보고 CLI
(`services/scenario_progress.py` · `scripts/scenario_report.py`) · 무대 파서
`models/scenario_draft.py` · 생성 프롬프트·job 처리 `services/scenario_generator.py` ·
워커 분기 하나. 마이그레이션 **016·017·018** 을 발급·적용했음.

**산출물**: 설계서 둘(`2026-09-12-scenario-rotation-70-30-design.md` ·
`2026-09-12-scenario-generator-design.md`) · 계획서 둘 · 회차
`tests/harness/runs/2026-09-12-task4-rotation-app-path.md`.

⛔ **이 세션의 핵심 교훈**: **초록 게이트가 「요구가 이행됐다」를 뜻하지 않음.** 같은 부류를 네 번
밟았고 동료 갈래와 함께 `H-BP` 로 올렸음. 그 넷은 `TASK-4`(순서를 재는 축이 없었음) ·
`TASK-118` · `TASK-131`(값역 단정이 부분 일치) · `TASK-132`(파서 동일성 주장에 가드 0건)임.

## ② 다음 한 걸음 — `TASK-5` Task 6 (여섯 중 마지막)

`TASK-5` 는 계획서 `docs/design/2026-09-12-scenario-generator-plan.md` 의 여섯 중 **다섯이 끝났음**
(018 · 배치 앞자리 · 파서 · 프롬프트 조립 · job 처리). 남은 Task 6 은 **질문 5개 블록을 세션
프롬프트에 싣고 진입을 배선**하는 것이고 그것만 `nova.py`·`factory.py`·`ws.py` 를 만짐.

⛔ **착수 전에 발음 축이 커밋했는지 확인함.** `factory.create_voice_adapter` 가 유일한 겹침이고
그쪽이 **먼저 닿기로 합의**했음. 그쪽이 넘긴 최종 시그니처(커밋 전 시점):
- `pronunciation_sound: str | None = None` → **`pronunciation_mode: bool = False`**
- 나머지 인자(`settings`·`known_sounds`·`plan`·`questions`·`scenario`·`usage_sink`)는 이름·순서·
  기본값 **전부 그대로**. Task 6 의 블록 재료는 **그 뒤에** 붙이면 충돌하지 않음.
- ⚠️ 전용 모드에서 `known_sounds` 의 **내용**이 달라짐(소켓이 후보 목록을 넘김) — 시그니처는
  그대로지만 그 인자를 읽는 자리가 늘었음.

**나란히 가능**: `TASK-132` AC#1(파서 두 판을 하나로 합칠지 · `Awaiting Decision`) ·
`TASK-130`(노출 순서가 `created_at` 에 얹혀 있음) · `TASK-122`(빈 이름 키 · `low`).

⚠️ **`TASK-102` 는 `TASK-5` 를 선행으로 기다림** — 남은 AC#1·#2 가 대화형 생성이라 그 태스크가
끝나면 함께 닫힘.

## ③ 착수 전 필수 — 7개

1. ⛔ 태스크를 새로 열기 전에 **결정 대장과 원장을 함께** `grep` 함. 이 세션이 `TASK-4` 를 끝낸
   **뒤에야** `TASK-102`(같은 요구의 원문)를 발견했음.
2. ⛔ **부분 실행에 `-c pyproject.toml`** 을 붙임(`H-AJ`). 빼면 `asyncio` 모드가 안 걸려 기존
   테스트가 거짓 빨강이 됨.
3. ⛔ **게이트는 cwd `app/backend`**(`H-A`·`H-BN`). 리포 루트에서 부르면 `line-length` 를 88 로 잼.
4. ⛔ **`ty` 는 절대경로 `/Users/redstar/.local/bin/ty`** — 이름만으로는 **exit 127** 임.
5. ⛔ `git add <디렉터리>` 금지(`H-BE`) · 커밋 **전** `git diff --cached --name-only` · push **전**
   `git log --oneline origin/<브랜치>..HEAD`(`H-BO`).
6. ⚠️ 마이그레이션 번호는 적용 직전 `schema_migrations` 조회로 발급함(`H-AL`) — **이 마감 시점의
   최대는 `018`** 임. ⛔ `drop`+`add` 로 CHECK 를 다시 세울 때 **기존 값 전부를 조회로 읽어** 옮김
   (초안이 `review` 를 빠뜨려 조용히 지울 자리였음).
7. ⛔ **`db_pool` 픽스처는 아무것도 정리하지 않음** — 손으로 지움. **사용자를 먼저** 지워야
   세션·발화·job 이 cascade 되고 그 뒤에 무대를 지울 수 있음(반대 순서는 FK 위반).

## ④ 인계 지표 — 이 마감 시점에 직접 돌려 얻음

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`0de0b87` 이상**(그 앞이 `209070e`) · ⛔ **`origin` 보다 2 앞섬(미푸시)** · 내 미커밋 **0건**. ⚠️ 이 표를 담은 커밋이 뒤에 붙으므로 **등호를 요구하지 않음** — 발음 축이 같은 브랜치에 커밋하면 더 앞섬. 미푸시 이유는 아래 ⚠️ |
| 2 | 다음 걸음 | **`TASK-5` Task 6** (계획서 여섯 중 마지막). `Awaiting Decision` 1건 = `TASK-132` AC#1 |
| 3 | 게이트 | ⛔ **전체는 빨강임** — `pytest` **25 failed · 1051 passed** · `ruff check .` 1 · 게이트 밖 `check` 1 · `format` 1 · `ty` 4 diagnostics. ⚠️ **원인이 전부 발음 축의 미커밋임**(아래). **내 파일만 골라 잰 값은 전부 초록**: `tests/unit` 에서 그 둘 제외 **618 passed** · 내가 만진 앱 7파일·테스트 8파일·스크립트 2파일에 `ruff check` 0 · `format --check` 0 |
| 4 | 착수 전 필수 | 7개(③) |

⚠️ **게이트 빨강의 원인을 갈라 적음 — 다음 세션이 회귀로 읽지 않게 함.** 실패한 파일은 넷이고
전부 세션 `ohmyenglish-d9` 가 `TASK-128.1`·`.2` 로 편집 중인 것임: `tests/integration/test_ws.py`
(23건) · `test_gateway.py` · `tests/unit/test_nova.py` · `test_ws_mode.py`. 수집 오류 둘은
`_known_sounds_block`(`nova.py`) · `_pronunciation_candidates`(`ws.py`) import 실패임.

⛔ **그래서 원경에 올리지 않았음.** 빨간 상태를 올리면 다음 사람이 회귀로 읽음. 그쪽이 커밋해
초록으로 되돌린 뒤 push 하면 **`209070e` 도 같이 올라감**(같은 브랜치 · `H-BO` 의 기전). 그쪽이
그때 커밋 열거를 이 창에 남기기로 했음.

## ⑤ 이 세션이 얻은 규율

- ⛔ **비율이 맞는다는 것과 순서가 맞는다는 것은 다른 단정임.** `TASK-4` 에서 게이트 여섯이
  초록인데 업무 상황이 12회 세션에서 0회였음 — 재는 축이 빠지면 게이트는 그 축에 침묵함.
- ⛔ **지목과 전수는 다른 단정이고, 전수의 축도 이름이 아니라 «부류» 로 잡음.** `_json_candidates`
  하나만 grep 하면 인접 축(`_FENCED`)의 기존 가드를 못 봄.
- ⛔ **단정의 판별력을 따로 잼** — 무력화해서 red 를 본 뒤 초록을 믿음. `starved == 0` 은 후보가
  창보다 많으면 구조적으로 늘 참이었음.
- ⚠️ **좋은 문장을 다른 자리에 재사용할 때 그 자리에서 참인지 먼저 확인함.** 「쓰는 코드가 없는
  값이라」가 한 값역에서 참이고 다른 값역에서 거짓이었음.
- ⚠️ **테스트 격리가 파일 순서에 의존하면 그 순서도 재는 축의 일부임.** 전체 실행에서 초록이었고
  순서를 바꿔 돌려서야 드러났음.
