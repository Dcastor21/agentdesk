import os
from collections.abc import AsyncGenerator
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
            await conn.execute(
                "SELECT set_config('app.workspace_id', $1, true)",
                workspace_id,
            )
            yield conn
