# Handoff — 발음 축 (주인 세션 없음 · 최종판)

> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 임. **짧게 씀** — 판정 근거를 옮기지 않고
> **태스크 조회와 설계서·회차 기록을 가리킴**(`backlog task view <ID> --plain`).
>
> **이전 판**: `handoff/archive/HANDOFF-pronunciation-2026-09-14-2253.md`(그 앞은 `…-2026-09-13-0019`
> · `…-2336` · `…-2232`). ⛔ **이전 판을 지우지 않았음** — 뒤집힌 결정의 경위가 그 안에만 있을 수 있음.
>
> ⛔ **이 판은 이 축의 주인 세션이 아니라 `realtime-meeting-b2` 가 썼음** (사용자 지시 2026-09-14).
> 이유는 **주인 세션 `ohmyenglish-d9` 가 종료됐고 그 뒤 이 파일이 하루 넘게 낡았기 때문임** —
> tmux 창 일곱 개 가운데 OhMyEnglish 창이 0개이고 에이전트 목록에도 그 세션이 없음(직접 확인).
> ⚠️ **판정을 새로 하지 않았음.** 이 판이 하는 것은 «지금 상태를 측정해 적는 것» 뿐임.

최종 갱신 **2026-09-14 22:53 KST** · 브랜치 `design/first-vertical-slice`

---

## ① 인계 지표 4개 — 이 턴에 직접 돌린 출력

| # | 지표 | 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`19568ab`** · `origin/design/first-vertical-slice` 와 **0/0** · 미커밋은 미추적 `paseo.json` 하나뿐 |
| 2 | 다음 한 걸음 | **`TASK-116.1` AC #5** — 「검증에 걸린 기록의 화면 표시는 사용자 승인을 받는다」. ⛔ **복습 큐에서 빼는 것은 결정 82 가 이미 정했으므로 묻지 않음.** AC 넷은 이미 충족됨 |
| 3 | 게이트 | `app/backend` cwd · 파이프 없이 · **넷 다 exit 0**: `pytest` **1191 passed**(13.36s) · `ruff check .` · `ruff format --check .` **48 files** · `ty check` |
| 4 | 착수 전 필수 | 이 축에 **열린 태스크 9건**(아래 ③). ⛔ **게이트 도구는 `python3` 에 없음** — `app/backend/.venv/bin/` 이고 `ty` 만 `~/.local/bin` 임 |

```bash
cd ~/MyProject/OhMyEnglish
git rev-parse --short HEAD
backlog task list --exclude-status Done --plain
cd app/backend && ./.venv/bin/pytest -q && ./.venv/bin/ruff check . && ~/.local/bin/ty check
```

⚠️ **zsh 는 변수를 단어로 쪼개지 않음** — `for c in "check ."; do ruff $c; done` 이 exit 2 로 죽음(이
턴에 실측). 게이트는 명령을 그대로 나눠 쓴다.

## ② ⛔ 이 파일이 낡았던 사이에 일이 계속 갔음

이전 판의 최종 갱신은 **2026-09-13 00:19** 이고 그 뒤 **커밋 79건**이 쌓였음. 그 가운데 발음 축을
만진 것이 다수임(`TASK-88` 계열 — 발음 기원 오류 라우팅 · 결정 92·93·94 등재 · 결정 94 로 복습 과제
생성 철회). 즉 **이전 판 ①의 「이 세션이 한 것」은 그 시점 기록으로만 읽어야 하고 현재 상태가 아님.**

⛔ 이 판은 그 79건을 다시 판정하지 않음 — 상태 정본은 원장이고 근거 정본은 태스크 노트·`runs/`·
`docs/design/` 임. **여기서 수치를 다시 세지 않음.**

## ③ 이 축에 열린 태스크 9건 — 원장에서 그대로 옮김

| 태스크 | 미충족 AC | 무엇 |
|---|--:|---|
| `TASK-116` (HIGH) | 1 | 결함(확정): 코칭한 소리와 tool 의 `target_sound` 가 어긋나 복습 일정이 오염됨 |
| `TASK-116.1` | 1 | 구현: 어긋난 `target_sound` 가 복습 단계를 전진시키지 못하게 함 (결정 82) |
| `TASK-128` | — | 이 축은 지시문 밖으로 나감: 더하기·덜기 두 방향이 모두 반증됨 |
| `TASK-128.4` | 1 | 구현 C4: 폴백이 사라지면 화면의 진입 안내가 거짓이 됨 |
| `TASK-88` | 1 | 구현: 발음 기원 오류를 문법·표현 패턴과 구별함 |
| `TASK-97` | — | 결함 후보: 발음 tool 의 내용이 쓸 수 없음(`target_form`·`target_sound`) |
| `TASK-81` | — | 구현: 계획 블록이 발음에 자리를 내주게 함 |
| `TASK-78` | — | 결함/재개: 결정 49 의 사실 전제 둘이 반증됨 |
| `TASK-129` | — | 관측: 계획 블록의 복습 목록이 발음 키를 이름으로 내는 둘째 경로 |

⚠️ `TASK-122`(LOW · 이름 없는 빈 키가 `level` 에 남음)도 같은 축이지만 `To Do` 임.
⛔ **미충족 AC 수를 적지 않은 칸은 이 턴에 세지 않았다는 뜻임** — 필요하면 직접 센다
(`backlog task view <ID> --plain | grep -c '^- \[ \]'`).

## ④ 착수 전 반드시 읽을 것 — 이전 판이 남긴 판단

- **설계 정본** `docs/design/2026-09-13-decision82-record-path-verification.md` — 결정 82 이행 설계.
  ⛔ **판단을 이미 끝냈으므로 다시 정하지 않고 읽고 착수함.**
- **회차 정본** `runs/2026-09-12-task128-sound-as-candidate.md` — Nova 7세션 · 죽은 회차 0.
  ⛔ 판별 팔 3/3 으로 **세 방향(더하기·덜기·재료)이 모두 반증됐음.** 한 세션은 코치가 없는 `/f/` 를
  발명했음(`early` 에 `/f/` 가 없음).
- **결정 82·83** 이 결정 대장에 있음 — 82: 다음 수단은 **기록 경로**이고 프롬프트를 더 고치지 않음 ·
  83: 진입 문구는 「후보가 아직 없음」을 참으로 말함.
- **영구 지식 `H-BQ`** — `backlog task edit --notes` 가 기존 노트를 **덮음**. 이어 쓸 때 `--append-notes`.

## ⑤ 다른 갈래를 건드리지 않았음

이 리포의 갈래 파일 넷 가운데 **이 파일만** 고쳤음. `HANDOFF-integration-test.md`(오늘 21:55 ·
`ohmyenglish-d9` 마감) · `HANDOFF-plan-prompt.md`(오늘 10:03 마감)는 최신이라 손대지 않았고,
`HANDOFF-test-harness.md` 는 같은 지시로 **따로** 최종판을 만들었음.
