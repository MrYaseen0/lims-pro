"""Request dependencies: auth, role guards, login rate limiting."""
from datetime import datetime, timezone, timedelta
from typing import Dict, List

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    COOKIE_NAME,
    LOGIN_RATE_LIMIT,
    LOGIN_RATE_WINDOW_SECONDS,
)
from app.core.database import db

security = HTTPBearer(auto_error=False)


async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    # Prefer the httpOnly cookie; fall back to the Authorization header
    # for API clients / backward compatibility.
    token = credentials.credentials if credentials else request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*allowed_roles: str):
    """Reusable role guard, e.g. Depends(require_role("admin", "lab_manager"))."""
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not authorized")
        return current_user
    return role_checker

# --- Login rate limiting (in-memory sliding window, per process) ---
_login_attempts: Dict[str, List[datetime]] = {}
LOGIN_RATE_LIMIT = 10          # max attempts
LOGIN_RATE_WINDOW_SECONDS = 60 # per this many seconds

def check_login_rate_limit(ip: str):
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=LOGIN_RATE_WINDOW_SECONDS)
    attempts = [t for t in _login_attempts.get(ip, []) if t > window_start]
    if len(attempts) >= LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again in a minute.",
        )
    attempts.append(now)
    _login_attempts[ip] = attempts
