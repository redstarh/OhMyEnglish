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
DATABASE_URL=postgresql://ohmy:ohmy@localhost:5433/ohmyenglish
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

## 4. ✅ 채택된 구성 — **별도 DB + 외부 테이블로 공유** (2026-08-30 구축·검증 완료)

캡틴 결정: "내부 별도의 database를 생성해서 사용하고, 나중에 OhMyEnglish와 table로 데이터를
함께 공유할 수 있어."

⚠️ **PostgreSQL은 DB가 다르면 일반 쿼리로 조인할 수 없다.** 그래서 공유는 `postgres_fdw`
(외부 테이블)로 잇는다 — 다른 App은 자기 DB에 있는 테이블처럼 우리 표를 **읽고, 자기
테이블과 조인**할 수 있다. 아래는 실제로 만들어 돌려 본 구성이다.

### 4.0 만들어진 것 (현재 상태)

| 대상 | 값 |
|---|---|
| 다른 App의 DB | **`otherapp`** (owner `otherapp`) |
| 다른 App의 역할 | **`otherapp`** — 자기 DB의 소유자. OhMyEnglish DB에는 직접 접근 권한이 없다 |
| 공유 전용 읽기 역할 | **`ohmy_share_ro`** — `ohmyenglish`에 CONNECT + `public` USAGE + **SELECT만** (`error_patterns` · `error_occurrences` · `pronunciation_attempts`) |
| 외부 서버 / 스키마 | `ohmyenglish_srv` → 외부 테이블 3개가 `otherapp` DB의 **`ohmyenglish` 스키마**에 있다 |

접속 URL (비밀번호는 별도 전달 — 이 문서에 적지 않는다):

```bash
DATABASE_URL=postgresql://otherapp:<비밀번호>@localhost:5433/otherapp
```

### 4.0a 검증된 동작 (직접 돌린 결과)

| # | 확인 | 결과 |
|--:|---|---|
| ① | 호스트에서 `otherapp` 접속 | ✅ (비밀번호 필요 — §2.3) |
| ② | `select … from ohmyenglish.error_patterns` | ✅ 우리 dev DB의 실제 행이 보인다 |
| ③ | 자기 테이블 생성·삽입 | ✅ 자기 DB는 자유롭게 쓴다 |
| ④ | **자기 테이블 × 우리 외부 테이블 조인** | ✅ — "table로 데이터를 함께 공유"가 이 형태로 성립한다 |
| ⑤ | 우리 표에 `update` | ✅ **차단됨** (`InsufficientPrivilegeError: permission denied`) |

### 4.0b ⚠️ 이 구성에서 걸렸던 것 — `trust`가 FDW를 막는다

`import foreign schema`가 처음에 이렇게 실패했다:

```
ERROR: password or GSSAPI delegated credentials required
DETAIL: Non-superuser cannot connect if the server does not request a password.
```

postgres_fdw는 **비superuser가 쓸 때 원격이 비밀번호를 실제로 요구할 것**을 강제한다(trust를
악용한 권한 상승 방지). 그런데 컨테이너 내부 접속은 `trust`라 비밀번호를 묻지 않는다(§2.3).
→ superuser가 매핑의 원격 역할을 `ohmy_share_ro`로 **고정해 두었으므로** 그 가드를 해제했다:

```sql
alter user mapping for otherapp server ohmyenglish_srv
  options (add password_required 'false');
```

**왜 안전한가**: 상승 위험은 "비superuser가 임의의 강한 역할로 붙는 것"인데, 매핑을 만든
주체가 superuser이고 원격 역할이 읽기 전용으로 못 박혀 있다. 원격·공유 환경으로 옮길 때는
이 옵션 대신 `pg_hba.conf`의 `127.0.0.1/32`를 `scram-sha-256`으로 바꾸는 쪽이 맞다.

### 4.0c 공유 표를 늘리거나 줄이려면

