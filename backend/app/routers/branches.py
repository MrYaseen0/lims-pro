"""Branch management (multi-branch support)."""
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.database import db
from app.core.deps import get_current_user, require_role
from app.core.pagination import paginate


router = APIRouter()


@router.get("/branches", response_model=List[dict])
async def list_branches(response: Response, page: int = 1, page_size: int = 50,
                        current_user: dict = Depends(get_current_user)):
    skip, limit = paginate(page, page_size)
    total = await db.branches.count_documents({})
    branches = await db.branches.find({}, {"_id": 0}).sort("name", 1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return branches


@router.post("/branches", response_model=dict)
async def create_branch(body: dict, current_user: dict = Depends(require_role("admin"))):
    name = (body.get("name") or "").strip()
    code = (body.get("code") or "").strip().upper()
    if not name or not code:
        raise HTTPException(status_code=400, detail="name and code are required")
    if await db.branches.find_one({"code": code}):
        raise HTTPException(status_code=400, detail="Branch code already exists")
    doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "code": code,
        "address": body.get("address", ""),
        "phone": body.get("phone", ""),
        "is_active": body.get("is_active", True),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.branches.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.put("/branches/{branch_id}", response_model=dict)
async def update_branch(branch_id: str, body: dict,
                        current_user: dict = Depends(require_role("admin"))):
    if "code" in body:
        new_code = (body["code"] or "").strip().upper()
        clash = await db.branches.find_one({"code": new_code})
        if clash and clash["id"] != branch_id:
            raise HTTPException(status_code=400, detail="Branch code already exists")
        body["code"] = new_code
    allowed = {k: body[k] for k in ("name", "code", "address", "phone", "is_active") if k in body}
    if not allowed:
        raise HTTPException(status_code=400, detail="No updatable fields")
    result = await db.branches.update_one({"id": branch_id}, {"$set": allowed})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Branch not found")
    return await db.branches.find_one({"id": branch_id}, {"_id": 0})


@router.delete("/branches/{branch_id}", response_model=dict)
async def delete_branch(branch_id: str, current_user: dict = Depends(require_role("admin"))):
    branch = await db.branches.find_one({"id": branch_id})
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    if branch.get("code") == "MAIN":
        raise HTTPException(status_code=400, detail="The default branch cannot be deleted")
    await db.branches.delete_one({"id": branch_id})
    return {"message": "Branch deleted", "id": branch_id}
