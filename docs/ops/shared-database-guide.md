# 같은 PostgreSQL을 다른 앱과 함께 쓰기 — 설정과 스키마 분리 가이드

> **대상**: OhMyEnglish의 dev PostgreSQL 인스턴스에 다른 앱을 붙이려는 경우.
> **작성 2026-08-30.** 아래 값은 이 문서를 쓴 턴에 코드·스크립트에서 직접 확인한 것이다
> (`scripts/dev_db.sh`, `scripts/db_utils.py`, `app/backend/app/config.py`,
> `db/migrations/001_initial_schema.sql`, `tests/conftest.py`).
>
> ⛔ **2026-09-17 재실측 (`TASK-152`)**: §2.1·§2.3 은 그날 **살아 있는 서버에 직접 붙어** 다시 얻은
> 값이고 **§2.3 은 결론이 뒤집혔다**(비밀번호가 필수가 아니다). 나머지 절의 수치는 2026-08-30 것이라
> 낡을 수 있다 — 그 자리마다 어느 날짜의 값인지 적어 두었다.

---

## 1. 먼저 알아야 할 것 — 요청한 변수 중 2개는 존재하지 않는다

| 요청한 변수 | 이 리포에 있나 | 실제 |
|---|:--:|---|
| `DATABASE_URL` | ✅ **있다** | 앱의 **필수** 설정. `app/backend/app/config.py:47` |
| `AUTH_TOKEN` | ❌ **없다** | 리포 전체 검색 결과 0건. **인증 계층 자체가 없다** — 첫 슬라이스는 localhost 전용·인증 없음이 승인된 범위다 |
| `AUTH_USER_ID` | ❌ **없다** | 환경변수가 아니라 **코드에 박힌 상수**다: `app/models/user.py` 의 `FIXED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")` (2026-09-17에 `api/ws.py` 에서 옮겼다 — `TASK-148`) |

**그래서 토큰으로 사용자를 구분하는 방식은 지금 이 앱에 없다.** 세션은 위 고정 UUID
하나로만 생성된다(`api/ws.py` 의 `session_socket`). 다른 앱이 사용자 개념을 공유하려면 그 UUID를 알고 있어야
하고, 사용자를 늘리려면 인증 도입이 **선행 결정**이다(범위 밖).

---

## 2. 연결 정보

### 2.1 dev DB (homebrew `postgresql@17`) — 2026-09-17 재실측

📌 **경로가 두 번 바뀌었다.** 2026-08-31에 podman 컨테이너(`ohmy-pg` · `:5433`)에서 homebrew
`postgresql@17`(`:5432`)로 옮겼고(함정 **H-T** — podman 가상머신이 내려가면 게이트가
`192 passed · 155 errors`로 무너졌다), 2026-09-17에 그 폴백을 도구에서 **지웠다**(`TASK-149`).
컨테이너 데이터가 이관 시점의 사본이라 되살리면 앱이 보지 않는 DB를 고치고 「통과」로 보고하게 된다.

| 항목 | 값 (2026-09-17 직접 조회) |
|---|---|
| 서버 | homebrew `postgresql@17` — `server_version` **17.9 (Homebrew)** · launchd가 부팅 시 띄운다 |
| 포트 | **5432** |
| 사용자 / 비밀번호 | `ohmy` / `ohmy` |
| 데이터베이스 | `ohmyenglish` (소유자 `ohmy`) |
| `psql` | **PATH에 없다** — keg-only다. `/opt/homebrew/opt/postgresql@17/bin/psql` |

```bash
scripts/dev_db.sh status    # 서버·버전·마이그레이션 건수 (내려가 있으면 dev_db.sh start)
```

⛔ **`stop`·`reset`은 그 스크립트에 없다** — 이 서버를 StockAgent(`stockagent`·`stocknews`)와
En-Coach(`en_coach` 스키마 · `en_coach_harness_test`)가 함께 쓴다. 인스턴스를 세우면 남의 앱이 함께
멈추고, dev DB를 재생성하면 `en_coach` 스키마까지 사라진다(§4.5).

SQL을 던질 때는 위 절대경로를 쓰거나 `tests/harness/psql_cli.py`를 쓴다 — 그 헬퍼는
`DATABASE_URL`을 따라가므로 **앱이 보는 DB**에 붙는다(`scripts/db_utils.base_dsn`).

