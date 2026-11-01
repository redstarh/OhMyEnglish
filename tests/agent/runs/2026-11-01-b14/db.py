"""회차 b14 — 읽기 전용 조회. 사용: db.py dev|paid snap  ·  db.py paid session <id>  ·  db.py paid sql '<select>'"""
import asyncio, json, sys
import asyncpg
def dsn(dbname):
    for line in open("/Users/redstar/MyProject/OhMyEnglish/app/backend/.env", encoding="utf-8"):
        if line.startswith("DATABASE_URL="):
            return line.split("=",1)[1].strip().strip('"').rpartition("/")[0] + "/" + dbname
NAMES = {"dev": "ohmyenglish", "paid": "ohmyenglish_course_paid"}
def j(v): return json.dumps([dict(r) for r in v], default=str, ensure_ascii=False, indent=1)
async def main(which, cmd, arg=None):
    c = await asyncpg.connect(dsn(NAMES[which]))
    try:
        await c.execute("set default_transaction_read_only = on"); await c.execute("set search_path = ohmyenglish")
        if cmd == "snap":
            out = {"db": await c.fetchval("select current_database()")}
            for t in ["learning_sessions","utterances","course_day_progress","course_attempts","analysis_jobs","llm_calls"]:
                try: out[t] = await c.fetchval(f"select count(*) from {t}")
                except Exception as e: out[t] = "ERR " + type(e).__name__
            out["sessions_max_started"] = str(await c.fetchval("select max(started_at) from learning_sessions"))
            print(json.dumps(out, ensure_ascii=False))
        elif cmd == "sql":
            print(j(await c.fetch(arg)))
    finally:
        await c.close()
asyncio.run(main(*sys.argv[1:]))
