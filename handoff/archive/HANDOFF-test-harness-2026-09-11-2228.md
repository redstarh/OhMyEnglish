# Handoff — 테스트 하네스 갈래

> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 다. **이 파일은 짧게 쓴다** — 근본 원인·실측
> 수치·판정 근거를 여기 옮기지 않고 **태스크 조회와 회차 기록을 가리킨다**(`backlog task view <ID> --plain`).
>
> **이전 판 백업**: `handoff/archive/HANDOFF-test-harness-2026-09-11-2100.md`(122줄 — 상한을 2줄 넘겨
> 백업했다). 그 앞은 같은 폴더의 `-1837.md` · `-0740.md` · `-2026-09-11.md` ·
> `HANDOFF-shared-2026-09-10.md` · `handoff/backup/2026-09-10/`.

최종 갱신 **2026-09-11 21:00 KST** · 브랜치 `design/first-vertical-slice` · 세션 `ohmyenglish-40`

---

## ① 이번 세션이 마무리한 것

**닫은 태스크 둘**: **`TASK-74`**(`08b4d04`) · **`TASK-99` AC#1·#4**(`7c85f3b`).
회차 기록 하나가 정본이고 **여기서 수치를 다시 세지 않는다**: `runs/2026-09-11-task99-reachability/`.

**⛔ 이 세션이 확정한 것 넷**:

1. **보조 신호는 발음 복습 단계를 전진시키지 않는다**(사용자 판정 → 결정 **59**). 이력 쿼리에
   `signal_source = 'nova_tool'` **허용 목록**을 걸어 집행하고 설계서 §3.2·PRD §10.4 에 명문화했다.
2. ⛔ **그 필터가 필요한 이유는 「지금도 도달 불가」였다** — 도달 불가의 근거가 전부 호출자 쪽
   관례였고 쿼리에는 방어가 0이었다. `AssistOutcome` 타입 잠금은 `incorrect` 만 막고 **`correct` 는
   허용한다.**
3. **`TASK-99` 를 잠재 결함으로 내렸다** — 실물 분석 18회에서 `pronunciation_` 접두 키 0건.
   ⛔ **양성 대조로 둔 팔 B 도 0 이라** 판별력은 별도 시험 4/4 로만 확보했다(`--self-check`).
4. ⛔ **태스크 설명의 「앱 쪽 검증은 없고」를 정정했다** — `resolve_pattern_keys` 가 upsert 앞에서
   `^{category}_` 를 강제하고, 그것이 문법 카테고리 갈래를 **다른 실패로 바꾼다**(그 발화의 분석
   전체 실패).

**정정한 낡은 서술**: `services/pronunciation.py` 세 곳이 「`_EXISTING_PATTERNS_SQL` 에 카테고리
필터가 없다」를 근거로 삼았는데 **G-8 이 그 필터를 넣은 뒤라 낡았다.** 줄 번호 참조도 이름으로 바꿨다.

---

## ② 다음 한 걸음 — **`TASK-99` AC#2 의 사용자 판정**(`Awaiting Decision`)

`backlog task view TASK-99 --plain` 을 먼저 돌린다. ⛔ **AC#2 가 판정으로 성질이 바뀌었다** —
등급이 잠재로 내려가서 「어느 층을 고치나」 앞에 **「고칠지 자체」**가 왔다.

**갈리는 축 한 문장**: `ErrorFinding.category` 가 발음 카테고리를 **값역에 갖고 금지가 프롬프트
문구뿐**인 것을 코드로 닫을지, 닫으면 그 발화의 교정 전체를 실패시킬지 그 finding 만 버릴지.
⚠️ **이 모듈에 「버리는」 선례가 있다** — `attempts` 의 미매치 키를 예외로 올리지 않고 버리며, 그
근거 주석이 「저가치 필드 하나가 그 발화의 교정 전체를 태우면 안 된다」다.

⛔ **이 회차를 「G-8 필터를 지워도 된다」의 근거로 인용하면 안 된다** — 팔 B 가 발화하지 않았으므로
필터의 **필요성은 입증되지 않았다.** 필터의 값은 「모델이 한 번이라도 재사용하면 데이터가 손상된다」는
비대칭에 있다.

**열려 있는 내 것 하나**: `TASK-97` AC#4 는 **상시 가드**라 열어 둔다 — 닫히는 조건이
**`TASK-103`**(앱 코드)이고 의존을 걸어 뒀다. ⛔ **결정 50 의 ③을 그 전에 실행하지 않는다.**

**내 갈래가 아닌 것**: `TASK-78`·`TASK-81`·`TASK-86`(발음 갈래 · 셋 다 `In Progress`) ·
`TASK-88`·`TASK-100`·`TASK-103`·`TASK-104`·`TASK-108`·`TASK-109`(앱 코드).

---

## ③ 착수 전 필수

1. ⛔ **워커를 켜기 전에 `p5_worker_leg.py` 의 새 계약을 읽는다** — `--expect-session` 이 **`guard` 에도
   필수**이고 `--out` 도 필수다. ⛔ **처리할 종류가 정해져 있으면 `--job-type` 을 «항상» 준다** —
   빠뜨리면 비보존 세션 넷 전부 `analyze_utterance` 가 더 일러 **항상 분석 job 이 당겨진다**.
   ⚠️ **그래도 회차 전 스냅샷은 필요하다** — `H-AY` 는 job 이 아니라 **학습 시계**의 문제다
