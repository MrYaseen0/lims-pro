"""Test catalog, result entry, and technician/pathologist queue routes."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.database import db
from app.core.deps import get_current_user, require_role
from app.core.pagination import paginate
from app.models.schemas import Test, TestCreate, ResultEntry, ResultApproval, OrderStatus
from app.services.ranges import compute_result_flags, check_critical_values
import uuid


router = APIRouter()


@router.post("/tests", response_model=dict)
async def create_test(test: TestCreate, current_user: dict = Depends(require_role("admin", "lab_manager"))):
    existing = await db.tests.find_one({"code": test.code})
    if existing:
        raise HTTPException(status_code=400, detail="Test code already exists")
    
    test_obj = Test(**test.model_dump())
    doc = test_obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.tests.insert_one(doc)
    doc.pop("_id", None)
    return doc

@router.get("/tests", response_model=List[dict])
async def get_tests(response: Response, category: Optional[str] = None, active_only: bool = True, page: int = 1, page_size: int = 20, current_user: dict = Depends(get_current_user)):
    query = {}
    if category:
        query["category"] = category
    if active_only:
        query["is_active"] = True
    skip, limit = paginate(page, page_size)
    total = await db.tests.count_documents(query)
    tests = await db.tests.find(query, {"_id": 0}).sort("name", 1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return tests

@router.get("/tests/{test_id}", response_model=dict)
async def get_test(test_id: str, current_user: dict = Depends(get_current_user)):
    test = await db.tests.find_one({"id": test_id}, {"_id": 0})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

@router.put("/tests/{test_id}", response_model=dict)
async def update_test(test_id: str, updates: dict, current_user: dict = Depends(require_role("admin", "lab_manager"))):
    result = await db.tests.update_one({"id": test_id}, {"$set": updates})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Test not found")
    updated = await db.tests.find_one({"id": test_id}, {"_id": 0})
    return updated

@router.get("/test-categories", response_model=List[str])
async def get_test_categories(current_user: dict = Depends(get_current_user)):
    categories = await db.tests.distinct("category")
    return categories


@router.post("/results", response_model=dict)
async def enter_result(result: ResultEntry, current_user: dict = Depends(require_role("technician", "lab_manager", "admin"))):
    order = await db.orders.find_one({"id": result.order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Auto-compute H/L flags against the test's reference ranges
    test_doc = await db.tests.find_one({"id": result.test_id}, {"_id": 0})
    flags, auto_abnormal = compute_result_flags(test_doc, result.values)
    is_abnormal = auto_abnormal or result.is_abnormal  # technician checkbox stays as manual override

    # Update the specific test result in the order
    tests = order.get("tests", [])
    for i, test in enumerate(tests):
        if test["test_id"] == result.test_id:
            tests[i]["result"] = {
                "values": result.values,
                "flags": flags,
                "is_abnormal": is_abnormal,
                "auto_abnormal": auto_abnormal,
                "technician_notes": result.technician_notes,
                "entered_by": current_user["id"],
                "entered_at": datetime.now(timezone.utc).isoformat()
            }
            tests[i]["status"] = "completed"
            break
    
    await db.orders.update_one(
        {"id": result.order_id},
        {
            "$set": {
                "tests": tests,
                "status": OrderStatus.UNDER_REVIEW
            },
            "$push": {"status_history": {
                "status": OrderStatus.UNDER_REVIEW,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "by": current_user["id"]
            }}
        }
    )

    # Check for critical (panic) values and create alerts
    criticals = check_critical_values(test_doc, result.values)
    for crit in criticals:
        alert = {
            "id": str(uuid.uuid4()),
            "order_id": result.order_id,
            "test_id": result.test_id,
            "patient_id": order.get("patient_id"),
            "parameter": crit["parameter"],
            "value": crit["value"],
            "critical_low": crit["critical_low"],
            "critical_high": crit["critical_high"],
            "direction": crit["direction"],
            "status": "pending",  # pending -> acknowledged
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user["id"],
            "acknowledged_by": None,
            "acknowledged_at": None,
        }
        await db.critical_alerts.insert_one(alert)
    
    updated = await db.orders.find_one({"id": result.order_id}, {"_id": 0})
    # Include critical alert info in response
    if criticals:
        updated["_critical_alerts"] = criticals
    return updated

@router.get("/technician/queue", response_model=List[dict])
async def get_technician_queue(response: Response, page: int = 1, page_size: int = 20, current_user: dict = Depends(get_current_user)):
    # Get orders that have samples collected but results not entered
    skip, limit = paginate(page, page_size)
    queue_query = {"status": {"$in": [OrderStatus.SAMPLE_COLLECTED, OrderStatus.IN_LAB]}}
    total = await db.orders.count_documents(queue_query)
    orders = await db.orders.find(
        queue_query,
        {"_id": 0}
    ).sort("priority", -1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    
    # Enrich with sample info
    for order in orders:
        samples = await db.samples.find({"order_id": order["id"]}, {"_id": 0}).to_list(10)
        order["samples"] = samples
        
        # Get patient info
        patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0, "name": 1, "age": 1, "gender": 1})
        if patient:
            order["patient"] = patient
    
    return orders


@router.post("/approve", response_model=dict)
async def approve_result(approval: ResultApproval, current_user: dict = Depends(require_role("pathologist", "lab_manager", "admin"))):
    
    order = await db.orders.find_one({"id": approval.order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update test approval
    tests = order.get("tests", [])
    all_approved = True
    for i, test in enumerate(tests):
        if test["test_id"] == approval.test_id:
            if "result" not in tests[i]:
                tests[i]["result"] = {}
            tests[i]["result"]["approved"] = approval.approved
            tests[i]["result"]["approved_by"] = current_user["id"]
            tests[i]["result"]["approved_at"] = datetime.now(timezone.utc).isoformat()
            tests[i]["result"]["pathologist_notes"] = approval.pathologist_notes
            tests[i]["status"] = "approved" if approval.approved else "rejected"
        
        if tests[i].get("status") != "approved":
            all_approved = False
    
    new_status = OrderStatus.APPROVED if all_approved else OrderStatus.UNDER_REVIEW
    
    await db.orders.update_one(
        {"id": approval.order_id},
        {
            "$set": {"tests": tests, "status": new_status},
            "$push": {"status_history": {
                "status": new_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "by": current_user["id"]
            }}
        }
    )
    
    updated = await db.orders.find_one({"id": approval.order_id}, {"_id": 0})
    return updated

@router.get("/pathologist/queue", response_model=List[dict])
async def get_pathologist_queue(response: Response, page: int = 1, page_size: int = 20, current_user: dict = Depends(get_current_user)):
    skip, limit = paginate(page, page_size)
    queue_query = {"status": OrderStatus.UNDER_REVIEW}
    total = await db.orders.count_documents(queue_query)
    orders = await db.orders.find(
        queue_query,
        {"_id": 0}
    ).sort("created_at", 1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    
    for order in orders:
        patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0, "name": 1, "age": 1, "gender": 1})
        if patient:
            order["patient"] = patient
    
    return orders

# --- Critical (panic) value alerts ---

@router.get("/critical-alerts", response_model=List[dict])
async def list_critical_alerts(
    response: Response,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user),
):
    """List critical value alerts. Filter by status: pending, acknowledged."""
    query = {}
    if status:
        query["status"] = status
    skip, limit = paginate(page, page_size)
    total = await db.critical_alerts.count_documents(query)
    alerts = await db.critical_alerts.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    # Enrich with patient info
    for alert in alerts:
        patient = await db.patients.find_one({"id": alert.get("patient_id")}, {"_id": 0, "name": 1, "patient_id": 1})
        if patient:
            alert["patient"] = patient
    return alerts


@router.post("/critical-alerts/{alert_id}/acknowledge", response_model=dict)
async def acknowledge_critical_alert(
    alert_id: str,
    current_user: dict = Depends(require_role("pathologist", "lab_manager", "admin", "doctor")),
):
    """Acknowledge a critical alert (records who/when)."""
    alert = await db.critical_alerts.find_one({"id": alert_id})
    if not alert:
        raise HTTPException(status_code=404, detail="Critical alert not found")
    if alert.get("status") == "acknowledged":
        return {"message": "Already acknowledged", "id": alert_id}
    now = datetime.now(timezone.utc).isoformat()
    await db.critical_alerts.update_one(
        {"id": alert_id},
        {"$set": {
            "status": "acknowledged",
            "acknowledged_by": current_user["id"],
            "acknowledged_at": now,
        }}
    )
    updated = await db.critical_alerts.find_one({"id": alert_id}, {"_id": 0})
    return updated
