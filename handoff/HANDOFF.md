# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-15 02:29 KST** · 세션 `ohmyenglish-65` · 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판 둘은 `handoff/backup/2026-09-15/` 에 있음**(`…-0034.md` · `…-0229.md`).
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 상태 정본은 원장(`backlog/`), 근거
> 정본은 **태스크 노트 · `tests/harness/runs/**` · `docs/ops/captain-instruction-register.md`** 임 —
> 여기서 수치를 다시 세지 않음.
>
> ⚠️ **이 세션은 사용자가 자러 간 뒤 위임을 받아 계속 진행했음**(원문은 결정 99 가 가짐).
> ⛔ **위임으로 정한 것과 사용자가 «고른» 것을 결정 대장이 구분해 적었음** — 결정 99·100 이 위임분임.
> 다음 세션은 그 둘을 사용자에게 확인받는 것으로 시작하는 것이 좋음(회수되면 결정이 바뀐 것이 아니라
> 위임이 회수된 것임).

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`461c938`** · `origin` 과 **0/0** · 미커밋은 원장 파일 둘(이 마감이 담음)과 미추적 `paseo.json`(내 것 아님) |
| 2 | 다음 한 걸음 | **`TASK-61`**(음성 명령) — ⛔ 착수하지 않았고 그 이유를 태스크 노트에 적었음(신규 기능이라 사용자가 깨어 있을 때 `brainstorming`→`writing-plans` 로 시작하는 것이 권고임) |
| 3 | 게이트 | **여섯 다 exit 0** — `pytest` **1200 passed**(14.95s) · `ruff check .` · `ruff format --check .` **48 files** · `ty check` · 프론트 `npx tsc --noEmit` · `npx eslint .`(둘 다 출력 0줄) |
| 4 | 착수 전 필수 | 아래 ③. 잔여 **6건**(To Do 5 · In Progress 1 · Awaiting Decision **0** · 전체 174 · 완료 **168 · 97%**) |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --exclude-status Done --plain
cd app/backend && ./.venv/bin/pytest -q && ./.venv/bin/ruff check . && ~/.local/bin/ty check
cd ../frontend && npx tsc --noEmit && npx eslint .
```

## ① 이번 세션이 한 것 — 발음 축을 닫았음

**닫은 태스크 14건**: `TASK-116`(부모) · `116.1`·`116.2`·`116.3`·`116.4` · `TASK-128`(부모) ·
`128.4` · `TASK-129` · `TASK-81`·`81.1` · `TASK-88`·`88.1` · `TASK-78` · `TASK-97` · `TASK-138`.
**새로 등록 6건**: `116.2`·`116.3`·`116.4`·`116.5` · `78.1` · `88.1`(넷은 닫았고 `116.5`·`78.1` 는 파킹).
**결정 등재 6건**: 95·96·97 (사용자가 고름) · 98 (사용자가 고름) · **99·100 (위임으로 정함)**.

**회차 6건** (`tests/harness/runs/`): `2026-09-14-task129-plan-review-key` ·
`2026-09-15-task81-app-leg` · `2026-09-15-task116-3-verdict-condition` ·
`2026-09-15-task116-2-review-excluded-card` · `2026-09-15-task88-p2m-end-to-end` ·
`2026-09-15-task88-1-analysis-row-screen` · `2026-09-15-task116-5-quote-shapes`.

**실물 사용 합**: Nova **7세션**(`TASK-129` 4 · `TASK-81` 3) · Claude **5회**(계획 4 · 분석 1).
⚠️ `llm_calls` 로는 셀 수 없음(하네스가 `usage_sink` 를 주입하지 않음) — 손으로 센 값임.

**하네스 확장 하나**: `p_app_path.py` 가 `--wav` 를 쉼표 목록으로 받고 둘째부터 **코치 턴 뒤**에 흘림.

## ② 지금 상태 — 발음 축의 오염 경로는 막혔고, 어긋남 자체는 남아 있음

- **어긋남은 13/13 으로 거의 항상 남**(모드·레그 무관 · `TASK-116` AC#1 집계). 결정 82 가
  「프롬프트를 더 고치지 않는다」로 정했으므로 그것이 현재 규약임.
- **막은 것**: 복습 전진 배제(116.1) · 일반 세션에서 검사가 발화하게 함(116.3 · 결정 98) ·
  증거 갈림에서 정상 기록 보호(116.4) · 화면이 그 사실을 말함(116.2 · 결정 95) ·
  분석 기원 기록의 내용과 화면 갈래(88.1 · 결정 99).
- ⛔ **아직 관측되지 않은 것**: 그 방어들이 **실사용에서** 도는 모습. `TASK-78.1` AC#2 가 그 관측을
  요구하고, 그것이 우회로 제거(결정 50 ③)의 전건임.
- **알려진 구멍 하나**: 문장 전체 인용은 검사가 판정하지 못함 — 세션 단위 **2/59** 로 재고 파킹함
  (`TASK-116.5`).

## ③ 착수 전 필수 — 앞 판에서 유효한 것 + 이번 세션 실측

1. ⛔ **게이트 도구는 `python3` 에 없음** — `app/backend/.venv/bin/` 이고 `ty` 만 `~/.local/bin` 임.
   게이트는 cwd `app/backend` 에서 돌림. 프론트 게이트는 `app/frontend` 에서 `npx tsc --noEmit` ·
   `npx eslint .` 임(이번 세션에 `tsc` 가 실제로 계약 구멍을 잡았음).
   ⚠️ **툴 호출 사이에 cwd 가 남음** — 긴 절차에서는 절대 경로를 씀.
2. ⛔ **파이프 뒤의 `$?` 는 마지막 명령 것임** — `cmd > /tmp/out 2>&1; echo "exit=$?"` 로 받음.
   ⚠️ **`pytest` 에 파일 경로를 직접 주면 `asyncio_mode=auto` 가 안 걸림**(rootdir 이 바뀜) —
   `-k` 로 고름(실측: async 테스트가 「plugin 없음」으로 실패했음).
3. ⛔ **`git add <디렉터리>` 금지** · 커밋 전 `git diff --cached --name-only`.
4. ⛔ **태스크를 열기 전에 결정 대장과 원장을 함께 `grep`** 함 — 이 세션이 그것으로 「이미 닫힌 판단
   둘」과 「낡은 AC 문면 둘」(`TASK-78` AC#4 · `TASK-128.4` AC#1)을 찾았음.
5. ⛔ **검증 전용 스택 규약**: DB 소유자 `ohmy` · `WORKER_ENABLED=false` · 끝나면 죽이고 drop.
   **dev DB 기준선(2026-09-15 실측)**: `learning_sessions=17` · `pronunciation_attempts=7` ·
   `error_patterns=9` · `session_plans=6` · `utterances=128` · `review_tasks=15`.
6. **브라우저 레그 조합**(이번 세션에 네 번 통했음): 전용 Chrome `:9333`(마이크가 필요하면
   `--use-fake-device-for-media-stream` 를 더함) + 프론트 사본 `/tmp/fe-*`(`cp -Rc` 3초 ·
   `.env.local` 로 백엔드 지정) + 래퍼 백엔드 `:8012`(`/tmp/*_app.py` 가 `:3001` origin 을 CORS 에
   더함 · 앱 코드를 고치지 않음). ⛔ `:9222` 는 다른 세션 것임.
7. ⚠️ **화면 문구가 한순간만 페인트되면 폴링으로 못 잡음** — 클릭 «전»에 `MutationObserver` 를 걸음
   (진입 안내를 그렇게 잡았음 · `runs/2026-09-15-task116-2-review-excluded-card/enter.py.txt`).
8. ⚠️ **`p8_inject_pronunciation.py inject` 뒤 `next_review_at` 이 내일임** — 계획 due 목록에 걸려면
   검증 전용 DB 에서 SQL 로 당기고 **그 개입을 회차에 적음**.
9. ⚠️ **`ws_session.py` 는 `--timeout 120`**(기본 30 은 코칭 왕복을 못 담음) ·
   `p_app_path.py` 는 이제 `--wav a.wav,b.wav` 로 왕복 2회를 만듦.
10. ⚠️ **ASR 이 오류 오디오를 정답 문장으로 정규화하는 일이 있음** — 전사문을 먼저 읽고 「코치가 들을
    근거가 있었나」를 가름.

## ④ 열린 태스크 6건 — 전부 «지금 열 자리가 아닌» 이유가 적혀 있음

| 태스크 | 왜 열려 있나 |
|---|---|
| `TASK-61`(In Progress) | **신규 기능**이라 제품 판단 셋이 앞에 있음 — 사용자와 함께 시작 권고 |
| `TASK-78.1` | 우회로 제거. 첫 AC 가 「문턱을 **먼저** 수치로 못박는다」이고 둘째가 실사용 관측임 |
| `TASK-116.5` | 문장 인용 구멍 2/59 — 측정하고 파킹함. 다시 올릴 조건은 그 비율이 커지는 것 |
| `TASK-122`(LOW) | AC#3 이 실물 8회 이상을 요구함. 재시도 1회로 흡수되는 부류 |
| `TASK-39` | AC#2 를 결정 96 이 보류(Phase 2 운영 관찰 시점) |
| `TASK-41` | 결정 31 이 「모든 구현이 끝난 뒤 다시 올린다」로 미룸 |

## ⑤ 착수 전 반드시 읽을 것

- **결정 95·96·97·98** (사용자가 고름) · **결정 99·100** (⚠️ **위임으로 정함** — 다음 세션이 확인받을
  대상). 정본은 `docs/ops/captain-instruction-register.md` 머리 근처임.
- **회차 여섯** — 위 ① 의 목록. 특히 `2026-09-15-task116-3-verdict-condition` 이 결정 98 의 이행과
  codex 리뷰 처리(발견 5건을 갈라 셋은 이전부터·하나는 고침·하나는 태스크로)를 갖고 있음.
- **영구 지식 `H-BQ`** — `backlog task edit --notes` 는 기존 노트를 덮음. 이어 쓸 때 `--append-notes`.
- ⚠️ **개수를 적을 때 그 수가 낡을지 먼저 생각함** — 이 파일의 개수는 위 지표 표의 시점 값임.