### 2.2 `DATABASE_URL`

```bash
# 기본값 (환경변수를 주지 않으면 이것이 쓰인다 — scripts/db_utils.py:DEFAULT_DEV_DSN)
DATABASE_URL=postgresql://ohmy:ohmy@localhost:5432/ohmyenglish
# ⛔ 폴백은 없다 — :5433 컨테이너 경로는 2026-09-17에 지웠다 (`TASK-149`)
```

- 앱은 `app/backend/.env`(gitignore 대상)에서 읽는다. 셸 export가 `.env`보다 우선한다.
- 스크립트(`scripts/migrate.py`, `scripts/smoke_analysis.py`)와 테스트는 같은 값을
  `db_utils.base_dsn()`으로 공유한다 — DSN 계산이 갈라지지 않게 한 곳이 소유한다.
- ⚠️ 이 자격증명은 **로컬 개발 전용**이다(비밀번호가 `ohmy`). 공유 환경·원격에 그대로
  쓰지 않는다.

### 2.3 인증 — **비밀번호를 보지 않는다** (2026-09-17 재실측 · ⛔ 이전 판과 결론이 반대다)

⛔ **이 절은 뒤집혔다.** 이전 판은 podman 컨테이너를 재고 *"호스트 → `localhost:5433`은 비밀번호가
**필수**"*라고 적었다(2026-08-30 실측 · 컨테이너 포트 포워딩이 `scram-sha-256` 줄에 걸렸기 때문).
homebrew 서버는 그렇지 않다 — 아래는 그 서버에 직접 붙어 얻은 값이다.

| 어떻게 붙었나 | 결과 (직접 실행) |
|---|---|
| `PGPASSWORD=COMPLETELY_WRONG` + `-h 127.0.0.1 -p 5432 -U ohmy` | ✅ **접속됐다** — 틀린 비밀번호를 아예 보지 않는다 |
| `postgresql://ohmy@localhost:5432/ohmyenglish` (비밀번호 없음) | ✅ **접속됐다** |

즉 **호스트 TCP 접속이 `trust`로 열려 있다.** `pg_hba.conf` 원문은 확인하지 못했다 —
`pg_hba_file_rules` 뷰가 `permission denied`다(`ohmy`가 superuser가 아니다, 아래).
⚠️ 그래서 **「trust다」는 관측된 동작이고 설정 파일로 대조한 것은 아니다.**

**사용자(role)는 여전히 필요하다.** 로그인 가능한 역할은 `ohmy` · `en_coach` · `redstar` ·
`stockagent` 넷이다(직접 조회).

⛔ **`ohmy`는 superuser가 아니다** — `rolsuper=f` · `rolcreaterole=f` · `rolcreatedb=t`(직접 조회).
superuser이면서 `CREATEROLE`인 역할은 **`redstar`와 `stockagent`** 다. §4.3의 SQL이 이 사실에
걸린다(그 절이 정정을 갖는다).

> ⚠️ **보안 함의**: 이 머신에서 `:5432`에 닿을 수 있으면 **비밀번호 없이 세 앱의 DB 전체에
> 접근된다** — OhMyEnglish · StockAgent(`stockagent`·`stocknews`) · En-Coach가 같은 인스턴스다.
> 로컬 개발 전용 구성이므로 수용하지만, 원격·공유 환경으로 옮길 때는 `pg_hba.conf`의 `local`·
> `127.0.0.1` 줄을 `scram-sha-256`으로 바꾸고 비밀번호를 `ohmy`가 아닌 값으로 돌린다.

### 2.4 참고: 다른 앱이 백엔드 API를 부를 경우

| 항목 | 값 |
|---|---|
| OhMyEnglish 백엔드 | `http://localhost:**8002**` |
| ⚠️ `:8000` | **다른 프로젝트(StockAgent)**가 쓴다. 2026-08-26 실측: `:8000`의 openapi title = `"StockAgent (MOCK)"` |
| 프론트가 읽는 변수 | `NEXT_PUBLIC_API_BASE=http://localhost:8002` (`app/frontend/.env.example`) |

백엔드에는 `--reload`가 없다 — 파이썬 소스를 고치면 반드시 재기동한다.

---

## 3. ⚠️ 붙이기 전에 반드시 읽을 위험 3개

