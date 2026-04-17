"""
FastAPI dependencies for authentication.

TODO: Full RS256 JWKS verification is implemented below.
      For production, ensure SUPABASE_URL is set in environment.
      If not set, falls back to unverified decode (dev mode only).
"""
import time
import base64
import json
from typing import Optional

import httpx
from fastapi import Header, HTTPException
from jose import jwt, JWTError

from config import get_settings

# In-memory JWKS cache: (jwks_data, expires_at)
_jwks_cache: tuple[Optional[dict], float] = (None, 0.0)
_JWKS_TTL = 3600  # 1 hour


async def _get_jwks() -> Optional[dict]:
    global _jwks_cache
    jwks_data, expires_at = _jwks_cache
    now = time.time()

    if jwks_data is not None and now < expires_at:
        return jwks_data

    settings = get_settings()
    if not settings.SUPABASE_URL:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
            )
            resp.raise_for_status()
            jwks_data = resp.json()
            _jwks_cache = (jwks_data, now + _JWKS_TTL)
            return jwks_data
    except Exception:
        return None


def _decode_unverified(token: str) -> dict:
    """Base64-decode the JWT payload without signature verification (dev/fallback mode)."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT structure")
        # Add padding if needed
        payload_b64 = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(payload_b64))
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid JWT: {e}")


async def verify_supabase_jwt(
    authorization: Optional[str] = Header(None),
) -> dict:
    """
    Verify a Supabase JWT from the Authorization header.

    - Fetches JWKS from Supabase and verifies RS256 signature.
    - Falls back to unverified decode if SUPABASE_URL is not configured (dev mode).
    - Returns {"user_id": str, "email": str}
    """
    # TEMP: auth bypass for dashboard debugging. Return a dummy user when no
    # Authorization header is sent. Remove this block to re-enable auth.
    if not authorization:
        return {"user_id": "dev-user", "email": "dev@localhost"}

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization header must start with 'Bearer '")

    token = authorization[len("Bearer "):]

    jwks = await _get_jwks()

    if jwks is None:
        # Dev mode: no SUPABASE_URL configured — skip signature verification
        payload = _decode_unverified(token)
    else:
        try:
            payload = jwt.decode(
                token,
                jwks,
                algorithms=["RS256"],
                audience="authenticated",
                options={"verify_exp": True},
            )
        except JWTError as e:
            raise HTTPException(status_code=401, detail=f"JWT verification failed: {e}")

    user_id = payload.get("sub")
    email = payload.get("email", "")

    if not user_id:
        raise HTTPException(status_code=401, detail="JWT missing 'sub' claim")

    return {"user_id": user_id, "email": email}
