# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-16 03:48 KST** · 세션 `ohmyenglish-42` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-16/HANDOFF-0348.md` 에 있음**(그 앞 판들도 같은 폴더).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 상태 정본은 원장(`backlog/`), 근거
> 정본은 **태스크 노트 · `tests/harness/runs/**` · `docs/ops/captain-instruction-register.md`** 임.
>
> ⚠️ **역할**: 이 세션은 사용자 지시로 **구현까지** 했음(2026-09-16 03시 KST 에 결정 103 을 이
> 세션에 대해 연장하고 「이후 작업 사전 승인」을 받았음).
> ⛔ **새 세션은 기본값(통합 테스트)에서 출발하고 열려 있는지 확인함.**

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`9048522`** · `origin` 과 **0/0**(push 했음) · **미커밋 0건**. ⚠️ **이 판을 담은 커밋이 그 뒤에 오므로 새 세션 `HEAD` 는 더 뒤일 수 있음** — 그 뒤 커밋은 handoff 파일뿐이므로 게이트 수치가 같으면 실질 일치임 |
| 2 | 다음 한 걸음 | **없음 — 잔여 8건이 전부 파킹이거나 사용자 판단을 기다림.** ⛔ **`TASK-61.13` 을 바로 열지 않음**(아래 ⑤) |
| 3 | 게이트 | **여섯 다 초록 · 전부 exit 0** — `pytest` **1239 passed**(15.78s) · `ruff check` · `ruff format --check` **49 files** · `ty check` · 프론트 `npx tsc --noEmit`(0줄) · `npx eslint .`(0줄) |
| 4 | 착수 전 필수 | 아래 ③. 잔여 **8건**(전부 `To Do` · In Progress **0** · 전체 **188** · 완료 **180**) |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --exclude-status Done --plain
cd app/backend && ./.venv/bin/pytest -q && ./.venv/bin/ruff check . && ~/.local/bin/ty check
cd ../frontend && npx tsc --noEmit && npx eslint .
```

## ① 이번 세션이 한 것 — 모드 변경을 접고, 그 자리에서 나온 구멍을 재서 문면을 뒤집었음

**닫은 태스크 2건**: `TASK-61.10`(모드 변경) · `TASK-61.12`(종류를 말하지 않은 요청).
**새로 등록 2건**: `61.12` · **`61.13`**(코치의 말과 앱 상태가 갈린 모양).
**결정 등재 1건**: **111**(모드 변경은 별도 명령이 아니고 `start_additional` 의 `target` 이 수행함).
**회차 2건**: `runs/2026-09-16-task61-10-mode-change` · `runs/2026-09-16-task61-12-unspecified-mode`.
**커밋 셋**: `6e04887`(구현) · `cf91207`(회차) · `9048522`(문면 뒤집음 + 둘째 회차).

**실물 사용**: Nova **15세션** · Claude **0회**. **픽스처 여섯 신설**(`vc21`~`vc26`).
**계측 하나 신설**: 래퍼에서 `NovaEventTranslator.translate` 를 감싸 제어 이벤트의
`command`·`stage`·`target` 을 남김(`control-events.log`).

## ② 지금 상태 — 음성 명령 넷 + 모드 변경이 그중 하나로 접혔음

- **받는 명령은 여전히 넷임**(`end` · `start_additional` · `show_report` · `next_question`).
  ⛔ **정본은 `models/voice_command.ControlCommand` 임** — 지시문 머리말의 열거를 없앴음(낡았음).
- ✅ **모드 변경이 성립함** — 「발음 연습 모드로 바꿔 줘」·「switch to pronunciation mode」가 두 언어
  **2/2** 로 새 세션의 `mode='pronunciation'` · `learning_source='additional'` 을 만들었음.
- **종류를 말하지 않은 요청에 되묻게 만들었음** — 되묻기 **0/4 → 3/5**. ⛔ **결정적이지 않음**:
  문면은 확률을 옮기고 거동을 보장하지 않음.
- ⛔ **안전을 지키는 것은 문면이 아니라 앱임** — 모델은 종류를 못 들어도 `requested` 를 추측한
  `conversation` 으로 부름(**3/3**). 세션이 그것으로 열리지 않는 이유는 `CONFIRMATION_REQUIRED`
  하나임. 「예」만 답한 팔에서 코치가 **다시 되물었고** 세션이 갈리지 않았음(1/1).
- ⚠️ **영어 표지의 ASR 은 그대로 불안정함**(결정 105 의 대가). 이번 세 회차에서
  `표지가 없는 턴의 음성 명령…` warning 은 **0건**이었음.

## ③ 착수 전 필수 — 앞 판에서 유효한 것 + 이번 세션 실측

1. ⛔ **게이트 도구는 `python3` 에 없음** — `app/backend/.venv/bin/` 이고 `ty` 만 `~/.local/bin` 임.
   프론트는 `app/frontend` 에서 `npx tsc --noEmit` · `npx eslint .`. ⚠️ **툴 호출 사이에 cwd 가
   남으므로** 긴 절차에서는 절대 경로를 씀.
2. ⛔ **`git add <디렉터리>` 금지** · 커밋 전 `git diff --cached --name-only`.
3. ⛔ **검증 전용 스택 규약**: DB 소유자 `ohmy` · `WORKER_ENABLED=false` · 끝나면 죽이고 drop.
   불변 지표만 적음: `schema_migrations` **22**(공유 dev DB 도 22 로 무변경 확인했음).
   ⚠️ 새 DB 를 `migrate.py` 로 만들면 **22 가 나오는 것이 정상임** — `db/migrations` 파일이 22개고
   002·008 은 애초에 없음(이번에 확인했음).
4. **브라우저 레그 조합**(이번 세션에 두 번 통했음): 전용 Chrome `:9333` + 프론트 사본
   `/tmp/fe-*`(`.env.local` 로 백엔드 지정 · 픽스처를 **그 사본의** `public/harness/` 에 복사) +
   래퍼 백엔드 `:8012`(`/tmp/*_app.py` 가 `FRONTEND_ORIGIN` 만 갈아 끼움). ⛔ `:9222` 는 남의 것.
   ⛔ `node_modules` 는 **하드링크 복사**(`cp -Rl` · 6.4초). 심볼릭 링크는 Next 16 이 거부함(`H-BU`).
   ⚠️ **드라이버가 쓰는 픽스처를 하나라도 사본에 안 넣으면 404 로 죽음** — 이번에 한 번 밟았음.
5. ⛔ **문면을 고친 뒤에는 회차 백엔드를 재기동하고 P5 를 돌림** — `--reload` 가 없어 그대로 두면
   **낡은 지시문을 잼.** 이번에 재기동 뒤 `소스 49건 → 통과` 를 직접 확인했음.
6. ⛔ **`recv.voice_command` 로 「무엇을 불렀는가」를 판정하지 않음** — 그것은 프레임 수이고 어느
   명령·어느 `target` 인지는 구별하지 못함. **어댑터 계측이 필요함**(래퍼에서 `translate` 를 감쌈 ·
   로그는 **어댑터 자신의 로거 + `warning`**).
7. ⚠️ **warning 0건이 「모델이 tool 을 불렀다」를 뜻하지 않음** — 「안 불렀음」과도 양립함.
   이 유도를 한 번 틀렸고 `task61-10` 회차 README 에 정정으로 남겼음.

## ④ 열린 태스크 8건 — 전부 «지금 열 자리가 아닌» 이유가 적혀 있음

| 태스크 | 왜 열려 있나 |
|---|---|
| `TASK-61.13` | 코치의 말과 앱 상태가 갈린 모양. **지금 열지 않음** — 이유는 ⑤ |
| `TASK-61.9` | 일시 정지. AC#1 이 **마이그레이션의 dev DB 적용 여부를 사용자 판단으로** 요구함 |
| `TASK-61.11` | 학습 계속. 「계속」의 뜻부터 사용자 판단임 |
| `TASK-78.1` | 결정 101 로 파킹. AC#2 는 닫혔고 AC#1(문턱)을 지금 정하지 않음 |
| `TASK-116.5` | 문장 인용 구멍 2/59 — 측정하고 파킹함 |
| `TASK-122`(LOW) | AC#3 이 조건부이고 판정이 「지금 고치지 않는다」임 |
| `TASK-39` | AC#2 를 결정 96 이 보류(Phase 2 운영 관찰 시점) |
| `TASK-41` | 결정 31 이 「모든 구현이 끝난 뒤 다시 올린다」로 미룸 |

## ⑤ 착수 전 반드시 읽을 것

- **결정 111** — 정본은 `docs/ops/captain-instruction-register.md` 머리 근처임. 흡수의 뜻이
  「요구를 버린 것이 아니라 수행 주체가 바뀐 것」이라는 대목을 먼저 읽음.
- **회차 둘의 §3** — 특히 `task61-12` §3 의 「고쳤다로 적지 않고 확률을 옮겼다로 적음」.
- ⛔ **`TASK-61.13` 을 바로 열지 않은 이유** — 회차가 다음 회차의 findings 를 만드는 사슬이 두 번
  이어졌음(`61.10` → `61.12` → `61.13`). 그 자리에서는 라운드를 더 도는 것이 아니라 **멈추고
  등재하는 것**이 규율임. 열려면 **문면 미준수의 크기를 재는 회차 하나**로 시작하고, 그 회차가 또
  새 findings 를 만들면 **라운드가 아니라 게이트를 바꿈.**
- ⚠️ **`TASK-61.9` 는 공유 dev DB 에 마이그레이션을 적용할지 묻는 자리임** — 사용자 승인 전에
  적용하지 않음(전역 DB 규약).