### (1) 이름이 비슷한 DB 2개가 **통째로 drop/create된다**

이 서버의 실제 DB 목록 (실측):

```
ohmyenglish         ← dev. migrate.py가 drop 없이 누적 적용한다 (안전)
ohmyenglish_test    ← ⚠️ 테스트마다 drop/create
ohmyenglish_smoke   ← ⚠️ 스모크 실행 시 drop/create
postgres
```

`tests/conftest.py:46`이 `TEST_DB_NAME = "ohmyenglish_test"`이고 세션 픽스처가
`db_utils.recreate_database()`를 부른다 — **파괴적 연산이다**(drop database → create →
마이그레이션 재적용). `scripts/smoke_analysis.py`도 같은 유틸을 `ohmyenglish_smoke`에 쓴다.

> **다른 앱은 `_test`·`_smoke`를 절대 쓰지 마라.** 우리 테스트가 한 번 돌면 그 안의 모든
> 데이터가 사라진다. 접미사 한 조각 차이라 오타로도 물릴 수 있다.

### (2) ~~우리 테이블은 전부 `public` 스키마에 있다~~ → **2026-09-17에 옮겼다**

⛔ **이 위험은 해소됐다** (`TASK-41` · 마이그레이션 026): 우리 표는 스키마 **`ohmyenglish`** 에 있고
`public`에는 En-Coach 호환 뷰 셋만 남았다(§5-1). 그래서 새로 붙는 앱이 `public`에 표를 만들어도
우리와 이름이 충돌하지 않는다. 아래 서술은 **왜 그것이 위험이었는지**의 기록으로 남긴다.

`db/migrations/**`에 `create schema`도 `search_path` 설정도 없다(검색 결과 0건). 즉
기본 스키마를 쓴다. ⚠️ **이 절의 실측값은 2026-08-30 것이고 그 뒤 바뀌었다** — 지금 스키마는
`public` 과 `en_coach` 둘이고 로그인 가능한 역할은 넷이다(§2.3). 즉 §4 가 이미 적용됐다는 뜻이고,
아래 위험 서술은 **새로 붙는 앱에 대해** 여전히 유효하다. 다른 앱이 그대로 `public`에 테이블을 만들면 **이름 충돌 위험**이
생기고, 무엇이 누구 것인지 구분이 사라진다. → §4가 그 해결이다.

`public`에 있는 우리 객체(001·003):

```
users · learning_scenarios · learning_sessions · utterances
error_patterns · error_occurrences · review_tasks · analysis_jobs
pronunciation_attempts · schema_migrations
+ extension pgcrypto
```

### (3) `schema_migrations`는 **파일명 기준**이라 공유하면 안 된다

`scripts/migrate.py:62`가 만드는 표는 `filename text primary key` 하나로 적용 여부를
판단한다. 다른 앱이 같은 표를 재사용하면 `001_...sql` 같은 흔한 파일명이 충돌해
**한쪽의 마이그레이션이 "이미 적용됨"으로 조용히 건너뛰어진다.**

> 다른 앱은 **자기 스키마 안에 자기 추적 표**를 둔다.

---

## 4. ✅ 채택된 구성 — **같은 DB + 스키마 분리** (2026-08-30 구축·검증 완료)

캡틴 결정: 별도 DB + FDW로 한 번 만들었다가 **철회하고 이 방식으로 옮겼다**(§4-alt에 그때
얻은 것을 남겼다). 이유는 조인이다 — 같은 DB 안이면 `postgres_fdw` 없이 **네이티브 조인**이
되고 외부 테이블 재동기화 문제도 없다.

### 4.1 만들어진 것 (현재 상태)

| 대상 | 값 |
|---|---|
| 데이터베이스 | **`ohmyenglish`** (우리와 공유) |
| 다른 App의 역할 | **`otherapp`** — 기본 `search_path = otherapp` |
| 다른 App의 스키마 | **`otherapp`** (owner `otherapp`) — 그 안에서는 자유롭게 만든다 |
| 우리 표 접근 | `public` USAGE + **SELECT만** — `error_patterns` · `error_occurrences` · `pronunciation_attempts` |
| `public`에 만들기 | **불가** (PG16 기본값이 PUBLIC에 USAGE만 준다 — 실측 확인) |

