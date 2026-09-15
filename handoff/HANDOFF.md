# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-15 23:06 KST**(마감 `session-wrap`) · 세션 `ohmyenglish-65` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-15/HANDOFF-2306.md` 에 있음**(그 앞 판 셋도 같은 폴더).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 상태 정본은 원장(`backlog/`), 근거
> 정본은 **태스크 노트 · `tests/harness/runs/**` · `docs/ops/captain-instruction-register.md`** 임.
>
> ⚠️ **역할**: 이 세션은 사용자 지시로 **구현까지** 했음(결정 103 을 이 세션에 대해 연장).
> ⛔ **새 세션은 기본값(통합 테스트)에서 출발하고 열려 있는지 확인함.**

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`85108d1`** · `origin` 과 **0/0**(push 완료) · 미커밋은 미추적 `paseo.json` 하나(내 것 아님 · 사용자가 「그대로 둠」으로 정했음). ⚠️ **이 판을 담은 커밋이 그 뒤에 오므로 새 세션 `HEAD` 는 더 뒤일 수 있음** — 그 뒤 커밋은 handoff·원장 갱신뿐이므로 게이트 수치가 같으면 실질 일치임(`H-P`) |
| 2 | 다음 한 걸음 | **`TASK-61.8`** — PRD Voice Control 의 남은 명령 넷. 착수 조건이 **사용자 판단**임(AC#1). 나머지 5건은 전부 파킹 |
| 3 | 게이트 | **여섯 다 초록 · 전부 exit 0** — `pytest` **1232 passed**(14.49s) · `ruff check` · `ruff format --check` **49 files** · `ty check` · 프론트 `npx tsc --noEmit`(0줄) · `npx eslint .`(0줄) |
| 4 | 착수 전 필수 | 아래 ③. 잔여 **6건**(전부 `To Do` · In Progress **0** · 전체 **183** · 완료 **177**) |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --exclude-status Done --plain
cd app/backend && ./.venv/bin/pytest -q && ./.venv/bin/ruff check . && ~/.local/bin/ty check
cd ../frontend && npx tsc --noEmit && npx eslint .
```

## ① 이번 세션이 한 것 — 음성 명령 둘을 열고 한국어 침묵을 원인까지 좁혀 닫았음

**닫은 태스크 3건**: `TASK-61.6`(주간 리포트 보기) · `TASK-61.7`(다음 문제) · **`TASK-61.5`**(한국어 침묵).
**새로 등록 2건**: `TASK-61.7` · `TASK-61.8`.
**결정 등재 3건**: **107**(리포트 보기의 계약 셋) · **108**(다음 문제 · 학습자 요청이 드릴 예산보다
우선) · **109**(제어 tool 에 `toolResult` 를 돌려보냄 — ⛔ **결정 106 을 뒤집음**).
**회차 3건**: `runs/2026-09-15-task61-6-report-command` · `…-task61-7-next-question` ·
`…-task61-5-toolresult`.

**실물 사용**: Nova **11세션** · Claude **0회**. **픽스처 여덟 신설**(`vc09`~`vc16`).
**함정 등재 1건**: `H-BU`(Next 16 이 프론트 사본의 `node_modules` 심볼릭 링크를 거부함).

## ② 지금 상태 — 음성 명령 셋이 두 언어에서 돌음

- **받는 명령 셋**: 종료(확인 있음) · 주간 리포트 보기 · 다음 문제(둘은 확인 없음).
  확인 필요 여부의 판정은 앱이 갖음(`models/voice_command.requires_confirmation`).
- ✅ **한국어 침묵이 닫혔음**(결정 109). 근본 원인은 앱이 `toolResult` 를 안 보내 `stopReason:
  TOOL_USE` 로 닫힌 턴을 모델이 이어갈 수 없었던 것임 — 계측으로 확정했고 설계서 F6 이 「1회
  관측이라 미검증」이라 적어 둔 자리였음. **제어 tool 에만** 결과를 보냄(발음 tool 은 안 건드림).
- **규칙 13 이 명령별로 갈렸음**: 종료는 소리로 **먼저** 묻고, 확인 없는 둘은 tool 을 먼저 부르고
  **결과를 받은 뒤 한 번만** 말함. 뒤쪽이 `toolResult` 가 만든 영어 중복 발화를 닫은 것임.
- ⛔ **남은 구멍 하나**: 영어 표지의 ASR 이 불안정함(결정 105 로 대가를 받아들였음). 이번에도
  `end` 가 `and` 로 전사된 예가 있었으나 표지가 살아 tool 은 왔음. 크기는 앱의
  `표지가 없는 턴의 음성 명령…` warning 건수로 셈.
- ⚠️ **화면이 수행하는 명령은 리포트 보기 하나**임 — `next_question` 에 화면이 반응하지 않는 것은
  누락이 아니라 계약임(결정 108 ②).

## ③ 착수 전 필수 — 앞 판에서 유효한 것 + 이번 세션 실측

1. ⛔ **게이트 도구는 `python3` 에 없음** — `app/backend/.venv/bin/` 이고 `ty` 만 `~/.local/bin` 임.
   프론트는 `app/frontend` 에서 `npx tsc --noEmit` · `npx eslint .`. ⚠️ **툴 호출 사이에 cwd 가
   남으므로** 긴 절차에서는 절대 경로를 씀.
2. ⛔ **`git add <디렉터리>` 금지** · 커밋 전 `git diff --cached --name-only`.
3. ⛔ **검증 전용 스택 규약**: DB 소유자 `ohmy` · `WORKER_ENABLED=false` · 끝나면 죽이고 drop.
   ⚠️ **dev DB 표 건수를 여기에 적지 않음**(`browser_leg.md` §8-3 — 여러 세션이 같은 DB 를 써서
   낡음). 불변 지표만 적음: `schema_migrations` **22**. 그 시점 값은 회차 기록이 갖음.
4. **브라우저 레그 조합**(이번 세션에 열한 번 통했음): 전용 Chrome `:9333` + 프론트 사본
   `/tmp/fe-*`(`.env.local` 로 백엔드 지정 · 픽스처를 그 사본의 `public/harness/` 에 복사) +
   래퍼 백엔드 `:8012`(`/tmp/*_app.py` 가 `FRONTEND_ORIGIN` 만 갈아 끼움). ⛔ `:9222` 는 남의 것.
   ⛔ **`node_modules` 는 하드링크로 복사함**(`cp -Rl`) — 심볼릭 링크는 Next 16 이 거부함(`H-BU`).
5. ⚠️ **드라이버 대기 조합이 관측을 정하고 방향이 둘임** — 코치가 침묵하는 팔에서 둘째 픽스처를
   흘리려면 `--next-wait-ms` 를 **작게**(6000/25000), 코치의 질문을 **들은 뒤** 명령을 흘리려면
   **크게**(30000). 뒤쪽이 「질문이 바뀌었는가」를 재는 조건임.
6. **어댑터가 받은 이벤트를 계측하는 방법**(이번에 근본 원인을 가른 수단): 회차 래퍼에서
   `NovaEventTranslator.translate` 를 감쌈. ⛔ **로그는 어댑터 자신의 로거 + `warning` 으로 남김** —
   전용 로거 + `info` 는 uvicorn 설정에서 전파되지 않아 출력이 0건이었음.
7. **계획이 실린 세션을 만드는 방법**: dev DB 의 최신 `session_plans` 한 행을 옮김(손으로 조립하지
   않음). ⚠️ `learning_sessions.mode` 는 **not null 이고 기본값이 없어** 명시해야 함.
   ⚠️ `focus_pattern_ids` 는 배열이라 FK 가 없어 dev 값을 그대로 넣을 수 있음.
8. ⚠️ **`p_app_path.py` 는 세션 하나만 돌림** — 한 문서에 두 세션을 돌리면 관측이 덮임.
9. ⚠️ **ASR 이 표지·낱말을 다시 씀** — `Oh My English` → `all my english` · `end` → `and`.
   전사문을 먼저 읽어 「모델이 무엇을 들었나」를 가름.

## ④ 열린 태스크 6건 — 전부 «지금 열 자리가 아닌» 이유가 적혀 있음

| 태스크 | 왜 열려 있나 |
|---|---|
| `TASK-61.8` | PRD 의 남은 명령 넷(추가 학습·일시 정지·모드 변경·학습 계속). 착수 조건이 사용자 판단임. ⚠️ 노트가 「수행 주체」 판정 축이 결정 109 로 **해소됐음**을 적어 뒀음 |
| `TASK-78.1` | 결정 101 로 파킹. AC#2 는 닫혔고 AC#1(문턱)을 지금 정하지 않음 |
| `TASK-116.5` | 문장 인용 구멍 2/59 — 측정하고 파킹함 |
| `TASK-122`(LOW) | AC#3 이 조건부이고 판정이 「지금 고치지 않는다」임 |
| `TASK-39` | AC#2 를 결정 96 이 보류(Phase 2 운영 관찰 시점) |
| `TASK-41` | 결정 31 이 「모든 구현이 끝난 뒤 다시 올린다」로 미룸 |

## ⑤ 착수 전 반드시 읽을 것

- **결정 107·108·109** — 정본은 `docs/ops/captain-instruction-register.md` 머리 근처임. 특히
  **109** 와 그 후속 절(규칙 13 을 명령별로 가른 근거), 그리고 **결정 106** 머리의 뒤집힘 표시.
- **회차 셋** — 특히 `task61-5-toolresult` §1(계측으로 원인을 가른 자리)과 §2 의 세션 일곱 표.
- ⚠️ **알고 남긴 것 하나**: `paseo.json` 이 미추적으로 떠 있음(3바이트 `{}` · 내 것 아님).
  **사용자가 「그대로 둠」을 골랐음** — 그래서 In Progress 가 0건이면 원장 게이트 G1 이 매 턴 이
  파일로 발동함. 조용히 만들려면 `.gitignore` 한 줄이 가장 싸고, 세션 단위로 내리려면
  `BACKLOG_GATE=0` 임. ⛔ 태스크를 억지로 In Progress 로 올려 통과시키지 않음.
