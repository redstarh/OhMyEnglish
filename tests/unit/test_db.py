"""Fix round 1 — `app.db.pool()` concurrency regression test.

Review finding: the lazy-singleton `_pool` has no concurrency guard. If N
coroutines call `pool()` before the first `asyncpg.create_pool()` call
resolves, they all observe `_pool is None` and all call `create_pool`,
leaking every pool but the last one written (and leaking their
connections — nothing ever closes them). This test proves `create_pool` is
invoked exactly once even when many callers race to initialize the pool
concurrently, using a fake `create_pool` that yields control (`await
asyncio.sleep(0)`) before returning, to force the interleaving the real
race depends on.
"""

from __future__ import annotations

import asyncio

import pytest

from app import db as db_module


class _FakeSettings:
    database_url = "postgresql://fake:fake@localhost/fake"


class _FakePool:
    async def close(self) -> None:
        return None


@pytest.fixture(autouse=True)
def _reset_pool_singleton(monkeypatch):
    """`_pool` is a process-wide global — never let one test's fake pool
    leak into another test."""
    monkeypatch.setattr(db_module, "_pool", None)
    yield
    monkeypatch.setattr(db_module, "_pool", None)


async def test_pool_calls_create_pool_exactly_once_under_concurrent_first_use(monkeypatch):
    call_count = 0
    fake_pool = _FakePool()

    async def fake_create_pool(dsn: str):
        nonlocal call_count
        call_count += 1
        # Yield control here so other concurrent callers get a chance to
        # run before this call returns — this is exactly the race window
        # the missing lock exposes.
        await asyncio.sleep(0)
        return fake_pool

    monkeypatch.setattr(db_module, "get_settings", lambda: _FakeSettings())
    monkeypatch.setattr(db_module.asyncpg, "create_pool", fake_create_pool)

    results = await asyncio.gather(*(db_module.pool() for _ in range(20)))

    assert call_count == 1, f"asyncpg.create_pool called {call_count} times, expected 1"
    assert all(result is fake_pool for result in results)