```bash
DATABASE_URL=postgresql://otherapp:<비밀번호>@localhost:5432/ohmyenglish
# 역할 기본 search_path가 otherapp이라 옵션 없이도 자기 스키마를 먼저 본다.
# 커넥션마다 못 박고 싶으면 (권장 — 명시적):
DATABASE_URL=postgresql://otherapp:<비밀번호>@localhost:5432/ohmyenglish?options=-csearch_path%3Dotherapp
```

`?options=-csearch_path%3Dotherapp`의 `%3D`는 `=`의 URL 인코딩이다. libpq 기반
드라이버(psycopg, asyncpg)가 이 형식을 지원한다. 비밀번호는 이 문서에 적지 않는다.

### 4.2 검증된 동작 (호스트에서 직접 돌린 결과)

| # | 확인 | 결과 |
|--:|---|---|
| ① | 호스트에서 `otherapp` 접속 | ✅ ⚠️ **「비밀번호 필요」는 그때 컨테이너(`:5433`)의 동작이다** — homebrew 서버는 `trust` 로 열려 있다(§2.3 재실측) |
| ② | `show search_path` | ✅ `otherapp` |
| ③ | 자기 테이블 생성 | ✅ **`otherapp` 스키마**에 만들어진다(`public` 아님) |
| ④ | `select count(*) from public.error_patterns` | ✅ 우리 실제 행이 보인다 |
| ⑤ | **자기 테이블 × 우리 표 네이티브 조인** | ✅ FDW 없이 그냥 된다 |
| ⑥ | 우리 표에 `update` | ✅ **차단** `permission denied for table error_patterns` |
| ⑦ | `create table public.x` | ✅ **차단** `permission denied for schema public` |
| ⑧ | 권한 안 준 우리 표 읽기(`users`) | ✅ **차단** `permission denied for table users` — 최소 권한이 실제로 걸려 있다 |
| ⑨ | 우리 표 `drop` | ✅ **차단** `must be owner of table` |

우리 앱 게이트도 함께 확인했다: **327 passed** · ruff · ty clean (영향 없음).

### 4.2-1 En-Coach가 실제로 붙었다 (실측, `TASKS.md` H-3에서 이관)

이 문서 §4가 준비한 구성에 En-Coach가 실제로 접속한 뒤의 확인값이다 — `en_coach`
스키마에 `ec_*` 접두 표 **9개** + 자기 `schema_migrations`가 생겼고, 우리 `public`
스키마에는 `ec_` 접두 표가 **0개**다(비대칭 없음 확인). §4.4의 "공유 표를 늘리거나
줄이려면"과 함께 읽는다.

### 4.3 만든 SQL (재현용)

```sql
-- ⛔ **`ohmy`로는 전부 돌아가지 않는다.** 실측한 것은 권한 속성이다(2026-09-17 직접 조회):
--    `ohmy` 는 rolsuper=f · rolcreaterole=f · rolcreatedb=t 이고 superuser 는 `redstar`·`stockagent`
--    다(§2.3). 거기서 갈라지는 것 — `create role` 과 `alter role … set` 은 CREATEROLE 을 요구하므로
--    **`redstar` 로** 돌리고, `grant`·`create schema` 는 DB·표 소유자인 `ohmy` 로 된다.
--    ⚠️ 이 갈라짐은 권한 모델에서 유도한 것이고 이 서버에서 한 문장씩 돌려 본 것은 아니다 —
--    공유 서버에 시험용 역할을 만들지 않기 위해서다.
-- psql 은 PATH 에 없다(keg-only) — 절대경로를 쓴다:
--   PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h 127.0.0.1 -p 5432 \
--     -U redstar -d ohmyenglish
create role otherapp login password '<강한 비밀번호>';
grant connect on database ohmyenglish to otherapp;
create schema otherapp authorization otherapp;
alter role otherapp set search_path = otherapp;

-- 우리 표는 읽기만
grant usage on schema public to otherapp;
grant select on table error_patterns, error_occurrences, pronunciation_attempts to otherapp;
```

`public`에 대한 `revoke create`는 **넣지 않았다** — PG15부터 `public` 스키마가 PUBLIC에게
CREATE를 주지 않는 것이 기본값이고, 이 서버에서 실측으로 확인했다(`nspacl`이 `=U/`,
그리고 위 ⑦이 실제로 차단됐다). 구버전(PG14 이하)에 옮길 때는 반드시 넣어라:
`revoke create on schema public from public;`

