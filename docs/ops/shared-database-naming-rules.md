# 공유 PostgreSQL — 네이밍·접근 규칙 (En-Coach 전달용)

> **한 DB(`ohmyenglish`)를 OhMyEnglish와 En-Coach가 함께 쓴다.** 이 문서는 En-Coach 쪽에
> 전달할 **규칙과 접속 정보**이고, **이 문서 하나로 자립한다** — 다른 문서를 함께 받지
> 않아도 된다. 작성 2026-08-30 (OhMyEnglish 팀).

---

## 체크리스트 — En-Coach가 할 일 (5개)

이것만 하면 붙는다. 근거는 아래 §0·§1에 있다.

| # | 할 일 | 어디 | 규칙 |
|--:|---|---|:--:|
| 1 | 표 **9개에 `ec_` 접두어** 일괄 적용 (마이그레이션·모델·쿼리 전부) | `db/migrations/001_initial_schema.sql` 외 | R1 |
| 2 | `search_path`에서 **`public` 제거** — 3곳 | `app/backend/app/db.py:33`·`:41`, `001_initial_schema.sql:4` | R2 |
| 3 | `.env`의 **포트·DB 이름** 교체 (`5432`→`5433`, `en_coach`→`ohmyenglish`) + 비밀번호 | `app/backend/.env` | §2 |
| 4 | `002` 확인 — 1번을 하면 **자동 no-op**이 된다. 안 하면 실패한다 | `002_move_legacy_public_tables_to_en_coach.sql` | R5 |
| 5 | 마이그레이션 추적표를 **`en_coach` 스키마 안**에 둔다 | 마이그레이션 러너 | R4 |

**비밀번호**: `mvs6pZyocJIyISV1fPD7tZVD` (§2에 전체 URL이 있다)

**OhMyEnglish 쪽은 이미 준비됐다**: 역할 `en_coach`, 스키마 `en_coach`(소유자 = 그 역할),
공유 표 3개 읽기 권한, 역할 기본 `search_path = en_coach`.

---

## 0. 지금 무엇이 위험한가 (규칙의 근거)

En-Coach의 표 9개 중 **7개가 OhMyEnglish 표와 이름이 같다**:

```
users · learning_sessions · utterances · error_patterns
error_occurrences · review_tasks · analysis_jobs        ← 7개 겹침
learning_plans · learning_plan_items                    ← En-Coach 고유
```

겹침 자체는 **스키마가 다르면 문제가 아니다.** 문제는 아래 둘이다.

| # | 위험 | 왜 위험한가 |
|--:|---|---|
| **W1** | `search_path = en_coach, public` | `en_coach`에 그 표가 없으면 **조용히 `public`(OhMyEnglish) 표로 떨어진다.** 오류가 아니라 **잘못된 데이터를 읽는다** — 가장 늦게 발견되는 고장이다 |
| **W2** | `002_move_legacy_public_tables_to_en_coach.sql` | "`public`의 9개 표를 `en_coach`로 옮긴다". 공유 DB에서 그 이름들은 **남의 표**다. 가드가 세는 것이 "내 표인가"가 아니라 "이름이 맞는가"뿐이라, 우리 public에 7개가 있어 **`RAISE EXCEPTION`(7 of 9)으로 마이그레이션이 실패한다** — 지금 상태로는 En-Coach가 이 DB에 붙을 수 없다. R1이 이것까지 해결한다 |

두 위험 모두 **이름이 겹치는 것**에서 나온다. 그래서 규칙의 1번이 접두어다.

---

## 1. 규칙 (이대로 전달)

### R1. En-Coach 표에 **`ec_` 접두어를 일괄로 붙인다** ⭐

| 지금 | 바꿀 이름 | 겹침 |
|---|---|:--:|
| `users` | **`ec_users`** | ⚠️ |
| `learning_sessions` | **`ec_learning_sessions`** | ⚠️ |
| `utterances` | **`ec_utterances`** | ⚠️ |
| `error_patterns` | **`ec_error_patterns`** | ⚠️ |
| `error_occurrences` | **`ec_error_occurrences`** | ⚠️ |
| `review_tasks` | **`ec_review_tasks`** | ⚠️ |
| `analysis_jobs` | **`ec_analysis_jobs`** | ⚠️ |
| `learning_plans` | **`ec_learning_plans`** | — |
| `learning_plan_items` | **`ec_learning_plan_items`** | — |

