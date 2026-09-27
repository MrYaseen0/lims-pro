"""Multi-branch: default seed, CRUD, and request scoping."""
import httpx

import server
from app.services.seed_data import ensure_default_branch
from tests.conftest import make_user, login, make_patient_via_api


def _fresh_client():
    transport = httpx.ASGITransport(app=server.app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def test_default_branch_seeded_and_idempotent(client, admin_client):
    branch_id = await ensure_default_branch()
    r = await admin_client.get("/api/branches")
    assert r.status_code == 200, r.text
    mains = [b for b in r.json() if b["code"] == "MAIN"]
    assert len(mains) == 1 and mains[0]["name"] == "Main Branch"
    assert mains[0]["id"] == branch_id
    await ensure_default_branch()
    count = await server.db.branches.count_documents({"code": "MAIN"})
    assert count == 1


async def test_branch_crud_admin_only(client, admin_client):
    await ensure_default_branch()
    r = await admin_client.post("/api/branches", json={
        "name": "DHA Branch", "code": "DHA", "address": "DHA Lahore", "phone": "+92111",
    })
    assert r.status_code == 200, r.text
    branch = r.json()
    assert branch["code"] == "DHA" and branch["is_active"] is True

    r = await admin_client.post("/api/branches", json={"name": "Dupe", "code": "dha"})
    assert r.status_code == 400  # code uniqueness (case-insensitive)

    r = await admin_client.put(f"/api/branches/{branch['id']}", json={"name": "DHA Renamed"})
    assert r.status_code == 200 and r.json()["name"] == "DHA Renamed"

    async with _fresh_client() as tc:
        tech, tech_pw = await make_user("technician")
        await login(tc, tech["email"], tech_pw)
        r = await tc.get("/api/branches")
        assert r.status_code == 200  # any authenticated user may list
        r = await tc.post("/api/branches", json={"name": "Nope", "code": "NOP"})
        assert r.status_code == 403
        r = await tc.delete(f"/api/branches/{branch['id']}")
        assert r.status_code == 403

    r = await admin_client.delete(f"/api/branches/{branch['id']}")
    assert r.status_code == 200, r.text

    main = await server.db.branches.find_one({"code": "MAIN"})
    r = await admin_client.delete(f"/api/branches/{main['id']}")
    assert r.status_code == 400  # default branch is protected


async def test_branch_scoping_patients(client, admin_client):
    main_id = await ensure_default_branch()
    r = await admin_client.post("/api/branches", json={"name": "Branch B", "code": "BRB"})
    assert r.status_code == 200, r.text
    b_id = r.json()["id"]

    user_a, pw_a = await make_user("receptionist", email="scope-a@example.com")
    user_b, pw_b = await make_user("receptionist", email="scope-b@example.com")
    await server.db.users.update_one({"id": user_a["id"]}, {"$set": {"branch_id": main_id}})
    await server.db.users.update_one({"id": user_b["id"]}, {"$set": {"branch_id": b_id}})

    async with _fresh_client() as ca, _fresh_client() as cb:
        await login(ca, user_a["email"], pw_a)
        await login(cb, user_b["email"], pw_b)

        pa = await make_patient_via_api(ca, name="Patient A")
        assert pa["branch_id"] == main_id

        # B cannot see A's patient.
        r = await cb.get("/api/patients")
        assert r.status_code == 200
        assert all(p["id"] != pa["id"] for p in r.json())

        pb = await make_patient_via_api(cb, name="Patient B")
        assert pb["branch_id"] == b_id

        # A cannot see B's patient.
        r = await ca.get("/api/patients")
        assert all(p["id"] != pb["id"] for p in r.json())

        # Admin ?branch_id override scopes to that branch only.
        r = await admin_client.get("/api/patients", params={"branch_id": b_id})
        ids = [p["id"] for p in r.json()]
        assert pb["id"] in ids and pa["id"] not in ids

        # Admin without override sees everything.
        r = await admin_client.get("/api/patients")
        ids = [p["id"] for p in r.json()]
        assert pa["id"] in ids and pb["id"] in ids


async def test_branch_scoping_orders_and_inventory(client, admin_client):
    main_id = await ensure_default_branch()
    user, pw = await make_user("receptionist", email="scope-c@example.com")
    await server.db.users.update_one({"id": user["id"]}, {"$set": {"branch_id": main_id}})

    async with _fresh_client() as cc:
        await login(cc, user["email"], pw)
        patient = await make_patient_via_api(cc, name="Scoped Patient")
        r = await cc.post("/api/orders", json={
            "patient_id": patient["id"],
            "tests": [{"test_id": "t1", "test_name": "T", "test_code": "T", "price": 10.0}],
        })
        assert r.status_code == 200, r.text
        assert r.json()["branch_id"] == main_id

        r = await cc.get("/api/orders")
        assert r.status_code == 200
        assert all(o["branch_id"] == main_id for o in r.json())

        # Non-admin inventory roles stay forbidden even with a branch.
        r = await cc.post("/api/inventory", json={
            "name": "X", "category": "reagent", "quantity": 1, "min_stock": 1,
        })
        assert r.status_code == 403


async def test_register_accepts_branch_id(client):
    main_id = await ensure_default_branch()
    r = await client.post("/api/auth/register", json={
        "email": "branched@example.com", "name": "Branched User",
        "role": "receptionist", "password": "Password123", "branch_id": main_id,
    })
    assert r.status_code == 200, r.text
    assert r.json()["user"]["branch_id"] == main_id