### 4.4 공유 표를 늘리거나 줄이려면

```sql
grant select on table public.<표이름> to otherapp;      -- 늘릴 때
revoke select on table public.<표이름> from otherapp;    -- 줄일 때
```

앞으로 만들어질 표까지 자동으로 열지 마라 — `alter default privileges`는 쓰지 않는다.
새 표가 조용히 노출된다.

> **쓰기 권한은 주지 않는다.** 우리 앱의 불변조건이 앱 코드와 CHECK 제약에 나뉘어 있어
> (예: `pronunciation_attempts`는 `pending` ⇔ `resolved_at is null`, 시도 순서는
> `attempt_seq` identity가 강제) 외부에서 직접 INSERT하면 그 규약이 깨진다. 데이터를
> 넣어야 한다면 표가 아니라 **백엔드 API를 통한다**.

### 4.5 ⚠️ dev DB를 재생성하면 다른 App 데이터도 함께 사라진다

이제 두 앱이 **같은 데이터베이스**를 쓴다. `docs/ops/local-run.md`가 적어 둔
"001을 재작성했다면 dev DB를 drop/재생성해야 한다"를 실행하면 **`otherapp` 스키마와 그
안의 데이터까지 없어진다.**

- 우리 테스트는 안전하다 — 파괴적 재생성 대상은 `ohmyenglish_test`·`ohmyenglish_smoke`뿐이고
  dev DB(`ohmyenglish`)는 `migrate.py`가 drop 없이 누적 적용한다(§3-(1)).
- 위험은 **사람이 손으로 dev DB를 재생성할 때**다. 그때는 다른 App 담당에게 먼저 알린다.
- 다른 App은 **자기 마이그레이션 스크립트를 갖는 것이 좋다** — 스키마를 언제든 다시 세울 수
  있으면 이 위험이 "재실행 한 번"으로 줄어든다. 추적 표는 자기 스키마 안에 둔다(§3-(3)).

### 4.6 확장(extension)은 DB 단위로 공유된다

`pgcrypto`는 이미 설치돼 있다(001). 다른 App이 `gen_random_uuid()`를 쓰려면 스키마 한정자
없이 그대로 부를 수 있다 — `create extension`을 다시 실행하지 않는다.

### 4.7 이름을 바꾸려면

```sql
alter schema otherapp rename to <새이름>;
alter role otherapp rename to <새이름>;   -- ⚠️ 역할명을 바꾸면 비밀번호를 다시 설정해야 한다
alter role <새이름> set search_path = <새이름>;
```

---

## 4-alt. 철회한 구성 — 별도 DB + `postgres_fdw` (2026-08-30에 만들었다가 되돌림)

**지금 이 구성은 남아 있지 않다** — DB `otherapp`, 역할 `ohmy_share_ro`, FDW 서버·매핑·외부
테이블을 전부 제거했다(실측 확인: foreign server 0, `postgres_fdw` 확장 0). 다시 필요해질
때를 위해 **그때 실제로 걸린 것**만 남긴다.

⚠️ **PostgreSQL은 DB가 다르면 일반 쿼리로 조인할 수 없다.** 별도 DB를 고르면 공유는
`postgres_fdw`(외부 테이블)로 이어야 하고, 아래 셋이 반드시 걸린다.

1. **`trust`가 FDW를 막는다.** `import foreign schema`가
   `password or GSSAPI delegated credentials required`로 실패한다 — postgres_fdw는 비superuser가
   쓸 때 **원격이 비밀번호를 실제로 요구할 것**을 강제하는데(trust 악용 방지) 컨테이너 내부
   접속은 `trust`라 묻지 않는다(§2.3). 우회는 superuser가 매핑을 읽기 전용 역할로 고정한 뒤
   `alter user mapping … options (add password_required 'false')`. 원격 환경이라면 이 대신
   `pg_hba.conf`의 `127.0.0.1/32`를 `scram-sha-256`으로 바꾸는 쪽이 맞다.
2. **`import foreign schema`는 실행한 사용자의 user mapping으로 원격에 붙는다.** `ohmy`
   (superuser)로 돌리면 `user mapping not found for "ohmy"`가 난다 — 매핑을 가진 역할
   (`otherapp`)로 실행해야 한다.
