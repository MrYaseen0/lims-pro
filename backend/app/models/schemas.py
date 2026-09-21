"""All Pydantic models and enums for the API."""
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, EmailStr


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
