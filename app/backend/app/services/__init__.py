"""Domain services. Raw SQL against an asyncpg connection supplied by the caller.

Every function here takes the `conn` it must run on as its first argument
rather than acquiring one itself: the caller owns the transaction boundary,
which is what lets `utterances.save_final_transcript` persist a transcript and
enqueue its analysis job atomically (`app.db.tx()`).
"""
