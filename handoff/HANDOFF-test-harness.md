# Handoff — 테스트 하네스 갈래

> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 다. **이 파일은 짧게 쓴다** — 근본 원인·실측
> 수치·판정 근거를 여기 옮기지 않고 **태스크 조회와 회차 기록을 가리킨다**(`backlog task view <ID> --plain`).
>
> **이전 판 백업**: `handoff/archive/HANDOFF-test-harness-2026-09-11-1837.md`(114줄). 그 앞은
> 같은 폴더의 `-0740.md` · `-2026-09-11.md` · `HANDOFF-shared-2026-09-10.md` · `handoff/backup/2026-09-10/`.

최종 갱신 **2026-09-11 18:37 KST** · 브랜치 `design/first-vertical-slice` · 세션 `ohmyenglish-40`

---

## ① 이번 세션이 마무리한 것

**닫은 태스크 다섯**: `TASK-94`(P8) · `TASK-79`(AC#2) · `TASK-101` · `TASK-92` · `TASK-97`(AC#1·#2·#3).
**신설 셋**: `TASK-99` · `TASK-101` · `TASK-103`. **회차 기록 넷이 정본이고 여기서 수치를 다시 세지 않는다**:
`runs/2026-09-11-task94-p8.md` · `-task79-task101.md` · `-task92-pq08-repro.md` · `-task97-tool-payload.md`.

**⛔ 이 갈래가 확정한 것 다섯**:

1. **P계층이 전부 닫혔다.** 저장·조회·렌더는 `pronunciation_intonation` 을 차별하지 않는다.
2. ⛔ **`error_patterns.frequency` 를 두 writer 가 서로 덮는다** — 개수를 가른 조건에서 2 → 1 로
   내려가고 `last_seen_at` 이 과거로 이동한다(**독립 2회 재현**). 도달성은 재지 않았다 → **`TASK-99`**
3. ⛔ **발음 시도의 `target_form` 이 무너진 전사로 굳어 화면의 「시범 문장」 자리에 뜬다** — Nova 가
   두 tool 호출을 다른 뜻으로 쓰고(**6/6**) 앱이 둘째의 옳은 문장을 **버린다** → **`TASK-103`**
4. **폴링 회복이 실측됐다** — 옛 상한(약 6초)의 4배 뒤에 flush 해도 화면이 **새로고침 없이**
   `확정`+교정 카드에 도달한다. **음성 대조가 같은 회차에 있다**(`final` 뒤 폴링이 27에서 멈춘다)
5. **`TASK-92` 는 제품 결함이 아니다** — 앱 경로 4/4 미재현. ⛔ 두 팔이 변수 **둘**에서 갈리므로
   원인을 프롬프트에 귀속하지 않았다

**도구 결함 둘을 고쳤다**(`p5_worker_leg.py`) — `guard` 가 남의 job 을 못 막던 것과 ⛔ **`running`·
임대만료 갈래에 눈이 멀었던 것.** 방향을 뒤집어 **내 job 하나를 전역 최소로 당긴다** → 남의 job
UPDATE **0건**. 판별력 시험 4건 + 성공 경로 1건을 같은 회차에서 쟀다. 동료가 뒤에 `--job-type` 을
더했고(결함 3) 내가 검토해 docstring 에 남겼다.

**사용자 결정 둘을 받아 등록했다** — **54**(결정 50 의 ③ 기준에 「내용의 질」을 넣는다 · 선행 조건이
`TASK-103` 이다) · **55**(코칭률 13% 판정을 보류하고 기록을 먼저 고친다). 정본은
`docs/ops/captain-instruction-register.md` 다.

---

## ② 다음 한 걸음 — **`TASK-74`**(보조 신호에서 복습 시계를 돌릴지 판정)

`backlog task view TASK-74 --plain` 을 먼저 돌린다. **`--ready` 20건 중 이 갈래 소유로 남은 유일한
것**이다(나머지는 앱 코드·문서 트랙). ⛔ **P·N 계층에 이월분이 없다** — 원래 소유 범위는 비었다.

**재료가 이미 있다**: `p2k` 를 첫 발화로 준 회차에서 `korean_transcript` 신호가 행을 만들었는데
`pattern_id`·`target_sound` 가 **둘 다 NULL** 이라 **복습 시계를 걸 재료가 없다**
(`runs/2026-09-10-task82-p4-p1.md`). ⚠️ **사용자 판정으로 닫히는 태스크**다 — 재료를 정리해
`AskUserQuestion` 으로 올린다.

⚠️ **결정 54 를 함께 올린다** — 그 결정이 「도착률만으로 우회로를 걷어내지 않는다」로 정했으므로
`TASK-74` 의 「보조 신호로 시계를 돌리나」와 **같은 축**에 있다.

**열려 있는 내 것 하나**: `TASK-97` AC#4 는 **상시 가드**라 열어 둔다 — 닫히는 조건이
**`TASK-103`**(앱 코드)이고 의존을 걸어 뒀다. ⛔ **결정 50 의 ③을 그 전에 실행하지 않는다.**

**내 갈래가 아닌 것**: `TASK-78`·`TASK-81`(발음 갈래) · `TASK-86`(`Awaiting Decision` — 사용자 답 대기) ·
`TASK-88`·`TASK-99`·`TASK-100`·`TASK-103`·`TASK-104`(앱 코드).

---

## ③ 착수 전 필수

1. ⛔ **워커를 켜기 전에 `p5_worker_leg.py` 의 새 계약을 읽는다** — `--expect-session` 이 **`guard` 에도
   필수**이고 `--out` 도 필수다. ⛔ **처리할 종류가 정해져 있으면 `--job-type` 을 «항상» 준다** —
   빠뜨리면 비보존 세션 넷 전부 `analyze_utterance` 가 더 일러 **항상 분석 job 이 당겨진다**(결함 3).
   ⚠️ **그래도 회차 전 스냅샷은 필요하다** — `H-AY` 는 job 이 아니라 **학습 시계**의 문제다
2. ⚠️ **`browser_leg.md` §8-0 의 두 산출물을 «함께» 낸다** — 회차 디렉터리 JSON(그 회차의 증거)과
   **DB baseline 표**(drift 대조의 기준). 두 표는 여섯 컬럼 스키마로 맞춰 뒀으니 그 절의 drift 쿼리가
   그대로 돈다. ⛔ **`pattern_attempts` 는 그 절차에 아직 없다** — 지난 회차가 간접 확인으로 때웠다
3. ⚠️ **복습 시계 불일치 1칸이 새 기준선으로 굳었다** — `verb_tense_past_simple_for_past_events`
   `next_review_at` `2026-09-12 23:59:37+00`. 경위는 `TASK-83` 노트
4. ⚠️ **다중 세션이다.** 매번 `ListAgents` · `pytest` 전에 알린다(`H-X`) · 커밋은 경로를 열거하고
   **`git diff --cached --name-only` 로 전수 확인한다**(`H-AM`·`H-BA`).
   ⛔ **`backlog browser`(6420)가 살아 있어 사용자가 원장 md 를 직접 고친다** — 매 세션 `git status` 로
   남의 편집을 본다(이 세션에 `task-2` 요구사항 변경과 `task-102` 신설이 그렇게 들어왔다)
5. ⛔ **원장 상태를 남의 태스크에서 돌리기 전에 «지금» 값을 조회한다.** 이 세션에 다른 세션이 18시간
   전 조회값을 현재로 믿고 `TASK-87` 을 되돌려 게이트 **G2** 를 발동시켰다. 감지 수단은
   `git diff <내 마지막 커밋> -- <태스크 파일>` 이고 그 diff 가 비면 안전하다
6. ⚠️ **DB 는 공유 인스턴스다**(`:5432`) — 재시작·`ALTER SYSTEM` 금지. `psql` 은 절대경로
   (`/opt/homebrew/opt/postgresql@17/bin/psql`). ⛔ `.env` 를 열지 않는다
7. ⚠️ **백엔드 구성이 바뀔 수 있다** — 지금 pid **25563** · `VOICE_ADAPTER=nova` ·
   `WORKER_ENABLED=false` 다. 다른 세션이 `stub_unresponsive` 로 재기동할 수 있으므로 회차 기록에
   **그 시점 구성을 적는다**. ✅ 「응답에 `awaiting_analysis` 키가 없다」는 **해소됐다**

**게이트는 `app/backend` cwd 에서만 판정한다**(`H-A`):
`pytest -q` · `ruff check .` · `ruff format --check .` · `/Users/redstar/.local/bin/ty check` ·
게이트 밖 `ruff check ../../tests ../../scripts` · `ruff format --check ../../tests` ·
프론트 `npx tsc --noEmit` · `npx eslint app lib`.
⚠️ format 의 「N files」는 `.md` 를 세므로 **지표로 적지 않는다**(`H-AR`).

---

## ④ 인계 지표 — **직접 돌려** 얻고 대조한다

| # | 지표 | 2026-09-11 18:37 KST 에 직접 돌려 얻은 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`7d706f8` 이상**(등호를 요구하지 않는다 — 다른 세션이 커밋한다) · `origin` 과 **동기** · 내 미커밋 **0건** |
| 2 | 다음 걸음 | **`TASK-74`** — 「보조 신호에서 복습 시계를 돌릴지 정한다」 · **사용자 판정으로 닫힌다** · `--ready` 20건 중 이 갈래 소유 |
| 3 | 게이트 | `pytest` **937 passed**(12.40s) · `ruff check` 안·밖 exit 0 · format **unformatted 0** · `ty` exit 0 · 프론트 `tsc`·`eslint` exit 0 |
| 4 | 착수 전 필수 | **7개**(위 ③). 원장: `In Progress` **3**(`TASK-78`·`81`·`97`) · `Awaiting Decision` **1**(`TASK-86`) · 착수 가능 **20** |

⛔ **DB 표 건수를 이 파일에 적지 않는다 — 적자마자 낡는다.** 가르는 절차는 `browser_leg.md` §8-3 이
갖는다. **불변으로 단정할 수 있는 것은 「보존 세션 6개의 결과 API 상태」뿐**이고 그 응답 전문
기준선은 `runs/2026-09-10-task82-p5-p6/results-api-baseline.json` 이다
(⚠️ 그 파일의 **마지막 원소가 `null`** 이다 — 대조 스크립트가 그것에 걸린다).
⚠️ **`schema_migrations` 를 불변으로 쓰지 않는다** — 추가만 되는 표이고 실제로 늘었다
(`012_daily_error_summary.sql` · 2026-09-10 23:33 UTC). 쓸 수 있는 것은 「내 회차가 새 행을
만들지 않았다」뿐이다.
