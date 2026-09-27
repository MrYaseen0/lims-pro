"""Inventory: reagents and consumables stock management."""
import uuid
from datetime import datetime, timezone, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.database import db
from app.core.deps import require_role, get_branch_scope
from app.core.pagination import paginate


router = APIRouter()

EXPIRING_SOON_DAYS = 30
CATEGORIES = ("reagent", "consumable")


def _parse_date(value) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value)).date()
    except ValueError:
        return None


def _validate_item(body: dict) -> dict:
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    category = body.get("category")
    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail=f"category must be one of {CATEGORIES}")
    try:
        quantity = float(body.get("quantity", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="quantity must be a number")
    try:
        min_stock = float(body.get("min_stock", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="min_stock must be a number")
    expiry = body.get("expiry_date")
    if expiry and _parse_date(expiry) is None:
        raise HTTPException(status_code=400, detail="expiry_date must be an ISO date")
    return {
        "name": name,
        "category": category,
        "lot_number": body.get("lot_number"),
        "quantity": quantity,
        "unit": body.get("unit"),
        "min_stock": min_stock,
        "expiry_date": expiry,
        "supplier": body.get("supplier"),
    }


@router.post("/inventory", response_model=dict)
async def create_item(body: dict, request: Request,
                     current_user: dict = Depends(require_role("admin", "lab_manager"))):
    branch_id = await get_branch_scope(request, current_user)
    item = _validate_item(body)
    doc = {
        "id": str(uuid.uuid4()),
        **item,
        "branch_id": branch_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.inventory_items.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/inventory", response_model=List[dict])
async def list_items(response: Response, request: Request, category: Optional[str] = None,
                     search: Optional[str] = None, page: int = 1, page_size: int = 20,
                     current_user: dict = Depends(require_role("admin", "lab_manager"))):
    branch_id = await get_branch_scope(request, current_user)
    query = {}
    if branch_id:
        query["branch_id"] = branch_id
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"supplier": {"$regex": search, "$options": "i"}},
            {"lot_number": {"$regex": search, "$options": "i"}},
        ]
    skip, limit = paginate(page, page_size)
    total = await db.inventory_items.count_documents(query)
    items = await db.inventory_items.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return items


# NOTE: /inventory/alerts must be registered before /inventory/{item_id}.
@router.get("/inventory/alerts", response_model=dict)
async def inventory_alerts(request: Request,
                           current_user: dict = Depends(require_role("admin", "lab_manager"))):
    branch_id = await get_branch_scope(request, current_user)
    query = {"branch_id": branch_id} if branch_id else {}
    items = await db.inventory_items.find(query, {"_id": 0}).to_list(10000)
    today = date.today()
    expired, expiring_soon, low_stock = [], [], []
    for item in items:
        qty, minimum = item.get("quantity") or 0, item.get("min_stock") or 0
        if qty <= minimum:
            low_stock.append(item)
        exp = _parse_date(item.get("expiry_date"))
        if exp is None:
            continue
        if exp < today:
            expired.append(item)
        elif (exp - today).days <= EXPIRING_SOON_DAYS:
            expiring_soon.append(item)
    return {"expired": expired, "expiring_soon": expiring_soon, "low_stock": low_stock}


@router.get("/inventory/{item_id}", response_model=dict)
async def get_item(item_id: str, request: Request,
                   current_user: dict = Depends(require_role("admin", "lab_manager"))):
    branch_id = await get_branch_scope(request, current_user)
    query = {"id": item_id}
    if branch_id:
        query["branch_id"] = branch_id
    item = await db.inventory_items.find_one(query, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.put("/inventory/{item_id}", response_model=dict)
async def update_item(item_id: str, body: dict, request: Request,
                      current_user: dict = Depends(require_role("admin", "lab_manager"))):
    branch_id = await get_branch_scope(request, current_user)
    query = {"id": item_id}
    if branch_id:
        query["branch_id"] = branch_id
    existing = await db.inventory_items.find_one(query)
    if not existing:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    updates = _validate_item({**existing, **body})
    await db.inventory_items.update_one({"id": item_id}, {"$set": updates})
    return await db.inventory_items.find_one({"id": item_id}, {"_id": 0})


@router.delete("/inventory/{item_id}", response_model=dict)
async def delete_item(item_id: str, request: Request,
                      current_user: dict = Depends(require_role("admin", "lab_manager"))):
    branch_id = await get_branch_scope(request, current_user)
    query = {"id": item_id}
    if branch_id:
        query["branch_id"] = branch_id
    result = await db.inventory_items.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return {"message": "Inventory item deleted", "id": item_id}