**9개 전부에 붙인다.** 겹치는 7개만 붙이면 규칙이 "겹칠 때만"이 되어 다음 표를 추가할 때마다
우리 스키마를 확인해야 한다 — 그런 규칙은 지켜지지 않는다.

접두어가 사는 이유 3개:

1. **이름 충돌이 물리적으로 불가능해진다.** 스키마 경계가 뚫리는 경로가 하나라도 남으면
   (아래 R2 참조) 이름이 최후의 방어다.
2. **`002`를 고치지 않아도 안전해진다.** 그 마이그레이션은 `public`에서 기대 표를 세는데,
   이름이 `ec_*`면 우리 `public`에 그런 표가 **0개**라 첫 조건(`count = 0`)에서 조용히
   `RETURN`한다. 지금 이름 그대로면 **7/9로 `RAISE EXCEPTION`이 나서 마이그레이션이 실패한다.**
3. **의존이 코드 한 줄이 아니라 이름에 박힌다.** R2는 누가 편의상 `public`을 다시 넣으면
   조용히 무력화되는데, 표 이름은 그렇게 되돌려지지 않는다.

> ⚠️ 이 규칙은 **한 DB를 공유하는 동안의 규칙**이다. En-Coach가 나중에 자기 DB로 독립하면
> 접두어는 불필요해진다 — 그때 떼는 것은 `alter table … rename`이라 어렵지 않다.

### R2. `search_path`에 `public`을 넣지 않는다 (두 번째 방어)

```python
# 지금 (app/backend/app/db.py:33)
cursor.execute(f"SET LOCAL search_path TO {EN_COACH_SCHEMA}, public")

# 이렇게
cursor.execute(f"SET LOCAL search_path TO {EN_COACH_SCHEMA}")
```

이 한 줄이 W1을 없앤다. 자기 스키마에 표가 없으면 **즉시 오류**가 나고, 남의 표로
조용히 떨어지지 않는다. `check_database_connection()`의 `SET search_path`(`:41`)도 같이 바꾼다.

`001_initial_schema.sql:4`의 `SET search_path TO en_coach, public`도 `en_coach`만으로 바꾼다.
그 파일은 자기 표만 만들므로 `public`이 필요 없다.

**R1을 했는데도 이것을 하는 이유**: 두 방어가 막는 것이 다르다. R1은 *이름이 겹쳐서* 생기는
오탐을 막고, R2는 *자기 표가 없을 때* 남의 스키마를 뒤지는 행동 자체를 막는다. 둘 중 하나만
한다면 **R1**을 한다 — 코드 설정보다 이름이 오래 간다.

### R3. 남의 표는 **항상 스키마 한정**으로 읽고, 뷰로 감싼다

```sql
-- ❌ 하지 않는다: 한정자 없이. 어느 스키마인지 코드만 보고 알 수 없다
select * from error_patterns;

-- ✅ 읽기 전용 뷰를 자기 스키마에 하나 만들어 두고 그것만 쓴다
create view en_coach.omy_error_patterns as
  select * from public.error_patterns;
```

**왜 뷰인가**: OhMyEnglish 스키마가 바뀌면 고칠 곳이 **한 군데**다. 앱 코드 여러 곳에
`public.error_patterns`가 흩어지면 그때마다 전수 수정이 된다.

**접두어 규칙 요약** — 셋을 구분한다:

| 대상 | 접두어 | 예 |
|---|---|---|
| En-Coach 자기 표 | **`ec_`** (R1) | `en_coach.ec_users` |
| OhMyEnglish 표를 읽는 뷰 | **`omy_`** | `en_coach.omy_error_patterns` |
| OhMyEnglish 자기 표 | 없음 (지금 `public`에 있다) | `public.error_patterns` |

읽는 사람이 이름만 보고 "내 것 / 남의 것"을 구분할 수 있게 하는 것이 목적이다.

### R4. 마이그레이션 추적표는 자기 스키마 안에

OhMyEnglish는 `public.schema_migrations`를 **파일명 기준**으로 쓴다. 같은 표를 공유하면
`001_...sql` 같은 흔한 이름이 충돌해 **한쪽 마이그레이션이 "이미 적용됨"으로 조용히
건너뛰어진다.** `en_coach.schema_migrations`를 따로 둔다.

