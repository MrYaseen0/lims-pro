"""Auth, users, and seed routes."""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials

from audit_logger import AuditAction
from app.core.database import db, audit_logger
from app.core.deps import get_current_user, require_role, check_login_rate_limit, security
from app.core.security import hash_password, verify_password, create_token
from app.core.config import (
    COOKIE_NAME,
    COOKIE_SECURE,
    JWT_EXPIRATION_HOURS,
    REFRESH_COOKIE_NAME,
    REFRESH_TOKEN_EXPIRY_DAYS,
)
from app.core.pagination import paginate
from app.models.schemas import UserCreate, UserLogin, TokenResponse, UserRole
from app.services.seed_data import (
    ensure_doctors_seeded,
    ensure_test_reference_ranges,
    ensure_default_branch,
    SEED_TESTS,
    REFERENCE_RANGES,
)


router = APIRouter()


# --- Refresh-token rotation (opaque tokens) ---

def _hash_refresh_token(raw: str) -> str:
    """SHA-256 hex digest — the only form of the token ever stored."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _issue_refresh_token(user_id: str, rotated_from: Optional[str] = None) -> str:
    """Persist a refresh-token doc and return the RAW token (shown once)."""
    raw = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    await db.refresh_tokens.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "token_hash": _hash_refresh_token(raw),
        "expires_at": (now + timedelta(days=REFRESH_TOKEN_EXPIRY_DAYS)).isoformat(),
        "revoked": False,
        "created_at": now.isoformat(),
        "rotated_from": rotated_from,
    })
    return raw


def _set_refresh_cookie(response: Response, raw: str):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=raw,
        max_age=REFRESH_TOKEN_EXPIRY_DAYS * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/api/auth",
    )


@router.post("/auth/register", response_model=dict)
async def register(user: UserCreate):
    existing = await db.users.find_one({"email": user.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user.model_dump()
    user_dict["id"] = str(uuid.uuid4())
    user_dict["password"] = hash_password(user.password)
    user_dict["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.users.insert_one(user_dict)
    del user_dict["password"]
    if "_id" in user_dict:
        del user_dict["_id"]
    
    # Audit log: User created
    await audit_logger.log(
        action=AuditAction.USER_CREATED,
        user_id=user_dict["id"],
        user_email=user_dict["email"],
        user_role=user_dict["role"],
        entity_type="user",
        entity_id=user_dict["id"],
        entity_name=user_dict["name"],
        details={"registered_role": user_dict["role"]}
    )
    
    return {"message": "User registered successfully", "user": user_dict}

@router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, request: Request, response: Response):
    check_login_rate_limit(request.client.host if request.client else "unknown")
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        # Audit log: Failed login attempt
        await audit_logger.log(
            action=AuditAction.LOGIN_FAILED,
            user_id=None,
            user_email=credentials.email,
            entity_type="auth",
            success=False,
            error_message="Invalid credentials"
        )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get("is_active", True):
        await audit_logger.log(
            action=AuditAction.LOGIN_FAILED,
            user_id=user["id"],
            user_email=credentials.email,
            entity_type="auth",
            success=False,
            error_message="Account deactivated"
        )
        raise HTTPException(status_code=401, detail="Account is deactivated")
    
    token = create_token({"id": user["id"], "email": user["email"], "role": user["role"]})
    user_response = {k: v for k, v in user.items() if k not in ["_id", "password"]}

    # httpOnly cookie so JS/XSS cannot steal the token. The token is still
    # returned in the body for non-browser API clients.
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=JWT_EXPIRATION_HOURS * 3600,
        httponly=True,
        samesite="lax",
        secure=COOKIE_SECURE,
        path="/",
    )

    # Opaque refresh token for rotation; only its SHA-256 digest is stored.
    refresh_raw = await _issue_refresh_token(user["id"])
    _set_refresh_cookie(response, refresh_raw)

    # Audit log: Successful login
    await audit_logger.log(
        action=AuditAction.LOGIN,
        user_id=user["id"],
        user_email=user["email"],
        user_role=user["role"],
        entity_type="auth",
        entity_id=user["id"],
        entity_name=user["name"]
    )
    
    return TokenResponse(access_token=token, user=user_response)

@router.post("/auth/refresh", response_model=dict)
async def refresh_tokens(request: Request, response: Response):
    """Rotate the refresh token: the presented token is revoked and a new
    one is issued. Presenting an already-revoked token is treated as reuse
    (possible theft) and revokes ALL of the user's refresh tokens."""
    raw = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw:
        raise HTTPException(status_code=401, detail="No refresh token")
    doc = await db.refresh_tokens.find_one({"token_hash": _hash_refresh_token(raw)})
    now = datetime.now(timezone.utc)
    if not doc or datetime.fromisoformat(doc["expires_at"]) < now:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    if doc.get("revoked"):
        # Reuse detected — kill the whole chain for this user.
        await db.refresh_tokens.update_many(
            {"user_id": doc["user_id"]}, {"$set": {"revoked": True}}
        )
        raise HTTPException(status_code=401, detail="Refresh token reuse detected")
    await db.refresh_tokens.update_one({"id": doc["id"]}, {"$set": {"revoked": True}})
    new_raw = await _issue_refresh_token(doc["user_id"], rotated_from=doc["id"])
    _set_refresh_cookie(response, new_raw)
    return {"message": "Token refreshed"}

