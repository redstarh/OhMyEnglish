# HANDOFF — OhMyEnglish (통합 · 갈래 파일 하나로 합침)

> 최종 갱신 **2026-09-14 23:03 KST** · 리포 `~/MyProject/OhMyEnglish` · 브랜치 `design/first-vertical-slice`
> ⛔ **이 파일 하나가 정본이다.** 갈래별 파일 넷(`HANDOFF-integration-test.md` ·
> `HANDOFF-plan-prompt.md` · `HANDOFF-pronunciation.md` · `HANDOFF-test-harness.md`)을 사용자
> 지시(2026-09-14)로 여기에 합치고 지웠음. **직전 내용은 `handoff/archive/HANDOFF-<갈래>-2026-09-14-2300.md`
> 에 그대로 있음** — 뒤집힌 결정의 경위가 그 안에만 있을 수 있어 삭제가 아니라 보관임.
> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. 상태 정본은 원장(`backlog/`), 근거 정본은
> **태스크 노트 · `runs/` · `docs/design/**` · 결정 대장**임 — 여기서 수치를 다시 세지 않음.
>
> ⛔ **네 갈래의 주인 세션이 모두 없음**(2026-09-14 확인 — tmux 창에 OhMyEnglish 가 0개이고 에이전트
> 목록에도 `ohmyenglish-*` 가 없음). 이 판은 `realtime-meeting-b2` 가 사용자 지시로 썼고
> ⚠️ **판정을 새로 하지 않았음** — 지금 상태를 측정해 적은 것뿐임.

