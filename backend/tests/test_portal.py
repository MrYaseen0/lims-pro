"""Patient portal: token issuance, report access, access logs."""
import hashlib

import server
from tests.conftest import make_test_doc, make_patient_via_api, make_order_via_api, make_user, login


async def _approved_order(admin_client, patient_id):
    test_doc = await make_test_doc("CBC")
    order = await make_order_via_api(admin_client, patient_id, test_doc)
    r = await admin_client.post("/api/results", json={
        "order_id": order["id"], "test_id": test_doc["id"],
        "values": {"Hemoglobin (Hb)": 14.0},
    })
    assert r.status_code == 200, r.text
    r = await admin_client.post("/api/approve", json={
        "order_id": order["id"], "test_id": test_doc["id"], "approved": True,
    })
    assert r.status_code == 200, r.text
    return order


async def test_portal_token_link_flow(client, admin_client):
    patient = await make_patient_via_api(admin_client, name="Portal Patient")
    await _approved_order(admin_client, patient["id"])

    r = await admin_client.post("/api/portal/access", json={
        "patient_id": patient["id"], "access_type": "token_link",
    })
    assert r.status_code == 200, r.text
    body = r.json()
    token = body["access_token"]
    assert token and body["expires_at"]

    # Only the SHA-256 digest is stored, never the raw token.
    docs = await server.db.portal_sessions.find({}).to_list(5)
    assert len(docs) == 1
    assert "access_token" not in docs[0]
    assert docs[0]["token_hash"] == hashlib.sha256(token.encode()).hexdigest()
    assert token not in str(docs[0])

    # Public report access with the token (no login).
    r = await client.get("/api/portal/reports", params={"token": token})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["patient"]["name"] == "Portal Patient"
    assert len(data["orders"]) == 1
    assert data["orders"][0]["tests"][0]["result"]["approved"] is True

    # Access was logged.
    r = await admin_client.get("/api/portal/access-logs")
    assert r.status_code == 200 and int(r.headers["X-Total-Count"]) >= 2


async def test_portal_invalid_and_expired_tokens(client, admin_client):
    r = await client.get("/api/portal/reports", params={"token": "nope"})
    assert r.status_code == 401

    patient = await make_patient_via_api(admin_client, name="Portal Patient 2")
    r = await admin_client.post("/api/portal/access", json={
        "patient_id": patient["id"], "access_type": "token_link", "expires_hours": -1,
    })
    assert r.status_code == 200, r.text
    r = await client.get("/api/portal/reports", params={"token": r.json()["access_token"]})
    assert r.status_code == 401  # already expired


async def test_portal_otp_flow(client, admin_client):
    patient = await make_patient_via_api(admin_client, name="OTP Patient")
    r = await admin_client.post("/api/portal/access", json={
        "patient_id": patient["id"], "access_type": "otp",
    })
    assert r.status_code == 200, r.text
    otp = r.json()["access_token"]
    assert len(otp) == 6 and otp.isdigit()
    r = await client.get("/api/portal/reports", params={"token": otp})
    assert r.status_code == 200, r.text


async def test_portal_grant_roles(client, admin_client):
    patient = await make_patient_via_api(admin_client, name="Role Patient")
    tech, tech_pw = await make_user("technician")
    await login(client, tech["email"], tech_pw)
    r = await client.post("/api/portal/access", json={"patient_id": patient["id"]})
    assert r.status_code == 403
    r = await client.get("/api/portal/access-logs")
    assert r.status_code == 403
