"""Invoice and payment routes."""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.database import db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.schemas import PaymentCreate, PaymentStatus


router = APIRouter()


@router.get("/invoices", response_model=List[dict])
async def get_invoices(response: Response, status: Optional[str] = None, page: int = 1, page_size: int = 20, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["payment_status"] = status
    skip, limit = paginate(page, page_size)
    total = await db.invoices.count_documents(query)
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    
    for invoice in invoices:
        patient = await db.patients.find_one({"id": invoice["patient_id"]}, {"_id": 0, "name": 1, "phone": 1})
        if patient:
            invoice["patient_name"] = patient.get("name")
            invoice["patient_phone"] = patient.get("phone")
    
    return invoices

@router.get("/invoices/{invoice_id}", response_model=dict)
async def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    patient = await db.patients.find_one({"id": invoice["patient_id"]}, {"_id": 0})
    order = await db.orders.find_one({"id": invoice["order_id"]}, {"_id": 0})
    
    invoice["patient"] = patient
    invoice["order"] = order
    return invoice

@router.post("/payments", response_model=dict)
async def record_payment(payment: PaymentCreate, current_user: dict = Depends(get_current_user)):
    invoice = await db.invoices.find_one({"id": payment.invoice_id})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    payment_record = {
        "amount": payment.amount,
        "mode": payment.payment_mode,
        "reference": payment.reference,
        "recorded_by": current_user["id"],
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }
    
    total_paid = sum(p.get("amount", 0) for p in invoice.get("payments", [])) + payment.amount
    
    if total_paid >= invoice["net_amount"]:
        new_status = PaymentStatus.PAID
    elif total_paid > 0:
        new_status = PaymentStatus.PARTIAL
    else:
        new_status = PaymentStatus.PENDING
    
    await db.invoices.update_one(
        {"id": payment.invoice_id},
        {
            "$set": {"payment_status": new_status},
            "$push": {"payments": payment_record}
        }
    )
    
    updated = await db.invoices.find_one({"id": payment.invoice_id}, {"_id": 0})
    return updated
