"""Domain services. Raw SQL against an asyncpg connection supplied by the caller.

Every function here takes the `conn` it must run on as its first argument
rather than acquiring one itself: the caller owns the transaction boundary,
which is what lets `utterances.save_final_transcript` persist a transcript and
enqueue its analysis job atomically.

⛔ **경계를 여는 자리는 `async with pool.acquire() as conn, conn.transaction():` 이고 공용 헬퍼가
아니다** (`TASK-145` · 사용자 결정 2026-09-17). 이 문장의 이전 판은 `app.db.tx()` 를 그 수단으로
지목했는데 **그 함수는 호출자가 0건이었고 쓸 수도 없었다** — 인자를 받지 않고 프로세스 전역 pool 을
스스로 얻으므로, 주입된 pool 로 도는 경계 9곳이 그것으로 바꾸면 **주입한 pool 이 무시된다.**
그래서 함수를 지웠고 이 문장을 실제와 맞췄다. ⚠️ 공용 헬퍼를 다시 만들려면 **pool 을 인자로 받는
형태**여야 한다 — 그렇지 않으면 같은 이유로 또 쓰이지 않는다.
"""
