"""읽기 전용 — dev DB(ohmyenglish) 의 문법 코스·사용량 표 지문 (쓰기가 없었는지 대조용)."""
import asyncio, json, sys
import asyncpg
sys.path.insert(0, sys.argv[0].rsplit("/", 1)[0])
from db import dsn
async def main():
    c = await asyncpg.connect(dsn("ohmyenglish"))
    try:
        await c.execute("set default_transaction_read_only = on"); await c.execute("set search_path = ohmyenglish")
        out = {"db": await c.fetchval("select current_database()")}
        out["course_attempts"] = dict(await c.fetchrow("select count(*) n, max(created_at)::text mx from course_attempts"))
        out["course_day_progress"] = dict(await c.fetchrow("select count(*) n, max(updated_at)::text mx from course_day_progress"))
        out["llm_calls"] = dict(await c.fetchrow("select count(*) n, max(called_at)::text mx from llm_calls"))
        out["xact_stats"] = dict(await c.fetchrow("select n_tup_ins+n_tup_upd+n_tup_del w from pg_stat_user_tables where schemaname='ohmyenglish' and relname='course_attempts'"))
    finally:
        await c.close()
    print(json.dumps(out, ensure_ascii=False))
asyncio.run(main())
