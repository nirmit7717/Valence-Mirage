"""Auth utilities — JWT creation/verification, password hashing."""

from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException, Header
from jose import JWTError, jwt
from passlib.context import CryptContext

import config

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXPIRATION_HOURS)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


async def get_current_user(authorization: str | None = Header(None)) -> dict | None:
    """Optional auth dependency — returns user dict if valid JWT, else None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:]
    payload = decode_access_token(token)
    if not payload:
        return None
    # payload contains {"sub": user_id, "username": ..., "role": ...}
    return {
        "id": payload.get("sub"),
        "username": payload.get("username"),
        "role": payload.get("role"),
    }


async def require_auth(user: dict | None = Depends(get_current_user)) -> dict:
    """Required auth — raises 401 if no valid token."""
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def require_admin(user: dict = Depends(require_auth)) -> dict:
    """Require admin role."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
