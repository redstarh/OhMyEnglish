# 같은 PostgreSQL을 다른 앱과 함께 쓰기 — 설정과 스키마 분리 가이드

> **대상**: OhMyEnglish의 dev PostgreSQL 인스턴스에 다른 앱을 붙이려는 경우.
> **작성 2026-08-30.** 아래 값은 이 문서를 쓴 턴에 코드·스크립트에서 직접 확인한 것이다
> (`scripts/dev_db.sh`, `scripts/db_utils.py`, `app/backend/app/config.py`,
> `db/migrations/001_initial_schema.sql`, `tests/conftest.py`).

---

## 1. 먼저 알아야 할 것 — 요청한 변수 중 2개는 존재하지 않는다

| 요청한 변수 | 이 리포에 있나 | 실제 |
|---|:--:|---|
| `DATABASE_URL` | ✅ **있다** | 앱의 **필수** 설정. `app/backend/app/config.py:47` |
| `AUTH_TOKEN` | ❌ **없다** | 리포 전체 검색 결과 0건. **인증 계층 자체가 없다** — 첫 슬라이스는 localhost 전용·인증 없음이 승인된 범위다 |
| `AUTH_USER_ID` | ❌ **없다** | 환경변수가 아니라 **코드에 박힌 상수**다: `app/backend/app/api/ws.py:44` `FIXED_USER_ID = UUID("00000000-0000-0000-0000-000000000001")` |

**그래서 토큰으로 사용자를 구분하는 방식은 지금 이 앱에 없다.** 세션은 위 고정 UUID
하나로만 생성된다(`ws.py:107`). 다른 앱이 사용자 개념을 공유하려면 그 UUID를 알고 있어야
하고, 사용자를 늘리려면 인증 도입이 **선행 결정**이다(범위 밖).

---

## 2. 연결 정보

### 2.1 dev DB (podman 컨테이너)

> 이 머신에 **`psql` 클라이언트가 없다**(실측: `command -v psql` → 없음). `docker`는
> **podman 별칭**이다. 그래서 아래 SQL은 전부 `podman exec`로 컨테이너 안에서 돌린다.

📌 **2026-08-31: dev DB의 기본 경로가 바뀌었다 — homebrew `postgresql@17`(:5432)다.**
아래 컨테이너(:5433)는 **폴백으로만 남아 있고 데이터는 이관 시점의 사본**이다.
현재 접속정보는 `docs/ops/local-run.md`와 `shared-database-naming-rules.md` §2가 소유한다.
옮긴 이유: podman 가상머신이 내려가 있으면 게이트가 `192 passed · 155 errors`로 무너졌다(함정 **H-T**).

`scripts/dev_db.sh`가 만드는 컨테이너의 실제 값:

| 항목 | 값 |
|---|---|
| 컨테이너 / 볼륨 | `ohmy-pg` / `ohmy-pg-data` |
| 이미지 | `postgres:16-alpine` |
| 호스트 포트 | **5433** (5432가 아니다) |
| 사용자 / 비밀번호 | `ohmy` / `ohmy` |
| 데이터베이스 | `ohmyenglish` |

```bash
scripts/dev_db.sh start     # 없으면 create, 있으면 start
scripts/dev_db.sh stop
```

### 2.2 `DATABASE_URL`

```bash
# 기본값 (환경변수를 주지 않으면 이것이 쓰인다 — scripts/db_utils.py:DEFAULT_DEV_DSN)
DATABASE_URL=postgresql://ohmy:ohmy@localhost:5432/ohmyenglish
# 폴백(podman 컨테이너)을 쓸 때만 5433으로 바꾼다
# DATABASE_URL=postgresql://ohmy:ohmy@localhost:5433/ohmyenglish
```

- 앱은 `app/backend/.env`(gitignore 대상)에서 읽는다. 셸 export가 `.env`보다 우선한다.
- 스크립트(`scripts/migrate.py`, `scripts/smoke_analysis.py`)와 테스트는 같은 값을
  `db_utils.base_dsn()`으로 공유한다 — DSN 계산이 갈라지지 않게 한 곳이 소유한다.
- ⚠️ 이 자격증명은 **로컬 개발 전용**이다(비밀번호가 `ohmy`). 공유 환경·원격에 그대로
  쓰지 않는다.

### 2.3 인증 — **어디서 붙느냐로 갈린다** (2026-08-30 실측)

컨테이너의 `pg_hba.conf`가 이렇게 돼 있다(postgres 공식 이미지 기본값):

```
local   all  all                     trust            ← 컨테이너 내부 유닉스 소켓
host    all  all  127.0.0.1/32       trust            ← 컨테이너 내부 TCP
host    all  all  ::1/128            trust
host    all  all  all                scram-sha-256    ← 그 밖의 전부 = 비밀번호 필요
```

