# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-15 14:13 KST** · 세션 `ohmyenglish-65` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판 셋은 `handoff/backup/2026-09-15/` 에 있음**(`…-0034.md` · `…-0229.md` · `…-1413.md`).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 상태 정본은 원장(`backlog/`), 근거
> 정본은 **태스크 노트 · `tests/harness/runs/**` · `docs/ops/captain-instruction-register.md`** 임 —
> 여기서 수치를 다시 세지 않음.
>
> ⚠️ **이 세션에서 역할 경계가 바뀌었음** — 사용자가 통합 테스트에 한정하지 않고 구현·마이그레이션
> 적용까지 지시했음(결정 103). ⛔ **새 세션은 기본값(통합 테스트)에서 출발하고 열려 있는지 확인함.**

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`4a20107`** · `origin` 과 **0/0** · 미커밋은 미추적 `paseo.json` 하나(내 것 아님 · 3바이트 `{}`) |
| 2 | 다음 한 걸음 | **없음 — 잔여 7건이 전부 파킹임.** 마지막으로 닫은 것은 `TASK-61.5` 의 원인 가르기이고 사용자가 결정 106 으로 「그대로 둠」을 골랐음. 착수하려면 `TASK-61.6`(PRD 의 남은 명령)의 첫 AC 가 사용자 판단을 요구함 |
| 3 | 게이트 | **여섯 다 초록** — `pytest` **1222 passed**(15.8s) · `ruff check .` · `ruff format --check .` **49 files** · `ty check` · 프론트 `npx tsc --noEmit` · `npx eslint .`(둘 다 0줄) |
| 4 | 착수 전 필수 | 아래 ③. 잔여 **7건**(전부 `To Do` · In Progress 0 · 전체 187 · 완료 180) |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --exclude-status Done --plain
cd app/backend && ./.venv/bin/pytest -q && ./.venv/bin/ruff check . && ~/.local/bin/ty check
cd ../frontend && npx tsc --noEmit && npx eslint .
```

## ① 이번 세션이 한 것 — 발음 축의 관측을 닫고 음성 명령 첫 조각을 만들었음

**닫은 태스크 9건**: `TASK-139`(dev DB 에 024 적용) · `TASK-61`(부모) · `61.1`·`61.2`·`61.3`·`61.4` ·
그리고 `TASK-78.1` AC#2 는 닫고 태스크는 파킹으로 되돌렸음.
**새로 등록 5건**: `TASK-139` · `61.1`·`61.2`·`61.3`·`61.4`·`61.5`·`61.6`.
**결정 등재 5건**: **101**(위임분 99·100 을 사용자가 유지로 확정) · **102**(음성 명령 첫 조각의 제품
계약 넷) · **103**(이 세션의 역할 경계를 넓힘) · **104**(D3 을 프롬프트로 · D5 는 앱이 표지를 요구) ·
**105**(표지를 `ohmyenglish` 와 한국어로 둠).

**회차 5건** (`tests/harness/runs/`): `2026-09-15-task78-1-defenses-in-use` ·
`2026-09-15-task139-analysis-row-real-path` · `2026-09-15-task139-dev-db-apply` ·
`2026-09-15-task61-3-voice-command-app-leg` · `2026-09-15-task61-4-refix-verify` ·
`2026-09-15-task61-5-korean-voice`.

**실물 사용 합**: Nova **15세션** · Claude **3회**. ⚠️ `llm_calls` 로는 셀 수 없음(하네스가
`usage_sink` 를 주입하지 않음) — 회차 기록에서 합한 값임.

**리포에 더한 것**: 픽스처 일곱(`tests/harness/fixtures/voice/vc0*.wav` · macOS TTS · 생성 명령은
`task61-3` 회차 §0) · 하네스 확장 하나(`p_app_path.py` 의 계수기에 `voice_command` 키).

## ② 지금 상태 — 음성 종료 명령이 실사용에서 돌지만 구멍 둘이 남았음

- **도는 것**: 표지가 살아난 발화 → tool `requested` → 확인 답 → tool `confirmed` → 세션이 닫힘.
  기록은 `voice_command` 1행 + `command_confirmation` 1행이고 `learning` 오염이 없음(실측).
- **결정 102 ③(음성 확인)이 오인식을 실제로 막았음** — 표지 없는 발화를 모델이 명령으로 읽었는데도
  확인이 오지 않아 세션이 닫히지 않았음(`task61-3` ARM-C).
- ⛔ **구멍 ①**: 영어 표지의 ASR 이 불안정함 — 같은 합성 픽스처에서 **6회 중 1회**만 `oh my english`
  로 왔고 나머지는 `all my english` 임. 사용자가 결정 105 로 그 대가를 받아들였고, 크기는 앱의
  `표지가 없는 턴의 음성 명령…` warning 건수로 셈.
- ⛔ **구멍 ②**: **한국어 명령에서 코치가 침묵함**(누적 0/4). 프롬프트에 한국어 예시를 더한 판을
  시험해 **원인 후보 ①(프롬프트)을 반증**하고 그 판을 되돌렸음 — 남은 후보는 Nova 의 거동임
  (`TASK-61.5`).
- **발음 축**: 오염 방어 넷이 실사용에서 함께 도는 것을 관측했음(`task78-1` 회차) · 분석 기원 기록의
  3줄 카드도 실물 분석 경로에서 확인했음(`task139-analysis-row-real-path`).

## ③ 착수 전 필수 — 앞 판에서 유효한 것 + 이번 세션 실측

1. ⛔ **게이트 도구는 `python3` 에 없음** — `app/backend/.venv/bin/` 이고 `ty` 만 `~/.local/bin` 임.
   프론트 게이트는 `app/frontend` 에서 `npx tsc --noEmit` · `npx eslint .` 임.
   ⚠️ **툴 호출 사이에 cwd 가 남음** — 긴 절차에서는 절대 경로를 씀.
2. ⛔ **`git add <디렉터리>` 금지** · 커밋 전 `git diff --cached --name-only`.
3. ⛔ **검증 전용 스택 규약**: DB 소유자 `ohmy` · `WORKER_ENABLED=false` · 끝나면 죽이고 drop.
   **dev DB 기준선(2026-09-15 실측)**: `learning_sessions=17` · `pronunciation_attempts=7` ·
   `error_patterns=9` · `session_plans=6` · `utterances=128` · `review_tasks=15` ·
   **`schema_migrations=22`**(024 적용 뒤 값임 — 이전 판의 21 이 아님).
4. **브라우저 레그 조합**(이번 세션에 여덟 번 통했음): 전용 Chrome `:9333` + 프론트 사본 `/tmp/fe-*`
   (`.env.local` 로 백엔드 지정 · 픽스처를 그 사본의 `public/harness/` 에 복사) + 래퍼 백엔드 `:8012`
   (`/tmp/*_app.py` 가 `FRONTEND_ORIGIN` 만 `:3001` 로 갈아 끼움 · 앱 코드를 고치지 않음).
   ⛔ `:9222` 는 다른 세션 것임.
5. ⚠️ **드라이버 대기 조합이 관측을 정한다** — 코치가 침묵하는 팔에서 둘째 픽스처를 흘리려면
   **`--next-wait-ms` 를 `--settle-ms` 보다 훨씬 작게** 둠(실측: 6000 / 25000 으로 확인 턴이 생겼음).
   그 반대 조합이면 `settle` 이 먼저 끝나 확인 발화가 흐르지 않음.
6. ⚠️ **공유 dev DB 에서 회차를 돌리면 「되돌릴 대상」을 먼저 스냅샷함** — 행 수만 뜨면 복습 시계
   변동을 놓침. 이번에 합성 전사문이 기존 문법 패턴의 `next_review_at` 을 움직이고
   `daily_error_summary` 행을 만들었고, 되돌릴 값을 준 것은 `pg_dump` 였음(`task139-dev-db-apply` §3).
7. ⚠️ **`p_app_path.py` 는 세션 하나만 돌림** — 한 문서에 두 세션을 돌리면 관측이 덮임.
8. ⚠️ **ASR 이 표지·오류를 다시 쓴다** — `Oh My English` → `all my english` · `blother` → `brother`.
   전사문을 먼저 읽고 「모델이 무엇을 들었나」를 가름.

## ④ 열린 태스크 7건 — 전부 «지금 열 자리가 아닌» 이유가 적혀 있음

| 태스크 | 왜 열려 있나 |
|---|---|
| `TASK-61.5` | 결정 106 으로 파킹. 원인을 「한국어 + tool 호출」 조합으로 좁혔고 고치지 않기로 정했음 |
| `TASK-61.6` | PRD 의 남은 명령 일곱 — 등록만 했음. 착수 조건이 사용자 판단임 |
| `TASK-78.1` | 결정 101 로 파킹. AC#2 는 닫혔고 AC#1(문턱)을 지금 정하지 않음 |
| `TASK-116.5` | 문장 인용 구멍 2/59 — 측정하고 파킹함 |
| `TASK-122`(LOW) | AC#3 이 「고치면 8회 이상으로 재라」는 조건부이고 판정이 「지금 고치지 않는다」임 |
| `TASK-39` | AC#2 를 결정 96 이 보류(Phase 2 운영 관찰 시점) |
| `TASK-41` | 결정 31 이 「모든 구현이 끝난 뒤 다시 올린다」로 미룸 |

## ⑤ 착수 전 반드시 읽을 것

- **결정 101~106** — 정본은 `docs/ops/captain-instruction-register.md` 머리 근처임. 특히 **103**
  (역할 경계)과 **105**(표지의 대가를 받아들인 근거).
- **회차 여섯** — 위 ① 의 목록. 특히 `task61-3` §3(결함 다섯의 재현 절차)과 `task61-4` §6-3
  (D2 를 닫은 팔) · `task61-5` §3(되돌린 프롬프트와 그 근거).
- ⚠️ **미해결로 남긴 관측 하나**: `paseo.json` 이 미추적으로 떠 있음(3바이트 `{}` · 2026-09-14 생성 ·
  내 것 아님). In Progress 태스크가 0건이면 원장 게이트 G1 이 이것으로 발동함 — 사용자 판단 대상임.