### R5. `public`에서 표를 옮겨오는 마이그레이션은 **공유 DB에서 금지**

R1(접두어)을 적용하면 `002`는 **손대지 않아도 자동으로 no-op**이 된다(기대 표가 `public`에
0개 → 첫 조건에서 `RETURN`). 그래도 규칙으로 남기는 이유는 다음에 비슷한 마이그레이션을
쓸 때다 — 이유는 W2다 —
이름만 보고 옮기면 남의 표를 가져갈 수 있다. 꼭 남겨야 한다면 옮기기 전에
**소유자까지 확인**해야 한다:

```sql
-- 이 조건을 만족할 때만 옮긴다: public에 있고, 그 표의 소유자가 en_coach다
select tablename from pg_tables
 where schemaname='public' and tableowner='en_coach';
```

우리 표의 소유자는 `ohmy`이므로 이 조건으로는 절대 걸리지 않는다.
**공유 DB에 legacy가 없다면 002는 그냥 건너뛰는 것이 맞다.**

### R6. 자기 스키마 밖에는 아무것도 만들지 않는다

`en_coach` 스키마 안에서는 자유다. `public`에는 **표를 만들 수 없다**(권한으로 막혀 있다).
새 스키마가 필요하면 우리에게 알린다.

### R7. `public`(OhMyEnglish) 표는 **읽기만 한다 — 고치지 않는다**

권한으로 이미 막혀 있지만 규칙으로도 적는다. **권한은 누군가 편의상 `grant` 한 줄로 열 수
있고, 규칙은 그 요청 자체를 막는다.**

| 하지 않는 것 | 지금 상태 |
|---|---|
| `insert` · `update` · `delete` | 권한 없음 (`SELECT`만) |
| `alter table` · `drop table` · 인덱스·트리거 추가 | 소유자가 아니라 불가 |
| **우리 표를 가리키는 FK를 만든다** | `REFERENCES` 권한 0건이라 불가 |
| 권한이 없는 표를 읽는다 (`users`·`utterances`·`learning_sessions` 등) | 권한 없음 |
| **쓰기 권한을 요청한다** | ← **이것이 R7의 진짜 내용이다** |

**왜 FK를 특별히 적는가**: `en_coach.ec_*` → `public.users` 같은 FK가 생기면 **우리 쪽
삭제와 마이그레이션이 남의 표 때문에 막힌다.** 우리는 그 제약이 있는지도 모르는 채
"왜 지워지지 않지"를 디버깅하게 된다. 지금은 권한으로 막혀 있으니 **쓰기 권한을 열어 줄 때
이것까지 함께 검토**해야 한다.

**권한으로는 막을 수 없는 것 하나 — 긴 트랜잭션.** `SELECT`만으로도 우리 표에 잠금이
걸린다. 우리 표를 읽는 트랜잭션을 오래 열어 두면 우리 마이그레이션(`alter table`)이
그 뒤에서 대기하고, 그동안 우리 앱이 멈춘다. **읽고 나면 곧 커밋한다** — 사람이 지켜야
하는 규칙이라 여기 적는다.

**데이터를 넣어야 하면 표가 아니라 백엔드 API를 쓴다.** 우리 앱의 불변조건이 앱 코드와
CHECK 제약에 나뉘어 있어(예: `pronunciation_attempts`는 `pending` ⇔ `resolved_at is null`,
시도 순서는 `attempt_seq` identity가 강제) 표에 직접 쓰면 그 규약이 조용히 깨진다.

---

## 2. 접속 정보 (En-Coach `.env`)

현재 `.env.example`은 **세 곳이 틀렸다** — 별도 DB 시절의 값이다:

```bash
# ❌ 지금 (app/backend/.env.example)
DATABASE_URL=postgresql://en_coach:change-me@localhost:5432/en_coach
#                                            ~~~~ 포트   ~~~~~~~~ DB

# ✅ 이렇게 — 그대로 복사해 쓴다
DATABASE_URL=postgresql://en_coach:mvs6pZyocJIyISV1fPD7tZVD@localhost:5433/ohmyenglish
```