@router.post("/auth/logout", response_model=dict)
async def logout(request: Request, response: Response):
    raw = request.cookies.get(REFRESH_COOKIE_NAME)
    if raw:
        await db.refresh_tokens.update_one(
            {"token_hash": _hash_refresh_token(raw)},
            {"$set": {"revoked": True}},
        )
    response.delete_cookie(key=COOKIE_NAME, path="/")
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/auth")
    return {"message": "Logged out successfully"}

@router.get("/auth/me", response_model=dict)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=List[dict])
async def get_users(response: Response, page: int = 1, page_size: int = 20, current_user: dict = Depends(require_role("admin", "lab_manager"))):
    skip, limit = paginate(page, page_size)
    total = await db.users.count_documents({})
    users = await db.users.find({}, {"_id": 0, "password": 0}).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return users

@router.put("/users/{user_id}", response_model=dict)
async def update_user(user_id: str, updates: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if "password" in updates:
        updates["password"] = hash_password(updates["password"])
    
    result = await db.users.update_one({"id": user_id}, {"$set": updates})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    
    # Audit log: User updated
    await audit_logger.log(
        action=AuditAction.USER_UPDATED,
        user_id=current_user["id"],
        user_email=current_user["email"],
        user_role=current_user["role"],
        entity_type="user",
        entity_id=user_id,
        details={"fields_updated": list(updates.keys())}
    )
    
    return updated


@router.post("/seed", response_model=dict)
async def seed_data(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Bootstrap exception: an empty database (no users yet) may be seeded
    # without auth so the very first admin can be created. Afterwards,
    # only admins may re-run the seed.
    if await db.users.count_documents({}) > 0:
        current_user = await get_current_user(request, credentials)
        if current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Not authorized")
    # Idempotent seeds — safe on every call. Also refreshes databases
    # that were seeded before doctors / reference ranges existed.
    await ensure_doctors_seeded()
    await ensure_test_reference_ranges()
    await ensure_default_branch()

    # Check if already seeded
    admin = await db.users.find_one({"email": "admin@lims.pro"})
    if admin:
        return {"message": "Data already seeded"}
    
    # Create default admin user
    admin_user = {
        "id": str(uuid.uuid4()),
        "email": "admin@lims.pro",
        "name": "System Admin",
        "role": UserRole.ADMIN,
        "phone": "+1234567890",
        "is_active": True,
        "password": hash_password("admin123"),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(admin_user)
    
    # Create sample users
    users = [
        {"email": "technician@lims.pro", "name": "John Technician", "role": UserRole.TECHNICIAN},
        {"email": "pathologist@lims.pro", "name": "Dr. Sarah Path", "role": UserRole.PATHOLOGIST},
        {"email": "receptionist@lims.pro", "name": "Emily Front", "role": UserRole.RECEPTIONIST},
        {"email": "manager@lims.pro", "name": "Mike Manager", "role": UserRole.LAB_MANAGER},
    ]
    for u in users:
        user_doc = {
            "id": str(uuid.uuid4()),
            "email": u["email"],
            "name": u["name"],
            "role": u["role"],
            "phone": "+1234567890",
            "is_active": True,
            "password": hash_password("password123"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.users.insert_one(user_doc)
    
    # Create sample tests (with reference ranges for CBC/RFT/LFT).
    # Skip codes already inserted by ensure_test_reference_ranges() above.
    for t in SEED_TESTS:
        if await db.tests.find_one({"code": t["code"]}):
            continue
        test_doc = {
            "id": str(uuid.uuid4()),
            **t,
            "description": f"Standard {t['name']} test",
            "reference_ranges": REFERENCE_RANGES.get(t["code"], []),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.tests.insert_one(test_doc)
    
    return {"message": "Seed data created successfully", "admin_email": "admin@lims.pro", "admin_password": "admin123"}

# Root endpoint
