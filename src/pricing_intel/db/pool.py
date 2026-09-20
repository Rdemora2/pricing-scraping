"""Shared async connection pool for the API and Procrastinate tasks.

The Scrapy collection pipeline does NOT use this: it runs in its own
subprocess and opens a plain synchronous psycopg connection instead
(see collection/db.py). Both share the SQL text in db/sql.py.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from pricing_intel.config import get_settings

_pool: AsyncConnectionPool | None = None


def get_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is None:
        _pool = AsyncConnectionPool(
            conninfo=get_settings().database_url,
            open=False,
            min_size=1,
            max_size=10,
        )
    return _pool


@asynccontextmanager
async def connection() -> AsyncIterator[AsyncConnection]:
    pool = get_pool()
    if pool.closed:
        await pool.open()
    async with pool.connection() as conn:
        yield conn


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
