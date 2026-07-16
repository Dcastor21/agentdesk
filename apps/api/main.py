from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel

import auth
import db
from auth import AuthContext, get_auth
from pipeline.graph import graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    await auth.refresh_jwks()
    await db.create_pool()
    yield
    await db.close_pool()


app = FastAPI(title="AgentDesk API", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


class SessionRequest(BaseModel):
    topic: str


@app.post("/sessions")
async def create_session(
    body: SessionRequest,
    auth_ctx: Annotated[AuthContext, Depends(get_auth)],
):
    workspace_id = auth_ctx["workspace_id"]

    # Short transaction 1: upsert user, insert session row.
    async with db.get_connection(workspace_id) as conn:
        user = await conn.fetchrow(
            """
            INSERT INTO users (workspace_id, clerk_user_id, email)
            VALUES ($1, $2, $3)
            ON CONFLICT (clerk_user_id)
            DO UPDATE SET workspace_id = EXCLUDED.workspace_id
            RETURNING id
            """,
            workspace_id,
            auth_ctx["clerk_user_id"],
            auth_ctx["email"],
        )
        session = await conn.fetchrow(
            """
            INSERT INTO sessions (workspace_id, user_id, topic, status)
            VALUES ($1, $2, $3, 'running')
            RETURNING id
            """,
            workspace_id,
            user["id"],
            body.topic,
        )
    session_id = session["id"]

    # Graph run outside any DB transaction — can take 30–60 s.
    final_status = "failed"
    result: dict = {}
    try:
        result = await graph.ainvoke({"topic": body.topic})
        final_status = "completed"
    finally:
        # Short transaction 2: record outcome regardless of success or failure.
        async with db.get_connection(workspace_id) as conn:
            await conn.execute(
                "UPDATE sessions SET status = $1 WHERE id = $2",
                final_status,
                session_id,
            )

    return {"session_id": str(session_id), "state": result}