```sql
-- 늘릴 때: ohmyenglish DB에서 읽기 권한을 주고
grant select on table public.<표이름> to ohmy_share_ro;
-- otherapp DB에서 외부 테이블을 다시 가져온다 (otherapp 역할로 실행해야 한다)
import foreign schema public limit to (<표이름>) from server ohmyenglish_srv into ohmyenglish;

-- 줄일 때
drop foreign table ohmyenglish.<표이름>;                      -- otherapp DB
revoke select on table public.<표이름> from ohmy_share_ro;    -- ohmyenglish DB
```

⚠️ `import foreign schema`는 **현재 사용자의 user mapping**으로 원격에 붙는다 — `ohmy`로
실행하면 `user mapping not found for "ohmy"`가 난다. **`otherapp`으로 실행한다.**

⚠️ 외부 테이블은 **스냅샷이 아니라 뷰처럼 매번 원격을 읽는다.** 우리가 컬럼을 바꾸면
외부 테이블 정의가 낡는다 — 스키마를 바꾸면 다시 `import`한다.

### 4.0d 이름을 바꾸려면

```sql
alter database otherapp rename to <새이름>;   -- 접속 중인 세션이 없어야 한다
alter role otherapp rename to <새이름>;       -- ⚠️ 역할명을 바꾸면 비밀번호를 다시 설정해야 한다
```

---

## 4-alt. 대안 구성 — 스키마로만 나눈다 (DB 공유)

FDW 없이 **네이티브 조인**이 필요하면 이쪽이다. 같은 DB 안이라 조인이 그냥 되고 외부 테이블
재동기화 문제도 없다. 대신 두 앱이 한 DB를 공유하므로 §3의 위험(특히 `public` 오염)을
`revoke`로 막아야 한다.

### 4.1 역할과 스키마를 만든다 (한 번)

```sql
-- superuser(= ohmy)로 접속: psql postgresql://ohmy:ohmy@localhost:5433/ohmyenglish
-- ⚠️ 이 머신에는 psql이 없다. podman으로 컨테이너 안에서 실행한다:
--    podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish

create role otherapp login password '<강한 비밀번호>';
create schema otherapp authorization otherapp;

-- public에 테이블을 만들지 못하게 막는다 (실수 방지 — 이것이 이 가이드의 핵심 한 줄)
revoke create on schema public from otherapp;

-- 그 역할이 접속할 때 자기 스키마를 먼저 보게 한다
alter role otherapp set search_path = otherapp;
```

`authorization otherapp`로 만들면 그 스키마 안에서는 별도 grant 없이 자유롭게
테이블을 만들 수 있다.

### 4.2 다른 앱의 `DATABASE_URL`

```bash
# 역할 기본 search_path를 위에서 정했으므로 URL에 옵션이 없어도 된다
DATABASE_URL=postgresql://otherapp:<비밀번호>@localhost:5433/ohmyenglish

# 역할 기본값에 기대지 않고 커넥션마다 못 박고 싶으면 (권장 — 명시적)
DATABASE_URL=postgresql://otherapp:<비밀번호>@localhost:5433/ohmyenglish?options=-csearch_path%3Dotherapp
```

`?options=-csearch_path%3Dotherapp`의 `%3D`는 `=`의 URL 인코딩이다. libpq 기반
드라이버(psycopg, asyncpg)가 이 형식을 지원한다.

### 4.3 우리 데이터를 **읽어야** 할 때만 최소 권한을 준다

기본은 **권한 없음**이다. 필요한 표만 명시적으로 열어 준다.

```sql
grant usage on schema public to otherapp;              -- 스키마 접근만 (객체 접근은 별도)
grant select on table public.error_patterns to otherapp;   -- 예: 약점 패턴만 읽기
-- 앞으로 만들어질 표까지 자동으로 열지 마라. default privileges는 쓰지 않는다 —
-- 새 표가 조용히 노출된다.
```

