"""
Patient Portal Service for LIMS.Pro
Secure self-service access for patients to view their reports
HIPAA-compliant implementation
"""
import os
import uuid
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

PORTAL_TOKEN_EXPIRY_HOURS = int(os.environ.get('PORTAL_TOKEN_EXPIRY_HOURS', 72))  # 3 days default
OTP_EXPIRY_MINUTES = int(os.environ.get('OTP_EXPIRY_MINUTES', 10))
MAX_OTP_ATTEMPTS = 3


# ==================== MODELS ====================

class PortalAccessType(str, Enum):
    TOKEN_LINK = "token_link"  # Secure link sent via email/SMS
    OTP = "otp"  # One-time password


class PortalSession(BaseModel):
    """Patient portal session"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    access_token: str
    access_type: PortalAccessType
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    last_accessed: Optional[datetime] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True
    access_count: int = 0


class OTPRequest(BaseModel):
    """OTP verification request"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    otp_hash: str  # Hashed OTP for security
    phone: Optional[str] = None
    email: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    attempts: int = 0
    verified: bool = False


class PortalAccessLog(BaseModel):
    """Audit log for portal access - HIPAA compliance"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    session_id: Optional[str] = None
    action: str  # login, view_report, download_pdf, logout
    resource_type: Optional[str] = None  # order, report
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool = True
    error_message: Optional[str] = None


# ==================== PORTAL SERVICE ====================

class PatientPortalService:
    """
    Secure patient portal service with HIPAA-compliant access controls
    """
    
    def __init__(self, db):
        self.db = db
        self.sessions = db.portal_sessions
        self.otp_requests = db.portal_otp_requests
        self.access_logs = db.portal_access_logs
    
    # ==================== TOKEN GENERATION ====================
    
    def _generate_secure_token(self) -> str:
        """Generate a cryptographically secure token"""
        return secrets.token_urlsafe(32)
    
    def _generate_otp(self) -> str:
        """Generate a 6-digit OTP"""
        return ''.join([str(secrets.randbelow(10)) for _ in range(6)])
    
    def _hash_otp(self, otp: str) -> str:
        """Hash OTP for secure storage"""
        return hashlib.sha256(otp.encode()).hexdigest()
    
    # ==================== SESSION MANAGEMENT ====================
    
    async def create_access_link(
        self,
        patient_id: str,
        created_by: str,
        expiry_hours: int = None,
        ip_address: str = None
    ) -> Dict[str, Any]:
        """
        Create a secure access link for a patient.
        Called by staff when releasing a report.
        """
        if expiry_hours is None:
            expiry_hours = PORTAL_TOKEN_EXPIRY_HOURS
        
        # Verify patient exists
        patient = await self.db.patients.find_one({"id": patient_id}, {"_id": 0})
        if not patient:
            raise ValueError("Patient not found")
        
        # Generate secure token
        access_token = self._generate_secure_token()
        
        # Create session
        session = PortalSession(
            patient_id=patient_id,
            access_token=access_token,
            access_type=PortalAccessType.TOKEN_LINK,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
            ip_address=ip_address
        )
        
        session_doc = session.model_dump()
        session_doc["created_at"] = session_doc["created_at"].isoformat()
        session_doc["expires_at"] = session_doc["expires_at"].isoformat()
        
        await self.sessions.insert_one(session_doc)
        
        # Log access link creation
        await self._log_access(
            patient_id=patient_id,
            action="access_link_created",
            ip_address=ip_address,
            details={"created_by": created_by, "expiry_hours": expiry_hours}
        )
        
        logger.info(f"Portal access link created for patient {patient_id}")
        
        return {
            "access_token": access_token,
            "expires_at": session.expires_at.isoformat(),
            "portal_url": f"/patient-portal?token={access_token}"
        }
    
    async def create_otp_request(
        self,
        patient_id: str,
        send_to: str,  # phone or email
        ip_address: str = None
    ) -> Dict[str, Any]:
        """
        Create an OTP request for patient verification.
        Returns OTP (to be sent via SMS/email by caller).
        """
        # Verify patient exists
        patient = await self.db.patients.find_one({"id": patient_id}, {"_id": 0})
        if not patient:
            raise ValueError("Patient not found")
        
        # Check for existing unexpired OTP requests
        existing = await self.otp_requests.find_one({
            "patient_id": patient_id,
            "verified": False,
            "expires_at": {"$gt": datetime.now(timezone.utc).isoformat()}
        })
        
        if existing and existing.get("attempts", 0) >= MAX_OTP_ATTEMPTS:
            raise ValueError("Too many OTP attempts. Please try again later.")
        
        # Generate OTP
        otp = self._generate_otp()
        otp_hash = self._hash_otp(otp)
        
        # Create OTP request
        otp_request = OTPRequest(
            patient_id=patient_id,
            otp_hash=otp_hash,
            phone=send_to if '@' not in send_to else None,
            email=send_to if '@' in send_to else None,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)
        )
        
        doc = otp_request.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["expires_at"] = doc["expires_at"].isoformat()
        
        await self.otp_requests.insert_one(doc)
        
        # Log OTP request
        await self._log_access(
            patient_id=patient_id,
            action="otp_requested",
            ip_address=ip_address,
            details={"send_to": send_to[:3] + "***"}  # Masked for privacy
        )
        
        return {
            "otp": otp,  # Caller should send this via SMS/email
            "otp_request_id": otp_request.id,
            "expires_in_minutes": OTP_EXPIRY_MINUTES
        }
    
    async def verify_otp(
        self,
        otp_request_id: str,
        otp: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Verify OTP and create portal session if valid.
        """
        otp_request = await self.otp_requests.find_one({"id": otp_request_id})
        
        if not otp_request:
            raise ValueError("Invalid OTP request")
        
        # Check expiry
        if datetime.fromisoformat(otp_request["expires_at"]) < datetime.now(timezone.utc):
            raise ValueError("OTP has expired")
        
        # Check attempts
        if otp_request.get("attempts", 0) >= MAX_OTP_ATTEMPTS:
            raise ValueError("Too many failed attempts")
        
        # Verify OTP
        if self._hash_otp(otp) != otp_request["otp_hash"]:
            await self.otp_requests.update_one(
                {"id": otp_request_id},
                {"$inc": {"attempts": 1}}
            )
            await self._log_access(
                patient_id=otp_request["patient_id"],
                action="otp_verification_failed",
                ip_address=ip_address,
                success=False,
                error_message="Invalid OTP"
            )
            raise ValueError("Invalid OTP")
        
        # Mark OTP as verified
        await self.otp_requests.update_one(
            {"id": otp_request_id},
            {"$set": {"verified": True}}
        )
        
        # Create session
        access_token = self._generate_secure_token()
        session = PortalSession(
            patient_id=otp_request["patient_id"],
            access_token=access_token,
            access_type=PortalAccessType.OTP,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=PORTAL_TOKEN_EXPIRY_HOURS),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        session_doc = session.model_dump()
        session_doc["created_at"] = session_doc["created_at"].isoformat()
        session_doc["expires_at"] = session_doc["expires_at"].isoformat()
        
        await self.sessions.insert_one(session_doc)
        
        # Log successful verification
        await self._log_access(
            patient_id=otp_request["patient_id"],
            session_id=session.id,
            action="otp_verified",
            ip_address=ip_address
        )
        
        return {
            "access_token": access_token,
            "expires_at": session.expires_at.isoformat()
        }
    
    async def validate_session(
        self,
        access_token: str,
        ip_address: str = None,
        user_agent: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a portal session token.
        Returns patient info if valid.
        """
        session = await self.sessions.find_one({
            "access_token": access_token,
            "is_active": True
        })
        
        if not session:
            return None
        
        # Check expiry
        if datetime.fromisoformat(session["expires_at"]) < datetime.now(timezone.utc):
            await self.sessions.update_one(
                {"id": session["id"]},
                {"$set": {"is_active": False}}
            )
            return None
        
        # Update last accessed
        await self.sessions.update_one(
            {"id": session["id"]},
            {
                "$set": {"last_accessed": datetime.now(timezone.utc).isoformat()},
                "$inc": {"access_count": 1}
            }
        )
        
        # Get patient info
        patient = await self.db.patients.find_one(
            {"id": session["patient_id"]},
            {"_id": 0, "id": 1, "name": 1, "patient_id": 1, "phone": 1, "email": 1}
        )
        
        return {
            "session_id": session["id"],
            "patient": patient,
            "expires_at": session["expires_at"]
        }
    
    async def revoke_session(self, session_id: str, ip_address: str = None):
        """Revoke a portal session"""
        session = await self.sessions.find_one({"id": session_id})
        if session:
            await self.sessions.update_one(
                {"id": session_id},
                {"$set": {"is_active": False}}
            )
            await self._log_access(
                patient_id=session["patient_id"],
                session_id=session_id,
                action="session_revoked",
                ip_address=ip_address
            )
    
    # ==================== PATIENT DATA ACCESS ====================
    
    async def get_patient_orders(
        self,
        patient_id: str,
        session_id: str,
        ip_address: str = None
    ) -> List[Dict[str, Any]]:
        """
        Get orders for a patient (released reports only).
        """
        # Only show released reports for HIPAA compliance
        orders = await self.db.orders.find(
            {
                "patient_id": patient_id,
                "status": "report_released"
            },
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
        
        # Log access
        await self._log_access(
            patient_id=patient_id,
            session_id=session_id,
            action="view_orders",
            ip_address=ip_address,
            details={"count": len(orders)}
        )
        
        return orders
    
    async def get_order_report(
        self,
        patient_id: str,
        order_id: str,
        session_id: str,
        ip_address: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific order report for a patient.
        """
        order = await self.db.orders.find_one(
            {
                "id": order_id,
                "patient_id": patient_id,
                "status": "report_released"
            },
            {"_id": 0}
        )
        
        if not order:
            await self._log_access(
                patient_id=patient_id,
                session_id=session_id,
                action="view_report",
                resource_type="order",
                resource_id=order_id,
                ip_address=ip_address,
                success=False,
                error_message="Report not found or not released"
            )
            return None
        
        # Get patient info for report
        patient = await self.db.patients.find_one(
            {"id": patient_id},
            {"_id": 0}
        )
        
        # Log access
        await self._log_access(
            patient_id=patient_id,
            session_id=session_id,
            action="view_report",
            resource_type="order",
            resource_id=order_id,
            ip_address=ip_address
        )
        
        return {
            "order": order,
            "patient": patient
        }
    
    async def log_pdf_download(
        self,
        patient_id: str,
        order_id: str,
        session_id: str,
        ip_address: str = None
    ):
        """Log PDF download for HIPAA compliance"""
        await self._log_access(
            patient_id=patient_id,
            session_id=session_id,
            action="download_pdf",
            resource_type="order",
            resource_id=order_id,
            ip_address=ip_address
        )
    
    # ==================== AUDIT LOGGING ====================
    
    async def _log_access(
        self,
        patient_id: str,
        action: str,
        session_id: str = None,
        resource_type: str = None,
        resource_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
        success: bool = True,
        error_message: str = None,
        details: dict = None
    ):
        """Log portal access for HIPAA compliance"""
        log_entry = PortalAccessLog(
            patient_id=patient_id,
            session_id=session_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
        
        doc = log_entry.model_dump()
        doc["timestamp"] = doc["timestamp"].isoformat()
        if details:
            doc["details"] = details
        
        await self.access_logs.insert_one(doc)
    
    async def get_access_logs(
        self,
        patient_id: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get portal access logs (admin only)"""
        query = {}
        
        if patient_id:
            query["patient_id"] = patient_id
        if start_date:
            query["timestamp"] = {"$gte": start_date}
        if end_date:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = end_date
            else:
                query["timestamp"] = {"$lte": end_date}
        
        return await self.access_logs.find(query, {"_id": 0}).sort("timestamp", -1).to_list(limit)


# ==================== HELPER FUNCTIONS ====================

def create_patient_portal_service(db) -> PatientPortalService:
    """Factory function to create portal service"""
    return PatientPortalService(db)
