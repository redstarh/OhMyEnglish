---
id: TASK-41
title: '검토: 우리 표를 public → 전용 스키마로 이관 (En-Coach 비대칭 해소)'
status: Done
assignee: []
created_date: '2026-09-07 17:51'
updated_date: '2026-09-17 00:40'
labels: []
dependencies: []
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
TASKS.md E절에서 이관. En-Coach는 전용 스키마(en_coach)를 쓰는데 우리 표는 public에 있어 비대칭이다 — 남의 search_path 폴백이 우리 표로 떨어질 수 있다. 우리 SQL이 전부 한정자 없이 쓰여 있어 범위가 커서 미뤄 왔다. 근거: docs/ops/shared-database-naming-rules.md §5.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 전용 스키마 이관의 영향 범위(한정자 없는 SQL 전수)를 조사한다
- [x] #2 이관 여부와 시점을 캡틴 결정으로 확정한다
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
## AC#2 답 (2026-09-17 · 결정 122)

사용자가 「모든 구현이 끝났다고 봐」로 정했음 — 결정 31 이 「모든 구현이 끝난 뒤」로 미뤄 둔 자리가
이것으로 열렸음. 착수하지 않았으므로 상태를 To Do 로 되돌림.

⚠️ 착수 전에 확인할 것 셋(팀리드 메모): ⑴ 이 DB 인스턴스는 StockAgent 와 공유하므로 인스턴스 단위
조작을 하지 않음 ⑵ search_path 를 바꾸면 하네스 드라이버와 scripts/ 가 함께 영향을 받음 —
그 목록을 먼저 뽑음 ⑶ 마이그레이션 번호는 실측 최대(025) 다음이고 002·008 은 영구 결번임.

## AC#1 조사 (2026-09-17 · 전수 실측)

**⑴ 우리 표는 21개** (`pg_tables where schemaname=public` 직접 조회): `analysis_jobs` ·
`daily_error_summary` · `error_occurrences` · `error_patterns` · `harness_pattern_baseline` ·
`harness_review_task_baseline` · `harness_runs` · `harness_sessions` · `learner_notes` ·
`learning_scenarios` · `learning_sessions` · `llm_calls` · `pattern_attempts` ·
`pronunciation_attempts` · `review_tasks` · `schema_migrations` · `session_plans` ·
`shadowing_items` · `users` · `utterances` · `weekly_reports`.

**⑵ 한정자 없는 표 참조 882건 · 파일 87개 · `public.` 로 한정한 것 0건.**

| 트리 | 참조 |
|---|--:|
| `tests` | 619 |
| `app/backend/app` | 172 |
| `db/migrations` | 72 |
| `scripts` | 19 |

⛔ **그런데 이 882가 이관 비용이 아님** — 전부 한정자가 없으므로 **고칠 곳은 882자리가 아니라
`search_path` 한 곳**임. 이 태스크의 설명이 *"우리 SQL 이 전부 한정자 없이 쓰여 있어 범위가 커서"*
라고 적어 둔 전제가 **거꾸로임**: 한정자가 없는 것이 오히려 이관을 싸게 만듦. 한정자가 섞여 있었다면
882자리를 손으로 갈라야 했음.

**⑶ 진짜 비용은 En-Coach 임** (실측 `information_schema.table_privileges`):

| 표 | 권한 |
|---|---|
| `public.error_patterns` → `en_coach` | SELECT |
| `public.error_occurrences` → `en_coach` | SELECT |
| `public.pronunciation_attempts` → `en_coach` | SELECT |

⛔ **표를 옮기면 그 셋의 grant 가 함께 옮겨 가고, En-Coach 쿼리가 `public.error_patterns` 를 이름으로
가리키면 깨짐** — `docs/ops/shared-database-naming-rules.md` 가 그들에게 그 형태를 알려 준 문서임.
즉 이관은 **남의 앱을 깨는 변경**이고 우리 리포 안에서 끝나지 않음. `en_coach` 스키마에는 표 14개가
살아 있음(실측).

**⑷ 착수 전 확인 셋의 결과**:
- 인스턴스 공유: 확인함 — 이관은 DB 단위 DDL 이라 인스턴스 조작이 아님. StockAgent 는 다른 DB 라 무영향.
- `search_path` 영향 목록: DSN 계산이 `scripts/db_utils.base_dsn` 하나로 모여 있어 앱·스크립트·하네스·
  테스트가 **같은 자리**를 지남. 즉 `?options=-csearch_path%3D<스키마>,public` 한 곳이면 넷이 함께 감.
  ⚠️ 단 `psql_cli.py` 도 그 DSN 을 psql 에 그대로 넘기므로 함께 따라옴(확인함).
- 마이그레이션 번호: 실측 최대가 **025** 이므로 다음은 **026**. 002·008 은 영구 결번임.

**설계 후보 둘 (대가가 갈림)**:
1. **깔끔한 이관** — 표 21개를 새 스키마로 옮기고 `en_coach` 에 `usage` + 그 셋의 `select` 를 다시 줌.
   En-Coach 가 자기 쿼리에서 `public.` 을 떼거나 새 스키마 이름으로 바꿔야 함(그쪽 작업이 필요함).
2. **호환 뷰를 public 에 남김** — En-Coach 는 한 줄도 안 고침. ⛔ 대가: 우리 `search_path` 가 틀어지면
   우리 코드가 그 뷰를 읽어 **읽기 전용 이상 동작이 조용히** 생김. 비대칭을 없애려는 목적과도 어긋남.