> **쓰기 권한은 주지 않는다.** 우리 앱의 불변조건이 앱 코드와 CHECK 제약에 나뉘어 있어
> (예: `pronunciation_attempts`는 `pending` ⇔ `resolved_at is null`, 시도 순서는
> `attempt_seq` identity가 강제) 외부에서 직접 INSERT하면 그 규약이 깨진다. 데이터를
> 넣어야 한다면 표가 아니라 **백엔드 API를 통한다**.

### 4.4 확장(extension)은 DB 단위로 공유된다

`pgcrypto`는 이미 설치돼 있다(001). 다른 앱이 `gen_random_uuid()`를 쓰려면 스키마
한정자 없이 그대로 부를 수 있다 — `create extension`을 다시 실행하지 않는다
(`if not exists`라 에러는 안 나지만 불필요하다).

---

## 5. 세 방식 비교

| 방식 | 조인 | 격리 | 대가 | 상태 |
|---|---|---|---|---|
| **별도 DB + `postgres_fdw`** | 외부 테이블 경유 (가능) | **강함** — 권한·마이그레이션·이름공간이 완전히 분리 | 스키마가 바뀌면 외부 테이블 재`import`. 원격 읽기라 대량 조인은 느릴 수 있다 | ✅ **채택·구축 완료** (§4) |
| 스키마 분리 (DB 공유) | 네이티브 (빠름) | 중간 — 같은 DB라 `public` 오염·권한 실수 여지 | `revoke create on public`을 반드시 걸어야 한다 | 대안 (§4-alt) |
| 별도 컨테이너 (포트 5434 등) | 불가 (FDW로도 네트워크 경유) | 가장 강함 | 리소스 두 배, 포트 관리 | 미사용 |
| `public` 공유 | 네이티브 | **없음** | 이름 충돌 · `schema_migrations` 충돌 · 소유 구분 소실 | ❌ 권장하지 않음 |

**대량 조인이 느려지면** 스키마 분리(§4-alt)로 옮기는 것이 정공법이다. 외부 테이블은 매 쿼리마다
원격을 읽으므로, 큰 표를 반복 조인하면 네이티브보다 확실히 불리하다.

---

## 6. 붙인 뒤 확인 (직접 돌려서 값을 보라)

```bash
# ① 우리 앱이 여전히 정상인가 — 게이트는 app/backend cwd에서만 판정한다
cd app/backend && .venv/bin/pytest -q && .venv/bin/ruff check . \
  && .venv/bin/ruff format --check . && ty check
#   2026-08-30 구축 후 실측: 327 passed (영향 없음)

# ② 별도 DB·역할·외부 테이블이 실제로 있나
podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish -tAc \
  "select datname from pg_database where not datistemplate order by 1"
podman exec -i ohmy-pg psql -U otherapp -d otherapp -c "\det ohmyenglish.*"

# ③ 공유 읽기가 되고 쓰기는 막히나 (otherapp 자격증명으로 호스트에서)
#    select … from ohmyenglish.error_patterns  → 행이 보여야 한다
#    update ohmyenglish.error_patterns …       → permission denied 가 정답이다

# ③ 다른 앱이 public에 테이블을 못 만드는가 (막혔으면 ERROR가 정답이다)
podman exec -i ohmy-pg psql -U otherapp -d ohmyenglish \
  -c "create table public.should_fail(x int)"
```

③이 성공하면 §4.1의 `revoke create on schema public`이 안 걸린 것이다.

---

## 7. 관련 문서

| 문서 | 무엇 |
|---|---|
| `docs/database-schema.md` | 표·컬럼의 의미와 **왜 그 값인지**. 컬럼을 읽기 전에 본다 |
| `docs/ops/local-run.md` | 로컬 실행 방법 (DB·백엔드·프론트·게이트) |
| `db/migrations/*.sql` | 스키마 정본. 주석에 결정 근거가 있다 |
| `scripts/db_utils.py` | DSN 계산과 파괴적 재생성의 경계 |
