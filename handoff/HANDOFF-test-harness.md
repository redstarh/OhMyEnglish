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
- **P6** — **FAIL.** 학습자가 문법적으로 옳게 말했는데 `error_patterns` 가 오염됐다. ⚠️ 회차 초판이
  「평가 불가」로 적었고 그것이 틀렸다 — 문서의 「문장」은 **픽스처 발화**를 가리키고 전사문이 아니다
  (`scenarios-P` §3 · `run-4` P6 행). 그 정정이 `TASK-84` 판정(**결함임**)을 낳았다

**신설한 실행체 둘** — `tests/harness/p_app_path.py`(앱 경로로 픽스처를 첫 발화로 흘린다) ·
`tests/harness/p5_worker_leg.py`(워커 구간을 job 1건으로 좁힌다. `H-AT` 의 두 경로를 각각 다른
수단으로 막고, `guard` 없이 `claim` 하면 코드가 `exit 2` 로 거부한다).

**사용자 판정 둘을 받아 실행했다** — `TASK-84`(발음 기원 오류의 카테고리 귀속) = **결함임** ·
잔여 처리 = **측정 근거가 있는 것까지 되돌림**. 정본은
`docs/design/2026-09-10-pronunciation-origin-error-attribution.md` 다.

**`TASK-84` 완료** — 사용자 판정으로 **결함 확정**. 구현 소유자는 `TASK-88`(앱 코드라 구현 세션 몫).
**`TASK-83` 완료** — `browser_leg.md` §8-0 이 이제 `next_review_at`·`mastery_score` 를 담고
`harness_review_task_baseline` 을 함께 뜬다. ⚠️ **그 두 표는 마이그레이션이 아니다**(하네스가
`create table as` 로 만든다) — 태스크를 만들 때 「승인 필요」로 적은 전제가 틀렸고 정정했다.
⛔ **컬럼을 늘린 첫 회차는 drift 쿼리가 못 돈다**(`ERROR: column b.next_review_at does not exist` —
직접 확인). 전이 절차를 그 절에 적었다.

**함정 셋을 등록했다** — `H-AX`(job 을 세션으로 되짚는 정본은 `utterance_id` 경유) ·
`H-AW`(남이 소스를 쓰는 중의 정적 검사 유령 실패) ·
`H-AY`(「drift 0」이 「되돌아왔다」를 뜻하지 않는다).

⛔ **이 세션이 틀린 것 넷을 남긴다**(전부 근거와 함께 철회했다 — `TASK-82` 노트가 정본):
⑴ 원장 날짜를 UTC 로 읽지 못해 handoff 를 낡았다고 판정 ⑵ 보존 세션 job 을 한쪽 술어로만 세어
개수를 틀림 ⑶ P6 을 「분석기의 발명」으로 판정 — 조회 **시점**을 확인하지 않았다 ⑷ 「출력 형식
압력」 가설 — 코드가 빈 배열을 명시 허용한다.

---

## ② 다음 한 걸음 — **`TASK-91`**

`backlog task view TASK-91 --plain` 을 먼저 돌린다. **의존 0건 · 착수 가능**하다.

**P계층 `p2` 쌍 이월분 — P2·P3·P7.** 4차수가 `p1` 쌍으로만 닫은 셋이다.
⛔ **P2 는 이번 세션이 이미 재료를 가졌다** — `p2m` 전사문이 `p2a` 와 문자 단위로 **다르다**(§4-1).
즉 4차수가 `p1` 쌍에서 얻은 「전사문이 동일하다 → 앱은 발음 오류를 인지하지 못한다」가 `p2` 쌍에서는
성립하지 않는다. **먼저 그 재료로 충분한지 판단하고 부족할 때만 세션을 새로 만든다.**

⚠️ **N계층은 이월분이 아니다.** 5차수가 `N6`·`N7`·`N8`·`N11`·`N12`·`N13` 을 전부 `PASS` 로 닫았고
(`runs/2026-09-09-run-5.md:16`) `N9`·`N10` 은 태스크 설명이 **일부러 뺀 것**이다.
**handoff 이전 판이 「N계층도 열려 있다」고 적은 것은 낡은 서술이었다** — 이 세션이 확인해 정정했다.

**내 갈래가 아닌 것 둘**: `TASK-88`(발음 기원 오류 구별 — **앱 코드 수정**이라 구현 세션 몫) ·
`TASK-89`·`TASK-90`(Qwen 음소 축 — **다른 세션이 착수했다.** 픽스처 `pq0*.wav` 를 이미 만들었고
`scenarios-P-pronunciation.md` §3.1-4 를 그 세션이 고쳤다). ⛔ **그 파일과 그 태스크를 건드리지 않는다.**

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
| 1 | 기준 커밋 | **`51f5d44` 이상**(등호를 요구하지 않는다 — 다른 세션이 커밋한다) · `origin` 과 동기 |
| 2 | 다음 걸음 | **`TASK-91`** — 「실행: P계층 p2 쌍 이월분 — P2·P3·P7 (4차수가 p1 쌍으로만 닫은 것)」 (`To Do` · AC **0/4**) |
| 3 | 게이트 | `pytest` **900 passed**(12.04s) · `ruff check` exit 0 · format **unformatted 0** · `ty` 통과 · 게이트 밖 `ruff` **0건** · 프론트 `tsc`·`eslint` exit 0 |
| 4 | 착수 전 필수 | **6개**(위 ③). 요지: 복습 시계 불일치 1칸 · 백엔드가 낡은 코드 · 워커 절차 · 다중 세션 · 첫 발화 규약 · 공유 DB. `TASK-91` 의 `dependencies` **0건** · 미충족 AC **4건** |

### ④-2 ⛔ DB 표 건수를 여기에 적지 않는다 — 적는 순간 낡는다

**이 갈래는 그것을 실측했다.** 마감 시점에 8개 표 건수를 「전부 기준선」으로 적었는데, 몇 시간 뒤
`learning_sessions`·`utterances`·`pronunciation_attempts`·`analysis_jobs` 넷이 **기준선보다 높아졌다.**
원인은 회귀도 내 잔여도 아니라 **다른 세션이 앱 경로 세션을 돌리는 중**이었다. 그 수치를 적어 둔
탓에 다음 세션이 그것을 **회귀로 오독할** 자리가 만들어졌다(에이전트가 그 위험을 지적했다).

**그래서 세지 않는 서술로 바꾼다. 다음 세션이 직접 재고 이렇게 가른다:**

1. **내 잔여인지 먼저 가른다** — 회차 기록의 세션 ID 를 명시로 조회한다. 0건이면 내 것이 아니다
2. **시각창으로 남의 것을 본다** — `select left(id::text,8), status, started_at from learning_sessions
   where started_at > '<내 마감 시각>' order by started_at`. ⛔ **잡힌 것을 지우지 않는다**
3. **불변이어야 하는 것만 단정으로 쓴다** — `schema_migrations` · **보존 세션 6개의 결과 API 상태**
   (`210233be` `analyzing` · `6225ddaf` `final` · `b2f0d169` `partial_failure` · `76d9ef31`
   `connection_failed` · `d127dece` `no_utterances` · `e0c5e580` `final`). 응답 전문 기준선은
   `runs/2026-09-10-task82-p5-p6/results-api-baseline.json` 이다
4. **`error_patterns`·`review_tasks` 는 이 갈래가 기준선으로 되돌렸다**(사용자 판정 실행) — 그 값이
   다르면 그때는 **의미가 있다.** 되돌리기 전 증거는 같은 디렉터리의 `*-before-revert.json` 둘이다
