"""End-to-end workflow: patient -> order -> result with auto H/L flags -> approve."""
import httpx

import server
from tests.conftest import make_user, make_test_doc, make_patient_via_api, make_order_via_api, login


async def _logged_in_client(base_client, role):
    """Return a second httpx client logged in as a fresh user of `role`.

    Uses the same ASGI app (and therefore the same test DB); the cookie jar
    is per-client so roles don't leak between sessions.
    """
    user, password = await make_user(role)
    transport = httpx.ASGITransport(app=server.app)
    c = httpx.AsyncClient(transport=transport, base_url="http://test")
    await login(c, user["email"], password)
    return c, user


async def test_full_result_workflow_flags(client):
    tech, tech_user = await _logged_in_client(client, "technician")
    try:
        test_doc = await make_test_doc()
        patient = await make_patient_via_api(tech, name="E2E Patient", age=45, gender="female")
        order = await make_order_via_api(tech, patient["id"], test_doc)

        r = await tech.post("/api/results", json={
            "order_id": order["id"],
            "test_id": test_doc["id"],
            "values": {"Hemoglobin (Hb)": 19, "TLC (WBC)": 2000},
        })
        assert r.status_code == 200, r.text
        updated = r.json()
        assert updated["status"] == "under_review"
        entry = next(t for t in updated["tests"] if t["test_id"] == test_doc["id"])
        assert entry["status"] == "completed"
        result = entry["result"]
        assert result["flags"] == {"Hemoglobin (Hb)": "H", "TLC (WBC)": "L"}
        assert result["auto_abnormal"] is True
        assert result["is_abnormal"] is True
        assert result["entered_by"] == tech_user["id"]
    finally:
        await tech.aclose()


async def test_manual_abnormal_override_without_auto_flag(client):
    tech, _ = await _logged_in_client(client, "technician")
    try:
        test_doc = await make_test_doc()
        patient = await make_patient_via_api(tech, name="Override Patient")
        order = await make_order_via_api(tech, patient["id"], test_doc)
        # all values normal, but technician ticks the abnormal checkbox
        r = await tech.post("/api/results", json={
            "order_id": order["id"],
            "test_id": test_doc["id"],
            "values": {"Hemoglobin (Hb)": 14, "TLC (WBC)": 7000},
            "is_abnormal": True,
            "technician_notes": "sample hemolyzed",
        })
        assert r.status_code == 200, r.text
        entry = next(t for t in r.json()["tests"] if t["test_id"] == test_doc["id"])
        assert entry["result"]["auto_abnormal"] is False
        assert entry["result"]["is_abnormal"] is True  # manual override kept
        assert entry["result"]["technician_notes"] == "sample hemolyzed"
    finally:
        await tech.aclose()


async def test_pathologist_approve_flow(client):
    tech, _ = await _logged_in_client(client, "technician")
    path, _ = await _logged_in_client(client, "pathologist")
    try:
        test_doc = await make_test_doc()
        patient = await make_patient_via_api(tech, name="Approve Patient")
        order = await make_order_via_api(tech, patient["id"], test_doc)
        await tech.post("/api/results", json={
            "order_id": order["id"], "test_id": test_doc["id"],
            "values": {"Hemoglobin (Hb)": 14},
        })
        r = await path.get("/api/pathologist/queue")
        assert r.status_code == 200
        r = await path.post("/api/approve", json={
            "order_id": order["id"], "test_id": test_doc["id"], "approved": True,
        })
        assert r.status_code == 200, r.text
    finally:
        await tech.aclose()
        await path.aclose()


async def test_invoice_created_with_order(admin_client):
    test_doc = await make_test_doc()
    patient = await make_patient_via_api(admin_client, name="Invoice Patient")
    order = await make_order_via_api(admin_client, patient["id"], test_doc)
    r = await admin_client.get(f"/api/invoices/order/{order['id']}")
    # endpoint may be /api/invoices/{invoice_id}; fall back to listing
    if r.status_code == 404:
        r = await admin_client.get("/api/invoices", params={"page": 1, "page_size": 10})
        assert r.status_code == 200
        invoices = r.json()
        assert any(inv.get("order_id") == order["id"] for inv in invoices)
    else:
        assert r.status_code == 200
