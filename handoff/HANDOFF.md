# HANDOFF — OhMyEnglish

> 최종 갱신 **2026-09-15 00:34 KST** · 세션 `ohmyenglish-65` · 리포 `~/MyProject/OhMyEnglish` ·
> 브랜치 `design/first-vertical-slice`
> ⛔ **이전 판은 `handoff/backup/2026-09-15/HANDOFF-2026-09-15-0034.md` 에 그대로 있음** — 지우지
> 않는 이유는 뒤집힌 결정의 경위가 그 안에만 있을 수 있기 때문임.
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 상태 정본은 원장(`backlog/`), 근거
> 정본은 **태스크 노트 · `tests/harness/runs/**` · `docs/ops/captain-instruction-register.md`** 임 —
> 여기서 수치를 다시 세지 않음.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`2257c33`** · `origin/design/first-vertical-slice` 와 **0/0** · 미커밋은 미추적 `paseo.json` 하나뿐(내 것이 아님) |
| 2 | 다음 한 걸음 | **`TASK-116.3`** AC#1·#2 — 결정 97 이 이 태스크를 「다음 수단」으로 지목했음. ⚠️ AC#3 은 사용자 판단이라 그 앞의 둘만 함 |
| 3 | 게이트 | `app/backend` cwd · 파이프 없이 · **넷 다 exit 0**: `pytest` **1191 passed**(13.05s) · `ruff check .` · `ruff format --check .` **48 files** · `ty check` |
| 4 | 착수 전 필수 | 아래 ③. 잔여 **13건**(To Do 5 · In Progress 8 · Awaiting Decision **0** · 전체 170 · 완료 157) |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD && git rev-list --left-right --count HEAD...origin/design/first-vertical-slice
backlog task list --exclude-status Done --plain
cd app/backend && ./.venv/bin/pytest -q && ./.venv/bin/ruff check . && ~/.local/bin/ty check
```

## ① 이번 세션이 한 것 — 근거는 회차와 결정 대장이 가짐

- **사용자 판단 넷을 닫고 결정 95·96·97 로 등재했음**(`docs/ops/captain-instruction-register.md`).
  handoff 이전 판이 「판단 셋」으로 적은 것 가운데 둘은 **이미 닫혀 있었음** — 낡은 서술을 정정했음.
- **닫은 태스크 넷**: `TASK-116.1`(AC#5 승인) · `TASK-129`(관측 완료) · `TASK-81`(AC#4 충족) ·
  `TASK-81.1`(하네스 확장).
- **새로 등록한 태스크 셋**: `TASK-116.2`(결정 95 이행 · 화면 표시) · `TASK-116.3`(아래 ②) ·
  `TASK-81.1`(닫음).
- **회차 둘**: `tests/harness/runs/2026-09-14-task129-plan-review-key`(WS 레그 · Nova 4세션) ·
  `tests/harness/runs/2026-09-15-task81-app-leg`(브라우저 레그 · Nova 3세션).
- **하네스 확장**: `p_app_path.py` 가 `--wav` 를 쉼표 목록으로 받고 둘째부터 **코치 턴 뒤**에 흘림.

## ② 다음 한 걸음 — `TASK-116.3` 과 그 앞의 판단 하나

**무엇이 관측됐나**: 계획이 고른 발음 키가 기록된 `target_sound` 를 되풀이하는데(일반 세션 3/3 ·
브라우저 1/1), **결정 82 의 어긋남 검사가 한 건도 표시하지 못함** — 코치가 소리를 인용하지 않고
낱말만 말하기 때문임(`sound_check_verdict` 를 실제 발화로 직접 돌려 `None` 확인). 그래서 **한 번도
내지 않은 소리의 복습 일정이 전진하고 화면에 `✓ 좋아요` 가 붙음.**

- **AC#1·#2 는 재현과 조건 특정이라 지금 착수 가능함.** 회차 절차가 그 디렉터리에 그대로 있음.
- ⛔ **AC#3 은 사용자 판단임** — 「인용이 없을 때도 배제할지」는 결정 82 의 전제(잘못된 배제가 더
  비싸다)를 뒤집는 것이라 팀리드가 정하지 않음.

**그 밖에 열린 것의 성격** — 주체를 가려서 잡음.
`TASK-116.2` · `TASK-128.4` AC#1 은 **프론트 구현**임. `TASK-138` 은 AC#1·#2 열거가 먼저이고 AC#3 이
사용자 승인임. `TASK-78` 은 선행(`TASK-81`)이 닫혀 **이제 `--ready` 에 있음**. `TASK-88` 은 AC#4
(p2m 종단 재현)만 남았고 방향은 결정 94 가 정했음. `TASK-39`·`TASK-41`·`TASK-122` 는 대기가 정상임
(`TASK-39` AC#2 는 결정 96 이 보류 · `TASK-41` 은 결정 31 이 마지막으로 미뤘음).

## ③ 착수 전 필수 — 앞 판에서 유효한 것 + 이번 세션 실측

1. ⛔ **게이트 도구는 `python3` 에 없음** — `app/backend/.venv/bin/` 이고 `ty` 만 `~/.local/bin` 임.
   게이트는 **cwd `app/backend`** 에서 돌리고 `pytest` 에 경로를 주지 않음.
   ⚠️ **툴 호출마다 cwd 가 초기화되지 않고 남음** — 상대 경로가 조용히 엉킴(이번 세션에 두 번 겪었음).
   긴 절차에서는 **절대 경로**를 씀.
2. ⛔ **파이프 뒤의 `$?` 는 마지막 명령 것임** — `cmd > /tmp/out 2>&1; echo "exit=$?"` 로 받음.
3. ⛔ **`git add <디렉터리>` 금지** · 커밋 **전** `git diff --cached --name-only` · push **전**
   `git log --oneline origin/<브랜치>..HEAD`.
4. ⛔ **태스크를 열기 전에 결정 대장과 원장을 함께 `grep`** 함 — 이번 세션이 그것으로 「이미 닫힌
   판단 둘」을 다시 묻지 않았음.
5. ⛔ **검증 전용 스택 규약**: DB 소유자 `ohmy` · `WORKER_ENABLED=false` · 끝나면 죽이고 drop 한 뒤
   dev DB 무오염을 조회로 확인. **dev DB 기준선(2026-09-15 실측)**: `learning_sessions=17` ·
   `pronunciation_attempts=7` · `error_patterns=9` · `session_plans=6` · `utterances=128` ·
   `review_tasks=15`.
6. **브라우저 레그 조합이 이번 세션에 통했음** — 전용 Chrome `:9333`(`--use-fake-device-for-media-stream`
   · `--user-data-dir`) + **프론트 사본** `/tmp/fe-t81`(`cp -Rc` 3초 · `.env.local` 로 백엔드 지정) +
   래퍼 백엔드 `:8012`(`/tmp/t81_app.py` 가 `:3001` origin 을 CORS 에 더함 · 앱 코드를 고치지 않음).
   ⛔ **`:9222` 의 Chrome 은 다른 세션 것임 — 그 탭을 빼앗지 않음.**
7. ⚠️ **`p8_inject_pronunciation.py inject` 뒤 `next_review_at` 이 «내일»임** — 계획의 due 목록에
   걸리게 하려면 검증 전용 DB 에서 SQL 로 당겨야 하고 **그 개입을 회차에 적음**(`review.py` 가 그
   컬럼의 유일한 writer 라는 규약을 우회하는 것임). `summarize_*` job 은 `available_at` 을 밀어 둠.
8. ⚠️ **`ws_session.py` 는 `--timeout 120`** 으로 돌림 — 기본 30 은 코칭 왕복을 담지 못함(실측).
   `p_app_path.py` 는 이제 `--wav a.wav,b.wav` 로 왕복 2회를 만들 수 있음.
9. ⚠️ **ASR 이 오류 오디오를 정답 문장으로 정규화하는 일이 있음**(`pq06`·`pq13` 에서 관측). 회차
   판정이 그것에 걸리므로 **전사문을 먼저 읽고** 「코치가 들을 근거가 있었나」를 가름.
10. ⚠️ **`llm_calls` 로 하네스 비용을 셀 수 없음** — `p5_worker_leg.py` 가 `usage_sink` 없이
    클라이언트를 만듦(제품 결함 아님). 호출 수는 손으로 셈.

## ④ 열린 태스크 13건

**To Do 5**: `TASK-116.2`(프론트) · `TASK-116.3`(다음 걸음) · `TASK-39`(AC#2 보류) ·
`TASK-41`(결정 31 로 마지막) · `TASK-122`(LOW).
**In Progress 8**: `TASK-116`(HIGH · 부모) · `TASK-128`(부모) · `TASK-128.4`(AC#1 프론트) ·
`TASK-78`(선행 풀림) · `TASK-88`(AC#4) · `TASK-97` · `TASK-61` · `TASK-138`(AC 넷 미충족).

## ⑤ 착수 전 반드시 읽을 것

- **결정 95·96·97** (`docs/ops/captain-instruction-register.md` 머리 근처) — 이번 세션의 판단 넷.
  ⛔ 특히 **결정 97**: `plan.py:320` 을 고치지 않고 다음 수단은 기록 경로임.
- **회차 정본 둘** — `runs/2026-09-14-task129-plan-review-key`(되풀이 3/3 · 결정 82 미표시) ·
  `runs/2026-09-15-task81-app-leg`(브라우저 코칭 확인 · 같은 어긋남 재확인).
- **결정 82·94** — 82: 다음 수단은 기록 경로 · 94: 발음 기원 오류는 기록만 남기고 복습을 만들지 않음.
- **영구 지식 `H-BQ`** — `backlog task edit --notes` 는 기존 노트를 덮음. 이어 쓸 때 `--append-notes`.
- ⚠️ **개수를 적을 때 그 수가 낡을지 먼저 생각함** — 이 파일의 개수는 위 지표 표의 시점 값임.
