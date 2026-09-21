"""Order and sample routes."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.database import db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.schemas import (
    Order,
    OrderCreate,
    OrderStatus,
    Sample,
    SampleCreate,
    SampleStatus,
    Invoice,
)


router = APIRouter()


@router.post("/orders", response_model=dict)
async def create_order(order: OrderCreate, current_user: dict = Depends(get_current_user)):
    # Get patient info
    patient = await db.patients.find_one({"id": order.patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Calculate totals
    total = sum(t.price for t in order.tests)
    
    order_obj = Order(**order.model_dump())
    order_obj.total_amount = total
    order_obj.net_amount = total - order_obj.discount
    order_obj.created_by = current_user["id"]
    order_obj.patient_name = patient["name"]
    order_obj.status_history = [{
        "status": OrderStatus.REGISTERED,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "by": current_user["id"]
    }]
    
    doc = order_obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["tests"] = [t.model_dump() if hasattr(t, 'model_dump') else t for t in doc["tests"]]
    await db.orders.insert_one(doc)
    
    # Create invoice
    invoice = Invoice(
        order_id=order_obj.id,
        patient_id=order.patient_id,
        amount=total,
        discount=order_obj.discount,
        net_amount=order_obj.net_amount
    )
    invoice_doc = invoice.model_dump()
    invoice_doc["created_at"] = invoice_doc["created_at"].isoformat()
    await db.invoices.insert_one(invoice_doc)
    
    doc.pop("_id", None)
    return doc

@router.get("/orders", response_model=List[dict])
async def get_orders(
    response: Response,
    status: Optional[str] = None, 
    patient_id: Optional[str] = None,
    priority: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if patient_id:
        query["patient_id"] = patient_id
    if priority:
        query["priority"] = priority
    
    skip, limit = paginate(page, page_size)
    total = await db.orders.count_documents(query)
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return orders

@router.get("/orders/{order_id}", response_model=dict)
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Get samples
    samples = await db.samples.find({"order_id": order_id}, {"_id": 0}).to_list(100)
    order["samples"] = samples
    
    # Get invoice
    invoice = await db.invoices.find_one({"order_id": order_id}, {"_id": 0})
    order["invoice"] = invoice
    
    return order

@router.put("/orders/{order_id}/status", response_model=dict)
async def update_order_status(order_id: str, status: OrderStatus, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    status_entry = {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "by": current_user["id"]
    }
    
    await db.orders.update_one(
        {"id": order_id},
        {
            "$set": {"status": status},
            "$push": {"status_history": status_entry}
        }
    )
    
    updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return updated


@router.post("/samples", response_model=dict)
async def create_sample(sample: SampleCreate, current_user: dict = Depends(get_current_user)):
    # Verify order exists
    order = await db.orders.find_one({"id": sample.order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    sample_obj = Sample(**sample.model_dump())
    sample_obj.collector_id = current_user["id"]
    sample_obj.collection_time = datetime.now(timezone.utc)
    sample_obj.status = SampleStatus.COLLECTED
    
    doc = sample_obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["collection_time"] = doc["collection_time"].isoformat() if doc["collection_time"] else None
    await db.samples.insert_one(doc)
    
    # Update order status
    await db.orders.update_one(
        {"id": sample.order_id},
        {
            "$set": {"status": OrderStatus.SAMPLE_COLLECTED},
            "$push": {"status_history": {
                "status": OrderStatus.SAMPLE_COLLECTED,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "by": current_user["id"]
            }}
        }
    )
    
    doc.pop("_id", None)
    return doc

@router.get("/samples", response_model=List[dict])
async def get_samples(response: Response, status: Optional[str] = None, page: int = 1, page_size: int = 20, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    skip, limit = paginate(page, page_size)
    total = await db.samples.count_documents(query)
    samples = await db.samples.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Enrich with order info
    for sample in samples:
        order = await db.orders.find_one({"id": sample["order_id"]}, {"_id": 0, "patient_name": 1, "order_id": 1})
        if order:
            sample["patient_name"] = order.get("patient_name")
            sample["order_number"] = order.get("order_id")
    
    response.headers["X-Total-Count"] = str(total)
    return samples

@router.put("/samples/{sample_id}/status", response_model=dict)
async def update_sample_status(sample_id: str, status: SampleStatus, current_user: dict = Depends(get_current_user)):
    result = await db.samples.update_one(
        {"id": sample_id},
        {"$set": {"status": status, "received_time": datetime.now(timezone.utc).isoformat() if status == SampleStatus.RECEIVED else None}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Sample not found")
    
    updated = await db.samples.find_one({"id": sample_id}, {"_id": 0})
    return updated
