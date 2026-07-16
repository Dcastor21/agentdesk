import os
import pathlib
import sys

import asyncpg
import pytest
import pytest_asyncio

# Make apps/api importable in all tests (pipeline, nodes, state, etc.)
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "apps" / "api"))

_DATABASE_URL = os.getenv("DATABASE_URL")
_ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")


@pytest_asyncio.fixture(scope="function")
async def pool():
    if not _DATABASE_URL:
        pytest.skip("DATABASE_URL not set — skipping integration tests")
    p = await asyncpg.create_pool(_DATABASE_URL, min_size=1, max_size=5)
    yield p
    await p.close()


@pytest.fixture
def require_anthropic():
    if not _ANTHROPIC_API_KEY:
        pytest.skip("ANTHROPIC_API_KEY not set — skipping LLM integration tests")