| 어디서 | 비밀번호 | 실측 결과 |
|---|:--:|---|
| **컨테이너 내부** (`podman exec … psql -U ohmy`) | **불필요** | `PGPASSWORD=COMPLETELY_WRONG`을 줘도 접속됐다 — `trust`는 비밀번호를 아예 보지 않는다 |
| **호스트 → `localhost:5433`** | **필수** | 비밀번호 없이·틀린 값으로 4가지 조합 전부 `InvalidPasswordError` |

**왜 `127.0.0.1/32 trust`가 호스트에는 안 걸리는가**: podman이 포트를 포워딩하면 서버가 보는
접속 주소가 `127.0.0.1`이 아니라 **컨테이너 네트워크 게이트웨이**다(실측: `inet_client_addr()`
→ `10.88.0.2`). 그래서 마지막 줄 `scram-sha-256`이 적용된다.

**사용자(role)는 언제나 필요하다.** 생략하면 클라이언트가 OS 사용자명으로 시도하고
(`redstar`), 그런 역할이 없어 실패한다. 즉 "user·password 없이 접근"은 불가능하고,
정확히는 **"컨테이너 내부에서는 user만 있으면 password가 불필요"**하다.

> ⚠️ **보안 함의**: `podman exec` 권한이 있으면 **비밀번호 없이 DB 전체에 접근된다.**
> 이 가이드의 §4.1 SQL이 비밀번호 없이 돌아가는 이유가 그것이다. 로컬 개발 전용 구성이므로
> 수용하지만, 원격·공유 환경으로 옮길 때는 `local`·`127.0.0.1` 줄을 `scram-sha-256`으로
> 바꾸고(`POSTGRES_HOST_AUTH_METHOD=scram-sha-256`) 비밀번호를 `ohmy`가 아닌 값으로 돌린다.

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

### (2) 우리 테이블은 전부 **`public` 스키마**에 있다

`db/migrations/**`에 `create schema`도 `search_path` 설정도 없다(검색 결과 0건). 즉
기본 스키마를 쓴다. 실측으로도 스키마는 `public` 하나뿐이고 로그인 가능한 역할은 `ohmy`
하나뿐이다(`\dn` · `pg_roles`). 다른 앱이 그대로 `public`에 테이블을 만들면 **이름 충돌 위험**이
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
DATABASE_URL=postgresql://otherapp:<비밀번호>@localhost:5433/ohmyenglish
# 역할 기본 search_path가 otherapp이라 옵션 없이도 자기 스키마를 먼저 본다.
# 커넥션마다 못 박고 싶으면 (권장 — 명시적):
DATABASE_URL=postgresql://otherapp:<비밀번호>@localhost:5433/ohmyenglish?options=-csearch_path%3Dotherapp
```

`?options=-csearch_path%3Dotherapp`의 `%3D`는 `=`의 URL 인코딩이다. libpq 기반
드라이버(psycopg, asyncpg)가 이 형식을 지원한다. 비밀번호는 이 문서에 적지 않는다.

### 4.2 검증된 동작 (호스트에서 직접 돌린 결과)

| # | 확인 | 결과 |
|--:|---|---|
| ① | 호스트에서 `otherapp` 접속 | ✅ (비밀번호 필요 — §2.3) |
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
-- superuser(= ohmy)로. ⚠️ 이 머신에 psql이 없다 → podman exec로 컨테이너 안에서:
--   podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish
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
podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish -c "\dn"
podman exec -i ohmy-pg psql -U otherapp -d ohmyenglish -c "show search_path"   # → otherapp

# ③ 다른 App이 public에 테이블을 못 만드는가 — **ERROR가 정답이다**
podman exec -i ohmy-pg psql -U otherapp -d ohmyenglish \
  -c "create table public.should_fail(x int)"
#   기대: permission denied for schema public

# ④ 권한 안 준 표는 못 읽는가 — 이것도 ERROR가 정답이다
podman exec -i ohmy-pg psql -U otherapp -d ohmyenglish -c "select count(*) from public.users"
#   기대: permission denied for table users
```

③·④가 **성공하면** 최소 권한이 안 걸린 것이다. `grant`를 과하게 준 적이 없는지 확인한다:
`podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish -c "\dp public.*"`

---

## 7. 관련 문서

| 문서 | 무엇 |
|---|---|
| **`docs/ops/shared-database-naming-rules.md`** | **En-Coach 전달용 네이밍·접근 규칙** (R1~R6 + 접속 정보 + 부여된 권한) |
| `docs/database-schema.md` | 표·컬럼의 의미와 **왜 그 값인지**. 컬럼을 읽기 전에 본다 |
| `docs/ops/local-run.md` | 로컬 실행 방법 (DB·백엔드·프론트·게이트) |
| `db/migrations/*.sql` | 스키마 정본. 주석에 결정 근거가 있다 |
| `scripts/db_utils.py` | DSN 계산과 파괴적 재생성의 경계 |
