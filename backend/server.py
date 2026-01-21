from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from enum import Enum

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'lis-secret-key-change-in-production')
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Create the main app
app = FastAPI(title="Laboratory Information System API")
api_router = APIRouter(prefix="/api")
security = HTTPBearer()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== ENUMS ====================
class UserRole(str, Enum):
    ADMIN = "admin"
    LAB_MANAGER = "lab_manager"
    TECHNICIAN = "technician"
    PATHOLOGIST = "pathologist"
    RECEPTIONIST = "receptionist"
    DOCTOR = "doctor"
    COLLECTION_STAFF = "collection_staff"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class OrderStatus(str, Enum):
    REGISTERED = "registered"
    SAMPLE_COLLECTED = "sample_collected"
    IN_LAB = "in_lab"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REPORT_RELEASED = "report_released"

class SampleStatus(str, Enum):
    PENDING = "pending"
    COLLECTED = "collected"
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    REJECTED = "rejected"

class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    REFUNDED = "refunded"

class PaymentMode(str, Enum):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    INSURANCE = "insurance"
    ONLINE = "online"

# ==================== MODELS ====================
class UserBase(BaseModel):
    email: EmailStr
    name: str
    role: UserRole
    phone: Optional[str] = None
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class PatientBase(BaseModel):
    name: str
    age: int
    gender: Gender
    phone: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class Patient(PatientBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str = Field(default_factory=lambda: f"PAT{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None

class TestBase(BaseModel):
    name: str
    code: str
    category: str
    sample_type: str
    price: float
    turn_around_time: int  # in hours
    description: Optional[str] = None
    reference_ranges: Optional[List[Dict[str, Any]]] = []
    is_active: bool = True

class TestCreate(TestBase):
    pass

class Test(TestBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OrderTestItem(BaseModel):
    test_id: str
    test_name: str
    test_code: str
    price: float
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"

class OrderBase(BaseModel):
    patient_id: str
    tests: List[OrderTestItem]
    priority: str = "normal"  # normal, urgent, stat
    referring_doctor: Optional[str] = None
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str = Field(default_factory=lambda: f"ORD{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}")
    status: OrderStatus = OrderStatus.REGISTERED
    total_amount: float = 0.0
    discount: float = 0.0
    net_amount: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    patient_name: Optional[str] = None
    status_history: List[Dict[str, Any]] = []

class SampleBase(BaseModel):
    order_id: str
    sample_type: str
    collector_id: Optional[str] = None

class SampleCreate(SampleBase):
    pass

class Sample(SampleBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sample_id: str = Field(default_factory=lambda: f"SMP{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}")
    barcode: str = Field(default_factory=lambda: str(uuid.uuid4())[:12].upper())
    status: SampleStatus = SampleStatus.PENDING
    collection_time: Optional[datetime] = None
    received_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ResultEntry(BaseModel):
    order_id: str
    test_id: str
    values: Dict[str, Any]
    is_abnormal: bool = False
    technician_notes: Optional[str] = None

class ResultApproval(BaseModel):
    order_id: str
    test_id: str
    approved: bool
    pathologist_notes: Optional[str] = None

class InvoiceBase(BaseModel):
    order_id: str
    patient_id: str
    amount: float
    discount: float = 0.0
    net_amount: float

class Invoice(InvoiceBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    invoice_id: str = Field(default_factory=lambda: f"INV{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:6].upper()}")
    payment_status: PaymentStatus = PaymentStatus.PENDING
    payments: List[Dict[str, Any]] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PaymentCreate(BaseModel):
    invoice_id: str
    amount: float
    payment_mode: PaymentMode
    reference: Optional[str] = None

# ==================== HELPER FUNCTIONS ====================
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_data: dict) -> str:
    payload = {
        "sub": user_data["id"],
        "email": user_data["email"],
        "role": user_data["role"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        token = credentials.credentials
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj

# ==================== AUTH ROUTES ====================
@api_router.post("/auth/register", response_model=dict)
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
    return {"message": "User registered successfully", "user": user_dict}

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account is deactivated")
    
    token = create_token({"id": user["id"], "email": user["email"], "role": user["role"]})
    user_response = {k: v for k, v in user.items() if k not in ["_id", "password"]}
    return TokenResponse(access_token=token, user=user_response)

@api_router.get("/auth/me", response_model=dict)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ==================== USER ROUTES ====================
@api_router.get("/users", response_model=List[dict])
async def get_users(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "lab_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    users = await db.users.find({}, {"_id": 0, "password": 0}).to_list(1000)
    return users

@api_router.put("/users/{user_id}", response_model=dict)
async def update_user(user_id: str, updates: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if "password" in updates:
        updates["password"] = hash_password(updates["password"])
    
    result = await db.users.update_one({"id": user_id}, {"$set": updates})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    updated = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    return updated

# ==================== PATIENT ROUTES ====================
@api_router.post("/patients", response_model=dict)
async def create_patient(patient: PatientCreate, current_user: dict = Depends(get_current_user)):
    patient_obj = Patient(**patient.model_dump())
    patient_obj.created_by = current_user["id"]
    doc = patient_obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.patients.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.get("/patients", response_model=List[dict])
async def get_patients(search: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if search:
        query = {"$or": [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"patient_id": {"$regex": search, "$options": "i"}}
        ]}
    patients = await db.patients.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return patients

@api_router.get("/patients/{patient_id}", response_model=dict)
async def get_patient(patient_id: str, current_user: dict = Depends(get_current_user)):
    patient = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    # Get patient orders
    orders = await db.orders.find({"patient_id": patient_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    patient["orders"] = orders
    return patient

@api_router.put("/patients/{patient_id}", response_model=dict)
async def update_patient(patient_id: str, updates: dict, current_user: dict = Depends(get_current_user)):
    result = await db.patients.update_one({"id": patient_id}, {"$set": updates})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Patient not found")
    updated = await db.patients.find_one({"id": patient_id}, {"_id": 0})
    return updated

# ==================== TEST CATALOG ROUTES ====================
@api_router.post("/tests", response_model=dict)
async def create_test(test: TestCreate, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in [UserRole.ADMIN, UserRole.LAB_MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    existing = await db.tests.find_one({"code": test.code})
    if existing:
        raise HTTPException(status_code=400, detail="Test code already exists")
    
    test_obj = Test(**test.model_dump())
    doc = test_obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.tests.insert_one(doc)
    doc.pop("_id", None)
    return doc

@api_router.get("/tests", response_model=List[dict])
async def get_tests(category: Optional[str] = None, active_only: bool = True, current_user: dict = Depends(get_current_user)):
    query = {}
    if category:
        query["category"] = category
    if active_only:
        query["is_active"] = True
    tests = await db.tests.find(query, {"_id": 0}).sort("name", 1).to_list(1000)
    return tests

@api_router.get("/tests/{test_id}", response_model=dict)
async def get_test(test_id: str, current_user: dict = Depends(get_current_user)):
    test = await db.tests.find_one({"id": test_id}, {"_id": 0})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

@api_router.put("/tests/{test_id}", response_model=dict)
async def update_test(test_id: str, updates: dict, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in [UserRole.ADMIN, UserRole.LAB_MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    result = await db.tests.update_one({"id": test_id}, {"$set": updates})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Test not found")
    updated = await db.tests.find_one({"id": test_id}, {"_id": 0})
    return updated

@api_router.get("/test-categories", response_model=List[str])
async def get_test_categories(current_user: dict = Depends(get_current_user)):
    categories = await db.tests.distinct("category")
    return categories

# ==================== ORDER ROUTES ====================
@api_router.post("/orders", response_model=dict)
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

@api_router.get("/orders", response_model=List[dict])
async def get_orders(
    status: Optional[str] = None, 
    patient_id: Optional[str] = None,
    priority: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    query = {}
    if status:
        query["status"] = status
    if patient_id:
        query["patient_id"] = patient_id
    if priority:
        query["priority"] = priority
    
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return orders

@api_router.get("/orders/{order_id}", response_model=dict)
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

@api_router.put("/orders/{order_id}/status", response_model=dict)
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

# ==================== SAMPLE ROUTES ====================
@api_router.post("/samples", response_model=dict)
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

@api_router.get("/samples", response_model=List[dict])
async def get_samples(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["status"] = status
    samples = await db.samples.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    # Enrich with order info
    for sample in samples:
        order = await db.orders.find_one({"id": sample["order_id"]}, {"_id": 0, "patient_name": 1, "order_id": 1})
        if order:
            sample["patient_name"] = order.get("patient_name")
            sample["order_number"] = order.get("order_id")
    
    return samples

@api_router.put("/samples/{sample_id}/status", response_model=dict)
async def update_sample_status(sample_id: str, status: SampleStatus, current_user: dict = Depends(get_current_user)):
    result = await db.samples.update_one(
        {"id": sample_id},
        {"$set": {"status": status, "received_time": datetime.now(timezone.utc).isoformat() if status == SampleStatus.RECEIVED else None}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Sample not found")
    
    updated = await db.samples.find_one({"id": sample_id}, {"_id": 0})
    return updated

# ==================== RESULT ROUTES ====================
@api_router.post("/results", response_model=dict)
async def enter_result(result: ResultEntry, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in [UserRole.TECHNICIAN, UserRole.LAB_MANAGER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    order = await db.orders.find_one({"id": result.order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Update the specific test result in the order
    tests = order.get("tests", [])
    for i, test in enumerate(tests):
        if test["test_id"] == result.test_id:
            tests[i]["result"] = {
                "values": result.values,
                "is_abnormal": result.is_abnormal,
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
    
    updated = await db.orders.find_one({"id": result.order_id}, {"_id": 0})
    return updated

@api_router.get("/technician/queue", response_model=List[dict])
async def get_technician_queue(current_user: dict = Depends(get_current_user)):
    # Get orders that have samples collected but results not entered
    orders = await db.orders.find(
        {"status": {"$in": [OrderStatus.SAMPLE_COLLECTED, OrderStatus.IN_LAB]}},
        {"_id": 0}
    ).sort("priority", -1).to_list(1000)
    
    # Enrich with sample info
    for order in orders:
        samples = await db.samples.find({"order_id": order["id"]}, {"_id": 0}).to_list(10)
        order["samples"] = samples
        
        # Get patient info
        patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0, "name": 1, "age": 1, "gender": 1})
        if patient:
            order["patient"] = patient
    
    return orders

# ==================== PATHOLOGIST ROUTES ====================
@api_router.post("/approve", response_model=dict)
async def approve_result(approval: ResultApproval, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in [UserRole.PATHOLOGIST, UserRole.LAB_MANAGER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
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

@api_router.get("/pathologist/queue", response_model=List[dict])
async def get_pathologist_queue(current_user: dict = Depends(get_current_user)):
    orders = await db.orders.find(
        {"status": OrderStatus.UNDER_REVIEW},
        {"_id": 0}
    ).sort("created_at", 1).to_list(1000)
    
    for order in orders:
        patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0, "name": 1, "age": 1, "gender": 1})
        if patient:
            order["patient"] = patient
    
    return orders

# ==================== REPORT ROUTES ====================
@api_router.post("/reports/{order_id}/release", response_model=dict)
async def release_report(order_id: str, current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in [UserRole.PATHOLOGIST, UserRole.LAB_MANAGER, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] != OrderStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Order must be approved before releasing report")
    
    await db.orders.update_one(
        {"id": order_id},
        {
            "$set": {
                "status": OrderStatus.REPORT_RELEASED,
                "report_released_at": datetime.now(timezone.utc).isoformat(),
                "report_released_by": current_user["id"]
            },
            "$push": {"status_history": {
                "status": OrderStatus.REPORT_RELEASED,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "by": current_user["id"]
            }}
        }
    )
    
    updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return updated

@api_router.get("/reports/{order_id}", response_model=dict)
async def get_report(order_id: str, current_user: dict = Depends(get_current_user)):
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0})
    
    return {
        "order": order,
        "patient": patient,
        "lab_name": "LIMS.Pro Diagnostic Laboratory",
        "lab_address": "123 Medical Center, Healthcare City",
        "lab_phone": "+1-234-567-8900",
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

# ==================== BILLING ROUTES ====================
@api_router.get("/invoices", response_model=List[dict])
async def get_invoices(status: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    query = {}
    if status:
        query["payment_status"] = status
    invoices = await db.invoices.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    for invoice in invoices:
        patient = await db.patients.find_one({"id": invoice["patient_id"]}, {"_id": 0, "name": 1, "phone": 1})
        if patient:
            invoice["patient_name"] = patient.get("name")
            invoice["patient_phone"] = patient.get("phone")
    
    return invoices

@api_router.get("/invoices/{invoice_id}", response_model=dict)
async def get_invoice(invoice_id: str, current_user: dict = Depends(get_current_user)):
    invoice = await db.invoices.find_one({"id": invoice_id}, {"_id": 0})
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    patient = await db.patients.find_one({"id": invoice["patient_id"]}, {"_id": 0})
    order = await db.orders.find_one({"id": invoice["order_id"]}, {"_id": 0})
    
    invoice["patient"] = patient
    invoice["order"] = order
    return invoice

@api_router.post("/payments", response_model=dict)
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

# ==================== ANALYTICS ROUTES ====================
@api_router.get("/analytics/dashboard", response_model=dict)
async def get_dashboard_analytics(current_user: dict = Depends(get_current_user)):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Today's stats
    today_orders = await db.orders.count_documents({"created_at": {"$gte": today.isoformat()}})
    today_patients = await db.patients.count_documents({"created_at": {"$gte": today.isoformat()}})
    
    # Revenue stats
    invoices_today = await db.invoices.find({"created_at": {"$gte": today.isoformat()}}, {"_id": 0, "net_amount": 1}).to_list(1000)
    today_revenue = sum(inv.get("net_amount", 0) for inv in invoices_today)
    
    invoices_month = await db.invoices.find({"created_at": {"$gte": month_ago.isoformat()}}, {"_id": 0, "net_amount": 1}).to_list(10000)
    month_revenue = sum(inv.get("net_amount", 0) for inv in invoices_month)
    
    # Pending work
    pending_samples = await db.orders.count_documents({"status": OrderStatus.REGISTERED})
    pending_results = await db.orders.count_documents({"status": {"$in": [OrderStatus.SAMPLE_COLLECTED, OrderStatus.IN_LAB]}})
    pending_approval = await db.orders.count_documents({"status": OrderStatus.UNDER_REVIEW})
    
    # Test volume by category
    test_volumes = []
    categories = await db.tests.distinct("category")
    for cat in categories:
        tests_in_cat = await db.tests.find({"category": cat}, {"_id": 0, "id": 1}).to_list(100)
        test_ids = [t["id"] for t in tests_in_cat]
        count = 0
        orders = await db.orders.find({}, {"_id": 0, "tests": 1}).to_list(10000)
        for order in orders:
            for test in order.get("tests", []):
                if test.get("test_id") in test_ids:
                    count += 1
        test_volumes.append({"category": cat, "count": count})
    
    # Daily revenue for chart (last 7 days)
    daily_revenue = []
    for i in range(7):
        day = today - timedelta(days=i)
        next_day = day + timedelta(days=1)
        day_invoices = await db.invoices.find({
            "created_at": {"$gte": day.isoformat(), "$lt": next_day.isoformat()}
        }, {"_id": 0, "net_amount": 1}).to_list(1000)
        daily_revenue.append({
            "date": day.strftime("%Y-%m-%d"),
            "revenue": sum(inv.get("net_amount", 0) for inv in day_invoices)
        })
    
    return {
        "today_orders": today_orders,
        "today_patients": today_patients,
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "pending_samples": pending_samples,
        "pending_results": pending_results,
        "pending_approval": pending_approval,
        "test_volumes": test_volumes,
        "daily_revenue": list(reversed(daily_revenue)),
        "total_patients": await db.patients.count_documents({}),
        "total_tests": await db.tests.count_documents({"is_active": True})
    }

# ==================== SEED DATA ====================
@api_router.post("/seed", response_model=dict)
async def seed_data():
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
    
    # Create sample tests
    tests = [
        {"name": "Complete Blood Count", "code": "CBC", "category": "Hematology", "sample_type": "blood", "price": 25.0, "turn_around_time": 4},
        {"name": "Blood Glucose Fasting", "code": "BGF", "category": "Biochemistry", "sample_type": "blood", "price": 15.0, "turn_around_time": 2},
        {"name": "Lipid Profile", "code": "LIPID", "category": "Biochemistry", "sample_type": "blood", "price": 45.0, "turn_around_time": 6},
        {"name": "Liver Function Test", "code": "LFT", "category": "Biochemistry", "sample_type": "blood", "price": 50.0, "turn_around_time": 6},
        {"name": "Kidney Function Test", "code": "KFT", "category": "Biochemistry", "sample_type": "blood", "price": 40.0, "turn_around_time": 6},
        {"name": "Thyroid Profile", "code": "THYROID", "category": "Endocrinology", "sample_type": "blood", "price": 60.0, "turn_around_time": 8},
        {"name": "Urine Routine", "code": "URINE", "category": "Clinical Pathology", "sample_type": "urine", "price": 10.0, "turn_around_time": 2},
        {"name": "HbA1c", "code": "HBA1C", "category": "Biochemistry", "sample_type": "blood", "price": 35.0, "turn_around_time": 4},
        {"name": "Vitamin D", "code": "VITD", "category": "Biochemistry", "sample_type": "blood", "price": 55.0, "turn_around_time": 24},
        {"name": "Vitamin B12", "code": "VITB12", "category": "Biochemistry", "sample_type": "blood", "price": 50.0, "turn_around_time": 24},
    ]
    for t in tests:
        test_doc = {
            "id": str(uuid.uuid4()),
            **t,
            "description": f"Standard {t['name']} test",
            "reference_ranges": [],
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.tests.insert_one(test_doc)
    
    return {"message": "Seed data created successfully", "admin_email": "admin@lims.pro", "admin_password": "admin123"}

# Root endpoint
@api_router.get("/")
async def root():
    return {"message": "Laboratory Information System API", "version": "1.0.0"}

# Include the router
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
