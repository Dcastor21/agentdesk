import os
from typing import Annotated

import httpx
from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt

# Populated at startup via refresh_jwks(); requests fail with 503 until ready.
_jwks_cache: dict | None = None

# Clerk puts workspace_id in a custom JWT claim; key is configurable.
_WORKSPACE_CLAIM = os.getenv("CLERK_WORKSPACE_ID_CLAIM", "workspace_id")


async def refresh_jwks() -> None:
    global _jwks_cache
    url = os.environ["CLERK_JWKS_URL"]
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()


async def get_workspace_id(
    authorization: Annotated[str, Header()],
) -> str:
    if _jwks_cache is None:
        raise HTTPException(status_code=503, detail="Auth not ready")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        claims = jwt.decode(token, _jwks_cache, algorithms=["RS256"])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    workspace_id = claims.get(_WORKSPACE_CLAIM)
    if not workspace_id:
        raise HTTPException(
            status_code=401,
            detail=f"Token missing '{_WORKSPACE_CLAIM}' claim",
        )
    return str(workspace_id)
