import asyncio, json, sys
import asyncpg
def dsn(dbname):
    for line in open("/Users/redstar/MyProject/OhMyEnglish/app/backend/.env", encoding="utf-8"):
        if line.startswith("DATABASE_URL="):
            base = line.split("=",1)[1].strip().strip('"').rpartition("/")[0]
            return f"{base}/{dbname}"
async def main(db):
    c = await asyncpg.connect(dsn(db))
    try:
        await c.execute("set default_transaction_read_only = on"); await c.execute("set search_path = ohmyenglish")
        out = {"db": await c.fetchval("select current_database()")}
        for t in ["learning_sessions","utterances","course_day_progress","course_attempts"]:
            out[t] = await c.fetchval(f"select count(*) from {t}")
        out["sessions_max_started"] = str(await c.fetchval("select max(started_at) from learning_sessions"))
    finally:
        await c.close()
    print(json.dumps(out))
if __name__ == "__main__": asyncio.run(main(sys.argv[1]))
