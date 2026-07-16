import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import asyncpg
from fastapi import Depends

from auth import get_workspace_id

_pool: asyncpg.Pool | None = None


async def create_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=2,
        max_size=10,
    )


async def close_pool() -> None:
    if _pool:
        await _pool.close()


async def get_db(
    workspace_id: Annotated[str, Depends(get_workspace_id)],
) -> AsyncGenerator[asyncpg.Connection, None]:
    """Yield a transaction-scoped connection with app.workspace_id set.

    SET LOCAL means the variable is cleared when the transaction ends,
    so pooled connections never leak one tenant's ID to the next request.
    set_config() is used because SET LOCAL doesn't accept $1 parameters.
    """
    async with _pool.acquire() as conn:
        async with conn.transaction():
            # Switch to the non-superuser role so RLS policies are enforced.
            # SET LOCAL ROLE reverts automatically when the transaction ends,
            # so pooled connections never leak role state across requests.
            await conn.execute("SET LOCAL ROLE authenticated")
            await conn.execute(
                "SELECT set_config('app.workspace_id', $1, true)",
                workspace_id,
            )
            yield conn


@asynccontextmanager
async def get_connection(workspace_id: str) -> AsyncGenerator[asyncpg.Connection, None]:
    """Manual context manager for acquiring a tenant-scoped connection.

    Use this when you need multiple short DB transactions separated by long
    async work (e.g. a graph run) so the connection isn't held across the gap.
    """
    async with _pool.acquire() as conn:
        async with conn.transaction():
            await conn.execute("SET LOCAL ROLE authenticated")
            await conn.execute(
                "SELECT set_config('app.workspace_id', $1, true)",
                workspace_id,
            )
            yield conn
