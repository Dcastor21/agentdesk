from contextlib import asynccontextmanager

from fastapi import FastAPI

import auth
import db


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