⇒ AC#2 의 「시점」이 남았고 그것은 **다른 팀과의 조율**이라 사용자 결정이 필요함.

## 이관 실행 (2026-09-17 · 마이그레이션 026)

**사용자 제약**: *"en-coach 는 현재 고치면 안됨, 관련해서 수정이 생기면 ohmyenglish 가 수정해야함"*.
⇒ 조율이 필요한 안(그쪽이 쿼리를 고치는 안)은 성립하지 않고 **호환 뷰**가 유일한 길이었음.

**026 이 하는 것 셋**: `ohmyenglish` 스키마 생성 · `public` 의 **`ohmy` 소유 표 전부** 이동 ·
En-Coach 가 읽는 표 셋에 대한 `public` 동명 뷰 + grant · 역할 `ohmy` 의 `search_path` 고정.

⛔ **표를 이름으로 열거하지 않고 소유자로 골랐음** — `shared-database-naming-rules.md` R5 가
*"이름만 보고 옮기면 남의 표를 가져갈 수 있다"* 라고 적었고 그 규칙이 우리에게도 적용됨.
개수를 조건에 넣지 않았음(세면 낡음).

⛔ **`search_path` 를 DSN 이 아니라 역할에 걸었음.** 이유: `DATABASE_URL` 환경변수가 DSN 을 덮으므로
(`db_utils.base_dsn`) DSN 에 걸면 `.env` 를 쓰는 앱에는 반영되지 않음. 역할에 걸면 앱·스크립트·하네스·
`psql` 이 전부 같은 값을 받음. 선례가 있음(같은 역할에 `TimeZone=UTC`).
⚠️ **`public` 을 search_path 에서 빼지 않았음** — `pgcrypto` 가 `public` 에 설치돼 있어(실측) 빼면
`gen_random_uuid()` 를 쓰는 DDL 이 깨짐.

**직접 돌린 검증**:
- 백업 선행: `pg_dump -n public` **139,444바이트 · CREATE TABLE 21 · COPY 21**
  (`.harness/backups/ohmyenglish-public-20260917T003650Z.sql`).
  ⚠️ `ohmy` 로는 뜨지 못했음 — `permission denied for table harness_pattern_baseline` (그 표가
  `redstar` 소유임). superuser 로 떴고 그 사실을 `TASK-153` 으로 등록했음.
- 테스트 DB: `search_path` = `ohmyenglish, public` · 표 16개가 새 스키마 · `public` 에 뷰 셋만 ·
  `current_schema()` = `ohmyenglish`.
- dev DB: 표 **19개**가 새 스키마(`ohmy` 소유) · `public` 에는 `redstar` 소유 하네스 기준선 둘만 남음 ·
  불변 지표 보존(`learning_sessions` **17** · `session_plans` **6** · `schema_migrations` 23→**24**).
- ⛔ **En-Coach 경로를 `set role en_coach` 로 직접 확인했음**: `public.error_patterns` **9행** ·
  `error_occurrences` **24행** · `pronunciation_attempts` **7행** 이 읽혔고,
  `ohmyenglish.error_patterns` 직접 접근은 **`permission denied for schema ohmyenglish`** 로 막혔음.
  그 막힘이 정답임 — 그것이 이관이 노린 대칭임.
- 앱 경로: 백엔드를 띄워 DB 를 타는 엔드포인트 넷(`/api/daily-summary` · `/api/history` ·
  `/api/sessions/next-plan` · `/api/weekly-report`)이 **전부 200 · 실데이터**, 로그 오류 **0건**.
- 게이트: `pytest` **1283 passed** · `ruff` 0 · `ruff format` 0 · `ty` 0.

**⚠️ 새 함정 `H-BX` — 동명 호환 뷰가 introspection 을 뒤집음.** 스키마를 걸지 않은
`information_schema.columns` 조회가 두 스키마의 행을 함께 돌려주고, **뷰는 모든 컬럼을
`is_nullable=YES`** 로 보고해 단정이 `assert YES == NO` 로 깨졌음(실제로 깨졌음). 테스트 네 자리에
`table_schema = current_schema()` 를 걸었음(스키마 이름을 박지 않음). ⚠️ 순서가 반대였으면 **깨지지
않고 통과**했을 것이라 더 위험한 방향임.

**함께 고친 규약 셋**: `pg_dump` 범위 `-n public` → `-n ohmyenglish`(`local-run.md` ·
`browser_leg.md` §7) · `shared-database-naming-rules.md` §5(숙제 완료 · En-Coach 가 할 일 없음) ·
`shared-database-guide.md` §3-(2)(위험 해소).

**갈라낸 것**: `TASK-153` — `public` 에 남은 `redstar` 소유 하네스 기준선 표 둘.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
created: 2026-09-07 22:56
---
캡틴 결정 31(2026-09-08): 「En-Coach DB 사용중이니, 모든 작업이 마무리되고 나중에 이관할지 결정해」 — 010·011 을 public 에 그대로 추가한다. ⚠️ 받아들이는 비용: 표를 더할수록 이관 범위가 커지고 우리 SQL 이 전부 한정자 없이 쓰여 있어 그 비용은 선형이 아니다. 모든 구현이 끝난 뒤 다시 올린다.
---
<!-- COMMENTS:END -->
