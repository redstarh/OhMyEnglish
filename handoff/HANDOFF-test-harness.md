# Handoff — 테스트 하네스 갈래

> 인계 원칙의 정본은 `~/.claude/rules/session-handoff.md` 다. **이 파일은 짧게 쓴다** — 근본 원인·실측
> 수치·판정 근거를 여기 옮기지 않고 **태스크 조회와 회차 기록을 가리킨다**(`backlog task view <ID> --plain`).
>
> **이 갈래의 첫 판이다.** 그 전 내용은 공유 1파일에 있었고 `handoff/archive/HANDOFF-shared-2026-09-10.md`
> 로 보관됐다(그 앞은 `handoff/backup/2026-09-10/`).

최종 갱신 **2026-09-10** · 브랜치 `design/first-vertical-slice` · 세션 `ohmyenglish-40`

---

## ① 이번 세션이 마무리한 것

**`TASK-82` 완료 — P계층 이월분 넷을 앱 경로에서 닫았다.** `TASK-37`(5차수)이 `Done` 인데 이월분의
소유자가 없어 신설한 태스크다. 회차 기록 둘이 정본이다:
`runs/2026-09-10-task82-p4-p1.md` · `runs/2026-09-10-task82-p5-p6.md`.

- **P4** — `p2k` 를 세션의 **첫** 발화로 주니 한글 전사가 앱 경로에서 재현됐고 **`korean_transcript`
  보조 신호가 처음으로 행을 만들었다.** 독립 세션 2회에서 재현됐다
- **P1** — 전사문이 첫 글자 대소문자만 다르고 57자 일치. 발음 언급 0건
- **P5** — 한글 전사문의 분석 job 이 **findings 0건으로 `done`**(기대 거동 ①)
- **P6** — 원 단정은 **평가 불가**(전사문이 원문으로 복원되지 않았다). 관측된 사실이 `TASK-84` 판정을 낳았다

**신설한 실행체 둘** — `tests/harness/p_app_path.py`(앱 경로로 픽스처를 첫 발화로 흘린다) ·
`tests/harness/p5_worker_leg.py`(워커 구간을 job 1건으로 좁힌다. `H-AT` 의 두 경로를 각각 다른
수단으로 막고, `guard` 없이 `claim` 하면 코드가 `exit 2` 로 거부한다).

**사용자 판정 둘을 받아 실행했다** — `TASK-84`(발음 기원 오류의 카테고리 귀속) = **결함임** ·
잔여 처리 = **측정 근거가 있는 것까지 되돌림**. 정본은
`docs/design/2026-09-10-pronunciation-origin-error-attribution.md` 다.

**함정 둘을 등록했다** — `H-AX`(job 을 세션으로 되짚는 정본은 `utterance_id` 경유) ·
`H-AW`(남이 소스를 쓰는 중의 정적 검사 유령 실패).

⛔ **이 세션이 틀린 것 넷을 남긴다**(전부 근거와 함께 철회했다 — `TASK-82` 노트가 정본):
⑴ 원장 날짜를 UTC 로 읽지 못해 handoff 를 낡았다고 판정 ⑵ 보존 세션 job 을 한쪽 술어로만 세어
개수를 틀림 ⑶ P6 을 「분석기의 발명」으로 판정 — 조회 **시점**을 확인하지 않았다 ⑷ 「출력 형식
압력」 가설 — 코드가 빈 배열을 명시 허용한다.

---

## ② 다음 한 걸음 — **`TASK-83` AC#1**

`backlog task view TASK-83 --plain` 을 먼저 돌린다. 지금 `In Progress` 이고 **AC#4 만 충족**이다.

**AC#1 이 다음 걸음이다**: 회차 전에 `error_patterns` 의 `next_review_at`·`mastery_score` 와
`review_tasks` 전체를 파일로 뜨는 절차를 **하네스 문서에 못박는다.** 승인이 필요 없고 가장 값어치가 크다.

AC#2(스냅샷 표 스키마를 고칠지)는 **마이그레이션이라 별도 승인**이 필요하다 — 먼저 하지 않는다.
AC#3 은 함정 등록이다.

**그 다음**: `TASK-88`(발음 기원 오류를 구별한다 — 사용자 판정으로 결함 확정). `TASK-84` 에 의존이
걸려 있고 그것은 `Done` 이므로 **지금 착수 가능하다.** ⚠️ 앱 코드를 고치는 태스크다.

---

## ③ 착수 전 필수

