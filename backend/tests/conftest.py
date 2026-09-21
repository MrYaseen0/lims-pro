"""Shared pytest fixtures for the LIMS.Pro backend test suite.

Environment is configured BEFORE importing the app module so that the
JWT fail-fast check picks up test values. The Motor client is (re)created
per test inside that test's event loop (see server.init_db) because a
client bound to one loop cannot be used from another.
"""
import os
import sys
import uuid

os.environ["JWT_SECRET"] = "test-secret-key-for-pytest-suite"
os.environ["MONGO_URL"] = "mongodb://localhost:27017"
os.environ["DB_NAME"] = "lims_test_db"
os.environ["COOKIE_SECURE"] = "false"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import pytest

import server  # noqa: E402  (import after env setup is intentional)

COLLECTIONS = [
    "users", "patients", "orders", "samples", "tests", "doctors",
    "invoices", "audit_logs", "portal_sessions", "portal_otps",
    "refresh_tokens", "critical_alerts",
]


@pytest.fixture()
async def client():
    """httpx client hitting the ASGI app, with a fresh DB-bound Motor client."""
    # Recreate the Motor client per-test to bind to the test's event loop.
    # We clear collections in SETUP only (not teardown) to avoid a race where
    # the previous test's teardown delete_many wipes the next test's data.
    server.reset_db()
    await server.ensure_indexes()
    for name in COLLECTIONS:
        await server.db[name].delete_many({})
    server._login_attempts.clear()
    transport = httpx.ASGITransport(app=server.app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    server._login_attempts.clear()


async def make_user(role="admin", email=None, password="Password123"):
    email = email or f"{role}-{uuid.uuid4().hex[:8]}@example.com"
    user = {
        "id": str(uuid.uuid4()),
        "email": email,
        "name": f"Test {role.title()}",
        "role": role,
        "phone": "+920000000000",
        "password": server.hash_password(password),
        "is_active": True,
    }
    await server.db.users.insert_one(user)
    return user, password


async def login(client, email, password):
    r = await client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r


@pytest.fixture()
async def admin_user():
    return await make_user("admin")


@pytest.fixture()
async def tech_user():
    return await make_user("technician")


@pytest.fixture()
async def admin_client(client, admin_user):
    user, password = admin_user
    await login(client, user["email"], password)
    assert "lims_token" in client.cookies
    return client


@pytest.fixture()
async def tech_client(client, tech_user):
    user, password = tech_user
    await login(client, user["email"], password)
    return client


async def make_test_doc(code="CBC", ranges=None):
    """Insert a test catalogue entry and return it."""
    ranges = ranges if ranges is not None else [
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "12 - 17"},
        {"parameter": "TLC (WBC)", "unit": "/uL", "normal_range": "4000 - 11000"},
    ]
    doc = {
        "id": str(uuid.uuid4()),
        "name": f"Test {code}",
        "code": code,
        "category": "Hematology",
        "sample_type": "Blood",
        "price": 500.0,
        "turn_around_time": 24,
        "reference_ranges": ranges,
        "is_active": True,
    }
    await server.db.tests.insert_one(doc)
    return doc


async def make_patient_via_api(client, name="Test Patient", age=30, gender="male"):
    r = await client.post("/api/patients", json={
        "name": name, "age": age, "gender": gender, "phone": "+921234567890",
    })
    assert r.status_code == 200, r.text
    return r.json()


async def make_order_via_api(client, patient_id, test_doc):
    r = await client.post("/api/orders", json={
        "patient_id": patient_id,
        "tests": [{
            "test_id": test_doc["id"],
            "test_name": test_doc["name"],
            "test_code": test_doc["code"],
            "price": test_doc["price"],
        }],
    })
    assert r.status_code == 200, r.text
    return r.json()
