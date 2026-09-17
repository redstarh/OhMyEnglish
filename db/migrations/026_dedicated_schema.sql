-- 026: 우리 표를 `public` → 전용 스키마 `ohmyenglish` 로 옮긴다 (`TASK-41` · 캡틴 결정 31 → 122).
--
-- **왜**: En-Coach 만 전용 스키마(`en_coach`)를 갖고 우리는 `public` 에 있어 **비대칭**이었다. 그래서
-- 우리 표가 「기본값 자리」를 차지하고, 남의 `search_path` 폴백이 우리 표로 떨어질 수 있었다
-- (`docs/ops/shared-database-naming-rules.md` W1·§5). 스키마 이름은 그 문서가 `ohmyenglish` 로 지정해
-- 두었다 — 여기서 발명하지 않았다.
--
-- ⛔ **결정 31 이 이 이관을 「모든 구현이 끝난 뒤」로 미뤄 두었고 결정 122 가 그 조건을 열었다.**
--
-- ## 이 마이그레이션이 세 가지를 한다
--
-- 1. `ohmyenglish` 스키마를 만들고 **`public` 에 있는 `ohmy` 소유 표 전부**를 옮긴다.
-- 2. En-Coach 가 읽는 표 셋에 대해 **`public` 에 같은 이름의 뷰**를 남긴다.
-- 3. 역할 `ohmy` 의 `search_path` 를 `ohmyenglish, public` 으로 고정한다.
--
-- ## ⛔ 표를 이름으로 열거하지 않고 «소유자» 로 고른다
--
-- `shared-database-naming-rules.md` R5 가 *"이름만 보고 옮기면 남의 표를 가져갈 수 있다 — 옮기기 전에
-- 소유자까지 확인해야 한다"* 라고 적었고, 그 규칙은 En-Coach 에게 준 것이지만 **우리에게도 그대로
-- 적용된다**. 그래서 `tableowner = 'ohmy'` 로 거른다. 부수 효과로 이 문장은 **앞으로 실수로 `public`
-- 에 만들어진 우리 표까지** 함께 데려온다.
-- ⚠️ 2026-09-17 실측: 대상은 21개였다. **개수를 조건에 넣지 않는다** — 세는 순간 낡는다.
--
-- ## ⛔ En-Coach 를 고치지 않는다 — 그래서 호환 뷰를 남긴다 (사용자 결정 2026-09-17)
--
-- 실측으로 확인한 것: En-Coach 는 R3 가 권한 「자기 스키마에 감싸는 뷰」를 **만들지 않았다**
-- (우리 `public` 표에 의존하는 다른 스키마 객체가 **0건**이었다 — `pg_depend`·`pg_rewrite` 조회).
-- 즉 그쪽 앱이 `public.error_patterns` 를 **이름으로** 가리키고 있고, 표만 옮기면 그 쿼리가 깨진다.
-- 뷰를 남기면 그쪽은 한 줄도 고치지 않는다.
--
-- ⚠️ **뷰는 소유자 권한으로 기반 표를 읽는다** — 뷰의 소유자가 `ohmy`(표 소유자)이므로 En-Coach 는
-- **새 스키마에 `usage` 가 필요 없다.** 그래서 `ohmyenglish` 스키마는 여전히 우리만의 것이다(이관의
-- 목적이 그 대칭이다).
-- ⛔ **표에 걸려 있던 `select` grant 는 표와 함께 새 스키마로 따라간다**(grant 는 객체에 붙는다).
-- 그 상태로 두면 En-Coach 는 그 grant 를 쓸 수 없다(`usage` 가 없으므로) — 해가 없고 되돌리기 쉬우니
-- 건드리지 않는다.
--
-- ## ⛔ 되돌리는 방법 (한 번에 되돌아간다)
--
--   drop view public.error_patterns, public.error_occurrences, public.pronunciation_attempts;
--   do $$ declare t record; begin
--     for t in select tablename from pg_tables where schemaname = 'ohmyenglish' loop
--       execute format('alter table ohmyenglish.%I set schema public', t.tablename);
--     end loop; end $$;
--   alter role ohmy reset search_path;
--   drop schema ohmyenglish;
--
-- ## ⚠️ 함께 바뀌는 규약 둘
--
-- * **백업 범위**: `pg_dump -n public` 은 이제 뷰 셋만 뜬다 → **`-n ohmyenglish`** 를 쓴다.
-- * **`search_path` 를 DSN 이 아니라 역할에 건다.** 이유는 `DATABASE_URL` 환경변수가 DSN 을 덮기
--   때문이다(`scripts/db_utils.base_dsn` 은 그 변수를 우선한다) — DSN 에 걸면 `.env` 를 쓰는 앱에는
--   반영되지 않는다. 역할에 걸면 앱·스크립트·하네스·`psql` 이 **전부** 같은 값을 받는다.
--   선례가 이미 있다: 같은 역할에 `TimeZone='UTC'` 가 걸려 있다(`docs/ops/local-run.md`).
--   ⚠️ 역할 설정은 **DB 경계를 넘는다** — `ohmyenglish_test`·`_smoke` 에도 함께 적용된다. 그것이
--   의도다(그 DB 들도 같은 배치를 쓴다). StockAgent 는 역할이 달라 영향을 받지 않는다.

create schema if not exists ohmyenglish;

-- 표 이동. ⛔ 소유자로 거른다(R5) · 개수를 조건에 넣지 않는다.
do $$
declare
  target record;
begin
  for target in
    select tablename from pg_tables where schemaname = 'public' and tableowner = 'ohmy' order by 1
  loop
    execute format('alter table public.%I set schema ohmyenglish', target.tablename);
  end loop;
end $$;

-- En-Coach 호환 뷰. ⛔ 이 셋만 만든다 — 그쪽에 준 `select` 가 정확히 이 셋이다(§3 의 부여 권한).
-- 넓히면 준 적 없는 표가 `public` 이름으로 노출된다.
create or replace view public.error_patterns as select * from ohmyenglish.error_patterns;
create or replace view public.error_occurrences as select * from ohmyenglish.error_occurrences;
create or replace view public.pronunciation_attempts as
  select * from ohmyenglish.pronunciation_attempts;

-- ⛔ **역할 존재를 확인하고 준다.** 역할은 클러스터 자산이라 이 리포를 처음 세우는 기계에는 없다 —
-- 가드가 없으면 깨끗한 클러스터에서 이 마이그레이션이 `role "en_coach" does not exist` 로 죽는다.
do $$
begin
  if exists (select 1 from pg_roles where rolname = 'en_coach') then
    execute 'grant select on public.error_patterns to en_coach';
    execute 'grant select on public.error_occurrences to en_coach';
    execute 'grant select on public.pronunciation_attempts to en_coach';
  end if;
end $$;

-- 우리 SQL 은 전부 한정자가 없다(2026-09-17 전수: 882건 · `public.` 한정 0건). 그래서 고칠 곳은
-- 882자리가 아니라 이 한 줄이다 — 한정자가 섞여 있었다면 그쪽이 훨씬 비쌌다.
alter role ohmy set search_path = ohmyenglish, public;
