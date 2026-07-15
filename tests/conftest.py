import os

import asyncpg
import pytest
import pytest_asyncio

_DATABASE_URL = os.getenv("DATABASE_URL")


@pytest_asyncio.fixture(scope="function")
async def pool():
    if not _DATABASE_URL:
        pytest.skip("DATABASE_URL not set — skipping integration tests")
    p = await asyncpg.create_pool(_DATABASE_URL, min_size=1, max_size=5)
    yield p
    await p.close()
