"""asyncpg pool/transaction helpers. Raw SQL only — no ORM."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator

import asyncpg

from app.config import get_settings

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def pool() -> asyncpg.Pool:
    """Return the process-wide asyncpg pool, creating it on first use.

    Guarded by a lock + double-check: without it, concurrent first callers
    all observe `_pool is None` before any of them finishes awaiting
    `asyncpg.create_pool(...)`, so each creates its own pool — leaking every
    pool but whichever one is the last to overwrite `_pool` (and leaking
    the connections of the discarded ones, since nothing ever closes them).
    """
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                settings = get_settings()
                _pool = await asyncpg.create_pool(dsn=settings.database_url)
    return _pool


async def close_pool() -> None:
    """Close the process-wide pool, if one was created."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


@contextlib.asynccontextmanager
async def tx() -> AsyncIterator[asyncpg.Connection]:
    """Acquire a pooled connection and run the block inside a transaction."""
    p = await pool()
    async with p.acquire() as conn, conn.transaction():
        yield conn
