"""F02 — RLS isolation: two workspaces cannot read each other's rows."""

import uuid

import asyncpg


async def _set_workspace(conn: asyncpg.Connection, workspace_id: uuid.UUID) -> None:
    """Switch to authenticated role and set the workspace discriminator.

    Mirrors exactly what db.get_db() does in production so the test exercises
    the same RLS path the API uses.
    """
    await conn.execute("SET LOCAL ROLE authenticated")
    await conn.execute(
        "SELECT set_config('app.workspace_id', $1, true)",
        str(workspace_id),
    )


async def _seed_workspace(pool: asyncpg.Pool, ws_id: uuid.UUID, label: str) -> uuid.UUID:
    """Insert workspace → user → session; returns the user id."""
    user_id = uuid.uuid4()
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _set_workspace(conn, ws_id)
            await conn.execute(
                "INSERT INTO workspaces (id, name) VALUES ($1, $2)",
                ws_id, label,
            )
            await conn.execute(
                "INSERT INTO users (id, workspace_id, clerk_user_id, email)"
                " VALUES ($1, $2, $3, $4)",
                user_id, ws_id,
                f"clerk_{ws_id}",
                f"user@{label.lower().replace(' ', '')}.test",
            )
            await conn.execute(
                "INSERT INTO sessions (workspace_id, user_id, topic)"
                " VALUES ($1, $2, $3)",
                ws_id, user_id, f"topic for {label}",
            )
    return user_id


async def _teardown(pool: asyncpg.Pool, ws_id: uuid.UUID) -> None:
    async with pool.acquire() as conn:
        async with conn.transaction():
            await _set_workspace(conn, ws_id)
            await conn.execute("DELETE FROM sessions WHERE workspace_id = $1", ws_id)
            await conn.execute("DELETE FROM users    WHERE workspace_id = $1", ws_id)
            await conn.execute("DELETE FROM workspaces WHERE id = $1", ws_id)


async def test_sessions_isolated_between_workspaces(pool: asyncpg.Pool) -> None:
    ws_a, ws_b = uuid.uuid4(), uuid.uuid4()
    await _seed_workspace(pool, ws_a, "WS A")
    await _seed_workspace(pool, ws_b, "WS B")

    try:
        # Workspace A sees only its own session.
        async with pool.acquire() as conn:
            async with conn.transaction():
                await _set_workspace(conn, ws_a)
                rows = await conn.fetch("SELECT workspace_id FROM sessions")
        assert len(rows) == 1, f"expected 1 row for WS A, got {len(rows)}"
        assert rows[0]["workspace_id"] == ws_a

        # Workspace B sees only its own session.
        async with pool.acquire() as conn:
            async with conn.transaction():
                await _set_workspace(conn, ws_b)
                rows = await conn.fetch("SELECT workspace_id FROM sessions")
        assert len(rows) == 1, f"expected 1 row for WS B, got {len(rows)}"
        assert rows[0]["workspace_id"] == ws_b

        # authenticated role with no workspace_id → RLS returns zero rows, not an error.
        async with pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("SET LOCAL ROLE authenticated")
                rows = await conn.fetch("SELECT * FROM sessions")
        assert len(rows) == 0, "authenticated role with no workspace_id should see zero rows"

    finally:
        await _teardown(pool, ws_a)
        await _teardown(pool, ws_b)