## 인계 지표 4개 (이 턴에 직접 돌린 출력)

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`6ee584c`** · `origin/design/first-vertical-slice` 와 **0/0** · 미커밋은 미추적 `paseo.json` 하나뿐 |
| 2 | 다음 한 걸음 | ⛔ **사용자 판단 셋이 앞에 있음**(아래 ②). 판단 없이 착수 가능한 것은 **`TASK-61`**(음성 명령 · 착수 전 조사가 원장에 있음) · **`TASK-116.1` AC #5** · **`TASK-138`** 임 |
| 3 | 게이트 | `app/backend` cwd · 파이프 없이 · **넷 다 exit 0**: `pytest` **1191 passed**(13.36s) · `ruff check .` · `ruff format --check .` **48 files** · `ty check` |
| 4 | 착수 전 필수 | 아래 ③ 의 여섯. 잔여 태스크 **14건**(To Do 4 · In Progress 10 · 전체 167 · 완료 153) |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD
backlog task list --exclude-status Done --plain
cd app/backend && ./.venv/bin/pytest -q && ./.venv/bin/ruff check . && ~/.local/bin/ty check
```

## ① 네 갈래가 지금 어디에 있나

| 갈래 | 주인 세션 | 지금 상태 |
|---|---|---|
| 통합 테스트 | `ohmyenglish-d9` (종료) | 2026-09-14 21:55 마감. 다음 걸음으로 `TASK-128.4` AC#1(브라우저 레그 관측)을 지목했음 |
| 계획 프롬프트·시나리오·총평 | `ohmyenglish-f4` (종료) | 2026-09-14 10:03 마감. **사용자 판단 셋**을 앞에 세워 두고 끝냈음 |
| 발음 | `ohmyenglish-d9` (종료) | 이전 판이 하루 낡은 사이 커밋 79건이 쌓였음. 다음 걸음 `TASK-116.1` AC #5 |
| 테스트 하네스 | `ohmyenglish-40` (종료) | 이전 판이 이틀 낡은 사이 커밋 164건. 다음 걸음 `TASK-138`(AC 넷 전부 미충족) |

⛔ **이전 판들의 「이 세션이 한 것」은 그 시점 기록으로만 읽음** — 그 뒤에 쌓인 커밋을 이 판이 다시
판정하지 않았음. 상태는 원장이 정본임.

## ② ⛔ 사용자 판단 셋 — 이것이 풀려야 그 축이 움직임

1. **`TASK-88` AC#2**(`Awaiting Decision`) — 발음 기원 오류를 어떻게 가르나. ⛔ 실측이 naive 한 안을
   배제했음(`nova_tool` 시도가 발화에 **4행 중 0행** 이어져 있음). 후보 둘 — ① 모델 출력에 기원 필드를
   더함 ② 발음 tool 을 최근 발화에 이음(시각 근접 규칙을 제품이 발명하게 됨).
2. **`TASK-26.7`**(`Awaiting Decision`) — dev DB 에 **023** 적용. ⚠️ 마이그레이션 최대는 `023` 이고
   **dev DB 는 `022`** 이며 `weekly_reports` 표가 없음.
3. **비용 승인이 필요한 관측 둘** — `TASK-129`(일반 세션의 되풀이를 재려면 실물 Nova) ·
   `TASK-39` AC#2(스로틀 관찰). ⚠️ `TASK-137` 의 `utterances` 갈래 미관측도 같은 부류임.

⚠️ `TASK-41` 은 결정 31 이 「`To Do` 로 두고 모든 구현이 끝난 뒤 다시 올린다」로 정했으므로 `--ready`
에 보이는 것이 정상임 — 지금 착수 대상이 아님.

## ③ 착수 전 필수 여섯

1. ⛔ **게이트 도구는 `python3` 에 없음** — `app/backend/.venv/bin/` 이고 `ty` 만 `~/.local/bin` 임.
   게이트는 **cwd `app/backend`** 에서 돌리고 `pytest` 에 경로를 주지 않음.
2. ⛔ **파이프 뒤의 `$?` 는 마지막 명령 것임** — 종료 코드는 따로 받음.
   ⚠️ **zsh 는 변수를 단어로 쪼개지 않음**: `for c in "check ."; do ruff $c; done` 이 exit 2 로 죽음(실측).
3. ⛔ **`git add <디렉터리>` 금지** · 커밋 **전** `git diff --cached --name-only` · push **전**
   `git log --oneline origin/<브랜치>..HEAD` · 공유 파일은 고친 턴에 커밋.
4. ⛔ **태스크를 열기 전에 결정 대장과 원장을 함께 `grep`** 함 — 내린 결정을 다시 묻는 것이 가장 비쌈.
5. ⛔ **검증 전용 스택 규약**: DB 소유자 `ohmy` · `WORKER_ENABLED=false` · 끝나면 죽이고 drop 한 뒤
   dev DB 무오염을 조회로 확인. 브라우저 레그에 마이크가 필요하면 **전용 Chrome**.
   ⚠️ `pg_dump -n public` 에 **`-T 'harness_*'`** 를 붙임.
6. ⚠️ `db_pool` 픽스처는 아무것도 정리하지 않음(사용자를 먼저 지워 cascade 시킴) ·
   `record_attempt` 로는 **두 pending 을 만들 수 없음**(`_legacy_pending` 헬퍼) ·
   무력화 되돌림이 `.pyc` 때문에 안 돌 수 있어 `__pycache__` 를 지움.

## ④ 열린 태스크 14건 — 원장에서 그대로 옮김

**발음 축 9건**: `TASK-116`(HIGH · 미충족 1) · `TASK-116.1`(1 · **AC #5 만 남음 — 화면 표시 승인**) ·
`TASK-128` · `TASK-128.4`(1) · `TASK-88`(1) · `TASK-97` · `TASK-81` · `TASK-78` · `TASK-129`.
**테스트 하네스 축 1건**: `TASK-138`(미충족 **4** — 열거 · 겹침 열거 · ⛔ **삭제는 사용자 승인** ·
지운 뒤 게이트 개수 대조. 기준선은 `pytest` **1191 passed**).
**그 밖 4건**: `TASK-61`(음성 명령 · 착수 가능) · `TASK-39` · `TASK-41` · `TASK-122`(LOW).

## ⑤ 착수 전 반드시 읽을 것 — 이전 판들이 남긴 판단

- **설계 정본** `docs/design/2026-09-13-decision82-record-path-verification.md` — 결정 82 이행 설계.
  ⛔ **판단을 이미 끝냈으므로 다시 정하지 않고 읽고 착수함.**
- **회차 정본** `runs/2026-09-12-task128-sound-as-candidate.md` — Nova 7세션 · 죽은 회차 0.
  ⛔ 판별 팔 3/3 으로 **세 방향(더하기·덜기·재료)이 모두 반증됐음.** 한 세션은 코치가 없는 `/f/` 를
  발명했음(`early` 에 `/f/` 가 없음).
- **결정 82·83** — 82: 다음 수단은 **기록 경로**이고 프롬프트를 더 고치지 않음 · 83: 진입 문구는
  「후보가 아직 없음」을 참으로 말함.
- **영구 지식 `H-BQ`** — `backlog task edit --notes` 가 기존 노트를 **덮음**. 이어 쓸 때 `--append-notes`.
- ⚠️ **테스트에 개수를 적을 때 그 수가 낡을지 먼저 생각함** — 시드가 3에서 30으로 늘며 개수 서술이
  두 번 낡았음(`TASK-138` 이 그것을 고치는 중임).