| 항목 | 값 | 주의 |
|---|---|---|
| host / port | `localhost` / **5433** | 5432가 아니다. 이 머신의 5432는 비어 있고 우리 컨테이너는 5433에 포워딩된다 |
| database | **`ohmyenglish`** | 공유 DB다. `en_coach`라는 DB는 없다(만들었다가 철회했다) |
| user / role | **`en_coach`** | 스키마 `en_coach`의 소유자 |
| password | `mvs6pZyocJIyISV1fPD7tZVD` | **로컬 dev 전용**이다. 이 문서가 git에 있으므로 원격·공유 환경에는 이 값을 쓰지 않는다 |
| search_path | **`en_coach`** | R2. 역할 기본값을 그렇게 설정해 두었다(2026-08-30 확인: 한정자 없이 `error_patterns`를 읽으면 `relation does not exist`로 **차단된다**). 앱이 `SET search_path`로 `public`을 다시 넣으면 이 방어가 풀린다 |

명시적으로 못 박고 싶으면 URL에 붙인다(`%3D`는 `=`의 인코딩):

```bash
DATABASE_URL=postgresql://en_coach:mvs6pZyocJIyISV1fPD7tZVD@localhost:5433/ohmyenglish?options=-csearch_path%3Den_coach
```

**비밀번호를 바꾸려면** (한 줄, 양쪽 `.env`만 갱신하면 된다):

```bash
podman exec -i ohmy-pg psql -U ohmy -d ohmyenglish -c "alter role en_coach password '<새값>'"
```

⚠️ **비밀번호는 반드시 필요하다.** 이 PostgreSQL은 컨테이너 안에서만 `trust`(무비밀번호)이고,
**호스트(`localhost:5433`)에서 오는 접속은 `scram-sha-256`**이다 — 비밀번호 없이·틀린 값으로는
붙지 않는다. `psql`이 이 머신에 설치돼 있지 않아 컨테이너 안에서 확인해야 할 때는
`podman exec -i ohmy-pg psql -U en_coach -d ohmyenglish` 를 쓴다(이때는 비밀번호가 필요 없다).

---

## 3. En-Coach에 부여된 권한 (이게 전부다)

| 대상 | 권한 |
|---|---|
| 스키마 `en_coach` | **소유자** — 자유롭게 만들고 지운다 |
| 데이터베이스 `ohmyenglish` | `CONNECT`, `CREATE`(스키마 생성용 — `001`의 `CREATE SCHEMA IF NOT EXISTS`가 필요로 한다) |
| 스키마 `public` | `USAGE`만 — **표 생성 불가** |
| `public.error_patterns` · `error_occurrences` · `pronunciation_attempts` | **`SELECT`만** |
| 그 밖의 OhMyEnglish 표 (`users`·`utterances`·`learning_sessions` 등) | **권한 없음** — 읽기도 안 된다 |

공유 표를 늘려야 하면 우리에게 요청한다(`grant select` 한 줄).
**쓰기 권한은 주지 않는다** — 이유와 예외 없는 이유는 **R7**에 있다.

---

## 4. ⚠️ 공유의 대가 — dev DB를 재생성하면 양쪽이 함께 사라진다

같은 데이터베이스이므로, 누군가 손으로 dev DB를 drop/재생성하면 `en_coach` 스키마와 그
데이터까지 없어진다. 우리 **자동 테스트는 안전하다**(파괴 대상은 `ohmyenglish_test`·
`ohmyenglish_smoke`뿐). 위험은 사람이 수동으로 재생성할 때다.

→ **En-Coach는 자기 마이그레이션을 언제든 재실행할 수 있게 유지한다.** 그러면 이 사고가
"재실행 한 번"으로 끝난다.

---

## 5. 참고 — OhMyEnglish 쪽 숙제 (En-Coach가 할 일은 아니다)

지금은 En-Coach만 전용 스키마를 갖고 우리는 `public`에 있다. **비대칭이라 우리 표가
"기본값 자리"를 차지한다** — W1이 위험한 이유가 그것이다. 우리 표도 전용 스키마
(`ohmyenglish`)로 옮기고 `public`을 비우면 두 앱이 대칭이 되고 R2가 없어도 안전해진다.
지금 하지 않는 이유는 우리 SQL이 전부 한정자 없이 쓰여 있어 범위가 크기 때문이다 —
`TASKS.md` E절 후속으로 남긴다.
