# backend/middleware/auth.py
"""JWT-based authentication for ArthAI API."""
import uuid
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from config import settings

security = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days


def create_access_token(user_id: str, phone: str) -> str:
    jti = str(uuid.uuid4())
    payload = {
        "sub": user_id,
        "phone": phone,
        "jti": jti,
        "exp": datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS),
        "iat": datetime.utcnow(),
        "type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """Verify JWT token — use as FastAPI dependency."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # SEC-02: Check Redis denylist
    from cache import get_redis
    redis = await get_redis()
    jti = payload.get("jti")
    if jti:
        is_revoked = await redis.get(f"revoked_token:{jti}")
        if is_revoked:
            raise HTTPException(status_code=401, detail="Token has been revoked")

    # ARCH-06: Multi-tenancy JWT sub verification
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Token subject invalid")

    return payload


def get_current_user_id(token: dict = Depends(verify_token)) -> str:
    """Extract user_id from verified JWT payload."""
    return token["sub"]


def get_current_phone(token: dict = Depends(verify_token)) -> str:
    return token["phone"]
