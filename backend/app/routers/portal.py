"""Patient portal: staff-issued token/OTP access links and report viewing."""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.database import db
from app.core.deps import require_role
from app.core.pagination import paginate


router = APIRouter()

DEFAULT_EXPIRY_HOURS = 72
# Only orders whose results were approved by a pathologist are visible.
VISIBLE_STATUSES = ("approved", "report_released")


def _hash_token(raw: str) -> str:
    """SHA-256 hex digest — the only form of the token ever stored."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _generate_otp() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(6))


async def _log_portal_access(patient_id: str, action: str, session_id: Optional[str] = None,
                             ip_address: Optional[str] = None, success: bool = True,
                             error_message: Optional[str] = None, details: Optional[dict] = None):
    doc = {
        "id": str(uuid.uuid4()),
        "patient_id": patient_id,
        "session_id": session_id,
        "action": action,
        "ip_address": ip_address,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": success,
        "error_message": error_message,
    }
    if details:
        doc["details"] = details
    await db.portal_access_logs.insert_one(doc)


async def _validate_session(raw_token: str, ip_address: Optional[str] = None):
    """Return (session, patient) for a valid token, else raise 401/403."""
    session = await db.portal_sessions.find_one({
        "token_hash": _hash_token(raw_token),
        "is_active": True,
    })
    if not session:
        raise HTTPException(status_code=401, detail="Invalid portal token")
    if datetime.fromisoformat(session["expires_at"]) < datetime.now(timezone.utc):
        await db.portal_sessions.update_one({"id": session["id"]}, {"$set": {"is_active": False}})
        raise HTTPException(status_code=401, detail="Portal token expired")
    patient = await db.patients.find_one({"id": session["patient_id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    await db.portal_sessions.update_one(
        {"id": session["id"]},
        {
            "$set": {"last_accessed": datetime.now(timezone.utc).isoformat()},
            "$inc": {"access_count": 1},
        },
    )
    return session, patient


@router.post("/portal/access", response_model=dict)
async def grant_portal_access(body: dict, request: Request,
                              current_user: dict = Depends(require_role("admin", "lab_manager", "receptionist"))):
    """Issue a portal access token (token_link) or OTP for a patient.
    The raw token is returned ONCE — only its SHA-256 digest is stored."""
    patient_id = body.get("patient_id")
    access_type = body.get("access_type", "token_link")
    if access_type not in ("token_link", "otp"):
        raise HTTPException(status_code=400, detail="access_type must be 'token_link' or 'otp'")
    patient = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    try:
        expires_hours = float(body.get("expires_hours") or DEFAULT_EXPIRY_HOURS)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="expires_hours must be a number")
    raw = secrets.token_urlsafe(32) if access_type == "token_link" else _generate_otp()
    now = datetime.now(timezone.utc)
    session_doc = {
        "id": str(uuid.uuid4()),
        "patient_id": patient_id,
        "token_hash": _hash_token(raw),
        "access_type": access_type,
        "created_at": now.isoformat(),
        "expires_at": (now + timedelta(hours=expires_hours)).isoformat(),
        "last_accessed": None,
        "is_active": True,
        "access_count": 0,
        "created_by": current_user["id"],
    }
    await db.portal_sessions.insert_one(session_doc)
    await _log_portal_access(
        patient_id=patient_id,
        action="access_link_created",
        session_id=session_doc["id"],
        ip_address=request.client.host if request.client else None,
        details={"access_type": access_type, "expires_hours": expires_hours, "created_by": current_user["id"]},
    )
    return {
        "access_token": raw,
        "access_type": access_type,
        "expires_at": session_doc["expires_at"],
        "session_id": session_doc["id"],
        "patient_id": patient_id,
    }


@router.get("/portal/reports", response_model=dict)
async def portal_reports(token: str, request: Request):
    """Public (token-authenticated) view of a patient's approved reports."""
    session, patient = await _validate_session(
        token, request.client.host if request.client else None
    )
    orders = await db.orders.find(
        {"patient_id": patient["id"], "status": {"$in": list(VISIBLE_STATUSES)}},
        {"_id": 0},
    ).sort("created_at", -1).to_list(100)
    # Only expose tests whose results were approved.
    visible = []
    for order in orders:
        approved_tests = [
            t for t in order.get("tests", [])
            if isinstance(t.get("result"), dict) and t["result"].get("approved") is True
        ]
        if approved_tests:
            order = dict(order)
            order["tests"] = approved_tests
            visible.append(order)
    await _log_portal_access(
        patient_id=patient["id"],
        action="view_reports",
        session_id=session["id"],
        ip_address=request.client.host if request.client else None,
        details={"order_count": len(visible)},
    )
    return {
        "patient": {
            "id": patient["id"],
            "name": patient["name"],
            "patient_id": patient.get("patient_id"),
            "age": patient.get("age"),
            "gender": patient.get("gender"),
        },
        "orders": visible,
    }


@router.get("/portal/access-logs", response_model=List[dict])
async def list_portal_access_logs(response: Response, page: int = 1, page_size: int = 20,
                                  current_user: dict = Depends(require_role("admin"))):
    skip, limit = paginate(page, page_size)
    total = await db.portal_access_logs.count_documents({})
    logs = await db.portal_access_logs.find({}, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return logs
