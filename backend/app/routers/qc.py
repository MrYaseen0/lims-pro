"""Quality control: control materials, QC runs with Westgard evaluation."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.database import db
from app.core.deps import get_current_user, require_role
from app.core.pagination import paginate
from app.services.qc import evaluate_westgard


router = APIRouter()


def _to_float(value, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{field} must be a number")


@router.post("/qc/controls", response_model=dict)
async def create_control(body: dict, current_user: dict = Depends(require_role("admin", "lab_manager"))):
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    mean = _to_float(body.get("target_mean"), "target_mean")
    sd = _to_float(body.get("sd"), "sd")
    if sd <= 0:
        raise HTTPException(status_code=400, detail="sd must be > 0")
    doc = {
        "id": str(uuid.uuid4()),
        "name": name,
        "test_id": body.get("test_id"),
        "target_mean": mean,
        "sd": sd,
        "unit": body.get("unit"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.qc_controls.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/qc/controls", response_model=List[dict])
async def list_controls(response: Response, page: int = 1, page_size: int = 20,
                        current_user: dict = Depends(get_current_user)):
    skip, limit = paginate(page, page_size)
    total = await db.qc_controls.count_documents({})
    controls = await db.qc_controls.find({}, {"_id": 0}).sort("name", 1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return controls


@router.get("/qc/controls/{control_id}", response_model=dict)
async def get_control(control_id: str, current_user: dict = Depends(get_current_user)):
    control = await db.qc_controls.find_one({"id": control_id}, {"_id": 0})
    if not control:
        raise HTTPException(status_code=404, detail="QC control not found")
    return control


@router.put("/qc/controls/{control_id}", response_model=dict)
async def update_control(control_id: str, body: dict,
                         current_user: dict = Depends(require_role("admin", "lab_manager"))):
    updates = {}
    if "name" in body:
        updates["name"] = body["name"]
    if "test_id" in body:
        updates["test_id"] = body["test_id"]
    if "target_mean" in body:
        updates["target_mean"] = _to_float(body["target_mean"], "target_mean")
    if "sd" in body:
        sd = _to_float(body["sd"], "sd")
        if sd <= 0:
            raise HTTPException(status_code=400, detail="sd must be > 0")
        updates["sd"] = sd
    if "unit" in body:
        updates["unit"] = body["unit"]
    if not updates:
        raise HTTPException(status_code=400, detail="No updatable fields")
    result = await db.qc_controls.update_one({"id": control_id}, {"$set": updates})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="QC control not found")
    return await db.qc_controls.find_one({"id": control_id}, {"_id": 0})


@router.delete("/qc/controls/{control_id}", response_model=dict)
async def delete_control(control_id: str,
                         current_user: dict = Depends(require_role("admin", "lab_manager"))):
    result = await db.qc_controls.delete_one({"id": control_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="QC control not found")
    await db.qc_runs.delete_many({"control_id": control_id})
    return {"message": "QC control deleted", "id": control_id}


@router.post("/qc/controls/{control_id}/runs", response_model=dict)
async def log_qc_run(control_id: str, body: dict,
                     current_user: dict = Depends(require_role("technician", "lab_manager", "admin"))):
    control = await db.qc_controls.find_one({"id": control_id})
    if not control:
        raise HTTPException(status_code=404, detail="QC control not found")
    measured = _to_float(body.get("measured_value"), "measured_value")
    run_date = body.get("date") or datetime.now(timezone.utc).isoformat()
    # History = previous runs (chronological) + this new point last.
    history = await db.qc_runs.find(
        {"control_id": control_id}, {"_id": 0, "measured_value": 1}
    ).sort("date", 1).to_list(10000)
    values = [r["measured_value"] for r in history] + [measured]
    violations = evaluate_westgard(values, control["target_mean"], control["sd"])
    doc = {
        "id": str(uuid.uuid4()),
        "control_id": control_id,
        "date": run_date,
        "measured_value": measured,
        "violations": violations,
        "entered_by": current_user["id"],
    }
    await db.qc_runs.insert_one(doc)
    doc.pop("_id", None)
    return doc


@router.get("/qc/controls/{control_id}/runs", response_model=List[dict])
async def list_qc_runs(control_id: str, response: Response, page: int = 1, page_size: int = 20,
                       current_user: dict = Depends(get_current_user)):
    if not await db.qc_controls.find_one({"id": control_id}, {"_id": 0, "id": 1}):
        raise HTTPException(status_code=404, detail="QC control not found")
    skip, limit = paginate(page, page_size)
    total = await db.qc_runs.count_documents({"control_id": control_id})
    runs = await db.qc_runs.find({"control_id": control_id}, {"_id": 0}).sort("date", -1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return runs


@router.get("/qc/controls/{control_id}/chart-data", response_model=dict)
async def qc_chart_data(control_id: str, current_user: dict = Depends(get_current_user)):
    control = await db.qc_controls.find_one({"id": control_id}, {"_id": 0})
    if not control:
        raise HTTPException(status_code=404, detail="QC control not found")
    runs = await db.qc_runs.find({"control_id": control_id}, {"_id": 0}).sort("date", 1).to_list(10000)
    mean, sd = control["target_mean"], control["sd"]
    points = [
        {"date": r["date"], "value": r["measured_value"], "violations": r.get("violations", [])}
        for r in runs
    ]
    return {
        "points": points,
        "mean": mean,
        "sd": sd,
        "lines": {
            "mean": mean,
            "plus1sd": mean + sd,
            "minus1sd": mean - sd,
            "plus2sd": mean + 2 * sd,
            "minus2sd": mean - 2 * sd,
            "plus3sd": mean + 3 * sd,
            "minus3sd": mean - 3 * sd,
        },
    }
