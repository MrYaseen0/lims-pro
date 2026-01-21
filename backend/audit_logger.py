"""
Audit Logging Service for LIMS.Pro
Tracks all critical actions across the system
"""
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from enum import Enum
import uuid
import logging

logger = logging.getLogger(__name__)

# Action types for audit logging
class AuditAction(str, Enum):
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    
    # Patient actions
    PATIENT_CREATED = "patient_created"
    PATIENT_UPDATED = "patient_updated"
    PATIENT_VIEWED = "patient_viewed"
    
    # Test catalog actions
    TEST_CREATED = "test_created"
    TEST_UPDATED = "test_updated"
    TEST_DISABLED = "test_disabled"
    TEST_ENABLED = "test_enabled"
    
    # Order actions
    ORDER_CREATED = "order_created"
    ORDER_STATUS_CHANGED = "order_status_changed"
    ORDER_VIEWED = "order_viewed"
    
    # Sample actions
    SAMPLE_COLLECTED = "sample_collected"
    SAMPLE_STATUS_CHANGED = "sample_status_changed"
    
    # Result actions
    RESULT_ENTERED = "result_entered"
    RESULT_UPDATED = "result_updated"
    
    # Pathologist actions
    RESULT_APPROVED = "result_approved"
    RESULT_REJECTED = "result_rejected"
    
    # Report actions
    REPORT_RELEASED = "report_released"
    REPORT_PDF_GENERATED = "report_pdf_generated"
    REPORT_DOWNLOADED = "report_downloaded"
    
    # Billing actions
    INVOICE_CREATED = "invoice_created"
    PAYMENT_RECORDED = "payment_recorded"
    
    # User management
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DEACTIVATED = "user_deactivated"
    USER_ACTIVATED = "user_activated"


class AuditLogger:
    """
    Centralized audit logging service
    """
    
    def __init__(self, db):
        self.db = db
        self.collection = db.audit_logs
    
    async def log(
        self,
        action: AuditAction,
        user_id: Optional[str],
        user_email: Optional[str] = None,
        user_role: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        entity_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> str:
        """
        Log an audit event
        
        Args:
            action: The action being performed
            user_id: ID of user performing action
            user_email: Email of user
            user_role: Role of user
            entity_type: Type of entity affected (patient, order, etc.)
            entity_id: ID of entity affected
            entity_name: Human-readable name of entity
            details: Additional details about the action
            ip_address: IP address of request
            success: Whether action was successful
            error_message: Error message if action failed
        
        Returns:
            ID of the audit log entry
        """
        log_entry = {
            "id": str(uuid.uuid4()),
            "action": action.value if isinstance(action, AuditAction) else action,
            "user_id": user_id,
            "user_email": user_email,
            "user_role": user_role,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "entity_name": entity_name,
            "details": details or {},
            "ip_address": ip_address,
            "success": success,
            "error_message": error_message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await self.collection.insert_one(log_entry)
            logger.info(f"Audit log: {action} by {user_email} on {entity_type}:{entity_id}")
        except Exception as e:
            logger.error(f"Failed to write audit log: {str(e)}")
        
        return log_entry["id"]
    
    async def get_logs(
        self,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        skip: int = 0
    ) -> list:
        """
        Query audit logs with filters
        """
        query = {}
        
        if action:
            query["action"] = action
        if user_id:
            query["user_id"] = user_id
        if entity_type:
            query["entity_type"] = entity_type
        if entity_id:
            query["entity_id"] = entity_id
        if start_date:
            query["timestamp"] = {"$gte": start_date}
        if end_date:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = end_date
            else:
                query["timestamp"] = {"$lte": end_date}
        
        cursor = self.collection.find(query, {"_id": 0})
        cursor = cursor.sort("timestamp", -1).skip(skip).limit(limit)
        
        return await cursor.to_list(limit)
    
    async def get_log_count(
        self,
        action: Optional[str] = None,
        user_id: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> int:
        """
        Get count of audit logs matching filters
        """
        query = {}
        if action:
            query["action"] = action
        if user_id:
            query["user_id"] = user_id
        if entity_type:
            query["entity_type"] = entity_type
        
        return await self.collection.count_documents(query)
    
    async def get_user_activity(self, user_id: str, limit: int = 50) -> list:
        """
        Get recent activity for a specific user
        """
        return await self.get_logs(user_id=user_id, limit=limit)
    
    async def get_entity_history(self, entity_type: str, entity_id: str) -> list:
        """
        Get complete history for a specific entity
        """
        return await self.get_logs(entity_type=entity_type, entity_id=entity_id, limit=500)
    
    async def get_summary_stats(self, days: int = 7) -> dict:
        """
        Get summary statistics for audit logs
        """
        from datetime import timedelta
        
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        
        # Get counts by action type
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {"_id": "$action", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        action_counts = {}
        async for doc in self.collection.aggregate(pipeline):
            action_counts[doc["_id"]] = doc["count"]
        
        # Get counts by entity type
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        
        entity_counts = {}
        async for doc in self.collection.aggregate(pipeline):
            if doc["_id"]:
                entity_counts[doc["_id"]] = doc["count"]
        
        # Get active users
        pipeline = [
            {"$match": {"timestamp": {"$gte": start_date}}},
            {"$group": {"_id": "$user_id", "actions": {"$sum": 1}}},
            {"$sort": {"actions": -1}},
            {"$limit": 10}
        ]
        
        active_users = []
        async for doc in self.collection.aggregate(pipeline):
            if doc["_id"]:
                active_users.append({"user_id": doc["_id"], "actions": doc["actions"]})
        
        total_count = await self.collection.count_documents({"timestamp": {"$gte": start_date}})
        
        return {
            "total_actions": total_count,
            "by_action": action_counts,
            "by_entity": entity_counts,
            "active_users": active_users,
            "period_days": days
        }


# Helper function to create audit logger instance
def create_audit_logger(db) -> AuditLogger:
    return AuditLogger(db)