3. **외부 테이블은 스냅샷이 아니라 매번 원격을 읽는다.** 우리가 컬럼을 바꾸면 정의가 낡으므로
   다시 `import`해야 하고, 큰 표를 반복 조인하면 네이티브보다 확실히 불리하다.

세 번째가 이 구성을 철회한 이유다.

---

## 5. 네 방식 비교

| 방식 | 조인 | 격리 | 대가 | 상태 |
|---|---|---|---|---|
| **스키마 분리 (DB 공유)** | **네이티브 — 그냥 된다** | 중간 — 같은 DB라 권한 실수 여지. dev DB 재생성이 양쪽을 날린다(§4.5) | 우리 표 접근을 `grant select`로 하나씩 열어야 한다 | ✅ **채택·구축 완료** (§4) |
| 별도 DB + `postgres_fdw` | 외부 테이블 경유 | **강함** — 권한·마이그레이션·이름공간 완전 분리 | 스키마 변경 시 재`import`, 대량 조인 느림, `trust`가 FDW를 막는 함정 | ↩️ 만들었다가 철회 (§4-alt) |
| 별도 컨테이너 (포트 5434 등) | 불가 (FDW로도 네트워크 경유) | 가장 강함 | 리소스 두 배, 포트 관리 | 미사용 |
| `public` 공유 | 네이티브 | **없음** | 이름 충돌 · `schema_migrations` 충돌 · 소유 구분 소실 | ❌ 권장하지 않음 |

**격리가 더 필요해지면**(예: 다른 App이 프로덕션급이 되거나 담당이 갈리면) §4-alt로 되돌리는
길이 열려 있다 — 그때 걸릴 것 3개를 §4-alt가 이미 적어 두었다.

---

## 6. 붙인 뒤 확인 (직접 돌려서 값을 보라)

```bash
# ① 우리 앱이 여전히 정상인가 — 게이트는 app/backend cwd에서만 판정한다
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . \
  && .venv/bin/ruff format --check . && ty check
#   2026-08-30 구축 후 실측: 327 passed (영향 없음)

# ② 스키마와 역할이 실제로 있나
# psql 은 keg-only 라 절대경로다. ⛔ 변수(`PSQL='psql -h …'`)로 묶지 마라 — zsh 는 변수를 단어로
#    쪼개지 않아 `command not found` 가 난다(2026-09-17 에 직접 밟았다). 함수로 묶는다.
pg() { PGPASSWORD=ohmy /opt/homebrew/opt/postgresql@17/bin/psql -h 127.0.0.1 -p 5432 \
         -d ohmyenglish "$@"; }
pg -U ohmy -c "\dn"
pg -U otherapp -c "show search_path"   # → otherapp

# ③ 다른 App이 public에 테이블을 못 만드는가 — **ERROR가 정답이다**
pg -U otherapp -c "create table public.should_fail(x int)"
#   기대: permission denied for schema public

# ④ 권한 안 준 표는 못 읽는가 — 이것도 ERROR가 정답이다
pg -U otherapp -c "select count(*) from public.users"
#   기대: permission denied for table users
```

⚠️ `PGPASSWORD` 를 넣어 두지만 이 서버는 그 값을 보지 않는다(§2.3) — 다른 머신·원격으로 옮겨도
같은 블록이 돌게 남겨 둔 것이다.

③·④가 **성공하면** 최소 권한이 안 걸린 것이다. `grant`를 과하게 준 적이 없는지 확인한다:
`pg -U ohmy -c "\dp public.*"`

---

## 7. 관련 문서

| 문서 | 무엇 |
|---|---|
| **`docs/ops/shared-database-naming-rules.md`** | **En-Coach 전달용 네이밍·접근 규칙** (R1~R6 + 접속 정보 + 부여된 권한) |
| `docs/database-schema.md` | 표·컬럼의 의미와 **왜 그 값인지**. 컬럼을 읽기 전에 본다 |
| `docs/ops/local-run.md` | 로컬 실행 방법 (DB·백엔드·프론트·게이트) |
| `db/migrations/*.sql` | 스키마 정본. 주석에 결정 근거가 있다 |
| `scripts/db_utils.py` | DSN 계산과 파괴적 재생성의 경계 |
