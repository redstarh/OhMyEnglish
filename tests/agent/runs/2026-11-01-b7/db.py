"""읽기 전용 — 격리 DB(ohmyenglish_course_paid) 의 문법 코스 집계 (회차 2026-11-01-b7)."""
import asyncio, json, sys
import asyncpg

def dsn(dbname: str) -> str:
    for line in open("/Users/redstar/MyProject/OhMyEnglish/app/backend/.env", encoding="utf-8"):
        if line.startswith("DATABASE_URL="):
            url = line.split("=", 1)[1].strip().strip('"')
            base, _, _ = url.rpartition("/")
            return f"{base}/{dbname}"
    raise SystemExit("no DATABASE_URL")

async def main(dbname: str) -> None:
    conn = await asyncpg.connect(dsn(dbname))
    try:
        await conn.execute("set default_transaction_read_only = on")
        await conn.execute("set search_path = ohmyenglish")
        out = {"db": await conn.fetchval("select current_database()"), "now": str(await conn.fetchval("select now()"))}
        out["tz"] = [dict(r) for r in await conn.fetch("select timezone from users")]
        out["attempts_total"] = await conn.fetchval("select count(*) from course_attempts")
        out["attempts"] = [ {k: str(v) for k, v in dict(r).items()} for r in await conn.fetch(
            "select sentence_key, transcript, words::text as words, created_at from course_attempts order by created_at")]
        out["by_kst_date"] = [ {k: str(v) for k, v in dict(r).items()} for r in await conn.fetch(
            "select (created_at at time zone 'Asia/Seoul')::date d, count(*) n, count(distinct sentence_key) s from course_attempts group by 1 order by 1")]
        out["progress"] = [ {k: str(v) for k, v in dict(r).items()} for r in await conn.fetch("select * from course_day_progress order by day")]
        out["llm_calls_total"] = await conn.fetchval("select count(*) from llm_calls")
        out["llm_calls_recent"] = [ {k: str(v) for k, v in dict(r).items()} for r in await conn.fetch(
            "select provider, model_id, purpose, input_tokens, output_tokens, called_at from llm_calls where called_at > now() - interval '6 hours' order by called_at")]
    finally:
        await conn.close()
    print(json.dumps(out, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "ohmyenglish_course_paid"))
