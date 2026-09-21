from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
import os
import re
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
from enum import Enum
from io import BytesIO

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration — fail fast if the secret is not provided; a hardcoded
# fallback would give every deployment the same signing key.
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    raise RuntimeError(
        "JWT_SECRET environment variable must be set. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.environ.get('JWT_EXPIRATION_HOURS', '24'))

# Auth cookie settings (httpOnly so JS/XSS cannot steal the token)
COOKIE_NAME = "lims_token"
COOKIE_SECURE = os.environ.get('COOKIE_SECURE', 'false').lower() == 'true'

# Reports directory
REPORTS_DIR = ROOT_DIR / 'reports'
REPORTS_DIR.mkdir(exist_ok=True)

# Import audit logger
from audit_logger import AuditLogger, AuditAction, create_audit_logger
audit_logger = create_audit_logger(db)

# Create the main app
async def ensure_indexes():
    """Create MongoDB indexes for the fields we filter/sort on.
    Non-unique on purpose so pre-existing data can never block startup."""
    await db.users.create_index("email")
    await db.patients.create_index("patient_id")
    await db.patients.create_index([("created_at", -1)])
    await db.patients.create_index("phone")
    await db.orders.create_index("patient_id")
    await db.orders.create_index("status")
    await db.orders.create_index([("created_at", -1)])
    await db.tests.create_index("code")
    await db.samples.create_index("order_id")
    await db.invoices.create_index("order_id")
    await db.doctors.create_index("name")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    logger.info("MongoDB indexes ensured")
    yield

app = FastAPI(title="Laboratory Information System API", lifespan=lifespan)
api_router = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

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
    father_name: Optional[str] = None
    referred_by: Optional[str] = None

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

async def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    # Prefer the httpOnly cookie; fall back to the Authorization header
    # for API clients / backward compatibility.
    token = credentials.credentials if credentials else request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*allowed_roles: str):
    """Reusable role guard, e.g. Depends(require_role("admin", "lab_manager"))."""
    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Not authorized")
        return current_user
    return role_checker

# --- Login rate limiting (in-memory sliding window, per process) ---
_login_attempts: Dict[str, List[datetime]] = {}
LOGIN_RATE_LIMIT = 10          # max attempts
LOGIN_RATE_WINDOW_SECONDS = 60 # per this many seconds

def check_login_rate_limit(ip: str):
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=LOGIN_RATE_WINDOW_SECONDS)
    attempts = [t for t in _login_attempts.get(ip, []) if t > window_start]
    if len(attempts) >= LOGIN_RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Please try again in a minute.",
        )
    attempts.append(now)
    _login_attempts[ip] = attempts

# --- Pagination helper ---
MAX_PAGE_SIZE = 200

def paginate(page: int = 1, page_size: int = 20):
    page = max(1, page)
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    return (page - 1) * page_size, page_size

