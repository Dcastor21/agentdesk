import os
from typing import Annotated, TypedDict

import httpx
from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwt

_jwks_cache: dict | None = None
_WORKSPACE_CLAIM = os.getenv("CLERK_WORKSPACE_ID_CLAIM", "workspace_id")


async def refresh_jwks() -> None:
    global _jwks_cache
    url = os.environ["CLERK_JWKS_URL"]
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()


class AuthContext(TypedDict):
    workspace_id: str
    clerk_user_id: str
    email: str


async def get_auth(authorization: Annotated[str, Header()]) -> AuthContext:
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
            status_code=401, detail=f"Token missing '{_WORKSPACE_CLAIM}' claim"
        )
    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")
    # email may not be present in all JWT templates; fall back to a safe placeholder
    email = claims.get("email") or f"{clerk_user_id}@clerk.invalid"
    return AuthContext(
        workspace_id=str(workspace_id),
        clerk_user_id=str(clerk_user_id),
        email=str(email),
    )


async def get_workspace_id(
    auth: Annotated[AuthContext, Depends(get_auth)],
) -> str:
    """Thin wrapper kept for get_db compatibility."""
    return auth["workspace_id"]
