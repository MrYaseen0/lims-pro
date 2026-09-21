"""MongoDB lifecycle.

The Motor client is created lazily inside the running event loop (import-time
creation breaks under TestClient/uvicorn workers that run the app on a
different loop). ``db`` is a proxy that is never rebound, so routers can do
``from app.core.database import db`` and always reach the live handle.
"""
from motor.motor_asyncio import AsyncIOMotorClient

from audit_logger import create_audit_logger
from app.core import config

audit_logger = create_audit_logger(None)  # bound to the live handle by init_db()

_client = None
_target = None


class _DatabaseProxy:
    """Forwards attribute/item access to the live Motor database handle.

    The proxy object itself is never replaced, so ``from ... import db``
    keeps working across init_db()/reset_db() rebinds.
    """

    def _resolve(self):
        if _target is None:
            raise RuntimeError(
                "Database not initialized. Call init_db() first "
                "(the FastAPI lifespan does this automatically)."
            )
        return _target

    def __getattr__(self, name):
        return getattr(self._resolve(), name)

    def __getitem__(self, name):
        return self._resolve()[name]


db = _DatabaseProxy()


def get_client():
    """Return the live Motor client (None before init_db)."""
    return _client


def init_db():
    """Create the Motor client and bind module globals. Idempotent."""
    global _client, _target
    if _target is None:
        _client = AsyncIOMotorClient(config.MONGO_URL)
        _target = _client[config.DB_NAME]
        # Rebind the audit logger to the live database handle.
        audit_logger.bind(_target)
    return db


def reset_db():
    """Test helper: drop the client so the next init_db() rebinds to the
    current event loop, then re-initialize immediately."""
    global _client, _target
    if _client is not None:
        _client.close()
    _client = None
    _target = None
    return init_db()


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
