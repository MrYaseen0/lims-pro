"""Patient and referring-doctor routes."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from audit_logger import AuditAction
from app.core.database import db, audit_logger
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.models.schemas import Patient, PatientCreate
from app.services.seed_data import next_patient_serial


router = APIRouter()


@router.post("/patients", response_model=dict)
async def create_patient(patient: PatientCreate, current_user: dict = Depends(get_current_user)):
    patient_obj = Patient(**patient.model_dump())
    # Yearly serial number: 0001-09-2026 (counter-month-year)
    patient_obj.patient_id = await next_patient_serial()
    patient_obj.created_by = current_user["id"]
    doc = patient_obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.patients.insert_one(doc)
    doc.pop("_id", None)
    
    # Audit log: Patient created
    await audit_logger.log(
        action=AuditAction.PATIENT_CREATED,
        user_id=current_user["id"],
        user_email=current_user["email"],
        user_role=current_user["role"],
        entity_type="patient",
        entity_id=doc["id"],
        entity_name=doc["name"],
        details={"patient_id": doc["patient_id"]}
    )
    
    return doc

@router.get("/patients", response_model=List[dict])
async def get_patients(response: Response, search: Optional[str] = None, page: int = 1, page_size: int = 20, current_user: dict = Depends(get_current_user)):
    query = {}
    if search:
        query = {"$or": [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"patient_id": {"$regex": search, "$options": "i"}}
        ]}
    skip, limit = paginate(page, page_size)
    total = await db.patients.count_documents(query)
    patients = await db.patients.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return patients

@router.get("/patients/{patient_id}", response_model=dict)
async def get_patient(patient_id: str, current_user: dict = Depends(get_current_user)):
    patient = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    # Get patient orders
    orders = await db.orders.find({"patient_id": patient_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    patient["orders"] = orders
    return patient

@router.put("/patients/{patient_id}", response_model=dict)
async def update_patient(patient_id: str, updates: dict, current_user: dict = Depends(get_current_user)):
    result = await db.patients.update_one({"id": patient_id}, {"$set": updates})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    updated = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    return updated

@router.get("/doctors", response_model=List[dict])
async def get_doctors(response: Response, page: int = 1, page_size: int = 100, current_user: dict = Depends(get_current_user)):
    skip, limit = paginate(page, page_size)
    total = await db.doctors.count_documents({})
    doctors = await db.doctors.find({}, {"_id": 0}).sort("name", 1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return doctors