# --- Automatic H/L flagging against reference ranges ---
_RANGE_RE = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*[-–]\s*([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*$")

def parse_range_bounds(normal_range: str):
    """Parse '12 - 17' -> (12.0, 17.0). Returns None if not parseable."""
    m = _RANGE_RE.match(normal_range or "")
    if not m:
        return None
    try:
        return float(m.group(1)), float(m.group(2))
    except ValueError:
        return None

def to_float(value) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return None

def compute_result_flags(test_doc: Optional[dict], values: Dict[str, Any]):
    """Compare entered values against the test's reference ranges.

    Returns (flags, auto_abnormal) where flags maps parameter name ->
    'H' | 'L' | 'N'. Handles per-parameter values keyed by parameter name,
    plus the legacy single {"value": ...} shape for single-range tests.
    """
    flags: Dict[str, str] = {}
    ranges = (test_doc or {}).get("reference_ranges") or []
    if not ranges:
        return flags, False
    norm_values = {str(k).strip().lower(): v for k, v in (values or {}).items()}
    for r in ranges:
        param = str(r.get("parameter", "")).strip()
        bounds = parse_range_bounds(str(r.get("normal_range", "")))
        if not param or not bounds:
            continue
        low, high = bounds
        raw = norm_values.get(param.lower())
        if raw is None and len(ranges) == 1:
            raw = (values or {}).get("value")
        num = to_float(raw)
        if num is None:
            continue
        if num < low:
            flags[param] = "L"
        elif num > high:
            flags[param] = "H"
        else:
            flags[param] = "N"
    auto_abnormal = any(f in ("H", "L") for f in flags.values())
    return flags, auto_abnormal

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

@api_router.post("/auth/login", response_model=TokenResponse)
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

@api_router.post("/auth/logout", response_model=dict)
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me", response_model=dict)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ==================== USER ROUTES ====================
@api_router.get("/users", response_model=List[dict])
async def get_users(response: Response, page: int = 1, page_size: int = 20, current_user: dict = Depends(require_role("admin", "lab_manager"))):
    skip, limit = paginate(page, page_size)
    total = await db.users.count_documents({})
    users = await db.users.find({}, {"_id": 0, "password": 0}).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
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

# ==================== CLINICAL LAB CUSTOMIZATIONS ====================
# Yearly patient serial numbers: 0001-09-2026 (counter-month-year).
# The counter restarts at 1 every calendar year.
async def next_patient_serial() -> str:
    now = datetime.now()
    year = now.year
    result = await db.counters.find_one_and_update(
        {"_id": f"patient_serial_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"{result['seq']:04d}-{now.month:02d}-{year}"

SEED_DOCTORS = ["Dr. Ahmed Khan", "Dr. Sara Malik", "Dr. Bilal Hussain"]

async def ensure_doctors_seeded():
    """Seed the referring-doctors list once (never duplicates)."""
    if await db.doctors.count_documents({}) == 0:
        await db.doctors.insert_many([
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            for name in SEED_DOCTORS
        ])

# Reference ranges keyed by test code. Each entry is a list of
# {"parameter", "unit", "normal_range"} dicts.
REFERENCE_RANGES = {
    "CBC": [
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "12 - 17"},
        {"parameter": "TLC (WBC)", "unit": "/uL", "normal_range": "4000 - 11000"},
        {"parameter": "RBC Count", "unit": "million/uL", "normal_range": "4.5 - 5.5"},
        {"parameter": "Platelet Count", "unit": "/uL", "normal_range": "150000 - 400000"},
        {"parameter": "PCV", "unit": "%", "normal_range": "36 - 46"},
        {"parameter": "MCV", "unit": "fL", "normal_range": "80 - 100"},
        {"parameter": "MCH", "unit": "pg", "normal_range": "27 - 32"},
        {"parameter": "MCHC", "unit": "g/dL", "normal_range": "32 - 36"},
        {"parameter": "Neutrophils", "unit": "%", "normal_range": "40 - 75"},
        {"parameter": "Lymphocytes", "unit": "%", "normal_range": "20 - 40"},
        {"parameter": "Monocytes", "unit": "%", "normal_range": "2 - 8"},
        {"parameter": "Eosinophils", "unit": "%", "normal_range": "1 - 6"},
        {"parameter": "Basophils", "unit": "%", "normal_range": "0 - 1"},
        {"parameter": "ESR", "unit": "mm/hr", "normal_range": "0 - 20"},
    ],
    "RFT": [
        {"parameter": "Urea", "unit": "mg/dL", "normal_range": "15 - 40"},
        {"parameter": "Creatinine", "unit": "mg/dL", "normal_range": "0.6 - 1.2"},
        {"parameter": "Uric Acid", "unit": "mg/dL", "normal_range": "3.0 - 7.0"},
        {"parameter": "Sodium (Na+)", "unit": "mEq/L", "normal_range": "135 - 145"},
        {"parameter": "Potassium (K+)", "unit": "mEq/L", "normal_range": "3.5 - 5.5"},
        {"parameter": "Chloride (Cl-)", "unit": "mEq/L", "normal_range": "98 - 107"},
        {"parameter": "Calcium", "unit": "mg/dL", "normal_range": "8.5 - 10.5"},
        {"parameter": "Phosphorus", "unit": "mg/dL", "normal_range": "2.5 - 4.5"},
    ],
    "LFT": [
        {"parameter": "Total Bilirubin", "unit": "mg/dL", "normal_range": "0.3 - 1.2"},
        {"parameter": "Direct Bilirubin", "unit": "mg/dL", "normal_range": "0.0 - 0.3"},
        {"parameter": "Indirect Bilirubin", "unit": "mg/dL", "normal_range": "0.2 - 0.8"},
        {"parameter": "SGPT (ALT)", "unit": "U/L", "normal_range": "7 - 56"},
        {"parameter": "SGOT (AST)", "unit": "U/L", "normal_range": "10 - 40"},
        {"parameter": "Alkaline Phosphatase", "unit": "U/L", "normal_range": "44 - 147"},
        {"parameter": "Total Protein", "unit": "g/dL", "normal_range": "6.0 - 8.3"},
        {"parameter": "Albumin", "unit": "g/dL", "normal_range": "3.5 - 5.5"},
        {"parameter": "Globulin", "unit": "g/dL", "normal_range": "2.0 - 3.5"},
        {"parameter": "A/G Ratio", "unit": "-", "normal_range": "1.0 - 2.5"},
    ],
}

SEED_TESTS = [
    {"name": "Complete Blood Count", "code": "CBC", "category": "Hematology", "sample_type": "blood", "price": 25.0, "turn_around_time": 4},
    {"name": "Renal Function Test", "code": "RFT", "category": "Biochemistry", "sample_type": "blood", "price": 40.0, "turn_around_time": 6},
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

async def ensure_test_reference_ranges():
    """Backfill reference ranges for CBC/RFT/LFT on databases seeded before this change.
    Also inserts the RFT test itself if it does not exist yet."""
    for t in SEED_TESTS:
        code = t["code"]
        ranges = REFERENCE_RANGES.get(code, [])
        if not ranges:
            continue
        existing = await db.tests.find_one({"code": code})
        if not existing:
            test_doc = {
                "id": str(uuid.uuid4()),
                **t,
                "description": f"Standard {t['name']} test",
                "reference_ranges": ranges,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.tests.insert_one(test_doc)
        elif not existing.get("reference_ranges"):
            await db.tests.update_one({"code": code}, {"$set": {"reference_ranges": ranges}})

# ==================== PATIENT ROUTES ====================
@api_router.post("/patients", response_model=dict)
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

@api_router.get("/patients", response_model=List[dict])
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

@api_router.get("/doctors", response_model=List[dict])
async def get_doctors(response: Response, page: int = 1, page_size: int = 100, current_user: dict = Depends(get_current_user)):
    skip, limit = paginate(page, page_size)
    total = await db.doctors.count_documents({})
    doctors = await db.doctors.find({}, {"_id": 0}).sort("name", 1).skip(skip).limit(limit).to_list(limit)
    response.headers["X-Total-Count"] = str(total)
    return doctors

# ==================== TEST CATALOG ROUTES ====================
@api_router.post("/tests", response_model=dict)
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

@api_router.get("/tests", response_model=List[dict])
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

@api_router.get("/tests/{test_id}", response_model=dict)
async def get_test(test_id: str, current_user: dict = Depends(get_current_user)):
    test = await db.tests.find_one({"id": test_id}, {"_id": 0})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

@api_router.put("/tests/{test_id}", response_model=dict)
async def update_test(test_id: str, updates: dict, current_user: dict = Depends(require_role("admin", "lab_manager"))):
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
    
    updated = await db.orders.find_one({"id": result.order_id}, {"_id": 0})
    return updated

@api_router.get("/technician/queue", response_model=List[dict])
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

# ==================== PATHOLOGIST ROUTES ====================
@api_router.post("/approve", response_model=dict)
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

@api_router.get("/pathologist/queue", response_model=List[dict])
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

# ==================== REPORT ROUTES ====================
@api_router.post("/reports/{order_id}/release", response_model=dict)
async def release_report(order_id: str, current_user: dict = Depends(require_role("pathologist", "lab_manager", "admin"))):
    
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

# ==================== PDF REPORT GENERATION (ADDITIVE) ====================
@api_router.post("/reports/{order_id}/generate-pdf", response_model=dict)
async def generate_pdf_report(order_id: str, current_user: dict = Depends(get_current_user)):
    """Generate a PDF report for an order (order must be approved or released)"""
    from pdf_generator import generate_report_pdf, save_report_pdf
    
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Only allow PDF generation for approved or released orders
    if order["status"] not in [OrderStatus.APPROVED, OrderStatus.REPORT_RELEASED]:
        raise HTTPException(status_code=400, detail="PDF can only be generated for approved or released orders")
    
    # Get patient info
    patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get samples for the order
    samples = await db.samples.find({"order_id": order_id}, {"_id": 0}).to_list(10)
    order["samples"] = samples
    
    # Get pathologist name if available
    pathologist_name = None
    for test in order.get("tests", []):
        result = test.get("result", {})
        if result.get("approved_by"):
            pathologist = await db.users.find_one({"id": result["approved_by"]}, {"_id": 0, "name": 1})
            if pathologist:
                pathologist_name = pathologist.get("name")
                break
    
    # Lab info
    lab_info = {
        'name': 'LIMS.Pro Diagnostic Laboratory',
        'address': '123 Medical Center, Healthcare City',
        'phone': '+1-234-567-8900',
        'email': 'info@lims.pro'
    }
    
    try:
        # Generate PDF
        pdf_buffer = generate_report_pdf(order, patient, pathologist_name, lab_info)
        
        # Save PDF to file
        filename = save_report_pdf(pdf_buffer, order["order_id"], str(REPORTS_DIR))
        
        # Store PDF reference in order
        pdf_url = f"/api/reports/{order_id}/download/{filename}"
        await db.orders.update_one(
            {"id": order_id},
            {"$set": {
                "pdf_filename": filename,
                "pdf_generated_at": datetime.now(timezone.utc).isoformat(),
                "pdf_generated_by": current_user["id"]
            }}
        )
        
        logger.info(f"PDF generated for order {order_id}: {filename}")
        
        return {
            "message": "PDF generated successfully",
            "filename": filename,
            "download_url": pdf_url,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"PDF generation failed for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")


@api_router.get("/reports/{order_id}/download/{filename}")
async def download_pdf_report(order_id: str, filename: str, current_user: dict = Depends(get_current_user)):
    """Download a generated PDF report"""
    # Verify order exists and user has access
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    # Verify filename matches order's PDF
    if order.get("pdf_filename") != filename:
        raise HTTPException(status_code=404, detail="PDF not found for this order")
    
    filepath = REPORTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    
    return FileResponse(
        path=str(filepath),
        media_type="application/pdf",
        filename=f"LabReport_{order.get('order_id', order_id)}.pdf",
        headers={"Content-Disposition": f"attachment; filename=LabReport_{order.get('order_id', order_id)}.pdf"}
    )


@api_router.get("/reports/{order_id}/pdf-stream")
async def stream_pdf_report(order_id: str, current_user: dict = Depends(get_current_user)):
    """Generate and stream PDF without saving (for preview)"""
    from pdf_generator import generate_report_pdf
    
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order["status"] not in [OrderStatus.APPROVED, OrderStatus.REPORT_RELEASED]:
        raise HTTPException(status_code=400, detail="PDF can only be generated for approved or released orders")
    
    patient = await db.patients.find_one({"id": order["patient_id"]}, {"_id": 0})
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Get samples
    samples = await db.samples.find({"order_id": order_id}, {"_id": 0}).to_list(10)
    order["samples"] = samples
    
    # Get pathologist name
    pathologist_name = None
    for test in order.get("tests", []):
        result = test.get("result", {})
        if result.get("approved_by"):
            pathologist = await db.users.find_one({"id": result["approved_by"]}, {"_id": 0, "name": 1})
            if pathologist:
                pathologist_name = pathologist.get("name")
                break
    
    lab_info = {
        'name': 'LIMS.Pro Diagnostic Laboratory',
        'address': '123 Medical Center, Healthcare City',
        'phone': '+1-234-567-8900',
        'email': 'info@lims.pro'
    }
    
    try:
        pdf_buffer = generate_report_pdf(order, patient, pathologist_name, lab_info)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=LabReport_{order.get('order_id', order_id)}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"PDF streaming failed for order {order_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

# ==================== BILLING ROUTES ====================
@api_router.get("/invoices", response_model=List[dict])
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
@api_router.get("/")
async def root():
    return {"message": "Laboratory Information System API", "version": "1.0.0"}

# Include the router
app.include_router(api_router)

# CORS: when credentials (httpOnly auth cookie) are used, browsers reject
# `Access-Control-Allow-Origin: *`, so a wildcard is expressed as an origin
# regex (which echoes the request origin) instead of a literal "*".
_cors_origins = os.environ.get('CORS_ORIGINS', '*').strip()
if _cors_origins == '*':
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in _cors_origins.split(',')],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