1. ⛔ **복습 시계에 불일치가 하나 남아 있다.** `review_tasks.ede30660`(1단계)은 `pending` 인데
   그 패턴(`verb_tense_past_simple_for_past_events`)의 `next_review_at` 은 `2026-09-12 23:59:37+00` 이다.
   회차 전 값을 아무도 스냅샷하지 않아 **복원 근거가 없다**(계산으로 만들지 않았다). **복습 주기
   시나리오(P9~P12)를 돌리는 회차는 이 한 칸을 전제로 삼는다.** 경위는 `TASK-83` 노트와
   `runs/2026-09-10-task82-p5-p6.md` §9 가 갖는다
2. ⛔ **실행 중 백엔드가 낡은 코드다** — 이 리포는 `--reload` 가 없다. 다른 세션이 결과 API 에
   `awaiting_analysis` 키를 추가해 커밋했으나 **응답에 아직 없다.** 누가 `:8002` 를 재기동하는 순간
   보존 세션 여섯의 응답 키가 하나씩 늘어난다. **응답 키 수를 단정으로 쓰지 말고 `status` 와
   `corrections` 수만 본다.** 기준선 파일은 `runs/2026-09-10-task82-p5-p6/results-api-baseline.json`
3. ⛔ **워커를 켜기 전에 `H-AT` 와 `H-AX` 를 함께 읽는다.** 이제 절차의 실행체가 있다 —
   `p5_worker_leg.py`(`guard` → `claim` → `restore` → `verify`). ⚠️ **`restore` 를 잊지 말고 스냅샷을
   `/tmp` 가 아니라 회차 디렉터리에 둔다** — 이 세션에서 `restore` 가 죽어 보존 job 15건이 밀린 채
   남았고 그 스냅샷이 유일한 복원 근거였다
4. ⚠️ **다른 세션이 같은 리포에서 일한다.** 매번 `ListAgents` 로 확인하고 **`pytest` 전에 알린다**(`H-X`).
   ⛔ **커밋은 경로를 열거해 스테이징한다**(`H-AM`) — 남의 태스크 md·handoff·소스를 건드리지 않는다.
   게이트 수치를 남기기 전에 `git status` 로 남의 미커밋 편집을 본다(`H-AW`)
5. ⚠️ **`P4`·`P12` 는 픽스처를 세션의 «첫» 발화로 준다** — 다른 발화 뒤에 두면 구조적으로 관측 불가다
   (`scenarios-P-pronunciation.md` §3.2)
6. ⚠️ **DB 는 공유 인스턴스다**(`:5432`) — 재시작·`ALTER SYSTEM` 금지. `psql` 은 절대경로
   (`/opt/homebrew/opt/postgresql@17/bin/psql`)

**게이트는 `app/backend` cwd 에서만 판정한다**(`H-A`):
`pytest -q` · `ruff check .` · `ruff format --check .` · `/Users/redstar/.local/bin/ty check` ·
게이트 밖 `ruff check ../../tests ../../scripts` · `ruff format --check ../../tests` ·
프론트 `npx tsc --noEmit` · `npx eslint app lib`.
⚠️ format 의 「N files」는 `.md` 를 세므로 **지표로 적지 않는다**(`H-AR`).

---

## ④ 인계 지표 — **직접 돌려** 얻고 대조한다

| # | 지표 | 2026-09-10 마감 시점에 직접 돌려 얻은 값 |
|--:|---|---|
| 1 | 기준 커밋 | **`7e3b2a3` 이상**(등호를 요구하지 않는다 — 다른 세션이 커밋한다) · `origin` 과 동기 |
| 2 | 다음 걸음 | **`TASK-83`** — 「결함: 분석 워커를 지나가는 하네스 회차는 원상복구가 불가능하다 — 복습 시계에 baseline 이 없다」 (`In Progress` · AC **1/4**) |
| 3 | 게이트 | `pytest` **900 passed**(12.04s) · `ruff check` exit 0 · format **unformatted 0** · `ty` 통과 · 게이트 밖 `ruff` **0건** · 프론트 `tsc`·`eslint` exit 0 |
| 4 | 착수 전 필수 | **6개**(위 ③). 요지: 복습 시계 불일치 1칸 · 백엔드가 낡은 코드 · 워커 절차 · 다중 세션 · 첫 발화 규약 · 공유 DB. `TASK-83` 의 `dependencies` **0건** · 미충족 AC **3건** |

⚠️ **DB 수치는 지표 4개에 없으므로 필요할 때 직접 잰다.** 이 마감 시점 값:
`error_patterns` **9** · `review_tasks` **15** · `error_occurrences` **24** · `learning_sessions` **13** ·
`utterances` **120** · `pronunciation_attempts` **4** · `analysis_jobs` **49** — 전부 기준선.
보존 세션 6개 전건 생존(`210233be` `analyzing` · `6225ddaf` `final` · `b2f0d169` `partial_failure` ·
`76d9ef31` `connection_failed` · `d127dece` `no_utterances` · `e0c5e580` `final`).
