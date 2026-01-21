"""
Multi-Location Support for LIMS.Pro
Manages Central Lab and Collection Centers
"""
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum
import uuid


class LocationType(str, Enum):
    CENTRAL_LAB = "central_lab"
    COLLECTION_CENTER = "collection_center"
    SATELLITE_LAB = "satellite_lab"


class LocationStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"


class SampleRouteStatus(str, Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    PROCESSING = "processing"


# ==================== MODELS ====================

class LocationBase(BaseModel):
    """Base location model"""
    name: str
    code: str  # Short unique code like "CL01", "CC01"
    location_type: LocationType
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    parent_location_id: Optional[str] = None  # For collection centers linked to central lab
    operating_hours: Optional[str] = None
    services: List[str] = []  # List of test categories available
    is_sample_collection_point: bool = True
    can_process_samples: bool = False  # Only central/satellite labs
    status: LocationStatus = LocationStatus.ACTIVE


class LocationCreate(LocationBase):
    pass


class Location(LocationBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class SampleRouteBase(BaseModel):
    """Sample routing between locations"""
    sample_id: str
    order_id: str
    source_location_id: str
    destination_location_id: str
    notes: Optional[str] = None


class SampleRouteCreate(SampleRouteBase):
    pass


class SampleRoute(SampleRouteBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: SampleRouteStatus = SampleRouteStatus.PENDING
    dispatched_at: Optional[datetime] = None
    dispatched_by: Optional[str] = None
    received_at: Optional[datetime] = None
    received_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== DEFAULT LOCATION ====================

DEFAULT_CENTRAL_LAB = {
    "id": "default-central-lab",
    "name": "Central Laboratory",
    "code": "CL01",
    "location_type": LocationType.CENTRAL_LAB,
    "address": "123 Medical Center, Healthcare City",
    "phone": "+1-234-567-8900",
    "email": "lab@lims.pro",
    "parent_location_id": None,
    "operating_hours": "24/7",
    "services": ["Hematology", "Biochemistry", "Microbiology", "Immunology", "Endocrinology", "Clinical Pathology", "Molecular Biology"],
    "is_sample_collection_point": True,
    "can_process_samples": True,
    "status": LocationStatus.ACTIVE,
    "created_at": datetime.now(timezone.utc).isoformat()
}


# ==================== LOCATION SERVICE ====================

class LocationService:
    """Service for managing locations"""
    
    def __init__(self, db):
        self.db = db
        self.collection = db.locations
        self.routes_collection = db.sample_routes
    
    async def ensure_default_location(self):
        """Ensure default central lab exists for backward compatibility"""
        existing = await self.collection.find_one({"id": DEFAULT_CENTRAL_LAB["id"]})
        if not existing:
            await self.collection.insert_one(DEFAULT_CENTRAL_LAB.copy())
        return DEFAULT_CENTRAL_LAB["id"]
    
    async def create_location(self, location: LocationCreate, created_by: str) -> dict:
        """Create a new location"""
        # Check for duplicate code
        existing = await self.collection.find_one({"code": location.code})
        if existing:
            raise ValueError(f"Location code '{location.code}' already exists")
        
        location_obj = Location(**location.model_dump())
        location_obj.created_by = created_by
        
        doc = location_obj.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        if doc.get("updated_at"):
            doc["updated_at"] = doc["updated_at"].isoformat()
        
        await self.collection.insert_one(doc)
        doc.pop("_id", None)
        return doc
    
    async def get_location(self, location_id: str) -> Optional[dict]:
        """Get location by ID"""
        return await self.collection.find_one({"id": location_id}, {"_id": 0})
    
    async def get_location_by_code(self, code: str) -> Optional[dict]:
        """Get location by code"""
        return await self.collection.find_one({"code": code}, {"_id": 0})
    
    async def get_all_locations(self, active_only: bool = True) -> List[dict]:
        """Get all locations"""
        query = {}
        if active_only:
            query["status"] = LocationStatus.ACTIVE
        return await self.collection.find(query, {"_id": 0}).sort("name", 1).to_list(100)
    
    async def get_collection_centers(self, parent_lab_id: Optional[str] = None) -> List[dict]:
        """Get all collection centers, optionally filtered by parent lab"""
        query = {"location_type": LocationType.COLLECTION_CENTER}
        if parent_lab_id:
            query["parent_location_id"] = parent_lab_id
        return await self.collection.find(query, {"_id": 0}).to_list(100)
    
    async def get_processing_labs(self) -> List[dict]:
        """Get all locations that can process samples"""
        return await self.collection.find(
            {"can_process_samples": True, "status": LocationStatus.ACTIVE},
            {"_id": 0}
        ).to_list(100)
    
    async def update_location(self, location_id: str, updates: dict) -> Optional[dict]:
        """Update a location"""
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await self.collection.update_one(
            {"id": location_id},
            {"$set": updates}
        )
        
        if result.modified_count == 0:
            return None
        
        return await self.get_location(location_id)
    
    async def get_user_locations(self, user_id: str) -> List[str]:
        """Get locations assigned to a user"""
        user = await self.db.users.find_one({"id": user_id}, {"_id": 0, "location_ids": 1})
        return user.get("location_ids", []) if user else []
    
    async def assign_user_to_location(self, user_id: str, location_id: str) -> bool:
        """Assign a user to a location"""
        result = await self.db.users.update_one(
            {"id": user_id},
            {"$addToSet": {"location_ids": location_id}}
        )
        return result.modified_count > 0
    
    async def remove_user_from_location(self, user_id: str, location_id: str) -> bool:
        """Remove a user from a location"""
        result = await self.db.users.update_one(
            {"id": user_id},
            {"$pull": {"location_ids": location_id}}
        )
        return result.modified_count > 0
    
    # ==================== SAMPLE ROUTING ====================
    
    async def create_sample_route(self, route: SampleRouteCreate, created_by: str) -> dict:
        """Create a sample routing record"""
        route_obj = SampleRoute(**route.model_dump())
        
        doc = route_obj.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        
        await self.routes_collection.insert_one(doc)
        doc.pop("_id", None)
        
        # Update sample with routing info
        await self.db.samples.update_one(
            {"id": route.sample_id},
            {"$set": {
                "route_id": doc["id"],
                "routing_status": SampleRouteStatus.PENDING,
                "destination_location_id": route.destination_location_id
            }}
        )
        
        return doc
    
    async def dispatch_sample(self, route_id: str, dispatched_by: str) -> Optional[dict]:
        """Mark sample as dispatched"""
        now = datetime.now(timezone.utc).isoformat()
        
        result = await self.routes_collection.update_one(
            {"id": route_id},
            {"$set": {
                "status": SampleRouteStatus.IN_TRANSIT,
                "dispatched_at": now,
                "dispatched_by": dispatched_by
            }}
        )
        
        if result.modified_count > 0:
            route = await self.routes_collection.find_one({"id": route_id}, {"_id": 0})
            if route:
                await self.db.samples.update_one(
                    {"id": route["sample_id"]},
                    {"$set": {"routing_status": SampleRouteStatus.IN_TRANSIT}}
                )
            return route
        return None
    
    async def receive_sample(self, route_id: str, received_by: str) -> Optional[dict]:
        """Mark sample as received at destination"""
        now = datetime.now(timezone.utc).isoformat()
        
        route = await self.routes_collection.find_one({"id": route_id})
        if not route:
            return None
        
        await self.routes_collection.update_one(
            {"id": route_id},
            {"$set": {
                "status": SampleRouteStatus.RECEIVED,
                "received_at": now,
                "received_by": received_by
            }}
        )
        
        # Update sample location
        await self.db.samples.update_one(
            {"id": route["sample_id"]},
            {"$set": {
                "routing_status": SampleRouteStatus.RECEIVED,
                "current_location_id": route["destination_location_id"],
                "received_at": now
            }}
        )
        
        return await self.routes_collection.find_one({"id": route_id}, {"_id": 0})
    
    async def get_pending_routes(self, location_id: Optional[str] = None) -> List[dict]:
        """Get pending sample routes"""
        query = {"status": {"$in": [SampleRouteStatus.PENDING, SampleRouteStatus.IN_TRANSIT]}}
        if location_id:
            query["$or"] = [
                {"source_location_id": location_id},
                {"destination_location_id": location_id}
            ]
        
        routes = await self.routes_collection.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
        
        # Enrich with sample and order info
        for route in routes:
            sample = await self.db.samples.find_one({"id": route["sample_id"]}, {"_id": 0})
            if sample:
                route["sample"] = sample
                order = await self.db.orders.find_one({"id": sample.get("order_id")}, {"_id": 0, "order_id": 1, "patient_name": 1})
                if order:
                    route["order"] = order
        
        return routes
    
    async def get_sample_route_history(self, sample_id: str) -> List[dict]:
        """Get routing history for a sample"""
        return await self.routes_collection.find(
            {"sample_id": sample_id},
            {"_id": 0}
        ).sort("created_at", 1).to_list(100)


# ==================== DATA VISIBILITY HELPERS ====================

def get_location_filter(user: dict, base_query: dict = None) -> dict:
    """
    Get query filter based on user's location access.
    Admins and lab managers see all data.
    Other users see only their assigned locations.
    Returns query dict for MongoDB.
    """
    query = base_query.copy() if base_query else {}
    
    # Admins and lab managers see everything
    if user.get("role") in ["admin", "lab_manager"]:
        return query
    
    # Users with no location restriction see everything (backward compatibility)
    user_locations = user.get("location_ids", [])
    if not user_locations:
        return query
    
    # Filter by user's assigned locations
    query["$or"] = [
        {"location_id": {"$in": user_locations}},
        {"location_id": None},  # Backward compatibility for records without location
        {"location_id": {"$exists": False}}
    ]
    
    return query


def get_default_location_id() -> str:
    """Get the default location ID for backward compatibility"""
    return DEFAULT_CENTRAL_LAB["id"]