2. ⚠️ **`browser_leg.md` §8-0 의 두 산출물을 «함께» 낸다** — 회차 디렉터리 JSON(그 회차의 증거)과
   **DB baseline 표**(drift 대조의 기준). ⛔ **`pattern_attempts` 는 그 절차에 아직 없다**
3. ⚠️ **복습 시계 불일치 1칸이 새 기준선으로 굳었다** — `verb_tense_past_simple_for_past_events`
   `next_review_at` `2026-09-12 23:59:37+00`. 경위는 `TASK-83` 노트
4. ⚠️ **다중 세션이다.** 매번 `ListAgents` · `pytest`·Bedrock 회차 전에 알린다(`H-X`) · 커밋은 경로를
   열거하고 **`git diff --cached --name-only` 로 전수 확인한다**(`H-AM`·`H-BA`).
   ⛔ **`backlog browser`(6420)가 살아 있어 사용자가 원장 md 를 직접 고친다** — 매 세션 `git status` 로
   남의 편집을 본다(이 세션에 대장 파일과 `task-26`·`task-86` 이 그렇게 들어왔다)
5. ⛔ **원장 상태를 남의 태스크에서 돌리기 전에 «지금» 값을 조회한다.** 감지 수단은
   `git diff <내 마지막 커밋> -- <태스크 파일>` 이고 그 diff 가 비면 안전하다
6. ⚠️ **DB 는 공유 인스턴스다**(`:5432`) — 재시작·`ALTER SYSTEM` 금지. `psql` 은 하네스의
   `psql_cli.py` 로 부른다(`DATABASE_URL` 을 따라간다). ⛔ `.env` 를 열지 않는다
7. ⚠️ **백엔드 구성이 바뀔 수 있다** — 이 세션 실측은 pid **25563** · `:8002` · `VOICE_ADAPTER=nova` ·
   `WORKER_ENABLED=false` 다. 회차 기록에 **그 시점 구성을 적는다.** 프로세스 env 에서 그 두 키만
   걸러 보면 `.env` 를 열지 않고 확인된다

**게이트는 `app/backend` cwd 에서만 판정한다**(`H-A`):
`pytest -q` · `ruff check .` · `ruff format --check .` · `/Users/redstar/.local/bin/ty check` ·
게이트 밖 `ruff check ../../tests ../../scripts` · `ruff format --check ../../tests` ·
프론트 `npx tsc --noEmit` · `npx eslint app lib`.
⚠️ format 의 「N files」는 `.md` 를 세므로 **지표로 적지 않는다**(`H-AR`).
⚠️ **`pytest`·`ruff` 는 PATH 에 없다** — `app/backend/.venv/bin/` 에서 부른다.
⚠️ **`ty` 는 `tests/harness/runs/**` 까지 본다** — 회차 스크립트의 `Settings()` 에
`# ty: ignore[missing-argument]` 를 붙이는 것이 확립된 관용이다.

---

## ④ 인계 지표 — **직접 돌려** 얻고 대조한다

| # | 지표 | 2026-09-11 21:00 KST 에 직접 돌려 얻은 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`7f25b25` 이상**(등호를 요구하지 않는다 — 다른 세션이 커밋한다) · 아무도 `origin` 에 push 하지 않았다 · 내 미커밋 **0건** |
| 2 | 다음 걸음 | **`TASK-99` AC#2** — `Awaiting Decision` 이고 **사용자 판정으로 열린다** |
| 3 | 게이트 | `pytest` **940 passed**(12.13s) · `ruff check` 안·밖 exit 0 · **unformatted 0** · `ty` **All checks passed** · 프론트 `tsc`·`eslint` exit 0 |
| 4 | 착수 전 필수 | **7개**(위 ③). 원장: 파일 **112** · `Done` **88** · `In Progress` **4** · `Awaiting Decision` **1** · `To Do` **19**(그중 `--ready` **18**) |

⚠️ **지표 4 를 상태별로 센다** — `--ready` **출력 행 수**로 세면 `In Progress`·`Awaiting Decision`
행이 섞여 커진다(이전 판의 「착수 가능 20」이 그 값이었다).
세는 명령: `grep -h '^status:' backlog/tasks/*.md | sort | uniq -c`.
⚠️ **원장이 이 세션 중에 110 → 112 로 늘었다** — 동료가 `TASK-108`·`TASK-109` 를 등록했다.

⛔ **DB 표 건수를 이 파일에 적지 않는다 — 적자마자 낡는다.** 가르는 절차는 `browser_leg.md` §8-3 이
갖는다. **불변으로 단정할 수 있는 것은 「보존 세션 6개의 결과 API 상태」뿐**이고 그 기준선은
`runs/2026-09-10-task82-p5-p6/results-api-baseline.json` 이다(⚠️ **마지막 원소가 `null`** 이라
대조 스크립트가 그것에 걸린다). ⚠️ **`schema_migrations` 를 불변으로 쓰지 않는다** — 추가만 되는
표이고 실제로 늘었다. 쓸 수 있는 것은 「내 회차가 새 행을 만들지 않았다」뿐이다.
